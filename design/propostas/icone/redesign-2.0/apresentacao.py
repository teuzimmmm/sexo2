"""Monta `apresentacao.html`: a apresentação das três propostas de ícone do SEXO2 (redesign antes da 2.0).

    python design/propostas/icone/redesign-2.0/apresentacao.py

Um arquivo só, para abrir por duplo clique: SVG, PNG e fontes entram embutidos (base64). Os ícones das
simulações são rasterizados no tamanho real (16, 24, 32, 48 px), com o corte pequeno abaixo de 25 px, para
mostrar o que o Windows mostraria. Nada aqui altera `assets/`; é só proposta (CLAUDE.md: decisão de design).
Requer cairosvg (só para gerar esta página; não faz parte do app).
"""

import base64
from pathlib import Path

import cairosvg

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
FONTS = ROOT / "design" / "fonts"
ATUAL = ROOT / "assets" / "sexo2.svg"
INK, PAPER, RED = "#15171a", "#ececec", "#d2412f"


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def svg_file(letter, small=False):
    if letter == "atual":
        return ATUAL
    return HERE / "svg" / f"{letter}-{'pequeno' if small else 'icone'}.svg"


def raster(letter, px):
    """PNG do ícone no tamanho exato; até 24 px usa o corte pequeno (como no .ico final)."""
    png = cairosvg.svg2png(url=str(svg_file(letter, px <= 24)), output_width=px, output_height=px)
    return "data:image/png;base64," + b64(png)


def img(letter, px, zoom=1, extra=""):
    style = "image-rendering:pixelated;" if zoom > 1 else ""
    return f'<img src="{raster(letter, px)}" width="{px * zoom}" height="{px * zoom}" style="{style}" alt="" {extra}>'


def vector(letter, px, small=False):
    uri = "data:image/svg+xml;base64," + b64(svg_file(letter, small).read_bytes())
    return f'<img src="{uri}" width="{px}" height="{px}" alt="">'


def font_css():
    out = []
    for fam, f in (("Oswald", "oswald-latin-wght-normal.woff2"), ("Inter", "inter-latin-wght-normal.woff2")):
        rng = "200 700" if fam == "Oswald" else "100 900"
        out.append(
            f'@font-face{{font-family:"{fam}";font-weight:{rng};font-display:swap;'
            f'src:url(data:font/woff2;base64,{b64((FONTS / f).read_bytes())}) format("woff2");}}'
        )
    return "".join(out)


# --------------------------------------------------------------------------- simulações do Windows
def ph(kind):
    return f'<span class="ph {kind}"></span>'


def taskbar(letter):
    others = ["sq", "ci", "tr", "sq2"]
    cells = "".join(f'<span class="tb-cell">{ph(k)}</span>' for k in others[:2])
    ours = f'<span class="tb-cell on">{img(letter, 24)}</span>'
    cells2 = "".join(f'<span class="tb-cell">{ph(k)}</span>' for k in others[2:])
    return (
        f'<div class="taskbar"><div class="tb-mid">{cells}{ours}{cells2}</div>'
        '<div class="tb-right"><span>^</span><span class="tray16">{t}</span><span class="clock">22:14<br>23/10/2026</span></div></div>'
    ).replace("{t}", img(letter, 16))


def lupa(letter):
    return (
        '<div class="lupa">'
        f"<figure>{img(letter, 24, 6)}<figcaption>24 px · barra de tarefas · 6×</figcaption></figure>"
        f"<figure>{img(letter, 16, 8)}<figcaption>16 px · bandeja · 8×</figcaption></figure>"
        f"<figure>{img(letter, 32, 4)}<figcaption>32 px · Alt+Tab, lista · 4×</figcaption></figure>"
        "</div>"
    )


def tray_flyout(letter):
    ph16 = "".join(ph(k) for k in ("sq", "ci", "tr", "sq2"))
    return (
        '<div class="flyout"><div class="fly-title">Ícones ocultos</div>'
        f'<div class="fly-grid"><span>{ph("ci")}</span><span>{img(letter, 16)}</span><span>{ph("tr")}</span>'
        f"<span>{ph('sq')}</span><span>{ph('sq2')}</span><span>{ph('ci')}</span></div></div>"
    ).replace("{p}", ph16)


def desktop(letter):
    return (
        '<div class="desk">'
        f'<div class="di">{ph("doc")}<b>Notas</b></div>'
        f'<div class="di sel">{img(letter, 48)}<b>SEXO2</b></div>'
        f'<div class="di">{ph("fold")}<b>Jogos</b></div>'
        "</div>"
    )


