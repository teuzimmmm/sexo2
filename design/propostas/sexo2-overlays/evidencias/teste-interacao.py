from mn import *

D = "/Users/matheus/Documents/tremdolol/sexo2-lab/overlays/design/propostas/sexo2-overlays"
URL = "file://" + D + "/index.html"
p, m = start()
m.cmd("WebDriver:SetWindowRect", {"width": 1280, "height": 805})
res = []


def ok(n, c, d=""):
    res.append(("PASS" if c else "FAIL") + " " + n + (("  | " + str(d)) if d else ""))


J = m.js


def go(h=""):
    m.cmd("WebDriver:Navigate", {"url": URL + h})
    time.sleep(0.8)


txt = "return [...document.querySelectorAll('#stage text')].map(t=>t.textContent)"


def setv(id, v):
    J(
        "const e=document.getElementById(arguments[0]);e.value=arguments[1];e.dispatchEvent(new Event('change',{bubbles:true}))",
        [id, v],
    )


go("")
ok(
    "sem hash -> #b e B pressionado",
    J("return location.hash") == "#b"
    and J("return document.querySelector('[data-mode=b]').getAttribute('aria-pressed')") == "true",
    J("return location.hash"),
)
ok("inner 1280x720", tuple(J("return [innerWidth,innerHeight]")) == (1280, 720), J("return [innerWidth,innerHeight]"))
ok('total B "ITENS · -210 ouro"', "ITENS · -210 ouro" in J(txt))
ok(
    "diffs B na tela",
    [t for t in J(txt) if t[:1] in "+-" and t[1:].isdigit()] == ["-340", "+770", "-640", "+540", "-540"],
    [t for t in J(txt) if t[:1] in "+-" and t[1:].isdigit()],
)
c = J("return sexo2Calc.scenarioData('normal')")
ok(
    "O02 calc normal",
    c["d"] == [-340, 770, -640, 540, -540]
    and c["total"] == -210
    and c["enemyTotal"] == 45850
    and c["allyTotal"] == 45640,
    c,
)
J("document.fonts.load('700 16px Inter');document.fonts.load('16px Oswald')")
time.sleep(0.5)
ok(
    "document.fonts: Inter e Oswald loaded",
    J("return [...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family).sort().join()") == "Inter,Oswald",
    J("return [...document.fonts].map(f=>f.family+':'+f.status).join(' ')"),
)
ok(
    "fonte computada: body Inter, h1 Oswald, svg Inter",
    J("return getComputedStyle(document.body).fontFamily")[:5] == "Inter"
    and J("return getComputedStyle(document.querySelector('h1')).fontFamily")[:6] == "Oswald"
    and J("return document.querySelector('#stage text').getAttribute('font-family')")[:5] == "Inter",
)
# hash e histórico
for md in ["blitz", "a", "b"]:
    J("document.querySelector('[data-mode=%s]').click()" % md)
    time.sleep(0.3)
    ok(
        "clique %s -> hash/pressed" % md,
        J("return location.hash") == "#" + md
        and J("return document.querySelector('[data-mode=%s]').getAttribute('aria-pressed')" % md) == "true",
    )
m.cmd("WebDriver:Back")
time.sleep(0.4)
ok(
    "voltar -> #a",
    J("return location.hash") == "#a"
    and J("return document.querySelector('[data-mode=a]').getAttribute('aria-pressed')") == "true",
    J("return location.hash"),
)
m.cmd("WebDriver:Back")
time.sleep(0.4)
ok("voltar -> #blitz", J("return location.hash") == "#blitz")
m.cmd("WebDriver:Forward")
time.sleep(0.4)
ok("avançar -> #a", J("return location.hash") == "#a")
for h in ["#a", "#b", "#blitz"]:
    go(h)
    ok(
        "abertura direta " + h,
        J("return document.querySelector('[data-mode=%s]').getAttribute('aria-pressed')" % h[1:]) == "true",
    )
