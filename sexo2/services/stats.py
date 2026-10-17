"""Champion statistics for the assistant, read through :class:`lolalytics.Client`.

Rune numbers are keystone-level: LoLalytics publishes win rate and games for
the layout's keystone, not for the joint nine-perk page. The model says so in
its field names (``keystone_win_rate``, ``games``, ``metric_scope``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lolalytics.builds import BuildPage
from lolalytics.client import Client
from lolalytics.errors import DataUnavailable
from lolalytics.query import Query
from lolalytics.recommendations import rune_candidates
from sexo2.services.rune_rules import PageSpec, StyleCatalog, page_from_layout

# LoLalytics slugs are the client alias lowercased to letters and digits, except
# for the entries below. Pending live validation against every champion; add a
# row when a slug is found to differ instead of special-casing callers.
SLUG_BY_ALIAS = {"MonkeyKing": "wukong"}
SLUG_BY_NAME = {"Nunu & Willump": "nunu", "Renata Glasc": "renata", "Wukong": "wukong"}

# Client assigned positions (champ select ``assignedPosition``) to LoLalytics lanes.
LANE_BY_POSITION = {"top": "top", "jungle": "jungle", "middle": "middle", "bottom": "bottom", "utility": "support"}

CACHE_FOLDER = "lolalytics-cache"


class StatsError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _simplify(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def champion_slug(alias: str | None, name: str | None = None) -> str:
    """LoLalytics slug from the client's champion alias (preferred) or name."""
    if alias and alias in SLUG_BY_ALIAS:
        return SLUG_BY_ALIAS[alias]
    if not alias and name and name in SLUG_BY_NAME:
        return SLUG_BY_NAME[name]
    slug = _simplify(alias or name or "")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", slug):
        raise StatsError("unknown_champion", f"no LoLalytics slug for alias={alias!r} name={name!r}")
    return slug


class ChampionDirectory:
    """Champion id to slug, from ``/lol-game-data/assets/v1/champion-summary.json``."""

    def __init__(self, slugs: dict[int, str], names: dict[int, str] | None = None) -> None:
        self._slugs = dict(slugs)
        self._names = dict(names or {})

    @classmethod
    def from_summary(cls, payload: Any) -> ChampionDirectory:
        if not isinstance(payload, list):
            raise StatsError("schema", "champion summary must be a list")
        slugs = {}
        names = {}
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            champion_id = entry.get("id")
            if isinstance(champion_id, bool) or not isinstance(champion_id, int) or champion_id <= 0:
                continue  # the summary lists id -1 for "None"
            slugs[champion_id] = champion_slug(entry.get("alias"), entry.get("name"))
            if isinstance(entry.get("name"), str) and entry["name"].strip():
                names[champion_id] = entry["name"].strip()
        return cls(slugs, names)

    def name(self, champion_id: int) -> str | None:
        """Display name as the client's summary gives it (localised), if known."""
        return self._names.get(champion_id)

    def slug(self, champion_id: int) -> str:
        try:
            return self._slugs[champion_id]
        except KeyError:
            raise StatsError("unknown_champion", f"champion {champion_id} is not in the summary") from None


@dataclass(frozen=True)
class RuneLayout:
    selection: str  # "win" (highest win rate) or "pick" (most common), as LoLalytics labels them
    keystone: int
    primary: tuple[int, ...]
    secondary: tuple[int, ...]
    stat_mods: tuple[int, ...]
    keystone_win_rate: float | None
    games: int | None
    metric_scope: str = "keystone_observation"

    def to_page(self, catalog: StyleCatalog) -> PageSpec:
        return page_from_layout(catalog, self.primary, self.secondary, self.stat_mods)


