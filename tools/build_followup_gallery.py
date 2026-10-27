"""Standalone offline experiment browser; all source text is escaped."""

import base64
import html
import json
from pathlib import Path


def build_gallery(run_dir, followup_dir, output, layout_dir=None):
    run_dir, followup_dir, output = Path(run_dir), Path(followup_dir), Path(output)
    layout_dir = Path(layout_dir) if layout_dir else followup_dir
    tasks = json.loads((run_dir/"tasks_public.json").read_text(encoding="utf-8"))
    records = []
    for task in tasks:
        record = {"task": task, "arms": {}}
        for mode in ("B0", "B1", "B2", "B3", "C0", "L3"):
            folder = (layout_dir if mode == "L3" else followup_dir if mode == "C0" else run_dir)/task["id"]/mode
            arm = {"available": False}
            status = folder/"status.json"
            if status.exists():
                arm["status"] = json.loads(status.read_text(encoding="utf-8"))
                image = folder/"chart.png"
                if image.exists():
                    arm["available"] = True
                    arm["image"] = "data:image/png;base64,"+base64.b64encode(image.read_bytes()).decode("ascii")
                    for ext in ("json", "svg"):
                        p = folder/("scene.json" if ext == "json" else "chart.svg")
                        if p.exists():
                            arm[ext] = p.read_text(encoding="utf-8")
                feedback = folder/"program_feedback.json"
                if feedback.exists():
                    arm["program"] = json.loads(feedback.read_text(encoding="utf-8"))
            record["arms"][mode] = arm
        vp = run_dir/task["id"]/"visual"/"feedback.json"
        record["visual"] = json.loads(vp.read_text(encoding="utf-8"))["text"] if vp.exists() else None
        records.append(record)
    payload = json.dumps(records, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    title = html.escape(run_dir.name + " + post-test " + followup_dir.name)
    page = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlowRefine — Offline Results</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#223047;font:15px/1.5 system-ui,sans-serif}
header{background:#17273e;color:white;padding:20px 28px}h1{margin:0;font-size:24px}
main{max-width:1500px;margin:auto;padding:22px}select,button{font:inherit;border:1px solid #bac6d7;border-radius:7px;padding:9px 13px;background:white;color:#223047}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.prompt,.feedback{background:white;border:1px solid #dde3eb;border-radius:10px;padding:16px;margin:16px 0;white-space:pre-wrap}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:white;border:1px solid #dde3eb;border-radius:10px;padding:16px}
.card h2{margin:0 0 10px;font-size:18px}.card img{width:100%;height:auto;max-height:920px;object-fit:contain;object-position:top}
.small{font-size:13px;color:#65748a}.issues{margin-top:12px;font-size:13px;white-space:pre-wrap}.downloads{display:flex;gap:8px;margin:8px 0}summary{cursor:pointer;font-weight:600}
@media(max-width:750px){.pair{grid-template-columns:1fr}main{padding:12px}}
</style><header><h1>FlowRefine</h1><div>Programmatic and Visual Feedback for Flowchart Refinement</div>
<div class="small" style="color:#c5d6ec">Saved real inference · CPU · RUN_TITLE</div></header>
<main><div class="controls"><label>Task <select id="task"></select></label><label>Compare <select id="mode"><option value="B1">B1 — Programmatic</option><option value="B2">B2 — Visual</option><option value="B3" selected>B3 — Combined</option><option value="C0">C0 - No-feedback edit (post-test)</option><option value="L3">L3 - Coordinates only (post-test)</option></select></label></div>
<div id="prompt" class="prompt"></div><div class="pair"><div class="card" id="before"></div><div class="card" id="after"></div></div>
<details class="feedback"><summary>Shared VLM feedback</summary><div id="visual"></div></details>
<p class="small">B0-B3 are the frozen test. C0/L3 are exploratory post-test additions using the same saved B0 and critique. L3 shows the revised layout_v2 schema: the first coordinate format failed on 8 saved tasks (16 logged calls); failures remain in runs/followup_v1 and are counted separately in analysis. One interrupted response has unknown cost. L3 preserves topology in code and cannot repair baseline logic. The viewer replays saved results without a GPU or network. Missing modes are marked unavailable. The VLM feedback is a model output and may contain errors.</p></main>
<script>const DATA=PAYLOAD;
const $=id=>document.getElementById(id);const names={B0:'B0 — Initial generation',B1:'B1 — Programmatic feedback',B2:'B2 — Visual feedback',B3:'B3 — Combined feedback',C0:'C0 — No-feedback edit (post-test)',L3:'L3 — Coordinates only (post-test)'};
DATA.forEach((r,i)=>{let o=document.createElement('option');o.value=i;o.textContent=r.task.id+' · '+r.task.family;$('task').append(o)});
function download(text,type,name){const blob=new Blob([text],{type});let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function card(el,arm,mode,task){el.replaceChildren();let h=document.createElement('h2');h.textContent=names[mode];el.append(h);
if(!arm.available){let p=document.createElement('p');p.textContent=arm.status?'Invalid scene: '+JSON.stringify(arm.status):'This mode has not been executed.';el.append(p);return}
let ds=document.createElement('div');ds.className='downloads';for(let ext of ['svg','json']){if(!arm[ext])continue;let b=document.createElement('button');b.textContent='Download '+ext.toUpperCase();b.onclick=()=>download(arm[ext],ext==='svg'?'image/svg+xml':'application/json',task+'_'+mode+'.'+ext);ds.append(b)}el.append(ds);
let im=document.createElement('img');im.src=arm.image;im.alt=names[mode]+' for '+task;el.append(im);let p=document.createElement('div');p.className='issues';p.textContent='Programmatic findings: '+(arm.program||[]).length+'\n'+(arm.program||[]).map(x=>x.code+': '+x.message).join('\n');el.append(p)}
function show(){if(!DATA.length)return;let r=DATA[Number($('task').value)||0],mode=$('mode').value;$('prompt').textContent=r.task.prompt;card($('before'),r.arms.B0,'B0',r.task.id);card($('after'),r.arms[mode],mode,r.task.id);$('visual').textContent=mode==='C0'?'C0 does not receive this saved VLM critique. It edits the original request and B0 without external feedback.':(r.visual||'Visual critique unavailable.')}
$('task').onchange=show;$('mode').onchange=show;show();
</script></html>'''
    page = page.replace("RUN_TITLE", title).replace("PAYLOAD", payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    return str(output)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(build_gallery(root / "runs/test_v1", root / "runs/followup_v1", root / "demo/followup.html", root / "runs/layout_v2"))
