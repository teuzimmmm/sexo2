"""Augment catalog per mode, from the client's game data.

``cherry-augments.json`` lists every augment (id, name, icon, rarity) and
``augment-lists.json`` the pool of each mode by ``augmentNameId``: ``CHERRY``
is Arena and ``KIWI`` is ARAM Mayhem. The pools differ, so an offer is only
ever matched against the pool of the mode being played. Both files are the
community-documented CommunityDragon/game-data shapes; reading them from the
live client (``/lol-game-data/assets/v1/cherry-augments.json``) still needs
checking in a real client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MODE_POOLS = {"arena": "CHERRY", "mayhem": "KIWI"}
RARITIES = {"kSilver": "silver", "kGold": "gold", "kPrismatic": "prismatic"}


@dataclass(frozen=True)
class Augment:
    id: int
    name_id: str
    name: str
    rarity: str  # silver, gold, prismatic or "" when unknown
    icon_path: str  # client asset path, e.g. /lol-game-data/assets/ASSETS/UX/Cherry/Augments/Icons/x_small.png


@dataclass(frozen=True)
class Catalog:
    mode: str
    augments: tuple[Augment, ...]
    unmatched: tuple[str, ...] = ()

    def by_id(self, augment_id: int) -> Augment | None:
        return next((a for a in self.augments if a.id == augment_id), None)

    def ids(self) -> frozenset[int]:
        return frozenset(a.id for a in self.augments)


def _rows(payload: Any, name: str) -> list[dict]:
    if not isinstance(payload, list):
        raise ValueError(f"{name} must be a list")
    return [row for row in payload if isinstance(row, dict)]


def build_catalog(cherry_augments: Any, augment_lists: Any, mode: str) -> Catalog:
    """The pool of ``mode`` ("arena" or "mayhem") with the entries that did not resolve."""
    if mode not in MODE_POOLS:
        raise ValueError(f"unsupported mode {mode!r}")
    by_name: dict[str, dict] = {}
    for row in _rows(cherry_augments, "cherry-augments"):
        name_id = row.get("augmentNameId")
        augment_id = row.get("id")
        if isinstance(name_id, str) and name_id and isinstance(augment_id, int) and not isinstance(augment_id, bool):
            by_name.setdefault(name_id, row)
    pool = next((row for row in _rows(augment_lists, "augment-lists") if row.get("modeName") == MODE_POOLS[mode]), None)
    if pool is None or not isinstance(pool.get("augmentList"), list):
        raise ValueError(f"no augment pool for {MODE_POOLS[mode]}")
    augments, unmatched, seen = [], [], set()
    for entry in pool["augmentList"]:
        name_id = str(entry).rsplit("/", 1)[-1]
        row = by_name.get(name_id)
        if row is None:
            unmatched.append(name_id)
            continue
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        augments.append(
            Augment(
                id=row["id"],
                name_id=name_id,
                name=str(row.get("nameTRA") or name_id),
                rarity=RARITIES.get(row.get("rarity"), ""),
                icon_path=str(row.get("augmentSmallIconPath") or ""),
            )
        )
    return Catalog(mode=mode, augments=tuple(augments), unmatched=tuple(unmatched))