def explorer(letter):
    return (
        '<div class="expl"><div class="expl-bar">Arquivos de Programas › SEXO2</div>'
        f'<div class="expl-row head"><span></span><span>Nome</span><span>Tipo</span></div>'
        f'<div class="expl-row"><span>{ph("fold16")}</span><span>_internal</span><span>Pasta de arquivos</span></div>'
        f'<div class="expl-row sel"><span>{img(letter, 16)}</span><span>SEXO2.exe</span><span>Aplicativo</span></div>'
        f'<div class="expl-row"><span>{img(letter, 16)}</span><span>SEXO2 Update.exe</span><span>Aplicativo</span></div>'
        "</div>"
    )


def installer(letter):
    return (
        '<div class="win"><div class="win-title">'
        f'<span class="wt-ico">{img(letter, 16)}</span><span>Instalação do SEXO2</span><span class="wt-btn">— &nbsp;☐ &nbsp;✕</span></div>'
        f'<div class="win-body"><div class="win-side">{img(letter, 96)}</div>'
        '<div class="win-main"><h4>Assistente de instalação</h4>'
        "<p>Simulação: este texto é só para mostrar o ícone na janela do instalador.</p>"
        '<div class="win-btns"><span class="b pri">Avançar</span><span class="b">Cancelar</span></div></div></div></div>'
    )


def alttab(letter):
    return (
        '<div class="alt"><div class="alt-card on">'
        f'<div class="alt-head">{img(letter, 24)}<span>SEXO2</span></div><div class="alt-thumb"></div></div>'
        f'<div class="alt-card"><div class="alt-head">{ph("sq")}<span>Cliente</span></div><div class="alt-thumb light"></div></div></div>'
    )


def scenes(letter):
    return (
        f'<div class="scene-grid"><div class="sc wide"><h5>Barra de tarefas (Windows 11, tamanho real)</h5>{taskbar(letter)}{lupa(letter)}</div>'
        f'<div class="sc"><h5>Bandeja do sistema</h5>{tray_flyout(letter)}</div>'
        f'<div class="sc"><h5>Atalho na área de trabalho</h5>{desktop(letter)}</div>'
        f'<div class="sc"><h5>Explorador de Arquivos</h5>{explorer(letter)}</div>'
        f'<div class="sc"><h5>Instalador</h5>{installer(letter)}</div>'
        f'<div class="sc"><h5>Alt+Tab</h5>{alttab(letter)}</div></div>'
    )


# --------------------------------------------------------------------------- diagramas de construção
GUIDE = "#4aa3ff"


def grid_overlay(extra):
    lines = "".join(
        f'<path d="M{p} 0V256M0 {p}H256" stroke="#fff" stroke-opacity=".06" stroke-width="1"/>'
        for p in range(0, 257, 32)
    )
    return f"<g>{lines}{extra}</g>"


def label(x, y, txt, anchor="start"):
    return f'<text x="{x}" y="{y}" fill="{GUIDE}" font-family="Inter" font-size="9" font-weight="600" text-anchor="{anchor}">{txt}</text>'


def construction(letter):
    base = Path(svg_file(letter)).read_text(encoding="utf-8")
    inner = base[base.index(">", base.index("<svg")) + 1 : base.rindex("</svg>")]
    inner = "".join(line for line in inner.splitlines() if not line.startswith("<title"))
    if letter == "a":
        ov = (
            f'<g stroke="{GUIDE}" stroke-width="1" fill="none"><rect x="59" y="36" width="138" height="184"/>'
            '<path d="M59 68H197M59 74H197M59 106H197M59 112H197M59 144H197M59 150H197M59 182H197M59 188H197" stroke-opacity=".35"/></g>'
            + label(128, 28, "138 × 184 · matriz 3 × 5", "middle")
            + label(201, 90, "módulo", "start")
            + label(201, 100, "42×32", "start")
            + label(201, 110, "vala 6", "start")
            + label(201, 135, "vermelho", "start")
            + label(201, 145, "= escolha", "start")
        )
    elif letter == "b":
        ov = (
            f'<g stroke="{GUIDE}" stroke-width="1" fill="none"><rect x="52" y="52" width="152" height="152" stroke-dasharray="3 3"/>'
            '<path d="M42 214L214 42" stroke-dasharray="3 3"/><path d="M52 52L204 204" stroke-opacity=".4" stroke-dasharray="2 3"/></g>'
            + label(52, 44, "quadrado 152", "start")
            + label(214, 38, "corte a 45°", "end")
            + label(250, 236, "deslize 14 · fresta 6", "end")
        )
    else:
        ov = (
            f'<g stroke="{GUIDE}" stroke-width="1" fill="none"><circle cx="128" cy="138" r="44" stroke-dasharray="3 3"/>'
            '<circle cx="128" cy="138" r="92" stroke-dasharray="3 3"/><path d="M128 138L174 58M128 138L82 58M128 138H220M36 138H128" stroke-dasharray="3 3"/></g>'
            + label(176, 52, "60°", "start")
            + label(80, 52, "120°", "end")
            + label(128, 240, "raios 44 e 92 · três peças de 60° · vala 6", "middle")
        )
    return (
        '<svg viewBox="0 0 256 256" width="260" height="260" role="img" aria-label="Construção" class="cons">'
        f"{inner.replace('<rect width="256" height="256"', '<rect width="256" height="256" opacity=".55"', 1)}"
        f"{grid_overlay(ov)}</svg>"
    )


