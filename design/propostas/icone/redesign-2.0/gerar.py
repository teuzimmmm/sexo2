"""Gera as três propostas de ícone do SEXO2 (redesign antes da 2.0). Só SVG estático, grade de 256.

    python design/propostas/icone/redesign-2.0/gerar.py

Cada proposta sai em três arquivos: `-simbolo` (preto, sem fundo), `-icone` (cor, com fundo) e
`-pequeno` (corte para 16 a 24 px). Nada aqui toca `assets/sexo2.svg` (o oficial, D-123).
"""

import math
from pathlib import Path

OUT = Path(__file__).parent / "svg"
INK = "#15171a"  # grafite do app (tokens)
PAPER = "#ececec"  # branco do app
RED = "#d2412f"  # único acento
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-label="{t}">\n<title>{t}</title>\n'


def save(name, title, body):
    (OUT / f"{name}.svg").write_text(HEAD.format(t=title) + body + "\n</svg>\n", encoding="utf-8")


def rect(x, y, w, h, fill):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'


# ---------------------------------------------------------------- A · Dois em módulos (numeral)
# Um "2" de matriz 3x5; módulos 36x28 com vala de 6. A vala some em tamanho pequeno e o 2 fica inteiro.
A_CELLS = ["###", "..#", "###", "#..", "###"]


def a_modules(color, red, x0, y0, w, h, g, red_cell):
    out = []
    for r, row in enumerate(A_CELLS):
        for c, ch in enumerate(row):
            if ch == "#":
                fill = red if (r, c) == red_cell else color
                out.append(rect(x0 + c * (w + g), y0 + r * (h + g), w, h, fill))
    return "".join(out)


def build_a():
    mods = dict(x0=59, y0=36, w=42, h=32, g=6, red_cell=(2, 1))
    save("a-simbolo", "A · Dois em módulos · símbolo", a_modules("#000", "#000", **mods))
    save("a-icone", "A · Dois em módulos", rect(0, 0, 256, 256, INK) + a_modules(PAPER, RED, **mods))
    small = dict(
        x0=56, y0=48, w=48, h=32, g=0, red_cell=(2, 1)
    )  # sem vala; módulos de 3x2 px a 16 px (grade de 16 unidades = 1 px)
    save("a-pequeno", "A · Dois em módulos · 16 px", rect(0, 0, 256, 256, INK) + a_modules(PAPER, RED, **small))


# ---------------------------------------------------------------- B · Sobreposição (abstrato)
def lamina(pts, fill):
    return f'<path fill="{fill}" d="M{" L".join("%g %g" % p for p in pts)}Z"/>'


def duelo(x0, s, gap, slide, top, bottom):
    """Um quadrado cortado na diagonal; as duas metades se afastam e deslizam uma contra a outra."""
    x1 = x0 + s
    up = [
        (x0 - gap + slide, x0 - gap - slide),
        (x1 - gap + slide, x0 - gap - slide),
        (x0 - gap + slide, x1 - gap - slide),
    ]
    low = [
        (x1 + gap - slide, x0 + gap + slide),
        (x1 + gap - slide, x1 + gap + slide),
        (x0 + gap - slide, x1 + gap + slide),
    ]
    return lamina(up, top) + lamina(low, bottom)


def build_b():
    # Dois lados (equipe, confronto) separados pela fresta diagonal; a do app antigo era uma fresta horizontal.
    save("b-simbolo", "B · Duelo · símbolo", duelo(52, 152, 6, 14, "#000", "#000"))
    save("b-icone", "B · Duelo", rect(0, 0, 256, 256, INK) + duelo(52, 152, 6, 14, PAPER, RED))
    save("b-pequeno", "B · Duelo · 16 px", rect(0, 0, 256, 256, INK) + duelo(48, 160, 8, 16, PAPER, RED))


# ---------------------------------------------------------------- C · Pedra-chave (emblema)
def edge_point(cx, cy, r, deg, s):
    """Ponto da borda radial de `deg` graus deslocada s unidades de lado, no círculo de raio r (a borda segue a 60°/120° exatos)."""
    a = math.radians(deg)
    t = math.sqrt(r * r - s * s)
    return cx + t * math.cos(a) - s * math.sin(a), cy - t * math.sin(a) - s * math.cos(a)


def voussoir(cx, cy, r_in, r_out, a0, a1, h0, h1):
    """Peça do arco entre os ângulos a0 e a1; h0 e h1 são os afastamentos das bordas (0 = rente à base)."""
    o0, o1 = edge_point(cx, cy, r_out, a0, h0), edge_point(cx, cy, r_out, a1, -h1)
    i1, i0 = edge_point(cx, cy, r_in, a1, -h1), edge_point(cx, cy, r_in, a0, h0)
    f = lambda pt: "%.2f %.2f" % pt
    return f"M{f(o0)}A{r_out} {r_out} 0 0 0 {f(o1)}L{f(i1)}A{r_in} {r_in} 0 0 1 {f(i0)}Z"


def arco(cx, cy, r_in, r_out, half, base, bottom, ink, key):
    cuts = [0, 60, 120, 180]  # três peças de 60°: ângulos limpos; a do meio é a pedra-chave
    pieces = []
    for i in range(3):
        h0 = half if i else 0
        h1 = half if i < 2 else 0
        pieces.append((voussoir(cx, cy, r_in, r_out, cuts[i], cuts[i + 1], h0, h1), i == 1))
    legs = [
        (f"M{cx - r_out} {cy + base}H{cx - r_in}V{bottom}H{cx - r_out}Z", False),
        (f"M{cx + r_in} {cy + base}H{cx + r_out}V{bottom}H{cx + r_in}Z", False),
    ]
    return "".join(f'<path fill="{key if k else ink}" d="{d}"/>' for d, k in pieces + legs)


def build_c():
    main = (128, 138, 44, 92, 3, 6, 212)  # vala de 6
    small = (128, 136, 40, 96, 8, 16, 216)  # vala de 16 unidades = 1 px a 16 px; tudo em múltiplos de 8
    save("c-simbolo", "C · Pedra-chave · símbolo", arco(*main, "#000", "#000"))
    save("c-icone", "C · Pedra-chave", rect(0, 0, 256, 256, PAPER) + arco(*main, INK, RED))
    save("c-pequeno", "C · Pedra-chave · 16 px", rect(0, 0, 256, 256, PAPER) + arco(*small, INK, RED))


if __name__ == "__main__":
    build_a()
    build_b()
    build_c()
