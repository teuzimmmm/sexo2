"""Visible inventory value only; no unspent gold, game memory or account storage."""
from dataclasses import dataclass
import json
import math
import re
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from .model import Card, text


class GoldError(ValueError):
    """Static, non-personal error; never embed a response or request exception."""


ROLES = {'TOP': 'top', 'JUNGLE': 'jungle', 'MIDDLE': 'middle', 'MID': 'middle',
         'BOTTOM': 'bottom', 'UTILITY': 'support', 'SUPPORT': 'support'}
ROLE_ORDER = ('top', 'jungle', 'middle', 'bottom', 'support', '')
TTL = 6


def number(value, maximum=1_000_000):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= maximum


def inventory(items):
    """Unknown is None; a real empty inventory is zero. Never a partial sum."""
    if not isinstance(items, list) or len(items) > 7:
        return None
    total, slots = 0, set()
    for item in items:
        if not isinstance(item, dict):
            return None
        price, count, slot, identifier = (item.get(k) for k in ('price', 'count', 'slot', 'itemID'))
        if (not number(price, 100_000) or price != int(price)
                or type(count) is not int or not 0 <= count <= 99
                or (price > 0 and count == 0)
                or type(slot) is not int or not 0 <= slot <= 6 or slot in slots
                or type(identifier) is not int or identifier <= 0):
            return None
        slots.add(slot)
        total += int(price) * count
    return total if total <= 1_000_000 else None


@dataclass(frozen=True)
class Player:
    champion: str
    team: str
    role: str
    value: int | None

    @property
    def key(self):
        return self.team + ':' + self.champion


@dataclass(frozen=True)
class Snapshot:
    own: Player
    enemies: tuple[Player, ...]
    game_time: float


def parse(player_name, players, before, after, mode):
    if mode not in ('ranked', 'swiftplay'):
        raise GoldError('Modo sem suporte à comparação de itens.')
    # Identity is used only in this function, and never retained in the result.
    if (not isinstance(player_name, str) or not 0 < len(player_name) <= 256
            or not isinstance(players, list) or not 1 <= len(players) <= 10):
        raise GoldError('Formato da identificação local indisponível.')
    for game in (before, after):
        if (not isinstance(game, dict) or game.get('mapNumber') != 11
                or game.get('gameMode') not in ({'CLASSIC', 'SWIFTPLAY'} if mode == 'swiftplay' else {'CLASSIC'})
                or not number(game.get('gameTime'), 86400)):
            raise GoldError('Contexto do jogo incompatível com a comparação de itens.')
    if not 0 <= after['gameTime'] - before['gameTime'] <= 10:
        raise GoldError('A partida mudou durante a leitura.')
    found, rows, keys, teams = [], [], set(), {'ORDER': 0, 'CHAOS': 0}
    for raw in players:
        if not isinstance(raw, dict):
            raise GoldError('Formato da lista de campeões incompatível.')
        champion, team = raw.get('championName'), raw.get('team')
        if (not isinstance(champion, str) or not champion or len(champion) > 80
                or text(champion, 80) != champion or team not in teams):
            raise GoldError('Campeão ou equipe indisponível.')
        player = Player(champion, team, ROLES.get(str(raw.get('position', '')).upper(), ''),
                        inventory(raw.get('items')))
        if player.key in keys:
            raise GoldError('Campeões ambíguos neste modo.')
        keys.add(player.key)
        teams[team] += 1
        if teams[team] > 5:
            raise GoldError('Modo incompatível com a comparação de itens.')
        if player_name in (raw.get('riotId'), raw.get('summonerName')):
            found.append(player)
        rows.append(player)
    if len(found) != 1:
        raise GoldError('Não foi possível identificar unicamente seu campeão.')
    own = found[0]
    enemies = tuple(sorted((p for p in rows if p.team != own.team),
                           key=lambda p: (ROLE_ORDER.index(p.role), p.champion)))
    return Snapshot(own, enemies, after['gameTime'])


