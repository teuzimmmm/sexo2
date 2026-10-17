"""Rune page rules, read from the client's own styles payload.

No rune tree is hardcoded: the slots, their perks and the allowed secondary
trees all come from ``GET /lol-perks/v1/styles``. The only fixed shape is the
one the client page format implies (``selectedPerkIds`` holds keystone, the
primary rows, two secondary perks and the stat mods, in that order).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

KEYSTONE_SLOT = "kKeyStone"
REGULAR_SLOT = "kMixedRegularSplashable"
STAT_MOD_SLOT = "kStatMod"
SECONDARY_PERK_COUNT = 2


class StylesError(Exception):
    """The styles payload cannot be used to judge pages."""


@dataclass(frozen=True)
class RuneSlot:
    kind: str
    perks: tuple[int, ...]
    label: str


@dataclass(frozen=True)
class RuneStyle:
    id: int
    name: str
    slots: tuple[RuneSlot, ...]
    allowed_sub_styles: tuple[int, ...]

    def slots_of(self, kind: str) -> tuple[RuneSlot, ...]:
        return tuple(slot for slot in self.slots if slot.kind == kind)

    @property
    def secondary_slots(self) -> tuple[RuneSlot, ...]:
        """Rows a perk can come from when this style is the secondary tree."""
        return tuple(slot for slot in self.slots if slot.kind not in (KEYSTONE_SLOT, STAT_MOD_SLOT))


@dataclass(frozen=True)
class PageSpec:
    """A page as the client stores it, without name or id."""

    primary_style_id: int
    sub_style_id: int
    perk_ids: tuple[int, ...]


@dataclass(frozen=True)
class Violation:
    """One broken rule. ``position`` indexes ``perk_ids`` when it applies."""

    code: str
    position: int | None = None
    perk_id: int | None = None


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StylesError(f"{path} must be an integer")
    return value


def _parse_style(payload: Any, index: int) -> RuneStyle:
    path = f"styles[{index}]"
    if not isinstance(payload, dict):
        raise StylesError(f"{path} must be an object")
    raw_slots = payload.get("slots")
    if not isinstance(raw_slots, list):
        raise StylesError(f"{path}.slots must be a list")
    slots = []
    for slot_index, raw in enumerate(raw_slots):
        slot_path = f"{path}.slots[{slot_index}]"
        if not isinstance(raw, dict) or not isinstance(raw.get("type"), str) or not isinstance(raw.get("perks"), list):
            raise StylesError(f"{slot_path} must have a type and a perks list")
        perks = tuple(_integer(perk, f"{slot_path}.perks") for perk in raw["perks"])
        label = raw.get("slotLabel") if isinstance(raw.get("slotLabel"), str) else ""
        slots.append(RuneSlot(raw["type"], perks, label))
    allowed = payload.get("allowedSubStyles")
    if not isinstance(allowed, list):
        raise StylesError(f"{path}.allowedSubStyles must be a list")
    name = payload.get("name") if isinstance(payload.get("name"), str) else ""
    return RuneStyle(
        id=_integer(payload.get("id"), f"{path}.id"),
        name=name,
        slots=tuple(slots),
        allowed_sub_styles=tuple(_integer(value, f"{path}.allowedSubStyles") for value in allowed),
    )


class StyleCatalog:
    """Validated view of the styles payload."""

    def __init__(self, styles: Iterable[RuneStyle]) -> None:
        self._styles = {style.id: style for style in styles}
        if not self._styles:
            raise StylesError("the client returned no rune styles")

    @classmethod
    def from_payload(cls, payload: Any) -> StyleCatalog:
        if not isinstance(payload, list):
            raise StylesError("styles must be a list")
        styles = [_parse_style(item, index) for index, item in enumerate(payload)]
        if len({style.id for style in styles}) != len(styles):
            raise StylesError("styles contain a repeated id")
        return cls(styles)

    def style(self, style_id: int) -> RuneStyle | None:
        return self._styles.get(style_id)

    @property
    def styles(self) -> tuple[RuneStyle, ...]:
        return tuple(self._styles.values())


def _slot_index(slots: tuple[RuneSlot, ...], perk: int) -> int | None:
    return next((index for index, slot in enumerate(slots) if perk in slot.perks), None)


def validate_page(spec: PageSpec, catalog: StyleCatalog) -> list[Violation]:
    """Every rule the page breaks; an empty list means the page is valid."""
    perks = spec.perk_ids
    if any(isinstance(perk, bool) or not isinstance(perk, int) for perk in perks):
        return [Violation("perk_not_integer")]
    primary = catalog.style(spec.primary_style_id)
    if primary is None:
        return [Violation("unknown_primary_style")]
    keystones = primary.slots_of(KEYSTONE_SLOT)
    rows = primary.slots_of(REGULAR_SLOT)
    stat_rows = primary.slots_of(STAT_MOD_SLOT)
    if len(keystones) != 1 or not rows or not stat_rows:
        return [Violation("unsupported_style_layout")]
    expected = 1 + len(rows) + SECONDARY_PERK_COUNT + len(stat_rows)
    if len(perks) != expected:
        return [Violation("perk_count")]

    violations: list[Violation] = []
    if perks[0] not in keystones[0].perks:
        violations.append(Violation("keystone_not_in_primary", 0, perks[0]))
    for offset, row in enumerate(rows, start=1):
        if perks[offset] not in row.perks:
            violations.append(Violation("primary_row_mismatch", offset, perks[offset]))

    secondary_start = 1 + len(rows)
    sub = catalog.style(spec.sub_style_id)
    if sub is None:
        violations.append(Violation("unknown_sub_style"))
    elif sub.id == primary.id:
        violations.append(Violation("sub_style_same_as_primary"))
    elif sub.id not in primary.allowed_sub_styles:
        violations.append(Violation("sub_style_not_allowed"))
    else:
        used_rows: list[int] = []
        for position in range(secondary_start, secondary_start + SECONDARY_PERK_COUNT):
            row_index = _slot_index(sub.secondary_slots, perks[position])
            if row_index is None:
                violations.append(Violation("secondary_not_in_sub_style", position, perks[position]))
            elif row_index in used_rows:
                violations.append(Violation("secondary_same_row", position, perks[position]))
            else:
                used_rows.append(row_index)

    stat_start = secondary_start + SECONDARY_PERK_COUNT
    for offset, row in enumerate(stat_rows):
        position = stat_start + offset
        if perks[position] not in row.perks:
            violations.append(Violation("stat_mod_row_mismatch", position, perks[position]))
    return violations


def page_from_layout(
    catalog: StyleCatalog, primary: Iterable[int], secondary: Iterable[int], stat_mods: Iterable[int]
) -> PageSpec:
    """Build a page from perk ids only (LoLalytics has no style ids).

    The primary style is the one whose keystone row holds the first perk; the
    secondary is the only other allowed style holding both secondary perks.
    The result still has to pass :func:`validate_page`.
    """
    try:
        primary_ids = tuple(int(perk) for perk in primary)
        secondary_ids = tuple(int(perk) for perk in secondary)
        stat_ids = tuple(int(perk) for perk in stat_mods)
    except (TypeError, ValueError):
        raise StylesError("layout perk ids must be integers") from None
    if not primary_ids:
        raise StylesError("layout has no keystone")
    owners = [
        style for style in catalog.styles if any(primary_ids[0] in s.perks for s in style.slots_of(KEYSTONE_SLOT))
    ]
    if len(owners) != 1:
        raise StylesError(f"keystone {primary_ids[0]} does not belong to exactly one style")
    main = owners[0]
    subs = [
        style
        for style in catalog.styles
        if style.id != main.id
        and style.id in main.allowed_sub_styles
        and all(_slot_index(style.secondary_slots, perk) is not None for perk in secondary_ids)
    ]
    if len(subs) != 1:
        raise StylesError("secondary perks do not identify exactly one style")
    return PageSpec(main.id, subs[0].id, primary_ids + secondary_ids + stat_ids)
