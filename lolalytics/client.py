"""Bounded collection, validated caches and per-client request coalescing."""
from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import threading
import time
from urllib.parse import urlencode

from .cache import FileCache
from .decoding import decode_page
from .errors import CollectorError, DataUnavailable, QueryError, SchemaError
from .parsing import parse_payload, sanitize_payload
from .query import Query
from .transport import HTTPTransport


def _reject_nonfinite(_):
    raise ValueError("non-finite JSON constant")


def _validate_item_sets(data):
    if not isinstance(data, dict) or not isinstance(data.get("itemSets"), dict):
        raise SchemaError("Lazy item sets: missing itemSets object")
    if not isinstance(data.get("response"), dict) or data["response"].get("valid") is not True:
        raise DataUnavailable("Lazy item sets: upstream did not confirm a valid response")
    for name, rows in data["itemSets"].items():
        if not isinstance(name, str) or not isinstance(rows, list):
            raise SchemaError("Lazy item sets: invalid table")
        for row in rows:
            if (not isinstance(row, list) or len(row) != 3 or not isinstance(row[0], str)
                    or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in row[1:])):
                raise SchemaError("Lazy item sets: unsupported row schema")


class Client:
    """A standalone client. No connection to LCU, Pengu or the game process.

    The disk cache is optional. Cached data expires after ``ttl`` seconds, even
    for explicit patches: historical data can still receive corrections. There
    is no implicit stale fallback. Batch calls are explicit and sequential.
    """

    def __init__(self, *, cache_dir=None, ttl=900, transport=None, clock=time.time):
        if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not math.isfinite(ttl) or not 0 <= ttl <= 86400:
            raise QueryError("ttl must be between 0 and 86400 seconds")
        self.ttl = ttl
        self._clock = clock
        self._transport = transport if transport is not None else HTTPTransport()
        self._disk = FileCache(cache_dir, clock=clock) if cache_dir is not None else None
        self._memory = OrderedDict()
        self._inflight = {}
        self._lock = threading.RLock()
        self._slots = threading.BoundedSemaphore(2)
        self._closed = False

    def _cached(self, key):
        with self._lock:
            def read(envelope):
                if envelope is None:
                    return None
                try:
                    age = self._clock() - envelope["stored_at"]
                    if not 0 <= age < self.ttl:
                        return None
                    return json.loads(envelope["value"], parse_constant=_reject_nonfinite)
                except (ValueError, UnicodeError, TypeError, KeyError, RecursionError):
                    return None

            value = read(self._memory.get(key))
            if value is not None:
                self._memory.move_to_end(key)
                return value
            self._memory.pop(key, None)
            # Another client may have refreshed the shared disk entry while our
            # in-memory copy expired. Corruption and expiration are both misses.
            if self._disk is not None:
                envelope = self._disk.get(key)
                value = read(envelope)
                if value is not None:
                    self._memory[key] = envelope
                    while len(self._memory) > 32:
                        self._memory.popitem(last=False)
                    return value
            return None

    def _remember(self, key, value):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(body) > 4 * 1024 * 1024 or self.ttl == 0:
            return
        with self._lock:
            self._memory[key] = {"stored_at": self._clock(), "value": body}
            self._memory.move_to_end(key)
            while len(self._memory) > 32:
                self._memory.popitem(last=False)
            if self._disk is not None:
                try:
                    self._disk.put(key, body)
                except OSError:
                    # A cache write cannot turn an otherwise valid collection into failure.
                    pass

    def _once(self, key, operation):
        with self._lock:
            if self._closed:
                raise CollectorError("LoLalytics client is closed")
            future = self._inflight.get(key)
            owner = future is None
            if owner:
                future = Future()
                self._inflight[key] = future
        if not owner:
            return deepcopy(future.result())
        try:
            with self._slots:
                result = operation()
            future.set_result(result)
            return deepcopy(result)
        except BaseException as error:
            future.set_exception(error)
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)

    def collect(self, query: Query):
        if not isinstance(query, Query):
            raise QueryError("collect expects a Query")

        def operation():
            cached = self._cached(query.key)
            if isinstance(cached, dict):
                try:
                    result = parse_payload(cached["nav"], cached["payload"], query, query.url, cached["collected_at"])
                    result.cache_hit = True
                    return result
                except (KeyError, TypeError, ValueError, CollectorError):
                    pass  # Cache content is revalidated; never trust a partial/corrupt record.
            body = self._transport.get(query.url)
            nav, payload = decode_page(body)
            collected_at = datetime.fromtimestamp(self._clock(), timezone.utc).isoformat()
            result = parse_payload(nav, payload, query, query.url, collected_at)
            # Persist only sanitized aggregate data, never the upstream Arena body.
            self._remember(query.key, {"nav": nav, "payload": sanitize_payload(payload, query.mode),
                                       "collected_at": collected_at})
            return result

        return self._once(query.key, operation)

    def collect_many(self, queries):
        """Collect up to 20 explicit queries; cached successes allow a rerun.

        Returns an iterator, so callers can persist each success before the next
        request. Errors propagate at the failing query without inventing a result.
        """
        bounded = []
        for query in queries:
            if len(bounded) == 20:
                raise QueryError("a batch is limited to 20 explicit queries")
            if not isinstance(query, Query):
                raise QueryError("batch entries must be Query instances")
            bounded.append(query)
        for query in bounded:
            yield self.collect(query)

    def collect_item_sets(self, query: Query) -> dict:
        """Opt-in lazy item sets. Counter columns retain their upstream meaning.

        No win rate is calculated from these counters. Only ranked's reproduced
        endpoint is exposed here; Arena's lazy counters remain unavailable.
        """
        if not isinstance(query, Query) or query.mode != "ranked":
            raise QueryError("lazy item sets currently support ranked only")
        base = self.collect(query)
        params = {"ep": "build-itemset", "v": 1, "patch": base.resolved["patch"],
                  "c": query.champion, "lane": query.lane, "tier": query.tier,
                  "queue": query.mode, "region": query.region}
        url = "https://a1.lolalytics.com/mega/?" + urlencode(params)

        def operation():
            cached = self._cached(url)
            if isinstance(cached, dict) and cached.get("source_url") == url and isinstance(cached.get("raw"), dict):
                try:
                    _validate_item_sets(cached["raw"])
                    cached["cache_hit"] = True
                    return cached
                except CollectorError:
                    pass
            try:
                data = json.loads(self._transport.get(url), parse_constant=_reject_nonfinite)
            except (ValueError, UnicodeError, RecursionError):
                raise SchemaError("Lazy item sets: expected JSON") from None
            _validate_item_sets(data)
            result = {"source_url": url, "query": query.to_dict(), "resolved": base.resolved,
                      "collected_at": datetime.fromtimestamp(self._clock(), timezone.utc).isoformat(),
                      "raw": data, "cache_hit": False, "stale": False,
                      "limitations": ["Counter columns are preserved without inferred metrics; not a full build ranking."]}
            self._remember(url, result)
            return result

        return self._once(url, operation)

    def close(self):
        with self._lock:
            self._closed = True
        self._transport.close()

    def __enter__(self):
        if self._closed:
            raise CollectorError("LoLalytics client is closed")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
