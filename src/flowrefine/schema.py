"""Strict, dependency-free scene contract for editable flowcharts.

Coordinates are canvas pixels; x/y are the top-left of the node bounding box.
Unknown fields are discarded rather than forwarded into SVG markup.
"""
from __future__ import annotations

import math
import re
from typing import Any

NODE_TYPES = frozenset({"start", "end", "process", "decision"})
MAX_NODES = 200
MAX_EDGES = 600
MAX_CANVAS = 4096
MAX_COORD = 32768
_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _text(value: Any, field: str, limit: int, empty: bool = True) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"{field} must be a string of at most {limit} characters")
    if (not empty and not value.strip()) or _ILLEGAL_XML.search(value):
        raise ValueError(f"{field} is empty or contains invalid XML characters")
    return value


def _number(value: Any, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f"{field} must be a finite number") from None
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return result


def normalize_scene(scene: Any) -> dict:
    """Return a safe independent scene; raise ValueError for malformed input.

    Layout defects (e.g. nodes outside the canvas) remain visible to the critic.
    Missing nodes, broken references or nonfinite dimensions are not repaired.
    """
    if not isinstance(scene, dict):
        raise ValueError("scene must be an object")
    canvas = scene.get("canvas")
    if not isinstance(canvas, dict):
        raise ValueError("canvas must be an object with width and height")
    result = {"canvas": {}, "nodes": [], "edges": []}
    for key in ("width", "height"):
        value = canvas.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 64 <= value <= MAX_CANVAS:
            raise ValueError(f"canvas.{key} must be an integer between 64 and {MAX_CANVAS}")
        result["canvas"][key] = value
    nodes, edges = scene.get("nodes"), scene.get("edges")
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise ValueError(f"nodes must be a nonempty list of at most {MAX_NODES} objects")
    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        raise ValueError(f"edges must be a list of at most {MAX_EDGES} objects")
    all_ids: set[str] = set()
    node_ids: set[str] = set()
    for index, item in enumerate(nodes):
        if not isinstance(item, dict):
            raise ValueError(f"nodes[{index}] must be an object")
        node_id = _text(item.get("id"), f"nodes[{index}].id", 128, False)
        if node_id in all_ids:
            raise ValueError(f"duplicate ID: {node_id}")
        all_ids.add(node_id)
        node_ids.add(node_id)
        kind = item.get("type")
        if not isinstance(kind, str) or kind not in NODE_TYPES:
            raise ValueError(f"node {node_id}: type must be one of {sorted(NODE_TYPES)}")
        node = {"id": node_id, "type": kind,
                "label": _text(item.get("label"), f"node {node_id}.label", 2000)}
        for key in ("x", "y", "width", "height"):
            node[key] = _number(item.get(key), f"node {node_id}.{key}",
                                -MAX_COORD if key in {"x", "y"} else 1,
                                MAX_COORD if key in {"x", "y"} else 8192)
        result["nodes"].append(node)
    for index, item in enumerate(edges):
        if not isinstance(item, dict):
            raise ValueError(f"edges[{index}] must be an object")
        edge_id = _text(item.get("id"), f"edges[{index}].id", 128, False)
        if edge_id in all_ids:
            raise ValueError(f"duplicate ID: {edge_id}")
        all_ids.add(edge_id)
        edge = {"id": edge_id}
        for key in ("source", "target"):
            value = _text(item.get(key), f"edge {edge_id}.{key}", 128, False)
            if value not in node_ids:
                raise ValueError(f"edge {edge_id}: unknown {key} {value}")
            edge[key] = value
        edge["label"] = _text(item.get("label", ""), f"edge {edge_id}.label", 1000)
        if "points" in item:
            points = item["points"]
            if not isinstance(points, list) or not 2 <= len(points) <= 128:
                raise ValueError(f"edge {edge_id}.points must contain 2 to 128 coordinate pairs")
            normalized_points = []
            for point in points:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise ValueError(f"edge {edge_id}: malformed point")
                normalized_points.append([_number(v, f"edge {edge_id}.point", -MAX_COORD, MAX_COORD) for v in point])
            if not any(a != b for a, b in zip(normalized_points, normalized_points[1:])):
                raise ValueError(f"edge {edge_id}: polyline has zero length")
            edge["points"] = normalized_points
        result["edges"].append(edge)
    if sum(len(n["label"]) for n in result["nodes"]) + sum(len(e["label"]) for e in result["edges"]) > 100000:
        raise ValueError("total label text exceeds 100000 characters")
    return result
