"""The build the player pinned for a champion: a rune page and an item trio (D-135).

Kept apart for Summoner's Rift and ARAM, whose builds differ: ranked, normal and
Swiftplay share ``sr``. Stored in ``assistant-favorites.json`` in the data folder,
written whole through a temporary file so a crash never leaves half a file.
Without a path (tests) the favourites live in memory only.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

log = logging.getLogger(__name__)

FILE_NAME = "assistant-favorites.json"
VERSION = 1


def group_for(mode: str | None) -> str | None:
    """``aram`` or ``sr`` for a statistics mode; None where the assistant has no statistics."""
    if mode == "aram":
        return "aram"
    if mode in ("ranked", "swift"):
        return "sr"
    return None


def _ids(value, low: int, high: int) -> list[int] | None:
    if not isinstance(value, list) or not low <= len(value) <= high:
        return None
    if any(isinstance(i, bool) or not isinstance(i, int) or i <= 0 for i in value):
        return None
    return list(value)


def _clean_page(page) -> dict | None:
    if not isinstance(page, dict):
        return None
    head = _ids([page.get("primary"), page.get("sub")], 2, 2)
    perks = _ids(page.get("perks"), 1, 12)
    if head is None or perks is None:
        return None
    return {"primary": head[0], "sub": head[1], "perks": perks}


class FavoriteBuilds:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: dict | None = None

    def get(self, group: str, champion_id: int) -> dict:
        """``{"runes": page or None, "items": [ids] or None}`` for this champion."""
        with self._lock:
            entry = self._load().get(group, {}).get(str(champion_id), {})
            return {"runes": entry.get("runes"), "items": entry.get("items")}

    def set_runes(self, group: str, champion_id: int, page: dict | None) -> None:
        self._set(group, champion_id, "runes", _clean_page(page) if page is not None else None)

    def set_items(self, group: str, champion_id: int, items: list[int] | None) -> None:
        self._set(group, champion_id, "items", _ids(items, 1, 6) if items is not None else None)

    def _set(self, group: str, champion_id: int, key: str, value) -> None:
        with self._lock:
            data = self._load()
            entry = data.setdefault(group, {}).setdefault(str(champion_id), {})
            if value is None:
                entry.pop(key, None)
                if not entry:
                    del data[group][str(champion_id)]
            else:
                entry[key] = value
            self._save(data)

    def _load(self) -> dict:
        if self._data is None:
            self._data = {}
            if self._path is not None and self._path.is_file():
                try:
                    raw = json.loads(self._path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict) and raw.get("version") == VERSION:
                        self._data = {g: raw[g] for g in ("sr", "aram") if isinstance(raw.get(g), dict)}
                except (OSError, ValueError) as error:
                    log.warning("[FAVORITES] unreadable %s: %s", self._path, error)
        return self._data

    def _save(self, data: dict) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"version": VERSION, **data}), encoding="utf-8")
            os.replace(temporary, self._path)
        except OSError as error:
            log.warning("[FAVORITES] could not save %s: %s", self._path, error)
