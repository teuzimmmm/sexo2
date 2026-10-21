"""The SEXO2 item set, built from LoLalytics builds and merged into the client.

There is one managed set, reused for every champion: its ``uid`` is fixed
(:data:`MANAGED_UID`) and each import rewrites its title, champion and blocks.
One reused set keeps the client's list from growing by one set per champion
played and needs no cleanup. Sets are recognised by ``uid`` only, never by
title. Sets written by earlier test versions (``sexo2-{championId}-{n}``) are
recognised the same way and removed on the next import. Every other set is
left exactly as the client returned it.

``associatedMaps`` is empty: in the client's item set format an empty list
means every map, so the same set serves Summoner's Rift, ARAM and Swiftplay.
That reading still needs checking in the shop of a real match.

The blocks come from :func:`lolalytics.item_pages.plan_assistant_page`.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import logging
import re
from time import sleep
from typing import Any

from lcu.features.lcu_item_sets import ItemSetsError, LCUItemSets, validate_document
from lolalytics.builds import BuildPage
from lolalytics.item_pages import plan_assistant_page

log = logging.getLogger(__name__)

MANAGED_UID = "sexo2-managed"
MANAGED_TITLE_PREFIX = "SEXO2"
_LEGACY_UID = re.compile(r"sexo2-\d+-\d+")


def is_managed(item_set: Any) -> bool:
    uid = item_set.get("uid") if isinstance(item_set, dict) else None
    return isinstance(uid, str) and (uid == MANAGED_UID or _LEGACY_UID.fullmatch(uid) is not None)


def build_item_set(
    champion_id: int,
    win: BuildPage | None,
    pick: BuildPage | None,
    matchup: BuildPage | None = None,
    *,
    champion_name: str | None = None,
) -> dict:
    """The managed set for one champion, in the client's field names."""
    if isinstance(champion_id, bool) or not isinstance(champion_id, int) or champion_id <= 0:
        raise ValueError("champion_id must be a positive integer")
    page = plan_assistant_page(win, pick, matchup)
    name = champion_name.strip() if isinstance(champion_name, str) and champion_name.strip() else page.title
    return {
        "title": f"{MANAGED_TITLE_PREFIX} — {name}",
        "associatedChampions": [champion_id],
        "associatedMaps": [],
        "blocks": [
            {
                "type": entry.label,
                "items": [{"id": choice.identifier, "count": choice.count} for choice in entry.block.choices],
            }
            for entry in page.blocks
        ],
        "uid": MANAGED_UID,
        "sortrank": 0,
        "type": "custom",
        "map": "any",
        "mode": "any",
        "startedFrom": "blank",
        "preferredItemSlots": [],
    }


def merge_item_sets(document: dict, new_set: dict) -> dict:
    """Put the managed set in place of the old one; keep every other set as it is."""
    validate_document(document)
    if not isinstance(new_set, dict) or new_set.get("uid") != MANAGED_UID:
        raise ValueError("the new set must carry the managed uid")
    merged = deepcopy(document)
    sets = merged["itemSets"]
    position = next((i for i, item in enumerate(sets) if is_managed(item)), len(sets))
    kept = [item for item in sets if not is_managed(item)]
    merged["itemSets"] = kept[:position] + [deepcopy(new_set)] + kept[position:]
    return merged


@dataclass(frozen=True)
class ItemSetImportResult:
    confirmed: bool
    written: bool
    error: str | None = None


def _others(document: dict) -> list[dict]:
    return [item for item in document["itemSets"] if not is_managed(item)]


def _content(item_set: dict) -> tuple:
    """What a set shows in the shop, as the client returns it after a write.

    The client fills in defaults on what it stores (block fields such as
    ``hideIfSummonerSpell``, ids as strings or numbers), so a read-back is
    compared on this rather than field for field.
    """

    def number(value: Any) -> Any:
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    blocks = item_set.get("blocks") or []
    return (
        item_set.get("uid"),
        item_set.get("title"),
        tuple(sorted(number(c) for c in item_set.get("associatedChampions") or [])),
        tuple(sorted(number(m) for m in item_set.get("associatedMaps") or [])),
        tuple(
            (
                block.get("type"),
                tuple((number(i.get("id")), number(i.get("count", 1))) for i in block.get("items") or []),
            )
            for block in blocks
            if isinstance(block, dict)
        ),
    )


def _confirmed(after: dict, before: dict, new_set: dict) -> bool:
    managed = [item for item in after["itemSets"] if is_managed(item)]
    return (
        [_content(item) for item in _others(after)] == [_content(item) for item in _others(before)]
        and len(managed) == 1
        and _content(managed[0]) == _content(new_set)
    )


def import_item_set(api: LCUItemSets, new_set: dict) -> ItemSetImportResult:
    """Read, merge, write the whole document, read it back and confirm.

    The client's PUT replaces the whole document and has no version check, so
    a set the user edits between our read and our write would be lost. To keep
    that window short the document is read a second time just before writing;
    if the other sets changed in between, the merge starts over from the newer
    document (once). Confirmation requires every other set to come back
    unchanged and exactly one managed set equal to what was sent.
    """
    written = False
    try:
        summoner_id = api.summoner_id()
        before = api.read(summoner_id)
        for _attempt in range(2):
            merged = merge_item_sets(before, new_set)
            if merged == before:
                return ItemSetImportResult(confirmed=True, written=False)
            latest = api.read(summoner_id)
            if _others(latest) == _others(before):
                break
            before = latest
        else:
            return ItemSetImportResult(confirmed=False, written=False, error="concurrent_edit")
        api.write(summoner_id, merged)
        written = True
        after = api.read(summoner_id)
        if not _confirmed(after, before, new_set):
            sleep(0.5)  # the client can answer a read right after a write with the old document
            after = api.read(summoner_id)
    except ItemSetsError as error:
        return ItemSetImportResult(confirmed=False, written=written, error=f"lcu_{error.code}")
    except ValueError:
        return ItemSetImportResult(confirmed=False, written=written, error="invalid_sets")
    confirmed = _confirmed(after, before, new_set)
    if not confirmed:
        managed = [item for item in after["itemSets"] if is_managed(item)]
        log.info(
            "[ITEM_SETS] read-back differs: %d managed sets, sent %s, read %s",
            len(managed),
            _content(new_set),
            _content(managed[0]) if managed else None,
        )
    return ItemSetImportResult(confirmed=confirmed, written=True, error=None if confirmed else "not_confirmed")
