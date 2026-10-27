"""Temporary fake-backend fixtures: never experimental model evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flowrefine.analysis import analyze_run
from flowrefine.runner import generate, critique, initialize_run, read_json, write_json


TASK = {"id": "fixture", "split": "development", "family": "chain",
        "prompt": "Start at Begin, then Finish."}
COMPACT = {"nodes": [["Begin", "start", 0, 0],
                     ["Finish", "end", 0, 1]],
           "edges": [["Begin", "Finish", ""]]}
REFERENCE = {"nodes": [{"id": "a", "type": "start", "label": "Begin"},
                       {"id": "b", "type": "end", "label": "Finish"}],
             "edges": [{"source": "a", "target": "b", "label": ""}]}


class FixtureText:
    def __init__(self, fail=False):
        self.calls, self.fail = 0, fail

    def complete(self, *args, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("fixture text failure")
        return {"text": json.dumps(COMPACT), "elapsed_seconds": 2,
                "backend": "TEST_FIXTURE", "usage": {"prompt_tokens": 10,
                                                       "completion_tokens": 20}}


class FixtureVision:
    def __init__(self):
        self.calls = 0

    def critique(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("fixture transient vision failure")
        return {"text": "No visible issues.", "elapsed_seconds": 3,
                "backend": "TEST_FIXTURE", "usage": {"prompt_tokens": 30,
                                                       "completion_tokens": 5}}


class RunnerTests(unittest.TestCase):
    def test_critique_before_generation_does_not_poison_later_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = FixtureVision()
            # This fixture backend has already spent its deliberate failure.
            backend.calls = 1
            critique(root, [TASK], backend)
            self.assertEqual(backend.calls, 1)
            self.assertFalse((root / TASK["id"] / "visual" / "status.json").exists())
            generate(root, [TASK], FixtureText())
            critique(root, [TASK], backend)
            self.assertEqual(backend.calls, 2)
            self.assertTrue(read_json(root / TASK["id"] / "visual" / "status.json")["available"])

    def test_interrupted_render_recovers_cached_response_without_new_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root, backend = Path(directory), FixtureText()
            folder = root / TASK["id"] / "B0"
            with patch("flowrefine.runner.render_scene", side_effect=RuntimeError("fixture render failure")):
                with self.assertRaisesRegex(RuntimeError, "render failure"):
                    generate(root, [TASK], backend)
            self.assertFalse((folder / "status.json").exists())
            self.assertTrue((folder / "call_generate_0.json").exists())
            generate(root, [TASK], backend)
            self.assertEqual(backend.calls, 1)
            self.assertTrue(read_json(folder / "status.json")["valid"])
            self.assertTrue((folder / "chart.png").exists())
            self.assertTrue((folder / "chart.svg").exists())

    def test_successful_generation_resume_skips_model(self):
        with tempfile.TemporaryDirectory() as directory:
            backend = FixtureText()
            generate(directory, [TASK], backend)
            generate(directory, [TASK], backend)
            self.assertEqual(backend.calls, 1)

    def test_visual_retry_preserves_both_attempts_and_cost_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "tasks_public.json", [TASK])
            write_json(root / "manifest.json", {"provenance": "TEST_FIXTURE"})
            write_json(root / "references.json", {TASK["id"]: REFERENCE})
            generate(root, [TASK], FixtureText())
            backend = FixtureVision()
            with self.assertRaisesRegex(RuntimeError, "transient vision"):
                critique(root, [TASK], backend)
            critique(root, [TASK], backend)
            critique(root, [TASK], backend)
            self.assertEqual(backend.calls, 2)
            folder = root / TASK["id"] / "visual"
            self.assertEqual(len(list(folder.glob("call_visual_*.json"))), 2)
            self.assertIn("error", read_json(folder / "call_visual_0.json")["response"])
            self.assertEqual(read_json(folder / "call_visual_1.json")["response"]["text"], "No visible issues.")
            result = analyze_run(root, root / "references.json", root / "analysis")
            self.assertEqual(result["actual_logged_calls"], 3)
            self.assertGreaterEqual(result["actual_logged_inference_seconds"], 5)

    def test_failed_text_call_is_logged_without_invented_output_and_not_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            root, backend = Path(directory), FixtureText(fail=True)
            with self.assertRaisesRegex(RuntimeError, "fixture text failure"):
                generate(root, [TASK], backend)
            folder = root / TASK["id"] / "B0"
            record = read_json(folder / "call_generate_0.json")
            self.assertIn("fixture text failure", record["response"]["error"])
            self.assertNotIn("text", record["response"])
            self.assertGreaterEqual(record["response"]["elapsed_seconds"], 0)
            self.assertFalse((folder / "status.json").exists())
            with self.assertRaisesRegex(RuntimeError, "Previous inference call failed"):
                generate(root, [TASK], backend)
            self.assertEqual(backend.calls, 1)
            write_json(root / "tasks_public.json", [TASK])
            write_json(root / "manifest.json", {"provenance": "TEST_FIXTURE"})
            write_json(root / "references.json", {TASK["id"]: REFERENCE})
            result = analyze_run(root, root / "references.json", root / "analysis")
            self.assertEqual(result["actual_logged_calls"], 1)
            self.assertEqual(result["arms"]["B0"]["executed"], 0)

    def test_changed_inference_fingerprint_rejected_but_unchanged_resume_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            initialize_run(directory, [TASK], {"backend": "TEST_FIXTURE"})
            initialize_run(directory, [TASK], {"backend": "TEST_FIXTURE"})
            path = Path(directory) / "manifest.json"
            manifest = read_json(path)
            manifest["source_sha256"]["prompts.py"] = "fixture-different-source"
            write_json(path, manifest)
            with self.assertRaisesRegex(ValueError, "source changed"):
                initialize_run(directory, [TASK], {"backend": "TEST_FIXTURE"})


if __name__ == "__main__":
    unittest.main()
