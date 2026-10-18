import hashlib, unicodedata

THEMES = [
    "Qualquer",
    "Arcane",
    "PROJETO",
    "Fliperama",
    "Guardiãs das Estrelas",
    "Curtindo o Verão",
    "Velho Oeste",
    "Florescer Espiritual",
]
ALIASES = {
    "Arcane": ["arcane"],
    "PROJETO": ["project", "projeto"],
    "Fliperama": ["arcade", "fliperama", "chefao"],
    "Guardiãs das Estrelas": [
        "star guardian",
        "star nemesis",
        "guardia estelar",
        "guardias das estrelas",
        "guardiao estelar",
    ],
    "Curtindo o Verão": ["pool party", "curtindo o verao", "ocean song", "cancao do oceano"],
    "Velho Oeste": ["high noon", "velho oeste"],
    "Florescer Espiritual": ["spirit blossom", "florescer espiritual"],
}


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text)).casefold() if not unicodedata.combining(c))


def eligible(skins, theme, excluded, available):
    if theme not in THEMES:
        raise ValueError("Temática desconhecida")
    aliases = [normalized(x) for x in ALIASES.get(theme, [])]
    result = []
    for skin in skins:
        sid = skin["skinId"]
        if sid % 1000 == 0 or skin.get("chroma") or sid in excluded:
            continue
        if aliases and not any(word in normalized(skin["name"]) for word in aliases):
            continue
        if not available(sid):
            continue
        result.append(skin)
    return sorted(result, key=lambda x: x["skinId"])


def draw(candidates, seed, summoner_id, champion_id):
    if not candidates:
        raise ValueError("Nenhuma skin disponível para esta temática. Ajuste o tema ou as exclusões.")
    value = hashlib.sha256(f"{seed}:{summoner_id}:{champion_id}".encode()).digest()
    return candidates[int.from_bytes(value, "big") % len(candidates)]
