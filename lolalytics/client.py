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
from .builds import BuildCollection, BuildPage, build_page
from .matchups import build_matchup_page
from .recommendations import Recommendation, item_rankings, rune_candidates as get_rune_candidates
from .risk import BUILD_PRIOR_GAMES, rank_candidates, score_observation, validate_risk_level


def _reject_nonfinite(_):
    raise ValueError("non-finite JSON constant")


def _bounded_cache_depth(value):
    # Python 3.14 can decode deeper JSON than 3.12. Enforce our own limit
    # instead of relying on the interpreter's recursion limit for cache safety.
    stack = [iter((value,))]
    while stack:
        try:
            node = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        children = node.values() if isinstance(node, dict) else node if isinstance(node, list) else None
        if children is not None:
            if len(stack) > 128:
                return False
            stack.append(iter(children))
    return True


def _validate_item_sets(data):
    if not isinstance(data, dict) or not isinstance(data.get("itemSets"), dict):
        raise SchemaError("Lazy item sets: missing itemSets object")
    if not isinstance(data.get("response"), dict) or data["response"].get("valid") is not True:
        raise DataUnavailable("Lazy item sets: upstream did not confirm a valid response")
    for name, rows in data["itemSets"].items():
        if not isinstance(name, str) or not isinstance(rows, list):
            raise SchemaError("Lazy item sets: invalid table")
        for row in rows:
            if (
                not isinstance(row, list)
                or len(row) != 3
                or not isinstance(row[0], str)
                or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in row[1:])
            ):
                raise SchemaError("Lazy item sets: unsupported row schema")


