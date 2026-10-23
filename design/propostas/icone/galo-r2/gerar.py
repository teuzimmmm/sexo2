"""Gera a segunda rodada de ícones do SEXO2 (o galo como núcleo): três territórios, só SVG estático, grade de 256.

    python design/propostas/icone/galo-r2/gerar.py

Cada território sai em `-simbolo` (preto, sem fundo), `-icone` (cor, com fundo) e `-pequeno` (corte para 16 a 24 px).
Nada aqui toca `assets/sexo2.svg` (o oficial, D-123).
"""

import math
from pathlib import Path

OUT = Path(__file__).parent / "svg"
INK = "#15171a"  # grafite do app
PAPER = "#ececec"  # branco do app
GREY = "#a4a9b0"  # segundo plano do galo plano (token fg-2)
RED = "#d2412f"  # único acento
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-label="{t}">\n<title>{t}</title>\n'


def save(name, title, body):
    (OUT / f"{name}.svg").write_text(HEAD.format(t=title) + body + "\n</svg>\n", encoding="utf-8")


def tile(color):
    return f'<rect width="256" height="256" fill="{color}"/>'


def path(d, fill):
    return f'<path fill="{fill}" d="{d}"/>'


def pts(*xy):
    return (
        "M" + " L".join(f"{x:.1f}".rstrip("0").rstrip(".") + f" {y:.1f}".rstrip("0").rstrip(".") for x, y in xy) + "Z"
    )


def shift(body, dx, dy=0, k=1.0):
    """Centragem óptica: desloca e, se preciso, escala em torno do centro da grade."""
    t = f"translate({dx + 128 * (1 - k):g} {dy + 128 * (1 - k):g})" + (f" scale({k})" if k != 1 else "")
    return f'<g transform="{t}">{body}</g>'


def solid(d, *holes):
    """Forma com furos de verdade (evenodd), para a versão de uma cor."""
    return f'<path fill="#000" fill-rule="evenodd" d="{d}{"".join(holes)}"/>'


# Cada galo devolve partes: `paper` (formas claras), `holes` (furos escuros, dentro das claras), `red` (acento) e,
# no galo plano, `grey`. A versão colorida pinta os furos com o grafite; a de uma cor usa furos de verdade.
def render(parts, ink, paper, grey, red, dx=0, k=1.0):
    out = "".join(path(d, paper) for d in parts["paper"])
    out += "".join(path(d, grey) for d in parts.get("grey", []))
    out += "".join(path(d, ink) for d in parts["holes"])
    out += "".join(path(d, red) for d in parts["red"])
    return shift(out, dx, 0, k)


def mono(parts, dx=0, k=1.0):
    holes = "".join(parts["holes"])
    body = "".join(solid(d, holes) if i == 0 else solid(d) for i, d in enumerate(parts["paper"]))
    body += "".join(solid(d) for d in parts.get("grey", []))
    body += "".join(solid(d) for d in parts["red"])
    return shift(body, dx, 0, k)


def emit(n, title, parts, dx, small_parts, k=1.0):
    save(f"{n}-simbolo", f"{title} · símbolo", mono(parts, dx, k))
    save(f"{n}-icone", title, tile(INK) + render(parts, INK, PAPER, GREY, RED, dx, k))
    save(f"{n}-pequeno", f"{title} · 16 px", tile(INK) + render(small_parts, INK, PAPER, GREY, RED, dx, k))


# ----------------------------------------------------------------------------- 1 · Galo busto (evolução)
# Os traços do ícone antigo, redesenhados: crista de três pontas, bico em cunha, a fresta (agora a linha da boca),
# a barbela vermelha e o pescoço de penas em dentes. Corta embaixo (busto sangrando), como um retrato.
def busto(small=False):
    head = pts((80, 102), (72, 54), (100, 84), (112, 36), (134, 84), (156, 52), (160, 104), (176, 120), (240, 146), (176, 168),
               (168, 192), (158, 226), (156, 256), (46, 256), (60, 224), (40, 198), (62, 176), (46, 150), (68, 126))  # fmt: skip
    if small:  # fresta e barbela mais grossas para segurar em 16 px
        slit = pts((236, 146), (180, 148), (126, 140), (126, 160), (180, 162))
        wattle = pts((168, 176), (206, 172), (180, 224))
    else:
        slit = pts((236, 146), (180, 150), (126, 144), (126, 156), (180, 158))
        wattle = pts((170, 176), (198, 174), (178, 214))
    return dict(paper=[head], holes=[slit], red=[wattle])


