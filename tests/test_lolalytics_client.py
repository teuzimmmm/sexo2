"""Deterministic Client tests using only sanitized, checked-in JSON fixtures."""
import base64
import json
from pathlib import Path
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.parse import urlencode

from lolalytics.client import Client
from lolalytics.errors import DataUnavailable, HTTPStatusError, QueryError, SchemaError
from lolalytics.query import Query

FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def entry(name):
    return next(item for item in MANIFEST if item["fixture"] == name)


def query_for(name):
    return Query(**entry(name)["filters"])


class FixtureTransport:
    def __init__(self, fixture_names=(), *, errors=None, before_return=None):
        self.bodies = {
            Query(**entry(name)["filters"]).url: (FIXTURES / name).read_bytes()
            for name in fixture_names
        }
        self.errors = errors or {}
        self.before_return = before_return
        self.calls = []
        self.lock = threading.Lock()

    def get(self, url):
        with self.lock:
            self.calls.append(url)
        if self.before_return:
            self.before_return(url)
        if url in self.errors:
            raise self.errors[url]
        if url not in self.bodies:
            raise AssertionError(f"unexpected offline URL: {url}")
        return self.bodies[url]

    def close(self):
        pass


def fixture_with_patch(name, patch_value):
    """Make a coherent test-only fixture variant by changing all literal patch fields."""
    document = json.loads((FIXTURES / name).read_bytes())

    def replace(value):
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        if isinstance(value, str):
            return value.replace("16.20", patch_value)
        return value

    return json.dumps(replace(document), separators=(",", ":")).encode()


def lazy_itemsets_url(query, patch="16.20"):
    params = {
        "ep": "build-itemset", "v": 1, "patch": patch,
        "c": query.champion, "lane": query.lane, "tier": query.tier,
        "queue": query.mode, "region": query.region,
    }
    return "https://a1.lolalytics.com/mega/?" + urlencode(params)


def add_deep_json_member(encoded, name="deep"):
    """Append JSON nesting beyond Python's decoder recursion limit without re-encoding."""
    depth = "[" * 12000 + "0" + "]" * 12000
    return encoded[:-1] + b',"' + name.encode() + b'":' + depth.encode() + b'}'


class MutableClock:
    def __init__(self, value=1000.0):
        self.value = value

    def __call__(self):
        return self.value


