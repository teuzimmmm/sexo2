"""Strict normalization of decoded LoLalytics page payloads."""
from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any

from .errors import DataUnavailable, SchemaError
from .models import Record, Snapshot


_METRIC_KEYS = ("win_rate", "pick_rate", "games")
_ARENA_ITEM_TABLES = (
    "startItem", "items", "item", "item1", "item2", "item3", "item4",
    "item5", "item6", "boots", "popularItem", "winningItem", "prismatic",
)


def _combo_tables(mode: str) -> tuple[str, ...]:
    if mode == "arena":
        return ("builtItemSet3", "startSet")
    return ("builtBootSet3", "startSet")


def _schema(message: str) -> SchemaError:
    return SchemaError(f"invalid LoLalytics payload: {message}")


def _number(value: Any, path: str) -> float | int | None:
    if value is None or value == "xx.xx":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _schema(f"{path} must be numeric, null, or 'xx.xx'")
    if not math.isfinite(value):
        raise _schema(f"{path} must be finite")
    return value


def _games(value: Any, path: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _schema(f"{path} must be a non-negative integer or null")
    return value


def _required_games(value: Any, path: str) -> int:
    result = _games(value, path)
    if result is None:
        raise _schema(f"{path} must be a non-negative integer")
    return result


def _id(value: Any, path: str) -> str:
    if isinstance(value, bool) or value is None or not isinstance(value, (int, str)):
        raise _schema(f"{path} must be an integer or opaque string ID")
    return str(value)


def _metrics(wr: Any, pr: Any, games: Any, path: str) -> dict[str, int | float | None]:
    return {
        "win_rate": _number(wr, f"{path}.wr"),
        "pick_rate": _number(pr, f"{path}.pr"),
        "games": _required_games(games, f"{path}.games"),
    }


def _array(value: Any, path: str) -> list:
    if not isinstance(value, list):
        raise _schema(f"{path} must be an array")
    return value


def _validate_raw_extra(value: Any, path: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, type(None))):
        raise _schema(f"{path} has an unsupported raw value")
    if isinstance(value, (int, float)) and not math.isfinite(value):
        raise _schema(f"{path} must be finite when numeric")


def _safe_metric_row(row: list, path: str, *, arena: bool, combination: bool) -> list:
    """Copy a confirmed row format and redact its win-rate cell for Arena."""
    if not isinstance(row, list):
        raise _schema(f"{path} row must be an array")
    allowed = (4,) if combination else (4, 5)
    if len(row) not in allowed:
        raise _schema(f"{path} row must have {allowed} fields")
    result = deepcopy(row)
    _id(result[0], f"{path}[0]")
    _number(result[1], f"{path}[1]")
    _number(result[2], f"{path}[2]")
    _required_games(result[3], f"{path}[3]")
    if len(row) == 5:
        # The final upstream value is preserved raw; its timing semantics are
        # intentionally not assigned a normalized name.
        _validate_raw_extra(row[4], f"{path}[4]")
    if arena:
        result[1] = None
    return result


def sanitize_payload(payload: dict, mode: str) -> dict:
    """Return an independent cache-safe payload copy.

    Arena is allowlisted to its champion header/graph and confirmed aggregate
    tables. Win-rate cells in item, combination, and augment rows are replaced
    by null. Unknown Arena fields are dropped because they may contain such
    rates. Other modes retain a deep copy of the decoded payload.
    """
    if not isinstance(payload, dict):
        raise _schema("payload must be an object")
    if mode != "arena":
        return deepcopy(payload)

    safe: dict[str, Any] = {}
    if "header" in payload:
        safe["header"] = deepcopy(payload["header"])
    if "graph" in payload:
        safe["graph"] = deepcopy(payload["graph"])
    if "analysed" in payload:
        safe["analysed"] = deepcopy(payload["analysed"])
    if "avgWr" in payload:
        safe["avgWr"] = deepcopy(payload["avgWr"])
    if "response" in payload:
        response = payload["response"]
        if not isinstance(response, dict):
            raise _schema("response must be an object")
        safe["response"] = {"valid": deepcopy(response.get("valid"))}

    for key in _combo_tables(mode):
        if key not in payload:
            continue
        table = _array(payload[key], f"payload.{key}")
        safe[key] = [
            _safe_metric_row(row, f"payload.{key}[{i}]", arena=True, combination=True)
            for i, row in enumerate(table)
        ]

    for key in _ARENA_ITEM_TABLES:
        if key not in payload:
            continue
        table = _array(payload[key], f"payload.{key}")
        safe[key] = [
            _safe_metric_row(row, f"payload.{key}[{i}]", arena=True, combination=False)
            for i, row in enumerate(table)
        ]

    if "augment" in payload:
        augments = payload["augment"]
        if not isinstance(augments, dict):
            raise _schema("payload.augment must be an object")
        safe_augment = {}
        for key, table in augments.items():
            rows = _array(table, f"payload.augment.{key}")
            safe_augment[key] = [
                _safe_metric_row(row, f"payload.augment.{key}[{i}]", arena=True, combination=True)
                for i, row in enumerate(rows)
            ]
        safe["augment"] = safe_augment

    return safe


