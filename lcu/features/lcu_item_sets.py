"""Typed access to the client's item sets (``/lol-item-sets/v1``).

Community-documented contract, pending validation in the live client:
``GET /lol-item-sets/v1/item-sets/{summonerId}/sets`` returns
``{accountId, itemSets: [...], timestamp}`` and ``PUT`` on the same path
replaces the whole document. The summoner id comes from
``/lol-summoner/v1/current-summoner``. Reads are uncached because they confirm
writes; the document is passed through untouched so unknown fields survive.
"""

from __future__ import annotations

from typing import Any

from lcu.features.lcu_perks import LCUTransport

CURRENT_SUMMONER_PATH = "/lol-summoner/v1/current-summoner"


class ItemSetsError(Exception):
    """``code`` is ``unavailable``, ``schema`` or ``rejected`` (see ``status``)."""

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def sets_path(summoner_id: int) -> str:
    return f"/lol-item-sets/v1/item-sets/{summoner_id}/sets"


def validate_document(document: Any) -> dict:
    if not isinstance(document, dict):
        raise ItemSetsError("schema", "item sets document must be an object")
    sets = document.get("itemSets")
    if not isinstance(sets, list) or any(not isinstance(item, dict) for item in sets):
        raise ItemSetsError("schema", "item sets document must have an itemSets list of objects")
    return document


class LCUItemSets:
    """Blocking item set calls. Use from a worker thread, never from the UI."""

    def __init__(self, api: LCUTransport, *, timeout: float = 2.0) -> None:
        self._api = api
        self._timeout = timeout

    def summoner_id(self) -> int:
        summoner = self._api.get(CURRENT_SUMMONER_PATH, timeout=self._timeout, use_cache=False)
        if summoner is None:
            raise ItemSetsError("unavailable", "current summoner: no answer from the client")
        value = summoner.get("summonerId") if isinstance(summoner, dict) else None
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ItemSetsError("schema", "current summoner has no summonerId")
        return value

    def read(self, summoner_id: int) -> dict:
        document = self._api.get(sets_path(summoner_id), timeout=self._timeout, use_cache=False)
        if document is None:
            raise ItemSetsError("unavailable", "item sets: no answer from the client")
        return validate_document(document)

    def write(self, summoner_id: int, document: dict) -> None:
        path = sets_path(summoner_id)
        response = self._api.put(path, validate_document(document), self._timeout)
        if response is None:
            raise ItemSetsError("unavailable", f"PUT {path}: no answer from the client")
        try:
            status = getattr(response, "status_code", None)
            if not isinstance(status, int) or not 200 <= status < 300:
                raise ItemSetsError("rejected", f"PUT {path}: client answered {status}", status=status)
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
