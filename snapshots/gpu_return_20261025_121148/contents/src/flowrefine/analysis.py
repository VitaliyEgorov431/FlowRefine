"""Reference-isolated analysis of saved experiments; never calls a model."""
import csv
import json
import random
import statistics
from pathlib import Path

from .evaluation import evaluate_scene
from .validators import check_scene

ARMS = ("B0", "B1", "B2", "B3")


def _read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _mean(values):
    return statistics.mean(values) if values else None


def _bootstrap(values):
    if not values:
        return {"n": 0, "mean": None, "ci95": None}
    rng = random.Random(20261024)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(1000))
    return {"n": len(values), "mean": statistics.mean(values), "ci95": [samples[24], samples[974]]}


def analyze_run(run_dir, reference_path, output_dir):
    """Write metrics, raw call audit, honest aggregate and three static figures.

    Unexecuted arms remain blank in metrics.csv. Executed invalid arms have zero
    semantic scores and an invalid_scene issue, but no invented geometry count.
    Standalone costs include shared dependencies; actual totals count log files
    once. Estimated CPU checking/rendering time is not included in model latency.
    """
    run_dir, output = Path(run_dir), Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    tasks = _read(run_dir / "tasks_public.json", [])
    refs = _read(reference_path, {})
    manifest = _read(run_dir / "manifest.json", {})
    calls = []
    for path in sorted(run_dir.glob("*/**/call_*.json")):
        record = _read(path, {})
        response = record.get("response", {})
        usage = response.get("usage") or {}
        rel = path.relative_to(run_dir)
        calls.append({"task_id": rel.parts[0], "component": rel.parts[1],
                      "file": rel.as_posix(), "role": record.get("role", ""),
                      "backend": response.get("backend", ""), "model": response.get("model", ""),
                      "elapsed_seconds": float(response.get("elapsed_seconds") or 0),
                      "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                      "completion_tokens": int(usage.get("completion_tokens") or 0),
                      "cached": bool(response.get("cached", record.get("cached", False))),
                      "reference_access": record.get("reference_access", "unknown")})
    rows = []
    for task in tasks:
        task_id = task["id"]
        if task_id not in refs:
            raise ValueError("Missing evaluation reference: " + task_id)
        for arm in ARMS:
            folder = run_dir / task_id / arm
            status = _read(folder / "status.json", {})
            executed = "valid" in status
            scene = _read(folder / "scene.json", None)
            valid = bool(status.get("valid")) and scene is not None if executed else None
            feedback = check_scene(scene) if valid else []
            if any(i["code"] == "invalid_scene" for i in feedback):
                valid = False
            deps = {"B0"}
            if arm != "B0":
                deps.add(arm)
            if arm in ("B2", "B3"):
                deps.add("visual")
            selected = [c for c in calls if c["task_id"] == task_id and c["component"] in deps]
            row = {"task_id": task_id, "split": task.get("split", ""),
                   "family": task.get("family", ""), "arm": arm,
                   "executed": executed, "valid": valid,
                   "reason": status.get("reason", "" if executed else "unexecuted"),
                   "invalid_scene_count": int(not valid) if executed else None,
                   "geometry_errors": sum(i["severity"] == "error" and i["code"] != "invalid_scene" for i in feedback) if valid else None,
                   "geometry_warnings": sum(i["severity"] == "warning" for i in feedback) if valid else None,
                   "render_available": (folder / "chart.png").exists() if executed else None,
                   "render_error": status.get("render_error", "") if executed else "",
                   "standalone_calls": len(selected) if executed else None,
                   "standalone_cached_calls": sum(c["cached"] for c in selected) if executed else None,
                   "standalone_inference_seconds": sum(c["elapsed_seconds"] for c in selected) if executed else None,
                   "standalone_prompt_tokens": sum(c["prompt_tokens"] for c in selected) if executed else None,
                   "standalone_completion_tokens": sum(c["completion_tokens"] for c in selected) if executed else None}
            semantic = evaluate_scene(scene if valid else {}, refs[task_id])
            if executed and not valid:
                # A parsing failure is a failed execution, even when a
                # reference happens to have no edges (empty-set F1 is 1).
                for key in semantic:
                    if key.endswith(("_precision", "_recall", "_f1")) or key == "exact_semantic":
                        semantic[key] = 0
            row.update({key: value if executed else None for key, value in semantic.items()})
            rows.append(row)
    by_arm = {}
    for arm in ARMS:
        group = [r for r in rows if r["arm"] == arm and r["executed"]]
        valid = [r for r in group if r["valid"]]
        by_arm[arm] = {"task_count": len(tasks), "executed": len(group),
                       "unexecuted": len(tasks) - len(group), "valid": len(valid),
                       "invalid": len(group) - len(valid),
                       "exact_semantic_mean": _mean([r["exact_semantic"] for r in group]),
                       "node_f1_mean": _mean([r["node_f1"] for r in group]),
                       "edge_f1_mean": _mean([r["edge_f1"] for r in group]),
                       "geometry_errors_valid_mean": _mean([r["geometry_errors"] for r in valid]),
                       "geometry_warnings_valid_mean": _mean([r["geometry_warnings"] for r in valid]),
                       "standalone_inference_seconds_mean": _mean([r["standalone_inference_seconds"] for r in group])}
    by_task = {(r["task_id"], r["arm"]): r for r in rows}
    paired = {}
    for arm in ARMS[1:]:
        comparable = [(by_task[(t["id"], "B0")], by_task[(t["id"], arm)]) for t in tasks
                      if by_task[(t["id"], "B0")]["executed"] and by_task[(t["id"], arm)]["executed"]]
        paired[arm + "_minus_B0"] = {}
        for metric in ("node_f1", "edge_f1", "exact_semantic"):
            paired[arm + "_minus_B0"][metric] = _bootstrap([b[metric] - a[metric] for a, b in comparable])
        valid_pairs = [(a, b) for a, b in comparable if a["valid"] and b["valid"]]
        paired[arm + "_minus_B0"]["geometry_errors_valid_pairs"] = _bootstrap([b["geometry_errors"] - a["geometry_errors"] for a, b in valid_pairs])
    aggregate = {"provenance": manifest.get("provenance", "unspecified"),
                 "task_count": len(tasks), "arms": by_arm, "paired_differences": paired,
                 "actual_logged_calls": len(calls), "actual_cached_calls": sum(c["cached"] for c in calls),
                 "actual_logged_inference_seconds": sum(c["elapsed_seconds"] for c in calls),
                 "actual_logged_prompt_tokens": sum(c["prompt_tokens"] for c in calls),
                 "actual_logged_completion_tokens": sum(c["completion_tokens"] for c in calls),
                 "reference_access_violations": [c["file"] for c in calls if c["reference_access"] is not False],
                 "notes": ["Pilot on a small template-based dataset; no population-level claim.",
                           "Unexecuted arms are excluded, never assigned zero quality.",
                           "Executed invalid scenes score zero semantics; geometry is undefined.",
                           "Standalone arm costs reuse shared initial generation and visual critique costs; actual total counts each saved call once.",
                           "Intervals use 1000 task-level bootstrap resamples with a fixed seed; not corrected for multiple comparisons.",
                           "Model latency excludes local CPU validation and rendering."]}
    _csv(output / "metrics.csv", rows)
    _csv(output / "raw_calls.csv", calls)
    (output / "aggregate.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    text = ["# Pilot experiment summary", "", f"Tasks: {len(tasks)}. Provenance: {aggregate['provenance']}.", "",
            "| Arm | Executed / tasks | Valid | Exact semantics | Edge F1 | Geometry errors (valid only) |", "|---|---:|---:|---:|---:|---:|"]
    def fmt(value):
        return "unavailable" if value is None else f"{value:.3f}"
    for arm, s in by_arm.items():
        text.append(f"| {arm} | {s['executed']} / {len(tasks)} | {s['valid']} | {fmt(s['exact_semantic_mean'])} | {fmt(s['edge_f1_mean'])} | {fmt(s['geometry_errors_valid_mean'])} |")
    text += ["", f"Actual saved calls: {len(calls)}; cached: {aggregate['actual_cached_calls']}; logged model time: {aggregate['actual_logged_inference_seconds']:.1f} seconds.", ""] + aggregate["notes"]
    (output / "SUMMARY.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    _plots(output, by_arm, len(tasks))
    return aggregate


def _plots(output, arms, task_count):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    available = [a for a in ARMS if arms[a]["executed"]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for offset, metric, label in ((-.22, "node_f1_mean", "Node F1"), (0, "edge_f1_mean", "Edge F1"), (.22, "exact_semantic_mean", "Exact semantics")):
        ax.bar([i + offset for i in range(len(available))], [arms[a][metric] for a in available], width=.22, label=label)
    ax.set_xticks(range(len(available)), [f"{a}\nn={arms[a]['executed']}" for a in available])
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Mean score (invalid executions included as zero)")
    ax.set_title("Semantic quality on executed tasks")
    if available:
        ax.legend(loc="upper right")
    else:
        ax.text(.5, .5, "No executed model outputs", transform=ax.transAxes, ha="center")
    fig.tight_layout(); fig.savefig(output / "semantic_quality.png", dpi=180); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    valid_arms = [a for a in ARMS if arms[a]["valid"]]
    axes[0].bar(valid_arms, [arms[a]["geometry_errors_valid_mean"] for a in valid_arms])
    axes[0].set_title("Geometry errors: valid scenes only")
    axes[0].set_ylabel("Mean error count; invalid scenes undefined")
    axes[1].bar(ARMS, [arms[a]["valid"] for a in ARMS], label="Valid")
    axes[1].bar(ARMS, [arms[a]["invalid"] for a in ARMS], bottom=[arms[a]["valid"] for a in ARMS], label="Invalid")
    axes[1].bar(ARMS, [arms[a]["unexecuted"] for a in ARMS], bottom=[arms[a]["executed"] for a in ARMS], label="Unexecuted", color="lightgray")
    axes[1].set_ylim(0, max(1, task_count)); axes[1].set_title("Coverage by arm"); axes[1].set_ylabel("Tasks"); axes[1].legend()
    fig.tight_layout(); fig.savefig(output / "geometry_coverage.png", dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for arm in available:
        x, y = arms[arm]["standalone_inference_seconds_mean"], arms[arm]["edge_f1_mean"]
        ax.scatter(x, y, s=70); ax.annotate(arm, (x, y), xytext=(5, 5), textcoords="offset points")
    ax.set_xlabel("Mean standalone model time per task (seconds)")
    ax.set_ylabel("Mean edge F1 (executed tasks)"); ax.set_ylim(-.03, 1.1)
    ax.set_title("Quality versus inference time; shared costs included")
    fig.tight_layout(); fig.savefig(output / "quality_cost.png", dpi=180); plt.close(fig)
