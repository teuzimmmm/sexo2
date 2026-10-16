"""Structured, opponent-conditioned build suggestions without inferred cores."""
from __future__ import annotations

from copy import deepcopy
import re

from .builds import BuildPage, ItemBlock, ItemChoice, _block_metrics, _items_block, _metric, _opaque_id
from .errors import DataUnavailable, SchemaError
from .query import LANES


def _schema(message: str) -> SchemaError:
    return SchemaError(f"invalid matchup snapshot: {message}")


def _object(value, path: str, *, missing_unavailable: bool = False) -> dict:
    if value is None and missing_unavailable:
        raise DataUnavailable(f"matchup snapshot is missing {path}")
    if not isinstance(value, dict):
        raise _schema(f"{path} must be an object")
    return value


def _slot_block(slot: str, item: dict, path: str) -> ItemBlock:
    identifier = _opaque_id(item.get("id"), f"{path}.id")
    metrics = _block_metrics(item, path)
    choice = ItemChoice(identifier, 1, metrics, deepcopy(item))
    # The item slot is positional; its observation belongs to this choice and
    # is intentionally not promoted to a multi-item block metric.
    return ItemBlock(slot, [choice], {}, path, True)


def build_matchup_page(snapshot, *, min_games: int = 100, selection: str = "win") -> BuildPage:
    """Build one opponent-specific suggestion from a summary selection."""
    if isinstance(min_games, bool) or not isinstance(min_games, int) or min_games < 0:
        raise _schema("min_games must be a non-negative integer")
    if selection not in ("win", "pick"):
        raise _schema("selection must be 'win' or 'pick'")

    query = _object(getattr(snapshot, "query", None), "snapshot.query")
    resolved = _object(getattr(snapshot, "resolved", None), "snapshot.resolved")
    if query.get("mode") != "ranked":
        raise DataUnavailable("matchup builds are supported only for ranked")
    if query.get("keystone") is not None or resolved.get("keystone") is not None:
        raise DataUnavailable("matchup snapshots must not have a keystone filter")
    opponent = query.get("opponent")
    if not isinstance(opponent, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", opponent):
        raise _schema("snapshot.query.opponent must be a lowercase opponent slug")
    if resolved.get("opponent") != opponent:
        raise _schema("resolved opponent does not match the query")
    opponent_lane = query.get("opponent_lane", "all")
    if opponent_lane not in LANES:
        raise _schema("snapshot.query.opponent_lane is unsupported")
    resolved_lane = resolved.get("opponent_lane")
    if resolved_lane is not None and resolved_lane != opponent_lane:
        raise _schema("resolved opponent lane does not match the query")

    opponent_name = resolved.get("opponent_name")
    if not isinstance(opponent_name, str) or not opponent_name.strip():
        opponent_name = opponent.replace("-", " ").title()
    label = f"vs {opponent_name}"

    raw = _object(getattr(snapshot, "raw", None), "snapshot.raw")
    summary = _object(raw.get("summary"), "payload.summary", missing_unavailable=True)
    suggestion = _object(summary.get(selection), f"payload.summary.{selection}", missing_unavailable=True)
    runes_source = _object(suggestion.get("runes"), f"payload.summary.{selection}.runes", missing_unavailable=True)
    rune_set = _object(runes_source.get("set"), f"payload.summary.{selection}.runes.set", missing_unavailable=True)
    runes = {}
    for slot, size in (("pri", 4), ("sec", 2), ("mod", 3)):
        values = rune_set.get(slot)
        if values is None:
            raise DataUnavailable(f"matchup rune layout is missing {slot}")
        if not isinstance(values, list):
            raise _schema(f"payload.summary.{selection}.runes.set.{slot} must be an array")
        if len(values) != size:
            raise DataUnavailable(f"matchup rune layout has incomplete {slot}")
        runes[slot] = [
            _opaque_id(value, f"payload.summary.{selection}.runes.set.{slot}[{index}]")
            for index, value in enumerate(values)
        ]
    primary = rune_set["pri"][0]
    if isinstance(primary, bool) or not isinstance(primary, int) or primary <= 0:
        raise _schema("suggested primary rune must be a positive integer ID")
    if "page" in runes_source:
        page = runes_source["page"]
        if not isinstance(page, dict):
            raise _schema(f"payload.summary.{selection}.runes.page must be an object")
        runes["page"] = deepcopy(page)

    items = _object(suggestion.get("items"), f"payload.summary.{selection}.items", missing_unavailable=True)
    blocks = []
    warnings = ["opponent_conditioned", "keystone_filter_unavailable", "not_joint_build_sample"]

    starting = items.get("start")
    if starting is None:
        warnings.append("starting_items_unavailable")
    else:
        starting = _object(starting, f"payload.summary.{selection}.items.start")
        if starting.get("set") is None or starting.get("set") == []:
            warnings.append("starting_items_unavailable")
        else:
            block = _items_block("starting", starting, f"payload.summary.{selection}.items.start", ordered=True)
            blocks.append(block)
            games = block.metrics.get("games")
            if games is None:
                warnings.append("missing_item_sample")
            elif games < min_games:
                warnings.append("low_item_sample")

    for slot in ("item1", "item2", "item3"):
        item = items.get(slot)
        if item is None:
            warnings.append(f"{slot}_unavailable")
            continue
        item = _object(item, f"payload.summary.{selection}.items.{slot}")
        block = _slot_block(slot, item, f"payload.summary.{selection}.items.{slot}")
        blocks.append(block)
        games = block.choices[0].metrics.get("games")
        if games is None:
            warnings.append("missing_item_sample")
        elif games < min_games:
            warnings.append("low_item_sample")

    for slot in ("item4", "item5", "item6"):
        alternatives = items.get(slot)
        if alternatives is None or alternatives == []:
            warnings.append(f"{slot}_unavailable")
            continue
        block = _items_block(slot, alternatives, f"payload.summary.{selection}.items.{slot}", ordered=False)
        blocks.append(block)
        for choice in block.choices:
            games = choice.metrics.get("games")
            if games is None:
                warnings.append("missing_item_sample")
            elif games < min_games:
                warnings.append("low_item_sample")

    if not blocks:
        raise DataUnavailable("matchup summary has no item suggestions")

    overview = _object(getattr(snapshot, "overview", None), "snapshot.overview")
    matchup_metrics = {
        "scope": "champion_matchup",
        "win_rate": _metric(overview.get("win_rate"), "snapshot.overview.win_rate"),
        "games": _metric(overview.get("games"), "snapshot.overview.games", integer=True),
    }
    core_metrics = {"win_rate": None, "games": None}
    return BuildPage(
        selection="vs",
        label=label,
        title=f"WR {label} / taxa conjunta indisponível",
        keystone=primary,
        runes=runes,
        blocks=blocks,
        core_metrics=core_metrics,
        source_url=getattr(snapshot, "source_url", ""),
        query=deepcopy(query),
        resolved=deepcopy(resolved),
        collected_at=getattr(snapshot, "collected_at", ""),
        cache_hit=bool(getattr(snapshot, "cache_hit", False)),
        warnings=list(dict.fromkeys(warnings)),
        conditioning="opponent",
        matchup_metrics=matchup_metrics,
    )