class ClientCacheTests(unittest.TestCase):
    def test_memory_cache_hit_and_expiry_failure_has_no_stale_fallback(self):
        clock = MutableClock()
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",), errors={})
        client = Client(ttl=5, transport=transport, clock=clock)
        first = client.collect(q)
        second = client.collect(q)
        self.assertEqual(len(transport.calls), 1)
        self.assertFalse(first.cache_hit)
        self.assertTrue(second.cache_hit)
        clock.value += 5
        transport.errors[q.url] = HTTPStatusError(503)
        with self.assertRaises(HTTPStatusError):
            client.collect(q)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_ttl_zero_disables_cache(self):
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",))
        client = Client(ttl=0, transport=transport)
        first = client.collect(q)
        second = client.collect(q)
        self.assertFalse(first.cache_hit)
        self.assertFalse(second.cache_hit)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_patch_and_mode_queries_have_separate_cache_entries(self):
        old = query_for("ahri-ranked-16.19-br-gold.json")
        current = query_for("ahri-ranked.json")
        aram = query_for("jinx-aram.json")
        arena = query_for("jinx-arena.json")
        transport = FixtureTransport(("ahri-ranked-16.19-br-gold.json", "ahri-ranked.json", "jinx-aram.json", "jinx-arena.json"))
        client = Client(transport=transport)
        for q in (old, current, aram, arena, old, current, aram, arena):
            client.collect(q)
        self.assertEqual(len(transport.calls), 4)
        self.assertEqual(len(set(transport.calls)), 4)
        client.close()

    def test_current_patch_cache_expiry_resolves_again_without_mixing_old_patch(self):
        clock = MutableClock()
        q = Query("ahri")  # No explicit patch: each miss resolves the current upstream patch.
        transport = FixtureTransport(("ahri-ranked.json",))
        transport.bodies[q.url] = (FIXTURES / "ahri-ranked.json").read_bytes()
        client = Client(ttl=2, transport=transport, clock=clock)
        first = client.collect(q)
        self.assertEqual(first.resolved["patch"], "16.20")
        clock.value += 2
        transport.bodies[q.url] = fixture_with_patch("ahri-ranked.json", "16.21")
        second = client.collect(q)
        self.assertEqual(second.resolved["patch"], "16.21")
        self.assertFalse(second.cache_hit)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_explicit_patch_cache_entries_are_distinct_with_identical_other_filters(self):
        first_query = Query("ahri", patch="16.20")
        second_query = Query("ahri", patch="16.21")
        transport = FixtureTransport(("ahri-ranked.json",))
        transport.bodies[first_query.url] = (FIXTURES / "ahri-ranked.json").read_bytes()
        transport.bodies[second_query.url] = fixture_with_patch("ahri-ranked.json", "16.21")
        client = Client(transport=transport)
        first = client.collect(first_query)
        second = client.collect(second_query)
        self.assertEqual(first.resolved["patch"], "16.20")
        self.assertEqual(second.resolved["patch"], "16.21")
        self.assertEqual(first.query["lane"], second.query["lane"])
        self.assertEqual(first.query["tier"], second.query["tier"])
        self.assertEqual(first.query["region"], second.query["region"])
        self.assertNotEqual(first_query.key, second_query.key)
        self.assertEqual(len(transport.calls), 2)
        self.assertTrue(client.collect(first_query).cache_hit)
        self.assertTrue(client.collect(second_query).cache_hit)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_semantically_corrupt_memory_cache_is_reparsed_and_refetched(self):
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",))
        client = Client(transport=transport)
        client.collect(q)
        cached = json.loads(client._memory[q.key]["value"])
        cached["payload"]["header"]["cid"] += 1000
        client._memory[q.key]["value"] = json.dumps(cached).encode()
        result = client.collect(q)
        self.assertFalse(result.cache_hit)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_disk_cache_is_shared_across_client_instances_without_second_network_call(self):
        q = query_for("ahri-ranked.json")
        with tempfile.TemporaryDirectory() as tmp:
            first_transport = FixtureTransport(("ahri-ranked.json",))
            first_client = Client(cache_dir=tmp, transport=first_transport)
            first_client.collect(q)
            first_client.close()

            second_transport = FixtureTransport(errors={q.url: HTTPStatusError(503)})
            second_client = Client(cache_dir=tmp, transport=second_transport)
            cached = second_client.collect(q)
            self.assertTrue(cached.cache_hit)
            self.assertEqual(second_transport.calls, [])
            second_client.close()

    def test_shared_disk_refresh_replaces_expired_memory_copy_in_older_client(self):
        q = Query("ahri")
        clock = MutableClock(1000)
        with tempfile.TemporaryDirectory() as tmp:
            transport_a = FixtureTransport(("ahri-ranked.json",))
            transport_a.bodies[q.url] = (FIXTURES / "ahri-ranked.json").read_bytes()
            client_a = Client(cache_dir=tmp, ttl=5, transport=transport_a, clock=clock)
            first_a = client_a.collect(q)
            self.assertEqual(first_a.resolved["patch"], "16.20")

            clock.value = 1005
            transport_b = FixtureTransport()
            transport_b.bodies[q.url] = fixture_with_patch("ahri-ranked.json", "16.21")
            client_b = Client(cache_dir=tmp, ttl=5, transport=transport_b, clock=clock)
            refreshed_b = client_b.collect(q)
            self.assertEqual(refreshed_b.resolved["patch"], "16.21")
            self.assertEqual(len(transport_b.calls), 1)

            clock.value = 1006
            refreshed_a = client_a.collect(q)
            self.assertTrue(refreshed_a.cache_hit)
            self.assertEqual(refreshed_a.resolved["patch"], "16.21")
            self.assertEqual(len(transport_a.calls), 1)
            client_b.close()
            client_a.close()

    def test_deeply_nested_memory_cache_is_a_miss_and_refetches(self):
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",))
        client = Client(transport=transport)
        client.collect(q)
        client._memory[q.key]["value"] = add_deep_json_member(client._memory[q.key]["value"])
        result = client.collect(q)
        self.assertFalse(result.cache_hit)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_deeply_nested_disk_envelope_is_a_miss_and_refetches(self):
        q = query_for("ahri-ranked.json")
        with tempfile.TemporaryDirectory() as tmp:
            initial_transport = FixtureTransport(("ahri-ranked.json",))
            initial = Client(cache_dir=tmp, transport=initial_transport)
            initial.collect(q)
            initial.close()

            cache_path = next(Path(tmp).glob("*.json"))
            envelope = json.loads(cache_path.read_text())
            value = base64.b64decode(envelope["value"])
            envelope["value"] = base64.b64encode(add_deep_json_member(value)).decode("ascii")
            cache_path.write_text(json.dumps(envelope, separators=(",", ":")))

            refresh_transport = FixtureTransport(("ahri-ranked.json",))
            refresh = Client(cache_dir=tmp, transport=refresh_transport)
            result = refresh.collect(q)
            self.assertFalse(result.cache_hit)
            self.assertEqual(len(refresh_transport.calls), 1)
            refresh.close()

    def test_cached_snapshots_do_not_share_mutable_objects(self):
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",))
        client = Client(transport=transport)
        first = client.collect(q)
        original_games = first.overview["games"]
        original_raw_keys = set(first.raw)
        first.overview["games"] = -123
        first.raw.clear()
        first.records[0].metrics["games"] = -1
        second = client.collect(q)
        self.assertTrue(second.cache_hit)
        self.assertEqual(second.overview["games"], original_games)
        self.assertEqual(set(second.raw), original_raw_keys)
        self.assertNotEqual(second.records[0].metrics["games"], -1)
        self.assertEqual(len(transport.calls), 1)
        client.close()


