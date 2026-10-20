"""Overlay study (docs/estudos/OVERLAYS.md): what costs frames in the user's own matches.

In the next three matches (any mode), 90 s after the match starts, the game's frame rate
and present mode are measured with PresentMon in three 40 s windows: nothing, the screen
capture the augment overlay does, and an invisible click-through window over the game
(as the overlays' windows). The augment overlay pauses its own capture meanwhile. The
game's local API is read every 5 s for the whole match: only its field names, and the
values of fields about augments (never player names). The result goes to
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
    """Frames, mean fps, 1 % low fps and present modes of a PresentMon CSV.

    PresentMon 2.x writes a byte order mark and names the columns ``msBetweenPresents`` and
    ``PresentMode`` (older ones ``MsBetweenPresents``): the names are matched without case.
    """
    frame_ms, modes = [], Counter()
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as stream:
        for row in csv.DictReader(stream):
            row = {(key or "").strip().lower(): value for key, value in row.items()}
            value = row.get("msbetweenpresents") or row.get("frametime") or ""
            try:
                ms = float(value)
            except ValueError:
                continue
            if ms > 0:
                frame_ms.append(ms)
                modes[row.get("presentmode") or "?"] += 1
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


def _measured(path: Path) -> bool:
    """A study file with at least one window that PresentMon really measured."""
    try:
        windows = json.loads(path.read_text(encoding="utf-8")).get("windows") or {}
        return any(isinstance(w, dict) and w.get("frames", 0) >= 10 for w in windows.values())
    except (OSError, ValueError, AttributeError):
        return True  # unreadable: never count it as a failed try, or the study could repeat for ever


def done_matches(folder: Path) -> int:
    """Matches that count: those measured, until as many tries measured nothing (then it stops)."""
    files = list(folder.glob(PREFIX + "*.json")) if folder.is_dir() else []
    measured = sum(_measured(path) for path in files)
    return measured if len(files) - measured < MATCHES else MATCHES


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


class _LiveProbe(threading.Thread):
    """The game's local API every 5 s for the whole match: the field names, and every
    distinct value of a field about augments (the offers come four times in Arena)."""

    def __init__(self, fetch: Callable[[], Any], every: float = 5.0) -> None:
        super().__init__(name="SEXO2-Study-live", daemon=True)
        self._fetch = fetch
        self._every = every
        self._halt = threading.Event()
        self._began = time.monotonic()
        self.fields: set[str] = set()
        self.samples: list[dict] = []
        self.errors = 0

    def stop(self) -> None:
        self._halt.set()

    def run(self) -> None:
        while not self._halt.is_set():
            self.read_once()
            self._halt.wait(self._every)

    def read_once(self) -> None:
        try:
            described = describe_live(self._fetch())
        except Exception:
            self.errors += 1
            return
        self.fields |= described["fields"]
        seen = {(sample["path"], json.dumps(sample["value"], sort_keys=True)) for sample in self.samples}
        for path, value in described["augments"].items():
            if (path, json.dumps(value, sort_keys=True)) not in seen and len(self.samples) < 60:
                self.samples.append({"s": round(time.monotonic() - self._began), "path": path, "value": value})

    def result(self) -> dict:
        return {"fields": sorted(self.fields), "augmentSamples": self.samples, "errors": self.errors}


def _fetch_live() -> Any:
    import requests

    with requests.get(LIVE_CLIENT + "/allgamedata", verify=False, timeout=2) as response:  # Riot's certificate
        response.raise_for_status()
        return response.json()


def _tail(done: Any) -> str:
    return ((done.stderr or "") + (done.stdout or ""))[-500:]


class OverlayStudyThread(threading.Thread):
    def __init__(self, state: Any) -> None:
        super().__init__(name="SEXO2-OverlayStudy", daemon=True)
        self._state = state
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def _in_match(self) -> bool:
        return getattr(self._state, "phase", None) == "InProgress"

    def run(self) -> None:
        if sys.platform != "win32":
            return
        folder = results_dir()
        while not self._stop.is_set() and done_matches(folder) < MATCHES:
            if not self._in_match():
                self._stop.wait(5.0)
                continue
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            result: dict = {
                "time": stamp,
                "queue": getattr(self._state, "current_queue_id", None),
                "gameMode": getattr(self._state, "current_game_mode", None),
                "presentmon": presentmon_path().is_file(),
                "windows": {},
            }
            probe = _LiveProbe(_fetch_live)
            probe.start()
            if not self._stop.wait(SETTLE_S) and self._in_match():
                try:
                    self._measure_windows(folder, stamp, result)
                except Exception:
                    log.exception("[ESTUDO] measurement failed")
            while not self._stop.is_set() and self._in_match():
                self._stop.wait(5.0)  # the API is read until the match ends; one study per match
            probe.stop()
            result["liveClient"] = probe.result()
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{PREFIX}{stamp}.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
            log.info(
                "[ESTUDO] %s",
                json.dumps(
                    {
                        "windows": result["windows"],
                        "augmentFields": sorted({s["path"] for s in result["liveClient"]["augmentSamples"]}),
                    }
                ),
            )

    def _measure_windows(self, folder: Path, stamp: str, result: dict) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        _measuring.set()
        try:
            for name, load in LOADS:
                if not self._in_match() or self._stop.is_set():
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
            done = subprocess.run(
                command,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=WINDOW_S + 30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError) as error:
            return {"error": str(error)}
        if not csv_path.is_file():
            return {"error": "no_csv", "exit": done.returncode, "output": _tail(done)}
        summary = summarize_csv(csv_path)
        if summary.get("frames", 0) < 10:  # nothing measured: keep what PresentMon said, to see why
            try:
                head = csv_path.read_text(encoding="utf-8", errors="replace")[:600]
            except OSError:
                head = ""
            summary.update({"exit": done.returncode, "output": _tail(done), "csvHead": head})
        return summary
