"""Overlay study (docs/estudos/OVERLAYS.md): what costs frames in the user's own matches.

In the next three matches (any mode), 90 s after the match starts, the game's frame rate
and present mode are measured with PresentMon in three 40 s windows: nothing, the screen
capture the augment overlay does, and an invisible click-through window over the game
(as the overlays' windows). The augment overlay pauses its own capture meanwhile. The
game's local API is read once: only its field names, and the values of fields about
augments (never player names). The result goes to
``diagnostics/estudo-overlay-<time>.json`` in the data folder, which "Gerar diagnóstico"
includes, and to one log line. After three matches the study stops for good.
"""

from __future__ import annotations

import csv
import json
import logging
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

MATCHES = 3
SETTLE_S = 90.0
WINDOW_S = 40
GAME_EXE = "League of Legends.exe"
LIVE_CLIENT = "https://127.0.0.1:2999/liveclientdata"
PREFIX = "estudo-overlay-"

_measuring = threading.Event()


def measuring() -> bool:
    """True while a window is measured: the augment overlay then pauses its capture."""
    return _measuring.is_set()


def results_dir() -> Path:
    from utils.core.paths import get_user_data_dir

    return get_user_data_dir() / "diagnostics"


def presentmon_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "diagnostic-tools" / "PresentMon.exe"


def summarize_csv(path: Path) -> dict:
    """Frames, mean fps, 1 % low fps and present modes of a PresentMon CSV."""
    frame_ms, modes = [], Counter()
    with path.open(newline="", encoding="utf-8", errors="replace") as stream:
        for row in csv.DictReader(stream):
            value = row.get("MsBetweenPresents") or row.get("FrameTime") or ""
            try:
                ms = float(value)
            except ValueError:
                continue
            if ms > 0:
                frame_ms.append(ms)
                modes[row.get("PresentMode") or "?"] += 1
    if len(frame_ms) < 10:
        return {"frames": len(frame_ms)}
    slow = sorted(frame_ms)[int(len(frame_ms) * 0.99) - 1]
    return {
        "frames": len(frame_ms),
        "fps": round(1000 / statistics.fmean(frame_ms), 1),
        "low1": round(1000 / slow, 1),
        "modes": dict(modes.most_common()),
    }


def describe_live(data: Any, path: str = "", out: dict | None = None) -> dict:
    """Field names of the local API's answer, and the values of fields about augments."""
    out = out if out is not None else {"fields": set(), "augments": {}}
    if isinstance(data, dict):
        for key, value in data.items():
            child = f"{path}.{key}" if path else str(key)
            out["fields"].add(child)
            if "augment" in str(key).lower():
                out["augments"][child] = value
            else:
                describe_live(value, child, out)
    elif isinstance(data, list):
        for item in data[:10]:
            describe_live(item, path + "[]", out)
    return out


def done_matches(folder: Path) -> int:
    return len(list(folder.glob(PREFIX + "*.json"))) if folder.is_dir() else 0


