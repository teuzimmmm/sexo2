"""Gera as opções de ícone do SEXO2 (D-121): um SVG por opção, o mesmo desenho em todos os tamanhos, e .ico.

    python design/propostas/icone/gerar.py          # só os SVG
    node design/propostas/icone/render.cjs          # PNG de cada tamanho (Chromium)
    python design/propostas/icone/gerar.py --ico    # junta os PNG em .ico

Desenho em grade de 256, só com formas básicas, para ler em 16 px. Cores: vermelho, branco quente e grafite.
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
RED = "#d2412f"
WHITE = "#f2efe9"
DARK = "#141518"


def tile(color):
    return f'<rect width="256" height="256" rx="58" fill="{color}"/>'


def galo(head, comb, eye, wattle=True):
    """Só formas básicas: três círculos de crista, um círculo de cabeça, um triângulo de bico."""
    barbela = (
        f'<path fill="{comb}" d="M178 176 C196 178 200 206 182 212 C166 214 162 188 178 176 Z"/>' if wattle else ""
    )
    # Crista e cabeça da mesma cor: um corte fino na cor do fundo separa as duas.
    cut = f' stroke="{eye}" stroke-width="10"' if head == comb else ""
    return f"""<g transform="translate(-6 0)">
<circle cx="96" cy="88" r="21" fill="{comb}"/><circle cx="130" cy="70" r="25" fill="{comb}"/><circle cx="166" cy="84" r="21" fill="{comb}"/>
<circle cx="130" cy="148" r="64" fill="{head}"{cut}/>
<path fill="{comb}" d="M186 126 L236 146 L186 166 Z"/>
{barbela}
<circle cx="150" cy="134" r="11" fill="{eye}"/></g>"""


def cabeca(head, comb, eye):
    return f"""<path fill="{comb}" d="M74 104 C64 78 82 58 104 70 C108 44 140 40 148 66 C162 50 190 60 182 88 Z"/>
<circle cx="128" cy="140" r="58" fill="{head}"/>
<path fill="{head}" d="M178 118 L224 140 L178 160 Z"/>
<path fill="{comb}" d="M162 186 C182 190 186 218 166 222 C150 222 146 198 162 186 Z"/>
<circle cx="146" cy="128" r="9" fill="{eye}"/>"""


def traco(line, eye):
    return f"""<g fill="none" stroke="{line}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round">
<path d="M84 104 C76 82 92 64 110 74 C114 52 142 48 148 72 C162 58 186 68 180 92"/>
<path d="M178 112 L214 132 L176 148"/>
<path d="M176 148 C170 196 120 214 88 196 C66 182 62 140 84 112 C100 94 140 90 170 104"/></g>
<circle cx="140" cy="126" r="9" fill="{eye}"/>"""


# id: (nome, desenho, descrição)
OPTIONS = {
    "a": (
        "Galo",
        tile(DARK) + galo(WHITE, RED, DARK, wattle=False),
        "Três círculos, um círculo e um triângulo. Cabeça branca, crista e bico vermelhos, fundo grafite.",
    ),
    "b": (
        "Galo com barbela",
        tile(DARK) + galo(WHITE, RED, DARK),
        "O mesmo, com a barbela: uma forma a mais que tira o ar de pintinho e deixa claro que é galo.",
    ),
    "c": (
        "Galo no vermelho",
        tile(RED) + galo(WHITE, WHITE, RED, wattle=False),
        "Uma marca branca sobre fundo vermelho, como o ícone do Claude: a cor inteira é o fundo.",
    ),
    "d": ("Galo no vermelho com barbela", tile(RED) + galo(WHITE, WHITE, RED), "O galo no vermelho, com a barbela."),
    "e": (
        "Galo preto",
        tile(WHITE) + galo(DARK, RED, WHITE),
        "Cabeça preta, crista vermelha, fundo claro: preto, branco e vermelho. Aparece bem em barra escura.",
    ),
    "f": (
        "Cabeça",
        tile(DARK) + cabeca(WHITE, RED, DARK),
        "Crista em uma peça só e cabeça branca; um pouco mais desenhado que o geométrico.",
    ),
    "g": (
        "Traço",
        tile(DARK) + traco(WHITE, RED),
        "O galo em uma linha contínua, com o olho vermelho. O mais leve; em 16 px perde força.",
    ),
}


def svg(inner):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">{inner}</svg>\n'


def write_svgs():
    out = HERE / "svg"
    out.mkdir(exist_ok=True)
    for key, (_name, drawing, _text) in OPTIONS.items():
        (out / f"{key}.svg").write_text(svg(drawing), encoding="utf-8")


SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def write_icos():
    from PIL import Image

    png, out = HERE / "png", HERE / "ico"
    out.mkdir(exist_ok=True)
    for key in OPTIONS:
        images = [Image.open(png / f"{key}-{size}.png").convert("RGBA") for size in SIZES]
        images[-1].save(out / f"{key}.ico", format="ICO", sizes=[(s, s) for s in SIZES], append_images=images[:-1])


if __name__ == "__main__":
    if "--ico" in sys.argv:
        write_icos()
    else:
        write_svgs()
