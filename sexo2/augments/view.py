"""What each offered card shows.

A card is "unknown" when the recogniser was not sure (and the player did not
correct it) or the augment is not in the current mode's pool; it then shows
no statistics. A known card without statistics shows no numbers.

The highlight marks the card with the highest win rate, only when at least
two known cards have a win rate with at least ``min_games`` games: a single
figure or a pick rate alone says nothing about which choice is better, so
Arena (pick rate only) is never highlighted.
"""

from __future__ import annotations

from dataclasses import dataclass

from sexo2.augments.catalog import Catalog
from sexo2.augments.offers import Offer
from sexo2.augments.stats import AugmentStat


@dataclass(frozen=True)
class CardView:
    index: int
    state: str  # "ok", "no_data" or "unknown"
    augment_id: int | None
    name: str
    rarity: str
    icon_path: str
    manual: bool
    stat: AugmentStat | None
    highlight: bool = False


def card_views(
    offer: Offer,
    catalog: Catalog,
    stats: dict[int, AugmentStat],
    *,
    min_confidence: float = 0.6,
    min_games: int = 200,
) -> tuple[CardView, ...]:
    views = []
    for index, card in enumerate(offer.cards):
        augment = catalog.by_id(card.augment_id) if card.augment_id is not None else None
        sure = card.manual or card.confidence >= min_confidence
        if augment is None or not sure:
            views.append(CardView(index, "unknown", None, "", "", "", card.manual, None))
            continue
        stat = stats.get(augment.id)
        if stat is not None and stat.mode != catalog.mode:
            stat = None  # never show one mode's figure in the other
        views.append(
            CardView(
                index,
                "ok" if stat is not None else "no_data",
                augment.id,
                augment.name,
                augment.rarity,
                augment.icon_path,
                card.manual,
                stat,
            )
        )
    eligible = [
        v for v in views if v.stat is not None and v.stat.win_rate is not None and (v.stat.games or 0) >= min_games
    ]
    if len(eligible) >= 2:
        best = max(eligible, key=lambda v: v.stat.win_rate)
        if sum(1 for v in eligible if v.stat.win_rate == best.stat.win_rate) == 1:
            views[best.index] = CardView(**{**best.__dict__, "highlight": True})
    return tuple(views)
