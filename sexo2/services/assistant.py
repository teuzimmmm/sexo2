"""Champion-select assistant: statistics, rune page import and item set import for the local player.

The plugin asks (bridge messages ``assistant-*``); this service reads the champion-select
session from the client, fetches LoLalytics statistics, and drives the rune import
controller and the item set import. State changes are published as ``assistant-state``.
All client and network calls run on one serial worker, never on the bridge loop.

The item set is imported automatically when the local player's champion is
confirmed (lock, trade or Swiftplay choice), without the panel being open:
:meth:`AssistantService.champion_confirmed` is called by the champion lock
handlers. Calls are debounced and the latest confirmation wins; a write is
skipped when the same session, champion and opponent were already confirmed.

A build pinned for the champion (D-135, kept apart for SR and ARAM) is applied on
that confirmation: its rune page is imported and its item trio heads the set. One
that no longer fits (the patch changed a rune, the trio left the statistics) is
not applied; the state says so and the default stays. Without a favourite the
highest win rate rune page is imported (D-136), unless the player chose one already.
In Swiftplay the page goes into each champion's lobby slot, once per champion and
lobby, so a page the player sets afterwards stays (D-137).
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, replace
from typing import Any, Callable

from lcu.features.lcu_item_sets import LCUItemSets
from lcu.features.lcu_perks import LCUPerks
from lolalytics.errors import QueryError
from lolalytics.item_pages import format_games, format_rate
from sexo2.services.favorite_builds import FavoriteBuilds, group_for
from sexo2.services.item_sets import build_item_set, import_item_set
from sexo2.services.rune_import import RuneImportController, RuneImportSnapshot, SessionKey
from sexo2.services.rune_rules import PageSpec, StyleCatalog, validate_page
from sexo2.services.stats import Alternatives, ChampionDirectory, ItemCombo, RuneLayout, StatsError, StatsService
from sexo2.services.work_queue import SerialWorker

log = logging.getLogger(__name__)

# Queues whose statistics exist on LoLalytics. Normal draft, quickplay, the
# other summoner's rift queues and the Practice Tool (3140, to test the assistant
# without a full match) use ranked data; anything else is unsupported.
QUEUE_MODES = {
    400: "ranked",
    420: "ranked",
    430: "ranked",
    440: "ranked",
    490: "ranked",
    3140: "ranked",
    480: "swift",
    450: "aram",
}
POSITION_LANES = {"top": "top", "jungle": "jungle", "middle": "middle", "bottom": "bottom", "utility": "support"}

# Ranked queues read from the client, in order of preference, and the per-side
# cap of players read in one champion select (D-140).
RANKED_QUEUES = ("RANKED_SOLO_5x5", "RANKED_FLEX_SR")
RANKED_LIMIT = 5
RANKED_TIMEOUT_S = 0.5
POSITION_ORDER = {"top": 0, "jungle": 1, "middle": 2, "bottom": 3, "support": 4}
_MISSING = object()


@dataclass(frozen=True)
class RankedEntry:
    queue: str
    tier: str
    division: str | None
    league_points: int | None

    def json(self) -> dict:
        return {
            "queue": self.queue,
            "tier": self.tier,
            "division": self.division,
            "leaguePoints": self.league_points,
        }


@dataclass(frozen=True)
class ChampSelectContext:
    session_id: str
    champion_id: int
    lane: str
    mode: str | None
    enemies: tuple[int, ...]
    can_edit: bool
    locked: bool = False


def read_context(session: Any, queue_id: int | None) -> ChampSelectContext | None:
    """The local player's champion-select context, or None outside a usable session."""
    if not isinstance(session, dict):
        return None
    local = session.get("localPlayerCellId")
    me = next((p for p in session.get("myTeam") or [] if isinstance(p, dict) and p.get("cellId") == local), None)
    if me is None:
        return None
    locked = me.get("championId") or 0
    champion = locked or me.get("championPickIntent") or 0
    if not isinstance(champion, int) or isinstance(champion, bool) or champion <= 0:
        return None
    session_id = str(session.get("id") or session.get("gameId") or "")
    if not session_id:
        return None
    phase = (session.get("timer") or {}).get("phase")
    enemies = tuple(
        p["championId"]
        for p in session.get("theirTeam") or []
        if isinstance(p, dict) and isinstance(p.get("championId"), int) and p["championId"] > 0
    )
    return ChampSelectContext(
        session_id=session_id,
        champion_id=champion,
        lane=POSITION_LANES.get(str(me.get("assignedPosition") or "").lower(), "all"),
        mode=QUEUE_MODES.get(queue_id) if isinstance(queue_id, int) else None,
        enemies=enemies,
        can_edit=phase != "GAME_STARTING",
        locked=isinstance(locked, int) and not isinstance(locked, bool) and locked > 0,
    )


