"""Item value comparison drawn over the scoreboard while Tab is held (decision D-009).

Off unless ``[Overlay] gold_enabled = true`` in config.ini. Row positions are calibrated
against a real 1920x1080 scoreboard (``gold_rows_top`` / ``gold_row_step`` override them).
Other resolutions and HUD scales still need checking in the game. It needs the game
in borderless or windowed mode; nothing is injected into the game.

Work happens only during a match: the Tab key is sampled every 100 ms and the Live Client
Data API is read at most once per second while Tab is held.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from sexo2.services.gold import CHAOS, ORDER, Comparison, Unsupported, compare, for_player_team, item_prices

log = logging.getLogger(__name__)

LIVE_CLIENT = "https://127.0.0.1:2999/liveclientdata"
ALLY = "#4f8cff"
ENEMY = "#e5484d"
NEUTRAL = "#a4a9b0"
TRANSPARENT = "#010203"


@dataclass(frozen=True)
class Geometry:
    """Positions measured on the 1080p scoreboard, expressed as screen fractions."""

    center_x: float = 0.5
    total_y: float = 234 / 1080
    rows_top: float = 346 / 1080
    row_step: float = 76.5 / 1080


@dataclass(frozen=True)
class Mark:
    kind: str  # "total" or "row"
    x: int
    y: int
    text: str
    color: str
    arrow: str | None  # "left" (toward my team), "right" (toward theirs) or None
    left: str = ""
    right: str = ""


def _number(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _side(diff: int) -> tuple[str, str | None]:
    if diff > 0:
        return ALLY, "left"
    if diff < 0:
        return ENEMY, "right"
    return NEUTRAL, None


def layout(comparison: Comparison, width: int, height: int, geometry: Geometry = Geometry()) -> list[Mark]:
    """What to draw for a comparison already expressed from the local player's side."""
    marks = []
    x = round(width * geometry.center_x)
    if comparison.difference is not None:
        color, arrow = _side(comparison.difference)
        marks.append(
            Mark(
                "total",
                x,
                round(height * geometry.total_y),
                _number(abs(comparison.difference)),
                color,
                arrow,
                _number(comparison.order_total),
                _number(comparison.chaos_total),
            )
        )
    for index, row in enumerate(comparison.rows):
        if row.difference is None:
            continue  # unknown price: show nothing rather than a wrong number
        color, arrow = _side(row.difference)
        y = round(height * (geometry.rows_top + index * geometry.row_step))
        marks.append(Mark("row", x, y, _number(abs(row.difference)), color, arrow))
    return marks


def overlay_bounds(width: int, height: int, geometry: Geometry) -> tuple[int, int, int, int]:
    """Only the central gold column needs a transparent window, not the whole screen."""
    scale = height / 1080
    half_width = max(96, round(128 * scale))
    padding = max(18, round(24 * scale))
    center = round(width * geometry.center_x)
    ys = (geometry.total_y, geometry.rows_top, geometry.rows_top + 4 * geometry.row_step)
    return (
        max(0, center - half_width),
        max(0, round(height * min(ys)) - padding),
        min(width, center + half_width),
        min(height, round(height * max(ys)) + padding),
    )


def my_team(playerlist: list[dict], active_name: str) -> str:
    for player in playerlist:
        if active_name and active_name in (player.get("riotId"), player.get("summonerName")):
            team = player.get("team")
            if team in (ORDER, CHAOS):
                return team
    raise Unsupported("active player not found")


def read_comparison(fetch: Callable[[str], Any], prices: dict[int, int]) -> Comparison:
    """One reading of the Live Client Data API, from the local player's side."""
    playerlist = fetch("/playerlist")
    name = fetch("/activeplayername")
    return for_player_team(compare(playerlist, prices), my_team(playerlist, str(name or "")))


def _tab_down() -> bool:
    if sys.platform != "win32":
        return False
    import ctypes

    return bool(ctypes.windll.user32.GetAsyncKeyState(0x09) & 0x8000)


