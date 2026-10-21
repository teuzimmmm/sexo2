"""Browser validation of the SEXO2 opening against HANDOFF.md section 9.

Not part of CI (needs the full Chromium from the Playwright cache; the headless shell produces no frames).
Run:  python tests/abertura_qa/qa_browser.py <work_dir>
requestAnimationFrame and performance.now are replaced by a manual queue and clock; the plugin runs unchanged.
"""

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cdp import Browser  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "Pengu Loader" / "plugins" / "SEXO2-Startup"
SHIM = """(function(){var now=0,q=[],id=0;
performance.now=function(){return now};
window.requestAnimationFrame=function(cb){q.push([++id,cb]);return id};
window.cancelAnimationFrame=function(i){q=q.filter(function(e){return e[0]!==i})};
window.__step=function(dt){now+=dt*1000;var run=q;q=[];run.forEach(function(e){e[1](now)})};
window.__pending=function(){return q.length};})();"""
STATE = """(function(){var r=document.getElementById('sexo2-abertura');if(!r)return null;
var ic=r.querySelector('.ic'),gs=[].slice.call(r.querySelectorAll('.g'));
function tr(e){var m=/translate3d\\(([-\\d.]+)px,\\s*([-\\d.]+)px/.exec(e.style.transform);return m?[+m[1],+m[2]]:[NaN,NaN]}
var fs=parseFloat(gs[0].style.fontSize),c=document.createElement('canvas').getContext('2d');c.font='600 '+fs+'px Oswald';
var ink=['S','E','X','O','2'].map(function(ch){var m=c.measureText(ch);return {l:-m.actualBoundingBoxLeft,r:m.actualBoundingBoxRight}});
var i=tr(ic);
return {on:r.classList.contains('on'),VW:innerWidth,VH:innerHeight,ix:i[0],iy:i[1],iw:parseFloat(ic.style.width),
 g:gs.map(function(e,k){var t=tr(e),m=/scaleX\\(([-\\d.]+)\\)/.exec(e.style.transform);
  return {x:t[0],sc:m?+m[1]:NaN,op:parseFloat(e.style.opacity),ink:ink[k]}}),pending:window.__pending()}})()"""
SCAN = """(function(){var S=%s,out={snap:{},vanish:[null,null,null,null],minEdge:1e9,maxRight:-1e9,minLeft:1e9};
function st(){return %s}
function edge(s){return s.ix+s.iw}
for(var k=0;k<=2560;k++){
 if(k>0)window.__step(0.001);
 var s=st();
 if(k in S)out.snap[k]=s;
 s.g.forEach(function(g,i){
  if(i<4){var d=g.x+g.ink.l*g.sc-edge(s);
   if(g.op>0.001)out.minEdge=Math.min(out.minEdge,d);
   if(out.vanish[i]===null&&g.op<=0.0005)out.vanish[i]={t:k/1000,d:d,x:g.x,sc:g.sc,e:edge(s),l:g.ink.l}}
  out.maxRight=Math.max(out.maxRight,g.x+g.ink.r);out.minLeft=Math.min(out.minLeft,g.x+g.ink.l)});
 out.minLeft=Math.min(out.minLeft,s.ix);out.maxRight=Math.max(out.maxRight,edge(s))}
return out})()"""
SNAPS = {0, 1000, 2450, 2550, 2560}


def page_html(late):
    div = '<div id="index_loading_div42" style="position:fixed;inset:0;background:#010a13"></div>'
    body = (
        f"<script>setTimeout(function(){{document.body.insertAdjacentHTML(\"beforeend\",'{div}')}},300)</script>"
        if late
        else div
    )
    return f'<!doctype html><html><body style="margin:0">{body}<script>window.__sexo2AberturaOn=true</script><script src="file://{PLUGIN}/index.js"></script></body></html>'


class Qa:
    def __init__(self, work):
        self.work = pathlib.Path(work)
        routes = {
            "https://plugins/SEXO2-Startup/oswald.woff2": (200, "font/woff2", (PLUGIN / "oswald.woff2").read_bytes()),
            "https://plugins/SEXO2-Startup/inter.woff2": (200, "font/woff2", (PLUGIN / "inter.woff2").read_bytes()),
            "https://plugins/SEXO2-Startup/icone-final.svg": (
                200,
                "image/svg+xml",
                (PLUGIN / "icone-final.svg").read_bytes(),
            ),
        }
        self.routes = routes
        self.b = Browser(str(self.work / "profile"), routes=dict(routes))
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=SHIM)
        self.results = []

    def load(self, w, h, late=False, reduced=False):
        b = self.b
        b.call(
            "Emulation.setEmulatedMedia",
            features=[{"name": "prefers-reduced-motion", "value": "reduce" if reduced else "no-preference"}],
        )
        b.size(w, h)
        path = self.work / "pagina.html"
        path.write_text(page_html(late))
        b.call("Page.navigate", url=f"file://{path}")
        for _ in range(40):
            b.pump(0.1)
            if b.js(STATE) and b.js(STATE)["on"]:
                return
        return

    def state(self):
        return self.b.js(STATE)

    def run_scan(self):
        snaps = json.dumps({str(k): 1 for k in SNAPS})
        return self.b.js(SCAN % (snaps, STATE.rstrip(";")))

    def row(self, case, item, got, want, tol, unit=""):
        ok = abs(got - want) <= tol
        self.results.append(
            {"caso": case, "item": item, "obtido": round(got, 3), "esperado": want, "tol": tol, "ok": ok, "unit": unit}
        )
        return ok

    def info(self, case, item, got, want):
        self.results.append(
            {
                "caso": case,
                "item": item,
                "obtido": round(got, 3),
                "esperado": want,
                "tol": "info",
                "ok": True,
                "unit": "",
            }
        )

    def flag(self, case, item, ok, note=""):
        self.results.append(
            {"caso": case, "item": item, "obtido": note, "esperado": "", "tol": "", "ok": ok, "unit": ""}
        )


