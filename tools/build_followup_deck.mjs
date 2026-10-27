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
const finalPath = path.resolve(workspaceDir, argumentsMap.get('output') || 'submission/followup_v1/FlowRefine_Defense.pptx');
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
const label = 'FROZEN TEST + EXPLORATORY FOLLOW-UP';
const follow = JSON.parse(await fs.readFile(path.join(workspaceDir, 'submission/followup_v1/deck_data.json'), 'utf8'));
const f = follow.arms;
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


// Full updated ten-slide defense, original deck preserved.
{
 const s=slide('FlowRefine', 'Generative AI final project | 24 October 2026', 'Pretrained CPU models; no training. AI-assisted implementation and synthetic tasks. Original frozen test and later exploratory additions are explicitly distinguished.');
 text(s,'Feedback and constrained editing\nfor editable flowcharts',64,190,1130,160,52,true);
 text(s,'Frozen four-arm pilot + exploratory follow-up\n15 saved initial diagrams, one correction round',64,420,1130,120,31);
}
{
 const s=slide('Can criticism improve a generated flowchart?', 'Source: baseline report; follow-up protocol and saved manifests', 'Research question: whether deterministic or image-conditioned criticism improves graph correctness and layout. Later exploratory questions: whether editing alone changes correctness, and whether coordinates can be changed safely. No causal or universal claim follows from one seed and template-based tasks.');
 paragraphs(s,['Generate editable JSON, then render SVG and PNG.','Compare correctness before and after one edit.','Follow-up: edit without feedback; edit coordinates only.'],64,190,1130,115);
}
{
 const s=slide('Every comparison reuses the same saved B0', 'Source: frozen_protocol.json; followup.py; run manifests', 'B0-B3 are the original frozen experiment, not rerun. C0/L3 were designed after seeing original test outcomes. C0 is feedback-free editing, not independent generation or a perfectly single-variable ablation: the final instruction differs. L3 reuses saved B0 geometry and visual feedback and uses a different constrained output schema. No new visual-model call. The initial L3 format produced eight invalid saved scenes in sixteen logged calls, then one response was interrupted before persistence. A revised schema was tested on development and saved separately in layout_v2; the final L3 values describe that revision. All failed calls are retained and included in logged follow-up cost; interrupted cost is unknown. All models receive public descriptions only; references enter evaluation.');
 paragraphs(s,['Frozen: B0 initial; B1 program; B2 image; B3 both.','Post-test C0: rewrite B0 without external criticism.','Post-test L3 v2: both critiques; coordinates only.','All 15 B0 and saved image critiques reused.'],64,170,1130,99,28);
}
{
 const s=slide('The original feedback modes lower mean edge F1', 'Source: frozen analysis/test_v1/aggregate.json', 'Original frozen results only. Node labels/types and labeled directed edges matched exactly after normalization. All 60 scenes valid. No original edit fixes an initially incorrect graph to exact correctness. Partial F1 changes and regressions are shown separately in the supplement.');
 text(s,'Mean edge F1 (higher is better)',64,148,1130,35,23);
 chart(s,'edge_f1_mean','Mean edge F1',1.12);
 text(s,'Exact graphs / 15',845,190,350,55,29,true);
 paragraphs(s,['B0: 11','B1: 11','B2: 9','B3: 7'],845,265,340,70,29);
}
{
 const s=slide('Paired outcomes distinguish fixes from regressions', 'Source: analysis/followup_v1/metrics.csv; all changes paired to B0', 'F1 up/down counts refer to edge F1. Exact fixed means incorrect B0 becomes exactly correct; broken means correct B0 becomes incorrect. All fifteen tasks are included. L3 preserves graph semantics by code, not model reasoning. C0 is post-test and one deterministic run.');
 const values=[['Arm','F1 up','F1 down','Exact fixed','Exact broken'],...['B1','B2','B3','C0','L3'].map(a=>[a,String(f[a].improved),String(f[a].worsened),String(f[a].fixed),String(f[a].broken)])];
 const t=s.tables.add({rows:6,columns:5,left:64,top:177,width:1140,height:401,columnWidths:[152,190,210,240,348],values});
 for(let r=0;r<6;r++)for(let c=0;c<5;c++){const cell=t.getCell(r,c);cell.fill=WHITE;cell.text.style={fontSize:27,typeface:'Arial',color:NAVY,bold:r===0,insets:10};}

}
function followChart(s,key,chosen,max,labelText){
 const ch=s.charts.add('bar',{position:{left:64,top:183,width:735,height:422},categories:chosen.map(a=>a==='L3'?'L3 v2':a),series:[{name:labelText,values:chosen.map(a=>Number(f[a][key].toFixed(6))),fill:BLUE,valuesFormatCode:'0.00'}],hasLegend:false,titlePlacement:'none',barOptions:{direction:'column',grouping:'clustered',gapWidth:100},xAxis:{textStyle:{fontSize:25,fill:NAVY},majorGridlines:null},yAxis:{min:0,max,numberFormatCode:'0.0',textStyle:{fontSize:23,fill:NAVY},majorGridlines:{fill:'#DCE6F1',width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00',textStyle:{fontSize:23,fill:NAVY,bold:true}},chartFill:WHITE,plotAreaFill:WHITE});
 applyPresentationChartFont(ch,{fontFamily:'Arial'});
}
{
 const s=slide(f.C0.unchanged===15?'C0 keeps the original semantic scores':'Editing without criticism changes semantic scores', 'Source: follow-up C0 and frozen B0/B3 saved outputs', 'Exploratory feedback-free editing control C0 is compared descriptively to B0 and B3 on the same saved tasks. The final instruction wording differs, so this is not a perfectly isolated causal ablation. No independent-regeneration arm, repeats or new held-out tasks.');
 followChart(s,'f1',['B0','B3','C0'],1.12,'Mean edge F1');
 paragraphs(s,[`Exact C0: ${f.C0.exact}/15`,`Fixed: ${f.C0.fixed}`,`Broken: ${f.C0.broken}`],845,210,350,100,28);
 text(s,'Mean edge F1\nHigher is better',845,520,350,75,23);
}
{
 const s=slide('Coordinates-only editing preserves graph structure', 'Source: revised runs/layout_v2; failed format attempt preserved separately', 'The program reconstructs all nodes and edges from B0 and accepts only model coordinates. Semantic preservation is guaranteed by code, not learned. L3 cannot fix an incorrect B0 graph. Geometry proxies are not human readability. A different constrained schema and shorter output prevent attribution of cost changes to feedback quality alone.');
 text(s,'Mean geometry errors / diagram (lower is better)',64,148,1130,35,23);
 followChart(s,'geometry',['B0','B3','L3'],Math.max(1.2,f.B3.geometry*1.3,f.L3.geometry*1.3),'Mean geometry errors');
 paragraphs(s,[`Exact L3 v2: ${f.L3.exact}/15`,'Topology enforced','v1: 8 invalid scenes','16 failed-format calls'],845,194,350,88,27);
}
{
 const s=slide('A combined edit adds two wrong shortcuts', 'Affected subgraph: test_chain_01 B0/B3; saved scenes and visual feedback', 'Affected four-node subgraph only; the earlier start, receive and weigh stages are omitted. All three original unlabeled edges remain in B3. Added unsupported edges are Print shipping label to Parcel workflow complete labeled Yes and Attach shipping label to Parcel workflow complete labeled No. The quote is a saved model output, not ground truth; edge additions illustrate association, not a proved causal mechanism. All nodes, labels, route segments and arrowheads are editable native slide objects.');
 const RED='#C43737';
 const labels=['Print shipping label','Attach shipping label','Dispatch parcel','Parcel workflow complete'];
 const centers=[260,930];
 const ys=[215,295,375,455];
 text(s,'B0: correct subgraph',110,166,510,40,27,true);
 text(s,'B3: two added shortcuts',780,166,440,40,27,true);
 function line(x,y,w,h,color=NAVY,head=false,tail=false){return s.shapes.add({geometry:'connector',kind:'straight',position:{left:x,top:y,width:w,height:h},line:{fill:color,width:2.5},...(head?{head:{type:'triangle',width:'med',length:'med'}}:{}),...(tail?{tail:{type:'triangle',width:'med',length:'med'}}:{})});}
 centers.forEach(cx=>{
   labels.forEach((label,i)=>{const n=s.shapes.add({geometry:'rect',position:{left:cx-150,top:ys[i],width:300,height:50},fill:WHITE,line:{fill:NAVY,width:1.3}});n.text=label;n.text.style={fontSize:24,typeface:'Arial',color:NAVY,verticalAlignment:'middle',alignment:'center',insets:6};});
   for(let i=0;i<3;i++)line(cx,ys[i]+50,0,30,NAVY,false,true);
 });
 // Print -> End (Yes), routed around the right side.
 line(1080,240,100,0,RED); line(1180,240,0,240,RED); line(1080,480,100,0,RED,true,false);
 text(s,'Yes',1113,330,65,40,24,true,RED);
 // Attach -> End (No), routed around the left side.
 line(680,320,100,0,RED); line(680,320,0,160,RED); line(680,480,100,0,RED,false,true);
 text(s,'No',691,389,65,40,24,true,RED);
 text(s,'Saved critic excerpt: Attach shipping label is connected with both Parcel workflow complete and Print shipping label',64,551,1152,70,22);
}

{
 const s=slide('The follow-up remains exploratory and limited', 'Sources: dataset card; manifests; critic audit; pretrained model cards', 'Qwen: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF\nSmolVLM: https://huggingface.co/ggml-org/SmolVLM-256M-Instruct-GGUF\nDataset and analysis are original AI-assisted project artifacts. No training, human readability experiment, unseen topology test or stronger-critic comparison. Detailed audit and case evidence are in the supplemental report and analysis directory.');
 paragraphs(s,['5 development; 15 synthetic test tasks, 6-7 nodes.','One seed, one round, strict label matching.','C0/L3 are post-test; failed L3 format revised separately.','Pretrained models: Qwen2.5-3B and SmolVLM-256M.'],64,175,1130,100,28);
}
{
 const s=slide('Evaluate corrections and protect graph structure', 'Reproduction and saved demonstration: README.md; demo/followup.html', 'Original frozen result: criticism does not improve mean edge F1. Follow-up adds a descriptive feedback-free control and an enforceable topology constraint. Interpret measured C0 outcomes and geometry separately. Stronger critics, new held-out tasks, repetitions and human readability study remain future work. Original artifacts remain preserved. No public publication or submission is performed.');
 paragraphs(s,['Feedback did not improve the original CPU pilot.',`C0: ${f.C0.fixed} exact fixes, ${f.C0.broken} exact regressions.`,`L3 keeps B0 semantics; geometry ${f.B0.geometry.toFixed(2)} to ${f.L3.geometry.toFixed(2)} errors.`, 'Broader claims need new tasks and repeated evaluation.'],64,175,1130,99,28);
}
const candidatePath = path.join(buildDir, 'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const result = await finalizePresentation({workspaceDir, candidatePath, finalPath,
  pythonExecutable: RUNTIME_PYTHON,
  explicitTotalSlideCount: 10,
  requiredNativeTableOwnerSlides: [5], requiredNativeChartOwnerSlides: [4, 6, 7],
  materializeLiteralChartWorkbooks: true,
  fontPolicy: {basis: 'design', families: ['Arial']},
  integrityValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(SKILL_DIR, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit', '--require-native-table-slide', '5'],
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildDir, 'validation.json')});
// Preview the validated file, including its materialized native chart data.
const finalPresentation = await PresentationFile.importPptx(await FileBlob.load(finalPath));
for (const [index, s] of finalPresentation.slides.items.entries()) {
  const png = await finalPresentation.export({slide: s, format: 'png', scale: 1});
  await fs.writeFile(path.join(previewDir, `slide-${String(index + 1).padStart(2, '0')}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({finalPath: result.finalPath, receiptPath: result.receiptPath, previewDir, slides: 10, label}, null, 2));
