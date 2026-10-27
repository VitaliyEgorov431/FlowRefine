/** Build an evidence-only academic deck from immutable FlowRefine results.
 * Usage: bundled-node tools/build_deck.mjs --run runs/test_v1
 *   --analysis analysis/test_v1 --output submission/presentation.pptx
 * Reruns require a NEW output filename; the finalizer refuses overwriting.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const workspaceDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SKILL_DIR = process.env.PRESENTATIONS_SKILL_DIR || 'C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1022.11436/skills/presentations';
const runtimeDir = process.env.CODEX_RUNTIME_DIR || 'C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES ||= path.join(runtimeDir, 'node/node_modules');
const RUNTIME_PYTHON = process.env.RUNTIME_PYTHON || path.join(runtimeDir, 'python/python.exe');
const {importRuntimeModule} = await import(pathToFileURL(path.join(SKILL_DIR, 'container_tools/runtime_helpers.mjs')).href);
const {FileBlob, Presentation, PresentationFile} = await importRuntimeModule('@oai/artifact-tool');
const {finalizePresentation, applyPresentationChartFont} = await import(pathToFileURL(path.join(SKILL_DIR, 'container_tools/artifact_tool_utils.mjs')).href);

const argumentsMap = new Map();
for (let i = 2; i < process.argv.length; i += 2) {
  if (!process.argv[i].startsWith('--') || !process.argv[i + 1]) throw Error('Expected --option value pairs');
  argumentsMap.set(process.argv[i].slice(2), process.argv[i + 1]);
}
const runDir = path.resolve(workspaceDir, argumentsMap.get('run') || 'runs/test_v1');
const analysisDir = path.resolve(workspaceDir, argumentsMap.get('analysis') || 'analysis/test_v1');
const finalPath = path.resolve(workspaceDir, argumentsMap.get('output') || 'submission/presentation.pptx');
if (await fs.stat(finalPath).catch(() => null)) throw Error('Output exists. Use a new filename; final files are immutable.');
const aggregate = JSON.parse(await fs.readFile(path.join(analysisDir, 'aggregate.json'), 'utf8'));
const manifest = JSON.parse(await fs.readFile(path.join(runDir, 'manifest.json'), 'utf8'));
const tasks = JSON.parse(await fs.readFile(path.join(runDir, 'tasks_public.json'), 'utf8'));
function parseCsv(source) {
  const rows = []; let row = [], field = '', quoted = false;
  for (let i = 0; i < source.length; i++) {
    const c = source[i];
    if (quoted) {
      if (c === '"' && source[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field.replace(/\r$/, '')); rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field || row.length) { row.push(field.replace(/\r$/, '')); rows.push(row); }
  const headers = rows.shift();
  return rows.filter(r => r.length === headers.length).map(r => Object.fromEntries(headers.map((h, i) => [h, r[i]])));
}
const metricRows = parseCsv(await fs.readFile(path.join(analysisDir, 'metrics.csv'), 'utf8'));
if (aggregate.task_count !== tasks.length) throw Error('Analysis/run task counts disagree');
if (aggregate.provenance !== 'real_model_inference') throw Error('Only real saved inference may support this deck');
const isTest = tasks.length > 0 && tasks.every(t => t.split === 'test');
const label = isTest ? 'TEST PILOT' : 'DEVELOPMENT CHECK';
const arms = ['B0', 'B1', 'B2', 'B3'];
const names = {B0: 'Initial', B1: 'Programmatic', B2: 'Visual', B3: 'Combined'};
const value = (a, key) => aggregate.arms[a]?.[key] ?? null;
const fmt = (number, digits = 2) => number == null ? 'unavailable' : Number(number).toFixed(digits);
const executedArms = arms.filter(a => value(a, 'executed') > 0);
if (!executedArms.length) throw Error('No executed model outputs to present');
const baseline = value('B0', 'edge_f1_mean');
const edits = arms.slice(1).filter(a => value(a, 'edge_f1_mean') != null);
const best = edits.sort((a, b) => value(b, 'edge_f1_mean') - value(a, 'edge_f1_mean'))[0];
const delta = best && baseline != null ? value(best, 'edge_f1_mean') - baseline : null;
const semanticFinding = delta == null ? 'The pilot has incomplete edit coverage' :
  delta > .0005 ? `${best} raises mean edge F1 by ${fmt(delta)}` :
  delta < -.0005 ? `All three feedback modes lower mean edge F1` : 'No edit improves mean edge F1';
const modelName = path.basename(manifest.settings?.text_model || 'unspecified');
const buildDir = path.join(workspaceDir, '.deck_build', `${path.basename(finalPath, '.pptx')}_${Date.now()}`);
const previewDir = path.join(workspaceDir, 'submission/qa_slides', path.basename(finalPath, '.pptx'));
await fs.mkdir(buildDir, {recursive: true});
await fs.mkdir(previewDir, {recursive: true});
await fs.mkdir(path.dirname(finalPath), {recursive: true});

const NAVY = '#1F4E79', BLUE = '#2E75B6', WHITE = '#FFFFFF';
const presentation = Presentation.create({slideSize: {width: 1280, height: 720}});
function text(slide, content, x, y, width, height, size = 27, bold = false, color = NAVY) {
  const shape = slide.shapes.add({geometry: 'textbox', position: {left: x, top: y, width, height},
    fill: 'none', line: {fill: 'none', width: 0}});
  shape.text = content;
  shape.text.style = {fontSize: size, typeface: 'Arial', bold, color, verticalAlignment: 'top', insets: 0};
  return shape;
}
function slide(title, source, notes = '') {
  const s = presentation.slides.add();
  s.background.fill = WHITE;
  text(s, title, 64, 46, 1152, 104, 41, true);
  text(s, `${label}  ${path.basename(runDir)}  ${presentation.slides.items.length}`, 64, 674, 1152, 23, 17);
  if (source) text(s, source, 64, 637, 1152, 31, 17);
  s.speakerNotes.text = `${notes}\n\nSource run: ${runDir}\nAnalysis: ${analysisDir}\nText model: ${modelName}\nSource files and prompt version: manifest.json\n${source || ''}`;
  return s;
}
function paragraphs(s, items, x = 64, y = 190, width = 1130, spacing = 100, size = 29) {
  items.forEach((line, i) => text(s, line, x, y + spacing * i, width, spacing - 12, size));
}
function chart(s, key, seriesName, max = null) {
  const available = executedArms.filter(a => value(a, key) != null);
  // Excel stores at most 15 significant digits. Charts keep six decimals;
  // aggregate.json remains the unrounded source and labels show two decimals.
  const values = available.map(a => Number(value(a, key).toFixed(6)));
  const ch = s.charts.add('bar', {position: {left: 64, top: 183, width: 735, height: 422},
    categories: available.map(a => a),
    series: [{name: seriesName, values, fill: BLUE, valuesFormatCode: '0.00'}],
    hasLegend: false, titlePlacement: 'none',
    barOptions: {direction: 'column', grouping: 'clustered', gapWidth: 100},
    xAxis: {textStyle: {fontSize: 25, fill: NAVY}, majorGridlines: null},
    yAxis: {min: 0, max: max ?? Math.max(1, ...values.map(v => v * 1.28)), numberFormatCode: '0.0',
      textStyle: {fontSize: 23, fill: NAVY}, majorGridlines: {fill: '#DCE6F1', width: 1, style: 'solid'}},
    dataLabels: {showValue: true, position: 'outEnd', numberFormatCode: '0.00', textStyle: {fontSize: 23, fill: NAVY, bold: true}},
    chartFill: WHITE, plotAreaFill: WHITE});
  applyPresentationChartFont(ch, {fontFamily: 'Arial'});
  return ch;
}

// 1: title, no invented presenter name or affiliation.
{
  const s = slide('FlowRefine', 'Generative AI final project, 24 October 2026',
    'A CPU-only pilot on generation and one-round correction of editable flowcharts. Author name is intentionally omitted because it was not supplied. The implementation, benchmark and prompts were developed with an AI coding assistant.');
  text(s, 'Programmatic and visual feedback\nfor editable flowcharts', 64, 192, 1120, 170, 54, true);
  text(s, `${tasks.length} ${isTest ? 'test' : 'development'} tasks\nOne correction round on CPU`, 64, 440, 1100, 100, 31);
}
// 2: explicit research question.
{
  const s = slide('Can feedback improve a generated flowchart?', 'Related work: Wang et al., IntroSVG (2026), arXiv:2603.09312',
    'Research question: how do deterministic geometry feedback, a small visual critic, and their combination change structural correctness after one edit? IntroSVG motivates rendered feedback but uses a different trained SVG generator-critic setup. FlowRefine does not replicate its method or claim comparable performance. https://arxiv.org/abs/2603.09312');
  paragraphs(s, ['Text descriptions require correct directed graphs.',
    'Readable layouts can still contain incorrect branches.',
    'Compare feedback sources on the same initial output.'], 64, 190, 1130, 116);
}
// 3: four arms, same initial diagram.
{
  const s = slide('All edit arms share one initial diagram', 'Source: src/flowrefine/runner.py and prompts.py',
    'B0 is the same saved initial scene for every edit arm. B1 sees program feedback, B2 sees one shared VLM response, B3 sees both. The editor receives the original public request and compact scene. One correction round only, with one allowed format-repair attempt. References and semantic scores never enter inference.');
  const rows = [['B0', 'Generate JSON, render SVG and PNG'], ['B1', 'Edit using geometry checks'],
                ['B2', 'Edit using the shared image critique'], ['B3', 'Edit using both feedback sources']];
  rows.forEach(([a, description], i) => {
    text(s, a, 64, 184 + i * 101, 110, 65, 34, true);
    text(s, description, 205, 184 + i * 101, 990, 65, 30);
  });
}
// 4: dataset and scoring.
{
  const s = slide('The benchmark isolates familiar graph structures', 'Source: data/DATASET_CARD.md and dataset.py',
    'The assistant authored 20 synthetic specifications and a deterministic verbalization template. Five development and fifteen test tasks have six or seven nodes. Test topics differ but topology families repeat. Exact normalized label plus node-type matching is deliberately strict. Test score changes do not establish generalization to human free prose.');
  paragraphs(s, ['5 development tasks and 15 test tasks',
    'Chains, branches and loops with 6–7 nodes',
    'Exact labels, node types and directed edge matching',
    'Reference graphs enter evaluation only'], 64, 178, 1130, 97);
}
// 5: native semantic evidence.
{
  const s = slide(semanticFinding, 'Source: saved model outputs, aggregate.json; edge F1 on executed tasks',
    'Native editable chart uses actual aggregate values. Invalid executed scenes have zero semantic scores. Unexecuted modes are excluded. Scores use exact normalized stage labels and types, plus directed edge labels. No statistical significance or broad generalization is claimed.');
  chart(s, 'edge_f1_mean', 'Mean edge F1', 1.12);
  text(s, 'Exact graph matches', 845, 184, 355, 58, 27, true);
  paragraphs(s, arms.map(a => `${a}: ${value(a, 'exact_semantic_mean') == null ? 'unavailable' : Math.round(value(a, 'exact_semantic_mean') * value(a, 'executed'))} / ${value(a, 'executed')}`), 845, 260, 355, 68, 27);
}
// 6: native geometry evidence, coverage always visible.
{
  const s = slide('Geometry scores require valid output coverage', 'Source: aggregate.json; error counts on valid scenes only',
    'Geometry checks measure bounding-box overlap, text fit, canvas bounds, attachment and unrelated-node crossings. They do not evaluate process meaning or human readability. Invalid outputs have undefined geometry. Arm-specific valid counts are shown to avoid reporting the easy surviving cases as total success.');
  chart(s, 'geometry_errors_valid_mean', 'Geometry errors on valid scenes');
  text(s, 'Valid scenes / executed', 845, 184, 365, 58, 27, true);
  paragraphs(s, arms.map(a => `${a}: ${value(a, 'valid')} / ${value(a, 'executed')}`), 845, 260, 355, 68, 27);
}
// 7: first exact-match regression in fixed task order, otherwise a critic excerpt.
{
  const rowFor = (id, arm) => metricRows.find(r => r.task_id === id && r.arm === arm);
  const regressed = tasks.find(t => Number(rowFor(t.id, 'B0')?.exact_semantic) === 1 &&
    rowFor(t.id, 'B3')?.executed === 'True' && Number(rowFor(t.id, 'B3')?.exact_semantic) === 0);
  if (regressed) {
    const before = JSON.parse(await fs.readFile(path.join(runDir, regressed.id, 'B0/scene.json'), 'utf8'));
    const after = JSON.parse(await fs.readFile(path.join(runDir, regressed.id, 'B3/scene.json'), 'utf8'));
    const edgeKeys = scene => scene.edges.map(e => {
      const labels = Object.fromEntries(scene.nodes.map(n => [n.id, n.label]));
      return [labels[e.source], labels[e.target], e.label || ''];
    });
    const beforeKeys = new Set(edgeKeys(before).map(e => JSON.stringify(e)));
    const added = edgeKeys(after).filter(e => !beforeKeys.has(JSON.stringify(e)));
    const s = slide('A correction breaks an initially correct graph', `Source: ${regressed.id}, B0 and B3 scenes and metrics.csv`,
      `Select the first task in fixed dataset order with exact_semantic B0=1 and B3=0. This is an illustrative regression, not a representative causal mechanism. Original edges: ${JSON.stringify(edgeKeys(before))}. Edited edges: ${JSON.stringify(edgeKeys(after))}. Read the saved visual/feedback.json and call_repair logs for actual feedback and edit. Other tasks may improve; aggregate includes all fifteen.`);
    text(s, `${regressed.id}: edge F1 ${fmt(Number(rowFor(regressed.id, 'B0').edge_f1))} before, ${fmt(Number(rowFor(regressed.id, 'B3').edge_f1))} after`, 64, 184, 1130, 80, 29, true);
    if (added.length) {
      text(s, 'The combined edit adds unsupported connections:', 64, 287, 1130, 70, 29);
      added.slice(0, 2).forEach((e, i) => text(s, `${e[0]} to ${e[1]}${e[2] ? ` (${e[2]})` : ''}`, 64, 382 + i * 92, 1130, 82, 28));
    } else {
      text(s, 'The edit changes the graph despite an initially exact match.', 64, 322, 1130, 160, 30);
    }
  } else {
  let quote = null, quoteTask = null;
  for (const task of tasks) {
    try {
      const feedback = JSON.parse(await fs.readFile(path.join(runDir, task.id, 'visual/feedback.json'), 'utf8'));
      quote = String(feedback.text).split(/\s+/).slice(0, 25).join(' ');
      quoteTask = task.id; break;
    } catch {}
  }
  const s = slide('A small visual critic can provide weak feedback', 'Source: first available saved visual feedback; full text in run logs',
    `The displayed excerpt is the first available task in fixed dataset order, ${quoteTask || 'none'}, not a manually chosen success. It is a model response, not ground truth. SmolVLM-256M may describe a picture instead of diagnosing errors. Review the full saved feedback and compare with the original SVG. Model source: https://huggingface.co/ggml-org/SmolVLM-256M-Instruct-GGUF`);
  if (quote) {
    text(s, `Saved response for ${quoteTask}`, 64, 184, 1120, 50, 27, true);
    text(s, `“${quote}…”`, 64, 262, 1110, 190, 31);
    text(s, 'Description alone does not establish a correct diagnosis.', 64, 506, 1120, 75, 28);
  } else {
    paragraphs(s, ['No visual feedback is available for this run.', 'Missing evidence remains explicit.']);
  }
  }
}
// 8: native cost evidence.
{
  const s = slide('Every correction adds CPU inference cost', 'Source: call logs and aggregate.json; seconds per task',
    'Native chart includes shared initial generation and visual critique in each standalone arm cost. The actual experimental total counts each stored call once. Model latency includes lazy initial loading but excludes deterministic rendering and validation. Missing modes are omitted, not assigned zero cost. A single fixed execution order, hardware load and first-call warm-up affect timing. This is descriptive experimental cost, not a controlled serving-throughput benchmark.');
  chart(s, 'standalone_inference_seconds_mean', 'Standalone model seconds per task');
  paragraphs(s, [`Saved calls: ${aggregate.actual_logged_calls}`, 'Shared calls count once in the actual total.',
    'Compare quality with coverage and cost.'], 845, 200, 355, 121, 27);
}
// 9: sources and limits; full URLs remain in notes.
{
  const s = slide('The pilot supports a limited empirical claim', 'Sources: Qwen model card; SmolVLM GGUF card; Wang et al. (2026)',
    'Qwen official GGUF model: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF\nSmolVLM GGUF and projector: https://huggingface.co/ggml-org/SmolVLM-256M-Instruct-GGUF\nWang, F. et al. (2026). IntroSVG: Learning from Rendering Feedback for Text-to-SVG Generation via an Introspective Generator-Critic Framework. https://arxiv.org/abs/2603.09312\nNo weights were trained for FlowRefine. One deterministic seed. No independent regeneration baseline, no human readability study, no claim of state-of-the-art performance. Assistant authored code, templates and prompts.');
  paragraphs(s, ['Small template dataset and one seed', 'Strict labels can penalize valid rephrasings',
    'No human readability or regeneration baseline', 'Models: Qwen2.5 and SmolVLM. Related work: IntroSVG'], 64, 178, 1130, 97);
}
// 10: conclusions must remain last.
{
  const s = slide('Feedback did not improve this CPU pilot', 'Reproduction: README.md and notebooks/FlowRefine_CPU.ipynb',
    `Main empirical observation: ${semanticFinding}. Interpret this together with invalid outputs, the tiny critic, task template overlap and added inference time. The delivered system includes safe editable scenes, deterministic checks, separate saved calls, immutable manifests, analysis and offline replay. Next work would add a stronger critic, independent regeneration and human readability assessment.`);
  paragraphs(s, [semanticFinding,
    'The system produces auditable SVG, JSON and CPU logs.',
    'Broader claims need stronger critics and new tasks.'], 64, 190, 1130, 112);
  text(s, `Run: ${path.basename(runDir)}, tasks: ${tasks.length}, README.md`, 64, 561, 1120, 50, 24);
}

const candidatePath = path.join(buildDir, 'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const result = await finalizePresentation({workspaceDir, candidatePath, finalPath,
  pythonExecutable: RUNTIME_PYTHON,
  explicitTotalSlideCount: 10,
  requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [5, 6, 8],
  materializeLiteralChartWorkbooks: true,
  fontPolicy: {basis: 'design', families: ['Arial']},
  integrityValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit'],
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildDir, 'validation.json')});
// Preview the validated file, including its materialized native chart data.
const finalPresentation = await PresentationFile.importPptx(await FileBlob.load(finalPath));
for (const [index, s] of finalPresentation.slides.items.entries()) {
  const png = await finalPresentation.export({slide: s, format: 'png', scale: 1});
  await fs.writeFile(path.join(previewDir, `slide-${String(index + 1).padStart(2, '0')}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({finalPath: result.finalPath, receiptPath: result.receiptPath, previewDir, slides: 10, label}, null, 2));