@dataclass(frozen=True)
class RuneStats:
    champion: str
    mode: str
    lane: str
    patch: str | None
    source_url: str
    collected_at: str
    cache_hit: bool
    layouts: tuple[RuneLayout, ...]
    opponent: str | None = None
    matchup: tuple[RuneLayout, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuildStats:
    pages: tuple[BuildPage, ...]
    warnings: tuple[str, ...] = ()


def _layouts(snapshot: Any) -> tuple[RuneLayout, ...]:
    result = []
    for candidate in rune_candidates(snapshot):
        runes, metrics = candidate["runes"], candidate["metrics"]
        result.append(
            RuneLayout(
                selection=candidate["selection"],
                keystone=candidate["keystone"],
                primary=tuple(int(perk) for perk in runes["pri"]),
                secondary=tuple(int(perk) for perk in runes["sec"]),
                stat_mods=tuple(int(perk) for perk in runes["mod"]),
                keystone_win_rate=metrics.get("win_rate"),
                games=metrics.get("games"),
                metric_scope=candidate["metric_scope"],
            )
        )
    return tuple(result)


class StatsService:
    """Blocking network calls; run from a worker thread."""

    def __init__(
        self,
        champions: ChampionDirectory,
        *,
        client: Client | None = None,
        cache_dir: Path | None = None,
        tier: str = "emerald_plus",
        region: str = "all",
    ) -> None:
        if client is None:
            if cache_dir is None:
                from utils.core.paths import get_user_data_dir

                cache_dir = get_user_data_dir() / CACHE_FOLDER
            client = Client(cache_dir=cache_dir)  # TTL: the LoLalytics client default
        self._client = client
        self._champions = champions
        self._tier = tier
        self._region = region

    def _query(self, champion_id: int, mode: str, lane: str, **extra: Any) -> Query:
        lane = lane if mode == "ranked" else "all"
        tier = self._tier if mode == "ranked" else "emerald_plus"
        region = self._region if mode == "ranked" and "opponent" not in extra else "all"
        return Query(self._champions.slug(champion_id), mode=mode, lane=lane, tier=tier, region=region, **extra)

    def _opponent_query(self, champion_id: int, lane: str, opponent_id: int) -> Query:
        opponent = self._champions.slug(opponent_id)
        return self._query(champion_id, "ranked", lane, opponent=opponent, opponent_lane=lane)

    def runes(
        self, champion_id: int, mode: str = "ranked", lane: str = "all", opponent_id: int | None = None
    ) -> RuneStats:
        """The two LoLalytics layouts (win and pick) and, in ranked, those against an opponent."""
        if mode not in ("ranked", "aram", "swift"):
            raise StatsError("unsupported_mode", f"rune statistics are not available for {mode}")
        query = self._query(champion_id, mode, lane)
        snapshot = self._client.collect(query)
        warnings = ["keystone_level_metrics"]
        matchup: tuple[RuneLayout, ...] = ()
        opponent = None
        if opponent_id is not None:
            if mode != "ranked":
                warnings.append("matchup_ranked_only")
            else:
                opponent_query = self._opponent_query(champion_id, lane, opponent_id)
                opponent = opponent_query.opponent
                try:
                    matchup = _layouts(self._client.collect(opponent_query))
                except DataUnavailable:
                    warnings.append("matchup_unavailable")
        return RuneStats(
            champion=query.champion,
            mode=mode,
            lane=snapshot.resolved.get("effective_lane") or query.lane,
            patch=snapshot.resolved.get("patch"),
            source_url=snapshot.source_url,
            collected_at=snapshot.collected_at,
            cache_hit=bool(snapshot.cache_hit),
            layouts=_layouts(snapshot),
            opponent=opponent,
            matchup=matchup,
            warnings=tuple(warnings),
        )

    def builds(
        self, champion_id: int, mode: str = "ranked", lane: str = "all", opponent_id: int | None = None
    ) -> BuildStats:
        """Keystone-conditioned win and pick builds, plus the opponent build in ranked."""
        pages = list(self._client.collect_builds(self._query(champion_id, mode, lane)).pages)
        warnings = []
        if opponent_id is not None:
            if mode != "ranked":
                warnings.append("matchup_ranked_only")
            else:
                try:
                    pages.append(self._client.collect_matchup(self._opponent_query(champion_id, lane, opponent_id)))
                except DataUnavailable:
                    warnings.append("matchup_unavailable")
        return BuildStats(pages=tuple(pages), warnings=tuple(warnings))
