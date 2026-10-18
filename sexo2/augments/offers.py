"""Offer tracking from successive screen readings, and what each card shows.

A reading is what the recogniser saw on one frame: ``None`` when no cards are
on screen, else one :class:`CardRead` per card. The tracker smooths readings so
a single bad frame neither opens, changes nor closes the offer:

- the offer opens after ``show_after`` consecutive frames with cards;
- a card changes (reroll) after ``change_after`` consecutive frames reading
  the same new augment in its place;
- the offer closes after ``close_after`` consecutive frames without cards.

The player can correct a card by hand; the correction holds until that card
changes or the offer closes. Cards are only ever the ones offered: nothing
outside the reading or a correction can appear.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence


@dataclass(frozen=True)
class CardRead:
    augment_id: int | None  # None: not recognised
    confidence: float = 0.0  # 0..1, from the recogniser


@dataclass(frozen=True)
class Card:
    augment_id: int | None
    confidence: float
    manual: bool = False
    seen_id: int | None = None  # what the recogniser read; a correction keeps it to notice a reroll

    @property
    def known(self) -> bool:
        return self.augment_id is not None


@dataclass(frozen=True)
class Offer:
    sequence: int  # increases for every new offer; rerolls keep it
    cards: tuple[Card, ...]


class OfferTracker:
    def __init__(self, *, show_after: int = 2, change_after: int = 2, close_after: int = 3) -> None:
        self._show_after = show_after
        self._change_after = change_after
        self._close_after = close_after
        self._offer: Offer | None = None
        self._sequence = 0
        self._seen = 0
        self._missing = 0
        self._pending: dict[int, tuple[int | None, int]] = {}  # card index -> (candidate id, frames)

    @property
    def offer(self) -> Offer | None:
        return self._offer

    def observe(self, reading: Sequence[CardRead] | None) -> bool:
        """Feed one frame; True when the visible offer changed (opened, rerolled or closed)."""
        if not reading:
            self._seen = 0
            self._pending.clear()
            if self._offer is None:
                return False
            self._missing += 1
            if self._missing >= self._close_after:
                self._offer = None
                return True
            return False
        self._missing = 0
        if self._offer is None or len(reading) != len(self._offer.cards):
            self._seen += 1
            if self._seen < self._show_after:
                return False
            self._sequence += 1
            self._offer = Offer(
                self._sequence, tuple(Card(r.augment_id, r.confidence, seen_id=r.augment_id) for r in reading)
            )
            self._pending.clear()
            return True
        changed = False
        cards = list(self._offer.cards)
        for index, read in enumerate(reading):
            current = cards[index]
            if read.augment_id == current.seen_id:
                self._pending.pop(index, None)
                if not current.manual and read.augment_id is not None and read.confidence > current.confidence:
                    cards[index] = replace(current, confidence=read.confidence)
                continue
            candidate, frames = self._pending.get(index, (None, 0))
            frames = frames + 1 if candidate == read.augment_id else 1
            if frames >= self._change_after:
                cards[index] = Card(read.augment_id, read.confidence, seen_id=read.augment_id)
                self._pending.pop(index, None)
                changed = True
            else:
                self._pending[index] = (read.augment_id, frames)
        self._offer = Offer(self._offer.sequence, tuple(cards))
        return changed

    def correct(self, index: int, augment_id: int) -> bool:
        """The player names the augment on card ``index``."""
        if self._offer is None or not 0 <= index < len(self._offer.cards):
            return False
        cards = list(self._offer.cards)
        cards[index] = Card(augment_id, 1.0, manual=True, seen_id=cards[index].seen_id)
        self._offer = Offer(self._offer.sequence, tuple(cards))
        self._pending.pop(index, None)
        return True

    def reset(self) -> None:
        self._offer = None
        self._seen = self._missing = 0
        self._pending.clear()
