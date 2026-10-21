"""The one assistant service of the process, shared by the bridge and the lock handlers.

The champion lock handlers need the service even when the plugin never asked
for it (the item set is imported without opening the panel), so it is created
on first use by whichever side comes first. State is published to the bridge
once the bridge has registered its publisher; before that it is dropped.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

log = logging.getLogger(__name__)

_lock = threading.Lock()
_service = None
_publisher: Callable[[dict], None] | None = None


def _publish(state: dict) -> None:
    publisher = _publisher
    if publisher is not None:
        publisher(state)


def set_publisher(publisher: Callable[[dict], None] | None) -> None:
    global _publisher
    _publisher = publisher


def get(lcu: Any, state: Any):
    """The shared service, created on first use with the given client and shared state."""
    global _service
    with _lock:
        if _service is None:
            from sexo2.services.assistant import AssistantService
            from sexo2.services.favorite_builds import FILE_NAME, FavoriteBuilds
            from utils.core.paths import get_user_data_dir

            _service = AssistantService(
                lcu,
                _publish,
                queue_id=lambda: getattr(state, "current_queue_id", None),
                in_champ_select=lambda: getattr(state, "phase", None) in ("ChampSelect", "FINALIZATION"),
                favorites=FavoriteBuilds(get_user_data_dir() / FILE_NAME),
            )
        return _service


def champion_confirmed(lcu: Any, state: Any, champion_id: Any, *, swiftplay: bool = False) -> None:
    """Called by the lock handlers; never raises into them."""
    if lcu is None:
        return
    try:
        get(lcu, state).champion_confirmed(champion_id, swiftplay=swiftplay)
    except Exception:
        log.exception("[ASSISTANT] automatic item set import could not start")


def reset() -> None:
    """Tests only."""
    global _service, _publisher
    with _lock:
        _service, _publisher = None, None
