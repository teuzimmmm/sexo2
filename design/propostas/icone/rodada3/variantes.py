"""Variantes da rodada 3. Grade 256; só formas básicas; cores K, W e R."""

K, W, R = "#141518", "#f2efe9", "#d2412f"


def line(d, w=22, col=W):
    return (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" '
            f'stroke-linejoin="miter" stroke-linecap="butt" stroke-miterlimit="6"/>')


def poly(d, col):
    return f'<path d="{d}" fill="{col}"/>'


def tile(col=K):
    return f'<rect width="256" height="256" rx="58" fill="{col}"/>'


# Contorno comum da família traço: cabeça virada para a direita, crista de 3 pontas, barbela.
HEAD = "M64 154 L78 108 L102 98 L106 54 L130 82 L150 44 L168 84 L190 66 L186 106 L230 134 L182 152 L174 198 L126 216 L78 194 Z"
BROW = "M98 112 L190 134"          # sobrancelha: desce em direção ao bico
EYE = "M122 136 L176 146 L142 162 Z"  # olho em lâmina logo abaixo da sobrancelha
SHIELD = "M128 22 L222 50 L214 150 L128 236 L42 150 L34 50 Z"


def scaled(inner, s=0.74, dx=0, dy=0):
    """Reduz o desenho e o centra (sem mudar o traço relativo)."""
    t = (1 - s) * 128
    return f'<g transform="translate({t + dx:.1f} {t + dy:.1f}) scale({s})">{inner}</g>'


V = {}
V["L1"] = ("Sobrancelha", "traço", "Contorno fechado, sobrancelha que desce sobre o olho vermelho em lâmina.",
           tile() + line(HEAD, 20) + line(BROW, 18) + poly(EYE, R))
V["L2"] = ("Olho vazado", "traço", "O mesmo desenho sem vermelho: o olho é um corte no fundo. Serve em uma cor só.",
           tile() + line(HEAD, 20) + line(BROW, 18) + poly(EYE, K))
V["L3"] = ("Traço pesado", "traço", "Sem sobrancelha e com linha grossa (26): contorno forte, só o olho como detalhe.",
           tile() + line(HEAD, 26) + poly("M118 124 L174 134 L140 154 Z", R))
V["L4"] = ("Escudo", "traço", "O mesmo galo dentro de um escudo vermelho; o olho passa a ser grafite.",
           tile() + poly(SHIELD, R) + scaled(line(HEAD, 26) + line(BROW, 22) + poly(EYE, K), 0.64, -6, 16))
V["L5"] = ("Fundo vermelho", "traço", "Fundo colorido, como um ícone de marca: traço claro, olho grafite.",
           tile(R) + line(HEAD, 20) + line(BROW, 18) + poly(EYE, K))
V["L6"] = ("Nuca aberta", "traço", "A linha nasce no pescoço e termina solta embaixo: menos peso, mais gesto.",
           tile() + line("M70 218 L64 154 L78 108 L102 98 L106 54 L130 82 L150 44 L168 84 L190 66 L186 106 L230 134 L182 152 L174 198 L130 224", 22)
           + line(BROW, 18) + poly(EYE, R))
V["L7"] = ("Crista simples", "traço", "Crista de duas pontas e menos vértices: o mais limpo em 16 px.",
           tile() + line("M66 152 L80 106 L104 98 L112 52 L142 84 L172 50 L186 106 L230 134 L182 152 L172 196 L126 214 L80 192 Z", 22)
           + line("M104 114 L190 136", 18) + poly("M124 138 L178 148 L144 164 Z", R))
V["L8"] = ("Barbela vermelha", "traço", "Dois toques de vermelho, olho e barbela: lê como galo mesmo sem crista.",
           tile() + line(HEAD, 20) + line(BROW, 18) + poly(EYE, R) + poly("M170 160 L196 164 L184 210 Z", R))
# Família angular: massa sólida, sem contorno.
SIL = "M64 154 L78 108 L102 98 L106 54 L130 82 L150 44 L168 84 L190 66 L186 106 L230 134 L182 152 L174 198 L126 216 L78 194 Z"
V["R1"] = ("Silhueta", "angular", "Uma massa branca (crista, cabeça e bico juntos); o único detalhe é o olho vermelho.",
           tile() + poly(SIL, W) + poly("M112 120 L184 132 L140 150 Z", R))
V["R2"] = ("Crista vermelha", "angular", "Cabeça branca e crista vermelha em três pontas; olho grafite em fenda.",
           tile() + poly("M78 108 L102 98 L190 106 L230 134 L182 152 L174 198 L126 216 L78 194 L64 154 Z", W)
           + poly("M100 100 L106 54 L130 82 L150 44 L168 84 L190 66 L190 106 Z", R) + poly("M114 126 L184 136 L142 152 Z", K))
V["R3"] = ("Silhueta sobre vermelho", "angular", "A silhueta clara no fundo vermelho; o olho vira grafite.",
           tile(R) + poly(SIL, W) + poly("M112 120 L184 132 L140 150 Z", K))
V["R4"] = ("Corte na crista", "angular", "Silhueta branca cortada por uma fresta diagonal (espaço vazio) que separa crista e cabeça.",
           tile() + poly(SIL, W) + poly("M60 114 L196 128 L196 138 L60 124 Z", K) + poly("M126 148 L186 140 L150 166 Z", R))

# Centragem comum: o desenho (sem o fundo) desce e vai um pouco para a esquerda.
for _k, _v in list(V.items()):
    if _k == "L4":
        continue
    _s = _v[-1]
    _i = _s.index("/>") + 2
    V[_k] = _v[:-1] + (_s[:_i] + '<g transform="translate(-12 6)">' + _s[_i:] + "</g>",)
