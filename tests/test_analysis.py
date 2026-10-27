import json
import tempfile
import unittest
from pathlib import Path

from flowrefine.analysis import analyze_run


class AnalysisTests(unittest.TestCase):
    def test_missing_invalid_and_costs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def put(name, value):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            put("run/tasks_public.json", [{"id": "t", "split": "test", "family": "chain"}])
            put("references.json", {"t": {"nodes": [{"id": "a", "label": "Begin", "type": "start"}], "edges": []}})
            scene = {"canvas": {"width": 400, "height": 300}, "nodes": [{"id": "a", "label": "Begin", "type": "start", "x": 50, "y": 50, "width": 150, "height": 80}], "edges": []}
            put("run/t/B0/status.json", {"valid": True})
            put("run/t/B0/scene.json", scene)
            put("run/t/B1/status.json", {"valid": False, "parse_errors": ["bad JSON"]})
            put("run/t/B3/status.json", {"valid": False, "reason": "initial_scene_invalid"})
            for component, seconds in (("B0", 2), ("B1", 3), ("visual", 4)):
                put(f"run/t/{component}/call_test_0.json", {"reference_access": False, "response": {"elapsed_seconds": seconds, "usage": {"prompt_tokens": 10, "completion_tokens": 5}}})
            result = analyze_run(root / "run", root / "references.json", root / "output")
            self.assertEqual(result["actual_logged_calls"], 3)
            self.assertEqual(result["actual_logged_inference_seconds"], 9)
            self.assertEqual(result["arms"]["B0"]["exact_semantic_mean"], 1)
            self.assertEqual(result["arms"]["B1"]["edge_f1_mean"], 0)
            self.assertEqual(result["arms"]["B1"]["invalid"], 1)
            self.assertIsNone(result["arms"]["B1"]["geometry_errors_valid_mean"])
            self.assertEqual(result["arms"]["B1"]["standalone_inference_seconds_mean"], 5)
            self.assertEqual(result["arms"]["B2"]["executed"], 0)
            self.assertIsNone(result["arms"]["B2"]["edge_f1_mean"])
            self.assertEqual(result["paired_differences"]["B1_minus_B0"]["edge_f1"]["n"], 1)
            self.assertEqual(result["paired_differences"]["B2_minus_B0"]["edge_f1"]["n"], 0)
            self.assertEqual(result["arms"]["B3"]["executed"], 1)
            self.assertEqual(result["arms"]["B3"]["invalid"], 1)
            self.assertEqual(result["arms"]["B3"]["exact_semantic_mean"], 0)
            for name in ("metrics.csv", "raw_calls.csv", "aggregate.json", "SUMMARY.md", "semantic_quality.png", "geometry_coverage.png", "quality_cost.png"):
                self.assertTrue((root / "output" / name).is_file())


if __name__ == "__main__":
    unittest.main()
