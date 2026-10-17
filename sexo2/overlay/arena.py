"""One bounded Arena popularity request per match/champion, outside the GUI."""
import threading
import time

from lolalytics import Client, Query
from sexo2.services.draft import DraftReader, positive
from sexo2.services.loadouts import GameCatalog
from sexo2.services.work_queue import SerialWorker
from .model import Card, View, text


def cards(recommendation, champion, names):
    """Expose only pick rate/games. Never copy raw or restricted WR cells."""
    result = []
    groups = recommendation.item_rankings
    # Public Arena component q-BDN2fHIE.js maps augment0 to All Augments,
    # augment1..4 to Augment 1..4. This is observation slot, not rarity.
    tables = [('augment_statistics', f'payload.augment.augment{i}',
               'Todos os aprimoramentos' if i == 0 else f'Aprimoramento {i}', 'augments') for i in range(5)]
    tables += [('item_statistics', 'payload.prismatic', 'Itens prismáticos', 'items'),
               ('item_statistics', 'payload.item', 'Itens · popularidade', 'items')]
    for category, source, label, catalog in tables:
        rows = next((v for k, v in groups.items() if k.startswith(category + ':') and k.endswith(':' + source)), [])
        if not rows:
            continue
        lines = [f"Patch {text(recommendation.resolved.get('patch'), 12)} · {text(recommendation.query.get('tier'), 24)}",
                 'Ordenação por pick rate da fonte, sem WR.',
                 'PR não prevê vitória nem combinações/sinergias.']
        valid = [r for r in rows if r.get('identifiers') and r['identifiers'] != ['0']]
        for row in valid[:256]:
            identifier = str(row['identifiers'][0])
            name = names.get(catalog, {}).get(identifier)
            name = text(name, 70) if name else ('Aprimoramento #' if catalog == 'augments' else 'Item #') + identifier
            metric = row.get('metrics', {})
            rate, games = metric.get('pick_rate'), metric.get('games')
            lines.append(f"{name} · PR {rate if rate is not None else '—'}% · {games if games is not None else '—'} jogos")
        if len(valid) > 256:
            lines.append('Mostrando as primeiras 256 observações desta tabela.')
        lines += ['As três cartas oferecidas não são detectadas automaticamente.',
                  'Nomes ausentes aparecem pelo ID, sem equivalências inventadas.',
                  'Coleta: ' + text(recommendation.collected_at, 32) + (' · cache' if recommendation.cache_hit else ''),
                  'Fonte: LoLalytics · Arena']
        result.append(Card(text(champion, 60) + ' · ' + label, tuple(lines)))
    if not result:
        raise ValueError('No supported Arena popularity tables')
    if not any(k.startswith('augment_statistics:') and rows for k, rows in groups.items()):
        result.insert(0, Card(text(champion, 60) + ' · aprimoramentos indisponíveis',
                              ('A fonte não retornou estatísticas de aprimoramentos para esta consulta.',)))
    return tuple(result)


def own_champion(lcu, game, fallback=None):
    """Use the known local pick, or match the local summoner in gameflow teams."""
    if positive(fallback):
        return fallback
    me = lcu.loadout_request('GET', '/lol-summoner/v1/current-summoner')
    data = game.get('gameData', {})
    if not isinstance(me, dict) or not isinstance(data, dict):
        return None
    rows = []
    for field in ('teamOne', 'teamTwo', 'playerChampionSelections'):
        team = data.get(field, [])
        if isinstance(team, list) and len(team) <= 20:
            rows.extend(r for r in team if isinstance(r, dict))
    ids = set()
    for row in rows:
        same = ((positive(me.get('summonerId')) and row.get('summonerId') == me['summonerId'])
                or (isinstance(me.get('puuid'), str) and me['puuid'] and row.get('puuid') == me['puuid']))
        if same and positive(row.get('championId')):
            ids.add(row['championId'])
    return next(iter(ids)) if len(ids) == 1 else None


class ArenaFeed:
    def __init__(self, lcu, *, client_factory=None, clock=time.monotonic):
        self.reader = DraftReader(lcu)
        self.catalog = GameCatalog(lcu)
        self._factory = client_factory or self._client_factory
        self._client = None
        self._clock = clock
        self._lock = threading.RLock()
        self._worker = SerialWorker('SEXO2-Overlay-Arena', capacity=1)
        self._desired = self._attempted = self._complete = None
        self._busy = self._closed = False
        self._cards = ()
        self._error = False
        self._last_retry = float('-inf')

    @staticmethod
    def _client_factory():
        from utils.core.paths import get_user_data_dir
        return Client(cache_dir=get_user_data_dir() / 'lolalytics-cache')

    def ensure(self, key, cid):
        signature = (key, cid)
        with self._lock:
            self._desired = signature
            if self._closed or self._busy or self._attempted == signature:
                return
            self._busy = True
            self._attempted = signature
            self._error = False

        def work():
            try:
                champion = self.reader.champion(cid)
                if self._client is None:
                    self._client = self._factory()
                recommendation = self._client.recommend(Query(champion['slug'], mode='arena'))
                self.catalog.bind_revision(recommendation.resolved['patch'])
                names = {}
                for field, catalog in [('augments', 'cherry-augments'), ('items', 'items')]:
                    try:
                        names[field] = self.catalog.names(catalog)
                    except Exception:
                        names[field] = {}
                prepared = cards(recommendation, champion['name'], names)
                with self._lock:
                    if not self._closed and self._desired == signature:
                        self._cards, self._complete = prepared, signature
            except Exception:
                with self._lock:
                    if self._desired == signature:
                        self._error = True
            finally:
                with self._lock:
                    self._busy = False
                    if self._closed and self._client is not None:
                        self._client.close()

        if not self._worker.submit(work, lambda error: None):
            with self._lock:
                self._busy = False
                self._error = True

    def view(self, key, cid):
        with self._lock:
            if self._complete == self._desired == (key, cid):
                return View(key, self._cards)
            error = self._error and self._desired == (key, cid)
            message = ('Não foi possível consultar Arena. Use Reconsultar Arena nas configurações.' if error
                       else 'Consultando popularidade de aprimoramentos e itens…')
            return View(key, (Card('Arena · ' + ('consulta indisponível' if error else 'carregando'), (message,)),))

    def clear(self):
        with self._lock:
            self._desired = self._complete = self._attempted = None
            self._cards = ()

    def retry(self):
        with self._lock:
            if self._closed or self._busy or self._clock() - self._last_retry < 30:
                return False
            self._attempted = None
            self._last_retry = self._clock()
            return True

    def close(self):
        with self._lock:
            self._closed = True
            self.clear()
        self._worker.close(timeout=.1)
        with self._lock:
            if not self._busy and self._client is not None:
                self._client.close()
