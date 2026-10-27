"""Meaningful boundary regressions for the renderer and geometry critic."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from flowrefine.rendering import edge_polyline, render_scene
from flowrefine.schema import normalize_scene
from flowrefine.validators import check_scene


def good_scene():
    return {"canvas": {"width": 600, "height": 500}, "nodes": [
        {"id": "start", "type": "start", "label": "Start", "x": 200, "y": 30, "width": 180, "height": 56},
        {"id": "work", "type": "process", "label": "Check documents", "x": 200, "y": 170, "width": 180, "height": 76},
        {"id": "end", "type": "end", "label": "Finish", "x": 200, "y": 350, "width": 180, "height": 56},
    ], "edges": [{"id": "e1", "source": "start", "target": "work"},
                 {"id": "e2", "source": "work", "target": "end"}]}


class SchemaTests(unittest.TestCase):
    def test_normalization_is_safe_copy(self):
        source = good_scene()
        source["script"] = "untrusted"
        result = normalize_scene(source)
        self.assertNotIn("script", result)
        result["nodes"][0]["x"] = 0
        self.assertEqual(source["nodes"][0]["x"], 200)

    def test_rejects_dangerous_or_invalid_geometry(self):
        for bad in (float("nan"), float("inf"), True, "100", 10 ** 1000):
            with self.subTest(bad=repr(bad)[:30]):
                scene = good_scene()
                scene["nodes"][0]["x"] = bad
                with self.assertRaises(ValueError):
                    normalize_scene(scene)
        for field, bad in (("width", 0), ("height", -1), ("type", "script"), ("label", "bad\x00label")):
            scene = good_scene()
            scene["nodes"][0][field] = bad
            with self.assertRaises(ValueError):
                normalize_scene(scene)

    def test_rejects_broken_graphs(self):
        scene = good_scene()
        scene["edges"][0]["target"] = "missing"
        with self.assertRaises(ValueError):
            normalize_scene(scene)
        self.assertEqual(check_scene(scene)[0]["code"], "invalid_scene")
        scene = good_scene()
        scene["nodes"][1]["id"] = "start"
        with self.assertRaises(ValueError):
            normalize_scene(scene)
        scene = good_scene()
        scene["edges"][0]["points"] = [[1, 1], [1, 1]]
        with self.assertRaises(ValueError):
            normalize_scene(scene)


class CriticTests(unittest.TestCase):
    def test_known_good_has_no_issues(self):
        self.assertEqual(check_scene(good_scene()), [])

    def test_detects_overlap_bounds_text_and_crossing(self):
        scene = good_scene()
        scene["nodes"][1]["x"] = -10
        scene["nodes"][1]["height"] = 10
        scene["nodes"].append({"id": "obstacle", "type": "process", "label": "Obstacle", "x": 270, "y": 110, "width": 120, "height": 60})
        scene["edges"][0]["points"] = [[290, 86], [290, 170], [80, 170]]
        scene["nodes"].append({"id": "overlap", "type": "process", "label": "Other", "x": 280, "y": 130, "width": 120, "height": 60})
        codes = {i["code"] for i in check_scene(scene)}
        self.assertTrue({"out_of_bounds", "node_overlap", "text_overflow", "edge_through_node"} <= codes)

    def test_cycles_and_reverse_edges_are_supported(self):
        scene = normalize_scene(good_scene())
        reverse = {"id": "back", "source": "end", "target": "work", "label": "Retry"}
        loop = {"id": "loop", "source": "work", "target": "work", "label": "Again"}
        scene["edges"] += [reverse, loop]
        for edge in (reverse, loop):
            points = edge_polyline(scene, edge)
            self.assertGreaterEqual(len(points), 3)
            self.assertNotEqual(points[0], points[-1])
        codes = {i["code"] for i in check_scene(scene)}
        self.assertNotIn("invalid_scene", codes)
        self.assertNotIn("edge_detached", codes)

    def test_full_explicit_polyline_and_detachment(self):
        scene = good_scene()
        points = [[0, 0], [10, 0], [10, 20]]
        scene["edges"][0]["points"] = points
        self.assertEqual(edge_polyline(scene, scene["edges"][0]), [tuple(p) for p in points])
        self.assertIn("edge_detached", {i["code"] for i in check_scene(scene)})


class RenderTests(unittest.TestCase):
    def test_renders_png_svg_with_escaped_labels_and_no_active_markup(self):
        scene = good_scene()
        label = '<script>alert("x")</script> & Проверка'
        scene["nodes"][1]["label"] = label
        scene["nodes"][1]["height"] = 140
        scene["edges"][0]["label"] = '<img onerror="x">'
        with tempfile.TemporaryDirectory() as directory:
            paths = render_scene(scene, Path(directory) / "example")
            root = ET.parse(paths["svg"]).getroot()
            texts = " ".join(e.text or "" for e in root.iter() if e.tag.endswith("text"))
            self.assertIn("Проверка", texts)
            self.assertFalse(any(e.tag.endswith("script") or e.tag.endswith("image") for e in root.iter()))
            svg = Path(paths["svg"]).read_text(encoding="utf-8")
            self.assertIn("&lt;", svg)
            with Image.open(paths["png"]) as image:
                self.assertEqual(image.size, (600, 500))
                self.assertIsNotNone(image.getbbox())

    def test_reverse_and_self_loop_render(self):
        scene = good_scene()
        scene["edges"] += [{"id": "back", "source": "end", "target": "work", "label": "Retry"},
                           {"id": "loop", "source": "work", "target": "work", "label": "Again"}]
        with tempfile.TemporaryDirectory() as directory:
            paths = render_scene(scene, Path(directory) / "loops")
            root = ET.parse(paths["svg"]).getroot()
            self.assertEqual(sum(e.tag.endswith("polyline") for e in root.iter()), 4)
            self.assertTrue(Path(paths["png"]).is_file())

    def test_touching_nodes_do_not_produce_zero_length_edge(self):
        scene = good_scene()
        scene["nodes"][1].update(x=380, y=20, height=76)
        scene["edges"][0]["label"] = "Adjacent"
        points = edge_polyline(scene, scene["edges"][0])
        self.assertGreaterEqual(len(points), 2)
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(Path(render_scene(scene, Path(directory) / "touching")["png"]).exists())


if __name__ == "__main__":
    unittest.main()
