"""Serializable response model for locally risk-ranked recommendations."""
from dataclasses import asdict, dataclass
from copy import deepcopy
import math
import re
from typing import Any

from .builds import BuildPage
from .errors import DataUnavailable, SchemaError
from .risk import rank_candidates


@dataclass
class Recommendation:
    query: dict
    resolved: dict
    source_url: str
    collected_at: str
    cache_hit: bool
    risk_level: str
    policy: dict
    rune_candidates: list[dict]
    recommended_selection: str | None
    build_page: BuildPage | None
    item_source: dict
    item_rankings: dict[str, list[dict]]
    warnings: list[str]
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rune_candidates(snapshot: Any) -> list[dict]:
    """Read complete summary layouts and their own keystone observations."""
    from .builds import _opaque_id

    raw = snapshot.raw
    summary = raw.get("summary") if isinstance(raw, dict) else None
    if summary is None:
        raise DataUnavailable("LoLalytics has no rune summary")
    if not isinstance(summary, dict):
        raise SchemaError("LoLalytics summary must be an object")
    candidates = []
    for selection in ("win", "pick"):
        block = summary.get(selection)
        if block is None:
            continue
        if not isinstance(block, dict):
            raise SchemaError(f"LoLalytics summary.{selection} must be an object")
        runes = block.get("runes")
        if runes is None:
            continue
        if not isinstance(runes, dict):
            raise SchemaError(f"LoLalytics summary.{selection}.runes must be an object")
        rune_set = runes.get("set")
        if rune_set is None:
            continue
        if not isinstance(rune_set, dict):
            raise SchemaError(f"LoLalytics summary.{selection}.runes.set must be an object")
        layout = {}
        complete = True
        for slot, size in (("pri", 4), ("sec", 2), ("mod", 3)):
            ids = rune_set.get(slot)
            if ids is None:
                complete = False
                continue
            if not isinstance(ids, list):
                raise SchemaError(f"LoLalytics summary.{selection}.runes.set.{slot} must be an array")
            if len(ids) != size:
                complete = False
            layout[slot] = [_opaque_id(item, f"summary.{selection}.runes.set.{slot}[{i}]")
                            for i, item in enumerate(ids)]
        if not complete:
            continue
        primary = rune_set["pri"][0]
        if isinstance(primary, bool) or not isinstance(primary, int) or primary <= 0:
            raise SchemaError(f"LoLalytics summary.{selection} primary keystone must be a positive integer ID")
        if "page" in runes:
            if not isinstance(runes["page"], dict):
                raise SchemaError(f"LoLalytics summary.{selection}.runes.page must be an object")
            layout["page"] = deepcopy(runes["page"])
        candidates.append({
            "selection": selection,
            "keystone": primary,
            "runes": layout,
            "source_path": f"payload.summary.{selection}.runes",
            "source_url": snapshot.source_url,
            "metric_scope": "keystone_observation",
            "metrics": {"win_rate": runes.get("wr"), "games": runes.get("n")},
        })
    return candidates


def item_rankings(snapshot: Any, baseline: float | int, risk_level: str) -> dict[str, list[dict]]:
    """Group normalized item/augment rows by table and rank within each table."""
    groups = {}
    for record in snapshot.records:
        if record.category not in ("item_statistics", "item_combination", "augment_statistics"):
            continue
        parent = re.sub(r"\[\d+\]$", "", record.source_path)
        key = f"{record.category}:{record.metric_scope}:{parent}"
        groups.setdefault(key, []).append(asdict(record))

    result = {}
    arena = snapshot.query.get("mode") == "arena"
    for key, rows in groups.items():
        if arena:
            for row in rows:
                rate = row["metrics"].get("pick_rate")
                if rate is not None and (isinstance(rate, bool) or not isinstance(rate, (int, float))
                                         or not math.isfinite(rate) or rate < 0):
                    raise SchemaError("Arena pick_rate must be a finite non-negative number or null")
            ordered = sorted(enumerate(rows), key=lambda pair: (
                pair[1]["metrics"].get("pick_rate") is None,
                -(pair[1]["metrics"].get("pick_rate") or 0),
                -(pair[1]["metrics"].get("games") or 0), pair[0]))
            result[key] = []
            for _index, row in ordered:
                row["risk"] = {"score": None, "criterion": "pick_rate",
                               "reason": "risk_not_applicable_to_arena_popularity",
                               "risk_level": risk_level}
                result[key].append(row)
        else:
            result[key] = rank_candidates(rows, baseline, risk_level)
    return result
