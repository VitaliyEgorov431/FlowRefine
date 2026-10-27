"""Deterministic semantic scoring, independent of the generation/repair loop.

Labels match after Unicode normalization, casefolding and punctuation removal.
There is deliberately no fuzzy matching or model judge. Matched nodes must also
have the same type. Edge direction and normalized branch label must match.
One-to-one matching prevents duplicated nodes/edges from earning extra credit.
"""
from collections import Counter
import unicodedata


def normalize_label(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join("".join(c if c.isalnum() else " " for c in value).split())


def _scores(tp, predicted, expected):
    # Two empty sets match perfectly; an empty prediction against a nonempty
    # reference has zero precision and recall for transparent aggregation.
    precision = tp / predicted if predicted else float(expected == 0)
    recall = tp / expected if expected else float(predicted == 0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def evaluate_scene(scene, reference):
    """Score JSON-like scenes; ignore geometry. Malformed entries get no credit.

    All supplied entries count as predictions, including dangling edges and
    duplicated IDs. Ambiguous repeated IDs cannot be used to match edges.
    Empty scene/reference dictionaries are supported.
    """
    scene = scene if isinstance(scene, dict) else {}
    reference = reference if isinstance(reference, dict) else {}
    nodes = scene.get("nodes", [])
    edges = scene.get("edges", [])
    refs = reference.get("nodes", [])
    ref_edges = reference.get("edges", [])
    nodes = nodes if isinstance(nodes, list) else []
    edges = edges if isinstance(edges, list) else []
    refs = refs if isinstance(refs, list) else []
    ref_edges = ref_edges if isinstance(ref_edges, list) else []
    available = {}
    for i, node in enumerate(refs):
        key = (normalize_label(node.get("label")), node.get("type"))
        available.setdefault(key, []).append(i)
    mapping = {}
    node_tp = 0
    id_counts = Counter(n.get("id") for n in nodes if isinstance(n, dict))
    for node in nodes:
        if not isinstance(node, dict):
            continue
        key = (normalize_label(node.get("label")), node.get("type"))
        candidates = available.get(key, [])
        if candidates and key[0]:
            index = candidates.pop(0)
            node_tp += 1
            if id_counts[node.get("id")] == 1:
                mapping[node.get("id")] = refs[index].get("id")
    expected_edges = Counter(
        (e.get("source"), e.get("target"), normalize_label(e.get("label")))
        for e in ref_edges
    )
    edge_tp = 0
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("source") not in mapping or edge.get("target") not in mapping:
            continue
        key = (mapping[edge.get("source")], mapping[edge.get("target")],
               normalize_label(edge.get("label")))
        if expected_edges[key] > 0:
            edge_tp += 1
            expected_edges[key] -= 1
    result = {}
    for prefix, tp, predicted, expected in (
        ("node", node_tp, len(nodes), len(refs)),
        ("edge", edge_tp, len(edges), len(ref_edges)),
    ):
        p, r, f = _scores(tp, predicted, expected)
        result.update({f"{prefix}_precision": p, f"{prefix}_recall": r,
                       f"{prefix}_f1": f, f"{prefix}_tp": tp,
                       f"{prefix}_fp": predicted - tp,
                       f"{prefix}_fn": expected - tp,
                       f"{prefix}_predicted": predicted,
                       f"{prefix}_expected": expected})
    result["exact_semantic"] = int(
        node_tp == len(nodes) == len(refs) and edge_tp == len(edges) == len(ref_edges)
    )
    return result
