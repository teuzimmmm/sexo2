from cdp import *

URL = "file:///Users/matheus/Documents/tremdolol/sexo2-lab/a/design/propostas/sexo2-ux-a/index.html"
EV = "/Users/matheus/Documents/tremdolol/sexo2-lab/a/design/propostas/sexo2-ux-a/evidencias/"
b = Br(1280, 720)
b.size(1280, 720)
b.go(URL + "#selecao")
R = []


def ck(n, c, extra=""):
    R.append((n, bool(c)))
    print(("OK  " if c else "FAIL"), n, extra)


def clk(k):
    r = b.js(
        f"(()=>{{const e=document.querySelector('[data-k=\"{k}\"]');if(!e)return 'none';if(e.disabled)return 'dis';e.focus();e.click();return 'ok'}})()"
    )
    if r != "ok":
        print("  click", k, r)


tx = b.js


def w(t=0.2):
    time.sleep(t)


def geo():
    return tx("""(()=>{const p=document.querySelector('.asst').getBoundingClientRect(),l=document.getElementById('launcher').getBoundingClientRect(),s=document.getElementById('stage').getBoundingClientRect();
    return JSON.stringify({pw:p.width,ph:p.height,right:Math.abs(p.right-l.right),gap:l.top-p.bottom,inside:p.left>=s.left&&p.top>=s.top+28&&p.right<=s.right&&p.bottom<=s.bottom,overlap:!(p.bottom<=l.top||p.top>=l.bottom||p.right<=l.left||p.left>=l.right)})})()""")


for W, H in [(1280, 720), (820, 560)]:
    b.size(W, H)
    b.go(URL + "#selecao")
    w()
    g = (
        eval(geo().replace("true", "True").replace("false", "False").replace("null", "None"))
        if False
        else __import__("json").loads(geo())
    )
    ck(
        f"A07 D-017 {W}x{H}",
        g["pw"] == 452
        and g["ph"] == 492
        and g["right"] <= 1
        and abs(g["gap"] - 8) <= 1
        and g["inside"]
        and not g["overlap"],
        str(g),
    )
    ck(
        f"A07 sem scroll horizontal {W}",
        tx(
            "document.documentElement.scrollWidth<=innerWidth&&document.getElementById('main').scrollWidth<=document.getElementById('main').clientWidth"
        ),
    )
    b.shot(EV + f"a07-selecao-{W}x{H}.png")
    if W == 820:
        tx("document.getElementById('main').scrollTop=9999")
        w(0.1)
        b.shot(EV + "a07-selecao-820x560-rolada.png")
        tx("document.getElementById('main').scrollTop=0")