def parse_page(body: bytes, query, source_url: str, collected_at: str) -> Snapshot:
    """Decode a Qwik q-data.json response and parse its resolved data."""
    from .decoding import decode_page

    nav, payload = decode_page(body)
    return parse_payload(nav, payload, query, source_url, collected_at)


def parse_payload(nav: dict, payload: dict, query, source_url: str, collected_at: str) -> Snapshot:
    """Validate decoded navigation/payload and create a normalized snapshot."""
    if not isinstance(nav, dict):
        raise _schema("nav must be an object")
    if not isinstance(payload, dict):
        raise _schema("payload must be an object")

    expected = {
        "champion": query.champion,
        "mode": query.mode,
        "tier": query.tier,
        "region": query.region,
        "lane": query.lane,
    }
    for key, want in expected.items():
        got = nav.get(key)
        if got != want:
            raise _schema(f"resolved {key} does not match the requested filter")
    if query.opponent is None:
        if nav.get("vs") not in (None, "") or any(nav.get(key) is not None for key in ("vsCid", "vsName")):
            raise _schema("resolved opponent does not match the requested filter")
    else:
        if nav.get("vs") != query.opponent:
            raise _schema("resolved opponent does not match the requested filter")
        if nav.get("vsLane") != query.opponent_lane:
            raise _schema("resolved opponent lane does not match the requested filter")
        nav_vs_cid = nav.get("vsCid")
        if isinstance(nav_vs_cid, bool) or not isinstance(nav_vs_cid, int) or nav_vs_cid <= 0:
            raise _schema("resolved opponent ID must be a positive integer")
        nav_vs_name = nav.get("vsName")
        if not isinstance(nav_vs_name, str) or not nav_vs_name:
            raise _schema("resolved opponent name must be a string")
    nav_keystone = nav.get("keystone")
    if query.keystone is None:
        if "keystone" in nav and (
            isinstance(nav_keystone, bool) or not isinstance(nav_keystone, int) or nav_keystone != -1
        ):
            raise _schema("resolved keystone does not match the requested filter")
    elif (
        isinstance(nav_keystone, bool)
        or not isinstance(nav_keystone, int)
        or nav_keystone != query.keystone
    ):
        raise _schema("resolved keystone does not match the requested filter")
    nav_patch = nav.get("patch")
    if not isinstance(nav_patch, str) or not re.fullmatch(r"\d{2}\.\d{1,2}", nav_patch):
        raise _schema("nav.patch must use the observed numeric patch format")
    if query.patch is not None and nav_patch != query.patch:
        raise _schema("resolved patch does not match the requested filter")
    if nav.get("status") != 200 or isinstance(nav.get("status"), bool):
        raise _schema("nav.status must be HTTP 200")

    header = payload.get("header")
    if not isinstance(header, dict):
        raise _schema("payload.header is required and must be an object")
    effective_opponent_lane = None
    if query.opponent is None:
        if header.get("vs") is not None:
            raise _schema("header contains an unexpected opponent")
    else:
        header_vs = header.get("vs")
        if isinstance(header_vs, bool) or not isinstance(header_vs, int) or header_vs <= 0:
            raise _schema("header opponent ID must be a positive integer")
        if header_vs != nav.get("vsCid"):
            raise _schema("header opponent ID does not match resolved navigation")
        from .query import LANES
        header_vs_lane = header.get("vsLane")
        if "vsLane" not in header and query.opponent_lane != "all":
            raise _schema("header opponent lane is missing")
        if header_vs_lane not in (None, "all"):
            if header_vs_lane not in LANES:
                raise _schema("header opponent lane is outside the supported positions")
            effective_opponent_lane = header_vs_lane
        else:
            default_vs_lane = header.get("defaultVsLane")
            if default_vs_lane is not None:
                if default_vs_lane not in LANES:
                    raise _schema("header default opponent lane is outside the supported positions")
                if default_vs_lane != "all":
                    effective_opponent_lane = default_vs_lane
            if effective_opponent_lane is None and header_vs_lane == "all":
                effective_opponent_lane = "all"
        if query.opponent_lane != "all" and effective_opponent_lane != query.opponent_lane:
            raise _schema("header opponent lane does not match the requested filter")
    effective_lane = None
    if query.mode == "ranked":
        effective_lane = header.get("lane")
        if effective_lane in (None, "all"):
            effective_lane = header.get("defaultLane")
        if effective_lane is not None and effective_lane != "all":
            from .query import LANES
            if effective_lane not in LANES:
                raise _schema("header lane is outside the supported positions")
            if query.lane != "all" and effective_lane != query.lane:
                raise _schema("header effective lane does not match the requested filter")
    nav_cid = nav.get("cid")
    header_cid = header.get("cid")
    if isinstance(nav_cid, bool) or not isinstance(nav_cid, int):
        raise _schema("nav.cid must be an integer")
    if nav_cid <= 0:
        raise _schema("nav.cid must be positive")
    if isinstance(header_cid, bool) or not isinstance(header_cid, int):
        raise _schema("header.cid must be an integer")
    if header_cid != nav_cid:
        raise _schema("header.cid does not match nav.cid")
    if "patch" in header and header["patch"] != nav_patch:
        raise _schema("header.patch does not match nav.patch")
    expected_queue = {"ranked": 420, "aram": 450, "swift": 480}.get(query.mode)
    if "queue" in header and expected_queue is not None:
        queue = header["queue"]
        if isinstance(queue, bool) or not isinstance(queue, int) or queue != expected_queue:
            raise _schema("header.queue does not match the resolved mode")
    if "n" not in header:
        raise _schema("header.n is required")
    if isinstance(header["n"], bool) or not isinstance(header["n"], int):
        raise _schema("header.n must be an integer")
    games = _games(header["n"], "payload.header.n")
    if games == 0:
        raise DataUnavailable("LoLalytics returned zero champion games for this query")

    response = payload.get("response")
    if not isinstance(response, dict):
        raise _schema("payload.response is required and must be an object")
    if "valid" not in response or not isinstance(response["valid"], bool):
        raise _schema("payload.response.valid is required and must be boolean")
    if response["valid"] is False:
        raise DataUnavailable("LoLalytics marked this payload invalid")

    safe_payload = sanitize_payload(payload, query.mode)
    arena = query.mode == "arena"
    records: list[Record] = []
    availability: dict[str, str] = {}
    warnings: list[str] = []
    if arena:
        warnings.append("Arena item, combination, and augment win rates are suppressed by policy; pick rates and game counts remain available.")
        safe_keys = {
            "header", "graph", "analysed", "avgWr", "response", "augment",
            *_combo_tables(query.mode), *_ARENA_ITEM_TABLES,
        }
        discarded = sorted(set(payload) - safe_keys)
        if discarded:
            warnings.append("Unrecognized Arena payload fields were discarded by policy.")

    # Known three-item combinations and explicit starting-item combinations.
    combo_tables = _combo_tables(query.mode)
    for key in combo_tables:
        if key not in payload:
            continue
        rows = _array(payload[key], f"payload.{key}")
        availability["item_combination:" + key] = "available"
        for index, row in enumerate(rows):
            path = f"payload.{key}[{index}]"
            if not isinstance(row, list) or len(row) != 4:
                raise _schema(f"{path} must be [ids, win_rate, pick_rate, games]")
            raw_ids = row[0]
            if not isinstance(raw_ids, str):
                raise _schema(f"{path}[0] must be an underscore-separated ID string")
            identifiers = [] if raw_ids == "" else [_id(part, path) for part in raw_ids.split("_")]
            metrics = _metrics(None if arena else row[1], row[2], row[3], path)
            safe_row = safe_payload.get(key, rows)[index]
            records.append(Record("item_combination", identifiers, metrics, path, deepcopy(safe_row), "joint_build_sample"))

    item_keys = tuple(dict.fromkeys(_ARENA_ITEM_TABLES + ("boots",)))
    for key in item_keys:
        if key not in payload:
            continue
        rows = _array(payload[key], f"payload.{key}")
        availability["item_statistics:" + key] = "available"
        for index, row in enumerate(rows):
            path = f"payload.{key}[{index}]"
            if not isinstance(row, list) or len(row) not in (4, 5):
                raise _schema(f"{path} must be [id, win_rate, pick_rate, games, ...]")
            if len(row) == 5:
                _validate_raw_extra(row[4], f"{path}[4]")
            identifier = _id(row[0], path)
            metrics = _metrics(None if arena else row[1], row[2], row[3], path)
            safe_row = safe_payload.get(key, rows)[index]
            records.append(Record("item_statistics", [identifier], metrics, path, deepcopy(safe_row), "item_observation"))

    runes = payload.get("runes")
    if arena:
        availability["rune_statistics"] = "not_applicable"
    else:
        if runes is None:
            availability["rune_statistics"] = "unavailable"
        else:
            if not isinstance(runes, dict) or not isinstance(runes.get("stats"), dict):
                raise _schema("payload.runes.stats must be an object")
            availability["rune_statistics"] = "available"
            for rune_id, slots in runes["stats"].items():
                rune_key = _id(rune_id, "payload.runes.stats key")
                if not isinstance(slots, list):
                    raise _schema(f"payload.runes.stats.{rune_key} must be an array")
                for slot, row in enumerate(slots):
                    path = f"payload.runes.stats.{rune_key}[{slot}]"
                    if not isinstance(row, list) or len(row) != 3:
                        raise _schema(f"{path} must be [pick_rate, win_rate, games]")
                    metrics = {
                        "win_rate": _number(row[1], f"{path}[1]"),
                        "pick_rate": _number(row[0], f"{path}[0]"),
                        "games": _required_games(row[2], f"{path}[2]"),
                    }
                    records.append(Record("rune_statistics", [rune_key, str(slot)], metrics, path, deepcopy(row), "rune_observation"))

    summary = payload.get("summary")
    complete_suggestions = 0
    if summary is not None and not arena:
        if not isinstance(summary, dict):
            raise _schema("payload.summary must be an object")
        for result_type in ("pick", "win"):
            block = summary.get(result_type)
            if block is None:
                continue
            if not isinstance(block, dict):
                raise _schema(f"payload.summary.{result_type} must be an object")
            rune_info = block.get("runes")
            if rune_info is None:
                availability[f"rune_suggestion:{result_type}"] = "unavailable"
                continue
            if not isinstance(rune_info, dict):
                raise _schema(f"payload.summary.{result_type}.runes must be an object")
            rune_set = rune_info.get("set")
            if rune_set is None:
                availability[f"rune_suggestion:{result_type}"] = "unavailable"
                warnings.append(f"Rune suggestion layout '{result_type}' is incomplete and was omitted.")
                continue
            if not isinstance(rune_set, dict):
                raise _schema(f"payload.summary.{result_type}.runes.set must be an object")
            expected_sizes = {"pri": 4, "sec": 2, "mod": 3}
            layout_ids: list[str] = []
            complete = True
            for slot in ("pri", "sec", "mod"):
                ids = rune_set.get(slot)
                if ids is None:
                    complete = False
                    continue
                if not isinstance(ids, list):
                    raise _schema(f"payload.summary.{result_type}.runes.set.{slot} must be an array")
                if len(ids) != expected_sizes[slot]:
                    complete = False
                for index, raw_id in enumerate(ids):
                    layout_ids.append(_id(raw_id, f"payload.summary.{result_type}.runes.set.{slot}[{index}]"))
            if not complete:
                availability[f"rune_suggestion:{result_type}"] = "unavailable"
                warnings.append(f"Rune suggestion layout '{result_type}' is incomplete and was omitted.")
                continue
            records.append(Record(
                "rune_suggestion", layout_ids, dict.fromkeys(_METRIC_KEYS),
                f"payload.summary.{result_type}.runes.set",
                {"selection": deepcopy(layout_ids), "page": deepcopy(rune_info.get("page")), "set": deepcopy(rune_set)},
                "suggested_layout_not_joint_sample",
            ))
            complete_suggestions += 1
            availability[f"rune_suggestion:{result_type}"] = "available"
    availability["rune_suggestion"] = "available" if complete_suggestions else "unavailable"
    if arena:
        availability["rune_suggestion"] = "not_applicable"
        for result_type in ("pick", "win"):
            availability.setdefault(f"rune_suggestion:{result_type}", "not_applicable")
    if complete_suggestions:
        warnings.append("Rune suggestions describe layouts and do not establish a joint sample or page-wide metrics.")

    augments = payload.get("augment")
    if query.mode != "arena":
        availability["augment_statistics"] = "not_applicable"
    else:
        if augments is None:
            availability["augment_statistics"] = "unavailable"
        else:
            if not isinstance(augments, dict):
                raise _schema("payload.augment must be an object")
            availability["augment_statistics"] = "available"
            for table_name, rows in augments.items():
                if not isinstance(rows, list):
                    raise _schema(f"payload.augment.{table_name} must be an array")
                for index, row in enumerate(rows):
                    path = f"payload.augment.{table_name}[{index}]"
                    if not isinstance(row, list) or len(row) != 4:
                        raise _schema(f"{path} must be [id, win_rate, pick_rate, games]")
                    identifier = _id(row[0], path)
                    metrics = _metrics(None, row[2], row[3], path)
                    safe_row = safe_payload["augment"][table_name][index]
                    records.append(Record("augment_statistics", [identifier], metrics, path, deepcopy(safe_row), "augment_observation"))

    # Missing optional tables are explicit; an absent table is not an empty
    # successful collector response.
    for key in combo_tables:
        availability.setdefault("item_combination:" + key, "unavailable")
    for key in item_keys:
        availability.setdefault("item_statistics:" + key, "unavailable")

    overview = {
        "champion_id": nav_cid,
        "patch": nav_patch,
        "games": games,
        "win_rate": _number(header.get("wr"), "payload.header.wr"),
        "pick_rate": _number(header.get("pr"), "payload.header.pr"),
    }
    if "tier" in header:
        overview["tier"] = deepcopy(header["tier"])
    if "rank" in header:
        overview["rank"] = deepcopy(header["rank"])
    if "rankTotal" in header:
        overview["rank_total"] = deepcopy(header["rankTotal"])
    if not arena:
        if "avgWr" in payload:
            overview["average_win_rate"] = _number(payload["avgWr"], "payload.avgWr")
        elif "avgWr" in header:
            overview["average_win_rate"] = _number(header["avgWr"], "payload.header.avgWr")
    else:
        average_wr = payload.get("avgWr", header.get("avgWr"))
        if average_wr is not None:
            overview["average_win_rate"] = _number(average_wr, "payload.avgWr")
        placements = {}
        for place in range(1, 9):
            key = f"place{place}"
            if key in header:
                placements[key] = _number(header[key], f"payload.header.{key}")
        if placements:
            overview["placement_rates"] = placements

    resolved = {
        key: deepcopy(nav.get(key))
        for key in ("champion", "cid", "mode", "patch", "lane", "tier", "region", "status", "key")
        if key in nav
    }
    resolved["keystone"] = query.keystone
    if query.opponent is not None:
        resolved.update({
            "opponent": query.opponent,
            "opponent_id": deepcopy(nav["vsCid"]),
            "opponent_name": deepcopy(nav["vsName"]),
            "opponent_lane": query.opponent_lane,
        })
        if effective_opponent_lane is not None and effective_opponent_lane != "all":
            resolved["effective_opponent_lane"] = deepcopy(effective_opponent_lane)
    if isinstance(nav.get("champName"), str):
        resolved["champion_name"] = nav["champName"]
    if isinstance(nav.get("currentPatch"), str):
        resolved["current_patch"] = nav["currentPatch"]
    if query.mode == "ranked":
        if effective_lane is not None and effective_lane != "all":
            resolved["effective_lane"] = effective_lane
    return Snapshot(
        query=query.to_dict(), resolved=resolved, source_url=source_url,
        collected_at=collected_at, overview=overview, records=records,
        raw=safe_payload, availability=availability, warnings=warnings,
    )
