"""Bounded, non-personal draft projections retained only for the same match."""
from copy import deepcopy
from dataclasses import dataclass
import re
import threading
import time
import unicodedata


def text(value, limit=120):
    return ''.join(c for c in str(value) if not unicodedata.category(c).startswith('C'))[:limit]


@dataclass(frozen=True)
class Card:
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class View:
    key: str
    cards: tuple[Card, ...]
    selected: int = 0


def _cards(context, result):
    """Only allowlisted presentation fields; no raw responses or account data."""
    items, runes = result.get('itemNames', {}), result.get('runeNames', {})
    cards = []
    for row in result['entries'][:4]:
        page = row['page']
        query, resolved = page['query'], page['resolved']
        title = text(context['champion']['name'], 60) + ' · ' + text(row['label'], 60)
        risk = {'very-low': 'muito baixo', 'low': 'baixo', 'medium': 'médio', 'high': 'alto', 'very-high': 'muito alto'}
        lines = [f"Patch {text(resolved.get('patch', '—'), 12)} · {text(query.get('lane', 'all'), 12)} · {text(query.get('tier', '—'), 24)}",
                 'Risco: ' + risk.get(result['riskLevel'], 'indisponível')]
        metric = row.get('runeMetrics', {})
        wr, games = metric.get('win_rate'), metric.get('games')
        lines.append(f"Runa principal: {wr if wr is not None else '—'}% · {games if games is not None else '—'} jogos")
        for key, label in [('pri', 'Primárias'), ('sec', 'Secundárias'), ('mod', 'Fragmentos')]:
            names = [text(runes.get(str(i), i), 65) for i in page['runes'].get(key, [])[:4]]
            lines.append(label + ': ' + ' · '.join(names))
        for block in page['blocks'][:8]:
            kind = block['kind']
            label = {'starting': 'Iniciais', 'core': 'Core (conjunto observado)'}.get(kind, kind.replace('item', 'Item '))
            names = [text(items.get(str(c['identifier']), c['identifier']), 65) +
                     (f" ×{c['count']}" if c['count'] > 1 else '') for c in block['choices']]
            lines.append(label + ': ' + (' → ' if kind == 'core' else ' + ' if block['ordered'] else ' / ').join(names))
            if block.get('more'):
                lines.append('Outras alternativas estão no conjunto importado.')
        lines.extend(('Itens 4–6: alternativas individuais.', 'WR da primária; sem WR conjunta das nove runas.'))
        if page.get('conditioning') == 'opponent':
            lines.append('Itens por adversário; filtro conjunto com runa indisponível.')
        if page.get('warnings') or result.get('warnings'):
            lines.append('Há limitações na fonte; consulte os avisos da seleção.')
        lines.append('Coleta: ' + text(page.get('collected_at', '—'), 32) + (' · cache' if page.get('cache_hit') else ''))
        # No URLs from arbitrary payload fields: source is the collector's fixed host.
        lines.append('Fonte: LoLalytics · dados preparados na seleção')
        cards.append(Card(title, tuple(lines)))
    return tuple(cards)


class OverlayStore:
    """No disk/network I/O. All operations are small and protected by one lock."""
    def __init__(self, *, clock=time.monotonic):
        self._lock = threading.RLock()
        self._clock = clock
        self._data = None
        self._closed = False

    def clear(self):
        with self._lock:
            self._data = None

    def close(self):
        with self._lock:
            self._closed = True
            self._data = None

    def prepare(self, context, result, *, selected_id=None):
        key = context.get('game_key')
        if (context.get('phase') != 'ChampSelect' or context.get('mode') not in ('ranked', 'aram')
                or not isinstance(key, str) or not re.fullmatch('[a-f0-9]{24}', key)):
            return
        # Retain only presentation fields, never the raw response or account data.
        projected = {key: deepcopy(result[key]) for key in ('revision', 'resultId', 'riskLevel')}
        projected['warnings'] = bool(result.get('warnings'))
        projected['entries'] = []
        for row in result['entries'][:4]:
            original = row['page']
            page = {key: deepcopy(original.get(key)) for key in
                    ('query', 'resolved', 'runes', 'conditioning', 'collected_at', 'cache_hit')}
            page['warnings'] = bool(original.get('warnings'))
            page['blocks'] = []
            for block in original['blocks'][:8]:
                limit = 16 if block['ordered'] else 3
                if block['ordered'] and len(block['choices']) > limit:
                    raise ValueError('Observed item combination exceeds presentation limit')
                page['blocks'].append({'kind': block['kind'], 'ordered': block['ordered'],
                                      'more': len(block['choices']) > limit,
                                      'choices': [{'identifier': c['identifier'], 'count': c['count']}
                                                  for c in block['choices'][:limit]]})
            projected['entries'].append({'id': row['id'], 'label': row['label'],
                                         'runeMetrics': deepcopy(row.get('runeMetrics', {})), 'page': page})
        safe_context = {'champion': {'name': context['champion']['name']}}
        cards = _cards(safe_context, projected)
        if not cards:
            return
        with self._lock:
            if self._closed:
                return
            self._data = {'key': key, 'mode': context['mode'], 'revision': result['revision'],
                          'champion_id': context['champion_id'],
                          'result_id': result['resultId'], 'context': safe_context,
                          'result': projected, 'cards': cards, 'selected': 0,
                          'at': self._clock()}
            if selected_id is not None:
                self.select(result['resultId'], selected_id)

    def enrich(self, result):
        with self._lock:
            data = self._data
            if data is None or result.get('resultId') != data['result_id']:
                return
            for field in ('itemNames', 'runeNames'):
                pages = [row['page'] for row in data['result']['entries']]
                if field == 'itemNames':
                    ids = {str(c['identifier']) for p in pages for b in p['blocks'] for c in b['choices']}
                else:
                    ids = {str(i) for p in pages for v in p['runes'].values() for i in v}
                names = result.get(field, {})
                data['result'][field] = {i: text(names[i], 65) for i in ids if i in names}
            data['cards'] = _cards(data['context'], data['result'])

    def select(self, result_id, entry_id):
        with self._lock:
            data = self._data
            if data is None or result_id != data['result_id']:
                return False
            ids = [row['id'] for row in data['result']['entries']]
            if entry_id not in ids:
                return False
            data['selected'] = ids.index(entry_id)
            return True

    def observe(self, phase, key, mode):
        """Failed observations hide in the controller; confirmed exits clear here."""
        with self._lock:
            if self._data and (phase not in ('ChampSelect', 'GameStart', 'InProgress', 'Reconnect')
                    or mode not in ('ranked', 'aram') or key != self._data['key']
                    or mode != self._data['mode']
                    or self._clock() - self._data['at'] > 6 * 3600):
                self._data = None

    def verify_champion(self, champion_id):
        """The existing champion monitor can invalidate a late trade at handoff."""
        with self._lock:
            if (type(champion_id) is int and champion_id > 0 and self._data
                    and champion_id != self._data['champion_id']):
                self._data = None

    def view(self, key, mode):
        with self._lock:
            data = self._data
            if (data is None or data['key'] != key or data['mode'] != mode
                    or self._clock() - data['at'] > 6 * 3600):
                return View(key or '', ())
            return View(key, data['cards'], data['selected'])
