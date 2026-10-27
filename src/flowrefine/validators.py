"""Deterministic, reference-free structural and layout criticism.

These checks never inspect the desired/ground-truth graph and make no claim
about semantic correctness. Cycles, disconnected nodes and multiple starts are
allowed: those can be legitimate user requirements.
"""
from __future__ import annotations

from itertools import combinations

from .rendering import edge_label_position, edge_polyline, node_text_layout, text_width, wrap_text, EDGE_FONT_SIZE
from .schema import normalize_scene


def _issue(code: str, ids: list[str], message: str, severity: str = "warning") -> dict:
    return {"code": code, "severity": severity, "affected_ids": ids, "message": message}


def _segment_hits_node(a: tuple, b: tuple, node: dict) -> bool:
    """Clip a segment against a slightly inset rectangle or exact diamond.

    Rectangle tests conservatively include rounded corners. Touching boundaries
    alone is not counted as crossing a block.
    """
    x, y, w, h = (node[k] for k in ("x", "y", "width", "height"))
    eps = 0.5
    if node["type"] == "decision":
        cx, cy = x + w / 2, y + h / 2
        # Interior of diamond: +/- (x-cx)/(w/2) +/- (y-cy)/(h/2) < 1.
        constraints = [(sx / (w / 2), sy / (h / 2),
                        1 - eps / max(1, min(w, h)) + sx * cx / (w / 2) + sy * cy / (h / 2))
                       for sx in (-1, 1) for sy in (-1, 1)]
    else:
        if w <= eps * 2 or h <= eps * 2:
            return False
        constraints = [(1, 0, x + w - eps), (-1, 0, -x - eps),
                       (0, 1, y + h - eps), (0, -1, -y - eps)]
    lower, upper = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for nx, ny, limit in constraints:
        origin, direction = nx * a[0] + ny * a[1], nx * dx + ny * dy
        if abs(direction) < 1e-12:
            if origin > limit:
                return False
        elif direction > 0:
            upper = min(upper, (limit - origin) / direction)
        else:
            lower = max(lower, (limit - origin) / direction)
        if lower > upper:
            return False
    return upper - lower > 1e-8


def _on_boundary(point: tuple, node: dict, tolerance: float = 3.0) -> bool:
    x, y, w, h = (node[k] for k in ("x", "y", "width", "height"))
    px, py = point
    if node["type"] == "decision":
        distance = abs(px - (x + w / 2)) / (w / 2) + abs(py - (y + h / 2)) / (h / 2)
        return abs(distance - 1) <= tolerance / max(1, min(w, h) / 2)
    # Rounded rectangles use the exact circular corner when near a corner.
    radius = min(w, h) / 2 if node["type"] in {"start", "end"} else min(8, w / 2, h / 2)
    if not x - tolerance <= px <= x + w + tolerance or not y - tolerance <= py <= y + h + tolerance:
        return False
    cx = min(max(px, x + radius), x + w - radius)
    cy = min(max(py, y + radius), y + h - radius)
    if px < x + radius or px > x + w - radius:
        if py < y + radius or py > y + h - radius:
            return abs(((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 - radius) <= tolerance
    return min(abs(px - x), abs(px - x - w), abs(py - y), abs(py - y - h)) <= tolerance


def check_scene(scene: dict) -> list[dict]:
    """Return reproducible issues; malformed structure becomes invalid_scene."""
    try:
        scene = normalize_scene(scene)
    except ValueError as exc:
        return [_issue("invalid_scene", [], str(exc), "error")]
    issues = []
    width, height = scene["canvas"]["width"], scene["canvas"]["height"]
    node_by_id = {n["id"]: n for n in scene["nodes"]}
    for node in scene["nodes"]:
        x, y, w, h = (node[k] for k in ("x", "y", "width", "height"))
        if x < 0 or y < 0 or x + w > width or y + h > height:
            issues.append(_issue("out_of_bounds", [node["id"]],
                                 f"Node {node['id']} is outside the {width}x{height} canvas.", "error"))
        if node_text_layout(node)["overflow"]:
            issues.append(_issue("text_overflow", [node["id"]],
                                 f"Label of node {node['id']} does not fit its available text area.", "error"))
    for a, b in combinations(scene["nodes"], 2):
        overlap_w = min(a["x"] + a["width"], b["x"] + b["width"]) - max(a["x"], b["x"])
        overlap_h = min(a["y"] + a["height"], b["y"] + b["height"]) - max(a["y"], b["y"])
        if overlap_w > 0.5 and overlap_h > 0.5:
            issues.append(_issue("node_overlap", [a["id"], b["id"]],
                                 f"Bounding boxes of {a['id']} and {b['id']} overlap by {overlap_w:.1f}x{overlap_h:.1f}px.", "error"))
    for index, edge in enumerate(scene["edges"]):
        points = edge_polyline(scene, edge, index)
        if any(x < 0 or y < 0 or x > width or y > height for x, y in points):
            issues.append(_issue("edge_out_of_bounds", [edge["id"]], f"Route of edge {edge['id']} leaves the canvas.", "error"))
        for endpoint, key in ((points[0], "source"), (points[-1], "target")):
            if not _on_boundary(endpoint, node_by_id[edge[key]]):
                issues.append(_issue("edge_detached", [edge["id"], edge[key]],
                                     f"Edge {edge['id']} does not meet the boundary of its {key} {edge[key]}.", "error"))
        for node in scene["nodes"]:
            if node["id"] in {edge["source"], edge["target"]}:
                continue
            if any(_segment_hits_node(a, b, node) for a, b in zip(points, points[1:])):
                issues.append(_issue("edge_through_node", [edge["id"], node["id"]],
                                     f"Edge {edge['id']} crosses unrelated node {node['id']}.", "error"))
        if edge["label"]:
            cx, cy = edge_label_position(points)
            lines = wrap_text(edge["label"], 180, EDGE_FONT_SIZE)
            tw, th = max(text_width(line, EDGE_FONT_SIZE) for line in lines) + 8, len(lines) * 16 + 4
            if cx - tw / 2 < 0 or cy - th / 2 < 0 or cx + tw / 2 > width or cy + th / 2 > height:
                issues.append(_issue("edge_label_out_of_bounds", [edge["id"]], f"Label of edge {edge['id']} leaves the canvas."))
            for node in scene["nodes"]:
                if min(cx + tw / 2, node["x"] + node["width"]) > max(cx - tw / 2, node["x"]) and min(cy + th / 2, node["y"] + node["height"]) > max(cy - th / 2, node["y"]):
                    issues.append(_issue("edge_label_overlap", [edge["id"], node["id"]], f"Label of edge {edge['id']} overlaps node {node['id']} description."))
    return issues