class _CaptureLoad:
    """The augment overlay's own work: a capture of the card area and the card check, every second."""

    def __init__(self) -> None:
        self._stop = threading.Event()

    def __enter__(self):
        threading.Thread(target=self._run, name="SEXO2-Study-capture", daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()

    def _run(self) -> None:
        from PIL import ImageGrab

        from sexo2.augments.vision import ARENA_LAYOUT, card_area, cards_present
        from sexo2.overlay.augment_overlay import _screen_size

        screen = _screen_size()
        area = card_area(*screen, ARENA_LAYOUT)
        while not self._stop.is_set():
            try:
                part = ImageGrab.grab(bbox=area)
                cards_present(part, ARENA_LAYOUT, screen=screen, origin=area[:2])
            except Exception as error:
                log.debug("[ESTUDO] capture failed: %s", error)
            self._stop.wait(1.0)


class _WindowLoad:
    """An invisible, click-through, always-on-top window over the whole game, like the overlays'."""

    def __init__(self) -> None:
        self._stop = threading.Event()

    def __enter__(self):
        threading.Thread(target=self._run, name="SEXO2-Study-window", daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()

    def _run(self) -> None:
        import tkinter as tk

        from sexo2.overlay.augment_overlay import _screen_size
        from sexo2.overlay.gold_overlay import _Window as GoldWindow

        width, height = _screen_size()
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.01)
        root.geometry(f"{width}x{height}+0+0")
        root.update_idletasks()
        GoldWindow._click_through(root)

        def poll() -> None:
            if self._stop.is_set():
                root.destroy()
            else:
                root.after(200, poll)

        root.after(200, poll)
        root.mainloop()


LOADS: tuple[tuple[str, Callable[[], Any] | None], ...] = (
    ("nada", None),
    ("captura", _CaptureLoad),
    ("janela", _WindowLoad),
)


class OverlayStudyThread(threading.Thread):
    def __init__(self, state: Any) -> None:
        super().__init__(name="SEXO2-OverlayStudy", daemon=True)
        self._state = state
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        if sys.platform != "win32":
            return
        folder = results_dir()
        while not self._stop.is_set() and done_matches(folder) < MATCHES:
            if getattr(self._state, "phase", None) != "InProgress":
                self._stop.wait(5.0)
                continue
            if self._stop.wait(SETTLE_S) or getattr(self._state, "phase", None) != "InProgress":
                continue
            try:
                self._study(folder)
            except Exception:
                log.exception("[ESTUDO] study failed")
            while not self._stop.is_set() and getattr(self._state, "phase", None) == "InProgress":
                self._stop.wait(5.0)  # one study per match

    def _study(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        result: dict = {
            "time": stamp,
            "queue": getattr(self._state, "current_queue_id", None),
            "gameMode": getattr(self._state, "current_game_mode", None),
            "presentmon": presentmon_path().is_file(),
            "windows": {},
        }
        result["liveClient"] = self._probe_live()
        _measuring.set()
        try:
            for name, load in LOADS:
                if getattr(self._state, "phase", None) != "InProgress" or self._stop.is_set():
                    break
                csv_path = folder / f"{PREFIX}{stamp}-{name}.csv"
                if load is None:
                    result["windows"][name] = self._measure(csv_path)
                else:
                    with load():
                        result["windows"][name] = self._measure(csv_path)
                csv_path.unlink(missing_ok=True)
        finally:
            _measuring.clear()
        (folder / f"{PREFIX}{stamp}.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
        log.info(
            "[ESTUDO] %s",
            json.dumps(
                {"windows": result["windows"], "augmentFields": sorted(result["liveClient"].get("augments", {}))}
            ),
        )

    def _measure(self, csv_path: Path) -> dict:
        exe = presentmon_path()
        if not exe.is_file():
            time.sleep(WINDOW_S)
            return {"error": "presentmon_missing"}
        command = [
            str(exe),
            "--process_name",
            GAME_EXE,
            "--output_file",
            str(csv_path),
            "--timed",
            str(WINDOW_S),
            "--terminate_after_timed",
            "--no_console_stats",
            "--v1_metrics",
            "--session_name",
            "SEXO2Estudo",
            "--stop_existing_session",
        ]
        try:
            subprocess.run(
                command,
                capture_output=True,
                timeout=WINDOW_S + 30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError) as error:
            return {"error": str(error)}
        if not csv_path.is_file():
            return {"error": "no_csv"}
        return summarize_csv(csv_path)

    def _probe_live(self) -> dict:
        try:
            import requests

            with requests.get(LIVE_CLIENT + "/allgamedata", verify=False, timeout=2) as response:  # Riot's certificate
                response.raise_for_status()
                described = describe_live(response.json())
        except Exception as error:
            return {"error": str(error)}
        return {"fields": sorted(described["fields"]), "augments": described["augments"]}
