"""The overlays the user switched on in Configurações (D-117), started and stopped live.

``[Overlay] gold_enabled`` and ``augments_enabled`` in config.ini say which overlays
run. :func:`setup` registers the enabled ones at startup; :func:`apply` is called
after the settings are saved and starts or stops each one to match, without
restarting SEXO2. A switched-off overlay has no thread at all.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from config import get_config_float, get_config_option

log = logging.getLogger(__name__)

KINDS = ("gold", "augments")

_lock = threading.Lock()
_context: tuple | None = None  # (thread manager, state, lcu)
_threads: dict[str, threading.Thread] = {}


def enabled(kind: str) -> bool:
    return (get_config_option("Overlay", f"{kind}_enabled", "false") or "").lower() == "true"


def _create(kind: str, state: Any, lcu: Any) -> tuple[str, threading.Thread]:
    if kind == "gold":
        from sexo2.overlay.gold_overlay import Geometry, GoldOverlayThread

        geometry = Geometry(
            rows_top=get_config_float("Overlay", "gold_rows_top", Geometry.rows_top),
            row_step=get_config_float("Overlay", "gold_row_step", Geometry.row_step),
        )
        return "Gold overlay", GoldOverlayThread(state, lcu, geometry)
    from sexo2.augments.vision import Layout
    from sexo2.overlay.augment_overlay import AugmentOverlayThread

    layout = Layout(
        card_top=get_config_float("Overlay", "augments_card_top", Layout.card_top),
        icon_top=get_config_float("Overlay", "augments_icon_top", Layout.icon_top),
    )
    return "Augment overlay", AugmentOverlayThread(state, lcu, layout)


def _sync(start: bool) -> None:
    manager, state, lcu = _context
    for kind in KINDS:
        thread = _threads.get(kind)
        running = thread is not None and thread.is_alive()
        if enabled(kind) and not running:
            name, thread = _create(kind, state, lcu)
            manager.register(name, thread, stop_method=thread.stop)
            _threads[kind] = thread
            if start:
                thread.start()
                log.info("[OVERLAY] %s switched on", name)
        elif not enabled(kind) and thread is not None:
            thread.stop()
            del _threads[kind]
            log.info("[OVERLAY] %s switched off", kind)


def setup(manager: Any, state: Any, lcu: Any) -> None:
    """At startup: register the enabled overlays; the manager starts them with the rest.

    The overlay study (docs/estudos/OVERLAYS.md) runs in the next three matches whatever
    the switches, and then never again.
    """
    global _context
    with _lock:
        _context = (manager, state, lcu)
        _sync(start=False)
        from sexo2.overlay.study import MATCHES, OverlayStudyThread, done_matches, results_dir

        if done_matches(results_dir()) < MATCHES:
            study = OverlayStudyThread(state)
            manager.register("Overlay study", study, stop_method=study.stop)


def apply() -> None:
    """After the settings change: start or stop each overlay to match config.ini."""
    with _lock:
        if _context is not None:
            _sync(start=True)
