"""Statistics under the augment cards offered in Arena and ARAM Mayhem.

Off unless ``[Overlay] augments_enabled = true`` in config.ini: the texts and their
look still need approval, and the recognition needs checking in real matches. Like the
gold overlay it needs the game in borderless or windowed mode on the main screen;
nothing is injected into the game and no choice is ever made for the player.

Work happens only during an Arena or Mayhem match: once a second the card area (not
the whole screen) is captured and checked for cards; icons are matched only when the
three cards are there, and twice a second while an offer is open to follow rerolls. The
card titles are read with the Windows OCR when available (D-115); the icons back it up.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from typing import Any

from sexo2.augments.ocr import combine, read_titles, windows_reader
from sexo2.augments.session import QUEUE_MODES, AugmentSession, arena_stats, load_catalog, load_templates, mayhem_stats
from sexo2.augments.view import CardView
from sexo2.augments.vision import ARENA_LAYOUT, IconMatcher, Layout, card_area, crops, read_offer

log = logging.getLogger(__name__)

TRANSPARENT = "#010203"
TEXT = "#ececec"
MUTED = "#a4a9b0"
HIGHLIGHT = "#f2d27a"


def _number(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def card_text(card: CardView) -> tuple[str, str]:
    """(text, colour) shown under one card."""
    if card.state == "unknown":
        return "Não reconhecida", MUTED
    if card.state == "no_data" or card.stat is None:
        return "Sem dados", MUTED
    parts = []
    if card.stat.win_rate is not None:
        parts.append(f"WR {_number(card.stat.win_rate)}%")
    if card.stat.pick_rate is not None:
        parts.append(f"PR {_number(card.stat.pick_rate)}%")
    if card.stat.games is not None:
        parts.append(f"{card.stat.games:,}".replace(",", "."))
    if not parts:
        return "Sem dados", MUTED
    return " · ".join(parts), HIGHLIGHT if card.highlight else TEXT


def text_positions(width: int, height: int, layout: Layout = Layout()) -> list[tuple[int, int]]:
    """Centre of the text under each card, just below the card."""
    return [
        (round((left + right) / 2), round(bottom + 0.018 * height))
        for left, _top, right, bottom in layout.cards(width, height)
    ]


def queue_from_gameflow(session: Any) -> int | None:
    """Queue id of the running game from /lol-gameflow/v1/session."""
    try:
        queue_id = session["gameData"]["queue"]["id"]
    except (KeyError, TypeError):
        return None
    return queue_id if isinstance(queue_id, int) and not isinstance(queue_id, bool) else None


def champion_from_live(playerlist: Any, active_name: Any, summary: Any) -> int | None:
    """Champion id of the local player from the Live Client Data API.

    The player list names champions as ``game_character_displayname_<alias>``; the
    alias is matched against the client's champion summary.
    """
    if not isinstance(playerlist, list) or not isinstance(summary, list) or not active_name:
        return None
    for player in playerlist:
        if not isinstance(player, dict) or active_name not in (player.get("riotId"), player.get("summonerName")):
            continue
        alias = str(player.get("rawChampionName") or "").rsplit("_", 1)[-1].lower()
        for entry in summary:
            if isinstance(entry, dict) and str(entry.get("alias") or "").lower() == alias and alias:
                champion_id = entry.get("id")
                return champion_id if isinstance(champion_id, int) and champion_id > 0 else None
    return None


def _screen_size() -> tuple[int, int]:
    import ctypes

    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class _Window:
    """A click-through, always-on-top transparent Tk window on its own thread."""

    def __init__(self, size: tuple[int, int]) -> None:
        self._size = size
        self._queue: queue.Queue = queue.Queue()
        threading.Thread(target=self._run, name="SEXO2-AugmentOverlay-UI", daemon=True).start()

    def show(self, cards: tuple[CardView, ...], layout: Layout) -> None:
        self._queue.put((cards, layout))

    def hide(self) -> None:
        self._queue.put(None)

    def close(self) -> None:
        self._queue.put(False)

    def _run(self) -> None:
        import tkinter as tk

        from sexo2.overlay.gold_overlay import _Window as GoldWindow

        width, height = self._size
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=TRANSPARENT)
        root.attributes("-transparentcolor", TRANSPARENT)
        root.geometry(f"{width}x{height}+0+0")
        canvas = tk.Canvas(root, width=width, height=height, bg=TRANSPARENT, highlightthickness=0)
        canvas.pack()
        root.withdraw()
        root.update_idletasks()
        GoldWindow._click_through(root)
        size = max(10, round(height * 0.013))

        def draw(cards: tuple[CardView, ...], layout: Layout) -> None:
            canvas.delete("all")
            for card, (x, y) in zip(cards, text_positions(width, height, layout)):
                text, colour = card_text(card)
                if card.name:  # what was read, so a wrong reading can be noticed
                    canvas.create_text(x, y, text=card.name, fill=MUTED, font=("Segoe UI", max(8, size - 3)))
                canvas.create_text(x, y + size + 6, text=text, fill=colour, font=("Segoe UI", size, "bold"))

        def poll() -> None:
            try:
                while True:
                    item = self._queue.get_nowait()
                    if item is False:
                        root.destroy()
                        return
                    if item is None:
                        root.withdraw()
                    else:
                        draw(*item)
                        root.deiconify()
                        root.attributes("-topmost", True)
            except queue.Empty:
                pass
            root.after(50, poll)

        root.after(50, poll)
        root.mainloop()


class AugmentOverlayThread(threading.Thread):
    def __init__(self, state: Any, lcu: Any, layout: Layout = Layout()) -> None:
        super().__init__(name="SEXO2-AugmentOverlay", daemon=True)
        self._state = state
        self._lcu = lcu
        self._layout = layout
        self._stop = threading.Event()
        self._window: _Window | None = None
        self._session: AugmentSession | None = None
        self._session_key: tuple | None = None
        self._failed_at = 0.0
        self._reader = None  # Windows OCR for the card titles, created on the thread
        self._waiting: str | None = None  # last reason logged for not preparing
        self._match: tuple | None = None  # (queue id, champion id) found for a game SEXO2 joined late
        self._match_asked_at = -60.0

    def stop(self) -> None:
        self._stop.set()
        if self._window is not None:
            self._window.close()

    def _fetch_json(self, url: str) -> Any:
        import requests

        from config import APP_USER_AGENT

        with requests.get(url, timeout=5, headers={"User-Agent": APP_USER_AGENT}) as response:
            response.raise_for_status()
            return response.json()

    def _prepare(self, mode: str, champion_id: int) -> AugmentSession:
        from lolalytics.client import Client
        from sexo2.services.stats import ChampionDirectory

        catalog = load_catalog(self._lcu, mode)
        matcher = IconMatcher(load_templates(self._lcu, catalog))
        if mode == "mayhem":
            stats = mayhem_stats(self._fetch_json, champion_id)
        else:
            directory = ChampionDirectory.from_summary(self._lcu.get("/lol-game-data/assets/v1/champion-summary.json"))
            stats = arena_stats(Client(), directory.slug(champion_id))
        log.info("[AUGMENTS] %s: %d augments, %d icons", mode, len(catalog.augments), len(matcher._templates))
        return AugmentSession(catalog, matcher, stats)

    def layout_for(self, mode: str | None) -> Layout:
        return ARENA_LAYOUT if mode == "arena" else self._layout

    def _wait(self, reason: str) -> None:
        if reason != self._waiting:
            log.info("[AUGMENTS] waiting: %s", reason)
            self._waiting = reason

    def _match_from_clients(self) -> tuple[int | None, int | None]:
        """Queue and champion when SEXO2 started after champion select: from the client and the game.

        Asked at most every 10 s until both are known, then kept for the rest of the game.
        """
        queue_id, champion_id = self._match or (None, None)
        if champion_id is not None or time.monotonic() - self._match_asked_at < 10:
            return queue_id, champion_id
        self._match_asked_at = time.monotonic()
        if queue_id is None:
            try:
                queue_id = queue_from_gameflow(self._lcu.get("/lol-gameflow/v1/session"))
            except Exception as error:
                log.debug("[AUGMENTS] gameflow session: %s", error)
        if queue_id in QUEUE_MODES:
            try:
                champion_id = champion_from_live(
                    self._live("/playerlist"),
                    self._live("/activeplayername"),
                    self._lcu.get("/lol-game-data/assets/v1/champion-summary.json"),
                )
            except Exception as error:
                log.debug("[AUGMENTS] live client: %s", error)
        self._match = (queue_id, champion_id)
        return self._match

    def _live(self, path: str) -> Any:
        import requests

        from sexo2.overlay.gold_overlay import LIVE_CLIENT

        with requests.get(LIVE_CLIENT + path, verify=False, timeout=1) as response:  # Riot's local certificate
            response.raise_for_status()
            return response.json()

    def _session_for_match(self) -> AugmentSession | None:
        if getattr(self._state, "phase", None) != "InProgress":
            self._match, self._match_asked_at = None, -60.0
            self._waiting = None
            return None
        queue_id = getattr(self._state, "current_queue_id", None)
        champion_id = getattr(self._state, "locked_champ_id", None)
        if queue_id is None or not isinstance(champion_id, int) or champion_id <= 0:
            found_queue, found_champion = self._match_from_clients()
            queue_id = queue_id if queue_id is not None else found_queue
            if not isinstance(champion_id, int) or champion_id <= 0:
                champion_id = found_champion
        mode = QUEUE_MODES.get(queue_id)
        if mode is None:
            self._wait(f"queue {queue_id} has no augments" if queue_id is not None else "queue unknown")
            return None
        if not isinstance(champion_id, int) or champion_id <= 0:
            self._wait("champion unknown")
            return None
        key = (mode, champion_id)
        if key != self._session_key:
            if time.monotonic() - self._failed_at < 60:
                return None
            try:
                self._session = self._prepare(mode, champion_id)
                self._session_key = key
            except Exception as error:
                log.warning("[AUGMENTS] could not prepare the match: %s", error)
                self._failed_at = time.monotonic()
                return None
        return self._session

    def run(self) -> None:
        if sys.platform != "win32":
            return
        from PIL import ImageGrab

        self._reader = windows_reader()
        log.info("[AUGMENTS] title OCR %s", "available" if self._reader else "unavailable; icons only")
        shown = False
        while not self._stop.is_set():
            session = self._session_for_match()
            if session is None:
                self._session, self._session_key = None, None
                if shown:
                    self._window.hide()
                    shown = False
                self._stop.wait(2.0)
                continue
            layout = self.layout_for(self._session_key[0])
            try:
                screen = _screen_size()
                area = card_area(*screen, layout)
                part = ImageGrab.grab(bbox=area)
                reading = read_offer(part, session.matcher, layout, screen=screen, origin=area[:2])
                if reading and self._reader:
                    titles = read_titles(part, self._reader, session.catalog, layout, screen=screen, origin=area[:2])
                    reading = combine(titles, reading)
                icons = crops(part, layout, screen=screen, origin=area[:2]) if reading else None
                session.observe(reading, icons)
                cards = session.cards()
                if cards:
                    if self._window is None:
                        self._window = _Window(screen)
                    self._window.show(cards, layout)
                    shown = True
                elif shown:
                    self._window.hide()
                    shown = False
            except Exception as error:
                log.debug("[AUGMENTS] reading failed: %s", error)
            self._stop.wait(0.5 if session.tracker.offer else 1.0)
