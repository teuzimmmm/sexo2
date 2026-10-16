"""Pure conversion of one filtered LoLalytics snapshot into a build page."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from copy import deepcopy
import math
from typing import Any

from .errors import DataUnavailable, SchemaError


@dataclass
class ItemChoice:
    identifier: str
    count: int
    metrics: dict
    raw: dict


@dataclass
class ItemBlock:
    kind: str
    choices: list[ItemChoice]
    metrics: dict
    source_path: str
    ordered: bool


@dataclass
class BuildPage:
    selection: str
    label: str
    title: str
    keystone: int
    runes: dict
    blocks: list[ItemBlock]
    core_metrics: dict
    source_url: str
    query: dict
    resolved: dict
    collected_at: str
    cache_hit: bool
    warnings: list[str]
    conditioning: str = "keystone"
    matchup_metrics: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BuildCollection:
    query: dict
    pages: list[BuildPage]
    schema_version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


def _schema(message: str) -> SchemaError:
    return SchemaError(f"invalid build snapshot: {message}")


def _mapping(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        raise _schema(f"{path} must be an object")
    return value


def _opaque_id(value: Any, path: str) -> str:
    if isinstance(value, bool) or value is None or not isinstance(value, (int, str)):
        raise _schema(f"{path} must be an integer or opaque string ID")
    if isinstance(value, int) and value <= 0:
        raise _schema(f"{path} integer ID must be positive")
    if isinstance(value, str) and not value.strip():
        raise _schema(f"{path} string ID must not be empty")
    return str(value)


def _metric(value: Any, path: str, *, integer: bool = False) -> int | float | None:
    if value is None:
        return None
    if not integer and value == "xx.xx":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _schema(f"{path} must be numeric or null")
    if not math.isfinite(value):
        raise _schema(f"{path} must be finite")
    if integer and (not isinstance(value, int) or value < 0):
        raise _schema(f"{path} must be a non-negative integer or null")
    if not integer and not 0 <= value <= 100:
        raise _schema(f"{path} must be between 0 and 100 or null")
    return value


def _block_metrics(source: dict, path: str) -> dict:
    # Upstream uses wr/n. Keep these values scoped to the source block.
    return {
        "win_rate": _metric(source.get("wr"), f"{path}.wr"),
        "games": _metric(source.get("n"), f"{path}.n", integer=True),
    }


def _format_games(value: int | float | None) -> str:
    if value is None:
        return "jogos indisponíveis"
    return f"{value:,}".replace(",", ".") + " jogos"


def _items_block(kind: str, obj: dict | list, path: str, *, ordered: bool) -> ItemBlock:
    metrics = {} if kind in ("item4", "item5", "item6") else _block_metrics(obj, path)
    choices: list[ItemChoice] = []
    if kind == "core":
        values = obj.get("set")
        if values is None:
            raise DataUnavailable("filtered build is missing its core item set")
        if not isinstance(values, list):
            raise _schema(f"{path}.set must be an array")
        if len(values) != 3:
            raise DataUnavailable("filtered build core must contain exactly three items")
        for index, value in enumerate(values):
            choices.append(ItemChoice(_opaque_id(value, f"{path}.set[{index}]"), 1, {}, deepcopy(obj)))
    elif kind == "starting":
        values = obj.get("set")
        if values is None:
            raise DataUnavailable("starting item set is absent")
        if not isinstance(values, list):
            raise _schema(f"{path}.set must be an array")
        grouped: dict[str, int] = {}
        order: list[str] = []
        for index, value in enumerate(values):
            identifier = _opaque_id(value, f"{path}.set[{index}]")
            if identifier not in grouped:
                grouped[identifier] = 0
                order.append(identifier)
            grouped[identifier] += 1
        choices = [ItemChoice(identifier, grouped[identifier], {}, deepcopy(obj)) for identifier in order]
    else:
        values = obj
        if not isinstance(values, list):
            raise _schema(f"{path} must be an array")
        for index, row in enumerate(values):
            choice_path = f"{path}[{index}]"
            if not isinstance(row, dict):
                raise _schema(f"{choice_path} must be an object")
            identifier = _opaque_id(row.get("id"), f"{choice_path}.id")
            choice_metrics = _block_metrics(row, choice_path)
            choices.append(ItemChoice(identifier, 1, choice_metrics, deepcopy(row)))
    return ItemBlock(kind, choices, metrics, path, ordered)


def build_page(snapshot, selection: str, keystone: int) -> BuildPage:
    """Create a structured suggestion from exactly one filtered snapshot."""
    if selection not in ("win", "pick"):
        raise _schema("selection must be 'win' or 'pick'")
    if isinstance(keystone, bool) or not isinstance(keystone, int) or keystone <= 0:
        raise _schema("keystone must be a positive integer")

    query = _mapping(getattr(snapshot, "query", None), "snapshot.query")
    resolved = _mapping(getattr(snapshot, "resolved", None), "snapshot.resolved")
    if query.get("mode") not in ("ranked", "aram"):
        raise DataUnavailable("build pages are supported only for ranked and ARAM")
    resolved_keystone = resolved.get("keystone")
    if isinstance(resolved_keystone, bool) or resolved_keystone != keystone or not isinstance(resolved_keystone, int):
        raise DataUnavailable("snapshot keystone does not match the requested keystone")

    raw = _mapping(getattr(snapshot, "raw", None), "snapshot.raw")
    summary = raw.get("summary")
    if summary is None:
        raise DataUnavailable("filtered snapshot has no build summary")
    if not isinstance(summary, dict):
        raise _schema("summary must be an object")
    suggestion = summary.get(selection)
    if suggestion is None:
        raise DataUnavailable(f"filtered snapshot has no {selection} suggestion")
    if not isinstance(suggestion, dict):
        raise _schema(f"summary.{selection} must be an object")
    runes_source = suggestion.get("runes")
    if runes_source is None:
        raise DataUnavailable(f"filtered snapshot has no {selection} rune layout")
    if not isinstance(runes_source, dict):
        raise _schema(f"summary.{selection}.runes must be an object")
    rune_set = runes_source.get("set")
    if rune_set is None:
        raise DataUnavailable(f"filtered snapshot has no complete {selection} rune layout")
    if not isinstance(rune_set, dict):
        raise _schema(f"summary.{selection}.runes.set must be an object")
    sizes = {"pri": 4, "sec": 2, "mod": 3}
    runes = {}
    for slot, size in sizes.items():
        values = rune_set.get(slot)
        if values is None:
            raise DataUnavailable(f"filtered snapshot {selection} rune layout is missing {slot}")
        if not isinstance(values, list):
            raise _schema(f"summary.{selection}.runes.set.{slot} must be an array")
        if len(values) != size:
            raise DataUnavailable(f"filtered snapshot {selection} rune layout has incomplete {slot}")
        runes[slot] = [_opaque_id(value, f"summary.{selection}.runes.set.{slot}[{i}]") for i, value in enumerate(values)]
    if runes["pri"][0] != str(keystone):
        raise DataUnavailable("suggested rune page does not begin with the requested keystone")
    # Keep auxiliary rune page metadata when present; never invent tree IDs.
    if "page" in runes_source:
        if not isinstance(runes_source["page"], dict):
            raise _schema(f"summary.{selection}.runes.page must be an object")
        runes["page"] = deepcopy(runes_source["page"])

    items = suggestion.get("items")
    if items is None:
        raise DataUnavailable(f"filtered snapshot has no {selection} item summary")
    if not isinstance(items, dict):
        raise _schema(f"summary.{selection}.items must be an object")
    core_obj = items.get("core")
    if core_obj is None:
        raise DataUnavailable(f"filtered snapshot has no {selection} core item set")
    if not isinstance(core_obj, dict):
        raise _schema(f"summary.{selection}.items.core must be an object")
    core = _items_block("core", core_obj, f"payload.summary.{selection}.items.core", ordered=True)
    if len(core.choices) != 3:
        raise DataUnavailable("filtered build core must contain exactly three items")
    core_metrics = deepcopy(core.metrics)
    title_prefix = "WR" if selection == "win" else "Common"
    wr = core_metrics["win_rate"]
    games = core_metrics["games"]
    rate = "indisponível" if wr is None else f"{wr:.1f}%"
    title = f"{title_prefix} {rate} / {_format_games(games)}"

    blocks = []
    warnings = ["keystone_conditioned", "not_full_rune_page_joint_sample"]
    starting = items.get("start")
    if starting is None or (isinstance(starting, dict) and (starting.get("set") is None or starting.get("set") == [])):
        warnings.append("starting_items_unavailable")
    elif not isinstance(starting, dict):
        raise _schema(f"summary.{selection}.items.start must be an object")
    else:
        blocks.append(_items_block("starting", starting, f"payload.summary.{selection}.items.start", ordered=True))
    blocks.append(core)
    for slot in ("item4", "item5", "item6"):
        alternatives = items.get(slot)
        if alternatives is None or alternatives == []:
            warnings.append(f"{slot}_unavailable")
            continue
        blocks.append(_items_block(slot, alternatives, f"payload.summary.{selection}.items.{slot}", ordered=False))

    return BuildPage(
        selection=selection,
        label="WR" if selection == "win" else "Common",
        title=title,
        keystone=keystone,
        runes=runes,
        blocks=blocks,
        core_metrics=core_metrics,
        source_url=getattr(snapshot, "source_url", ""),
        query=deepcopy(query),
        resolved=deepcopy(resolved),
        collected_at=getattr(snapshot, "collected_at", ""),
        cache_hit=bool(getattr(snapshot, "cache_hit", False)),
        warnings=warnings,
    )
