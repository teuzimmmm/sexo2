"""Seleção aleatória ponderada de skins e cromas para o SEXO2.

Substitui o sorteio uniforme (`friends/lottery.py::draw`) por um sorteio com
pesos que favorece favoritas, skins de gacha e skins históricas excepcionais,
mantendo surpresa (nunca proíbe repetição). Cromas também entram no sorteio,
com peso influenciado pela raridade que o cliente informa; para que skins com
muitas variantes não dominem, o peso total dos cromas de uma skin é limitado
(fração fixa do peso da própria skin).

Somente biblioteca padrão. Sem aprendizado de máquina, sem estado global e sem
persistência: a "memória" de uso recente é apenas a lista `recent` recebida por
parâmetro.

Formato aceito para cada candidata (mesmo dicionário do catálogo do SEXO2, com
campos opcionais que a integração deve preservar do cliente):

    Skin:
    {
        "skinId": 4001,              # obrigatório (int)
        "name": "PAX Twisted Fate",  # opcional, só informativo
        "rarity": "kNoRarity",       # opcional: token de raridade do cliente
        "favorite": False,           # opcional: atalho para favorita
        "popular": False,            # opcional: atalho para skin famosa
    }

    Croma:
    {
        "skinId": 1014,              # obrigatório (int), id do croma
        "chroma": True,              # obrigatório para identificar variação
        "baseSkinId": 1013,          # obrigatório: skin à qual o croma pertence
        "chromaRarity": 2,           # opcional: inteiro de `rarities[].rarity`
        "favorite": False,           # opcional
    }

Tokens de raridade do cliente (mesmos valores de
/lol-game-data/assets/v1/champions/{id}.json -> skins[].rarity e de
CommunityDragon /v1/champions/{id}.json): kNoRarity, kEpic, kRare,
kLegendary, kMythic, kUltimate, kTranscendent, kExalted.

Raridade de croma: o cliente expõe, dentro de cada skin, o campo
`chromas[].rarities` como `[{"region": "riot", "rarity": <int>}]`. Esse inteiro
é o único sinal verificado; nenhuma categoria nominal é inventada aqui.
"""

from __future__ import annotations

import random

# --- Pesos por categoria ---------------------------------------------------
# Escala arbitrária; importa a razão entre os valores. Diretrizes do pedido:
# favoritas acima de tudo, gacha e Transcendent empatados no topo das raridades
# (decisão de produto), demais raridades progressivamente menores.
RARITY_WEIGHT = {
    "kNoRarity": 1.0,  # base: standard, budget, timeworn
    "kEpic": 2.0,  # normal
    "kLegendary": 4.0,  # intermediária
    "kRare": 8.0,  # limitadas/era (Victorious, Arcane, Conqueror)
    "kMythic": 8.0,  # míticas e prestígio
    "kUltimate": 8.0,  # alta
    "kTranscendent": 16.0,  # igualado ao gacha (decisão de produto)
    "kExalted": 16.0,  # gacha (The Sanctum)
}
DEFAULT_RARITY_WEIGHT = RARITY_WEIGHT["kNoRarity"]

GACHA_WEIGHT = RARITY_WEIGHT["kExalted"]
HISTORIC_WEIGHT = 16.0  # igual ao gacha, por decisão de produto

FAVORITE_BONUS = 20.0  # > qualquer peso de categoria, garante prioridade máxima
POPULARITY_BONUS = 3.0  # bônus adicional moderado

# Histórico recente: fator multiplicativo com piso, para nunca zerar a chance.
RECENCY_DECAY = 0.3
RECENCY_FLOOR = 0.05
RECENT_WINDOW = 10  # só as últimas N escolhas contam

GACHA_RARITIES = frozenset({"kExalted"})