class _Window:
    """A click-through, always-on-top transparent Tk window on its own thread."""

    def __init__(self, geometry: Geometry) -> None:
        self._geometry = geometry
        self._queue: queue.Queue = queue.Queue()
        threading.Thread(target=self._run, name="SEXO2-GoldOverlay-UI", daemon=True).start()

    def show(self, comparison: Comparison) -> None:
        self._queue.put(comparison)

    def hide(self) -> None:
        self._queue.put(None)

    def close(self) -> None:
        self._queue.put(False)

    def _run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=TRANSPARENT)
        root.attributes("-transparentcolor", TRANSPARENT)
        width, height = root.winfo_screenwidth(), root.winfo_screenheight()
        left, top, right, bottom = overlay_bounds(width, height, self._geometry)
        root.geometry(f"{right - left}x{bottom - top}+{left}+{top}")
        canvas = tk.Canvas(root, width=right - left, height=bottom - top, bg=TRANSPARENT, highlightthickness=0)
        canvas.pack()
        root.update_idletasks()
        self._click_through(root)
        scale = height / 1080
        offset = round(70 * scale)
        arrow_width = max(3, round(4 * scale))
        arrow_half_height = max(3, round(4 * scale))
        gap = max(4, round(6 * scale))

        def draw(comparison: Comparison) -> None:
            canvas.delete("all")
            for mark in layout(comparison, width, height, self._geometry):
                x, y = mark.x - left, mark.y - top
                # Negative Tk font sizes are pixels, so Windows DPI does not
                # enlarge labels a second time on top of the game resolution.
                size = -max(8, round((12 if mark.kind == "total" else 10) * scale))
                if mark.kind == "total":
                    canvas.create_text(x - offset, y, text=mark.left, fill=ALLY, font=("Segoe UI", size, "bold"))
                    canvas.create_text(x + offset, y, text=mark.right, fill=ENEMY, font=("Segoe UI", size, "bold"))
                if mark.arrow:
                    w = arrow_width if mark.arrow == "left" else -arrow_width
                    canvas.create_polygon(
                        x - w,
                        y - gap,
                        x + w,
                        y - gap - arrow_half_height,
                        x + w,
                        y - gap + arrow_half_height,
                        fill=mark.color,
                    )
                canvas.create_text(x, y + gap, text=mark.text, fill=mark.color, font=("Segoe UI", size, "bold"))

        visible = False
        drawn: Comparison | None = None

        def poll() -> None:
            nonlocal visible, drawn
            try:
                while True:
                    item = self._queue.get_nowait()
                    if item is False:
                        root.destroy()
                        return
                    if item is None:
                        if visible:
                            root.withdraw()
                            visible = False
                    else:
                        if item != drawn:
                            draw(item)
                            drawn = item
                        if not visible:
                            root.deiconify()
                            visible = True
            except queue.Empty:
                pass
            root.after(50, poll)

        root.after(50, poll)
        root.mainloop()

    @staticmethod
    def _click_through(root: Any) -> None:
        if sys.platform != "win32":
            return
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
        GWL_EXSTYLE = -20
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        # layered | transparent (click-through) | toolwindow (no taskbar) | noactivate
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x80000 | 0x20 | 0x80 | 0x08000000)


class GoldOverlayThread(threading.Thread):
    def __init__(self, state: Any, lcu: Any, geometry: Geometry = Geometry()) -> None:
        super().__init__(name="SEXO2-GoldOverlay", daemon=True)
        self._state = state
        self._lcu = lcu
        self._geometry = geometry
        self._stop_event = threading.Event()
        self._prices: dict[int, int] = {}
        self._window: _Window | None = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._window is not None:
            self._window.close()

    def _fetch(self, path: str) -> Any:
        import requests

        with requests.get(LIVE_CLIENT + path, verify=False, timeout=0.5) as response:  # Riot's local certificate
            response.raise_for_status()
            return response.json()

    def run(self) -> None:
        shown = False
        last_read = 0.0
        last_prices = float("-inf")
        while not self._stop_event.is_set():
            if getattr(self._state, "phase", None) != "InProgress":
                self._prices = {}
                last_prices = float("-inf")
                if shown:
                    self._window.hide()
                    shown = False
                self._stop_event.wait(1.0)
                continue
            # Prepare once the match starts, before the first Tab press. Tk
            # stays withdrawn and catalog retries reuse this existing loop.
            if self._window is None:
                self._window = _Window(self._geometry)
            now = time.monotonic()
            if not self._prices and now - last_prices >= 5.0:
                last_prices = now
                try:
                    self._prices = item_prices(self._lcu.get("/lol-game-data/assets/v1/items.json") or [])
                except Exception as error:
                    log.debug("[GOLD] item catalog not ready: %s", error)
            if not _tab_down():
                if shown:
                    self._window.hide()
                    shown = False
                self._stop_event.wait(0.1)
                continue
            if now - last_read >= 1.0:
                last_read = now
                try:
                    comparison = read_comparison(self._fetch, self._prices)
                    self._window.show(comparison)
                    shown = True
                except Unsupported:
                    pass  # Arena and other modes without a paired scoreboard
                except Exception as error:
                    log.debug("[GOLD] reading failed: %s", error)
            self._stop_event.wait(0.1)
