"""Draft-scoped recommendation orchestration; no UI or game mutations."""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import replace
import hashlib
import logging
import threading
import uuid

from lolalytics import Query
from lolalytics.builds import build_page
from lolalytics.errors import CollectorError
from lolalytics.risk import validate_risk_level

from .draft import BuildError, DraftReader, positive
from .settings import get_risk_level

log = logging.getLogger(__name__)


class BuildService:
    def __init__(self, lcu, collector, *, risk=get_risk_level, overlay=None, item_plans=None):
        self.reader = DraftReader(lcu)
        self.collector = collector
        self.risk = risk
        self.overlay = overlay
        self.item_plans = item_plans
        self._lock = threading.RLock()
        self._context_lock = threading.Lock()
        self._revision = None
        self._generation = 0
        self._result_id = None
        self._pages = OrderedDict()
        self._filter = None
        self._closed = False

    def invalidate(self):
        with self._lock:
            self._generation += 1
            self._result_id = None
            self._pages.clear()

    def context(self):
        # Keep observation + publication ordered across the fast and query workers.
        with self._context_lock:
            return self._read_context()

    def _read_context(self):
        try:
            draft = self.reader.read()
            level = validate_risk_level(self.risk())
        except Exception:
            self.invalidate()
            raise
        revision = hashlib.sha256((draft.revision + level).encode()).hexdigest()[:24]
        with self._lock:
            if self._closed:
                raise BuildError('O serviço de builds foi encerrado.')
            if revision != self._revision:
                self.invalidate()
                if self.overlay is not None and draft.phase == 'ChampSelect':
                    self.overlay.clear()
                self._revision = revision
                self._filter = None
        result = draft.to_dict()
        result.update(revision=revision, riskLevel=level, champion=None,
                      available=draft.phase == 'ChampSelect' and bool(draft.champion_id) and draft.game_key is not None
                      and draft.mode in ('ranked', 'aram'))
        if draft.champion_id:
            result['champion'] = self.reader.champion(draft.champion_id)
        result['enemies'] = [dict(self.reader.champion(cid), lane=position) for cid, position in draft.enemies]
        return result

    def begin_query(self):
        # Called before queueing: a new intent invalidates in-flight/visible results.
        with self._lock:
            self._generation += 1
            self._result_id = None
            return self._generation

    def _current(self, ticket, revision):
        context = self.context()
        with self._lock:
            if ticket != self._generation or revision != self._revision:
                raise BuildError('A seleção mudou. Consulte novamente antes de importar.')
        if not context['available']:
            if context['mode'] == 'arena':
                raise BuildError('Este painel não é usado na seleção de Arena.')
            raise BuildError('Escolha um campeão em um modo compatível antes de consultar.')
        return context

    def query(self, payload, ticket):
        context = self._current(ticket, payload.get('revision'))
        selection = payload.get('selection', 'general')
        if selection not in ('general', 'matchup'):
            raise BuildError('Tipo de recomendação inválido.')
        position = payload.get('lane') or (context['lane'] if context['mode'] == 'ranked' else 'all')
        opponent = None
        if selection == 'matchup':
            if context['mode'] != 'ranked' or not context['finalization']:
                raise BuildError('Matchup disponível após o draft, em Summoner’s Rift.')
            cid = payload.get('opponentId')
            opponent = next((p for p in context['enemies'] if positive(cid) and p['id'] == cid), None)
            if opponent is None:
                raise BuildError('Selecione um adversário deste draft.')
        query = Query(context['champion']['slug'], mode=context['mode'], lane=position,
                      tier=payload.get('tier', 'emerald_plus'), region='all',
                      opponent=opponent['slug'] if opponent else None,
                      opponent_lane=opponent['lane'] if opponent else 'all')
        signature = (query.champion, query.mode, query.lane, query.tier, context['riskLevel'])
        try:
            recommendation = self.collector.recommend(query, risk_level=context['riskLevel'])
            self._current(ticket, payload.get('revision'))
            entries = OrderedDict()
            page = recommendation.build_page
            if page is None:
                raise BuildError('A fonte não retornou uma página completa.')
            winner = recommendation.rune_candidates[0]
            key = 'vs:' + str(opponent['id']) if opponent else 'wr'
            entries[key] = {'page': page, 'label': 'vs ' + opponent['name'] if opponent else 'WR · risco',
                            'rune_metrics': winner['metrics'], 'policy': recommendation.policy}
            if not opponent:
                common = next((r for r in recommendation.rune_candidates if r['selection'] == 'pick'), None)
                if common is None:
                    raise BuildError('A fonte não retornou a sugestão Common completa.')
                filtered = replace(query, patch=recommendation.resolved['patch'],
                                   lane=page.query['lane'], keystone=common['keystone'])
                common_page = build_page(self.collector.collect(filtered), 'pick', common['keystone'])
                entries['common'] = {'page': common_page, 'label': 'Common',
                                     'rune_metrics': common['metrics'], 'policy': recommendation.policy}
        except CollectorError as error:
            raise BuildError(str(error)) from None
        self._current(ticket, payload.get('revision'))
        with self._lock:
            if ticket != self._generation or payload.get('revision') != self._revision or self._closed:
                raise BuildError('A seleção mudou durante a consulta.')
            if signature != self._filter:
                self._pages.clear()
                self._filter = signature
            # Never pack results from different upstream patches/roles together.
            if entries and self._pages:
                previous = next(iter(self._pages.values()))['page']
                incoming = next(iter(entries.values()))['page']
                if (previous.resolved.get('patch'), previous.resolved.get('effective_lane')) != (
                        incoming.resolved.get('patch'), incoming.resolved.get('effective_lane')):
                    self._pages.clear()
            for key, value in entries.items():
                self._pages[key] = value
                self._pages.move_to_end(key)
            # WR + Common + at most two opponent preparations, all explicitly requested.
            while sum(k.startswith('vs:') for k in self._pages) > 2:
                self._pages.pop(next(k for k in self._pages if k.startswith('vs:')))
            self._result_id = uuid.uuid4().hex
            result = {'revision': self._revision, 'resultId': self._result_id,
                    'riskLevel': context['riskLevel'], 'arena': None,
                    'entries': [dict(id=key, label=value['label'], page=value['page'].to_dict(),
                                     runeMetrics=deepcopy(value['rune_metrics']),
                                     runeMetricScope='keystone_observation', policy=deepcopy(value['policy']))
                                for key, value in self._pages.items()],
                    'warnings': recommendation.warnings}
            if self.item_plans is not None:
                self.item_plans.prepare(context, [v['page'] for v in self._pages.values()])
            if self.overlay is not None:
                try:
                    self.overlay.prepare(context, result, selected_id='vs:' + str(opponent['id']) if opponent else 'wr')
                except Exception:
                    log.warning('Não foi possível preparar a visualização em partida; consulta preservada.')
            return result

    def select_overlay(self, payload):
        """Select only a prepared result from this draft, never accept page data."""
        context = self.context()
        with self._lock:
            if (not context['available'] or payload.get('revision') != self._revision
                    or payload.get('resultId') != self._result_id
                    or payload.get('entryId') not in self._pages):
                raise BuildError('Esta recomendação expirou. Consulte novamente.')
            if self.overlay is not None:
                self.overlay.select(self._result_id, payload['entryId'])
        return {'selected': True}

    def import_selection(self, payload, importer):
        result_id, entry_id = payload.get('resultId'), payload.get('entryId')
        revision = payload.get('revision')

        def guard():
            context = self.context()
            with self._lock:
                if (not result_id or result_id != self._result_id or revision != self._revision
                        or not context['available'] or entry_id not in self._pages):
                    raise BuildError('Esta recomendação expirou. Consulte novamente.')
            return context

        context = guard()
        with self._lock:
            selected = deepcopy(self._pages[entry_id]['page'])
            pages = [deepcopy(v['page']) for v in self._pages.values()]
        target = payload.get('target')
        if target not in ('runes', 'items'):
            raise BuildError('Escolha importar runas ou itens.')
        return importer.apply(target, selected, pages, context['champion_id'], guard=guard)

    def stop(self):
        with self._lock:
            self._closed = True
            self.invalidate()

    def close(self):
        self.stop()
        self.collector.close()