class Client:
    """A standalone client. No connection to LCU, Pengu or the game process.

    The disk cache is optional. Cached data expires after ``ttl`` seconds, even
    for explicit patches: historical data can still receive corrections. There
    is no implicit stale fallback. Batch calls are explicit and sequential.
    """

    def __init__(self, *, cache_dir=None, ttl=900, transport=None, clock=time.time):
        if (
            isinstance(ttl, bool)
            or not isinstance(ttl, (int, float))
            or not math.isfinite(ttl)
            or not 0 <= ttl <= 86400
        ):
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
                    body = envelope["value"]
                    if not isinstance(body, bytes) or len(body) > 4 * 1024 * 1024:
                        return None
                    value = json.loads(body, parse_constant=_reject_nonfinite)
                    return value if _bounded_cache_depth(value) else None
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
            self._remember(
                query.key, {"nav": nav, "payload": sanitize_payload(payload, query.mode), "collected_at": collected_at}
            )
            return result

        return self._once(query.key, operation)

    @staticmethod
    def _summary_keystone(snapshot, selection):
        """Read the primary rune from one validated summary selection."""
        try:
            value = snapshot.raw["summary"][selection]["runes"]["set"]["pri"][0]
        except (KeyError, TypeError, IndexError):
            raise DataUnavailable(f"LoLalytics has no primary keystone for {selection}") from None
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SchemaError(f"LoLalytics returned an invalid {selection} keystone")
        return value

    def collect_builds(self, query: Query) -> BuildCollection:
        """Collect win and common builds conditioned on their primary keystone."""
        if not isinstance(query, Query):
            raise QueryError("collect_builds expects a Query")
        if getattr(query, "opponent", None) is not None:
            raise QueryError("collect_builds does not support opponent-filtered queries")
        if query.mode not in ("ranked", "aram", "swift"):
            raise QueryError("structured builds currently support ranked, ARAM and Swiftplay only")

        base = self.collect(query)
        if query.mode == "swift":
            return BuildCollection(
                query=query.to_dict(),
                pages=[
                    build_page(base, selection, self._summary_keystone(base, selection), conditioning="mode")
                    for selection in ("win", "pick")
                ],
            )
        if query.keystone is not None:
            pages = [build_page(base, selection, query.keystone) for selection in ("win", "pick")]
            return BuildCollection(query=query.to_dict(), pages=pages)

        selections = {name: self._summary_keystone(base, name) for name in ("win", "pick")}

        pinned_patch = base.resolved["patch"]
        pinned_lane = query.lane
        if query.mode == "ranked" and query.lane == "all":
            pinned_lane = base.resolved.get("effective_lane")
            if pinned_lane is None or pinned_lane == "all":
                raise DataUnavailable("LoLalytics did not resolve an effective ranked lane")
        filtered_query = Query(
            query.champion, mode=query.mode, patch=pinned_patch, lane=pinned_lane, tier=query.tier, region=query.region
        )
        snapshots = {}
        pages = []
        for selection in ("win", "pick"):
            keystone = selections[selection]
            if keystone not in snapshots:
                keyed_query = Query(
                    filtered_query.champion,
                    mode=filtered_query.mode,
                    patch=filtered_query.patch,
                    lane=filtered_query.lane,
                    tier=filtered_query.tier,
                    region=filtered_query.region,
                    keystone=keystone,
                )
                snapshots[keystone] = self.collect(keyed_query)
            pages.append(build_page(snapshots[keystone], selection, keystone))
        return BuildCollection(query=query.to_dict(), pages=pages)

    def collect_matchup(self, query: Query, *, min_games: int = 100, selection: str = "win") -> BuildPage:
        """Collect one validated ranked matchup suggestion for an explicit opponent."""
        if not isinstance(query, Query):
            raise QueryError("collect_matchup expects a Query")
        if query.mode != "ranked":
            raise QueryError("matchup collection currently supports ranked only")
        if getattr(query, "opponent", None) is None:
            raise QueryError("collect_matchup requires an opponent")
        if isinstance(min_games, bool) or not isinstance(min_games, int) or min_games < 0:
            raise QueryError("min_games must be a non-negative integer")
        if selection not in ("win", "pick"):
            raise QueryError("selection must be 'win' or 'pick'")
        return build_matchup_page(self.collect(query), min_games=min_games, selection=selection)

    def recommend(self, query: Query, *, risk_level: str = "medium") -> Recommendation:
        """Collect a bounded source snapshot and apply the local risk policy."""
        if not isinstance(query, Query):
            raise QueryError("recommend expects a Query")
        if query.mode == "swift":
            raise QueryError("Swiftplay supports collect_builds without keystone conditioning, not recommend")
        level = validate_risk_level(risk_level)
        # Input and policy validation happen above the first transport call.
        base = self.collect(query)
        if query.mode != "arena":
            # The baseline is essential to every local risk score, including
            # item tables and opponent-conditioned recommendations.
            baseline = base.overview.get("win_rate")
            if baseline is None:
                raise DataUnavailable("champion overview win rate is unavailable for recommendation")
            score_observation(None, None, baseline, level)
        arena = query.mode == "arena"
        policy = {
            "method": "pick_rate" if arena else "prior_weighted_mean",
            "prior_games": None if arena else BUILD_PRIOR_GAMES[level],
            "baseline": None if arena else base.overview.get("win_rate"),
            "baseline_source": None if arena else "champion_query_overview",
            "item_baseline": None,
            "item_baseline_source": None,
            "score_unit": None if arena else "percent",
            "not_calibrated": True,
        }
        warnings = list(base.warnings)
        if query.mode != "arena":
            warnings.extend(
                (
                    "rune_scope_primary_not_joint_page",
                    "only_two_upstream_layout_candidates",
                    "local_risk_not_draftgap_prediction",
                )
            )
        selected_page = None
        selected = None
        rune_candidates = []
        working = base

        if query.mode == "arena":
            warnings.append("risk_not_applicable_to_arena_popularity")
        elif query.opponent is not None:
            # Opponent-conditioned pages never add a keystone filter.
            rune_candidates = get_rune_candidates(base)
            ranked = rank_candidates(rune_candidates, baseline, level)
            winner = next((candidate for candidate in ranked if candidate["risk"]["score"] is not None), None)
            if winner is None:
                raise DataUnavailable("LoLalytics has no opponent summary with a usable primary-keystone sample")
            rune_candidates = ranked
            selected = winner["selection"]
            selected_page = build_matchup_page(base, selection=selected)
        else:
            rune_candidates = get_rune_candidates(base)
            if query.keystone is not None:
                rune_candidates = [c for c in rune_candidates if c["keystone"] == query.keystone]
                if not rune_candidates:
                    raise DataUnavailable("LoLalytics has no complete summary layout for the requested keystone")
            ranked = rank_candidates(rune_candidates, baseline, level)
            if not ranked or ranked[0]["risk"]["score"] is None:
                raise DataUnavailable("LoLalytics has no complete rune layout with an available keystone sample")
            rune_candidates = ranked
            winner = next((candidate for candidate in ranked if candidate["risk"]["score"] is not None), None)
            if winner is None:
                raise DataUnavailable("LoLalytics has no rune candidate with a usable sample")
            selected = winner["selection"]
            chosen_keystone = query.keystone if query.keystone is not None else winner["keystone"]
            if query.keystone is None:
                pinned_lane = query.lane
                if query.mode == "ranked" and pinned_lane == "all":
                    pinned_lane = base.resolved.get("effective_lane")
                    if pinned_lane is None or pinned_lane == "all":
                        raise DataUnavailable("LoLalytics did not resolve an effective ranked lane")
                filtered = Query(
                    query.champion,
                    mode=query.mode,
                    patch=base.resolved["patch"],
                    lane=pinned_lane,
                    tier=query.tier,
                    region=query.region,
                    keystone=chosen_keystone,
                )
                working = self.collect(filtered)
            selected_page = build_page(working, selected, chosen_keystone)
            source_layout = winner["runes"]
            if any(source_layout.get(slot) != selected_page.runes.get(slot) for slot in ("pri", "sec", "mod")):
                warnings.append("selected_keystone_then_refresh_layout")

        if selected_page is not None:
            warnings.extend(selected_page.warnings)
        item_baseline = None
        if not arena:
            item_baseline = working.overview.get("win_rate")
            if item_baseline is None:
                raise DataUnavailable("item snapshot champion overview win rate is unavailable for recommendation")
            score_observation(None, None, item_baseline, level)
            policy["item_baseline"] = item_baseline
            policy["item_baseline_source"] = "item_source.champion_query_overview"
        item_rankings_result = item_rankings(working, item_baseline, level)
        item_source = {
            "source_url": working.source_url,
            "query": deepcopy(working.query),
            "resolved": deepcopy(working.resolved),
            "collected_at": working.collected_at,
            "cache_hit": bool(working.cache_hit),
        }
        return Recommendation(
            query=query.to_dict(),
            resolved=deepcopy(base.resolved),
            source_url=base.source_url,
            collected_at=base.collected_at,
            cache_hit=bool(base.cache_hit and working.cache_hit),
            risk_level=level,
            policy=policy,
            rune_candidates=rune_candidates,
            recommended_selection=selected,
            build_page=selected_page,
            item_source=item_source,
            item_rankings=item_rankings_result,
            warnings=list(dict.fromkeys(warnings)),
        )

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
        if query.keystone is not None:
            raise QueryError("lazy item sets do not support keystone-filtered queries")
        if getattr(query, "opponent", None) is not None:
            raise QueryError("lazy item sets do not support opponent-filtered queries")
        base = self.collect(query)
        params = {
            "ep": "build-itemset",
            "v": 1,
            "patch": base.resolved["patch"],
            "c": query.champion,
            "lane": query.lane,
            "tier": query.tier,
            "queue": query.mode,
            "region": query.region,
        }
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
            result = {
                "source_url": url,
                "query": query.to_dict(),
                "resolved": base.resolved,
                "collected_at": datetime.fromtimestamp(self._clock(), timezone.utc).isoformat(),
                "raw": data,
                "cache_hit": False,
                "stale": False,
                "limitations": ["Counter columns are preserved without inferred metrics; not a full build ranking."],
            }
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
