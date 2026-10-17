"""Minimal, non-personal draft context read from the existing LCU connection."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import threading


class BuildError(ValueError):
    """An actionable recommendation/import error safe to show in the panel."""


def positive(value):
    return type(value) is int and value > 0


def game_key(value):
    """Stable in-memory match binding without publishing the native game ID."""
    if not positive(value):
        return None
    return hashlib.sha256(('sexo2-game:' + str(value)).encode()).hexdigest()[:24]


def game_mode(data):
    """Confirmed queue/map combinations; never approximate unknown variants."""
    if not isinstance(data, dict):
        return None
    queue = data.get('queue')
    queue = queue if isinstance(queue, dict) else {}
    qid = queue.get('id', data.get('queueId'))
    if qid == 450:
        return 'aram'
    mode_name = str(data.get('gameMode') or queue.get('gameMode', '')).upper()
    if qid == 1700 or mode_name == 'CHERRY':
        return 'arena'
    if (str(data.get('gameMode', queue.get('gameMode', ''))).upper() == 'CLASSIC'
            and data.get('mapId', queue.get('mapId')) == 11):
        return 'ranked'
    return None


def lane(value):
    return {'top': 'top', 'jungle': 'jungle', 'middle': 'middle',
            'mid': 'middle', 'bottom': 'bottom', 'adc': 'bottom',
            'utility': 'support', 'support': 'support'}.get(str(value).lower(), 'all')


@dataclass(frozen=True)
class DraftContext:
    revision: str
    phase: str
    champion_id: int
    mode: str | None
    lane: str
    finalization: bool
    enemies: tuple
    warning: str | None = None
    game_key: str | None = None

    def to_dict(self):
        return asdict(self)


class DraftReader:
    def __init__(self, lcu):
        self.lcu = lcu
        self._lock = threading.RLock()
        self._epoch = 0
        self._previous = None
        self._champions = None

    def _get(self, path):
        try:
            return self.lcu.draft_request(path)
        except ValueError:
            raise BuildError('Não foi possível ler a seleção do cliente. Aguarde ou reconecte.') from None

    def read(self):
        with self._lock:
            phase = self._get('/lol-gameflow/v1/gameflow-phase')
            if not isinstance(phase, str):
                raise BuildError('Não foi possível ler o estado do cliente LoL.')
            cid, mode, own_lane, finalization, enemies, warning, session_id = 0, None, 'all', False, [], None, None
            if phase == 'ChampSelect':
                session = self._get('/lol-champ-select/v1/session')
                game = self._get('/lol-gameflow/v1/session')
                if not isinstance(session, dict) or not isinstance(game, dict):
                    raise BuildError('A seleção de campeões ainda não está disponível.')
                team, opponents = session.get('myTeam'), session.get('theirTeam')
                if not isinstance(team, list) or not isinstance(opponents, list):
                    raise BuildError('O formato da seleção mudou; aguarde ou reconecte.')
                cell = session.get('localPlayerCellId')
                if type(cell) is not int or cell < 0 or len(team) > 20 or len(opponents) > 20:
                    raise BuildError('Os identificadores da seleção mudaram de formato.')
                own = next((p for p in team if isinstance(p, dict) and p.get('cellId') == cell), None)
                if own is None:
                    raise BuildError('Seu campeão ainda não foi identificado nesta seleção.')
                cid = own.get('championId') if positive(own.get('championId')) else 0
                own_lane = lane(own.get('assignedPosition'))
                data = game.get('gameData') or {}
                if not isinstance(data, dict):
                    raise BuildError('Modo de jogo indisponível.')
                queue = data.get('queue') or {}
                if not isinstance(queue, dict):
                    queue = {}
                qid = queue.get('id', data.get('queueId'))
                mode = game_mode(data)
                if mode == 'ranked':
                    if qid not in (420, 440):
                        warning = 'As estatísticas de Summoner’s Rift são da fila Ranked.'
                elif mode is None:
                    warning = 'Este modo/variante ainda não tem uma fonte confirmada.'
                timer = session.get('timer') or {}
                if not isinstance(timer, dict):
                    raise BuildError('O estado de finalização do draft está indisponível.')
                finalization = timer.get('phase') == 'FINALIZATION'
                # No account, player name, PUUID, credential or countdown in this projection.
                for player in opponents:
                    if isinstance(player, dict) and positive(player.get('championId')):
                        enemies.append((player['championId'], lane(player.get('assignedPosition'))))
                enemies = sorted(set(enemies))
                session_id = game.get('gameId') or data.get('gameId') or session.get('gameId')
                if not positive(session_id):
                    raise BuildError('O identificador deste draft ainda não está disponível.')
                if positive(session.get('gameId')) and session['gameId'] != session_id:
                    raise BuildError('O cliente está trocando de seleção. Aguarde um instante.')
            identity = (phase, cid, mode, own_lane, finalization, tuple(enemies), session_id)
            if identity != self._previous:
                self._epoch += 1
                self._previous = identity
            revision = hashlib.sha256(json.dumps((self._epoch, identity)).encode()).hexdigest()[:24]
            return DraftContext(revision, phase, cid, mode, own_lane, finalization,
                                tuple(enemies), warning, game_key(session_id))

    def champions(self):
        with self._lock:
            if self._champions is None:
                rows = self._get('/lol-game-data/assets/v1/champion-summary.json')
                if not isinstance(rows, list) or len(rows) > 2000:
                    raise BuildError('O catálogo de campeões do cliente não está disponível.')
                catalog = {}
                for row in rows:
                    if not isinstance(row, dict) or not positive(row.get('id')):
                        continue
                    alias = row.get('alias')
                    if not isinstance(alias, str):
                        continue
                    slug = {'MonkeyKing': 'wukong'}.get(alias, alias.lower())
                    if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', slug):
                        continue
                    catalog[row['id']] = {'id': row['id'], 'slug': slug,
                                          'name': str(row.get('name') or alias)[:80]}
                if not catalog:
                    raise BuildError('O catálogo retornou sem identificadores válidos.')
                self._champions = catalog
            return self._champions

    def champion(self, cid):
        value = self.champions().get(cid)
        if value is None:
            raise BuildError('Campeão não encontrado no catálogo do cliente.')
        return dict(value)