# --------------------------------------------------------------------------- conteúdo
PROPOSTAS = [
    dict(
        l="a",
        nome="Dois em módulos",
        tipo="Numeral (letra/forma) · construído em módulos",
        ideia="O 2 do SEXO2 montado como os campos de uma seleção: onze módulos quadrados e um deles, o do centro, em vermelho. É a escolha dentro da grade.",
        porque=[
            "Carrega o nome e o marco da versão: o ícone é literalmente o “2”, sem figura que precise de explicação.",
            "Fala a língua do app: tudo quadrado, em linhas e campos (aba Equipe, cartas, tabela), com a vala fina igual às linhas finas da interface.",
            "Um acento só, o vermelho, no ponto exato em que o olho para: a escolha. Os outros dez módulos são neutros, como o painel.",
            "Em tamanho pequeno a vala some e sobra um 2 inteiro (corte de 16 a 24 px alinhado à grade de pixels).",
        ],
        cores=[
            ("Grafite", INK, "fundo: o mesmo do app"),
            ("Branco do app", PAPER, "dez módulos"),
            ("Vermelho", RED, "o módulo da escolha"),
        ],
        fortes=[
            "É a única que nomeia o produto sozinha.",
            "Silhueta inconfundível: um dígito alto entre ícones quadrados e redondos.",
            "Sistema pronto: a mesma matriz serve para animação de abertura, favicon do painel e padrões.",
            "Corte de 16 px é o mais legível das três.",
        ],
        fracos=[
            "Parece “um 2”: pouco narrativa além do nome; fica presa à versão (na 3.0 pede revisão).",
            "Em 32 a 48 px as valas ficam serrilhadas se o Windows reduzir sem o corte pequeno.",
            "Espelhada, parece um 5 (aceitável; ninguém vê espelhado).",
        ],
        testes=[
            ("Tamanhos 16/24/32/48", "ok · corte pequeno em 16 e 24"),
            ("Uma cor / invertido", "ok · lê como 2 em preto e branco"),
            ("Desfoque", "ok · silhueta de 2 e ponto vermelho"),
            ("Espelho · 180°", "espelho lembra 5 · 180° ok"),
            ("Tons de cinza", "módulo vermelho cinza-médio, distinto"),
        ],
    ),
    dict(
        l="b",
        nome="Duelo",
        tipo="Abstrato geométrico",
        ideia="Um quadrado cortado por uma fresta diagonal; as duas metades deslizam, uma branca e uma vermelha. Dois lados, um confronto.",
        porque=[
            "A seleção de campeões é um confronto: sua equipe e a deles, sua escolha e a do adversário direto. O desenho é isso, sem desenhar nada de LoL.",
            "A fresta é a herdeira da fresta do ícone atual: o corte que atravessa a forma passa de horizontal para diagonal.",
            "Duas formas e duas cores: é a mais simples, a mais forte em 16 px e a que mais se destaca na barra de tarefas escura.",
            "Triângulos têm lado reto e ponta viva, como o resto do design quadrado do app.",
        ],
        cores=[
            ("Grafite", INK, "fundo"),
            ("Branco do app", PAPER, "metade de cima"),
            ("Vermelho", RED, "metade de baixo"),
        ],
        fortes=[
            "Máximo impacto em qualquer tamanho; lê igual de 16 a 256 px.",
            "Duas formas apenas: fácil de animar (as metades podem se unir ou se afastar).",
            "Sobrevive a uma cor, invertida, espelhada e girada sem criar leitura estranha.",
        ],
        fracos=[
            "É a mais genérica: quadrado cortado na diagonal existe em muitos produtos; ganha identidade só pela cor e pelo deslize.",
            "Não diz nada do nome nem da função; depende de explicação.",
            "Muito vermelho na barra pode competir com alertas do sistema.",
        ],
        testes=[
            ("Tamanhos 16/24/32/48", "ok · o mais firme de todos"),
            ("Uma cor / invertido", "ok · lê perfeito"),
            ("Desfoque", "ok · duas massas nítidas"),
            ("Espelho · 180°", "sem leitura indevida"),
            ("Tons de cinza", "metades distintas por valor"),
        ],
    ),
    dict(
        l="c",
        nome="Pedra-chave",
        tipo="Emblema pictórico · abstrato",
        ideia="Um arco de três peças; a do topo, em vermelho, é a pedra-chave, aquela que trava as outras. É a runa-chave, o centro da seleção de runas.",
        porque=[
            "Tem a melhor história: a pedra-chave sustenta o arco como a runa-chave sustenta a página; é o que o assistente decide por você.",
            "Forma de portal: o app abre uma porta entre o cliente e a partida.",
            "O fundo claro faz o ícone se destacar na barra de tarefas escura e entre as outras janelas, ao contrário das outras duas.",
            "Ângulos limpos (0° e 60°) e raios múltiplos de 4; a vala entre pedras segue a linha fina da interface.",
        ],
        cores=[
            ("Branco do app", PAPER, "fundo: único ícone claro"),
            ("Grafite", INK, "pedras do arco"),
            ("Vermelho", RED, "a pedra-chave"),
        ],
        fortes=[
            "Conceito mais rico e fácil de explicar em uma frase.",
            "Destaque máximo sobre barra escura e janelas escuras.",
            "A pedra vermelha dá um ponto de foco que se vê até em 16 px.",
        ],
        fracos=[
            "Fundo claro destoa do restante do app, todo grafite.",
            "Girado 180° vira um “U”/ímã; sem querer, parece ferradura ou ponte.",
            "As valas finas competem em 16 px (por isso o corte pequeno tem vala de 1 px).",
            "Em janela de fundo claro o fundo do ícone se perde (veja o teste claro da prancha).",
            "É a mais figurativa e a mais fácil de ser confundida com outros arcos.",
        ],
        testes=[
            ("Tamanhos 16/24/32/48", "ok · corte pequeno com vala de 1 px"),
            ("Uma cor / invertido", "ok · arco legível, chave perde o acento"),
            ("Desfoque", "ok · arco com ponto vermelho"),
            ("Espelho · 180°", "180° lembra U/ímã (risco anotado)"),
            ("Tons de cinza", "pedra-chave cinza, distinta"),
        ],
    ),
]

