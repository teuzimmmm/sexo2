"""Augment statistics for one champion, kept apart per mode and source.

ARAM Mayhem comes from ARAMKit (``data.aramkit.com``, no key):
``versions.json`` names the current data path and
``/{dataPath}/stats/all/champion-details/{championId}.json`` lists
``augments.all[{id, winRate, sampleCount, pickRate, ...}]`` with rates as
fractions. That shape comes from reading the site; no response has been
captured from this environment yet, so the parser fails closed on anything
else.

Arena comes from the LoLalytics Arena page already decoded by ``lolalytics``:
``augment.augment0..4`` hold, for each of the five augment choices of a game,
the most picked augments as ``[id, win_rate, pick_rate, games]``. The library
redacts the Arena win rate (docs/lolalytics/FONTES.md), so Arena shows pick
rate and games only. Only those top rows exist, so most Arena offers have no
data for some cards.

A statistic is never derived from another one, and Arena and Mayhem figures
are never mixed.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

ARAMKIT_BASE = "https://data.aramkit.com/data"


@dataclass(frozen=True)
class AugmentStat:
    augment_id: int
    mode: str  # "arena" or "mayhem"
    source: str  # "aramkit" or "lolalytics"
    patch: str
    scope: str  # e.g. "champion" or "champion_choice_2"
    win_rate: float | None  # percent
    pick_rate: float | None  # percent
    games: int | None


def _percent_from_fraction(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return round(value * 100, 2) if 0 <= value <= 1 else None


def _percent(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value) if 0 <= value <= 100 else None


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def aramkit_data_path(versions: Any) -> tuple[str, str]:
    """(dataPath, version) of the latest data set from ``versions.json``."""
    if not isinstance(versions, dict):
        raise ValueError("versions.json must be an object")
    latest = versions.get("latest")
    rows = versions.get("versions")
    if not isinstance(rows, list):
        raise ValueError("versions.json has no versions list")
    row = next((r for r in rows if isinstance(r, dict) and r.get("version") == latest), None)
    if row is None or not isinstance(row.get("dataPath"), str) or not row["dataPath"].strip("/"):
        raise ValueError("versions.json does not name the latest data path")
    return row["dataPath"].strip("/"), str(latest)


def aramkit_champion_url(data_path: str, champion_id: int) -> str:
    return f"{ARAMKIT_BASE}/{data_path}/stats/all/champion-details/{int(champion_id)}.json"


def parse_aramkit_champion(payload: Any, patch: str) -> dict[int, AugmentStat]:
    """ARAM Mayhem statistics of one champion's augments."""
    augments = payload.get("augments") if isinstance(payload, dict) else None
    rows = augments.get("all") if isinstance(augments, dict) else None
    if not isinstance(rows, list):
        raise ValueError("champion details have no augments.all list")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        augment_id = row.get("id")
        if not isinstance(augment_id, int) or isinstance(augment_id, bool) or augment_id <= 0:
            continue
        result[augment_id] = AugmentStat(
            augment_id=augment_id,
            mode="mayhem",
            source="aramkit",
            patch=patch,
            scope="champion",
            win_rate=_percent_from_fraction(row.get("winRate")),
            pick_rate=_percent_from_fraction(row.get("pickRate")),
            games=_count(row.get("sampleCount")),
        )
    return result


def parse_lolalytics_arena(snapshot: Any, choice: int) -> dict[int, AugmentStat]:
    """Arena statistics for the ``choice``-th augment pick of a game (0 to 4)."""
    query = getattr(snapshot, "query", None)
    query = query if isinstance(query, dict) else getattr(query, "__dict__", {})
    if query.get("mode") != "arena":
        raise ValueError("not an Arena snapshot")
    if not isinstance(choice, int) or not 0 <= choice <= 4:
        raise ValueError("choice must be 0 to 4")
    raw = getattr(snapshot, "raw", None) or {}
    rows = (raw.get("augment") or {}).get(f"augment{choice}") or []
    patch = str((getattr(snapshot, "resolved", None) or {}).get("patch") or query.get("patch") or "")
    result = {}
    for row in rows:
        if not isinstance(row, list) or len(row) != 4:
            continue
        augment_id = row[0]
        if not isinstance(augment_id, int) or isinstance(augment_id, bool) or augment_id <= 0:
            continue  # 0 is "no augment"
        result[augment_id] = AugmentStat(
            augment_id=augment_id,
            mode="arena",
            source="lolalytics",
            patch=patch,
            scope=f"champion_choice_{choice + 1}",
            win_rate=_percent(row[1]),
            pick_rate=_percent(row[2]),
            games=_count(row[3]),
        )
    return result
