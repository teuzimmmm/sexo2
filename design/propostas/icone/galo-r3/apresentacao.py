"""Monta `apresentacao.html`: o refino do conceito 1 (galo busto) do SEXO2.

    python design/propostas/icone/galo-r3/apresentacao.py

Reaproveita as simulações do Windows da primeira rodada (`../redesign-2.0/apresentacao.py`). Um arquivo só, com SVG,
PNG e fontes embutidos. Nada aqui altera `assets/` (decisão pendente). Requer cairosvg (só para gerar esta página).
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("rodada1", HERE.parent / "redesign-2.0" / "apresentacao.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

ANTERIOR = HERE.parent / "galo-r2" / "svg"


def svg_file(letter, small=False):
    if letter == "atual":
        return base.ATUAL
    if letter == "ant":  # o galo busto da rodada anterior
        return ANTERIOR / f"g1-{'pequeno' if small else 'icone'}.svg"
    return HERE / "svg" / f"{letter}-{'pequeno' if small else 'icone'}.svg"


base.svg_file = svg_file  # as simulações chamam esta função em tempo de execução
img, vector, taskbar, scenes = base.img, base.vector, base.taskbar, base.scenes

NOMES = {"a": "A · Firme e fluido", "b": "B · Mais fluido", "c": "C · Firme e fluido, com olho"}
MUDANCAS = [
    (
        "Barbela",
        "Era um triângulo vermelho pendurado abaixo do bico, com ar de peça solta. Agora é uma gota que nasce na base do bico e acompanha a linha da garganta, dentro do contorno da cabeça.",
        "Lê-se como parte do rosto, não como acessório, e continua presa à cabeça em 16 px.",
    ),
    (
        "Silhueta",
        "O contorno que era só reta virou reta e curva: as pontas da crista, o bico e os dentes do pescoço continuam firmes; os flancos da crista, a testa, a garganta e o peito passam a ser curvas de transição.",
        "Tira o ar de recorte em papel sem amolecer: nenhum círculo, nenhuma ponta arredondada.",
    ),
    (
        "Crista",
        "Mais encorpada, com flancos côncavos e ritmo: gancho à esquerda, ponta alta no centro, ponta inclinada à direita.",
        "Fica mais natural, menos coroa de espinhos, e segue sendo o traço que o ícone atual já tinha.",
    ),
    (
        "Bico e fresta",
        "O bico ficou um pouco mais curto (a ponta foi de 240 para 230) e o contorno de cima é uma curva suave. A fresta virou um fio curvo que afina na ponta, em vez de uma faixa reta.",
        "Menos focinho, mais bico; a fresta lê como linha da boca e mantém a assinatura do ícone atual.",
    ),
    (
        "Pescoço",
        "Dentes de penas em curva e uma varredura contínua do peito até a base, em vez de degraus retos.",
        "Dá ao busto uma postura (peito para a frente) e resolve a base, que antes parecia cortada à faca.",
    ),
    (
        "Proporções",
        "Cabeça mais cheia em relação ao pescoço e massa recentrada para a esquerda, já que o bico puxa o peso para a direita.",
        "O ícone fica equilibrado dentro do quadrado, com respiro à direita do bico.",
    ),
]
VARIACOES = [
    (
        "a",
        "Firme e fluido",
        "O ponto de equilíbrio: pontas e dentes firmes, transições em curva, olho ausente como no original.",
        ["Mais próximo do conceito 1 aprovado.", "A melhor leitura da barbela e da fresta em tamanho pequeno."],
        ["Bico ainda longo: em 16 px pode lembrar uma ave de rapina ou raposa."],
    ),
    (
        "b",
        "Mais fluido",
        "As mesmas peças com curvas mais soltas: crista em chama, barbela maior, pescoço mais sinuoso, fresta com ponta redonda.",
        ["O mais natural e o mais orgânico.", "Barbela mais cheia e bem integrada."],
        [
            "Chega perto do macio: a ponta redonda da fresta e a barbela cheia suavizam o que você quer firme.",
            "Perde um pouco da dureza do app.",
        ],
    ),
    (
        "c",
        "Firme e fluido, com olho",
        "A mesma forma da A com um olho em cunha acima da fresta.",
        ["O olho dá face ao galo e afasta a leitura de raposa.", "Em 16 px a fresta e o olho se separam bem."],
        [
            "O olho muda a personalidade: o ícone atual não tinha olho e o rosto fica mais “ilustração”.",
            "Mais um detalhe para se perder em 16 px.",
        ],
    ),
]


def page():
    P = [
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>SEXO2 · galo busto, refino</title><style>" + base.font_css() + base.CSS + "</style></head><body>",
        "<nav class='top'><a href='#mudou'>O que mudou</a><a href='#var'>Variações</a><a href='#peq'>Tamanhos</a><a href='#win'>Windows</a><a href='#rec'>Recomendação</a></nav><div class='wrap'>",
        "<h1>SEXO2 · galo busto, refino</h1><p class='lead'>Só o conceito 1, refinado: barbela integrada, silhueta menos geométrica, firme sem rigidez. Os conceitos 2 e 3 foram descartados. Nada foi aplicado: <code>assets/sexo2.svg</code> continua como está.</p>",
        "<div class='banner'><b>Material experimental</b> · só na branch <code>gunderfrank</code> · pasta <code>design/propostas/icone/galo-r3/</code>.</div>",
        "<h2>Antes e depois</h2><div class='card'><div style='display:flex;gap:24px;flex-wrap:wrap;align-items:flex-end'>",
    ]
    for k, n in (("atual", "Ícone atual (D-123)"), ("ant", "Galo busto, rodada anterior"), ("a", "Refino A")):
        P.append(
            f"<figure style='margin:0;text-align:center'>{vector(k, 280)}<figcaption class='muted' style='margin-top:6px'>{n}</figcaption></figure>"
        )
    P.append("</div></div>")

    P.append(
        "<h2 id='mudou'>O que mudou e por quê</h2><div class='card'><table><tr><th>Ponto</th><th>O que mudou</th><th>Por quê</th></tr>"
    )
    for a, b, c in MUDANCAS:
        P.append(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>")
    P.append("</table></div>")

    P.append("<h2 id='var'>As três variações</h2><div class='cols'>")
    for k, nome, ideia, fortes, riscos in VARIACOES:
        P.append(
            f"<div class='card'><div style='display:flex;justify-content:center'>{vector(k, 300)}</div><h3 style='margin-top:12px'>{k.upper()} · {nome}</h3><p class='muted'>{ideia}</p>"
            "<h4>Ganha</h4><ul class='t good'>"
            + "".join(f"<li>{x}</li>" for x in fortes)
            + "</ul><h4>Custa</h4><ul class='t bad'>"
            + "".join(f"<li>{x}</li>" for x in riscos)
            + "</ul></div>"
        )
    P.append("</div>")

    P.append(
        "<h2 id='peq'>Leitura em tamanhos pequenos</h2><p class='muted'>16 e 24 px usam o corte pequeno (fresta, barbela e olho mais grossos).</p>"
    )
    for cls in ("", "light"):
        P.append(f"<div class='ladder {cls}' style='margin-bottom:10px'>")
        for k in ("ant", "a", "b", "c"):
            P.append(
                f"<div style='display:flex;gap:14px;align-items:flex-end;margin-right:18px'>"
                + "".join(
                    f"<figure>{img(k, s)}<figcaption>{k.upper() if k != 'ant' else 'ant.'} {s}</figcaption></figure>"
                    for s in (16, 24, 32, 64)
                )
                + "</div>"
            )
        P.append("</div>")
    P.append("<div class='ladder light' style='align-items:center'>")
    for k in ("a", "b", "c"):
        mono = base.b64((HERE / "svg" / f"{k}-simbolo.svg").read_bytes())
        P.append(
            f"<figure><img src='data:image/svg+xml;base64,{mono}' width='110' height='110' alt=''><figcaption>{k.upper()} · uma cor</figcaption></figure>"
        )
    P.append("</div>")

    P.append("<h2 id='win'>Aplicações simuladas no Windows (variação A)</h2>" + scenes("a"))
    P.append("<h4>Na barra de tarefas, lado a lado</h4><div class='sc wide'>")
    for k, n in (("atual", "Atual"), ("ant", "Rodada anterior"), ("a", "A"), ("b", "B"), ("c", "C")):
        P.append(f"<p class='muted' style='margin:8px 0 2px'>{n}</p>{taskbar(k)}")
    P.append("</div>")

    P.append(
        "<h2 id='rec'>Recomendação</h2><div class='card' style='border-color:var(--red)'>"
        "<p class='lead' style='color:var(--fg)'><b>A · Firme e fluido.</b></p>"
        "<ul class='t'><li><b>Silhueta e firmeza:</b> pontas e dentes duros, transições em curva; é o que você descreveu.</li>"
        "<li><b>Integração:</b> a barbela agora pertence à cabeça, sem peça solta.</li>"
        "<li><b>Equity:</b> é o mesmo galo, com a fresta e a crista que o ícone atual já tinha.</li></ul>"
        "<p>A <b>B</b> é a que chega mais perto do macio e eu a evitaria. A <b>C</b> vale se o risco de raposa o incomodar: o olho resolve, ao custo de mudar a personalidade. Se quiser, testo A com o bico um pouco mais curto, sem olho.</p>"
        "<p class='muted'>Limites: as curvas foram desenhadas à mão e não passaram pelo ajuste final de ângulos; as simulações do Windows são desenhadas, não capturas do sistema real; nada foi integrado ao app.</p></div>"
        "</div></body></html>"
    )
    return "".join(P)


if __name__ == "__main__":
    out = HERE / "apresentacao.html"
    out.write_text(page(), encoding="utf-8")
    print(f"escrito: {out} ({out.stat().st_size // 1024} KB)")
