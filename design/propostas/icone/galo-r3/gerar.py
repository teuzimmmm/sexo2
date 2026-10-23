"""Refino do conceito 1 do SEXO2 (galo busto): variações A, B e C, só SVG estático, grade de 256.

    python design/propostas/icone/galo-r3/gerar.py

O que muda em relação ao galo busto da rodada anterior (`../galo-r2`):
- a silhueta passa a combinar facetas firmes (pontas da crista, bico, dentes do pescoço) com curvas de transição
  (flancos da crista, testa, garganta, peito), em vez de só retas;
- a barbela deixa de ser um triângulo solto: nasce na base do bico e acompanha a garganta, dentro do contorno;
- o bico fica um pouco mais curto, a crista mais encorpada e o pescoço ganha uma varredura contínua.
Cada variação sai em `-simbolo` (preto, sem fundo), `-icone` (cor, com fundo) e `-pequeno` (16 a 24 px).
Nada aqui toca `assets/sexo2.svg` (o oficial, D-123).
"""

from pathlib import Path

OUT = Path(__file__).parent / "svg"
INK = "#15171a"  # grafite do app
PAPER = "#ececec"  # branco do app
RED = "#d2412f"  # único acento
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-label="{t}">\n<title>{t}</title>\n'
DX = -6  # centragem óptica: a massa fica à esquerda do bico


def path(d, fill):
    return f'<path fill="{fill}" d="{d}"/>'


def save(name, title, body, fundo=""):
    shifted = f'<g transform="translate({DX} 0)">{body}</g>'
    (OUT / f"{name}.svg").write_text(HEAD.format(t=title) + fundo + shifted + "\n</svg>\n", encoding="utf-8")


def tile():
    return f'<rect width="256" height="256" fill="{INK}"/>'


# Contorno da cabeça, do alto do crânio no sentido horário. A crista é o único trecho que varia entre as versões.
CRISTA_A = (
    "M80 104 C74 92 70 74 72 56 C86 66 96 76 102 88 C104 72 107 54 112 38 C122 54 130 68 135 88 "
    "C143 78 150 66 156 54 C160 68 162 88 160 106"
)
CRISTA_B = (
    "M80 104 C72 92 66 74 70 54 C86 62 98 76 104 90 C104 72 108 54 114 34 C124 52 132 68 136 88 "
    "C146 76 152 66 160 50 C164 68 164 90 160 108"
)
ROSTO = "C166 112 172 118 178 122 C196 125 216 134 230 146 C216 152 198 160 178 167"
GARGANTA = "C177 180 174 192 168 206 C163 224 169 242 174 256"
PESCOCO = (
    "L46 256 C50 240 54 228 60 220 C54 214 46 206 40 198 C50 192 56 188 62 184 "
    "C58 176 52 164 46 152 C54 148 60 142 66 134 C70 124 74 114 80 104 Z"
)
PESCOCO_B = (
    "L46 256 C48 242 54 232 60 222 C52 218 44 210 38 200 C48 196 56 192 62 186 "
    "C56 178 50 166 44 154 C52 150 60 144 66 136 C70 126 74 114 80 104 Z"
)


def cabeca(crista, pescoco, rosto=ROSTO, garganta=GARGANTA):
    return f"{crista} {rosto} {garganta} {pescoco}"


# fresta: a linha da boca, um fio que afina na ponta do bico
FRESTA = "M228 147 C206 145 170 147 126 143 L128 151 C170 157 206 155 228 147 Z"
FRESTA_P = "M228 147 C206 144 170 145 126 139 L128 153 C170 159 206 157 228 147 Z"
FRESTA_B = "M228 147 C206 145 170 147 130 143 C126 147 126 150 130 152 C170 157 206 155 228 147 Z"
# barbela: nasce na base do bico, acompanha a garganta e fica dentro do contorno
BARBELA = "M178 167 C186 174 186 192 170 208 C160 198 156 184 160 174 C166 169 172 167 178 167 Z"
BARBELA_B = "M180 167 C192 176 188 196 170 212 C158 202 154 186 160 174 C166 169 174 166 180 167 Z"
BARBELA_P = "M178 167 C190 174 190 198 170 214 C158 202 154 186 158 174 C164 168 172 166 178 167 Z"
OLHO = "M140 128 L156 123.7 L158.5 133.4 L142.5 137.7 Z"
OLHO_P = "M136 127 L158 121.1 L161.6 134.6 L139.6 140.5 Z"

VARIACOES = [
    # nome, título, cabeça, fresta, barbela, olho (grande, pequeno)
    ("a", "A · Firme e fluido", cabeca(CRISTA_A, PESCOCO), FRESTA, BARBELA, None),
    ("b", "B · Mais fluido", cabeca(CRISTA_B, PESCOCO_B), FRESTA_B, BARBELA_B, None),
    ("c", "C · Firme e fluido, com olho", cabeca(CRISTA_A, PESCOCO), FRESTA, BARBELA, (OLHO, OLHO_P)),
]


def build():
    for nome, titulo, head, fresta, barbela, olho in VARIACOES:
        holes = fresta + (olho[0] if olho else "")
        mono = f'<path fill="#000" fill-rule="evenodd" d="{head}{holes}"/>' + path(barbela, "#000")
        save(f"{nome}-simbolo", f"{titulo} · símbolo", mono)
        cor = path(head, PAPER) + path(fresta, INK) + (path(olho[0], INK) if olho else "") + path(barbela, RED)
        save(f"{nome}-icone", titulo, cor, tile())
        pequeno = path(head, PAPER) + path(FRESTA_P, INK) + (path(olho[1], INK) if olho else "") + path(BARBELA_P, RED)
        save(f"{nome}-pequeno", f"{titulo} · 16 px", pequeno, tile())


if __name__ == "__main__":
    build()
