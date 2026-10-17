"""One match's augment offers: catalog, icons and statistics loaded once, readings in, cards out.

Everything is loaded from the League client except the statistics:

- ``/lol-game-data/assets/v1/cherry-augments.json`` and ``augment-lists.json``
  (the game-data files CommunityDragon mirrors under ``global/{locale}/v1``);
- each augment's icon from its ``augmentSmallIconPath`` on the same client;
- ARAM Mayhem statistics from ARAMKit, Arena statistics from LoLalytics.

The client paths and the queue ids below are the community-documented ones and
still need checking in a real client and match.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Callable

from PIL import Image

from sexo2.augments.catalog import Catalog, build_catalog
from sexo2.augments.offers import OfferTracker
from sexo2.augments.stats import (
    AugmentStat,
    aramkit_champion_url,
    aramkit_data_path,
    parse_aramkit_champion,
    parse_lolalytics_arena,
)
from sexo2.augments.view import CardView, card_views
from sexo2.augments.vision import IconMatcher

log = logging.getLogger(__name__)

QUEUE_MODES = {1700: "arena", 1710: "arena", 2400: "mayhem"}
CHERRY_AUGMENTS = "/lol-game-data/assets/v1/cherry-augments.json"
AUGMENT_LISTS = "/lol-game-data/assets/v1/augment-lists.json"


def load_catalog(lcu: Any, mode: str) -> Catalog:
    return build_catalog(lcu.get(CHERRY_AUGMENTS, timeout=3.0), lcu.get(AUGMENT_LISTS, timeout=3.0), mode)


def load_templates(lcu: Any, catalog: Catalog) -> dict[int, Image.Image]:
    """Icons of the pool from the client; augments whose icon cannot be read are left out."""
    templates = {}
    for augment in catalog.augments:
        if not augment.icon_path:
            continue
        data = lcu.get_bytes(augment.icon_path)
        if not data:
            continue
        try:
            templates[augment.id] = Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception:
            log.debug("[AUGMENTS] unreadable icon for %s", augment.id)
    return templates


def mayhem_stats(fetch_json: Callable[[str], Any], champion_id: int) -> dict[int, AugmentStat]:
    data_path, version = aramkit_data_path(fetch_json("https://data.aramkit.com/data/versions.json"))
    return parse_aramkit_champion(fetch_json(aramkit_champion_url(data_path, champion_id)), version)


class AugmentSession:
    """The offers of one match for one champion in one mode."""

    def __init__(
        self,
        catalog: Catalog,
        matcher: IconMatcher,
        stats: dict[int, AugmentStat] | Callable[[int], dict[int, AugmentStat]],
    ) -> None:
        self.catalog = catalog
        self.matcher = matcher
        self._stats = stats  # a dict, or per offer number for Arena
        self.tracker = OfferTracker()
        self._last_crops: list[Image.Image] = []

    @property
    def mode(self) -> str:
        return self.catalog.mode

    def stats_for_offer(self, offer_number: int) -> dict[int, AugmentStat]:
        if callable(self._stats):
            try:
                return self._stats(offer_number)
            except Exception:
                log.debug("[AUGMENTS] no statistics for offer %s", offer_number)
                return {}
        return self._stats

    def observe(self, reading, icon_crops: list[Image.Image] | None = None) -> bool:
        if reading and icon_crops:
            self._last_crops = icon_crops
        return self.tracker.observe(reading)

    def correct(self, index: int, augment_id: int) -> bool:
        """The player names a card; its icon is learnt so the next offers read it."""
        if self.catalog.by_id(augment_id) is None or not self.tracker.correct(index, augment_id):
            return False
        if index < len(self._last_crops):
            self.matcher.add(augment_id, self._last_crops[index])
        return True

    def cards(self) -> tuple[CardView, ...]:
        offer = self.tracker.offer
        if offer is None:
            return ()
        return card_views(offer, self.catalog, self.stats_for_offer(offer.sequence))


def arena_stats(lolalytics_client: Any, champion_slug: str) -> Callable[[int], dict[int, AugmentStat]]:
    """Arena statistics by offer number (1 to 5), read once per match."""
    from lolalytics.query import Query

    snapshot = lolalytics_client.collect(Query(champion_slug, mode="arena", tier="all"))
    return lambda offer_number: parse_lolalytics_arena(snapshot, offer_number - 1)