# cenários
go("#b")
setv("scenario", "adv")
ok("vantagem: total +2070", "ITENS · +2070 ouro" in J(txt))
g = J("return [...document.querySelectorAll('#stage path[stroke=\"#97d1b8\"]')].map(p=>p.getAttribute('d'))")
ok("vantagem: 5 barras p/ direita (equipe à direita)", len(g) == 5 and all("h-" not in x for x in g), g[:2])
setv("scenario", "dis")
ok("desvantagem: total -2070", "ITENS · -2070 ouro" in J(txt))
g = J("return [...document.querySelectorAll('#stage path[stroke=\"#edaf8c\"]')].map(p=>p.getAttribute('d'))")
ok("desvantagem: 5 barras p/ esquerda", len(g) == 5 and all("h-" in x for x in g), g[:2])
setv("scenario", "tie")
t = J(txt)
ok(
    "empate: total empate, linhas 0, sem barras",
    any("empate" in x for x in t)
    and t.count("0") >= 5
    and J('return document.querySelectorAll(\'#stage path[stroke="#97d1b8"],#stage path[stroke="#edaf8c"]\').length')
    == 0,
    [x for x in t if "empate" in x],
)
setv("scenario", "missing")
t = J(txt)
ok(
    'indisponível B: total indisponível, 1 linha "—", nenhum total numérico, linha não é 0',
    ("TOTAL INDISPONÍVEL" in t) and t.count("—") == 1 and not any(x.startswith("ITENS") for x in t),
    t.count("—"),
)
mm = J("return sexo2Calc.scenarioData('missing')")
ok("calc missing: d[2]=null total=null", mm["d"][2] is None and mm["total"] is None, mm)
J("document.querySelector('[data-mode=blitz]').click()")
time.sleep(0.3)
t = J(txt)
ok(
    'indisponível Blitz: sem totais/diamante numérico de total, 1 "—" de linha',
    ("— TOTAL INDISPONÍVEL" in t) and "45850" not in t and t.count("—") == 1,
    t[-12:],
)
J("document.querySelector('[data-mode=a]').click()")
time.sleep(0.3)
t = J(txt)
ok("indisponível A: total e linha indisponíveis", ("TOTAL INDISPONÍVEL" in t) and t.count("—") == 1)
# lado
setv("scenario", "normal")
J("document.querySelector('[data-mode=b]').click()")
time.sleep(0.3)


def xs(name):
    return J(
        "return +([...document.querySelectorAll('#stage text')].find(t=>t.textContent===arguments[0]).getAttribute('x'))",
        [name],
    )


ok("direita: Garen(aliado) à direita de Darius", xs("Garen") > xs("Darius"), (xs("Garen"), xs("Darius")))
setv("side", "left")
ok("esquerda: Garen à esquerda de Darius", xs("Garen") < xs("Darius"), (xs("Garen"), xs("Darius")))
pos = J("return [...document.querySelectorAll('#stage path[stroke=\"#97d1b8\"]')].map(p=>p.getAttribute('d'))")
neg = J("return [...document.querySelectorAll('#stage path[stroke=\"#edaf8c\"]')].map(p=>p.getAttribute('d'))")
ok(
    "esquerda: vantagem(+770,+540) p/ esquerda; desvantagem(3) p/ direita",
    len(pos) == 2 and all("h-" in x for x in pos) and len(neg) == 3 and all("h-" not in x for x in neg),
    (pos, neg),
)
J("document.querySelector('[data-mode=a]').click()")
time.sleep(0.3)
at = [t for t in J(txt) if "◂" in t or "▸" in t]
ok("A esquerda: -340 ▸ ; +770 ◂", at[0].startswith("▸") and at[1].startswith("◂"), at)
setv("side", "right")
at = [t for t in J(txt) if "◂" in t or "▸" in t]
ok("A direita: -340 ◂ ; +770 ▸", at[0].startswith("◂") and at[1].startswith("▸"), at)
# persistência
J("document.querySelector('[data-mode=b]').click()")
setv("scenario", "dis")
setv("font", "Oswald")
setv("side", "left")
J("document.getElementById('visible').click()")
time.sleep(0.2)
t = J(txt)
ok(
    "ocultar: sem total nem diferenças (restam nomes/KDA/16/8), aviso",
    not any(x.startswith("ITENS") for x in t)
    and not any(x.lstrip("+-").isdigit() and x not in ("16", "8") for x in t)
    and "oculto" in J("return document.getElementById('feedback').textContent"),
    t,
)
m.shot(D + "/evidencias/b-oculto-via-controle-1280x720.png")
J("document.getElementById('visible').click()")
time.sleep(0.2)
ok(
    "reexibir: cenário/lado/fonte mantidos e total",
    J("return [scenario.value,side.value,font.value]") == ["dis", "left", "Oswald"] and "ITENS · -2070 ouro" in J(txt),
)
# Escape real
J("document.activeElement.blur()")
m.keys("")
time.sleep(0.2)
ok("Escape (tecla real) oculta", J("return document.getElementById('visible').checked") == False)
J("document.getElementById('visible').click()")
go("#b")  # recarrega: preferências
ok(
    "após recarregar: prefs restauradas (dis/left/Oswald)",
    J("return [scenario.value,side.value,font.value,document.getElementById('visible').checked]")
    == ["dis", "left", "Oswald", True],
    J("return [scenario.value,side.value,font.value]"),
)
# Tab / Shift+Tab reais
go("#b")
ae = "const a=document.activeElement;return a.tagName+':'+(a.dataset.mode||a.id||a.textContent.slice(0,8))+':'+a.matches(':focus-visible')"
order = []
for i in range(12):
    m.keys("\ue004")
    order.append(J(ae))