CSS = """
:root{--bg:#0d0e10;--s1:#15171a;--s2:#1b1d21;--line:#2a2d32;--fg:#ececec;--fg2:#a4a9b0;--fg3:#6e747b;--red:#d2412f}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:400 15px/1.55 Inter,"Segoe UI",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 24px 96px}
h1,h2,h3,h4,h5{font-family:Oswald,"Segoe UI",sans-serif;font-weight:500;text-transform:uppercase;letter-spacing:.03em;margin:0}
h1{font-size:34px}h2{font-size:24px;margin:56px 0 4px}h3{font-size:19px}h4{font-size:14px;color:var(--fg2);margin:16px 0 6px}
h5{font-size:12px;color:var(--fg3);margin:0 0 8px;letter-spacing:.07em}
p{margin:0 0 10px}.lead{color:var(--fg2);max-width:760px}.muted{color:var(--fg3);font-size:13px}
nav.top{position:sticky;top:0;background:#0d0e10ee;border-bottom:1px solid var(--line);z-index:5;padding:10px 24px;display:flex;gap:18px;flex-wrap:wrap;font:500 12px Oswald;letter-spacing:.07em;text-transform:uppercase}
nav.top a{color:var(--fg2);text-decoration:none}nav.top a:hover{color:var(--fg)}
.banner{border:1px solid var(--line);background:var(--s1);padding:12px 16px;margin:18px 0;color:var(--fg2);font-size:13px}
.banner b{color:var(--fg)}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.card{background:var(--s1);border:1px solid var(--line);padding:18px}
.diag{display:grid;grid-template-columns:200px 1fr;gap:20px;align-items:start}
.hero{display:grid;grid-template-columns:320px 1fr;gap:32px;margin-top:20px}
.hero .big{width:320px;height:320px;border:1px solid var(--line)}
.hero .big img{display:block;width:100%;height:100%}
.tag{display:inline-block;border:1px solid var(--line);color:var(--fg2);font:600 11px Inter;padding:2px 8px;letter-spacing:.04em;text-transform:uppercase}
.rec{border-color:var(--red);color:var(--fg)}
ul.t{margin:6px 0 0;padding-left:18px}ul.t li{margin:0 0 6px}
.sw{display:flex;gap:10px;margin:8px 0;flex-wrap:wrap}
.sw div{width:150px;border:1px solid var(--line);background:var(--s1)}.sw i{display:block;height:38px}.sw span{display:block;padding:6px 8px;font-size:12px;color:var(--fg2)}.sw b{color:var(--fg)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:760px){.two,.hero,.diag{grid-template-columns:1fr}.hero .big{width:100%;height:auto;aspect-ratio:1}}
.good li::marker{color:#7fc97f}.bad li::marker{color:var(--red)}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}th{background:var(--s2);font:500 12px Oswald;letter-spacing:.06em;text-transform:uppercase;color:var(--fg2)}
.ladder{display:flex;gap:24px;align-items:flex-end;flex-wrap:wrap;padding:16px;background:var(--s1);border:1px solid var(--line)}
.ladder.light{background:#e9e9e9}.ladder figure,.lupa figure{margin:0;text-align:center}.ladder figcaption,.lupa figcaption{font-size:11px;color:var(--fg3);margin-top:6px}
.ladder.light figcaption{color:#555}
.scene-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px;margin-top:10px}.sc{background:var(--s1);border:1px solid var(--line);padding:14px}.sc.wide{grid-column:1/-1}
.taskbar{height:48px;background:#1f2328;border:1px solid #2f353c;display:flex;justify-content:space-between;align-items:center;padding:0 10px;color:#ddd;font-size:11px}
.tb-mid{display:flex;gap:4px;margin:0 auto;padding-left:120px}.tb-cell{width:40px;height:40px;display:grid;place-items:center;border-radius:5px;position:relative}
.tb-cell.on{background:#ffffff14}.tb-cell.on:after{content:"";position:absolute;bottom:2px;width:14px;height:3px;border-radius:2px;background:#8ab4ff}
.tb-right{display:flex;gap:12px;align-items:center}.clock{text-align:right;line-height:1.2;font-size:11px}.tray16{display:flex}
.ph{display:block;width:24px;height:24px;background:#5b6573;border-radius:4px}.ph.ci{border-radius:50%;background:#7a6f5c}.ph.tr{clip-path:polygon(50% 6%,94% 92%,6% 92%);background:#5c7a6b;border-radius:0}.ph.sq2{background:#6d5c7a;border-radius:7px}
.ph.doc{width:36px;height:44px;background:#d9dde2;border-radius:3px}.ph.fold{width:46px;height:36px;background:#d9b856;border-radius:3px}.ph.fold16{width:16px;height:13px;background:#d9b856;border-radius:2px}
.tray16 .ph{width:16px;height:16px}.lupa{display:flex;gap:30px;align-items:flex-end;margin-top:14px;padding:14px;background:#1f2328;border:1px solid #2f353c}
.flyout{width:200px;background:#2a2f36;border:1px solid #3a4048;border-radius:8px;padding:10px;margin:auto}.fly-title{font-size:11px;color:#aab;margin-bottom:8px}
.fly-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.fly-grid span{display:grid;place-items:center;height:36px;border-radius:5px;background:#ffffff0d}.fly-grid .ph{width:16px;height:16px}
.desk{background:linear-gradient(135deg,#27384f,#4a3b5c 60%,#6b3f48);padding:20px;display:flex;gap:14px;justify-content:center;min-height:130px}
.di{width:76px;text-align:center;color:#fff;font-size:12px;padding:6px 2px;display:flex;flex-direction:column;align-items:center;gap:5px;border:1px solid transparent}.di b{font-weight:400;text-shadow:0 1px 2px #000}.di.sel{background:#ffffff26;border-color:#ffffff40}
.expl{background:#202327;border:1px solid #33383e;font-size:12px}.expl-bar{padding:6px 10px;background:#2a2e33;color:#cdd}.expl-row{display:grid;grid-template-columns:28px 1fr 1fr;align-items:center;padding:4px 10px;color:#ddd}.expl-row.head{color:#889;font-size:11px}.expl-row.sel{background:#ffffff14}
.win{border:1px solid #444;background:#f3f3f3;color:#222;font-size:12px;max-width:380px;margin:auto}.win-title{background:#fff;padding:6px 8px;display:flex;gap:8px;align-items:center;border-bottom:1px solid #ddd}.win-title .wt-btn{margin-left:auto;color:#666}.wt-ico{display:flex}
.win-body{display:grid;grid-template-columns:122px 1fr;min-height:150px}.win-side{background:#15171a;display:grid;place-items:center}.win-main{padding:14px}.win-main h4{color:#222;margin:0 0 8px;font-size:13px}.win-main p{color:#555}
.win-btns{display:flex;gap:8px;margin-top:14px}.b{border:1px solid #aaa;padding:3px 12px;background:#fdfdfd}.b.pri{border-color:#0067c0;background:#0067c0;color:#fff}
.alt{display:flex;gap:12px;justify-content:center;background:#1b1e22;padding:16px;border-radius:10px}.alt-card{width:150px;padding:8px;border:2px solid transparent;border-radius:8px}.alt-card.on{border-color:#cfd6df;background:#ffffff12}
.alt-head{display:flex;gap:8px;align-items:center;font-size:12px;margin-bottom:6px}.alt-thumb{height:70px;background:#0d0e10;border:1px solid #333}.alt-thumb.light{background:#c9d4e3}
.cons{background:#0d0e10;border:1px solid var(--line)}
.ratings td.c{text-align:center;font-weight:600}
.shelf{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-end}.shelf figure{margin:0;text-align:center}.shelf figcaption{font-size:11px;color:var(--fg3);margin-top:6px}
.next li{margin-bottom:6px}
"""


