"""Supplemental controls: topology, provenance and interruption regression checks."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flowrefine.compact import to_scene
from flowrefine.followup import (apply_positions, initialize_followup, run_followup,
                                 control_messages, layout_messages)
from flowrefine.runner import read_json, write_json

TASK = {"id": "fixture", "split": "development", "family": "branch",
        "prompt": "Begin -> Ready?; Yes -> Finish; No -> Begin."}
COMPACT = {"nodes": [["Begin", "start", 1, 0], ["Ready?", "decision", 1, 1],
                      ["Finish", "end", 1, 2]],
           "edges": [["Begin", "Ready?", ""], ["Ready?", "Finish", "Yes"],
                     ["Ready?", "Begin", "No"]]}


class FixtureBackend:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, **kwargs):
        self.calls += 1
        return {"text": json.dumps({"positions": [[2, 2, 3], [0, 0, 0], [1, 1, 2]]}),
                "elapsed_seconds": 0, "usage": {}, "backend": "TEST_FIXTURE"}


class FollowupTests(unittest.TestCase):
    def make_baseline(self, directory):
        root = Path(directory) / "baseline"
        model = Path(directory) / "fixture-model.gguf"
        model.write_bytes(b"TEST_FIXTURE_NOT_A_MODEL")
        write_json(root / "manifest.json", {"settings": {"text_model": str(model),
            "threads": 4, "max_tokens": 900, "temperature": 0.0}})
        write_json(root / "tasks_public.json", [TASK])
        write_json(root / "fixture/B0/scene.json", to_scene(COMPACT))
        write_json(root / "fixture/B0/program_feedback.json", {"issues": []})
        write_json(root / "fixture/B0/status.json", {"valid": True})
        write_json(root / "fixture/visual/feedback.json", {"text": "Remove the No branch."})
        write_json(root / "fixture/visual/status.json", {"available": True})
        return root

    def test_layout_preserves_loop_branch_labels_ids_types_dimensions_and_input(self):
        scene = to_scene(COMPACT)
        # IDs need not equal labels, and canvas/style metadata must survive too.
        scene["canvas"]["width"] = 900
        original = copy.deepcopy(scene)
        result = apply_positions(scene, {"positions": [[2, 2, 3], [0, 0, 0], [1, 1, 2]]})
        self.assertEqual(scene, original)
        self.assertEqual(result["edges"], original["edges"])
        self.assertEqual(result["canvas"], original["canvas"])
        for actual, before in zip(result["nodes"], original["nodes"]):
            self.assertEqual({k: v for k, v in actual.items() if k not in ("x", "y")},
                             {k: v for k, v in before.items() if k not in ("x", "y")})
        self.assertEqual((result["nodes"][2]["x"], result["nodes"][2]["y"]), (535, 540))

    def test_layout_rejects_semantic_injection_and_ambiguous_coordinates(self):
        for obj in ({"positions": [[0, 0, 0]], "edges": []},
                    {"positions": [[0, 0, 0], [0, 1, 1], [2, 2, 2]]},
                    {"positions": [[0, 0, 0], [1, 3, 1], [2, 2, 2]]},
                    {"positions": [[False, 0, 0], [1, 1, 1], [2, 2, 2]]}):
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                apply_positions(to_scene(COMPACT), obj)

    def test_resume_rejects_changed_baseline_model_settings_or_source(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = self.make_baseline(directory)
            output = Path(directory) / "followup"
            initialize_followup(baseline, output)
            initialize_followup(baseline, output)
            feedback = baseline / "fixture/visual/feedback.json"
            old = feedback.read_bytes()
            write_json(feedback, {"text": "Different feedback"})
            with self.assertRaisesRegex(ValueError, "changed"):
                initialize_followup(baseline, output)
            feedback.write_bytes(old)
            model = Path(directory) / "fixture-model.gguf"
            model.write_bytes(b"CHANGED")
            with self.assertRaisesRegex(ValueError, "changed"):
                initialize_followup(baseline, output)
            model.write_bytes(b"TEST_FIXTURE_NOT_A_MODEL")
            with patch("flowrefine.followup.source_hashes", return_value={"followup.py": "changed"}):
                with self.assertRaisesRegex(ValueError, "changed"):
                    initialize_followup(baseline, output)
            manifest = read_json(output / "manifest.json")
            manifest["settings"]["max_tokens"] = 100
            write_json(output / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "changed"):
                initialize_followup(baseline, output)

    def test_layout_recovers_cached_call_after_render_failure_and_skips_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = self.make_baseline(directory)
            output, backend = Path(directory) / "followup", FixtureBackend()
            with patch("flowrefine.runner.render_scene", side_effect=RuntimeError("render interrupted")):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    run_followup(baseline, output, [TASK], backend, ("L3",))
            self.assertFalse((output / "fixture/L3/status.json").exists())
            run_followup(baseline, output, [TASK], backend, ("L3",))
            run_followup(baseline, output, [TASK], backend, ("L3",))
            self.assertEqual(backend.calls, 1)
            result = read_json(output / "fixture/L3/scene.json")
            self.assertEqual(result["edges"], to_scene(COMPACT)["edges"])
            self.assertTrue(read_json(output / "fixture/L3/layout_audit.json")["topology_preserved"])
            self.assertTrue((output / "fixture/L3/chart.png").exists())

    def test_prompts_expose_feedback_only_to_layout_arm(self):
        scene = to_scene(COMPACT)
        control = json.dumps(control_messages(TASK, scene))
        layout = json.dumps(layout_messages(TASK, scene, {"marker": "PROGRAM_SENTINEL"}, "VISUAL_SENTINEL"))
        self.assertNotIn("Programmatic feedback", control)
        self.assertNotIn("Visual feedback", control)
        self.assertIn("original requested process", control)
        self.assertIn("PROGRAM_SENTINEL", layout)
        self.assertIn("VISUAL_SENTINEL", layout)


if __name__ == "__main__":
    unittest.main()
