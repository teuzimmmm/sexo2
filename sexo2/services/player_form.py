"""A player's recent form, read from the client's own match history (D-151).

Pure functions over the answers of ``/lol-match-history/v1/products/lol/{puuid}/matches`` and
``/lol-match-history/v1/recently-played-summoners``. Nothing here reaches the network, and every
field is optional: whatever the client leaves out is left out of the summary, so the panel shows
less, never something invented. The list endpoint describes each game from the point of view of
the player asked about, so only that player's own entry is read.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import quote

RECENT = 5  # results shown as dots
TOP_CHAMPIONS = 3  # most played, for the tooltip
MIN_ROLE_GAMES = 2  # a role needs this many games to be called the player's main one
ROLES = ("top", "jungle", "middle", "bottom", "support")
_POSITIONS = {
    "TOP": "top",
    "JUNGLE": "jungle",
    "MIDDLE": "middle",
    "MID": "middle",
    "BOTTOM": "bottom",
    "UTILITY": "support",
}


def _games(payload: Any) -> list[dict]:
    games = payload.get("games") if isinstance(payload, dict) else payload
    if isinstance(games, dict):
        games = games.get("games")
    return [g for g in games if isinstance(g, dict)] if isinstance(games, list) else []


def _own_participant(game: dict, puuid: str) -> dict | None:
    participants = [p for p in game.get("participants") or [] if isinstance(p, dict)]
    for identity in game.get("participantIdentities") or []:
        player = identity.get("player") if isinstance(identity, dict) else None
        if isinstance(player, dict) and player.get("puuid") == puuid:
            for participant in participants:
                if participant.get("participantId") == identity.get("participantId"):
                    return participant
    return participants[0] if len(participants) == 1 else None


def _won(participant: dict) -> bool | None:
    win = (participant.get("stats") or {}).get("win")
    if isinstance(win, bool):
        return win
    if isinstance(win, str) and win.lower() in ("win", "fail"):
        return win.lower() == "win"
    return None


def _role(participant: dict) -> str | None:
    timeline = participant.get("timeline") or {}
    position = str(participant.get("teamPosition") or participant.get("individualPosition") or "").upper()
    if position in _POSITIONS:
        return _POSITIONS[position]
    lane, role = str(timeline.get("lane") or "").upper(), str(timeline.get("role") or "").upper()
    if lane == "BOTTOM":
        return "support" if role in ("DUO_SUPPORT", "SUPPORT") else "bottom"
    return _POSITIONS.get(lane)


def summarize(payload: Any, puuid: str) -> dict | None:
    """Recent results, main role and per-champion record of ``puuid``; None without usable games."""
    games = _games(payload)
    games.sort(
        key=lambda g: g.get("gameCreation") if isinstance(g.get("gameCreation"), (int, float)) else 0, reverse=True
    )
    results: list[bool] = []
    roles: Counter = Counter()
    champions: dict[int, list[int]] = {}
    for game in games:
        mine = _own_participant(game, puuid)
        if mine is None:
            continue
        won = _won(mine)
        if won is None:
            continue
        results.append(won)
        role = _role(mine)
        if role:
            roles[role] += 1
        champion = mine.get("championId")
        if isinstance(champion, int) and not isinstance(champion, bool) and champion > 0:
            record = champions.setdefault(champion, [0, 0])
            record[0] += 1
            record[1] += won
    if not results:
        return None
    main, count = roles.most_common(1)[0] if roles else (None, 0)
    return {
        "games": len(results),
        "wins": sum(results),
        "recent": results[:RECENT],
        "role": main if count >= MIN_ROLE_GAMES else None,
        "champions": champions,
        "top": [
            {"id": c, "games": r[0]} for c, r in sorted(champions.items(), key=lambda kv: -kv[1][0])[:TOP_CHAMPIONS]
        ],
    }


def with_champion(summary: dict | None, champion_id: int) -> dict | None:
    """How the player did in the recent games on the champion now picked."""
    record = (summary or {}).get("champions", {}).get(champion_id)
    return {"games": record[0], "wins": record[1]} if record else None


def public(summary: dict | None, champion_id: int) -> dict | None:
    """What the panel receives: no per-champion table, only the champion of the moment."""
    if summary is None:
        return None
    return {
        "games": summary["games"],
        "wins": summary["wins"],
        "recent": summary["recent"],
        "role": summary["role"],
        "top": summary["top"],
        "withChampion": with_champion(summary, champion_id),
    }


# The site the profile button opens. Only this address is ever built, from the client's own data.
PROFILE_URL = "https://www.op.gg/summoners/{region}/{name}-{tag}"
_PROFILE_REGIONS = {
    "BR": "br", "NA": "na", "EUW": "euw", "EUNE": "eune", "LAN": "lan", "LAS": "las", "OCE": "oce", "TR": "tr",
    "RU": "ru", "JP": "jp", "KR": "kr", "PH2": "ph", "SG2": "sg", "TH2": "th", "TW2": "tw", "VN2": "vn",
}  # fmt: skip


def profile_region(payload: Any) -> str | None:
    """The site's region code for the client's region (``/riotclient/region-locale``), or None."""
    region = payload.get("region") if isinstance(payload, dict) else None
    return _PROFILE_REGIONS.get(region.strip().upper()) if isinstance(region, str) else None


def profile_url(region: str | None, name: str, tag: str) -> str | None:
    """The address of a player's profile; None when the region, the name or the tag is missing."""
    if not region or not name or not tag:
        return None
    return PROFILE_URL.format(region=region, name=quote(name, safe=""), tag=quote(tag, safe=""))
