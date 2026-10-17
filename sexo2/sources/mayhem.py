"""Public aramkit community cache; Mayhem data never substitutes Arena/ARAM data."""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import re
import time

import requests
from lolalytics.cache import FileCache
from lolalytics.transport import HTTPTransport
from lolalytics.errors import SchemaError, TransportError
from lolalytics.builds import BuildPage, ItemBlock, ItemChoice

BASE = 'https://mayhemcache.drawyoursword.lol'
RARITIES = ('silver', 'gold', 'prismatic')


class MayhemTransport(HTTPTransport):
    @staticmethod
    def validate_url(url):
        if not isinstance(url, str) or not re.fullmatch(
            re.escape(BASE) + r'/v1/(champion\?champion=[1-9][0-9]{0,4}|pool\?champion=[1-9][0-9]{0,4}&rarity=(silver|gold|prismatic))', url):
            raise TransportError('URL outside the public Mayhem source endpoints')


def _invalid_constant(value):
    raise ValueError('Non-finite JSON constant')


def _number(value, limit):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= limit


def _metrics(row):
    rate, games = row.get('pickRate'), row.get('sampleCount')
    if not _number(rate, 1) or type(games) is not int or games < 0:
        raise SchemaError('Mayhem source returned invalid popularity metrics')
    return {'pick_rate': round(rate * 100, 4), 'games': games, 'win_rate': None}


def _meta(data, cid):
    if (not isinstance(data, dict) or not isinstance(data.get('champion'), dict)
            or type(data['champion'].get('id')) is not int or data['champion']['id'] != cid
            or not isinstance(data.get('patch'), str) or not re.fullmatch(r'\d{2}\.\d{1,2}', data['patch'])
            or not isinstance(data.get('dataDate'), str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', data['dataDate'])):
        raise SchemaError('Mayhem source identity, patch or date changed')
    return data['patch'], data['dataDate']


@dataclass
class Pools:
    patch: str
    data_date: str
    metrics: dict
    cache_hit: bool = False


def parse_pool(data, cid, rarity):
    patch, date = _meta(data, cid)
    if data.get('stage', 'missing') is not None or data.get('rarity') != rarity:
        raise SchemaError('Mayhem pool must be pooled across stages and match its rarity')
    rows = data.get('augments')
    if not isinstance(rows, list) or not rows or len(rows) > 1000:
        raise SchemaError('Mayhem augment pool changed')
    metrics = {}; seen = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] <= 0:
            raise SchemaError('Mayhem source returned invalid augment IDs')
        identifier = str(row['id'])
        if identifier in seen:
            raise SchemaError('Mayhem source returned duplicate augment IDs')
        seen.add(identifier)
        if row.get('source') == 'champion':
            metrics[identifier] = _metrics(row)
        elif row.get('source') not in ('none', 'global'):
            raise SchemaError('Mayhem pooled source scope changed')
        # Never present a global fallback as this champion's popularity.
    return Pools(patch, date, metrics)


def _choices(ids):
    if not isinstance(ids, list) or not ids or len(ids) > 16 or any(type(i) is not int or not 0 < i < 1_000_000 for i in ids):
        raise SchemaError('Mayhem item IDs changed')
    return [ItemChoice(str(i), count, {}, {}) for i, count in Counter(ids).items()]


def build_pages(data, cid, slug, name, *, cache_hit=False, collected_at=''):
    patch, date = _meta(data, cid)
    rows = data.get('archetypes')
    if not isinstance(rows, list) or not rows or len(rows) > 20:
        raise SchemaError('Mayhem item archetypes are unavailable')
    if any(not isinstance(r, dict) or type(r.get('rank')) is not int or r['rank'] <= 0 for r in rows):
        raise SchemaError('Mayhem item archetype rank changed')
    pages = []
    for row in sorted(rows, key=lambda r: r['rank'])[:2]:
        key = row.get('key')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z0-9_]{1,32}', key):
            raise SchemaError('Mayhem item archetype key changed')
        blocks = []
        starters = row.get('starters')
        if not isinstance(starters, list) or len(starters) > 8:
            raise SchemaError('Mayhem starting items changed')
        for start in starters[:3]:
            if not isinstance(start, dict): raise SchemaError('Mayhem starting item combination changed')
            blocks.append(ItemBlock('starting', _choices(start.get('items')), _metrics(start),
                                    'archetypes.'+key+'.starters', True))
        blocks.append(ItemBlock('suggested_core', _choices(row.get('core')), {},
                                'archetypes.'+key+'.core', False))
        for field, kind in [('boots', 'boots'), ('situational', 'situational')]:
            values = row.get(field)
            if not isinstance(values, list) or len(values) > 16:
                raise SchemaError('Mayhem item alternatives changed')
            choices = []
            for value in values:
                if not isinstance(value, dict): raise SchemaError('Mayhem item alternative changed')
                choice = _choices([value.get('id')])[0]
                choice.metrics = _metrics(value)
                choices.append(choice)
            if choices:
                blocks.append(ItemBlock(kind, choices, {}, 'archetypes.'+key+'.'+field, False))
        query = {'champion': slug, 'mode': 'mayhem', 'patch': patch, 'lane': 'all', 'tier': 'all', 'region': 'all'}
        resolved = dict(query, cid=cid, champion_name=name)
        label = 'Mayhem · ' + key.upper()
        pages.append(BuildPage('archetype', label, label, 0, {}, blocks, {},
            BASE+'/v1/champion?champion='+str(cid), query, resolved, collected_at, cache_hit,
            ['archetype_core_order_unconfirmed', 'source_aramkit_community_cache'], conditioning='archetype'))
    return pages


