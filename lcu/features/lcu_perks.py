"""Typed access to the client's rune pages (``/lol-perks/v1``).

The endpoint contract below is the community-documented one; it has not been
checked against the live client by this project yet (pending real
validation). Every read is uncached, because callers use it to confirm a
write. Missing or mistyped fields raise :class:`PerksError`; nothing here
reports success it did not observe.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

PAGES_PATH = "/lol-perks/v1/pages"
CURRENT_PAGE_PATH = "/lol-perks/v1/currentpage"
INVENTORY_PATH = "/lol-perks/v1/inventory"
STYLES_PATH = "/lol-perks/v1/styles"


class PerksError(Exception):
    """A rune page read or write that did not produce a usable answer.

    ``code`` is stable and meant for callers: ``unavailable`` (no answer),
    ``schema`` (answer with an unexpected shape) or ``rejected`` (the client
    refused a write; ``status`` holds the HTTP status).
    """

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class LCUTransport(Protocol):
    """The subset of :class:`lcu.core.lcu_api.LCUAPI` used here."""

    def get(self, path: str, timeout: float = 1.0, cache_ttl: float | None = None, use_cache: bool = True) -> Any: ...

    def put(self, path: str, json_data: Any, timeout: float, headers: dict | None = None) -> Any: ...

    def post(self, path: str, json_data: Any, timeout: float) -> Any: ...


@dataclass(frozen=True)
class RunePage:
    id: int
    name: str
    is_editable: bool
    is_deletable: bool
    is_active: bool
    current: bool
    primary_style_id: int
    sub_style_id: int
    selected_perk_ids: tuple[int, ...]

    @property
    def is_custom(self) -> bool:
        """A page the player made, counted against ``ownedPageCount``."""
        return self.is_editable and self.is_deletable


@dataclass(frozen=True)
class PageBody:
    """What a write sends. ``selected_perk_ids`` keeps the client's order."""

    name: str
    primary_style_id: int
    sub_style_id: int
    selected_perk_ids: tuple[int, ...]

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "primaryStyleId": self.primary_style_id,
            "subStyleId": self.sub_style_id,
            "selectedPerkIds": list(self.selected_perk_ids),
            "current": True,
        }


def _schema(message: str) -> PerksError:
    return PerksError("schema", f"unexpected rune page data: {message}")


def _field(source: dict, name: str, kind: type, path: str) -> Any:
    if name not in source:
        raise _schema(f"{path}.{name} is missing")
    value = source[name]
    if kind is int and (isinstance(value, bool) or not isinstance(value, int)):
        raise _schema(f"{path}.{name} must be an integer")
    if kind is not int and not isinstance(value, kind):
        raise _schema(f"{path}.{name} must be {kind.__name__}")
    return value


def parse_page(payload: Any, path: str = "page") -> RunePage:
    if not isinstance(payload, dict):
        raise _schema(f"{path} must be an object")
    perks = _field(payload, "selectedPerkIds", list, path)
    if any(isinstance(perk, bool) or not isinstance(perk, int) for perk in perks):
        raise _schema(f"{path}.selectedPerkIds must contain integers")
    return RunePage(
        id=_field(payload, "id", int, path),
        name=_field(payload, "name", str, path),
        is_editable=_field(payload, "isEditable", bool, path),
        is_deletable=_field(payload, "isDeletable", bool, path),
        is_active=bool(payload.get("isActive", False)),
        current=_field(payload, "current", bool, path),
        primary_style_id=_field(payload, "primaryStyleId", int, path),
        sub_style_id=_field(payload, "subStyleId", int, path),
        selected_perk_ids=tuple(perks),
    )


def _accepted(response: Any, method: str, path: str) -> Any:
    if response is None:
        raise PerksError("unavailable", f"{method} {path}: no answer from the client")
    status = getattr(response, "status_code", None)
    try:
        if not isinstance(status, int) or not 200 <= status < 300:
            raise PerksError("rejected", f"{method} {path}: client answered {status}", status=status)
        if status == 204 or not getattr(response, "content", b""):
            return None
        try:
            return response.json()
        except ValueError:
            return None
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()


class LCUPerks:
    """Blocking rune page calls. Use from a worker thread, never from the UI."""

    def __init__(self, api: LCUTransport, *, timeout: float = 2.0) -> None:
        self._api = api
        self._timeout = timeout

    def _get(self, path: str) -> Any:
        value = self._api.get(path, timeout=self._timeout, use_cache=False)
        if value is None:
            raise PerksError("unavailable", f"GET {path}: no answer from the client")
        return value

    def pages(self) -> list[RunePage]:
        payload = self._get(PAGES_PATH)
        if not isinstance(payload, list):
            raise _schema("pages must be a list")
        return [parse_page(item, f"pages[{index}]") for index, item in enumerate(payload)]

    def current_page(self) -> RunePage:
        return parse_page(self._get(CURRENT_PAGE_PATH), "currentpage")

    def owned_page_count(self) -> int:
        payload = self._get(INVENTORY_PATH)
        if not isinstance(payload, dict):
            raise _schema("inventory must be an object")
        count = _field(payload, "ownedPageCount", int, "inventory")
        if count < 0:
            raise _schema("inventory.ownedPageCount must not be negative")
        return count

    def styles(self) -> list[dict]:
        """Raw styles payload; :mod:`sexo2.services.rune_rules` interprets it."""
        payload = self._get(STYLES_PATH)
        if not isinstance(payload, list):
            raise _schema("styles must be a list")
        return payload

    def create_page(self, body: PageBody) -> RunePage:
        created = _accepted(self._api.post(PAGES_PATH, body.to_json(), self._timeout), "POST", PAGES_PATH)
        if created is None:
            raise _schema("POST pages returned no page")
        return parse_page(created, "created page")

    def update_page(self, page_id: int, body: PageBody) -> None:
        """Replace a page. The answer is not trusted; read the page back."""
        path = f"{PAGES_PATH}/{page_id}"
        _accepted(self._api.put(path, {"id": page_id, **body.to_json()}, self._timeout), "PUT", path)

    def set_current(self, page_id: int) -> None:
        _accepted(self._api.put(CURRENT_PAGE_PATH, page_id, self._timeout), "PUT", CURRENT_PAGE_PATH)