def read_ranked_entry(payload: Any) -> RankedEntry | None:
    """Solo/duo first, flex second, from the client's ``queueMap``/``queues``.

    The real response carries both shapes; either is enough. Missing tier means
    the player has no rank in that queue.
    """
    if not isinstance(payload, dict):
        return None
    by_queue: dict[str, dict] = {}
    queue_map = payload.get("queueMap")
    if isinstance(queue_map, dict):
        for name, entry in queue_map.items():
            if isinstance(name, str) and isinstance(entry, dict):
                by_queue[name.upper()] = entry
    queues = payload.get("queues")
    if isinstance(queues, list):
        for entry in queues:
            if not isinstance(entry, dict):
                continue
            name = entry.get("queueType")
            if isinstance(name, str):
                by_queue.setdefault(name.upper(), entry)
    for queue in RANKED_QUEUES:
        entry = by_queue.get(queue.upper())
        if entry is None:
            continue
        tier = entry.get("tier")
        if not isinstance(tier, str) or tier.strip().upper() in ("", "NONE", "UNRANKED"):
            continue
        division = entry.get("division")
        division = division.strip().upper() if isinstance(division, str) else ""
        if division in ("", "NA", "NONE"):
            division = None
        points = entry.get("leaguePoints")
        if isinstance(points, bool) or not isinstance(points, int):
            points = None
        return RankedEntry(queue, tier.strip().upper(), division, points)
    return None


def champion_id(player: dict, allow_intent: bool) -> int:
    for key in ("championId", "championPickIntent") if allow_intent else ("championId",):
        value = player.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
    return 0


def layout_json(layout: RuneLayout, page: PageSpec) -> dict:
    return {
        "selection": layout.selection,
        "keystoneWinRate": layout.keystone_win_rate,
        "games": layout.games,
        "page": page_json(page),
    }


def page_json(page: PageSpec | None) -> dict | None:
    if page is None:
        return None
    return {"primary": page.primary_style_id, "sub": page.sub_style_id, "perks": list(page.perk_ids)}


SWIFT_SLOTS_PATH = "/lol-lobby/v1/lobby/members/localMember/player-slots"
# The session id of the context built for a Swiftplay lobby champion (there is no champion select).
SWIFT_SESSION = "swiftplay"
SWIFT_PERK_KEYS = frozenset(("perkIds", "perkStyle", "perkSubStyle"))


def swift_perks(raw: Any, page: PageSpec) -> Any:
    """The slot's ``perks`` value with this page, in the format the client gave it (a JSON
    string or an object), or None when that format is not the known one."""
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return None
    if not isinstance(parsed, dict) or not SWIFT_PERK_KEYS <= parsed.keys():
        return None
    value = {
        **parsed,
        "perkIds": list(page.perk_ids),
        "perkStyle": page.primary_style_id,
        "perkSubStyle": page.sub_style_id,
    }
    return json.dumps(value, separators=(",", ":")) if isinstance(raw, str) else value


def slot_page(raw: Any) -> PageSpec | None:
    """The rune page a Swiftplay slot holds (its ``perks`` value, a JSON string or an object)."""
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return None
    if not isinstance(parsed, dict) or not SWIFT_PERK_KEYS <= parsed.keys():
        return None
    values = [
        parsed["perkStyle"],
        parsed["perkSubStyle"],
        *(parsed["perkIds"] if isinstance(parsed["perkIds"], list) else [None]),
    ]
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        return None
    return PageSpec(parsed["perkStyle"], parsed["perkSubStyle"], tuple(parsed["perkIds"]))


def favorite_lane(context: ChampSelectContext) -> str:
    """The lane a favourite belongs to: the chosen lane in Summoner's Rift modes (D-148),
    ``all`` (no lane) in ARAM and Swiftplay and while the lane is not known."""
    return context.lane if context.mode == "ranked" and context.lane in POSITION_LANES.values() else "all"


def page_from_json(payload: Any) -> PageSpec:
    if not isinstance(payload, dict):
        raise ValueError("page must be an object")
    perks = payload.get("perks")
    values = [payload.get("primary"), payload.get("sub"), *(perks if isinstance(perks, list) else [None])]
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("page ids must be integers")
    return PageSpec(payload["primary"], payload["sub"], tuple(perks))


