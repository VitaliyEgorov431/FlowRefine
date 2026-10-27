import json
from pathlib import Path
import tempfile
import unittest

from flowrefine.followup_analysis import analyze_followup, audit_claims, paired_summary


class FollowupAnalysisTests(unittest.TestCase):
    def test_claim_checks_image_and_requirement_separately(self):
        scene = {"nodes": [{"id": "a", "label": "Begin"}, {"id": "b", "label": "Review"}, {"id": "c", "label": "Finish"}],
                 "edges": [{"source": "a", "target": "c"}]}
        reference = {"nodes": scene["nodes"], "edges": [{"source": "a", "target": "b"}]}
        claims = audit_claims("Begin is connected with Finish. Review is connected with Finish. If Finish then Begin.", scene, reference)
        supported = claims[0]
        self.assertEqual(supported["assessment"], "supported_by_B0")
        self.assertFalse(supported["edge_required"])
        self.assertEqual(claims[2]["assessment"], "contradicted_by_B0")
        self.assertEqual(claims[-1]["assessment"], "uncertain")
        self.assertTrue(all(c["branch_label_assessment"] == "not_inferred" for c in claims))

    def test_empty_pairs_not_fabricated(self):
        result = paired_summary([])
        self.assertEqual(result["edge_f1"]["n"], 0)
        self.assertIsNone(result["edge_f1"]["mean"])
        self.assertEqual(result["exact_transitions"]["fixed"], 0)

    def test_ocr_intermediate_nodes_never_become_direct_claim(self):
        scene = {"nodes": [{"id": "a", "label": "Parcel workflow begins"},
                           {"id": "b", "label": "Attach shipping label"}], "edges": []}
        text = "Parcel workflow begins with Receiver parcel connected with Wrought parcel which is then connected with Attach shipping label"
        claims = audit_claims(text, scene, scene)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["assessment"], "uncertain")
        claims = audit_claims("Parcel workflow begins with Unknown parcel connected with Attach shipping label", scene, scene)
        self.assertEqual(claims[0]["assessment"], "uncertain")

    def test_coverage_failure_transitions_and_shared_costs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def put(path, value):
                path = root/path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            task = {"id": "t", "split": "test", "family": "chain", "prompt": "Begin"}
            scene = {"canvas": {"width": 400, "height": 300}, "nodes": [{"id": "a", "label": "Begin", "type": "start", "x": 50, "y": 50, "width": 150, "height": 80}], "edges": []}
            put("baseline/tasks_public.json", [task])
            put("refs.json", {"t": scene})
            for folder in ("baseline/t/B0", "followup/t/L3"):
                put(folder+"/scene.json", scene)
                put(folder+"/status.json", {"valid": True})
            put("followup/t/C0/status.json", {"valid": False, "parse_errors": ["invalid JSON"]})
            for source, component, seconds in (("baseline", "B0", 2), ("baseline", "visual", 3), ("followup", "C0", 5), ("followup", "L3", 7)):
                put(f"{source}/t/{component}/call_test_0.json", {"reference_access": False, "response": {"elapsed_seconds": seconds}})
            result = analyze_followup(root/"baseline", root/"followup", root/"out", root/"refs.json")
            self.assertEqual(result["baseline_actual_logged_calls"], 2)
            self.assertEqual(result["followup_actual_logged_calls"], 2)
            self.assertEqual(result["followup_actual_logged_inference_seconds"], 12)
            self.assertEqual(result["arms"]["C0"]["edge_f1_mean"], 0)
            self.assertIsNone(result["arms"]["C0"]["geometry_errors_valid_mean"])
            self.assertEqual(result["arms"]["L3"]["standalone_inference_seconds_mean"], 12)
            self.assertEqual(result["arms"]["C0"]["standalone_inference_seconds_mean"], 7)
            self.assertIsNone(result["arms"]["B1"]["edge_f1_mean"])
            self.assertEqual(result["paired_differences"]["C0_minus_B0"]["exact_transitions"]["broken"], 1)
            self.assertEqual(result["paired_differences"]["B3_minus_C0"]["edge_f1"]["n"], 0)
            self.assertEqual(result["reference_access_violations"], [])
            for name in ("metrics.csv", "aggregate.json", "critic_audit.json", "CRITIC_AUDIT_RU.md", "case_studies.json", "CASE_STUDIES_RU.md"):
                self.assertTrue((root/"out"/name).is_file())
            # A revised layout arm replaces only the main L3 score, while all
            # failed first-attempt costs remain in the total and audit.
            put("followup/t/L3/status.json", {"valid": False})
            put("layout_v2/t/L3/scene.json", scene)
            put("layout_v2/t/L3/status.json", {"valid": True})
            put("layout_v2/t/L3/call_test_0.json", {"reference_access": False, "response": {"elapsed_seconds": 11}})
            revised = analyze_followup(root/"baseline", root/"followup", root/"revised", root/"refs.json", root/"layout_v2")
            self.assertEqual(revised["arms"]["L3"]["valid"], 1)
            self.assertEqual(revised["arms"]["L3"]["standalone_inference_seconds_mean"], 16)
            self.assertEqual(revised["failed_layout_attempts"]["invalid"], 1)
            self.assertEqual(revised["failed_layout_attempts"]["logged_inference_seconds"], 7)
            self.assertEqual(revised["followup_actual_logged_inference_seconds"], 23)
            self.assertEqual(revised["followup_actual_logged_calls"], 3)
            self.assertEqual(revised["layout_revision_actual_logged_calls"], 1)


if __name__ == "__main__":
    unittest.main()
