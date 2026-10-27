"""Build an evidence-linked course report from a completed saved run.

Run with a Python environment containing reportlab and Pillow. Never runs models.
"""
import argparse
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageChops
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt(value, digits=3):
    return "N/A" if value is None else f"{value:.{digits}f}"


def build(run, analysis, output):
    run, analysis, output = Path(run), Path(analysis), Path(output)
    manifest, aggregate = load(run / "manifest.json"), load(analysis / "aggregate.json")
    tasks = load(run / "tasks_public.json")
    arms, settings = aggregate["arms"], manifest["settings"]
    expected = len(tasks)
    is_test = bool(tasks) and all(t.get("split") == "test" for t in tasks)
    # A partial experiment must not silently become a final four-arm report.
    if is_test and any(arms[a]["executed"] < expected for a in arms):
        raise ValueError("Test run incomplete: finish or explicitly document missing arms before authoring the final report")
    output.mkdir(parents=True, exist_ok=True)
    preview = "" if is_test else "DEVELOPMENT PREVIEW - NOT FINAL TEST RESULTS. "
    text_model = Path(settings.get("text_model", "unspecified")).name
    vision_model = Path(settings.get("vision_model", "unspecified")).name
    projector = Path(settings.get("vision_projector", "unspecified")).name
    source_calls = sorted(run.glob("*/**/call_*.json"))
    response = load(source_calls[0]).get("response", {}) if source_calls else {}
    runtime = response.get("runtime_version", "not recorded")
    seed = response.get("seed", "not recorded")
    lines = []
    body = []
    styles = getSampleStyleSheet()
    base = ParagraphStyle("ReportBody", fontName="Helvetica", fontSize=10.5, leading=14.1,
                          textColor=colors.HexColor("#17202a"), spaceAfter=7)
    title = ParagraphStyle("ReportTitle", parent=base, fontName="Helvetica-Bold", fontSize=23,
                           leading=27, textColor=colors.black, spaceAfter=11)
    heading = ParagraphStyle("ReportHeading", parent=base, fontName="Helvetica-Bold", fontSize=13,
                             leading=17, textColor=colors.black, spaceBefore=8, spaceAfter=7)
    small = ParagraphStyle("ReportSmall", parent=base, fontSize=8.6, leading=11.6, spaceAfter=5)
    caption = ParagraphStyle("ReportCaption", parent=small, textColor=colors.HexColor("#45505a"))
    table_style = TableStyle([("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                              ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf1f5")),
                              ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#adb6bf")),
                              ("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 6),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                              ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])

    def p(text, style=base):
        body.append(Paragraph(escape(text), style))
        lines.append(text + "\n")

    def h(text):
        p(text, heading)
        lines[-1] = "## " + text + "\n"

    def table(data, widths):
        wrapped = [[Paragraph(escape(str(cell)), small) for cell in row] for row in data]
        t = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(table_style)
        body.extend([t, Spacer(1, 7)])
        for index, row in enumerate(data):
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
            if index == 0:
                lines.append("| " + " | ".join("---" for _ in row) + " |")
        lines.append("")

    def chart(name, width, height, description):
        path = analysis / name
        if not path.exists():
            raise FileNotFoundError(path)
        body.append(Image(str(path), width=width, height=height, kind="proportional"))
        p(description, caption)
        lines.append(f"![{description}]({path.resolve().as_posix()})\n")

    def page():
        body.append(PageBreak())
        lines.append("\n---\n")

    p("FlowRefine", title)
    lines[-1] = "# FlowRefine\n"
    p("Can visual feedback improve generated flowcharts on a CPU?", heading)
    p(preview + "Generative AI final project | Reproducible pilot study | 24 October 2026", small)
    h("Research question")
    p("Does one round of feedback-driven editing improve the semantic correctness and layout of editable flowcharts? We compare programmatic, visual, and combined feedback under the same initial diagram and the same text editor. The study measures both correction and regression; it does not assume that adding a visual critic helps.")
    if is_test:
        improved = [a for a in ("B1", "B2", "B3") if arms[a]["edge_f1_mean"] > arms["B0"]["edge_f1_mean"] + 1e-9]
        observation = "No feedback arm improves mean edge F1 in this run." if not improved else "Mean edge F1 improves for " + ", ".join(improved) + " in this run."
        p(f"Observed outcome: the initial model produces exactly correct graphs on {round(arms['B0']['exact_semantic_mean'] * expected)}/{expected} tasks. Exact correctness after programmatic, visual and combined feedback is {round(arms['B1']['exact_semantic_mean'] * expected)}/{expected}, {round(arms['B2']['exact_semantic_mean'] * expected)}/{expected} and {round(arms['B3']['exact_semantic_mean'] * expected)}/{expected}. {observation} The result argues for checking regressions before trusting a small visual critic, within this limited model and task setting.")
    h("System and contributions")
    p("A text model converts an explicit process description into a compact JSON graph. Each node contains its exact stage label, type and grid location; each edge contains source label, target label and branch label. A deterministic renderer expands the grid into fixed-size blocks and routes arrows, producing editable SVG and a PNG for visual inspection. Grid coordinates simplify output syntax but restrict possible layouts.")
    p("A reference-free checker identifies geometry and rendering risks. A separate small vision-language model receives only the rendered image and the original request. The text editor then regenerates the complete graph using the assigned feedback. No critic, generator or editor receives a reference graph, semantic score or test-ground-truth correction.")
    p("Project contributions are an implemented scene representation and renderer; geometric checks and structured programmatic feedback; an image-conditioned criticism and editing pipeline; a small controlled dataset; and auditable semantic, geometry and inference-cost analysis. Pretrained models are reused without fine-tuning. The contribution is a course-level system and evaluation, not a claim of a novel model architecture.")
    h("Dataset and scope")
    p("The dataset contains 5 development tasks and 15 held-out test tasks: five chains, five two-way branches and five loops. Each process contains 6 or 7 explicitly named nodes. A fixed template verbalizes assistant-authored process specifications. Development and test topics differ; graph families remain shared. This evaluates unseen process content within familiar structures, not transfer to unseen graph topologies or unrestricted natural-language workflows.")
    p("All prompts request exact labels and explicit Yes/No decision branches. References contain nodes, types and directed labeled edges, but no target coordinates. Generation reads public task files; references are read only by the analysis stage. No independent human-authored or blinded evaluation dataset is claimed.")
    page()
    h("Frozen experimental protocol")
    table([["Arm", "Available feedback for one editing round"],
           ["B0", "Initial generated graph; no editing."],
           ["B1", "Reference-free programmatic geometry checks."],
           ["B2", "Visual critic output from the initial PNG."],
           ["B3", "The same programmatic checks and visual critic output."]], [48, 447])
    p("Every task has one shared initial graph. B1-B3 each use one semantic editing round, with a common text model and prompt format. The VLM feedback is computed once per initial image and reused identically by B2 and B3. This is shared feedback reuse, not a second independent visual sample. A bounded format-recovery retry may occur after invalid output; these calls are logged and included in costs. No best-of-test-score selection is used.")
    h("CPU implementation and model settings")
    table([["Setting", "Recorded value"],
           ["Text generator/editor", text_model], ["Visual critic", vision_model],
           ["Vision projector", projector],
           ["Backend", f"llama-cpp-python {runtime}; MTMD vision; CPU only"],
           ["Decoding", f"temperature={settings.get('temperature', 'not recorded')}; seed={seed}; threads={settings.get('threads', 'not recorded')}"],
           ["Output budgets", f"text={settings.get('max_tokens', 'not recorded')}; vision={settings.get('vision_max_tokens', 'not recorded')}; format retries={settings.get('format_repairs', 'not recorded')}"],
           ["Prompt version", manifest.get("prompt_version", "not recorded")]], [120, 375])
    p("Models are loaded sequentially without GPU offloading. Exact repositories, revisions, byte sizes and SHA-256 hashes are recorded in configs/model_lock.json; runtime_setup/HANDOFF.md documents CPU smoke tests. Qwen2.5-3B uses the qwen-research license; SmolVLM distributions use Apache-2.0. Initial 1.5B probes are exploratory and retained under development runs, not pooled into test metrics. The larger text model was selected on development tasks. Earlier smoke scripts used an older output format. Prompt or model changes were development decisions, not per-test-task selection.", small)
    h("Metrics and failure handling")
    p("Nodes match one-to-one by normalized exact label and type. Normalization applies Unicode NFKC, case folding and punctuation-to-space replacement. Edges match only when source, target, direction and normalized branch label agree. Node and edge precision, recall and F1 penalize omissions and additions. Exact semantics requires a complete match. No fuzzy matcher or model judge is used.")
    p("Executed invalid scenes receive zero semantic scores. Unexecuted/unavailable arms remain missing and are excluded from quality means. Geometry counts are defined only on valid scenes, with coverage reported alongside them; invalid scenes are never interpreted as zero geometry errors. Render availability is tracked separately. Paired differences use comparable tasks and a fixed-seed 1,000-resample task bootstrap.")
    page()
    h(preview + "Results from saved inference")
    p(f"Run: {run.name}. Public tasks: {len(tasks)}. Provenance: {aggregate.get('provenance', 'unspecified')}. All values below are read from saved analysis artifacts; no expected or illustrative accuracy is inserted.", small)
    result_table = [["Arm", "Run / valid", "Node F1", "Edge F1", "Exact", "Seconds/task"]]
    for arm in ("B0", "B1", "B2", "B3"):
        s = arms[arm]
        result_table.append([arm, f"{s['executed']} / {s['valid']}", fmt(s["node_f1_mean"]), fmt(s["edge_f1_mean"]), fmt(s["exact_semantic_mean"]), fmt(s["standalone_inference_seconds_mean"], 1)])
    table(result_table, [35, 85, 75, 75, 65, 160])
    p("Run / valid gives executed and structurally valid counts. Scores average all executed tasks, including invalid outputs as zero. Exact is the proportion of exactly correct graphs. Seconds/task is standalone model-call time including shared generation and the relevant visual critique.", caption)
    chart("semantic_quality.png", 490, 275, "Figure 1. Semantic quality by feedback arm. Sample counts are shown; higher is better.")
    h("Paired semantic effects")
    for arm in ("B1", "B2", "B3"):
        delta = aggregate["paired_differences"][arm + "_minus_B0"]["edge_f1"]
        interval = delta["ci95"]
        interval_text = "N/A" if interval is None else f"[{fmt(interval[0])}, {fmt(interval[1])}]"
        p(f"{arm} minus B0: mean edge-F1 change {fmt(delta['mean'])}; bootstrap 95% interval {interval_text}; paired tasks n={delta['n']}.", small)
    p("Intervals are descriptive for this small pilot and are not multiplicity-corrected. Arm means may use different task sets when an arm is unavailable; paired effects are the appropriate within-task comparison. Exact scores and edge F1 should be considered together with validity and geometry.", small)
    if all(arms[a]["executed"] == expected for a in arms):
        differences = {a: aggregate["paired_differences"][a + "_minus_B0"]["edge_f1"]["mean"] for a in ("B1", "B2", "B3")}
        positives = [a for a, change in differences.items() if change is not None and change > 1e-9]
        if not positives:
            p("For this run, no feedback arm improves mean edge F1 over the shared initial baseline. This is a limited empirical outcome, not evidence that stronger visual critics cannot help.", small)
        else:
            p("Mean edge F1 increases for " + ", ".join(positives) + " in this run; effect sizes and intervals above should be interpreted with the small task count and validity outcomes.", small)
    page()
    h("Layout, cost and interpretation")
    chart("geometry_coverage.png", 495, 195, "Figure 2. Geometry error counts are conditional on validity; coverage includes invalid and unavailable cases.")
    p(f"Actual persisted calls: {aggregate['actual_logged_calls']}; calls explicitly marked cached: {aggregate['actual_cached_calls']}. Total logged model time: {aggregate['actual_logged_inference_seconds']:.1f} seconds. Logged prompt/completion tokens: {aggregate['actual_logged_prompt_tokens']} / {aggregate['actual_logged_completion_tokens']}. Each saved call is counted once in the actual total. Standalone arm costs intentionally reinclude shared dependencies and must not be summed as the physical experiment cost.")
    p("Feedback reuse across B2/B3 is distinct from a backend cache hit. Timings are serial single-pass observations: the first call may include model loading, and prompt-prefix caches may be warm. They are not a standardized serving benchmark. Local CPU checking/rendering is excluded. Token counts are recorded from model responses. See raw_calls.csv for per-call evidence and quality_cost.png for the quality/time plot.", small)
    h("Limitations and next steps")
    p("Fifteen synthetic test tasks, one decoding seed and shared graph templates do not support broad generalization. Strict labels can penalize meaningful paraphrases. Fixed grid geometry and automatic arrow routing constrain what the editor can change. The tiny visual model may describe a diagram instead of diagnosing errors, hallucinate links or produce unhelpful criticism. A null or negative repair effect is a result about this implementation and model budget, not proof that visual feedback cannot work.")
    p("There is no independent human or blinded readability study: any qualitative inspection is assistant spot-checking only. We do not estimate human preference. Stronger follow-up work would add an equal-budget resampling control, a standard graph-layout baseline, multiple seeds, a stronger VLM, free-form descriptions and independent human evaluation. These are not represented as completed experiments.")
    h("Related work, sources and AI assistance")
    p("IntroSVG [1] studies generator-critic feedback for text-to-SVG and includes learned alignment. This project uses pretrained models and checks directed process semantics; it does not reproduce IntroSVG training or claim novelty for the generator-critic idea. The CPU models/runtime are documented in [2-5]. Codex assistance was used for implementation, synthetic-task authoring, execution, evaluation and report drafting. All reported measurements derive from persisted inference logs.", small)
    for ref in [
        "[1] Wang et al. IntroSVG: Learning from Rendering Feedback for Text-to-SVG Generation via an Introspective Generator-Critic Framework (2026). https://arxiv.org/abs/2603.09312",
        "[2] Qwen model source and GGUF distributions. https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF (exact checkpoint, license and revision in configs/model_lock.json).",
        "[3] SmolVLM-256M-Instruct model card. https://huggingface.co/HuggingFaceTB/SmolVLM-256M-Instruct",
        "[4] CPU GGUF conversion and projector. https://huggingface.co/ggml-org/SmolVLM-256M-Instruct-GGUF",
        "[5] llama.cpp runtime. https://github.com/ggml-org/llama.cpp ; Python bindings: https://github.com/abetlen/llama-cpp-python",
    ]:
        p(ref, small)
    # A first-ID case avoids selecting only a favorable correction as a showcase.
    example = None
    for task in sorted(tasks, key=lambda t: t["id"]):
        b0, b3 = run / task["id"] / "B0", run / task["id"] / "B3"
        if all((folder / "chart.png").exists() and load(folder / "status.json").get("valid") for folder in (b0, b3)):
            example = task
            break
    if example:
        page()
        h("Appendix: one saved before/after case")
        p(f"Task {example['id']}: selected as the first task ID with valid rendered B0 and B3 outputs. It is not selected for the largest improvement. This is an illustrative case, not an independent human quality judgment. Empty margins are cropped; clipping already present in an original rendered canvas is preserved.", small)
        p(example["prompt"], small)
        pictures = []
        for arm in ("B0", "B3"):
            path = run / example["id"] / arm / "chart.png"
            with PILImage.open(path) as image:
                image = image.convert("RGB")
                background = PILImage.new("RGB", image.size, image.getpixel((0, 0)))
                bbox = ImageChops.difference(image, background).getbbox()
                if bbox:
                    left, top, right, bottom = bbox
                    image = image.crop((max(0, left - 12), max(0, top - 12), min(image.width, right + 12), min(image.height, bottom + 12)))
                crop = output / "qa_report" / f"{example['id']}_{arm}_crop.png"
                crop.parent.mkdir(parents=True, exist_ok=True)
                image.save(crop)
                w, height = image.size
                scale = min(235 / w, 410 / height)
                pictures.append([Paragraph(arm + (" initial" if arm == "B0" else " combined feedback"), heading), Image(str(crop), width=w * scale, height=height * scale)])
        table_images = Table([[pictures[0], pictures[1]]], colWidths=[247, 248])
        table_images.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        body.append(table_images)
        feedback = run / example["id"] / "visual" / "feedback.json"
        if feedback.exists():
            p("Saved visual feedback (verbatim; may be incorrect):", small)
            p(load(feedback).get("text", "")[:1400], small)
        lines.append(f"Example images: {run.name}/{example['id']}/B0/chart.png and B3/chart.png\n")
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#58626d"))
        canvas.drawString(48, 28, "FlowRefine | Generative AI course pilot" + (" | DEVELOPMENT PREVIEW" if not is_test else ""))
        canvas.drawRightString(A4[0] - 48, 28, str(document.page))
        canvas.restoreState()

    document = SimpleDocTemplate(str(output / "report.pdf"), pagesize=A4,
                                 rightMargin=48, leftMargin=48, topMargin=42, bottomMargin=43,
                                 title="FlowRefine: CPU-only feedback for generated flowcharts", author="Generative AI course project")
    document.build(body, onFirstPage=footer, onLaterPages=footer)
    print(output / "report.pdf")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("submission"))
    args = parser.parse_args()
    build(args.run, args.analysis, args.output)
