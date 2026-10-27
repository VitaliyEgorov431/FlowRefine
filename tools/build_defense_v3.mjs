import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const skill='C:/Users/User/.codex/plugins/cache/openai-primary-runtime/presentations/26.1022.11436/skills/presentations';
const runtime='C:/Users/User/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES ||= path.join(runtime,'node/node_modules');
const {importRuntimeModule}=await import(pathToFileURL(path.join(skill,'container_tools/runtime_helpers.mjs')).href);
const {FileBlob,PresentationFile}=await importRuntimeModule('@oai/artifact-tool');
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const source=path.join(root,'submission/examples_v2/FlowRefine_Defense_Examples.pptx');
const out=path.join(root,'submission/defense_v3',process.argv[2]||'FlowRefine_Defense_EN.pptx');
const build=path.join(root,'.deck_build',`defense_v3_${Date.now()}`);
const preview=path.join(build,'renders');
await Promise.all([fs.mkdir(preview,{recursive:true}),fs.mkdir(path.dirname(out),{recursive:true})]);
const p=await PresentationFile.importPptx(await FileBlob.load(source));
await fs.writeFile(path.join(build,'source-inspect.json'),JSON.stringify(await p.inspect({kind:'slide,textbox,layout',maxChars:70000}),null,2));
const originals=[...p.slides.items];
const appendix1=originals[3].duplicate(),appendix2=originals[10].duplicate();
// Retain the source theme and two saved-example slides. Rebuild changed content
// in the imported source slide canvases rather than rasterizing slide content.
p.slides.keep([...originals.slice(0,11),appendix1,appendix2].map(s=>p.slides.items.findIndex(x=>x.id===s.id)));
const main=originals.slice(0,11);
for(const [i,s] of [...main,appendix1,appendix2].entries())s.moveTo(i);
for(const s of main){s.shapes.deleteAll();for(const kind of ['images','charts','tables'])for(const x of [...s[kind].items])s[kind].deleteById(x.id);}
const N='#1F4E79',B='#2E75B6',R='#C43737',W='#FFFFFF';
function txt(s,t,x,y,w,h,size=28,bold=false,color=N){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={fontSize:size,typeface:'Arial',color,bold,insets:0,verticalAlignment:'top'};return a;}
function setup(i,title,src,notes){const s=main[i-1];s.background.fill=W;txt(s,title,64,46,1152,102,40,true);txt(s,src,64,638,1152,30,16);txt(s,`FlowRefine   CPU pilot and exploratory GPU comparison   ${i}`,64,675,1152,23,16);s.speakerNotes.text=notes+'\n\n'+src;return s;}
function lines(s,arr,x=64,y=183,w=1150,step=99,size=29){arr.forEach((t,i)=>txt(s,t,x,y+step*i,w,step-12,size));}
function table(s,values,x,y,w,h,widths,size=26){const a=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){let k=a.getCell(r,c);k.fill=W;k.text.style={fontSize:size,typeface:'Arial',color:N,bold:r===0,insets:12};}return a;}
function chart(s,categories,series,max){const c=s.charts.add('bar',{position:{left:64,top:190,width:750,height:405},categories,series,hasLegend:series.length>1,titlePlacement:'none',barOptions:{direction:'column',grouping:'clustered',gapWidth:90},xAxis:{textStyle:{fontSize:24,fill:N},majorGridlines:null},yAxis:{min:0,max,numberFormatCode:'0',textStyle:{fontSize:23,fill:N},majorGridlines:{fill:'#DCE6F1',width:1}},legend:{position:'bottom',textStyle:{fontSize:23,fill:N}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0',textStyle:{fontSize:24,fill:N,bold:true}},chartFill:W,plotAreaFill:W});applyPresentationChartFont(c,{fontFamily:'Arial'});return c;}
async function pic(s,rel,crop,frame,alt){const bytes=await fs.readFile(path.join(root,rel));const [x,y,w,h]=crop;const k=Math.min(frame.width/w,frame.height/h);s.images.add({blob:new Uint8Array(bytes),contentType:'image/png',fit:'cover',alt,position:{left:frame.left+(frame.width-w*k)/2,top:frame.top+(frame.height-h*k)/2,width:w*k,height:h*k},crop:{left:x/790,top:y/1440,right:(790-x-w)/790,bottom:(1440-y-h)/1440}});}
let s=setup(1,'FlowRefine','Generative AI final project   25 October 2026','Моя основная специальность — нефтегазовое дело. Поэтому мне интересны инструменты, которые помогают описывать производственные процессы и проверять последовательность действий. Здесь я проверяю техническую основу такого инструмента на общих синтетических задачах, а не на реальных нефтегазовых регламентах.');
txt(s,'Local generation and verification\nof editable process flowcharts',64,184,1152,155,49,true);
txt(s,'Motivation: process documentation\nin my oil and gas engineering field',64,409,1152,104,32);
txt(s,'General synthetic tasks, with CPU and GPU experiments',64,555,1152,48,26);
s=setup(2,'Can feedback improve a generated flowchart?','Sources: frozen protocol and original task descriptions','Вопрос: можно ли улучшить правильность схемы за один раунд критики и исправления? Система создаёт редактируемый граф. Я проверяю точное соответствие узлов и направленных подписанных связей эталону. Картинка сама по себе не доказывает правильность процесса.');
txt(s,'Editable graph',64,180,550,40,30,true);
lines(s,['Nodes: steps and decisions','Directed edges: process logic','JSON scene rendered as SVG / PNG'],64,250,560,92,28);
txt(s,'Evaluation after one edit',720,180,480,40,30,true);
lines(s,['Exact graph match','Node F1 and edge F1','Separate geometry checks'],720,250,480,92,28);
s=setup(3,'The architecture separates generation and verification','Source: pipeline implementation and frozen_protocol.json','Текстовая модель получает описание процесса и создаёт JSON. Рендерер превращает его в изображение. Программный критик проверяет формальные ограничения, визуальная модель смотрит на изображение. Редактор получает исходный граф и выбранный вид обратной связи и делает одну попытку исправления. Эталон доступен только оцениванию.');
// Editable technical architecture diagram, intentionally native.
const boxes=[['Process description',64,190,330,75],['Text model\nJSON graph B0',470,190,330,90],['Renderer\nSVG and PNG',876,190,330,90],['Programmatic checks',64,355,330,80],['Visual critic',470,355,330,80],['Text editor\nB0 + selected feedback',876,355,330,80],['Saved graph and metrics',876,520,330,75]];
for(const [label,x,y,w,h] of boxes){const a=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:W,line:{fill:N,width:1.3}});a.text=label;a.text.style={fontSize:label.startsWith('Text editor')?24:26,typeface:'Arial',color:N,alignment:'center',verticalAlignment:'middle',insets:8};}
function connector(x,y,w,h,reverse=false){s.shapes.add({geometry:'connector',kind:'straight',position:{left:x,top:y,width:w,height:h},line:{fill:N,width:2},[reverse?'head':'tail']:{type:'triangle',width:'med',length:'med'}});}
connector(394,230,76,0);connector(800,230,76,0);
// JSON to checks via the left gutter, PNG to visual via the central gutter.
connector(420,267,50,0,true);connector(420,267,0,50);connector(229,317,191,0,true);connector(229,317,0,38);
connector(1035,280,0,33);connector(635,313,400,0,true);connector(635,313,0,42);
// Programmatic feedback routes under the visual critic, avoiding its text.
connector(229,435,0,44);connector(229,479,621,0);connector(850,395,0,84,true);connector(850,395,26,0);
connector(800,395,76,0);connector(1040,435,0,85);
txt(s,'B1 checks / B2 visual / B3 both',64,535,735,60,25,true);
s=setup(4,'Compact models test local execution on a CPU','Sources: model manifests, dataset card, frozen protocol','Первый вариант сознательно ориентирован на локальный запуск с ограниченными ресурсами. Это компактные модели под доступное оборудование, а не утверждение, что выбраны самые слабые существующие модели. На разработке переходил от 1.5B к 3B. Основной тест: пять цепочек, пять развилок и пять циклов. Всего 20 задач с разработкой, без нефтегазовой валидации.');
table(s,[['Role / control','Original CPU configuration'],['Generator and editor','Qwen2.5-3B-Instruct, Q4_K_M'],['Visual critic','SmolVLM-256M-Instruct, Q8_0'],['Data','5 development + 15 synthetic test tasks'],['Comparison','Same saved B0, one correction round'] ],64,177,1150,368,[380,770],26);
txt(s,'Office-PC feasibility was the motivation. No hardware-wide benchmark.',64,574,1150,43,25,true);
s=setup(5,'The original feedback modes reduce exact correctness','Source: analysis/test_v1/aggregate.json, all 15 test tasks','Исходная генерация дала 11 точных графов из 15. Программная обратная связь сохранила это число. Визуальная снизила до девяти, совместная до семи. Это важный отрицательный результат: наличие критика ещё не гарантирует полезного исправления. Считается семантическая правильность, а не впечатление от картинки.');
txt(s,'Exactly correct graphs out of 15',64,148,750,37,25);
chart(s,['B0','B1','B2','B3'],[{name:'CPU experiment',values:[11,11,9,7],fill:B}],15);
lines(s,['B0  Initial','B1  Checks','B2  Visual critique','B3  Both'],860,208,345,76,27);
txt(s,'No edit fixes an incorrect B0 to exact correctness',860,521,345,88,26,true);
s=setup(6,'The GPU experiment replaces the visual critic','Sources: gpu_vlm_v1 manifest and execution metadata','Дальше проверил, изменится ли результат с более крупным визуальным критиком. Поменял только этот компонент на Qwen2.5-VL-3B в FP16. Текстовый генератор и редактор остались прежними, а исходные изображения и контрольные результаты переиспользованы. Вместе с моделью менялись её бэкенд и обработка изображения, поэтому это сравнение конфигураций, а не чистый эффект числа параметров.');
table(s,[['Component','GPU comparison'],['Visual critic','Qwen2.5-VL-3B-Instruct, FP16'],['Hardware','RTX 3060, 12 GB VRAM'],['Measured peak allocation','7.33 GiB'],['Reused controls','Same B0 / B1, text editor and 15 tasks']],64,177,1150,370,[380,770],26);
txt(s,'Exploratory rerun after viewing the original test results',64,577,1150,42,25,true);
s=setup(7,'The larger critic lowers downstream graph scores','Sources: test_v1 and gpu_vlm_v1 aggregate.json, same 15 saved tasks','После замены критика в обоих режимах осталось по пять точных схем из пятнадцати. Средний Edge F1 снизился примерно с 0.912 до 0.810 для B2 и с 0.899 до 0.810 для B3. В каждом новом режиме по одному невалидному результату, они включены в расчёт с нулём. Это качество всей цепочки критик плюс редактор, а не отдельный экзамен визуальной модели.');
txt(s,'Exactly correct graphs out of 15',64,148,750,37,25);
chart(s,['B2 visual','B3 combined'],[{name:'SmolVLM-256M',values:[9,7],fill:N},{name:'Qwen-VL-3B',values:[5,5],fill:B}],15);
txt(s,'Mean edge F1',860,190,345,45,29,true);
lines(s,['B2   0.912 to 0.810','B3   0.899 to 0.810','New invalid: 1/15 each'],860,263,345,86,26);
txt(s,'System outcome, including the unchanged text editor',860,525,345,85,25,true);
s=setup(8,'False criticism removes a required start node','Source: test_chain_01, saved B0, GPU visual critique and new B3','В конкретном примере исходная схема полностью правильна. Критик предлагает удалить обязательное начало как избыточное. В последующем B3 редактор действительно убирает этот узел, и точное соответствие теряется. Edge F1 падает с 1 до 0.909. Это наблюдаемая связь между замечанием и правкой. Без отдельного опыта с удалением только этого замечания нельзя строго приписать ему весь причинный эффект.');
txt(s,'B0: required start',64,156,390,36,27,true);txt(s,'New B3: start removed',472,156,390,36,27,true);
await pic(s,'runs/test_v1/test_chain_01/B0/chart.png',[250,10,300,300],{left:64,top:205,width:340,height:345},'Actual saved initial chain start and first stages');
await pic(s,'snapshots/gpu_return_20261025_121148/contents/runs/gpu_vlm_v1/test_chain_01/B3/chart.png',[250,10,300,300],{left:472,top:205,width:340,height:345},'Actual GPU B3 top of diagram without required start');
txt(s,'Saved critic instruction',872,182,330,65,27,true);
txt(s,'“Remove the\n\"Parcel workflow begins\"\nbox as it is redundant.”',872,267,330,150,26,false,R);
txt(s,'Exact: yes to no\nEdge F1: 1.000 to 0.909',872,469,330,100,26,true);
s=setup(9,'The evidence points to unreliable feedback and editing','Sources: saved critic outputs, edited graphs and validity errors','Проверяемое наблюдение: неверное замечание соответствует вредной правке. Возможное объяснение: общая визуально-языковая модель не настроена специально на проверку графов и может убедительно описывать несуществующие ошибки. Свободное переписывание всего JSON даёт редактору возможность испортить правильные части. Сам редактор не усиливался и тоже может ограничивать результат. Но этот опыт не изолирует вклад каждого механизма и не доказывает, что крупные модели вообще хуже.');
txt(s,'Observed',64,177,500,42,30,true);
lines(s,['False instruction in a saved critique','Corresponding deletion in the edit','A valid loop fix remains unexecuted'],64,250,530,98,27);
txt(s,'Plausible explanations',690,177,515,42,30,true);
lines(s,['General VLM lacks graph calibration','Full-graph rewriting permits regressions','The same small editor may limit gains'],690,250,515,98,27);
txt(s,'One rerun cannot isolate these mechanisms or rank model families',64,574,1150,43,25,true);
s=setup(10,'Local execution works, while correction remains unreliable','Project conclusions and next experiment proposal','Основной итог: локальная генерация редактируемых схем технически работает. Однако автоматическую коррекцию пока нельзя считать надёжной. Замена только визуального критика в этом тесте не помогла. Следующий шаг — проверять замечания до применения, ограничивать правки и отклонять ухудшения. Для выводов об отрасли нужны новые задачи по реальным процессам, а для сравнения моделей — повторения и независимый тест. На этом завершаю доклад.');
lines(s,['Local editable flowchart generation is feasible.','A larger critic alone did not improve this pipeline.','Next: verify critiques and constrain accepted edits.','New held-out tasks and repeated runs remain necessary.'],64,183,1150,98,29);
s=setup(11,'References and experiment sources','Appendix A   Source files and official model cards','Справочный слайд для вопросов. Модели предобученные, обучение в проекте не выполнялось. Нефтегазовое применение служит мотивацией, эксперимент использует общие синтетические задачи.');
lines(s,['Qwen2.5-3B-Instruct-GGUF: huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF','SmolVLM: huggingface.co/ggml-org/SmolVLM-256M-Instruct-GGUF','Qwen2.5-VL-3B: huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct','Original results: runs/test_v1 and analysis/test_v1','GPU results: snapshots/gpu_return_20261025_121148/contents/runs/gpu_vlm_v1'],64,172,1150,83,24);
for(const [j,a] of [appendix1,appendix2].entries()){for(const sh of a.shapes.items){if(sh.text?.replace){const oldText=sh.text.toString();if(/^FROZEN TEST \+ EXPLORATORY FOLLOW-UP\s+test_v1\s+\d+$/.test(oldText.trim()))sh.text=`Appendix ${j?'C':'B'}   Saved original CPU example   ${12+j}`;}}}
const fullTalk=await fs.readFile(path.join(root,'submission/defense_v3/DEFENSE_SPEECH_RU.md'),'utf8');
const talks={};
for(const m of fullTalk.matchAll(/^##\s+(\d+)\.[^\n]*\n([\s\S]*?)(?=^##\s|$(?![\s\S]))/gm))talks[m[1]]=m[2].trim();
for(let i=0;i<10;i++){const t=talks[String(i+1)];if(t)main[i].speakerNotes.text=t+'\n\n'+main[i].speakerNotes.text.split('\n\n').at(-1);}
const candidate=path.join(build,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:out,pythonExecutable:path.join(runtime,'python/python.exe'),explicitTotalSlideCount:13,requiredNativeTableOwnerSlides:[4,6],requiredNativeChartOwnerSlides:[5,7],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'reference',families:['Arial'],referencePath:source,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex')},integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','4','--require-native-table-slide','6'],verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
const final=await PresentationFile.importPptx(await FileBlob.load(out));
for(const [i,a] of final.slides.items.entries()){await fs.writeFile(path.join(preview,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await(await final.export({slide:a,format:'png',scale:1})).arrayBuffer()));}
await fs.writeFile(path.join(build,'final-inspect.json'),JSON.stringify(await final.inspect({kind:'slide,textbox,chart,table,notes',maxChars:100000}),null,2));
console.log(JSON.stringify({output:out,build,preview,slides:13}));
