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
    preview: bool = False


class OverlayRuntime:
    def __init__(self, lcu, *, enabled, champion=lambda: None, window_factory=None,
                 arena_factory=None, clock=time.monotonic):
        self.lcu, self.enabled = lcu, enabled
        self.champion = champion
        self.store = OverlayStore(clock=clock)
        self._clock = clock
        self._lock = threading.Lock()
        self._frame = Frame()
        self._observed_at = float('-inf')
        self._stop = threading.Event()
        self._thread = None
        self._window = None
        self._factory = window_factory
        self._arena_factory = arena_factory
        self._arena = None
        self._arena_champion = None
        self._preview_until = float('-inf')
        self._diagnostic = {'code': 'not-started', 'message': 'Overlay ainda não iniciado.'}

    def diagnostic(self):
        with self._lock:
            result = dict(self._diagnostic)
        if self._window is not None and hasattr(self._window, 'diagnostic'):
            result['window'] = self._window.diagnostic()
        return result

    def preview(self):
        with self._lock:
            if self._stop.is_set():
                return False
            self._preview_until = self._clock() + 20
            self._diagnostic = {'code': 'preview', 'message': 'Prévia solicitada por 20 segundos; não é um teste dentro do LoL.'}
        return True

    def retry_arena(self):
        return bool(not self._stop.is_set() and self._arena is not None and self._arena.retry())

    def poll(self):
        """Public seam for deterministic tests; never called by the GDI thread."""
        frame = Frame()
        status = {'code': 'disabled', 'message': 'Overlay desativado nas configurações.'}
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
                    self.store.verify_champion(self.champion())
                    status = {'code': 'draft', 'message': 'Aguardando a partida; não há overlay na seleção.'}
                    if phase in ('InProgress', 'Reconnect'):
                        if mode == 'arena':
                            if self._arena is None:
                                from .arena import ArenaFeed
                                self._arena = self._arena_factory() if self._arena_factory else ArenaFeed(self.lcu)
                            cid = self.champion()
                            if not positive(cid):
                                if self._arena_champion is None or self._arena_champion[0] != key:
                                    from .arena import own_champion
                                    try:
                                        cid = own_champion(self.lcu, game)
                                    except Exception:
                                        cid = None
                                    if positive(cid):
                                        self._arena_champion = (key, cid)
                                else:
                                    cid = self._arena_champion[1]
                            if positive(cid):
                                self._arena.ensure(key, cid)
                                view = self._arena.view(key, cid)
                            else:
                                from .model import Card
                                view = View(key, (Card('Arena · aguardando campeão',
                                                      ('Seu campeão ainda não foi identificado pelo cliente.',)),))
                            frame = Frame(True, view)
                            status = {'code': 'arena', 'message': 'Arena habilitado: popularidade por campeão, sem WR.'}
                        elif mode in ('ranked', 'aram'):
                            frame = Frame(True, self.store.view(key, mode))
                            status = {'code': 'match', 'message': 'Partida reconhecida; aguardando a janela do jogo em primeiro plano.'}
                        else:
                            status = {'code': 'unsupported-mode', 'message': 'Este modo ainda não tem fonte confirmada para o overlay.'}
                else:
                    self.store.clear()
                    self._arena_champion = None
                    if self._arena is not None:
                        self._arena.clear()
                    status = {'code': 'not-in-game', 'message': 'Aguardando uma partida. Use Testar janela para verificar a exibição.'}
            # Disabling hides immediately; retain prepared pages until an observed exit.
        except Exception:
            # No false empty success, no exception repr (may contain local credentials).
            # Keep bounded snapshot for same-match reconnect; frame expires/hides.
            status = {'code': 'client-unavailable', 'message': 'Não foi possível confirmar a partida pelo LCU. Confira se o cliente permanece aberto.'}
        with self._lock:
            self._frame = frame
            self._diagnostic = status
            self._observed_at = self._clock()
        return frame

    def frame(self):
        with self._lock:
            if not self._stop.is_set() and self._clock() < self._preview_until:
                from .model import Card
                card = Card('SEXO2 · prévia da janela',
                    ('Esta é uma prévia, sem dados de partida.', 'Ela fecha automaticamente em 20 segundos.',
                     'F8 expande/recolhe; os cliques passam para o aplicativo.',
                     'A prévia não comprova exibição sobre o LoL em tela cheia.'))
                return Frame(True, View('preview', (card,)), True)
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
        if self._arena is not None:
            self._arena.close()
        if self._window is not None:
            try:
                self._window.stop()
            except Exception:
                log.warning('Não foi possível confirmar o encerramento da janela do overlay.')
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=.2)