class LiveClient:
    """Anonymous HTTPS loopback session, not the authenticated LCU session."""
    PATHS = frozenset(('activeplayername', 'playerlist', 'gamestats'))

    def __init__(self, *, base='https://127.0.0.1:2999', clock=time.monotonic):
        if not isinstance(base, str) or not re.fullmatch(r'https://127\.0\.0\.1:[1-9][0-9]{0,4}', base):
            raise GoldError('A API de itens deve usar HTTPS loopback.')
        if int(base.rsplit(':', 1)[1]) > 65535:
            raise GoldError('Porta local inválida.')
        self.base, self.clock = base, clock
        self.session = requests.Session()
        self.session.trust_env = False  # No proxy, .netrc or LCU credentials.
        self.session.mount('https://', HTTPAdapter(max_retries=0, pool_connections=1, pool_maxsize=1))

    def get(self, path, deadline):
        if path not in self.PATHS or self.clock() >= deadline:
            raise GoldError('Leitura local não permitida ou prazo excedido.')
        try:
            # Riot's local game API uses a self-signed certificate. This TLS
            # exception is restricted to literal HTTPS 127.0.0.1, never redirects.
            with self.session.get(self.base + '/liveclientdata/' + path,
                    timeout=(.5, .75), verify=False, allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    raise GoldError('API local de itens indisponível.')
                body = bytearray()
                for chunk in response.iter_content(4096):
                    body.extend(chunk)
                    if len(body) > 256 * 1024 or self.clock() >= deadline:
                        raise GoldError('Resposta local excedeu limite ou prazo.')
                def invalid(_):
                    raise GoldError('JSON local inválido.')
                return json.loads(body, parse_constant=invalid)
        except GoldError:
            raise
        except Exception:
            raise GoldError('Não foi possível ler a API local de itens.') from None

    def sample(self, mode):
        deadline = self.clock() + 4
        before = self.get('gamestats', deadline)
        name = self.get('activeplayername', deadline)
        players = self.get('playerlist', deadline)
        after = self.get('gamestats', deadline)
        if self.clock() >= deadline:
            raise GoldError('Coleta de itens expirou.')
        return parse(name, players, before, after, mode)

    def close(self):
        self.session.close()


def opponent(snapshot, selected):
    if selected is not None:
        return next((p for p in snapshot.enemies if p.key == selected), None)
    matches = [p for p in snapshot.enemies if snapshot.own.role and p.role == snapshot.own.role]
    return matches[0] if len(matches) == 1 else None


def amount(value):
    return 'indisponível' if value is None else f'{value:,}'.replace(',', '.') + ' G'


class GoldFeed:
    """Single observer calls refresh; renderer only reads snapshots or cycles IDs."""
    def __init__(self, *, client_factory=LiveClient, clock=time.monotonic):
        self._factory, self._clock = client_factory, clock
        self._lock = threading.Lock()
        self._client = None
        self._context = self._snapshot = self._selected = None
        self._at = float('-inf')
        self._next = float('-inf')
        self._last_game_time = None
        self._invalidated = False
        self._version = self._failures = 0
        self._busy = self._closed = False
        self._state = 'waiting'

    def refresh(self, context):
        with self._lock:
            if self._closed:
                return
            if context != self._context:
                self._context, self._snapshot, self._selected = context, None, None
                self._version += 1
                self._next, self._failures = float('-inf'), 0
                self._last_game_time, self._invalidated = None, False
            if self._invalidated or self._busy or self._clock() < self._next:
                return
            self._busy = True
            version = self._version
        started = self._clock()
        snapshot = None
        try:
            if self._client is None:
                self._client = self._factory()
            snapshot = self._client.sample(context[1])
            with self._lock:
                if (context == self._context and version == self._version
                        and self._last_game_time is not None and snapshot.game_time < self._last_game_time):
                    self._invalidated = True
                    raise GoldError('Relógio da partida reiniciado.')
            if not isinstance(snapshot, Snapshot) or self._clock() - started >= TTL:
                raise GoldError('Leitura de inventário expirou.')
        except Exception:
            snapshot = None  # No raw exception or identities in logs/diagnostics.
        finally:
            with self._lock:
                self._busy = False
                closed = self._closed
                if not closed and context == self._context and version == self._version:
                    self._snapshot, self._at = snapshot, started
                    self._failures = 0 if snapshot else min(4, self._failures + 1)
                    self._next = self._clock() + (2 if snapshot else min(10, 2 ** self._failures))
                    self._state = 'ready' if snapshot else 'unavailable'
                    if snapshot is not None:
                        self._last_game_time = snapshot.game_time
            if closed and self._client is not None:
                self._client.close()

    def diagnostic(self):
        with self._lock:
            return self._state

    def _current(self, context):
        return (not self._closed and context == self._context and self._snapshot is not None
                and self._clock() - self._at < TTL)

    def cycle(self, context):
        with self._lock:
            if not self._current(context) or not self._snapshot.enemies:
                return False
            enemies = self._snapshot.enemies
            current = opponent(self._snapshot, self._selected)
            index = next((i for i, p in enumerate(enemies) if p == current), -1)
            self._selected = enemies[(index + 1) % len(enemies)].key
            return True

    def card(self, context):
        with self._lock:
            if not self._current(context):
                return Card('Ouro em itens · indisponível',
                    ('Aguardando inventários pela API local do jogo.', 'Valores antigos não são exibidos.'))
            snapshot, selected = self._snapshot, self._selected
            enemy = opponent(snapshot, selected)
            lines = [f'Seus itens ({snapshot.own.champion}): {amount(snapshot.own.value)}']
            if enemy is None:
                lines.extend(('Adversário não identificado por rota.', 'F7 para selecionar um adversário.'))
            else:
                delta = (None if snapshot.own.value is None or enemy.value is None else snapshot.own.value - enemy.value)
                lines.extend((f'Itens de {enemy.champion}: {amount(enemy.value)}',
                    'Diferença em itens: ' + (('+' if delta > 0 else '-' if delta < 0 else '') + amount(abs(delta))
                                             if delta is not None else 'indisponível'),
                    'Adversário: ' + ('seleção manual' if selected is not None else 'mesma rota'),
                    'F7: trocar adversário'))
            lines.extend(('Estimativa do valor dos itens observados.', 'Fonte: API local do jogo'))
            return Card('Ouro em itens', tuple(lines))

    def clear(self):
        with self._lock:
            self._context = self._snapshot = self._selected = None
            self._version += 1
            self._state = 'waiting'

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._snapshot = self._selected = self._context = None
            self._version += 1
            busy = self._busy
        if self._client is not None and not busy:
            self._client.close()