# --- Cromas ----------------------------------------------------------------
# O peso total dos cromas de uma skin é limitado a esta fração do peso-base da
# própria skin. Assim, ter 1 ou 25 variantes não aumenta a presença da skin no
# sorteio: muda só a divisão interna entre os cromas dela.
CHROMA_FAMILY_SHARE = 0.5
# +50% no fator de um croma por ponto de raridade do cliente (`chromaRarity`).
CHROMA_RARITY_STEP = 0.5
# Orçamento de cromas quando a skin-base não está entre as candidatas.
CHROMA_FAMILY_FALLBACK = 1.0

# Skins cujas transformações dependem do atalho CTRL+5 no cliente. Aplicar um
# croma nelas desabilita o CTRL+5, então TODOS os cromas dessas skins ficam
# fora do sorteio (mesmo favoritos); só a versão original é elegível.
#
# Isto NÃO é "toda skin Exalted": a lista reúne quem o SEXO2 já modela como
# forma (`ui/chroma/special_cases.py`) ou quem o cliente marca com
# `questSkinInfo` (tiers). Validar no jogo antes de ampliar; editar basta.
FORM_TOGGLE_SKIN_IDS = frozenset(
    {
        99007,  # Elementalist Lux
        82054,  # Sahn-Uzal Mordekaiser
        25080,  # Spirit Blossom Morgana
        875066,  # Radiant Serpent Sett
        147001,  # K/DA ALL OUT Seraphine
        234043,  # Revenant Reign Viego
        21016,  # Gun Goddess Miss Fortune
        145070,  # Risen Legend Kai'Sa
        103085,  # Risen Legend Ahri
        18079,  # Risen Legend Tristana
    }
)

# Skins históricas excepcionais: peso equivalente ao gacha.
# Lista obrigatória do pedido (IDs conferidos no cliente/CommunityDragon).
HISTORIC_MANDATORY_SKIN_IDS = frozenset(
    {
        4001,  # PAX Twisted Fate — Twisted Fate
        24004,  # PAX Jax — Jax
        15005,  # PAX Sivir — Sivir (não confundir com Neo PAX Sivir 15009)
        12001,  # Black Alistar — Alistar
        10001,  # Silver Kayle — Kayle
        13001,  # Young Ryze — Ryze
        33001,  # King Rammus — Rammus
        10005,  # Judgment Kayle — Kayle
        59004,  # Victorious Jarvan IV — Jarvan IV
        27001,  # Riot Squad Singed — Singed
        42001,  # UFO Corki — Corki
        53001,  # Rusty Blitzcrank — Blitzcrank
    }
)
# Candidatas fundamentadas em pesquisa.md (história/disponibilidade). Todas são
# obtidas apenas por evento/época e não voltam à loja por meios convencionais.
# Remova itens daqui se a equipe decidir restringir.
HISTORIC_EXTRA_SKIN_IDS = frozenset(
    {
        1001,  # Goth Annie (Digital Collector's Pack)
        10007,  # Riot Kayle
        12005,  # Unchained Alistar
        18001,  # Riot Girl Tristana
        19001,  # Grey Warwick
        19002,  # Urf the Manatee
        19009,  # Urfwick
        75004,  # Riot K-9 Nasus
        53007,  # Riot Blitzcrank
        92004,  # Worlds 2012 Riven
        104004,  # Riot Graves
    }
)
HISTORIC_SKIN_IDS = HISTORIC_MANDATORY_SKIN_IDS | HISTORIC_EXTRA_SKIN_IDS

# Skins famosas/admiradas pela comunidade: bônus adicional. Lista curada e
# editável (não é uma classificação oficial da Riot); ver ressalvas em
# pesquisa.md.
POPULAR_SKIN_IDS = frozenset(
    {
        99007,  # Elementalist Lux
        77003,  # Spirit Guard Udyr
        37006,  # DJ Sona
        21016,  # Gun Goddess Miss Fortune
        81005,  # Pulsefire Ezreal
        157002,  # PROJECT: Yasuo
        222004,  # Star Guardian Jinx
        84009,  # K/DA Akali
        245019,  # True Damage Ekko
        122015,  # God-King Darius
        157009,  # Nightbringer Yasuo
        412005,  # Dark Star Thresh
        23004,  # Demonblade Tryndamere
        45008,  # Final Boss Veigar
        51011,  # Pulsefire Caitlyn
        92003,  # Battle Bunny Riven
    }
)