class ClientBatchTests(unittest.TestCase):
    def test_batch_over_twenty_is_rejected_before_any_network_call(self):
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",))
        client = Client(transport=transport)
        with self.assertRaisesRegex(QueryError, "limited to 20"):
            list(client.collect_many([q] * 21))
        self.assertEqual(transport.calls, [])
        client.close()

    def test_batch_can_resume_from_cache_and_propagates_failure_at_query(self):
        good = query_for("ahri-ranked.json")
        bad = Query("jinx", mode="aram", tier="all")
        transport = FixtureTransport(("ahri-ranked.json",), errors={bad.url: HTTPStatusError(403)})
        client = Client(transport=transport)
        first = client.collect(good)
        resumed = list(client.collect_many([good]))
        self.assertTrue(resumed[0].cache_hit)
        self.assertEqual(len(transport.calls), 1)
        iterator = client.collect_many([good, bad])
        self.assertTrue(next(iterator).cache_hit)
        with self.assertRaises(HTTPStatusError):
            next(iterator)
        self.assertEqual(transport.calls.count(good.url), 1)
        self.assertEqual(transport.calls.count(bad.url), 1)
        client.close()

    def test_disk_cache_arena_payload_has_no_item_or_augment_win_rates(self):
        q = query_for("ahri-arena.json")
        transport = FixtureTransport(("ahri-arena.json",))
        with tempfile.TemporaryDirectory() as tmp:
            client = Client(cache_dir=tmp, transport=transport)
            snapshot = client.collect(q)
            self.assertTrue(snapshot.raw.get("augment"))
            cache_files = list(Path(tmp).glob("*.json"))
            self.assertEqual(len(cache_files), 1)
            envelope = json.loads(cache_files[0].read_text())
            stored = json.loads(base64.b64decode(envelope["value"]))
            payload = stored["payload"]
            for key in ("builtItemSet3", "startSet", "item", "item1", "item2", "item3", "item4", "item5", "item6", "startItem", "prismatic"):
                for row in payload.get(key, []):
                    self.assertIsNone(row[1], key)
            for rows in payload.get("augment", {}).values():
                for row in rows:
                    self.assertIsNone(row[1])
            self.assertNotIn("sidebar", payload)
            client.close()

    def test_lazy_itemsets_fixture_preserves_raw_counters_without_inventing_win_rate(self):
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",))
        url = lazy_itemsets_url(q)
        transport.bodies[url] = (FIXTURES / "ahri-ranked-itemsets.json").read_bytes()
        client = Client(transport=transport)
        result = client.collect_item_sets(q)
        self.assertEqual(result["source_url"], url)
        self.assertEqual(result["raw"]["itemSets"]["itemSet1"][0], ["3118", 9960, 3592])
        self.assertNotIn("win_rate", result)
        self.assertTrue(any("without inferred metrics" in note for note in result["limitations"]))
        self.assertEqual(transport.calls, [q.url, url])
        client.close()

    def test_lazy_itemsets_reject_malformed_json_schema_and_invalid_response(self):
        q = query_for("ahri-ranked.json")
        cases = (
            (b"not JSON", SchemaError),
            (b"[" * 2000 + b"0" + b"]" * 2000, SchemaError),
            (b'{"itemSets":{},"response":{"valid":true},"extra":NaN}', SchemaError),
            (b'{"itemSets":{"itemSet1":[["3118",1.5,2]]},"response":{"valid":true}}', SchemaError),
            (b'{"itemSets":{"itemSet1":[["3118",1,1]]},"response":{"valid":false}}', DataUnavailable),
        )
        for body, expected_error in cases:
            with self.subTest(error=expected_error.__name__, body=body[:20]):
                transport = FixtureTransport(("ahri-ranked.json",))
                transport.bodies[lazy_itemsets_url(q)] = body
                client = Client(transport=transport)
                with self.assertRaises(expected_error):
                    client.collect_item_sets(q)
                self.assertEqual(transport.calls, [q.url, lazy_itemsets_url(q)])
                client.close()

    def test_corrupt_lazy_cache_is_revalidated_before_reuse(self):
        q = query_for("ahri-ranked.json")
        transport = FixtureTransport(("ahri-ranked.json",))
        url = lazy_itemsets_url(q)
        transport.bodies[url] = (FIXTURES / "ahri-ranked-itemsets.json").read_bytes()
        with Client(transport=transport) as client:
            client.collect_item_sets(q)
            envelope = client._memory[url]
            cached = json.loads(envelope["value"])
            cached["raw"]["itemSets"]["itemSet1"][0][1] = "invalid counter"
            envelope["value"] = json.dumps(cached).encode()
            result = client.collect_item_sets(q)
            self.assertFalse(result["cache_hit"])
            self.assertEqual(transport.calls.count(url), 2)

    def test_lazy_itemsets_reject_arena_before_any_network_call(self):
        q = query_for("ahri-arena.json")
        transport = FixtureTransport(("ahri-arena.json",))
        client = Client(transport=transport)
        with self.assertRaises(QueryError):
            client.collect_item_sets(q)
        self.assertEqual(transport.calls, [])
        client.close()