# runas
b.size(1280, 720)
b.go(URL + "#selecao")
w()
clk("runeImport|r1")
w(0.1)
ck("A04 importando visivel", tx("S.run.status==='importing'&&document.body.innerText.includes('Importando')"))
w(0.9)
ck("A04 sucesso", tx("S.run.status==='success'&&document.body.innerText.includes('Sucesso')"))
tx(
    "(()=>{const s=document.getElementById('simRes');s.value='no_free_page';s.dispatchEvent(new Event('change',{bubbles:true}))})()"
)
w()
clk("runeImport|r1")
w(1)
ck(
    "A04 no_free_page sem apagar",
    tx(
        "S.run.status==='no_free_page'&&document.body.innerText.toLowerCase().includes('nenhuma página pessoal foi apagada')"
    ),
)
b.shot(EV + "a04-runas-no-free-page.png")
tx(
    "(()=>{const s=document.getElementById('simRes');s.value='failed';s.dispatchEvent(new Event('change',{bubbles:true}))})()"
)
w()
clk("runeImport|r2")
w(1)
ck("A04 falha", tx("S.run.status==='failed'"))
clk("runeEdit|")
clk("runeKey|8229")
clk("runeKey|8230")
w()
ck(
    "A04 editor agrupa edicoes",
    tx("S.run.edits===2&&document.body.innerText.includes('2 edição(ões) agrupada(s) em 1 importação')"),
)
# fonte preferida nao importa
tx("S.run.status='idle';rerender()")
clk("qpToggle|")
w()
tx(
    "(()=>{const s=document.getElementById('pref-fonte');s.value='Onetricks';s.dispatchEvent(new Event('change',{bubbles:true}))})()"
)
w()
ck("A04 mudar fonte nao importa", tx("S.run.status==='idle'&&dirty()===1&&!!document.querySelector('.drawer')"))
b.shot(EV + "a06-preferencias-rapidas.png")
clk("toCfg|")
w()
ck(
    "A06 todas as configuracoes preserva rascunho",
    tx(
        "S.page==='Configurações'&&dirty()===1&&document.body.innerText.includes('Rascunho e escolhas foram preservados')"
    ),
)
clk("back|")
w()
ck("A06 retorno a selecao", tx("S.page==='Seleção'&&dirty()===1"))
clk("qpToggle|")
w()
clk("cfgCancel|")
w()
ck("A06 cancelar no painel", tx("dirty()===0&&S.prefs.fonte==='Lolalytics'"))
# comparar
clk("qpToggle|")
w()
clk("compare|")
w()
ck("A04 comparacao lado a lado", tx("S.compare&&document.querySelectorAll('.asst .grid.g2 .card').length===2"))
ck("A04 onetricks indisponivel honesto", tx("document.body.innerText.includes('Sem dados. Não substituímos')"))
tx(
    "(()=>{const s=document.getElementById('otMode');s.value='simulado';s.dispatchEvent(new Event('change',{bubbles:true}))})()"
)
w()
ck(
    "A04 amostras/patch separados",
    tx(
        "(()=>{const t=document.querySelector('.asst').innerText;return t.includes('12.480')&&t.includes('740')&&t.includes('15.20')&&t.includes('15.19')&&t.includes('simulados')})()"
    ),
)
b.shot(EV + "a04-comparar-fontes.png")
clk("compare|")
# itens
clk("tab|asst:Itens")
w()
ck(
    "A05 trios ordenados por partidas",
    tx(
        "(()=>{const n=[...document.querySelectorAll('#trioList .st')].map(x=>+x.innerText.match(/([\\d.]+) partidas/)[1].replace('.',''));return n.length===6&&n.every((v,i)=>i==0||n[i-1]>=v)})()"
    ),
)
ck(
    "A05 icones + WR",
    tx(
        "document.querySelectorAll('#trioList .trio')[0].querySelectorAll('img').length===3&&document.querySelector('#trioList').innerText.includes('54,2%')"
    ),
)
tx(
    "(()=>{const i=document.getElementById('itemQ');i.value='Zhonya';i.dispatchEvent(new Event('input',{bubbles:true}))})()"
)
ck("A05 busca por item", tx("document.querySelectorAll('#trioList .trio').length===3"))
tx(
    "(()=>{const i=document.getElementById('itemQ');i.value='6653';i.dispatchEvent(new Event('input',{bubbles:true}))})()"
)
ck("A05 busca por id", tx("document.querySelectorAll('#trioList .trio').length===2"))
tx("(()=>{const i=document.getElementById('itemQ');i.value='';i.dispatchEvent(new Event('input',{bubbles:true}))})()")
clk("trioUse|t2")
w()
ck(
    "A05 trio antes do padrao",
    tx("S.trio==='t2'&&document.querySelector('#abody').innerText.toLowerCase().includes('trio escolhido')"),
)
clk("itemConfirm|")
w()
ck("A05 importacao simulada ao confirmar", tx("S.itemMsg&&S.itemMsg.includes('trio')"))
b.shot(EV + "a05-itens-trios.png")
clk("trioReset|")
w()
ck(
    "A05 restaurar padrao",
    tx("S.trio===null&&!document.querySelector('#abody').innerText.toLowerCase().includes('trio escolhido')"),
)
ck(
    "A05 so trios (3 ic./linha)",
    tx("[...document.querySelectorAll('#trioList .trio')].every(t=>t.querySelectorAll('img').length===3)"),
)
# skins e mods
clk("tab|asst:Skins e mods")
w()
b.shot(EV + "a02-assistente-skins.png")
# fontes
ck(
    "A07 fontes carregadas",
    tx(
        "document.fonts.check('16px Oswald')&&document.fonts.check('16px Inter')&&[...document.fonts].every(f=>f.status==='loaded')"
    ),
)
ck(
    "A07 sem serif/azul",
    tx(
        """(()=>{const bad=[];document.querySelectorAll('*').forEach(e=>{const c=getComputedStyle(e);const f=c.fontFamily;if(!/Oswald|Inter/.test(f))bad.push(e.tagName+f);[c.color,c.backgroundColor,c.borderTopColor,c.outlineColor].forEach(x=>{const m=x.match(/rgba?\\((\\d+), (\\d+), (\\d+)/);if(m&&+m[3]>+m[1]+25&&+m[3]>+m[2]+25)bad.push('blue '+e.tagName+x)})});return bad.length===0||bad.slice(0,5).join(';')})()"""
    ),
)
print(sum(1 for r in R if not r[1]), "falhas de", len(R))
b.close()
