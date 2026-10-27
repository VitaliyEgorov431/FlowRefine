"""Regression checks for fixed-key layout protocol; fixtures are not model evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from flowrefine.compact import to_scene
from flowrefine.layout_followup import (apply_object_positions, position_schema, model_layout,
                                       messages_for_layout, initialize_layout)
from flowrefine.runner import write_json, read_json
import test_followup as fixture_module
from test_followup import TASK, COMPACT


class Backend:
    def __init__(self, texts):
        self.texts, self.calls = iter(texts), 0

    def complete_layout(self, messages, schema, max_tokens):
        self.calls += 1
        return {"text": next(self.texts), "usage": {}, "backend": "TEST_FIXTURE"}


class ObjectLayoutTests(unittest.TestCase):
    def output(self):
        return {"positions": {"0": {"column": 0, "row": 0},
                              "1": {"column": 1, "row": 2},
                              "2": {"column": 2, "row": 3}}}

    def test_per_node_schema_uses_enum_and_required_fixed_keys(self):
        schema = position_schema(to_scene(COMPACT))
        nodes = schema["properties"]["positions"]
        self.assertEqual(nodes["required"], ["0", "1", "2"])
        self.assertFalse(nodes["additionalProperties"])
        for value in nodes["properties"].values():
            self.assertEqual(value["properties"]["column"]["enum"], [0, 1, 2])
            self.assertEqual(value["properties"]["row"]["enum"], list(range(8)))
        # Grammar compilation exercises the installed runtime schema converter without loading a model.
        try:
            from llama_cpp import LlamaGrammar
        except ImportError:
            return
        grammar = LlamaGrammar.from_json_schema(json.dumps(schema), verbose=False)
        self.assertIsNotNone(grammar)

    def test_coordinates_change_while_loop_and_branch_content_remain_identical(self):
        scene = to_scene(COMPACT)
        result = apply_object_positions(scene, self.output())
        self.assertEqual(result["edges"], scene["edges"])
        self.assertEqual(result["canvas"], scene["canvas"])
        for before, after in zip(scene["nodes"], result["nodes"]):
            self.assertEqual({k: v for k, v in before.items() if k not in ("x", "y")},
                             {k: v for k, v in after.items() if k not in ("x", "y")})
        self.assertEqual((result["nodes"][2]["x"], result["nodes"][2]["y"]), (535, 540))

    def test_missing_keys_semantic_injection_and_out_of_range_values_rejected(self):
        bad = [self.output() for _ in range(4)]
        bad[0]["positions"].pop("1")
        bad[1]["positions"]["0"]["label"] = "Injected"
        bad[2]["positions"]["2"]["column"] = 5
        bad[3]["positions"]["0"]["row"] = False
        for obj in bad:
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                apply_object_positions(to_scene(COMPACT), obj)

    def test_truncation_retry_logs_both_calls_and_resume_does_not_reinfer(self):
        scene = to_scene(COMPACT)
        messages = messages_for_layout(TASK, scene, {}, "No issues")
        self.assertIn('"0": {"label": "Begin"', messages[1]["content"])
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            backend = Backend(['{"positions":', json.dumps(self.output())])
            result, errors = model_layout(folder, messages, scene, backend, 900)
            self.assertIsNotNone(result)
            self.assertEqual(len(errors), 1)
            self.assertTrue((folder/"call_repair_0.json").exists())
            self.assertTrue((folder/"call_repair_1.json").exists())
            self.assertIn("output_schema", read_json(folder/"call_repair_0.json"))
            model_layout(folder, messages, scene, backend, 900)
            self.assertEqual(backend.calls, 2)

    def test_invalid_both_attempts_has_no_silent_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            result, errors = model_layout(Path(directory), [], to_scene(COMPACT), Backend(['{}', '{}']), 900)
            self.assertIsNone(result)
            self.assertEqual(len(errors), 2)

    def test_manifest_resume_rejects_changed_failed_run_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = fixture_module.FollowupTests().make_baseline(directory)
            failed = Path(directory)/"failed"
            write_json(failed/"manifest.json", {"fixture": True})
            output = Path(directory)/"layout"
            initialize_layout(baseline, output, failed)
            initialize_layout(baseline, output, failed)
            write_json(failed/"manifest.json", {"fixture": "changed"})
            with self.assertRaisesRegex(ValueError, "changed"):
                initialize_layout(baseline, output, failed)


if __name__ == "__main__":
    unittest.main()

