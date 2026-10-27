import copy
import unittest

from flowrefine.dataset import build_dataset
from flowrefine.evaluation import evaluate_scene


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        tasks, refs = build_dataset()
        self.ref = refs["test_branch_01"]
        self.scene = copy.deepcopy(self.ref)

    def test_exact_and_punctuation(self):
        self.scene["nodes"][0]["label"] = " ORDER---begins! "
        self.assertEqual(evaluate_scene(self.scene, self.ref)["exact_semantic"], 1)

    def test_missing_node(self):
        self.scene["nodes"].pop()
        result = evaluate_scene(self.scene, self.ref)
        self.assertEqual(result["node_fn"], 1)
        self.assertEqual(result["edge_fn"], 1)
        self.assertEqual(result["exact_semantic"], 0)

    def test_reversed_edge(self):
        edge = self.scene["edges"][0]
        edge["source"], edge["target"] = edge["target"], edge["source"]
        result = evaluate_scene(self.scene, self.ref)
        self.assertEqual(result["edge_fn"], 1)
        self.assertEqual(result["edge_fp"], 1)

    def test_extra_edge(self):
        self.scene["edges"].append(copy.deepcopy(self.scene["edges"][0]))
        result = evaluate_scene(self.scene, self.ref)
        self.assertEqual(result["edge_recall"], 1)
        self.assertLess(result["edge_precision"], 1)

    def test_wrong_branch(self):
        self.scene["edges"][2]["label"] = "No"
        result = evaluate_scene(self.scene, self.ref)
        self.assertEqual(result["edge_fn"], 1)
        self.assertEqual(result["edge_fp"], 1)

    def test_wrong_type(self):
        self.scene["nodes"][2]["type"] = "process"
        self.assertEqual(evaluate_scene(self.scene, self.ref)["node_fn"], 1)

    def test_empty(self):
        result = evaluate_scene({}, self.ref)
        self.assertEqual(result["node_f1"], 0)
        self.assertEqual(result["edge_f1"], 0)
        self.assertEqual(evaluate_scene({}, {})["exact_semantic"], 1)

    def test_arbitrary_node_ids(self):
        for n in self.scene["nodes"]:
            n["id"] = "new_" + n["id"]
        for e in self.scene["edges"]:
            e["source"] = "new_" + e["source"]
            e["target"] = "new_" + e["target"]
        self.assertEqual(evaluate_scene(self.scene, self.ref)["exact_semantic"], 1)

    def test_dataset_shapes(self):
        tasks, refs = build_dataset()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(sum(t["split"] == "development" for t in tasks), 5)
        for family in ("chain", "branch", "loop"):
            self.assertEqual(sum(t["split"] == "test" and t["family"] == family for t in tasks), 5)
        for task in tasks:
            ref = refs[task["id"]]
            self.assertTrue(6 <= len(ref["nodes"]) <= 10)
            for node in ref["nodes"]:
                self.assertIn('"' + node["label"] + '"', task["prompt"])
            ids = {n["id"] for n in ref["nodes"]}
            for edge in ref["edges"]:
                self.assertIn(edge["source"], ids)
                self.assertIn(edge["target"], ids)


if __name__ == "__main__":
    unittest.main()
