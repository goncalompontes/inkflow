"""Save intermediate visual artifacts and a standalone interactive inspector."""
from __future__ import annotations

import base64
from html import escape
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from .pipeline import Analysis


def image_data(image: np.ndarray) -> str:
    im = Image.fromarray(image.astype(np.uint8))
    buf = BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def save_image(path: Path, image: np.ndarray):
    Image.fromarray(image.astype(np.uint8)).save(path)


def mask_rgb(mask: np.ndarray) -> np.ndarray:
    return np.where(mask[..., None], np.array([24, 34, 46]), np.array([255, 255, 255])).astype(np.uint8)


def overlay(base: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], alpha=.78) -> np.ndarray:
    arr = base.astype(float).copy()
    arr[mask] = arr[mask] * (1 - alpha) + np.array(color) * alpha
    return arr.clip(0, 255).astype(np.uint8)


def svg_graph(a: Analysis) -> str:
    w, h = a.grayscale.shape[1], a.grayscale.shape[0]
    paths = []
    for edge in a.edges:
        coords = edge["points"]
        if len(coords) < 2:
            continue
        d = "M " + " L ".join(f"{x},{y}" for x, y in coords)
        color = "#f59e0b" if edge["ambiguous"] else "#2563eb"
        paths.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.9" stroke-linejoin="round" stroke-linecap="round" data-edge="{edge["id"]}"><title>Edge {edge["id"]}: {edge["length_px"]}px; order unknown</title></path>')
    for node in a.nodes:
        x, y = node["point"]
        color = "#ef4444" if node["kind"] == "junction" else "#16a34a"
        paths.append(f'<circle cx="{x}" cy="{y}" r="2.7" fill="{color}" stroke="white" stroke-width=".6"><title>Node {node["id"]}: {node["kind"]}</title></circle>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">' + "".join(paths) + "</svg>"


def render_reconstruction(a: Analysis) -> np.ndarray:
    # Width-aware centerline reconstruction. Still not historically faithful ink.
    return mask_rgb(a.reconstruction)


def save_report(a: Analysis, output: Path, *, input_path: str, options: dict) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    stages = {
        "source": a.source,
        "grayscale": np.repeat(a.grayscale[..., None], 3, axis=2),
        "threshold": mask_rgb(a.mask),
        "cleaned": mask_rgb(a.cleaned),
        "distance": np.stack([np.minimum(a.distance * 35, 255), np.minimum(a.distance * 15, 255), np.minimum(a.distance * 9, 255)], axis=-1).astype(np.uint8),
        "components": overlay(a.source, a.cleaned, (18, 150, 110), .62),
        "skeleton": overlay(a.source, a.skeleton, (222, 44, 69), .95),
        "reconstruction": render_reconstruction(a),
    }
    stages["graph"] = stages["skeleton"]
    discrepancy = a.source.copy()
    discrepancy[a.cleaned & ~a.reconstruction] = [220, 44, 69]
    discrepancy[a.reconstruction & ~a.cleaned] = [38, 99, 235]
    stages["difference"] = discrepancy
    for name, arr in stages.items():
        save_image(output / f"{name}.png", arr)
    (output / "graph.svg").write_text(svg_graph(a), encoding="utf-8")
    manifest = {"schema_version": "0.1-prototype", "source_path": str(input_path),
                "options": options, "diagnostics": a.diagnostics,
                "components": a.components, "nodes": a.nodes, "edges": a.edges,
                "stage_files": {name: f"{name}.png" for name in stages},
                "graph_file": "graph.svg"}
    (output / "run.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # Self-contained report: can be opened directly without a server.
    encoded = {name: image_data(img) for name, img in stages.items()}
    html = make_html(encoded, svg_graph(a), manifest)
    (output / "index.html").write_text(html, encoding="utf-8")
    return output / "index.html"


def make_html(images: dict[str, str], graph: str, manifest: dict) -> str:
    payload = json.dumps({"images": images, "graph": graph, "run": manifest}).replace("<", "\\u003c")
    title = escape(Path(manifest["source_path"]).name)
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>InkFlow Inspector — """ + title + """</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color-scheme:dark;background:#10141c;color:#e8edf4}
*{box-sizing:border-box}body{margin:0;padding:22px;max-width:1500px;margin:auto}
h1{margin:0 0 4px;font-size:25px}p{color:#9aa8b8}header{margin-bottom:18px}
.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:16px}
select,button,input{accent-color:#5fa8ff;background:#202c3c;color:#e8edf4;border:1px solid #405067;padding:8px;border-radius:7px}
label{font-size:13px;color:#b8c6d7}input[type=range]{padding:0}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:18px}
.view{position:relative;background:#fff;border-radius:8px;overflow:auto;min-height:180px;max-height:75vh}
canvas{display:block;width:100%;height:auto;image-rendering:auto}
.view svg{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none}
aside{background:#1b2431;border:1px solid #334152;border-radius:8px;padding:15px;max-height:75vh;overflow:auto}
aside h2{font-size:16px;margin-top:0}.metric{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #344054;font-size:13px}
.metric strong{font-variant-numeric:tabular-nums}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:11px}
.legend{font-size:12px;color:#9aa8b8;margin-top:12px}.dot{display:inline-block;width:9px;height:9px;border-radius:100%;margin-right:4px}
footer{margin-top:15px;font-size:12px;color:#a7b1bf}
@media(max-width:800px){.layout{grid-template-columns:1fr}aside{max-height:40vh}}
</style></head>
<body><header><h1>InkFlow — visual pipeline inspector</h1>
<p>""" + title + """ · Offline centerline reconstruction baseline. No historical stroke sequence or pressure is inferred.</p></header>
<div class="controls"><label>Stage <select id="stage"></select></label>
<label>Overlay opacity <input id="opacity" type="range" min="0" max="100" value="80"></label>
<label><input id="nodes" type="checkbox" checked> Graph annotations</label>
<button id="previous">Previous</button><button id="next">Next</button>
<button id="download">Download graph JSON</button>
</div>
<div class="layout"><div class="view"><canvas id="canvas"></canvas><div id="graph"></div></div>
<aside><h2>Run diagnostics</h2><div id="metrics"></div><h2>Stage notes</h2><p id="notes"></p>
<div class="legend"><span class="dot" style="background:#16a34a"></span>endpoint
<span class="dot" style="background:#ef4444"></span>junction<br>
<span class="dot" style="background:#2563eb"></span>unambiguous segment
<span class="dot" style="background:#f59e0b"></span>junction-adjacent segment</div>
<h2>Selected pixel</h2><pre id="pixel">Click the image to inspect a pixel coordinate.</pre></aside></div>
<footer>Generated locally, with all assets embedded. Space/arrow keys change stages. The graph is an undirected topology hypothesis, not a stroke-order reconstruction.</footer>
<script>
const data = """ + payload + """;
const stages = ['source','grayscale','threshold','cleaned','distance','components','skeleton','graph','reconstruction','difference'];
const notes = {
source:'Original rescaled color image; check rotation, perspective and lighting.',
grayscale:'Luminance image; preserve source for later paper/ink color modeling.',
threshold:'Global Otsu binary mask. Thin/faint marks and uneven illumination may require adaptive segmentation.',
cleaned:'Connected-component filtering. Tiny dots and punctuation may be removed if minimum area is too high.',
distance:'Approximate chamfer distance of ink to background, shown as a heatmap. Larger values indicate thicker ink.',
components:'Cleaned ink over source. Components are contiguous ink regions, not necessarily characters.',
skeleton:'Zhang–Suen pixel centerlines in red. Examine gaps, spurs, junctions and changes in topology.',
graph:'Compressed centerline graph; red junctions / green endpoints, gold edges touch uncertain junctions.',
reconstruction:'Centerline candidates rendered with locally estimated width. This is an approximation, not recovered pen pressure or true dynamics.',
difference:'Difference against cleaned ink: red marks missed ink; blue marks excess reconstructed ink. The IoU metric measures pixel overlap.'
};
const canvas=document.getElementById('canvas'),ctx=canvas.getContext('2d'),select=document.getElementById('stage'),overlay=document.getElementById('opacity'),graph=document.getElementById('graph');
for(let i=0;i<stages.length;i++){const opt=document.createElement('option');opt.value=stages[i];opt.textContent=(i+1)+'. '+stages[i];select.append(opt)}
const sources={};for(const [k,url] of Object.entries(data.images)){const image=new Image();image.src=url;sources[k]=image;image.onload=draw}
const svgMarkup = data.graph.replace('<svg ','<svg id="overlay-svg" ');
graph.innerHTML=svgMarkup;
function draw(){
 const name=select.value||'source',src=sources.source,dst=sources[name];
 if(!src?.complete||!dst?.complete)return;
 canvas.width=dst.naturalWidth;canvas.height=dst.naturalHeight;
 ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(src,0,0);
 ctx.globalAlpha=Number(overlay.value)/100;ctx.drawImage(dst,0,0);ctx.globalAlpha=1;
 const show=document.getElementById('nodes').checked && ['graph','skeleton'].includes(name);
 graph.style.display=show?'block':'none';document.getElementById('notes').textContent=notes[name];
}
select.onchange=draw;overlay.oninput=draw;document.getElementById('nodes').onchange=draw;
function step(n){select.selectedIndex=(select.selectedIndex+n+stages.length)%stages.length;draw()}
document.getElementById('previous').onclick=()=>step(-1);document.getElementById('next').onclick=()=>step(1);
window.addEventListener('keydown',e=>{if(['INPUT','SELECT','BUTTON'].includes(document.activeElement.tagName))return;if(e.key==='ArrowRight'||e.key===' ')step(1);if(e.key==='ArrowLeft')step(-1)});
document.getElementById('download').onclick=()=>{const blob=new Blob([JSON.stringify(data.run,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='run.json';a.click();URL.revokeObjectURL(a.href)};
canvas.onclick=e=>{const r=canvas.getBoundingClientRect();const x=Math.floor((e.clientX-r.left)*canvas.width/r.width),y=Math.floor((e.clientY-r.top)*canvas.height/r.height);
const distances=data.run.nodes.map(n=>({id:n.id,kind:n.kind,d:Math.hypot(x-n.point[0],y-n.point[1])})).sort((a,b)=>a.d-b.d);
document.getElementById('pixel').textContent=JSON.stringify({x,y,nearest_node:distances[0]||null},null,2)};
const metrics=document.getElementById('metrics');
for(const [key,val] of Object.entries(data.run.diagnostics)){const d=document.createElement('div');d.className='metric';const label=document.createElement('span');label.textContent=key.replaceAll('_',' ');const value=document.createElement('strong');value.textContent=typeof val==='object'?JSON.stringify(val):String(val);d.append(label,value);metrics.append(d)}
draw();
</script></body></html>"""
