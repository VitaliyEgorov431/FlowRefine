"""Build the exploratory follow-up supplement from saved analysis (no inference)."""
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build():
    analysis = ROOT / "analysis/followup_v1"
    aggregate = load(analysis / "aggregate.json")
    out = ROOT / "submission/followup_v1"
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((analysis / "metrics.csv").open(encoding="utf-8", newline="")))
    arms = ["B0", "B1", "B2", "B3", "C0", "L3"]
    if any(sum(r["arm"] == a and r["executed"] == "True" for r in rows) != 15 for a in arms):
        raise ValueError("All six arms need 15 saved executed results; partial runs are not final evidence")
    if any(not any(r["arm"] == a and r["valid"] == "True" for r in rows) for a in arms):
        raise ValueError("An arm has no valid geometry observations; revise presentation logic to show geometry unavailable")
    baseline = {r["task_id"]: r for r in rows if r["arm"] == "B0"}
    stats = {}
    for arm in arms:
        rr = [r for r in rows if r["arm"] == arm]
        differences = [float(r["edge_f1"]) - float(baseline[r["task_id"]]["edge_f1"]) for r in rr]
        stats[arm] = dict(exact=sum(float(r["exact_semantic"]) == 1 for r in rr),
            node_f1=sum(float(r["node_f1"]) for r in rr) / 15,
            f1=sum(float(r["edge_f1"]) for r in rr) / 15,
            geometry=sum(float(r["geometry_errors"]) for r in rr if r["valid"] == "True") / max(1, sum(r["valid"] == "True" for r in rr)),
            valid=sum(r["valid"] == "True" for r in rr),
            improved=sum(d > 1e-9 for d in differences), worsened=sum(d < -1e-9 for d in differences), unchanged=sum(abs(d) <= 1e-9 for d in differences),
            geometry_better=sum(float(r["geometry_errors"]) < float(baseline[r["task_id"]]["geometry_errors"]) for r in rr if r["valid"] == "True"),
            geometry_worse=sum(float(r["geometry_errors"]) > float(baseline[r["task_id"]]["geometry_errors"]) for r in rr if r["valid"] == "True"),
            fixed=sum(float(baseline[r["task_id"]]["exact_semantic"]) == 0 and float(r["exact_semantic"]) == 1 for r in rr),
            broken=sum(float(baseline[r["task_id"]]["exact_semantic"]) == 1 and float(r["exact_semantic"]) == 0 for r in rr))
    lines, story = [], []
    body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.2, leading=14, spaceAfter=8, textColor=colors.HexColor("#17202A"))
    title = ParagraphStyle("Title", parent=body, fontName="Helvetica-Bold", fontSize=24, leading=29, spaceAfter=14, textColor=colors.HexColor("#1F4E79"))
    heading = ParagraphStyle("Heading", parent=body, fontName="Helvetica-Bold", fontSize=14, leading=18, spaceBefore=9, spaceAfter=9, keepWithNext=True)
    small = ParagraphStyle("Small", parent=body, fontSize=8.4, leading=11)

    def p(t, style=body):
        story.append(Paragraph(escape(t), style)); lines.append(t + "\n")
    def h(t):
        p(t, heading); lines[-1] = "## " + t + "\n"
    def table(data, widths):
        t = Table([[Paragraph(escape(str(c)), small) for c in r] for r in data], colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF1F5")), ("LINEBELOW", (0, 0), (-1, 0), .6, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
        story.extend([t, Spacer(1, 9)])
        lines.extend(["| " + " | ".join(map(str, r)) + " |" for r in data[:1]])
        lines.append("| " + " | ".join("---" for _ in data[0]) + " |")
        lines.extend(["| " + " | ".join(map(str, r)) + " |" for r in data[1:]]); lines.append("")
    def page():
        story.append(PageBreak()); lines.append("\n---\n")
    p("FlowRefine: exploratory follow-up", title)
    lines[-1] = "# FlowRefine: exploratory follow-up\n"
    p("Supplement to the frozen test_v1 report | 24 October 2026", small)
    h("Purpose and status")
    p("The original frozen four-arm CPU pilot tested one correction round with programmatic, visual and combined feedback. The present supplement was designed after those outcomes were inspected. It adds a no-feedback edit control (C0) and a combined-feedback layout-only editor (L3). These are exploratory post-test comparisons, not a new held-out confirmatory test.")
    p("All 15 saved B0 diagrams, the original public descriptions, and the saved programmatic and visual feedback were reused. The original generator and visual critic were not rerun. The baseline protocol, raw results, original report, original presentation and archive remain preserved. C0 and failed initial L3 outputs live in runs/followup_v1; revised final L3 lives in runs/layout_v2. Analysis lives in analysis/followup_v1.")
    h("Research questions")
    p("C0 asks whether rewriting the same diagram without external criticism can itself change correctness. L3 asks whether model-proposed coordinates can improve the measured layout while programmatically preserving the baseline graph. L3 cannot repair a wrong baseline edge, and preserved semantics alone does not establish better layout or validate the critic.")
    h("Methods")
    table([["Arm", "Editor input and allowed changes"], ["B0", "Original generated graph and layout"], ["B1 / B2 / B3", "Frozen original edits: programmatic / visual / both; whole graph editable"], ["C0", "Original public request and B0; edit without external feedback"], ["L3", "B0, original request and saved combined feedback; coordinates only, topology enforced in code"]], [68, 430])
    p("The same local Qwen2.5-3B Q4_K_M CPU model and saved settings are used for follow-up editing. New inference logs, prompt content and hashes are saved separately. C0's final instruction asks to use the original requested process; B1-B3 ask to use feedback. It is a feedback-free editing control, not a perfectly isolated single-variable causal ablation. L3 uses a constrained coordinate schema and shorter output; any cost difference cannot be attributed solely to feedback quality. Exact matching follows the original evaluator. Geometry counts are diagnostic proxies; no human readability study is claimed.")
    h("Failed coordinate-format attempt and revision")
    failed = aggregate.get("failed_layout_attempts", {})
    p(f"The first L3 coordinate format failed: {failed.get('invalid', 8)} completed invalid scenes, {failed.get('logged_calls', 16)} saved model calls including retries. The next in-flight response was interrupted before persistence; its elapsed time and tokens are unknown. Failed outputs are retained rather than replaced. The schema was revised and checked on development tasks before the separate layout_v2 run. The final L3 column describes this revised post-test method, not successful outputs from the first attempt.")
    page()
    h("Complete six-arm descriptive comparison")
    table([["Arm", "Valid / 15", "Exact / 15", "Node F1", "Edge F1", "Geometry errors"], *[[a, stats[a]["valid"], stats[a]["exact"], f'{stats[a]["node_f1"]:.3f}', f'{stats[a]["f1"]:.3f}', f'{stats[a]["geometry"]:.3f}'] for a in arms]], [45, 70, 70, 70, 75, 168])
    p("B0-B3 belong to the frozen original test. C0 and L3 were added after inspecting that test. Geometry is averaged over valid scenes; invalid executed scenes have zero semantic scores and undefined geometry. All changes below are paired to the same task's B0, rather than comparing unpaired averages.", small)
    h("Corrections and regressions relative to B0")
    table([["Arm", "F1 up", "F1 down", "F1 same", "Exact fixed", "Exact broken"], *[[a, *[stats[a][k] for k in ["improved", "worsened", "unchanged", "fixed", "broken"]]] for a in arms[1:]]], [48, 65, 72, 76, 112, 125])
    p("Exact fixed means B0 was not exactly correct and the edited graph is exactly correct. Exact broken means an exactly correct B0 became incorrect. Partial F1 improvement is different from fully fixing a graph. L3's semantic preservation is an enforced implementation invariant and cannot be interpreted as semantic reasoning by the model.")
    h("Interpretation")
    p(f"C0 yields {stats['C0']['exact']}/15 exact graphs, with {stats['C0']['fixed']} exact fixes and {stats['C0']['broken']} exact regressions. Edge F1 is unchanged in {stats['C0']['unchanged']}/15 tasks. B3 yields {stats['B3']['exact']}/15. This control makes the effect of editing without feedback visible in the same saved tasks. A single deterministic run and post-test choice of this control do not establish a universal causal mechanism.")
    p(f"L3 yields {stats['L3']['exact']}/15 exact graphs, the same semantic target as B0 by construction. Its mean measured geometry errors are {stats['L3']['geometry']:.3f}, versus {stats['B0']['geometry']:.3f} for B0: {stats['L3']['geometry_better']} tasks improve and {stats['L3']['geometry_worse']} worsen; the rest are unchanged. Layout quality did not improve by this metric. The two increases are test_branch_02 (0 to 1 error) and test_loop_04 (1 to 2). Topology preservation must be evaluated separately from layout quality; movement alone is not an improvement.")
    page()
    h("Inference cost")
    p(f"Original physical experiment: 75 saved calls, 1312.894 registered model seconds. Follow-up physical calls: {aggregate['followup_actual_logged_calls']}; registered model seconds: {aggregate['followup_actual_logged_inference_seconds']:.3f}. These include saved C0, failed first-layout and revised-layout calls once each. The interrupted unsaved call has unknown cost, so the logged total is a lower bound. No new baseline generation or visual critique is included in follow-up physical calls.", small)
    p(f"Failed-layout cost: {failed['logged_calls']} logged calls, {failed['logged_inference_seconds']:.3f} model seconds. Original follow-up source calls: {aggregate['followup_v1_actual_logged_calls']}; revised-layout calls: {aggregate['layout_revision_actual_logged_calls']}. Development checks are separate from these test-source totals.", small)
    dev_calls = [load(p) for p in (ROOT / "runs/layout_development_v2").glob("*/L3/call_*.json")]
    dev_seconds = sum(c.get("response", {}).get("elapsed_seconds", 0) for c in dev_calls)
    p(f"Development validation adds {len(dev_calls)} separately saved model calls and {dev_seconds:.3f} logged model seconds. All five development outputs were valid on the first attempt and preserved all fields except node coordinates. These development calls are outside the main six-arm test-source totals.", small)
    table([["Arm", "Standalone model seconds / task"], *[[a, f"{aggregate['arms'][a]['standalone_inference_seconds_mean']:.2f}"] for a in arms]], [90, 408])
    p("Standalone costs include the shared baseline generation and, where applicable, the saved visual critique as if the arm were run alone. They must not be summed to obtain actual experiment cost. Timing includes lazy model loading, fixed execution order and caching effects; excludes rendering and validation. L3's schema/output length differs, so its cost does not isolate criticism quality.", small)
    page()
    h("Case studies and critic audit")
    p("Full Russian-language case evidence and deterministic selection rules are in analysis/followup_v1/CASE_STUDIES_RU.md. The same cases from case_studies.json are summarized below. They illustrate partial improvement, an unchanged result and an exact regression, rather than estimating prevalence or a causal mechanism.")
    def edges(scene):
        labels = {n["id"]: n["label"] for n in scene["nodes"]}
        return {(labels[e["source"]], labels[e["target"]], e.get("label", "")) for e in scene["edges"]}
    for case in load(analysis / "case_studies.json"):
        h(case["category"].replace("_", " ").capitalize())
        r = next(r for r in rows if r["task_id"] == case["task_id"] and r["arm"] == case["arm"])
        task, arm = r["task_id"], r["arm"]
        source = ROOT / "runs/test_v1" / task
        target = ROOT / ("runs/followup_v1" if arm == "C0" else "runs/test_v1") / task / arm
        before, after = edges(load(source / "B0/scene.json")), edges(load(target / "scene.json"))
        p(f"{task}, {arm}: edge F1 {float(baseline[task]['edge_f1']):.3f} to {float(r['edge_f1']):.3f}; exact {baseline[task]['exact_semantic']} to {r['exact_semantic']}.")
        for name, changes in [("Added", after - before), ("Removed", before - after)]:
            p(name + ": " + ("; ".join(f"{a} -> {b} [{c or 'unlabeled'}]" for a, b, c in sorted(changes)) if changes else "none"), small)
        if arm in {"B2", "B3"}:
            feedback = load(source / "visual/feedback.json")["text"]
            p("Saved critic excerpt (model output): " + " ".join(feedback.split()[:42]), small)
        elif arm == "C0":
            p("C0 received the original request and B0, without external criticism.", small)
        else:
            feedback = load(source / "B0/program_feedback.json")
            p(f"The editor received {len(feedback)} programmatic findings; these check geometry, not process semantics.", small)
    page()
    h("Critic audit: scope and limitations")
    p("The saved visual responses are inspected against the original scene. Describing the figure, proposing a plausible change, and correctly identifying an existing defect are different behaviors. An editor may also fail to follow a correct criticism. The audit should therefore distinguish the critic's statement from the subsequent edit.")
    audit = analysis / "critic_audit_summary.md"
    if audit.exists():
        for line in audit.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                p(line.strip().lstrip("- "), small)
    else:
        p("Full per-task evidence and the audit rubric are in CRITIC_AUDIT_RU.md and critic_audit.json. This is reproducible automated extraction of adjacent literal full node-label mentions. Only explicit simple connection language is treated as a directional candidate; ambiguity, conditionals and distorted names remain uncertain. Candidate counts are not precision/recall of the whole critic, and branch labels are not automatically assessed. No independent human or blinded multi-rater annotation is claimed.")
        audit_stats = aggregate.get("critic_audit", {})
        p(f"Audited tasks: {audit_stats.get('tasks', 15)}. Candidate classifications: {audit_stats.get('candidate_claim_counts', {})}. These assess a statement against B0 separately from whether the edge is required by the reference. Describing a wrong B0 edge faithfully is different from diagnosing its error.", small)
    h("Remaining limits")
    p("The benchmark contains 15 synthetic test tasks from three repeated topology families, with explicit labels and six or seven nodes. Development and test differ in content rather than unseen graph families. There is one deterministic seed, one correction round, no independent-regeneration control, no stronger-critic comparison, no human readability measurement, and no new held-out tasks for this supplement. The post-test follow-up cannot retroactively change the original protocol.")
    h("Reproduce and inspect")
    p("Set PYTHONPATH=src. Recompute saved analysis with python -m flowrefine.followup_analysis --baseline runs/test_v1 --followup runs/followup_v1 --layout-followup runs/layout_v2 --output analysis/followup_v1. Build this supplement with python tools/build_followup_report.py. Revised layout inference is separate: python -m flowrefine.layout_followup --baseline runs/test_v1 --output runs/NEW_NAME --failed-run runs/followup_v1. Never reuse a completed output folder for a changed experiment.", small)
    p("Sources: baseline report.md, configs/frozen_protocol.json, runs/test_v1/manifest.json, runs/followup_v1/manifest.json, analysis/followup_v1/metrics.csv and aggregate.json; implementation: followup.py and followup_analysis.py. The project uses pretrained Qwen and SmolVLM; no model weights were trained. Code, synthetic data, prompts and written material were prepared with substantial AI assistance. No public publication or course submission is performed.", small)
    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8); canvas.setFillColor(colors.HexColor("#45505A")); canvas.drawString(48, 27, "FlowRefine | Exploratory follow-up, original test preserved"); canvas.drawRightString(A4[0] - 48, 27, str(doc.page))
    SimpleDocTemplate(str(out / "report_followup.pdf"), pagesize=A4, leftMargin=48, rightMargin=48, topMargin=42, bottomMargin=43).build(story, onFirstPage=footer, onLaterPages=footer)
    (out / "report_followup.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "deck_data.json").write_text(json.dumps({"arms": stats, "aggregate": aggregate}, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    build()
