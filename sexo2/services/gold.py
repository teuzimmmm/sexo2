"""Item value comparison for the in-game scoreboard (decision D-009).

The value of a player's inventory is the sum of each item's total price for the
current patch (`priceTotal` from the client's own items.json) times its count.
It is the value of what players hold now, not the gold they earned: sold items,
spent consumables and unspent gold are invisible to the Live Client Data API.

Rows pair the players of both teams by their position in the Live Client
`playerlist`, which is assumed to follow the scoreboard order. That assumption,
and whether reordering the scoreboard is reflected there, still needs checking
in a real match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

ORDER = "ORDER"
CHAOS = "CHAOS"


class Unsupported(Exception):
    """The match has no two-team scoreboard to compare (e.g. Arena)."""


@dataclass(frozen=True)
class Row:
    order_champion: str
    chaos_champion: str
    order_value: int | None
    chaos_value: int | None

    @property
    def difference(self) -> int | None:
        """Positive when the ORDER player holds more value."""
        if self.order_value is None or self.chaos_value is None:
            return None
        return self.order_value - self.chaos_value


@dataclass(frozen=True)
class Comparison:
    rows: tuple[Row, ...]
    order_total: int | None
    chaos_total: int | None
    unknown_items: frozenset[int]

    @property
    def difference(self) -> int | None:
        if self.order_total is None or self.chaos_total is None:
            return None
        return self.order_total - self.chaos_total


def item_prices(items_json: Iterable[dict[str, Any]]) -> dict[int, int]:
    """Map item id to total price from /lol-game-data/assets/v1/items.json."""
    prices: dict[int, int] = {}
    for item in items_json:
        item_id = item.get("id")
        total = item.get("priceTotal")
        if isinstance(item_id, int) and isinstance(total, int) and not isinstance(total, bool) and total >= 0:
            prices[item_id] = total
    return prices


def inventory_value(items: Iterable[dict[str, Any]], prices: dict[int, int], unknown: set[int]) -> int | None:
    """Value of one inventory, or None when an item's price is unknown."""
    value = 0
    complete = True
    for item in items:
        item_id = item.get("itemID")
        count = item.get("count", 1)
        if not isinstance(item_id, int) or not isinstance(count, int) or count < 0:
            complete = False
            continue
        price = prices.get(item_id)
        if price is None:
            unknown.add(item_id)
            complete = False
            continue
        value += price * count
    return value if complete else None


def compare(playerlist: list[dict[str, Any]], prices: dict[int, int]) -> Comparison:
    """Pair both teams row by row and total their inventory values."""
    if not isinstance(playerlist, list):
        raise Unsupported("playerlist is not a list")
    teams: dict[str, list[dict[str, Any]]] = {ORDER: [], CHAOS: []}
    for player in playerlist:
        team = player.get("team") if isinstance(player, dict) else None
        if team not in teams:
            raise Unsupported(f"unexpected team {team!r}")
        teams[team].append(player)
    if not teams[ORDER] or len(teams[ORDER]) != len(teams[CHAOS]):
        raise Unsupported("teams are not paired")

    unknown: set[int] = set()
    rows = []
    for ally, enemy in zip(teams[ORDER], teams[CHAOS]):
        rows.append(
            Row(
                order_champion=str(ally.get("championName", "")),
                chaos_champion=str(enemy.get("championName", "")),
                order_value=inventory_value(ally.get("items") or [], prices, unknown),
                chaos_value=inventory_value(enemy.get("items") or [], prices, unknown),
            )
        )

    def total(values: list[int | None]) -> int | None:
        return None if any(v is None for v in values) else sum(values)  # type: ignore[arg-type]

    return Comparison(
        rows=tuple(rows),
        order_total=total([r.order_value for r in rows]),
        chaos_total=total([r.chaos_value for r in rows]),
        unknown_items=frozenset(unknown),
    )


def for_player_team(comparison: Comparison, my_team: str) -> Comparison:
    """Express differences from the local player's side (positive = ahead)."""
    if my_team == ORDER:
        return comparison
    if my_team != CHAOS:
        raise Unsupported(f"unexpected team {my_team!r}")
    rows = tuple(Row(r.chaos_champion, r.order_champion, r.chaos_value, r.order_value) for r in comparison.rows)
    return Comparison(rows, comparison.chaos_total, comparison.order_total, comparison.unknown_items)