def build_busto():
    emit("g1", "1 · Galo busto", busto(), -10, busto(True))


# ----------------------------------------------------------------------------- 2 · Galo plano (abstração)
# O galo em planos: um branco (crânio e bico), um cinza (maxilar e pescoço), separados pela fresta; crista e barbela
# vermelhas, como no animal. Sem pescoço: a cabeça flutua, como uma dobradura.
def plano(small=False):
    g = 8 if small else 6  # fresta entre os planos
    skull = pts((66, 154 - g / 2), (80, 104), (156, 96), (176, 122), (230, 148), (230, 154 - g / 2))
    low = pts((66, 154 + g / 2), (230, 148 + g / 2), (178, 154 + g / 2), (168, 190), (128, 226), (86, 204))
    comb = pts((80, 104), (74, 56), (100, 86), (112, 38), (134, 90), (156, 56), (156, 96))
    wattle = pts((172, 168), (200, 166), (182, 206))
    eye = pts((132, 124), (156, 118), (152, 138)) if small else pts((136, 124), (154, 120), (150, 134))
    return dict(paper=[skull], grey=[low], holes=[eye], red=[comb, wattle])


def build_plano():
    emit("g2", "2 · Galo plano", plano(), -22, plano(True), 1.12)


# ----------------------------------------------------------------------------- 3 · Galo-2 (signo)
# O 2 é o galo: a curva de cima é a cabeça (crista no alto, bico à esquerda, olho, barbela); a diagonal e a base
# são o pescoço e o corpo. Lê-se como número e como galo.
def pol(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy - r * math.sin(a)


def dois(small=False):
    cx, cy, ro, ri = 128, 120, 72, 32
    a0, a1 = 190, -35
    f = lambda p: "%.1f %.1f" % p
    ring = (
        f"M{f(pol(cx, cy, ro, a0))}A{ro} {ro} 0 1 1 {f(pol(cx, cy, ro, a1))}"
        f"L{f(pol(cx, cy, ri, a1))}A{ri} {ri} 0 1 0 {f(pol(cx, cy, ri, a0))}Z"
    )
    body = pts(pol(cx, cy, ro - 4, a1 + 14), pol(cx, cy, ro, a1), (206, 202), (206, 238), (52, 238), (52, 202), (146, 158),
               pol(cx, cy, ri, a1), pol(cx, cy, ri + 4, a1 + 14))  # fmt: skip
    beak = pts(pol(cx, cy, ro, a0), (12, 144), (56, 164), pol(cx, cy, ri, a0))
    angs = (158, 128, 98) if small else (160, 138, 116, 94)  # a crista nasce no alto da cabeça (a curva do 2)
    lift = 52 if small else 46
    base = [pol(cx, cy, ro - 2, a) for a in angs]
    comb = [base[0]]
    for i in range(len(base) - 1):
        comb += [((base[i][0] + base[i + 1][0]) / 2 - 2, min(base[i][1], base[i + 1][1]) - lift + 12), base[i + 1]]
    wattle = pts((58, 166), (94, 158), (68, 204))
    eye = pts((66, 110), (88, 106), (80, 122)) if small else pts((68, 111), (86, 108), (80, 121))
    return dict(paper=[ring, body, beak], holes=[eye], red=[pts(*comb), wattle])


def build_dois():
    emit("g3", "3 · Galo-2", dois(), 18, dois(True))


if __name__ == "__main__":
    build_busto()
    build_plano()
    build_dois()
