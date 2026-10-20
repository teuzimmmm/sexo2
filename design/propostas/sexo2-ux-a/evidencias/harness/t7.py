from cdp import *
import json

URL = "file:///Users/matheus/Documents/tremdolol/sexo2-lab/a/design/propostas/sexo2-ux-a/index.html"
EV = "/Users/matheus/Documents/tremdolol/sexo2-lab/a/design/propostas/sexo2-ux-a/evidencias/"
b = Br(1280, 720)
b.size(1280, 720)
b.go(URL + "#sala")
R = []


def ck(n, c, extra=""):
    R.append((n, bool(c)))
    print(("OK  " if c else "FAIL"), n, extra)


tx = b.js


def w(t=0.15):
    time.sleep(t)


def ak():
    return tx(
        "(document.activeElement.dataset&&document.activeElement.dataset.k)||document.activeElement.id||document.activeElement.tagName"
    )


b.js("A.roomCreate();rerender()")
# Tab sequencial na Sala
seq = []
tx("document.body.focus();document.getElementById('nav').querySelector('button').focus()")
for i in range(8):
    b.key("Tab")
    w(0.05)
    seq.append(ak())
print(seq)
ck("A08 Tab percorre navegacao e conteudo", len(set(seq)) == 8)
for i in range(3):
    b.key("Tab", 8)
    w(0.05)
ck("A08 Shift+Tab volta", ak() == seq[4], ak())
# modal por teclado
tx("document.querySelector('[data-k=\"coordAsk|\"]').focus()")
b.key("Enter")
w(0.3)
print(
    tx("location.href+'|'+document.readyState+'|'+!!document.getElementById('dlg')+'|'+document.body.innerHTML.length")
)
ck("A08 Enter abre modal", tx("document.getElementById('dlg').open"))
inside = []
for i in range(6):
    b.key("Tab")
    w(0.05)
    inside.append(tx("!!document.activeElement.closest('#dlg')"))
for i in range(6):
    b.key("Tab", 8)
    w(0.05)
    inside.append(tx("!!document.activeElement.closest('#dlg')"))
ck("A08 foco preso no modal (Tab/Shift+Tab)", all(inside), str(inside))
b.shot(EV + "a08-modal-foco.png")
b.key("Escape")
w(0.3)
ck("A08 Escape fecha modal", tx("!document.getElementById('dlg').open"))
ck("A08 foco restaurado ao abridor", ak() == "coordAsk|", ak())
# gotcha: foco depois de acao que re-renderiza
tx("document.querySelector('[data-k=\"roomAdd|\"]').focus()")
b.key("Enter")
w(0.2)
ck("A08 foco mantido apos acao", ak() == "roomAdd|", ak())
# Escape fecha drawer
b.go(URL + "#selecao")
w()
tx("document.querySelector('[data-k=\"qpToggle|\"]').focus()")
b.key("Enter")
w(0.2)
ck(
    "A08 drawer abre e foca primeiro controle",
    tx("!!document.querySelector('.drawer')") and ak() == "pref-autoaceite",
    ak(),
)
b.key("Escape")
w(0.2)
ck("A08 Escape fecha drawer e devolve foco", tx("!document.querySelector('.drawer')") and ak() == "qpToggle|", ak())
# foco visivel
b.key("Tab")
w(0.1)
ck(
    "A07 anel de foco claro",
    tx(
        "(()=>{const c=getComputedStyle(document.activeElement);return c.outlineStyle==='solid'&&c.outlineColor==='rgb(236, 236, 236)'&&parseFloat(c.outlineWidth)>=2})()"
    ),
)
# compact 452x492
b.size(452, 492)
b.go(URL + "#assistente")
w(0.5)
g = tx(
    """JSON.stringify((()=>{const p=document.querySelector('.asst').getBoundingClientRect();return {w:p.width,h:p.height,sx:document.documentElement.scrollWidth,sy:document.documentElement.scrollHeight,compact:document.body.classList.contains('compact')}})())"""
)
print(g)
g = json.loads(g)
ck(
    "A07 compacto 452x492 sem rolagem de pagina",
    g["w"] == 452 and g["h"] == 492 and g["sx"] <= 452 and g["sy"] <= 492 and g["compact"],
)
b.shot(EV + "a07-assistente-452x492.png")
tx("document.querySelector('[data-k=\"tab|asst:Itens\"]').click()")
w()
b.shot(EV + "a07-assistente-itens-452x492.png")
tx(
    "document.querySelector('[data-k=\"tab|asst:Runas\"]').click();document.querySelector('[data-k=\"qpToggle|\"]').click()"
)
w()
b.shot(EV + "a07-assistente-prefs-452x492.png")
tx("document.querySelector('[data-k=\"toCfg|\"]').click()")
w()
ck("A06 compacto -> config completa e volta", tx("S.page==='Configurações'&&!S.compact"))
b.size(452, 492)
b.shot(EV + "a07-config-452x492.png")
tx("document.querySelector('[data-k=\"back|\"]').click()")
w()
ck("A06 volta ao compacto", tx("S.compact&&S.page==='Seleção'"))
# 820x560 todas as paginas
b.size(820, 560)
b.go(URL)
w()
for p in ["Skins", "Mods", "Sala", "Configurações", "Suporte"]:
    tx(f"go('{p}')")
    w(0.1)
    ov = tx(
        "[...document.querySelectorAll('#main *')].filter(e=>{const r=e.getBoundingClientRect();return r.right>document.getElementById('main').getBoundingClientRect().right+1&&r.width>0}).map(e=>e.tagName+'.'+e.className).slice(0,3).join(',')"
    )
    ck(
        f"A07 820x560 {p} sem estouro horizontal",
        tx("document.getElementById('main').scrollWidth<=document.getElementById('main').clientWidth") and not ov,
        ov,
    )
    b.shot(EV + f"a07-{p.lower().replace('ç', 'c').replace('õ', 'o')}-820x560.png")
b.size(1280, 720)
b.go(URL)
w()
for p in ["Mods", "Suporte", "Sala"]:
    tx(f"go('{p}')")
    w(0.1)
    b.shot(EV + f"a07-{p.lower()}-1280x720.png")
print(sum(1 for r in R if not r[1]), "falhas de", len(R))
b.close()
