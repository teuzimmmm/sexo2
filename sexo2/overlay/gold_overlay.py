"""Item value comparison drawn over the scoreboard while Tab is held (decision D-009).

Off unless ``[Overlay] gold_enabled = true`` in config.ini. Row positions are calibrated
against a real 1920x1080 scoreboard (``gold_rows_top`` / ``gold_row_step`` override them).
Other resolutions and HUD scales still need checking in the game. It needs the game
in borderless or windowed mode; nothing is injected into the game.

Work happens only during a match: the Tab key is sampled every 100 ms and the Live Client
Data API is read at most once per second while Tab is held over the game. The connection
and active player's name are reused within a match and discarded on exit or read failure.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

from sexo2.services.gold import CHAOS, ORDER, Comparison, Unsupported, compare, for_player_team, item_prices

log = logging.getLogger(__name__)

LIVE_CLIENT = "https://127.0.0.1:2999/liveclientdata"
ALLY = "#4db0fc"
ENEMY = "#e8404f"
NEUTRAL = "#a4a9b0"


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
    padding = max(30, round(40 * scale))
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
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    if not user32.GetAsyncKeyState(0x09) & 0x8000:
        return False
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    hwnd = user32.GetForegroundWindow()
    name = ctypes.create_unicode_buffer(64)
    return bool(hwnd and user32.GetClassNameW(hwnd, name, len(name)) and name.value == "RiotWindowClass")


SUPERSAMPLE = 4  # drawn at 4x and reduced: smooth digits, edges and arrows
# Look of the scoreboard comparison made popular by Blitz, drawn here: dark diamonds with
# a bronze edge on the seam between the players, the arrow inside, the number below.
FRAME = (58, 56, 47, 255)
FRAME_LIGHT = (96, 88, 62, 255)
ALLY_FILL = (13, 30, 43, 240)
ENEMY_FILL = (42, 14, 18, 240)
NEUTRAL_FILL = (24, 26, 29, 240)
BAR_FILL = (14, 30, 38, 235)
COIN = (201, 164, 92, 255)
COIN_DARK = (120, 92, 44, 255)
SHADOW = (0, 0, 0, 160)


@lru_cache(maxsize=8)
def _font(size: int):
    """Inter Bold (D-007), at the supersampled size."""
    from PIL import ImageFont

    from utils.core.paths import get_asset_path

    return ImageFont.truetype(str(get_asset_path("fonts/inter-bold.ttf")), size * SUPERSAMPLE)


def render(comparison: Comparison, width: int, height: int, geometry: Geometry):
    """The overlay bitmap with true alpha: diamonds on the scoreboard seam and a totals bar."""
    from PIL import Image, ImageDraw

    left, top, right, bottom = overlay_bounds(width, height, geometry)
    k = SUPERSAMPLE
    s = height / 1080 * k  # one 1080p pixel, supersampled
    image = Image.new("RGBA", ((right - left) * k, (bottom - top) * k))
    draw = ImageDraw.Draw(image)

    def font(size: int):
        return _font(max(9, round(size * height / 1080)))

    def text(x: float, y: float, value: str, color: str, size: int) -> None:
        value = value.replace(".", "")  # 1928, as the scoreboard writes numbers
        draw.text((x, y), value, fill=color, font=font(size), anchor="mm", stroke_width=round(s), stroke_fill=SHADOW)

    def diamond(x: float, y: float, radius: float, mark: Mark) -> None:
        def shape(r: float) -> list[tuple[float, float]]:
            return [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]

        fill = {"left": ALLY_FILL, "right": ENEMY_FILL}.get(mark.arrow, NEUTRAL_FILL)
        draw.polygon(shape(radius), fill=FRAME)
        draw.polygon(shape(radius - 1.2 * s), fill=FRAME_LIGHT)
        draw.polygon(shape(radius - 2.4 * s), fill=FRAME)
        draw.polygon(shape(radius - 3.6 * s), fill=fill)
        if mark.arrow:
            tip = -5 * s if mark.arrow == "left" else 5 * s
            x0 = x - tip * 0.25
            draw.polygon([(x0 + tip, y), (x0 - tip, y - 6 * s), (x0 - tip, y + 6 * s)], fill=mark.color)

    def coin(x: float, y: float) -> None:
        for dx, dy in ((-1.5, 2), (1.5, -1.5)):
            box = (x + (dx - 6) * s, y + (dy - 4) * s, x + (dx + 6) * s, y + (dy + 4) * s)
            draw.ellipse(box, fill=COIN, outline=COIN_DARK, width=round(s))

    for mark in layout(comparison, width, height, geometry):
        x, y = (mark.x - left) * k, (mark.y - top) * k
        if mark.kind == "total":
            half_w, half_h = 111 * s, 12 * s
            draw.rectangle(
                (x - half_w, y - half_h, x + half_w, y + half_h), fill=BAR_FILL, outline=FRAME_LIGHT, width=round(s)
            )
            draw.rectangle(
                (x - half_w + 2 * s, y - half_h + 2 * s, x + half_w - 2 * s, y + half_h - 2 * s),
                outline=FRAME,
                width=round(s),
            )
            # Coin before each total, as the scoreboard shows gold.
            coin(x - 95 * s, y)
            text(x - 57 * s, y, mark.left, ALLY, 16)
            coin(x + 42 * s, y)
            text(x + 81 * s, y, mark.right, ENEMY, 16)
            diamond(x, y, 20 * s, mark)
            text(x, y + 17 * s, mark.text, mark.color, 13)
        else:
            diamond(x, y, 17.5 * s, mark)
            text(x, y + 25 * s, mark.text, mark.color, 12)
    return image.resize((right - left, bottom - top), Image.Resampling.LANCZOS)


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

        from sexo2.overlay.alpha_surface import AlphaSurface

        root = tk.Tk()
        root.withdraw()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        width, height = root.winfo_screenwidth(), root.winfo_screenheight()
        left, top, right, bottom = overlay_bounds(width, height, self._geometry)
        root.geometry(f"{right - left}x{bottom - top}+{left}+{top}")
        root.update_idletasks()
        hwnd = self._click_through(root)
        surface = AlphaSurface(hwnd, right - left, bottom - top)

        def draw(comparison: Comparison) -> None:
            surface.update(render(comparison, width, height, self._geometry), left, top)

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
                            # Normal state shows without activation on Windows;
                            # deiconify additionally restacks the toplevel.
                            root.state("normal")
                            visible = True
            except queue.Empty:
                pass
            root.after(50, poll)

        root.after(50, poll)
        try:
            root.mainloop()
        finally:
            surface.close()

    @staticmethod
    def _click_through(root: Any) -> int | None:
        if sys.platform != "win32":
            return
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.GetParent.argtypes = (wintypes.HWND,)
        user32.GetParent.restype = wintypes.HWND
        user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.SetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_long)
        hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
        GWL_EXSTYLE = -20
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        # layered | transparent (click-through) | toolwindow (no taskbar) | noactivate
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x80000 | 0x20 | 0x80 | 0x08000000)
        return hwnd


class GoldOverlayThread(threading.Thread):
    def __init__(self, state: Any, lcu: Any, geometry: Geometry = Geometry()) -> None:
        super().__init__(name="SEXO2-GoldOverlay", daemon=True)
        self._state = state
        self._lcu = lcu
        self._geometry = geometry
        self._stop_event = threading.Event()
        self._prices: dict[int, int] = {}
        self._window: _Window | None = None
        self._session: Any = None
        self._active_name: str | None = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._window is not None:
            self._window.close()

    def _fetch(self, path: str) -> Any:
        import requests

        if path == "/activeplayername" and self._active_name is not None:
            return self._active_name
        if self._session is None:
            self._session = requests.Session()
            self._session.trust_env = False  # Loopback must not use a system proxy.
        try:
            with self._session.get(
                LIVE_CLIENT + path, verify=False, timeout=0.5
            ) as response:  # Riot's local certificate
                response.raise_for_status()
                data = response.json()
        except Exception:
            self._reset_client()
            raise
        if path == "/activeplayername" and isinstance(data, str) and data:
            self._active_name = data
        return data

    def _reset_client(self) -> None:
        session, self._session = self._session, None
        self._active_name = None
        if session is not None:
            session.close()

    def run(self) -> None:
        shown = False
        last_read = 0.0
        last_prices = float("-inf")
        try:
            while not self._stop_event.is_set():
                if getattr(self._state, "phase", None) != "InProgress":
                    self._prices = {}
                    last_prices = float("-inf")
                    self._reset_client()
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
                        if self._stop_event.is_set():
                            break
                        if getattr(self._state, "phase", None) == "InProgress" and _tab_down():
                            self._window.show(comparison)
                            shown = True
                        elif shown:
                            self._window.hide()
                            shown = False
                    except Unsupported:
                        # Retry the name if the game's identity changed before
                        # the next phase event; the connection is still usable.
                        self._active_name = None
                    except Exception as error:
                        log.debug("[GOLD] reading failed: %s", error)
                self._stop_event.wait(0.1)
        finally:
            self._reset_client()
