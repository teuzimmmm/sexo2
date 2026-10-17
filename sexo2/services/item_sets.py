"""Item sets built from LoLalytics builds and merged into the client.

Managed sets are recognised by ``uid`` only (``sexo2-{championId}-{n}``); the
title prefix is cosmetic and provisional. A merge replaces the managed sets of
one champion and leaves every other set exactly as the client returned it.

Blocks come from :func:`lolalytics.plan_item_pages`, one per observed block:
starting items, the core trio observed together, and the alternatives for
slots 4, 5 and 6. Block labels carry no combined win rate. LoLalytics has no
separate boots block today; boots appear where they were observed (usually
in the core). A ``boots`` block, if a future build page has one, passes
through unchanged.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

from lcu.features.lcu_item_sets import ItemSetsError, LCUItemSets, validate_document
from lolalytics.builds import BuildPage
from lolalytics.item_pages import plan_item_pages

MANAGED_UID_PREFIX = "sexo2-"
# Provisional visible text, pending approval (docs/produto/decisoes.md, D-113).
MANAGED_TITLE_PREFIX = "SEXO2"
_COMPARED_FIELDS = ("uid", "title", "associatedChampions", "associatedMaps", "blocks")


def managed_uid(champion_id: int, index: int) -> str:
    return f"{MANAGED_UID_PREFIX}{champion_id}-{index}"


def is_managed(item_set: Any, champion_id: int) -> bool:
    uid = item_set.get("uid") if isinstance(item_set, dict) else None
    return isinstance(uid, str) and uid.startswith(f"{MANAGED_UID_PREFIX}{champion_id}-")


def build_item_sets(champion_id: int, pages: list[BuildPage], *, map_ids: Iterable[int] = ()) -> list[dict]:
    """Client item set objects for one champion, in the client's field names."""
    if isinstance(champion_id, bool) or not isinstance(champion_id, int) or champion_id <= 0:
        raise ValueError("champion_id must be a positive integer")
    prepared = plan_item_pages(pages, max_pages=min(20, max(1, len(pages))))
    result = []
    for index, page in enumerate(prepared, start=1):
        blocks = [
            {
                "type": entry.label,
                "items": [{"id": choice.identifier, "count": choice.count} for choice in entry.block.choices],
            }
            for entry in page.blocks
        ]
        result.append(
            {
                "title": f"{MANAGED_TITLE_PREFIX} {page.title}",
                "associatedChampions": [champion_id],
                "associatedMaps": list(map_ids),
                "blocks": blocks,
                "uid": managed_uid(champion_id, index),
                "sortrank": 0,
                "type": "custom",
                "map": "any",
                "mode": "any",
                "startedFrom": "blank",
                "preferredItemSlots": [],
            }
        )
    return result


def merge_item_sets(document: dict, champion_id: int, new_sets: list[dict]) -> dict:
    """Replace this champion's managed sets; keep every other set as it is."""
    validate_document(document)
    uids = [item.get("uid") for item in new_sets]
    if len(set(uids)) != len(uids) or not all(is_managed(item, champion_id) for item in new_sets):
        raise ValueError("new sets must have distinct managed uids for this champion")
    merged = deepcopy(document)
    kept = [item for item in merged["itemSets"] if not is_managed(item, champion_id)]
    merged["itemSets"] = kept + deepcopy(new_sets)
    return merged


@dataclass(frozen=True)
class ItemSetImportResult:
    confirmed: bool
    written: bool
    error: str | None = None


def _others(document: dict, champion_id: int) -> list[dict]:
    return [item for item in document["itemSets"] if not is_managed(item, champion_id)]


def _essentials(sets: list[dict]) -> list[dict]:
    return [{name: item.get(name) for name in _COMPARED_FIELDS} for item in sets]


def import_item_sets(api: LCUItemSets, champion_id: int, new_sets: list[dict]) -> ItemSetImportResult:
    """Write the merged document and confirm it by reading it back.

    Confirmation requires every other set to come back unchanged and the
    managed sets to match what was sent on the fields this module sets.
    """
    written = False
    try:
        summoner_id = api.summoner_id()
        before = api.read(summoner_id)
        merged = merge_item_sets(before, champion_id, new_sets)
        if merged == before:
            return ItemSetImportResult(confirmed=True, written=False)
        api.write(summoner_id, merged)
        written = True
        after = api.read(summoner_id)
    except ItemSetsError as error:
        return ItemSetImportResult(confirmed=False, written=written, error=f"lcu_{error.code}")
    except ValueError:
        return ItemSetImportResult(confirmed=False, written=written, error="invalid_sets")
    managed_after = [item for item in after["itemSets"] if is_managed(item, champion_id)]
    confirmed = _others(after, champion_id) == _others(before, champion_id) and _essentials(
        managed_after
    ) == _essentials(new_sets)
    return ItemSetImportResult(confirmed=confirmed, written=True, error=None if confirmed else "not_confirmed")