class MayhemClient:
    def __init__(self, *, transport=None, cache_dir=None, clock=time.time):
        if transport is None:
            session = requests.Session()
            session.headers['User-Agent'] = 'SEXO2/2.0 personal companion'
            transport = MayhemTransport(session=session, timeout=(3, 8), max_wait=10, attempts=2)
        self.transport, self.clock = transport, clock
        self.cache = FileCache(cache_dir, ttl=3600, clock=clock) if cache_dir is not None else None

    def _get(self, url, parse):
        cached = self.cache.get(url) if self.cache is not None else None
        if cached and 0 <= self.clock()-cached['stored_at'] < 3600:
            try:
                return parse(json.loads(cached['value'], parse_constant=_invalid_constant)), True, cached['stored_at']
            except (SchemaError, ValueError, KeyError, TypeError, RecursionError):
                pass
        body = self.transport.get(url)
        if len(body) > 4*1024*1024:
            raise SchemaError('Mayhem response exceeds limit')
        try:
            value = parse(json.loads(body, parse_constant=_invalid_constant))
        except (SchemaError, ValueError, KeyError, TypeError, RecursionError):
            raise SchemaError('Mayhem response schema changed') from None
        if self.cache is not None:self.cache.put(url, body)
        return value, False, self.clock()

    def pools(self, cid):
        if type(cid) is not int or not 0 < cid < 100000:
            raise SchemaError('Invalid Mayhem champion ID')
        result = None
        all_cached = True
        for rarity in RARITIES:
            url = BASE+f'/v1/pool?champion={cid}&rarity={rarity}'
            pool, cached, _ = self._get(url, lambda data:parse_pool(data,cid,rarity))
            all_cached &= cached
            if result is None:result = pool
            elif (pool.patch, pool.data_date) != (result.patch, result.data_date):
                raise SchemaError('Mayhem pools have different data versions')
            else:
                if result.metrics.keys() & pool.metrics.keys():raise SchemaError('Mayhem augment IDs conflict across rarities')
                result.metrics.update(pool.metrics)
        result.cache_hit = all_cached
        return result

    def builds(self, cid, slug, name):
        if type(cid) is not int or not 0 < cid < 100000:
            raise SchemaError('Invalid Mayhem champion ID')
        url = BASE+f'/v1/champion?champion={cid}'
        collected = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat()
        pages, cached, at = self._get(url, lambda data:build_pages(data,cid,slug,name,collected_at=collected))
        for page in pages:
            page.cache_hit=cached
            page.collected_at=datetime.fromtimestamp(at, timezone.utc).isoformat()
        return pages

    def close(self):
        self.transport.close()