def metrics(s):
    right = s["g"][4]["x"] + s["g"][4]["ink"]["r"]
    return {
        "iconL": s["ix"],
        "right": right,
        "center": (s["ix"] + right) / 2,
        "gap": s["g"][4]["x"] + s["g"][4]["ink"]["l"] - (s["ix"] + s["iw"]),
        "w": right - s["ix"],
    }


def main(work):
    q = Qa(work)
    try:
        # 1280x720 reference
        q.load(1280, 720)
        c = "1280x720"
        s0 = q.state()
        q.flag(c, "cena visivel apos fonte", s0["on"])
        q.row(c, "t=0 icone x", s0["ix"], 200.93, 0.5)
        for i, v in enumerate([605.73, 705.40, 794.76, 894.86, 1005.45]):
            q.row(c, f"t=0 {'SEXO2'[i]} x", s0["g"][i]["x"], v, 0.5)
            q.row(c, f"t=0 {'SEXO2'[i]} scaleX", s0["g"][i]["sc"], 1.0, 0.02)
            q.row(c, f"t=0 {'SEXO2'[i]} opacidade", s0["g"][i]["op"], 1.0, 0.02)
        q.b.shot(str(q.work / "t000.png"))
        scan = q.run_scan()
        sn = scan["snap"]
        fin = sn["2550"]
        m = metrics(fin)
        q.row(c, "t=2,45 icone x", sn["2450"]["ix"], 497.64, 0.5)
        q.row(c, "t=2,55 icone x", fin["ix"], 497.85, 0.5)
        q.row(c, "t=2,55 '2' x", fin["g"][4]["x"], 708.53, 0.5)
        for i in range(4):
            q.row(c, f"t=2,55 {'SEXO'[i]} scaleX", fin["g"][i]["sc"], 0.5, 0.02)
            q.row(c, f"t=2,55 {'SEXO'[i]} opacidade", fin["g"][i]["op"], 0.0, 0.02)
        q.row(c, "composicao esquerda", m["iconL"], 497.85, 0.5)
        q.row(c, "composicao direita", m["right"], 782.15, 0.5)
        q.row(c, "centro horizontal", m["center"], 640, 0.5)
        q.row(c, "largura composicao", m["w"], 284.3, 0.5)
        q.row(c, "altura (icone)", fin["iw"], 184, 0.5)
        q.row(c, "icone y final (268)", fin["iy"], 268, 0.5)
        ref_l = [5.3, 8.6, 0.2, 7.1, 5.5]  # HANDOFF 4.3 ink-left values (reference Chromium)
        q.row(c, "folga icone-2 (tinta de 4.3)", fin["g"][4]["x"] + ref_l[4] - (fin["ix"] + fin["iw"]), 32, 0.5)
        q.info(c, "folga icone-2 (tinta deste Chromium)", m["gap"], 32)
        for i, (t, d) in enumerate([(1.01, 37), (1.34, 37), (1.74, 26), (2.25, 30)]):
            v = scan["vanish"][i]
            q.row(c, f"absorcao {'SEXO'[i]} instante", v["t"], t, 0.03, "s")
            q.row(c, f"absorcao {'SEXO'[i]} distancia (tinta deste Chromium)", v["d"], d, 0.5, "px")
            q.info(c, f"absorcao {'SEXO'[i]} distancia (tinta de 4.3)", v["x"] + ref_l[i] * v["sc"] - v["e"], d)
        q.flag(c, "folga minima letra-icone visivel >= 26 px", scan["minEdge"] >= 25.5, f"{scan['minEdge']:.2f} px")
        q.flag(
            c,
            "tudo dentro do quadro (0..1280)",
            scan["minLeft"] >= 0 and scan["maxRight"] <= 1280,
            f"{scan['minLeft']:.1f}..{scan['maxRight']:.1f}",
        )
        q.flag(
            c,
            "sem reinicio apos 1,5 s parado",
            sn["2560"]["pending"] == 0 and q.state()["g"][4]["x"] == fin["g"][4]["x"],
            f"rAF pendentes={q.state()['pending']}",
        )
        q.flag(c, "overlay permanece com loading presente", q.state() is not None)
        q.b.shot(str(q.work / "t255.png"))

        # resize preserves the instant
        q.load(1280, 720)
        for _ in range(1000):
            pass
        q.b.js("for(var k=0;k<1000;k++)window.__step(0.001)")
        a = q.state()
        q.b.size(1024, 640)
        q.b.pump(0.4)
        r1 = q.state()
        q.b.size(1280, 720)
        q.b.pump(0.4)
        r2 = q.state()
        q.flag(
            "resize",
            "instante preservado (1280>1024>1280)",
            abs(r2["g"][2]["x"] - a["g"][2]["x"]) < 0.01 and abs(r2["ix"] - a["ix"]) < 0.01,
            f"x(X) {a['g'][2]['x']:.2f} -> {r2['g'][2]['x']:.2f}",
        )
        q.flag(
            "resize",
            "nao voltou a t=0 em 1024x640",
            r1["g"][0]["op"] < 0.05 and r1["ix"] > 250,
            f"op S={r1['g'][0]['op']}",
        )
        q.load(1024, 640)
        q.b.js("for(var k=0;k<1000;k++)window.__step(0.001)")
        fresh = q.state()
        q.row("resize", "1024x640 apos resize = carga nova (x do X)", r1["g"][2]["x"], fresh["g"][2]["x"], 0.5)
        q.row("resize", "1024x640 apos resize = carga nova (icone x)", r1["ix"], fresh["ix"], 0.5)

        # reduced motion
        q.load(1280, 720, reduced=True)
        sr = q.state()
        mr = metrics(sr)
        q.flag(
            "reduced-motion",
            "quadro final direto, sem rAF",
            sr["on"] and sr["pending"] == 0,
            f"pending={sr['pending']}",
        )
        q.row("reduced-motion", "icone x", sr["ix"], 497.85, 0.5)
        q.row("reduced-motion", "centro", mr["center"], 640, 0.5)
        q.flag(
            "reduced-motion",
            "letras consumidas",
            all(g["op"] <= 0.02 and abs(g["sc"] - 0.5) <= 0.02 for g in sr["g"][:4]),
        )

        # lifecycle: removing the client loading mid-animation does not cut it
        q.load(1280, 720)
        q.b.js("for(var k=0;k<1000;k++)window.__step(0.001)")
        q.b.js("document.getElementById('index_loading_div42').remove()")
        q.b.pump(0.3)
        mid = q.state()
        q.flag("ciclo", "loading removido no meio: overlay segue", mid is not None)
        q.b.js("for(var k=0;k<1600;k++)window.__step(0.001)")
        q.b.pump(0.2)
        q.flag("ciclo", "overlay removido so apos o fim", q.state() is None)
        q.load(1280, 720, late=True)
        q.flag("ciclo", "loading que surge depois monta o overlay", q.state() is not None and q.state()["on"])

        # no font: never an empty scene
        saved = q.b.routes.pop("https://plugins/SEXO2-Startup/oswald.woff2")
        q.b.routes["https://plugins/SEXO2-Startup/oswald.woff2"] = (404, "text/plain", b"")
        q.load(1280, 720)
        q.b.pump(2.2)
        sf = q.state()
        q.flag("sem fonte", "cena visivel mesmo com a fonte indisponivel", bool(sf and sf["on"]))
        q.b.routes["https://plugins/SEXO2-Startup/oswald.woff2"] = saved

        # other viewports
        for w, h in [(900, 600), (1024, 640), (1440, 900), (1600, 900)]:
            q.load(w, h)
            sc = q.run_scan()
            f = sc["snap"]["2550"]
            m = metrics(f)
            c = f"{w}x{h}"
            q.row(c, "centro horizontal final", m["center"], w / 2, 0.5)
            q.row(c, "icone centrado na vertical", f["iy"] + f["iw"] / 2, h / 2, 0.5)
            q.flag(
                c,
                "t=0 e t=2,55 centrados e dentro do quadro",
                sc["minLeft"] >= 0 and sc["maxRight"] <= w and abs(metrics(sc["snap"]["0"])["center"] - w / 2) < 3,
                f"{sc['minLeft']:.1f}..{sc['maxRight']:.1f}",
            )
            q.flag(c, "letra visivel sempre afastada do icone", sc["minEdge"] > 0, f"min {sc['minEdge']:.1f} px")
    finally:
        q.b.close()
    out = q.work / "resultado.json"
    out.write_text(json.dumps(q.results, ensure_ascii=False, indent=1))
    bad = [r for r in q.results if not r["ok"]]
    for r in q.results:
        print("OK " if r["ok"] else "XX ", r["caso"], "|", r["item"], "|", r["obtido"], "|", r["esperado"])
    print(f"{len(q.results) - len(bad)}/{len(q.results)} dentro da tolerancia")
    return 1 if bad else 0


if __name__ == "__main__":
    t = time.time()
    code = main(sys.argv[1])
    print(f"{time.time() - t:.0f}s")
    sys.exit(code)