class AssistantService:
    def __init__(
        self,
        lcu: Any,
        publish: Callable[[dict], None],
        *,
        queue_id: Callable[[], int | None],
        in_champ_select: Callable[[], bool],
        stats_factory: Callable[[ChampionDirectory], StatsService] = StatsService,
        worker: SerialWorker | None = None,
        controller: RuneImportController | None = None,
        schedule: Callable[[float, Callable[[], None]], None] | None = None,
        auto_delay: float = 0.5,
        favorites: FavoriteBuilds | None = None,
    ) -> None:
        self._lcu = lcu
        self._publish = publish
        self._queue_id = queue_id
        self._in_champ_select = in_champ_select
        self._stats_factory = stats_factory
        self._worker = worker if worker is not None else SerialWorker("SEXO2-Assistant", capacity=16)
        self._context: ChampSelectContext | None = None
        self._controller = controller or RuneImportController(
            LCUPerks(lcu), can_edit=self._can_edit, on_change=self._on_runes
        )
        self._stats: StatsService | None = None
        self._catalog: StyleCatalog | None = None
        self._opponent: int | None = None
        self._lane: tuple[str, str] | None = None  # (session id, lane) chosen in the panel
        self._runes: dict = {}
        self._items: dict = {}
        self._error: str | None = None
        self._last_rune_sequence = -1
        self._directory: ChampionDirectory | None = None
        self._schedule = schedule or _timer
        self._auto_delay = auto_delay
        self._auto_lock = threading.Lock()
        self._auto_generation = 0
        self._auto_target: tuple[int, bool] | None = None
        self._items_key: tuple | None = None
        self._alternatives: Alternatives | None = None
        self._chosen_build: ItemCombo | None = None  # the player's own pick in "Outras builds"
        self._keystone_pending: int | None = None
        self._alternatives_key: tuple | None = None
        self._favorites = favorites if favorites is not None else FavoriteBuilds()
        self._favorite_key: tuple | None = None  # (session, champion) the favourite was applied to
        self._favorite_wanted: tuple[int, ...] | None = None  # trio to put first in the next set
        self._favorite_unavailable: set[str] = set()  # "runes"/"items" pinned but not applicable
        self._swift_runes_done: set[tuple] = set()  # (lobby, champion) whose Swiftplay slot was filled
        self._swift_context: ChampSelectContext | None = None  # the lobby champion opened in the Hub
        self._swift_runes: dict = {"chosen": None, "applied": None, "pending": False, "error": None}
        self._ranked_team: list[dict] = []
        self._ranked_enemies: list[dict] = []
        self._ranked_session: str | None = None
        self._ranked_cache: dict[str, RankedEntry | None] = {}
        self._ranked_seen: dict[str, set[str]] = {"team": set(), "enemies": set()}

    # Bridge entry points (return quickly; work goes to the worker) ----------

    def handle(self, payload: dict) -> None:
        kind = payload.get("type")
        if kind == "assistant-request":
            self._submit(self._refresh)
        elif kind == "assistant-ranked":
            self._submit(self._refresh_ranked)
        elif kind == "assistant-opponent":
            opponent = payload.get("championId")
            self._opponent = opponent if isinstance(opponent, int) and opponent > 0 else None
            self._submit(self._refresh)
            target = self._auto_target
            if target is not None:
                self.champion_confirmed(target[0], swiftplay=target[1])
        elif kind == "assistant-lane":
            lane = payload.get("lane")
            if lane not in POSITION_LANES.values():
                raise ValueError("unknown lane")
            context = self._context
            self._lane = (context.session_id, lane) if context else None
            self._submit(self._refresh)
        elif kind == "assistant-swiftplay-open":
            champion = payload.get("championId")
            if isinstance(champion, bool) or not isinstance(champion, int) or champion <= 0:
                raise ValueError("championId must be a positive integer")
            self._submit(lambda: self._swift_open(champion))
        elif kind == "assistant-swiftplay-close":
            self._submit(self._swift_close)
        elif kind == "assistant-runes-choose":
            self._choose(str(payload.get("selection") or ""), bool(payload.get("matchup")))
        elif kind == "assistant-runes-edit":
            page = page_from_json(payload.get("page"))
            if self._is_swift():
                self._submit(lambda: self._swift_apply(page))
            else:
                self._controller.edit(page)
        elif kind == "assistant-runes-confirm":
            if self._is_swift():
                self._submit(self._publish_state)  # a Swiftplay page is written as it is chosen
            else:
                self._controller.confirm()
        elif kind == "assistant-runes-back":
            if self._is_swift():
                self._submit(self._publish_state)
            else:
                self._controller.back()
        elif kind == "assistant-items-import":
            self._submit(self._import_items)
        elif kind == "assistant-items-choose":
            items = payload.get("items")
            if not isinstance(items, list) or not 1 <= len(items) <= 6:
                raise ValueError("items must be a list of one to six item ids")
            if any(isinstance(i, bool) or not isinstance(i, int) or i <= 0 for i in items):
                raise ValueError("item ids must be positive integers")
            self._submit(lambda: self._choose_build(tuple(items)))
        elif kind == "assistant-items-default":
            self._submit(self._default_build)
        elif kind == "assistant-runes-keystone":
            keystone = payload.get("keystone")
            if isinstance(keystone, bool) or not isinstance(keystone, int) or keystone <= 0:
                raise ValueError("keystone must be a positive integer")
            self._keystone_pending = keystone
            self._publish_state()
            self._submit(lambda: self._load_keystone(keystone))
        elif kind == "assistant-favorite":
            what, action = payload.get("what"), payload.get("action")
            if what not in ("runes", "items") or action not in ("pin", "unpin", "apply"):
                raise ValueError("unknown favourite request")
            self._submit(lambda: self._favorite(what, action))

    def champion_confirmed(self, champion_id: int, *, swiftplay: bool = False) -> None:
        """The local player's champion is confirmed: import its item set (debounced).

        Safe to call from any thread; returns at once.
        """
        if isinstance(champion_id, bool) or not isinstance(champion_id, int) or champion_id <= 0:
            return
        with self._auto_lock:
            self._auto_generation += 1
            generation = self._auto_generation
            self._auto_target = (champion_id, swiftplay)

        def fire() -> None:
            if generation == self._auto_generation:
                self._submit(lambda: self._auto_import(generation, champion_id, swiftplay))

        self._schedule(self._auto_delay, fire)

    def _submit(self, work: Callable[[], None]) -> None:
        def failed(error: BaseException) -> None:
            log.error("[ASSISTANT] work failed: %s", error)
            self._error = "unexpected"
            self._publish_state()

        if not self._worker.submit(work, failed):
            self._error = "busy"
            self._publish_state()

    # Worker ------------------------------------------------------------------

    def _can_edit(self) -> bool:
        context = self._context
        return bool(context and context.can_edit and self._in_champ_select())

    def _read_session(self) -> Any:
        return self._lcu.get("/lol-champ-select/v1/session")

    def _read_context(self, session: Any = _MISSING) -> ChampSelectContext | None:
        if session is _MISSING:
            session = self._read_session()
        context = read_context(session, self._queue_id())
        if context is not None and self._lane is not None and self._lane[0] == context.session_id:
            context = replace(context, lane=self._lane[1])
        return context

    def _ensure_stats(self) -> StatsService:
        if self._stats is None:
            self._directory = ChampionDirectory.from_summary(
                self._lcu.get("/lol-game-data/assets/v1/champion-summary.json")
            )
            self._stats = self._stats_factory(self._directory)
        return self._stats

    def _refresh_ranked(self) -> None:
        """Refresh only the team ranks, without touching runes or builds."""
        self._load_ranked(self._read_session())
        self._publish_state()

    def _clear_ranked(self) -> None:
        self._ranked_team = []
        self._ranked_enemies = []
        self._ranked_session = None
        self._ranked_cache = {}
        self._ranked_seen = {"team": set(), "enemies": set()}

    def _load_ranked(self, session: Any) -> None:
        if not isinstance(session, dict):
            self._clear_ranked()
            return
        session_id = str(session.get("id") or session.get("gameId") or "")
        if session_id != self._ranked_session:
            self._ranked_session = session_id
            self._ranked_cache = {}
            self._ranked_seen = {"team": set(), "enemies": set()}
        self._ranked_team = self._ranked_rows(session.get("myTeam"), "team", allow_intent=True)
        self._ranked_enemies = self._ranked_rows(
            session.get("theirTeam"), "enemies", allow_intent=False, require_puuid=True
        )

    def _ranked_rows(self, players: Any, side: str, *, allow_intent: bool, require_puuid: bool = False) -> list[dict]:
        rows = []
        for player in players or []:
            if not isinstance(player, dict):
                continue
            puuid = player.get("puuid")
            puuid = puuid.strip() if isinstance(puuid, str) else ""
            if require_puuid and not puuid:
                continue  # the client did not reveal this enemy: never infer it
            entry = self._ranked_entry(puuid, side) if puuid else None
            position = POSITION_LANES.get(str(player.get("assignedPosition") or "").lower(), "")
            rows.append(
                {
                    "cellId": player.get("cellId"),
                    "position": position,
                    "championId": champion_id(player, allow_intent),
                    "elo": entry.json() if entry is not None else None,
                }
            )
        rows.sort(key=lambda row: POSITION_ORDER.get(row["position"], len(POSITION_ORDER)))
        return rows

    def _ranked_entry(self, puuid: str, side: str) -> RankedEntry | None:
        if puuid in self._ranked_cache:
            return self._ranked_cache[puuid]
        seen = self._ranked_seen[side]
        if len(seen) >= RANKED_LIMIT:
            return None  # per-selection cap (D-140)
        seen.add(puuid)
        try:
            payload = self._lcu.ranked_stats(puuid, timeout=RANKED_TIMEOUT_S)
        except Exception as error:
            log.info("[ASSISTANT] ranked stats unavailable: %s", error)
            payload = None
        entry = read_ranked_entry(payload)
        self._ranked_cache[puuid] = entry
        return entry

    def _refresh(self) -> None:
        session = self._read_session()
        context = self._read_context(session)
        if context is None and self._swift_context is not None:
            context = self._swift_context  # Swiftplay lobby: no champion select, the opened champion
        self._context = context
        # The team's ranks do not depend on the local player having a champion.
        self._load_ranked(session)
        if context is None:
            self._controller.set_session(None)
            self._runes, self._error = {}, None
            self._publish_state()
            return
        if self._catalog is None:
            self._catalog = StyleCatalog.from_payload(self._lcu.get("/lol-perks/v1/styles"))
            self._controller.set_catalog(self._catalog)
        self._ensure_stats()
        # A Swiftplay page goes into the lobby slot, not into a live rune page: no controller
        self._controller.set_session(
            None if context.session_id == SWIFT_SESSION else SessionKey(context.session_id, context.champion_id)
        )
        self._error = None
        if context.mode is None:
            self._runes = {}
            self._error = "unsupported_mode"
            self._publish_state()
            return
        try:
            stats = self._stats.runes(context.champion_id, context.mode, context.lane, opponent_id=self._opponent)
        except StatsError as error:
            self._runes, self._error = {}, f"stats_{error.code}"
            self._publish_state()
            return
        except Exception:
            log.exception("[ASSISTANT] statistics unavailable")
            self._runes, self._error = {}, "stats_unavailable"
            self._publish_state()
            return
        general = [(layout, layout.to_page(self._catalog)) for layout in stats.layouts]
        self._alternatives_key = None  # reloaded below
        matchup = [(layout, layout.to_page(self._catalog)) for layout in stats.matchup]
        keystone = self._runes.get("keystone", []) if self._runes.get("champion") == context.champion_id else []
        self._runes = {
            "champion": context.champion_id,
            "patch": stats.patch,
            "lane": stats.lane,
            "opponent": stats.opponent,
            "general": general,
            "matchup": matchup,
            "keystone": keystone,
            "warnings": list(stats.warnings),
        }
        try:
            self._alternatives = self._fetch_alternatives(context)
            self._alternatives_key = (context.champion_id, context.mode, context.lane)
        except Exception as error:
            log.info("[ASSISTANT] no alternatives for champion %s: %s", context.champion_id, error)
            self._alternatives = None
        if context.session_id != SWIFT_SESSION:
            self._controller.display([page for _, page in general + matchup + keystone])
        self._publish_state()

    def _keystone_ids(self) -> frozenset[int]:
        """Keystones: the first slot of every rune tree."""
        return self._keystone_ids_of(self._catalog)

    @staticmethod
    def _keystone_ids_of(catalog: StyleCatalog) -> frozenset[int]:
        return frozenset(
            perk
            for style in catalog.styles
            if style.slots and style.slots[0].kind != "kStatMod"
            for perk in style.slots[0].perks
        )

    def _load_keystone(self, keystone: int) -> None:
        """Fetch the most played page with this keystone for "Outras runas"."""
        context = self._context
        try:
            if context is None or context.mode is None or self._catalog is None:
                raise StatsError("no_session", "no champion select")
            layout = self._ensure_stats().keystone_layout(context.champion_id, context.mode, context.lane, keystone)
            page = layout.to_page(self._catalog)
        except Exception as error:
            log.info("[ASSISTANT] no page with keystone %s: %s", keystone, error)
            if self._keystone_pending == keystone:
                self._keystone_pending = None
                self._error = "keystone_unavailable"
                self._publish_state()
            return
        if self._keystone_pending != keystone:
            return  # the player asked for another keystone meanwhile
        self._keystone_pending = None
        self._error = None
        self._runes["keystone"] = [(layout, page)]
        displayed = [page for _, page in self._runes.get("general", []) + self._runes.get("matchup", [])]
        if not self._is_swift():
            self._controller.display([*displayed, page])
        self._publish_state()

    def _choose(self, selection: str, matchup: bool) -> None:
        group = "matchup" if matchup else "keystone" if selection == "keystone" else "general"
        candidates = self._runes.get(group) or []
        page = next((page for layout, page in candidates if layout.selection == selection), None)
        if page is None:
            self._error = "unknown_recommendation"
            self._publish_state()
            return
        if self._is_swift():
            self._submit(lambda: self._swift_apply(page))
            return
        self._controller.choose(page)

    def _auto_import(self, generation: int, champion_id: int, swiftplay: bool) -> None:
        if generation != self._auto_generation:
            return  # a newer confirmation is queued
        if swiftplay:
            queue_id = self._queue_id()
            context = ChampSelectContext(
                session_id="swiftplay",
                champion_id=champion_id,
                lane="all",
                mode=QUEUE_MODES.get(queue_id) if isinstance(queue_id, int) else None,
                enemies=(),
                can_edit=True,
                locked=True,
            )
        else:
            context = self._read_context()
            if context is None or not context.locked or context.champion_id != champion_id:
                return  # provisional pick, another player's champion, or the session is gone
            self._context = context
        if context.mode is None:
            self._items = {"error": "unsupported_mode"}
            self._publish_state()
            return
        if swiftplay:
            self._apply_swiftplay_runes(context.mode)
        if (context.session_id, champion_id) != self._favorite_key:
            # First confirmation of this champion here: its pinned build, if any. Later ones
            # (opponent changed) keep what the player picked meanwhile.
            self._favorite_key = (context.session_id, champion_id)
            self._favorite_unavailable = set()
            group = group_for(context.mode)
            lane = favorite_lane(context)
            favorite = self._favorites.get(group, champion_id, lane) if group else {"runes": None, "items": None}
            if not swiftplay:  # Swiftplay runes are set outside champion select
                if favorite["runes"]:
                    self._apply_favorite_runes(context, favorite["runes"])
                if not favorite["runes"] or "runes" in self._favorite_unavailable:
                    self._apply_default_runes(context)
            self._favorite_wanted = tuple(favorite["items"]) if favorite["items"] else None
        key = (context.session_id, champion_id, self._opponent)
        if key == self._items_key:
            return  # this champion's set is already confirmed
        self._write_items(context, generation)

    def _ensure_catalog(self) -> StyleCatalog:
        if self._catalog is None:
            self._catalog = StyleCatalog.from_payload(self._lcu.get("/lol-perks/v1/styles"))
            self._controller.set_catalog(self._catalog)
        return self._catalog

    def _apply_favorite_runes(self, context: ChampSelectContext, page: dict) -> None:
        if context.session_id == SWIFT_SESSION:
            try:
                error = self._swift_apply(page_from_json(page))
            except ValueError:
                error = "invalid_page"
            if error is not None:
                self._favorite_unavailable.add("runes")
            return
        try:
            self._ensure_catalog()
            self._controller.set_session(SessionKey(context.session_id, context.champion_id))
            snapshot = self._controller.choose(page_from_json(page))
        except Exception as error:
            log.info("[ASSISTANT] favourite rune page not applied: %s", error)
            self._favorite_unavailable.add("runes")
            return
        if snapshot.error == "invalid_page":
            self._favorite_unavailable.add("runes")  # the patch changed a rune of the page

    def _apply_default_runes(self, context: ChampSelectContext) -> None:
        """No favourite (or one that no longer fits): import the highest win rate page (D-136),
        unless the player already chose a page in this champion select."""
        try:
            catalog = self._ensure_catalog()
            self._controller.set_session(SessionKey(context.session_id, context.champion_id))
            snapshot = self._controller.snapshot()
            if snapshot.chosen is not None or snapshot.applied is not None:
                return
            stats = self._ensure_stats().runes(
                context.champion_id, context.mode, context.lane, opponent_id=self._opponent
            )
            layout = next((layout for layout in stats.layouts if layout.selection == "win"), None)
            if layout is None:
                return
            self._controller.choose(layout.to_page(catalog))
        except Exception as error:
            log.info("[ASSISTANT] no automatic rune page for champion %s: %s", context.champion_id, error)

    def _swift_page(self, champion_id: int, mode: str, catalog: StyleCatalog) -> PageSpec | None:
        """The favourite page if it still fits, else the highest win rate page."""
        favorite = self._favorites.get(group_for(mode) or "sr", champion_id)["runes"]
        if favorite:
            try:
                page = page_from_json(favorite)
                if not validate_page(page, catalog):
                    return page
            except ValueError:
                pass
        stats = self._ensure_stats().runes(champion_id, mode, "all")
        layout = next((layout for layout in stats.layouts if layout.selection == "win"), None)
        return layout.to_page(catalog) if layout else None

    def _apply_swiftplay_runes(self, mode: str | None) -> None:
        """Fill each Swiftplay slot's rune page once per champion and lobby (D-137)."""
        if mode is None:
            return
        try:
            lobby = self._lcu.get("/lol-lobby/v2/lobby")
            slots = ((lobby or {}).get("localMember") or {}).get("playerSlots")
            if not isinstance(slots, list):
                return
            lobby_id = str((lobby or {}).get("partyId") or "")
            catalog = self._ensure_catalog()
            changed = False
            for slot in slots:
                champion = slot.get("championId") if isinstance(slot, dict) else None
                if isinstance(champion, bool) or not isinstance(champion, int) or champion <= 0:
                    continue
                if (lobby_id, champion) in self._swift_runes_done:
                    continue  # filled once: a page the player set since stays
                self._swift_runes_done.add((lobby_id, champion))
                page = self._swift_page(champion, mode, catalog)
                value = swift_perks(slot.get("perks"), page) if page else None
                if value is None:
                    log.info("[ASSISTANT] Swiftplay slot runes left as they are: %r", slot.get("perks"))
                    continue
                slot["perks"] = value
                changed = True
            if changed:
                response = self._lcu.put(SWIFT_SLOTS_PATH, slots, 10, headers={"x-riot-source": "rcp-fe-lol-parties"})
                status = getattr(response, "status_code", None)
                if status not in (200, 201, 204):
                    log.warning("[ASSISTANT] Swiftplay rune pages refused: %s", status)
        except Exception as error:
            log.info("[ASSISTANT] no Swiftplay rune pages: %s", error)

    def _fetch_alternatives(self, context: ChampSelectContext) -> Alternatives:
        """Other builds and keystones (Solo/Duo data in every mode: the stats service decides, D-147)."""
        keystones = self._keystone_ids_of(self._ensure_catalog())
        return self._ensure_stats().alternatives(context.champion_id, context.mode, context.lane, keystones)

    def _ensure_alternatives(self, context: ChampSelectContext) -> Alternatives | None:
        key = (context.champion_id, context.mode, context.lane)
        if self._alternatives_key != key:
            try:
                self._alternatives = self._fetch_alternatives(context)
                self._alternatives_key = key
            except Exception as error:
                log.info("[ASSISTANT] no alternatives for champion %s: %s", context.champion_id, error)
                self._alternatives = None
        return self._alternatives

    def _top_trio(self) -> tuple[int, ...] | None:
        """The first three items of the set's first block: the build on top of the set."""
        blocks = self._items.get("blocks") or []
        try:
            trio = tuple(int(item["id"]) for item in blocks[0]["items"][:3])
        except (IndexError, KeyError, TypeError, ValueError):
            return None
        return trio or None

    def _favorite(self, what: str, action: str) -> None:
        """Pin, unpin or (runes) apply the champion's favourite build."""
        context = self._context
        group = group_for(context.mode) if context else None
        if group is None:
            self._error = "no_session"
            self._publish_state()
            return
        champion = context.champion_id
        lane = favorite_lane(context)
        if action == "pin" and context.mode == "ranked" and lane == "all":
            self._error = "no_lane"  # a favourite belongs to one lane (D-148): choose it first
            self._publish_state()
            return
        if what == "runes" and action == "apply":
            page = self._favorites.get(group, champion, lane)["runes"]
            if page:
                self._apply_favorite_runes(context, page)
            self._publish_state()
            return
        if what == "runes":
            applied = self._applied_page() if action == "pin" else None
            if action == "pin" and applied is None:
                self._error = "nothing_applied"
                self._publish_state()
                return
            self._favorites.set_runes(group, champion, page_json(applied), lane)
        else:
            trio = self._top_trio() if action == "pin" else None
            if action == "pin" and trio is None:
                self._error = "nothing_applied"
                self._publish_state()
                return
            self._favorites.set_items(group, champion, list(trio) if trio else None, lane)
        self._favorite_unavailable.discard(what)
        self._error = None
        self._publish_state()

    def _import_items(self) -> None:
        """Import on request from the panel (same set as the automatic import)."""
        context = self._context
        if context is None or context.mode is None:
            self._items = {"error": "no_session"}
            self._publish_state()
            return
        self._write_items(context, None)

    def _choose_build(self, items: tuple[int, ...]) -> None:
        """The player picked a build in "Outras builds": it heads the SEXO2 set."""
        alternatives = self._alternatives
        combo = next((c for c in alternatives.builds if c.items == items), None) if alternatives else None
        if combo is None:
            self._items = {**self._items, "error": "unknown_build"}
            self._publish_state()
            return
        self._chosen_build = combo
        self._import_items()

    def _default_build(self) -> None:
        self._chosen_build = None
        self._import_items()

    def _write_items(self, context: ChampSelectContext, generation: int | None) -> None:
        self._items = {"pending": True, "championId": context.champion_id}
        self._publish_state()
        try:
            stats = self._ensure_stats()
            builds = stats.builds(context.champion_id, context.mode, context.lane, opponent_id=self._opponent)
        except StatsError as error:
            self._items = {"error": f"stats_{error.code}"}
            self._publish_state()
            return
        except Exception:
            log.exception("[ASSISTANT] build statistics unavailable")
            self._items = {"error": "stats_unavailable"}
            self._publish_state()
            return
        if generation is not None and generation != self._auto_generation:
            return  # the champion changed while the statistics loaded
        wanted, self._favorite_wanted = self._favorite_wanted, None
        if wanted is not None:
            alternatives = self._ensure_alternatives(context)
            self._chosen_build = (
                next((c for c in alternatives.builds if c.items == wanted), None) if alternatives else None
            )
        by_selection = {page.selection: page for page in builds.pages}
        try:
            item_set = build_item_set(
                context.champion_id,
                by_selection.get("win"),
                by_selection.get("pick"),
                by_selection.get("vs"),
                champion_name=self._directory.name(context.champion_id) if self._directory else None,
            )
        except (QueryError, ValueError) as error:
            log.info("[ASSISTANT] no item set for champion %s: %s", context.champion_id, error)
            self._items = {"error": "no_builds"}
            self._publish_state()
            return
        chosen = self._chosen_build
        if chosen is not None and self._alternatives is not None and chosen in self._alternatives.builds:
            label = format_games(chosen.games)
            if chosen.win_rate is not None:
                label = f"{format_rate(chosen.win_rate, 1)} — {label}"  # as the other sections (D-018)
            block = {"type": label, "items": [{"id": str(i), "count": 1} for i in chosen.items]}
            item_set = {**item_set, "blocks": [block, *item_set["blocks"]]}
        else:
            chosen = self._chosen_build = None
        if wanted is not None:
            top = tuple(int(i["id"]) for i in item_set["blocks"][0]["items"][:3]) if item_set["blocks"] else ()
            if top != wanted:
                self._favorite_unavailable.add("items")  # the trio left the statistics: default kept
        result = import_item_set(LCUItemSets(self._lcu), item_set)
        if result.confirmed:
            self._items_key = (context.session_id, context.champion_id, self._opponent)
        self._items = {
            "confirmed": result.confirmed,
            "championId": context.champion_id,
            "title": item_set["title"],
            "blocks": item_set["blocks"],
            "chosen": list(chosen.items) if chosen else None,
            "error": result.error,
        }
        self._publish_state()

    # Swiftplay: runes and items of one lobby champion --------------------------------

    def _is_swift(self) -> bool:
        context = self._context
        return bool(context and context.session_id == SWIFT_SESSION)

    def _applied_page(self) -> PageSpec | None:
        return self._swift_runes["applied"] if self._is_swift() else self._controller.snapshot().applied

    def _swift_open(self, champion: int) -> None:
        """The player opened this lobby champion in the Hub: the panel works on it."""
        queue_id = self._queue_id()
        mode = QUEUE_MODES.get(queue_id) if isinstance(queue_id, int) else None
        self._swift_context = ChampSelectContext(
            session_id=SWIFT_SESSION,
            champion_id=champion,
            lane="all",
            mode=mode,
            enemies=(),
            can_edit=True,
            locked=True,
        )
        self._opponent = None
        self._chosen_build = None
        if self._items.get("championId") != champion:
            self._items = {}
        self._swift_runes = {"chosen": None, "applied": self._slot_page(champion), "pending": False, "error": None}
        self._refresh()
        context = self._context
        if context is not None and context.session_id == SWIFT_SESSION and context.mode is not None:
            if not self._items.get("blocks"):
                self._write_items(context, None)  # as at a champion lock: the set is imported at once

    def _swift_close(self) -> None:
        self._swift_context = None
        self._swift_runes = {"chosen": None, "applied": None, "pending": False, "error": None}
        self._refresh()

    def _slot_page(self, champion: int) -> PageSpec | None:
        try:
            slots = ((self._lcu.get("/lol-lobby/v2/lobby") or {}).get("localMember") or {}).get("playerSlots")
            slot = next((s for s in slots or [] if isinstance(s, dict) and s.get("championId") == champion), None)
            return slot_page(slot.get("perks")) if slot else None
        except Exception as error:
            log.info("[ASSISTANT] no Swiftplay slot page: %s", error)
            return None

    def _swift_apply(self, page: PageSpec) -> str | None:
        """Write the page into the champion's lobby slot; returns an error code or None."""
        context = self._context
        if context is None or context.session_id != SWIFT_SESSION:
            return "no_session"
        previous = self._swift_runes["applied"]
        self._swift_runes = {"chosen": page, "applied": previous, "pending": True, "error": None}
        self._publish_state()
        error = self._write_swift_slot(context.champion_id, page)
        self._swift_runes = {
            "chosen": page,
            "applied": page if error is None else previous,
            "pending": False,
            "error": error,
        }
        self._publish_state()
        return error

    def _write_swift_slot(self, champion: int, page: PageSpec) -> str | None:
        try:
            if validate_page(page, self._ensure_catalog()):
                return "invalid_page"
            lobby = self._lcu.get("/lol-lobby/v2/lobby")
            slots = ((lobby or {}).get("localMember") or {}).get("playerSlots")
            slot = next((s for s in slots or [] if isinstance(s, dict) and s.get("championId") == champion), None)
            if slot is None:
                return "no_swiftplay_slot"
            value = swift_perks(slot.get("perks"), page)
            if value is None:
                return "slot_format"
            slot["perks"] = value
            response = self._lcu.put(SWIFT_SLOTS_PATH, slots, 10, headers={"x-riot-source": "rcp-fe-lol-parties"})
            if getattr(response, "status_code", None) not in (200, 201, 204):
                return "slot_refused"
            # What the player picks here is never overwritten by the automatic fill (D-137)
            self._swift_runes_done.add((str((lobby or {}).get("partyId") or ""), champion))
            return None
        except Exception as error:
            log.info("[ASSISTANT] Swiftplay rune page not written: %s", error)
            return "slot_failed"

    # State -------------------------------------------------------------------

    def _on_runes(self, snapshot: RuneImportSnapshot) -> None:
        if snapshot.sequence < self._last_rune_sequence:
            return  # an older snapshot delivered late
        self._last_rune_sequence = snapshot.sequence
        self._publish_state(snapshot)

    def _publish_state(self, snapshot: RuneImportSnapshot | None = None) -> None:
        try:
            self._publish(self.state(snapshot))
        except Exception:
            log.exception("[ASSISTANT] could not publish state")

    def state(self, snapshot: RuneImportSnapshot | None = None) -> dict:
        snapshot = snapshot or self._controller.snapshot()
        context = self._context
        runes = self._runes
        swift = self._is_swift()
        chosen, applied, pending, rune_error = (
            (snapshot.chosen, snapshot.applied, snapshot.pending, snapshot.error)
            if not swift
            else tuple(self._swift_runes[k] for k in ("chosen", "applied", "pending", "error"))
        )
        queue_id = self._queue_id()
        return {
            "type": "assistant-state",
            # False in queues without statistics: the panel then opens the mods directly
            "supported": isinstance(queue_id, int) and queue_id in QUEUE_MODES,
            "swiftplay": swift,
            "championId": context.champion_id if context else None,
            "lane": context.lane if context else None,
            "mode": context.mode if context else None,
            "enemies": list(context.enemies) if context else [],
            "ranked": {"team": self._ranked_team, "enemies": self._ranked_enemies},
            "opponentId": self._opponent,
            "error": self._error,
            "runes": {
                "patch": runes.get("patch"),
                "general": [layout_json(layout, page) for layout, page in runes.get("general", [])],
                "matchup": [layout_json(layout, page) for layout, page in runes.get("matchup", [])],
                "keystone": [layout_json(layout, page) for layout, page in runes.get("keystone", [])],
                "keystonePending": self._keystone_pending,
                "chosen": page_json(chosen),
                "applied": page_json(applied),
                "pending": pending,
                "error": rune_error,
            },
            "items": dict(self._items),
            "options": _options_json(self._alternatives),
            "favorite": self._favorite_state(context),
        }

    def _favorite_state(self, context: ChampSelectContext | None) -> dict:
        group = group_for(context.mode) if context else None
        favorite = (
            self._favorites.get(group, context.champion_id, favorite_lane(context))
            if group
            else {"runes": None, "items": None}
        )
        return {**favorite, "unavailable": sorted(self._favorite_unavailable)}


def _options_json(alternatives: Alternatives | None) -> dict:
    if alternatives is None:
        return {"builds": [], "keystones": []}
    return {
        "builds": [
            {"items": list(c.items), "winRate": c.win_rate, "pickRate": c.pick_rate, "games": c.games}
            for c in alternatives.builds
        ],
        "keystones": [
            {"id": k.keystone, "winRate": k.win_rate, "pickRate": k.pick_rate, "games": k.games}
            for k in alternatives.keystones
        ],
    }


def _timer(delay: float, action: Callable[[], None]) -> None:
    timer = threading.Timer(delay, action)
    timer.daemon = True
    timer.start()