ok(
    "Tab real percorre 12 controles na ordem do documento",
    [o.split(":")[1] for o in order[:9]]
    == ["Proposta", "Proposta", "b", "blitz", "a", "scenario", "side", "font", "visible"],
    order,
)
go("#b")
for i in range(3):
    m.keys("\ue004")
ae2 = J(
    "const a=document.activeElement;const cs=getComputedStyle(a);return [a.dataset.mode,cs.outlineStyle,cs.outlineColor,cs.outlineWidth,a.matches(':focus-visible')]"
)
ok(
    "Tab até botão B: :focus-visible com outline claro 2px",
    ae2 == ["b", "solid", "rgb(236, 236, 236)", "2px", True],
    ae2,
)
m.keys("\ue004")
ok("Tab seguinte -> botão Blitz", J("return document.activeElement.dataset.mode") == "blitz")
m.shot(D + "/evidencias/foco-teclado-1280x720.png")
m.keys("\ue007")
time.sleep(0.3)
ok("Enter no botão focado ativa Blitz", J("return location.hash") == "#blitz", J("return location.hash"))
m.cmd(
    "WebDriver:PerformActions",
    {
        "actions": [
            {
                "type": "key",
                "id": "kb",
                "actions": [
                    {"type": "keyDown", "value": "\ue008"},
                    {"type": "keyDown", "value": "\ue004"},
                    {"type": "keyUp", "value": "\ue004"},
                    {"type": "keyUp", "value": "\ue008"},
                ],
            }
        ]
    },
)
ok(
    "Shift+Tab volta ao botão B",
    J("return document.activeElement.dataset.mode") == "b",
    J("return document.activeElement.dataset.mode"),
)
# seleção por teclado (select) e checkbox por Espaço
m.keys("\ue004", "\ue004", "\ue004", "\ue004", "\ue004", "\ue004")
ok(
    "foco chega ao checkbox Exibir",
    J("return document.activeElement.id") == "visible",
    J("return document.activeElement.id"),
)
m.keys(" ")
ok("Espaço desmarca Exibir (oculta)", J("return document.getElementById('visible').checked") == False)
m.keys(" ")
ok("Espaço remarca Exibir (reexibe)", J("return document.getElementById('visible').checked") == True)
m.keys("\ue00c")
ok("Escape com foco no checkbox oculta", J("return document.getElementById('visible').checked") == False)
m.keys(" ")
# cores neutras
ok(
    "UI neutra: botão/links/foco sem azul",
    J(
        "const c=getComputedStyle(document.querySelector('a')).color+getComputedStyle(document.querySelector('button')).backgroundColor+getComputedStyle(document.body).backgroundColor;return c"
    )
    in ("rgb(236, 236, 236)rgb(21, 23, 26)rgb(13, 14, 16)", "rgb(236, 236, 236)rgb(34, 37, 42)rgb(13, 14, 16)"),
)
ok("sem rolagem horizontal 1280", J("return document.documentElement.scrollWidth<=innerWidth"))
ok(
    "assets locais: imagens carregadas",
    J("return [...document.images].every(i=>i.complete&&i.naturalWidth>0)"),
    J("return [...document.images].map(i=>i.src.split('/').pop()+':'+i.naturalWidth)"),
)
ok(
    "sem rede/fetch: nenhuma URL http em src/link/@font-face (links http só <a>)",
    J(
        "return [...document.querySelectorAll('[src],link')].every(e=>!/^https?:/.test(e.getAttribute('src')||e.href||''))"
    ),
)
print("\n".join(res))
open("/private/tmp/claude-501/res.txt", "w").write("\n".join(res))
m.cmd("WebDriver:DeleteSession")
p.terminate()
