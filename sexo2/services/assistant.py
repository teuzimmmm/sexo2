"""Champion-select assistant: statistics, rune page import and item set import for the local player.

The plugin asks (bridge messages ``assistant-*``); this service reads the champion-select
session from the client, fetches LoLalytics statistics, and drives the rune import
controller and the item set import. State changes are published as ``assistant-state``.
All client and network calls run on one serial worker, never on the bridge loop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from lcu.features.lcu_item_sets import LCUItemSets
from lcu.features.lcu_perks import LCUPerks
from sexo2.services.item_sets import build_item_sets, import_item_sets
from sexo2.services.rune_import import RuneImportController, RuneImportSnapshot, SessionKey
from sexo2.services.rune_rules import PageSpec, StyleCatalog
from sexo2.services.stats import ChampionDirectory, RuneLayout, StatsError, StatsService
from sexo2.services.work_queue import SerialWorker

log = logging.getLogger(__name__)

# Queues whose statistics exist on LoLalytics. Normal draft, quickplay and the
# other summoner's rift queues use ranked data; anything else is unsupported.
QUEUE_MODES = {400: "ranked", 420: "ranked", 430: "ranked", 440: "ranked", 490: "ranked", 480: "swift", 450: "aram"}
POSITION_LANES = {"top": "top", "jungle": "jungle", "middle": "middle", "bottom": "bottom", "utility": "support"}


@dataclass(frozen=True)
class ChampSelectContext:
    session_id: str
    champion_id: int
    lane: str
    mode: str | None
    enemies: tuple[int, ...]
    can_edit: bool


def read_context(session: Any, queue_id: int | None) -> ChampSelectContext | None:
    """The local player's champion-select context, or None outside a usable session."""
    if not isinstance(session, dict):
        return None
    local = session.get("localPlayerCellId")
    me = next((p for p in session.get("myTeam") or [] if isinstance(p, dict) and p.get("cellId") == local), None)
    if me is None:
        return None
    champion = me.get("championId") or me.get("championPickIntent") or 0
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
    )


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


def builds_json(pages) -> list[dict]:
    """Display model of the build pages: kind and item ids with their own block statistics."""
    return [
        {
            "selection": page.selection,
            "label": page.label,
            "blocks": [
                {
                    "kind": block.kind,
                    "winRate": block.metrics.get("win_rate"),
                    "games": block.metrics.get("games"),
                    "items": [
                        {"id": choice.identifier, "count": choice.count, "winRate": choice.metrics.get("win_rate")}
                        for choice in block.choices
                    ],
                }
                for block in page.blocks
            ],
        }
        for page in pages
    ]


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
        self._runes: dict = {}
        self._items: dict = {}
        self._builds: list | None = None
        self._error: str | None = None
        self._last_rune_sequence = -1

    # Bridge entry points (return quickly; work goes to the worker) ----------

    def handle(self, payload: dict) -> None:
        kind = payload.get("type")
        if kind == "assistant-request":
            self._submit(self._refresh)
        elif kind == "assistant-opponent":
            opponent = payload.get("championId")
            self._opponent = opponent if isinstance(opponent, int) and opponent > 0 else None
            self._builds = None
            self._submit(self._refresh)
        elif kind == "assistant-runes-choose":
            self._choose(str(payload.get("selection") or ""), bool(payload.get("matchup")))
        elif kind == "assistant-runes-edit":
            self._controller.edit(page_from_json(payload.get("page")))
        elif kind == "assistant-runes-confirm":
            self._controller.confirm()
        elif kind == "assistant-runes-back":
            self._controller.back()
        elif kind == "assistant-items-request":
            self._submit(self._fetch_builds)
        elif kind == "assistant-items-import":
            selections = [s for s in payload.get("selections") or [] if isinstance(s, str)]
            self._submit(lambda: self._import_items(selections))

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

    def _refresh(self) -> None:
        context = read_context(self._lcu.get("/lol-champ-select/v1/session"), self._queue_id())
        self._context = context
        if context is None:
            self._controller.set_session(None)
            self._runes, self._items, self._builds, self._error = {}, {}, None, None
            self._publish_state()
            return
        if self._catalog is None:
            self._catalog = StyleCatalog.from_payload(self._lcu.get("/lol-perks/v1/styles"))
            self._controller.set_catalog(self._catalog)
        if self._stats is None:
            directory = ChampionDirectory.from_summary(self._lcu.get("/lol-game-data/assets/v1/champion-summary.json"))
            self._stats = self._stats_factory(directory)
        self._controller.set_session(SessionKey(context.session_id, context.champion_id))
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
        matchup = [(layout, layout.to_page(self._catalog)) for layout in stats.matchup]
        self._runes = {
            "patch": stats.patch,
            "lane": stats.lane,
            "opponent": stats.opponent,
            "general": general,
            "matchup": matchup,
            "warnings": list(stats.warnings),
        }
        self._controller.display([page for _, page in general + matchup])
        self._publish_state()

    def _choose(self, selection: str, matchup: bool) -> None:
        candidates = self._runes.get("matchup" if matchup else "general") or []
        page = next((page for layout, page in candidates if layout.selection == selection), None)
        if page is None:
            self._error = "unknown_recommendation"
            self._publish_state()
            return
        self._controller.choose(page)

    def _fetch_builds(self) -> None:
        context = self._context
        if context is None or context.mode is None or self._stats is None:
            self._builds = []
            self._publish_state()
            return
        try:
            builds = self._stats.builds(context.champion_id, context.mode, context.lane, opponent_id=self._opponent)
            self._builds = builds_json(builds.pages)
        except StatsError as error:
            self._builds, self._error = [], f"stats_{error.code}"
        except Exception:
            log.exception("[ASSISTANT] builds unavailable")
            self._builds, self._error = [], "stats_unavailable"
        self._publish_state()

    def _import_items(self, selections: list[str]) -> None:
        context = self._context
        if context is None or context.mode is None or self._stats is None:
            self._items = {"error": "no_session"}
            self._publish_state()
            return
        if not self._can_edit():
            self._items = {"error": "cannot_edit"}
            self._publish_state()
            return
        self._items = {"pending": True}
        self._publish_state()
        builds = self._stats.builds(context.champion_id, context.mode, context.lane, opponent_id=self._opponent)
        pages = [page for page in builds.pages if page.selection in selections]
        if not pages:
            self._items = {"error": "no_builds"}
            self._publish_state()
            return
        result = import_item_sets(
            LCUItemSets(self._lcu), context.champion_id, build_item_sets(context.champion_id, pages)
        )
        self._items = {"confirmed": result.confirmed, "count": len(pages), "error": result.error}
        self._publish_state()

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
        return {
            "type": "assistant-state",
            "championId": context.champion_id if context else None,
            "lane": context.lane if context else None,
            "mode": context.mode if context else None,
            "enemies": list(context.enemies) if context else [],
            "opponentId": self._opponent,
            "error": self._error,
            "runes": {
                "patch": runes.get("patch"),
                "general": [layout_json(layout, page) for layout, page in runes.get("general", [])],
                "matchup": [layout_json(layout, page) for layout, page in runes.get("matchup", [])],
                "chosen": page_json(snapshot.chosen),
                "applied": page_json(snapshot.applied),
                "pending": snapshot.pending,
                "error": snapshot.error,
            },
            "items": dict(self._items),
            "builds": self._builds,
        }