def page():
    P = []
    P.append(
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
    )
    P.append("<title>SEXO2 · propostas de ícone</title><style>" + font_css() + CSS + "</style></head><body>")
    P.append(
        "<nav class='top'><a href='#ctx'>Contexto</a><a href='#a'>A · Dois em módulos</a><a href='#b'>B · Duelo</a><a href='#c'>C · Pedra-chave</a><a href='#prancha'>Prancha comparativa</a><a href='#rec'>Recomendação</a></nav><div class='wrap'>"
    )
    P.append(
        "<h1>SEXO2 · redesign do ícone</h1><p class='lead'>Três propostas distintas para a última mudança de produto antes da 2.0. Nada foi aplicado: o ícone oficial (<code>assets/sexo2.svg</code>) continua o mesmo até a sua escolha.</p>"
    )
    P.append(
        "<div class='banner'><b>Material experimental</b> · só na branch <code>gunderfrank</code> · pasta <code>design/propostas/icone/redesign-2.0/</code>. Todas as simulações do Windows são desenhadas; os ícones aparecem rasterizados no tamanho real que o sistema usaria.</div>"
    )

    # contexto
    P.append("<h2 id='ctx'>Ponto de partida</h2><div class='card diag'>")
    P.append(
        f"<div>{img('atual', 192)}<p class='muted' style='margin-top:6px'>Ícone atual (D-123, “2 · Degrau”)</p><div style='display:flex;gap:10px;align-items:flex-end'>{img('atual', 48)}{img('atual', 32)}{img('atual', 24)}{img('atual', 16)}</div></div>"
    )
    P.append(
        "<div><h4>Diagnóstico</h4><ul class='t'>"
        "<li><b>O que é:</b> uma cabeça de galo facetada (crista, bico) com uma fresta e um pequeno triângulo vermelho. É o galo antigo reduzido, embora a decisão D-112 tenha tirado o Galo como marca.</li>"
        "<li><b>Leitura:</b> a figura não diz o nome nem a função; a barbela vermelha, único acento, desaparece abaixo de 32 px e a fresta fecha em 16 px.</li>"
        "<li><b>Construção:</b> polígono irregular (um lado a 106,9°, quase 105°), sem grade; foi desenhado a mão.</li></ul>"
        "<h4>Auditoria de patrimônio (o que vale manter)</h4><ul class='t'>"
        "<li><b>Manter:</b> grafite + branco quente + <i>um</i> vermelho; o tile quadrado (o app inteiro é quadrado); a fresta como corte que atravessa a forma.</li>"
        "<li><b>Abandonar (liberdade criativa dada):</b> a silhueta de galo e seus ângulos soltos; a figura sem relação com o produto.</li>"
        "<li><b>Contexto de produto:</b> app privado para League of Legends, em Windows; assistente de seleção (runas, itens, equipe), skins, sala e overlays; visual escuro, quadrado, Oswald e Inter; azul e vermelho reservados para aliado e inimigo na interface.</li></ul></div></div>"
    )
    P.append(
        "<p class='muted'>Método: skill de logo (modo Redesign): diagnóstico, auditoria de patrimônio, 12 conceitos de uma frase, três escolhidos por serem os mais diferentes entre si em tipo de marca e em leitura. Duas rodadas de refino, com auditoria de SVG e testes de tamanho. Não há garantia de registro de marca; recomenda-se busca de anterioridade antes de publicar.</p>"
    )
    P.append(
        "<details class='card' style='margin-top:12px'><summary>Os 12 conceitos considerados (os três finalistas estão em negrito)</summary><ol class='t'>"
        "<li><b>Numeral 2 em módulos de seleção</b> (A)</li><li>Monograma S2 em uma só linha contínua</li><li>Quadrado cortado na diagonal, metades deslizadas (<b>B</b>)</li>"
        "<li><b>Arco com pedra-chave vermelha</b> (C)</li><li>Duas molduras sobrepostas, interseção vermelha (descartada: lê como “copiar”)</li><li>Cursor/mira de travar escolha (comum em apps de jogo)</li>"
        "<li>Ping em losango (marca registrada do jogo, evitar)</li><li>Chave-fenda/cadeado de “trava” (literal)</li><li>Pinguim do Pengu (tirado: Galo/Pengu fora da marca, D-112)</li>"
        "<li>Camadas empilhadas (clichê de “layers”)</li><li>Escada de três degraus rumo ao 2 (continuação do “Degrau”; fraca em 16 px)</li><li>Selo circular com notch (genérico)</li></ol></details>"
    )

    for p in PROPOSTAS:
        l = p["l"]
        P.append(f"<h2 id='{l}'>{l.upper()} · {p['nome']}</h2><p class='muted'>{p['tipo']}</p>")
        P.append(
            f"<div class='hero'><div class='big'>{vector(l, 320)}</div><div><p class='lead' style='font-size:17px'>{p['ideia']}</p><h4>Por que funciona</h4><ul class='t'>"
            + "".join(f"<li>{x}</li>" for x in p["porque"])
            + "</ul></div></div>"
        )
        P.append(
            "<div class='two' style='margin-top:20px'><div class='card'><h4 style='margin-top:0'>Construção visual</h4><div style='display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start'>"
            + construction(l)
        )
        P.append(
            "<p class='muted' style='max-width:330px'>Grade de 256. Só formas básicas (retângulos, triângulos, arcos), sem texto vivo, sem filtros nem imagens, 3 cores. Pontuação do auditor do skill: 100/100.</p></div></div>"
        )
        P.append(
            "<div class='card'><h4 style='margin-top:0'>Escolhas de cor</h4><div class='sw'>"
            + "".join(
                f"<div><i style='background:{c}'></i><span><b>{n}</b> {c}<br>{u}</span></div>" for n, c, u in p["cores"]
            )
            + "</div>"
        )
        P.append(
            "<p class='muted'>Contraste (WCAG): branco sobre grafite 15,2:1 · vermelho sobre grafite 3,9:1 e sobre branco 3,9:1 (acima dos 3:1 exigidos de elementos gráficos). Só as três cores do app; nenhum azul, que fica para o aliado.</p>"
        )
        P.append(
            "<h4>Testes do skill</h4><table>"
            + "".join(f"<tr><th>{a}</th><td>{b}</td></tr>" for a, b in p["testes"])
            + "</table></div></div>"
        )
        P.append(
            "<h4>Escada de tamanhos (o corte pequeno entra em 16 e 24 px)</h4><div class='ladder'>"
            + "".join(
                f"<figure>{img(l, s)}<figcaption>{s} px</figcaption></figure>" for s in (16, 20, 24, 32, 48, 64, 96)
            )
            + "</div>"
        )
        P.append(
            "<div class='ladder light' style='margin-top:10px'>"
            + "".join(f"<figure>{img(l, s)}<figcaption>{s} px</figcaption></figure>" for s in (16, 24, 32, 48))
            + "</div>"
        )
        P.append("<h4>Simulações no Windows</h4>" + scenes(l))
        P.append(
            "<div class='two' style='margin-top:16px'><div class='card'><h4 style='margin-top:0'>Pontos fortes</h4><ul class='t good'>"
            + "".join(f"<li>{x}</li>" for x in p["fortes"])
            + "</ul></div>"
        )
        P.append(
            "<div class='card'><h4 style='margin-top:0'>Pontos fracos</h4><ul class='t bad'>"
            + "".join(f"<li>{x}</li>" for x in p["fracos"])
            + "</ul></div></div>"
        )

    # prancha comparativa
    P.append(
        "<h2 id='prancha'>Prancha comparativa</h2><p class='lead'>As três e o ícone atual no mesmo tamanho, sobre fundo escuro e claro, depois lado a lado na barra de tarefas.</p>"
    )
    row = lambda cls, sizes: "".join(
        f"<div class='ladder {cls}' style='margin-bottom:10px'>"
        + "".join(
            f"<figure>{img(k, s)}<figcaption>{n} · {s}</figcaption></figure>"
            for k, n in (("atual", "atual"), ("a", "A"), ("b", "B"), ("c", "C"))
        )
        + "</div>"
        for s in sizes
    )
    P.append("<h4>Escuro</h4>" + row("", (16, 24, 32, 48)) + "<h4>Claro</h4>" + row("light", (24, 48)))
    P.append("<h4>Prateleira: na barra de tarefas, entre outros</h4><div class='sc wide'>")
    for k, n in (("atual", "Atual"), ("a", "A"), ("b", "B"), ("c", "C")):
        P.append(f"<p class='muted' style='margin:8px 0 2px'>{n}</p>{taskbar(k)}")
    P.append("</div>")
    P.append(
        "<h4>Matriz de avaliação</h4><table class='ratings'><tr><th>Critério</th><th>A · Módulos</th><th>B · Duelo</th><th>C · Pedra-chave</th></tr>"
        "<tr><td>Legibilidade a 16–24 px</td><td class='c'>alta</td><td class='c'>máxima</td><td class='c'>média</td></tr>"
        "<tr><td>Identidade e ligação com o produto</td><td class='c'>alta (nome)</td><td class='c'>baixa</td><td class='c'>alta (runa-chave)</td></tr>"
        "<tr><td>Distinção (prateleira)</td><td class='c'>alta</td><td class='c'>média</td><td class='c'>média/alta</td></tr>"
        "<tr><td>Coerência com o app (quadrado, escuro)</td><td class='c'>máxima</td><td class='c'>alta</td><td class='c'>baixa (fundo claro, arco)</td></tr>"
        "<tr><td>Versatilidade (uma cor, animação, padrões)</td><td class='c'>alta</td><td class='c'>alta</td><td class='c'>média</td></tr>"
        "<tr><td>Risco principal</td><td class='c'>presa à versão 2</td><td class='c'>genérica</td><td class='c'>lê como ferradura/ímã</td></tr></table>"
    )

    P.append(
        "<h2 id='rec'>Recomendação</h2><div class='card' style='border-color:var(--red)'>"
        "<p class='lead' style='color:var(--fg)'><b>A · Dois em módulos</b>, com o corte pequeno de 16 e 24 px.</p>"
        "<ul class='t'><li>É a que mais pertence ao produto: o nome, a versão e o jeito quadrado, em campos, do app, em um único gesto.</li>"
        "<li>Passa nos testes de pequeno tamanho com folga, e o ponto vermelho é o mesmo acento que o app já usa.</li>"
        "<li>Dá um sistema: o mesmo módulo serve à abertura animada, ao favicon do painel e ao ícone da bandeja.</li></ul>"
        "<p><b>Segunda opção: B · Duelo</b>, se a prioridade for o impacto na barra de tarefas com o mínimo de desenho. <b>C · Pedra-chave</b> vale se o que mais importa é a história (a runa-chave), aceitando o fundo claro e o risco de ser lida como arco ou ferradura.</p>"
        "<p class='muted'>Riscos honestos: A depende do número 2 (a 3.0 pede revisão); B é a mais genérica; C destoa da paleta escura do app.</p></div>"
    )
    P.append(
        "<h2>O que acontece depois da sua escolha</h2><div class='card'><ol class='t next'>"
        "<li>Refinos finais da escolhida (você pode pedir ajustes de cor, proporção ou vala).</li>"
        "<li>Integração: <code>assets/sexo2.svg</code> e os derivados de <code>python scripts/render_icon.py</code> (ICO de 16 a 256, PNG da bandeja, aviso do Pengu, item de menu do cliente), conforme <code>docs/ICONE-NOVO.md</code>; teste <code>tests/test_icon.py</code> ajustado ao novo hash.</li>"
        "<li>Verificações: suíte Python, plugins, ruff, tokens e conferência visual no Windows real (barra, bandeja, instalador).</li>"
        "<li>Só então o fechamento da 2.0 na <code>gunderfrank</code>, sem publicar sem a sua autorização.</li></ol></div>"
    )
    P.append("</div></body></html>")
    return "".join(P)


if __name__ == "__main__":
    out = HERE / "apresentacao.html"
    out.write_text(page(), encoding="utf-8")
    print(f"escrito: {out} ({out.stat().st_size // 1024} KB)")