class ClientSingleFlightTests(unittest.TestCase):
    def _run_concurrent(self, *, fail_first=False):
        q = query_for("ahri-ranked.json")
        entered_transport = threading.Event()
        release_transport = threading.Event()
        all_waiters = threading.Event()
        count_lock = threading.Lock()
        waiter_count = 0

        # Patch the Future factory used by Client so the test can release the
        # fake response only after every non-owner has joined the shared future.
        from concurrent.futures import Future as BaseFuture

        class CountingFuture(BaseFuture):
            def result(self, *args, **kwargs):
                nonlocal waiter_count
                with count_lock:
                    waiter_count += 1
                    if waiter_count == 5:
                        all_waiters.set()
                return super().result(*args, **kwargs)

        attempts = 0
        attempts_lock = threading.Lock()

        def gate(_url):
            nonlocal attempts
            with attempts_lock:
                attempts += 1
                this_attempt = attempts
            entered_transport.set()
            if this_attempt == 1:
                if not release_transport.wait(timeout=5):
                    raise TimeoutError("test gate timed out")
                if fail_first:
                    raise HTTPStatusError(503)

        transport = FixtureTransport(("ahri-ranked.json",), before_return=gate)
        client = Client(transport=transport)
        with patch("lolalytics.client.Future", CountingFuture):
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = [pool.submit(client.collect, q) for _ in range(6)]
                self.assertTrue(entered_transport.wait(2))
                self.assertTrue(all_waiters.wait(3), "all identical callers should join one in-flight request")
                release_transport.set()
                outcomes = []
                for future in futures:
                    try:
                        outcomes.append(future.result(timeout=5))
                    except Exception as error:
                        outcomes.append(error)
        self.assertEqual(len(transport.calls), 1)
        return client, q, outcomes, transport

    def test_identical_concurrent_queries_share_one_response_and_independent_snapshots(self):
        _client, _q, outcomes, _transport = self._run_concurrent()
        self.assertTrue(all(not isinstance(value, Exception) for value in outcomes))
        self.assertEqual(len({id(value) for value in outcomes}), 6)
        outcomes[0].overview["games"] = -4
        self.assertNotEqual(outcomes[1].overview["games"], -4)
        _client.close()

    def test_shared_failure_reaches_all_waiters_and_inflight_is_cleared(self):
        client, q, outcomes, transport = self._run_concurrent(fail_first=True)
        self.assertTrue(all(isinstance(value, HTTPStatusError) for value in outcomes))
        self.assertTrue(all(str(value) == "LoLalytics returned HTTP 503" for value in outcomes))
        # The next call must become a new owner; it must not inherit a failed future.
        result = client.collect(q)
        self.assertGreater(result.overview["games"], 0)
        self.assertEqual(len(transport.calls), 2)
        client.close()


if __name__ == "__main__":
    unittest.main()