def is_chroma(skin):
    """True quando o candidato é um croma (variação de outra skin)."""
    return bool(skin.get("chroma"))


def skin_id(skin):
    return skin.get("skinId")


def category_weight(skin, historic_ids=HISTORIC_SKIN_IDS):
    """Peso-base pela categoria mais alta aplicável (nunca soma sobreposições)."""
    value = RARITY_WEIGHT.get(skin.get("rarity"), DEFAULT_RARITY_WEIGHT)
    if skin.get("rarity") in GACHA_RARITIES or skin.get("gacha"):
        value = max(value, GACHA_WEIGHT)
    if skin.get("skinId") in historic_ids or skin.get("historic"):
        value = max(value, HISTORIC_WEIGHT)
    return value


def chroma_rarity_factor(rarity):
    """Fator relativo de um croma a partir do inteiro `rarities[].rarity`.

    Ausente/ inválido equivale a 1.0 (baseline). Nunca é zero.
    """
    if rarity is None:
        return 1.0
    try:
        value = int(rarity)
    except (TypeError, ValueError):
        return 1.0
    return 1.0 + CHROMA_RARITY_STEP * max(0, value)


def form_toggle_chromas_excluded(skin, form_toggle_ids=FORM_TOGGLE_SKIN_IDS):
    """True se o candidato é um croma que deve sumir do sorteio (regra CTRL+5)."""
    return is_chroma(skin) and skin.get("baseSkinId") in form_toggle_ids


def recency_factor(recent_count):
    """Fator de decaimento por uso recente. Nunca chega a zero."""
    return max(RECENCY_FLOOR, RECENCY_DECAY**recent_count)


def recent_counts(recent, window=RECENT_WINDOW):
    """Conta ocorrências na janela recente (as primeiras `window` escolhas)."""
    counts = {}
    for sid in list(recent)[:window]:
        counts[sid] = counts.get(sid, 0) + 1
    return counts


def skin_weight(
    skin,
    *,
    favorite=False,
    recent_count=0,
    historic_ids=HISTORIC_SKIN_IDS,
    popular_ids=POPULAR_SKIN_IDS,
    form_toggle_ids=FORM_TOGGLE_SKIN_IDS,
):
    """Peso final de uma candidata isolada (croma tratado como família de 1).

    Para o sorteio real use `weights`/`select_skin`, que normaliza os cromas em
    conjunto. Aqui serve para inspeção e para testes de bônus.

    Peso = categoria + bônus favorita + bônus popularidade, tudo multiplicado
    pelo fator de uso recente. Sobreposições de categoria usam o máximo (não
    somam); bônus são aditivos e moderados.
    """
    if form_toggle_chromas_excluded(skin, form_toggle_ids):
        return 0.0
    if is_chroma(skin):
        weight = CHROMA_FAMILY_SHARE * CHROMA_FAMILY_FALLBACK * chroma_rarity_factor(skin.get("chromaRarity"))
    else:
        weight = category_weight(skin, historic_ids)
    if favorite or skin.get("favorite"):
        weight += FAVORITE_BONUS
    if skin.get("popular") or skin.get("skinId") in popular_ids:
        weight += POPULARITY_BONUS
    return weight * recency_factor(recent_count)


