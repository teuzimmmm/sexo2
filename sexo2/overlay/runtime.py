"""Bounded LCU observation off the native window thread; no live game scraping."""
from dataclasses import dataclass
import logging
import os
import threading
import time

from sexo2.services.draft import game_key, game_mode, positive
from .model import OverlayStore, View

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Frame:
    active: bool = False
    view: View = View('', ())


class OverlayRuntime:
    def __init__(self, lcu, *, enabled, window_factory=None, clock=time.monotonic):
        self.lcu, self.enabled = lcu, enabled
        self.store = OverlayStore(clock=clock)
        self._clock = clock
        self._lock = threading.Lock()
        self._frame = Frame()
        self._observed_at = float('-inf')
        self._stop = threading.Event()
        self._thread = None
        self._window = None
        self._factory = window_factory

    def poll(self):
        """Public seam for deterministic tests; never called by the GDI thread."""
        frame = Frame()
        try:
            enabled = self.enabled()
            if enabled:
                phase = self.lcu.draft_request('/lol-gameflow/v1/gameflow-phase')
                if phase in ('ChampSelect', 'GameStart', 'InProgress', 'Reconnect'):
                    game = self.lcu.draft_request('/lol-gameflow/v1/session')
                    # Avoid publishing a session observed across a phase transition.
                    after = self.lcu.draft_request('/lol-gameflow/v1/gameflow-phase')
                    if phase != after or not isinstance(game, dict):
                        raise ValueError('Unstable game context')
                    data = game.get('gameData')
                    if not isinstance(data, dict):
                        raise ValueError('Unknown game session')
                    key = game_key(game.get('gameId') or data.get('gameId'))
                    if (positive(game.get('gameId')) and positive(data.get('gameId'))
                            and game['gameId'] != data['gameId']):
                        raise ValueError('Conflicting game identity')
                    mode = game_mode(data)
                    if key is None:
                        raise ValueError('Unknown game identity')
                    self.store.observe(phase, key, mode)
                    if phase in ('InProgress', 'Reconnect') and mode in ('ranked', 'aram'):
                        frame = Frame(True, self.store.view(key, mode))
                else:
                    self.store.clear()
            # Disabling hides immediately; retain prepared pages until an observed exit.
        except Exception:
            # No false empty success, no exception repr (may contain local credentials).
            # Keep bounded snapshot for same-match reconnect; frame expires/hides.
            pass
        with self._lock:
            self._frame = frame
            self._observed_at = self._clock()
        return frame

    def frame(self):
        with self._lock:
            # If the observer blocks/disappears, fail closed rather than displaying stale UI.
            if self._stop.is_set() or self._clock() - self._observed_at > 8:
                return Frame()
            return self._frame

    def start(self):
        if self._thread is not None or self._stop.is_set():
            return
        if self._factory is None:
            if os.name != 'nt':
                return
            from .win32 import NativeOverlay
            self._factory = NativeOverlay
        try:
            self._window = self._factory(self.frame)
            self._window.start()
            self._thread = threading.Thread(target=self._run, name='SEXO2-Overlay-context', daemon=True)
            self._thread.start()
        except Exception:
            self.stop()
            log.warning('Overlay indisponível; painel e skins continuam ativos.')

    def _run(self):
        while not self._stop.is_set():
            self.poll()
            self._stop.wait(2)

    def stop(self):
        self._stop.set()
        self.store.close()
        if self._window is not None:
            try:
                self._window.stop()
            except Exception:
                log.warning('Não foi possível confirmar o encerramento da janela do overlay.')
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=.2)
