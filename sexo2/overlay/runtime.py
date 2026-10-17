"""Bounded LCU observation off the native window thread; no live game scraping."""
from dataclasses import dataclass
import logging
import os
import threading
import time

from sexo2.services.draft import game_key, game_mode, positive
from .model import Card, OverlayStore, View

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Frame:
    active: bool = False
    view: View = View('', ())
    preview: bool = False


class OverlayRuntime:
    def __init__(self, lcu, *, enabled, champion=lambda: None, window_factory=None,
                 arena_factory=None, offer_reader_factory=None, clock=time.monotonic):
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
        self._offer_factory = offer_reader_factory
        self._offers = None
        self._offer_context = None
        self._preview_until = float('-inf')
        self._diagnostic = {'code': 'not-started', 'message': 'Overlay ainda não iniciado.'}

    def diagnostic(self):
        with self._lock:
            result = dict(self._diagnostic)
        if self._window is not None and hasattr(self._window, 'diagnostic'):
            result['window'] = self._window.diagnostic()
        if self._offers is not None:
            result['offers'] = self._offers.diagnostic()
            if result.get('code') == 'offers' and result['offers'] == 'unavailable':
                result['message'] = 'Leitura das cartas indisponível. Confira o helper OCR, o idioma do Windows e o jogo em primeiro plano.'
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
        offer_context = None
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
                    queue = data.get('queue') if isinstance(data.get('queue'), dict) else {}
                    # Riot's public queues.json confirms 2400 as ARAM: Mayhem.
                    if (data.get('queueId', queue.get('id')) == 2400
                            or str(data.get('gameMode', queue.get('gameMode', ''))).upper() == 'KIWI'):
                        mode = 'mayhem'
                    if key is None:
                        raise ValueError('Unknown game identity')
                    self.store.observe(phase, key, mode)
                    self.store.verify_champion(self.champion())
                    status = {'code': 'draft', 'message': 'Aguardando a partida; não há overlay na seleção.'}
                    if phase in ('InProgress', 'Reconnect'):
                        if mode in ('arena', 'mayhem'):
                            if mode == 'arena' and self._arena is None:
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
                                if mode == 'arena':
                                    self._arena.ensure(key, cid)
                                offer_context = (key, cid, mode)
                                if self._offers is None and (self._offer_factory or os.name == 'nt'):
                                    from .reader import OfferReader
                                    self._offers = self._offer_factory() if self._offer_factory else OfferReader(self.lcu)
                                if self._offers is not None:
                                    self._offers.ensure(offer_context)
                                frame = self._offered_frame(offer_context)
                            else:
                                frame = Frame(True, View(key, (Card('SEXO2 · identificando campeão',
                                    ('Partida reconhecida.', 'Aguardando identificação local do seu campeão.',
                                     'Nenhuma oferta ou estatística foi presumida.')),)))
                            status = {'code': 'offers', 'message': 'Leitura local: aguardando cartas na tela; nenhuma lista geral será exibida.'}
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
            offer_context = None
            status = {'code': 'client-unavailable', 'message': 'Não foi possível confirmar a partida pelo LCU. Confira se o cliente permanece aberto.'}
        with self._lock:
            self._frame = frame
            self._offer_context = offer_context
            self._diagnostic = status
            self._observed_at = self._clock()
        if offer_context is None and self._offers is not None:
            self._offers.clear()
        return frame

    def _offered_frame(self, context):
        offer = self._offers.current(context) if self._offers is not None else None
        if offer is None:
            key, _, mode = context
            unavailable = self._offers is None or self._offers.diagnostic() == 'unavailable'
            message = ('Leitura indisponível: confira o OCR/idioma do Windows.' if unavailable else
                       'Aguardando duas leituras das cartas oferecidas.')
            return Frame(True, View(key, (Card(('Arena' if mode == 'arena' else 'Mayhem') + ' · aguardando oferta',
                (message, 'Use o jogo em janela ou sem bordas.',
                 'Sem cartas reconhecidas, nenhuma métrica é exibida.')),)))
        key, cid, mode = context
        if mode == 'arena':
            view = self._arena.offered_view(key, cid, offer)
        else:
            from .offers import offer_view
            view = offer_view(key, offer, mode='mayhem')
        return Frame(bool(view.cards), view)

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
            if self._offer_context is not None:
                return self._offered_frame(self._offer_context)
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
        if self._offers is not None:
            self._offers.close()
        if self._arena is not None:
            self._arena.close()
        if self._window is not None:
            try:
                self._window.stop()
            except Exception:
                log.warning('Não foi possível confirmar o encerramento da janela do overlay.')
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=.2)