def weights(
    skins,
    *,
    favorites=(),
    recent=(),
    historic_ids=HISTORIC_SKIN_IDS,
    popular_ids=POPULAR_SKIN_IDS,
    available=None,
    form_toggle_ids=FORM_TOGGLE_SKIN_IDS,
):
    """Pesos na mesma ordem de `skins`.

    Regras de cromas:
    - `available(sid)` (opcional) zera candidatas indisponíveis, cromas inclusive;
    - cromas de skins com CTRL+5 (`form_toggle_ids`) são zerados **antes** de
      qualquer bônus, mesmo se favoritos;
    - entre os cromas restantes de uma mesma `baseSkinId`, o peso total é
      limitado a `CHROMA_FAMILY_SHARE * categoria(baseSkinId)` e dividido pela
      raridade relativa, de modo que a quantidade de variantes não aumenta a
      presença da skin no sorteio.
    """
    skins = list(skins)
    favorites = frozenset(favorites)
    counts = recent_counts(recent)

    base_category = {}
    for skin in skins:
        if not is_chroma(skin):
            base_category[skin.get("skinId")] = category_weight(skin, historic_ids)

    chroma_factor = {}  # index -> fator de raridade (só disponíveis e sem CTRL+5)
    group_total = {}  # baseSkinId -> soma dos fatores do grupo disponível
    for index, skin in enumerate(skins):
        if not is_chroma(skin) or form_toggle_chromas_excluded(skin, form_toggle_ids):
            continue
        if available is not None and not available(skin.get("skinId")):
            continue
        base = skin.get("baseSkinId")
        factor = chroma_rarity_factor(skin.get("chromaRarity"))
        chroma_factor[index] = factor
        group_total[base] = group_total.get(base, 0.0) + factor

    result = []
    for index, skin in enumerate(skins):
        sid = skin.get("skinId")
        if available is not None and not available(sid):
            result.append(0.0)
            continue
        if form_toggle_chromas_excluded(skin, form_toggle_ids):
            result.append(0.0)
            continue
        if is_chroma(skin):
            base = skin.get("baseSkinId")
            base_cat = base_category.get(base, CHROMA_FAMILY_FALLBACK)
            value = CHROMA_FAMILY_SHARE * base_cat * (chroma_factor[index] / group_total[base])
        else:
            value = base_category.get(sid, category_weight(skin, historic_ids))
        if sid in favorites or skin.get("favorite"):
            value += FAVORITE_BONUS
        if skin.get("popular") or sid in popular_ids:
            value += POPULARITY_BONUS
        result.append(value * recency_factor(counts.get(sid, 0)))
    return result


def probabilities(skins, **kwargs):
    """Probabilidade normalizada de cada candidata, na mesma ordem de `skins`."""
    values = weights(skins, **kwargs)
    total = sum(values)
    if total <= 0:
        return [0.0] * len(values)
    return [value / total for value in values]


def select_skin(
    skins,
    *,
    favorites=(),
    recent=(),
    rng=None,
    historic_ids=HISTORIC_SKIN_IDS,
    popular_ids=POPULAR_SKIN_IDS,
    available=None,
    form_toggle_ids=FORM_TOGGLE_SKIN_IDS,
):
    """Escolhe e devolve uma candidata (o próprio dicionário) por sorteio ponderado.

    - `rng`: `random.Random` (ou compatível) para reprodutibilidade com seed.
    - `available`: predicado opcional `sid -> bool` (cromas inclusive).
    - Levanta ValueError se não houver candidatas.
    - Funciona com uma única candidata.
    """
    if not skins:
        raise ValueError("Nenhuma skin disponível para o sorteio.")
    rng = rng or random.Random()
    values = weights(
        skins,
        favorites=favorites,
        recent=recent,
        historic_ids=historic_ids,
        popular_ids=popular_ids,
        available=available,
        form_toggle_ids=form_toggle_ids,
    )
    total = sum(values)
    if total <= 0:  # defensivo: piso de recência > 0, então só zera por exclusão
        eligible = [s for s, v in zip(skins, values) if v > 0] or list(skins)
        return rng.choice(eligible)
    target = rng.random() * total
    cumulative = 0.0
    for skin, value in zip(skins, values):
        cumulative += value
        if target < cumulative:
            return skin
    return skins[-1]  # arredondamento de ponto flutuante
