"""Decode the small subset of Qwik's JSON state used by LoLalytics pages."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from .errors import DataUnavailable, SchemaError

_BASE36 = re.compile(r"^[0-9a-z]+$")
_MAX_OBJECTS = 50_000
_MAX_DEPTH = 80
_MAX_NODES = 200_000


def _ref_index(value: str, size: int) -> int | None:
    """Return a valid index or None; container strings must be references."""
    # Any index in a supported table is at most four base36 digits. Avoid
    # converting hostile, arbitrarily long strings to Python integers.
    if len(value) > 8 or not _BASE36.fullmatch(value):
        return None
    try:
        index = int(value, 36)
    except ValueError:  # defensive; the regular expression already constrains it
        return None
    return index if index < size else None


def decode_page(body: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    """Decode Qwik ``q-data.json`` into navigation metadata and page payload.

    This resolves only the metadata and loader object containing a page header.
    Qwik's object table uses base36 strings as references; a resolved table
    string is returned literally and is never interpreted as a second reference.
    """
    if not isinstance(body, bytes):
        raise SchemaError("Qwik page data must be bytes")
    if len(body) > 4 * 1024 * 1024:
        raise SchemaError("Qwik page data exceeds 4 MiB")

    def reject_constant(_):
        raise ValueError("non-finite JSON constant")

    try:
        document = json.loads(body, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SchemaError("Qwik page data is not valid JSON") from exc
    if not isinstance(document, dict):
        raise SchemaError("Qwik page data root must be an object")
    objects = document.get("_objs")
    entry_ref = document.get("_entry")
    if not isinstance(objects, list) or not isinstance(entry_ref, str):
        raise SchemaError("Qwik page data requires _entry and _objs")
    if len(objects) > _MAX_OBJECTS:
        raise SchemaError(f"Qwik object table exceeds {_MAX_OBJECTS} objects")
    if any(not isinstance(item, (dict, list, str, int, float, bool, type(None))) for item in objects):
        raise SchemaError("Qwik object table contains an unsupported value")

    entry_index = _ref_index(entry_ref, len(objects))
    if entry_index is None:
        raise SchemaError("Qwik entry reference is invalid")
    entry = objects[entry_index]
    if not isinstance(entry, dict) or "loaders" not in entry:
        raise SchemaError("Qwik entry does not contain loader references")

    nodes = 0

    def literal_string(value: str) -> str | None:
        if value == "\x01":
            return None
        if any(ord(char) < 32 and char not in "\t\r\n" for char in value):
            raise SchemaError("Qwik value contains an unsupported marker")
        return value

    def required_index(value: Any, label: str = "reference") -> int:
        if not isinstance(value, str):
            raise SchemaError(f"Qwik {label} is not a string reference")
        index = _ref_index(value, len(objects))
        if index is None:
            raise SchemaError(f"Qwik {label} is invalid")
        return index

    def resolve(value: Any, depth: int = 0, active: frozenset[int] = frozenset()) -> Any:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_NODES:
            raise SchemaError(f"Qwik expansion exceeds {_MAX_NODES} nodes")
        if depth > _MAX_DEPTH:
            raise SchemaError(f"Qwik expansion exceeds depth {_MAX_DEPTH}")
        if isinstance(value, str):
            if value == "\x01":
                return None
            if any(ord(char) < 32 and char not in "\t\r\n" for char in value):
                raise SchemaError("Qwik value contains an unsupported marker")
            index = required_index(value)
            if index in active:
                raise SchemaError("Qwik object reference cycle detected")
            target = objects[index]
            if isinstance(target, str):
                # Strings in the object table are literal values, even when
                # their contents happen to look like a base36 reference.
                return literal_string(target)
            return resolve(target, depth + 1, active | {index})
        if isinstance(value, list):
            return [resolve(item, depth + 1, active) for item in value]
        if isinstance(value, dict):
            return {key: resolve(item, depth + 1, active) for key, item in value.items()}
        if isinstance(value, float) and not math.isfinite(value):
            raise SchemaError("Qwik value must be a finite number")
        if value is None or isinstance(value, (bool, int, float)):
            return value
        raise SchemaError("Qwik value has an unsupported type")

    if "status" not in entry:
        raise SchemaError("Qwik entry does not contain a status")
    status = resolve(entry["status"])
    if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
        raise SchemaError("Qwik entry status must be an HTTP status integer")
    if status != 200:
        raise DataUnavailable(f"LoLalytics page data is unavailable (status {status})")

    loaders_index = required_index(entry["loaders"], "loader map reference")
    loader_map = objects[loaders_index]
    if not isinstance(loader_map, dict):
        raise SchemaError("Qwik loader map is not an object")

    nav_candidates: list[dict[str, Any]] = []
    payload_candidates: list[dict[str, Any]] = []
    for loader_ref in loader_map.values():
        if not isinstance(loader_ref, str):
            raise SchemaError("Qwik loader reference is not a string")
        loader_index = required_index(loader_ref, "loader reference")
        loader = objects[loader_index]
        if not isinstance(loader, dict):
            continue

        # The field names are literal schema keys. Inspect their structure
        # before resolving so unrelated loaders (large constants) stay untouched.
        if {"currentPatch", "champion", "mode"}.issubset(loader):
            candidate = resolve(loader, active=frozenset({loader_index}))
            if isinstance(candidate, dict):
                nav_candidates.append(candidate)
        if "header" in loader:
            candidate = resolve(loader, active=frozenset({loader_index}))
            header = candidate.get("header") if isinstance(candidate, dict) else None
            if isinstance(header, dict) and any(key in header for key in ("patch", "cid", "queue", "n")):
                payload_candidates.append(candidate)

    def unique_candidate(candidates: list[dict[str, Any]], label: str) -> dict[str, Any]:
        if not candidates:
            raise SchemaError(f"Qwik page has no structurally valid {label} loader")
        first = candidates[0]
        if any(candidate != first for candidate in candidates[1:]):
            raise SchemaError(f"Qwik page has contradictory {label} loaders")
        return first

    nav = unique_candidate(nav_candidates, "navigation")
    payload = unique_candidate(payload_candidates, "payload")
    return nav, payload
