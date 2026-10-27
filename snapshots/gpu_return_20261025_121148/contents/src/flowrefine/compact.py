"""Public compact model format <-> drawing format; never has reference access."""

import json
import math

from .schema import normalize_scene


def parse_object(text):
    """Extract first decodable JSON object (including responses wrapped in fences)."""
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "nodes" in obj and "edges" in obj:
            return obj
    raise ValueError("Model response has no JSON object with nodes and edges")


def to_scene(obj):
    if not isinstance(obj, dict):
        raise ValueError("Scene must be an object")
    if "canvas" in obj:
        return normalize_scene(obj)
    if not isinstance(obj.get("nodes"), list) or not isinstance(obj.get("edges"), list):
        raise ValueError("Compact nodes and edges must be lists")
    if len(obj["nodes"]) > 30 or len(obj["edges"]) > 60:
        raise ValueError("Compact scene exceeds node/edge limits")
    nodes, edges = [], []
    for row in obj["nodes"]:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("Each compact node must have 4 entries: exact stage label, type, column, row")
        label, kind, col, gridrow = row
        node_id = label
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in (col, gridrow)):
            raise ValueError("Grid positions must be finite numbers")
        if abs(col) > 10 or abs(gridrow) > 20:
            raise ValueError("Grid coordinate magnitude exceeds technical limits")
        height = 140 if kind == "decision" else 72
        nodes.append(dict(id=node_id, type=kind, label=label,
                          x=25 + 255 * col, y=30 + 170 * gridrow,
                          width=220, height=height))
    for i, edge in enumerate(obj["edges"]):
        if not isinstance(edge, list) or len(edge) not in (2, 3):
            raise ValueError("Each compact edge must have source, target and optional label")
        edges.append(dict(id=f"e{i+1}", source=edge[0], target=edge[1],
                          label=edge[2] if len(edge) == 3 else ""))
    return normalize_scene(dict(canvas=dict(width=790, height=1440), nodes=nodes, edges=edges))


def from_scene(scene):
    return {"nodes": [[n["label"], n["type"],
                       round((n["x"]-25)/255, 2), round((n["y"]-30)/170, 2)]
                      for n in scene["nodes"]],
            "edges": [[next(n["label"] for n in scene["nodes"] if n["id"]==e["source"]),
                       next(n["label"] for n in scene["nodes"] if n["id"]==e["target"]), e.get("label", "")]
                      for e in scene["edges"]]}
