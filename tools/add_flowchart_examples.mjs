/** Insert three evidence slides into the accepted deck, retaining imported slides. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const skill='C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1022.11436/skills/presentations';
const runtime='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES ||= path.join(runtime,'node/node_modules');
const {importRuntimeModule}=await import(pathToFileURL(path.join(skill,'container_tools/runtime_helpers.mjs')).href);
const {FileBlob,PresentationFile}=await importRuntimeModule('@oai/artifact-tool');
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const source=path.join(root,'submission/followup_v1/FlowRefine_Defense.pptx');
const output=path.join(root,process.argv[2]||'submission/examples_v1/FlowRefine_Defense_Examples.pptx');
const build=path.join(root,'.deck_build',`examples_${Date.now()}`);
const preview=path.join(root,'submission/qa_slides',path.basename(output,'.pptx'));
if(await fs.stat(output).catch(()=>null))throw Error('Use a new output filename');
await Promise.all([fs.mkdir(build,{recursive:true}),fs.mkdir(preview,{recursive:true}),fs.mkdir(path.dirname(output),{recursive:true})]);
const sourceBytes=await fs.readFile(source);
const presentation=await PresentationFile.importPptx(await FileBlob.load(source));
const original=[...presentation.slides.items];
if(original.length!==10)throw Error('Expected accepted ten-slide source deck');
await fs.writeFile(path.join(build,'before.json'),JSON.stringify(await presentation.inspect({kind:'slide,textbox,chart,table,layout',maxChars:50000}),null,2));
const NAVY='#1F4E79';
function text(s,t,x,y,w,h,size=27,bold=false){
 const shape=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 shape.text=t;shape.text.style={fontSize:size,typeface:'Arial',color:NAVY,bold,insets:0,verticalAlignment:'top'};return shape;
}
function add(title,sourceText,notes){
 const s=presentation.slides.add();s.background.fill='#FFFFFF';
 text(s,title,64,46,1152,100,41,true);
 text(s,sourceText,64,637,1152,34,16);
 s.speakerNotes.text=notes+'\nImages are unmodified saved PNGs. PowerPoint cropping removes only the indicated margins/stages. No new inference or reference-guided editing.\n'+sourceText;
 return s;
}
const evidence=[];
async function picture(s,relative,rect,frame,alt){
 const file=path.join(root,relative),bytes=await fs.readFile(file);
 const [x,y,w,h]=rect,scale=Math.min(frame.width/w,frame.height/h);
 const pos={left:frame.left+(frame.width-w*scale)/2,top:frame.top+(frame.height-h*scale)/2,width:w*scale,height:h*scale};
 s.images.add({blob:new Uint8Array(bytes),contentType:'image/png',alt,fit:'cover',position:pos,
  crop:{left:x/790,top:y/1440,right:(790-x-w)/790,bottom:(1440-y-h)/1440}});
 evidence.push({source:relative,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),crop_pixels:rect,position:pos});
}
const good=add('A generated branching process matches the request',
 'Source: test_branch_01/B0/chart.png and scene.json. Enlarged branch detail at right.',
 'Удачный исходный результат: ветвление заказа. Покажите весь граф слева и увеличенный фрагмент справа. Yes ведёт к Reserve item, No к Request replenishment; обе ветви объединяются в Notify customer. Node F1=1, edge F1=1, exact=1; zero hard geometry errors. This is a selected success, not a representative estimate. No improvement claim.');
text(good,'B0: complete saved output',64,150,410,36,25,true);
text(good,'Decision and merge, enlarged',510,150,700,36,25,true);
await picture(good,'runs/test_v1/test_branch_01/B0/chart.png',[0,10,790,965],{left:64,top:190,width:400,height:410},'Full saved correct order flowchart');
await picture(good,'runs/test_v1/test_branch_01/B0/chart.png',[0,350,790,450],{left:510,top:190,width:700,height:365},'Enlarged actual decision, Yes/No branches and merge');
text(good,'Edge F1 1.000    Exact match',510,565,700,40,27,true);
const regression=add('The saved edited image exposes the regression',
 'Source: test_chain_01/B0 and B3 chart.png. Detail: final three stages. Full subgraph on previous slide.',
 'Переход от предыдущего слайда: там явно показаны два добавленных ребра, здесь настоящий рендер системы. Обрезан верх графа, не исправлена исходная геометрия. В B3 лишние пути от Print shipping label и Attach shipping label к завершению; подписи Yes/No и стрелки накладываются на обычную цепочку. F1 1 to 6/7, exact 1 to 0. This is an illustrative post-hoc case, not proof of critic causality.');
text(regression,'B0: initial',90,151,380,35,27,true);
text(regression,'B3: combined feedback',510,151,680,35,27,true);
await picture(regression,'runs/test_v1/test_chain_01/B0/chart.png',[250,680,300,460],{left:78,top:193,width:360,height:392},'Actual initial final three parcel stages');
await picture(regression,'runs/test_v1/test_chain_01/B3/chart.png',[250,680,300,460],{left:485,top:193,width:360,height:392},'Actual edited parcel stages with erroneous Yes/No and crossing arrows');
text(regression,'Two extra\nshortcuts',900,250,300,90,30,true);
text(regression,'Extra routes\noverlap the\noriginal chain',900,375,300,140,27);
text(regression,'Edge F1: 1.000 to 0.857     Exact match: yes to no',64,587,1152,38,27,true);
const loop=add('A loop edit improves edge F1 but stays incorrect',
 'Source: test_loop_02/B0 and B3 chart.png. Detail: review, decision, loop and exit.',
 'Сложный цикл заявки: условие Application complete? должно отправлять No на Request missing documents с возвратом к Review application, а Yes на Submit application и далее к концу. B0 не содержит Submit to end и содержит лишний прямой выход из условия. B3 добавляет нужное Submit to end, но также неверное Submit to Request missing documents; прежний лишний выход остаётся. F1 0.857142857 to 0.875. Both graphs incorrect; geometry errors 1 to 1. Selected partial improvement, not a successful full correction. Crops omit initial start and Collect documents stages.');
text(loop,'B0: initial',64,151,540,35,27,true);
text(loop,'B3: combined feedback',662,151,550,35,27,true);
await picture(loop,'runs/test_v1/test_loop_02/B0/chart.png',[0,350,790,625],{left:64,top:193,width:545,height:360},'Saved initial loop detail with missing Submit-to-end connection');
await picture(loop,'runs/test_v1/test_loop_02/B3/chart.png',[0,350,790,625],{left:662,top:193,width:545,height:360},'Saved edited loop detail with added Submit-to-end and erroneous return');
text(loop,'Edge F1: 0.857 to 0.875',64,565,565,40,27,true);
text(loop,'Both graphs remain incorrect',662,565,550,40,27,true);
text(loop,'Submit application gains an exit and a wrong link to Request missing documents.',64,607,1152,26,21);
good.moveTo(3);
regression.moveTo(9);
loop.moveTo(10);
for(const [index,s] of presentation.slides.items.entries()){
 const oldIndex=original.findIndex(v=>v.id===s.id);
 const footer=`FROZEN TEST + EXPLORATORY FOLLOW-UP  test_v1  ${index+1}`;
 if(oldIndex>=0){for(const sh of s.shapes.items){if(sh.text?.replace)sh.text.replace(`FROZEN TEST + EXPLORATORY FOLLOW-UP  test_v1  ${oldIndex+1}`,footer);}}
 else text(s,footer,64,674,1152,23,17);
}
const candidate=path.join(build,'candidate.pptx');
await(await PresentationFile.exportPptx(presentation)).save(candidate);
// Import/export drops workbook relationships. Restore original chart parts byte-for-byte,
// retaining their existing lineage rather than creating replacement workbook snapshots.
execFileSync(path.join(root,'.venv/Scripts/python.exe'),[path.join(root,'tools/preserve_example_chart_parts.py'),source,candidate]);
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:output,pythonExecutable:path.join(runtime,'python/python.exe'),
 explicitTotalSlideCount:13,requiredNativeTableOwnerSlides:[6],requiredNativeChartOwnerSlides:[5,7,8],
 fontPolicy:{basis:'reference',families:['Arial'],referencePath:source,referenceSha256:crypto.createHash('sha256').update(sourceBytes).digest('hex')},
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','6'],
 verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
const final=await PresentationFile.importPptx(await FileBlob.load(output));
for(const [i,s] of final.slides.items.entries()){
 const png=await final.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(preview,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(path.join(build,'evidence.json'),JSON.stringify({source_deck:source,source_sha256:crypto.createHash('sha256').update(sourceBytes).digest('hex'),output,examples:[4,10,11],evidence},null,2));
console.log(JSON.stringify({output,preview,build,slides:13,examples:[4,10,11]}));
