"""Keystone query and resolved-navigation contracts."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from lolalytics.decoding import decode_page
from lolalytics.errors import QueryError, SchemaError
from lolalytics.parsing import parse_payload
from lolalytics.query import Query


FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
KEYSTONE_FIXTURES = FIXTURES / "keystone"
KEYSTONE_MANIFEST = json.loads((KEYSTONE_FIXTURES / "manifest.json").read_text())


class KeystoneQueryTests(unittest.TestCase):
    def test_none_preserves_historical_url_and_dict(self):
        query = Query("ahri")
        self.assertEqual(
            query.url,
            "https://lolalytics.com/lol/ahri/build/q-data.json?lane=all&tier=emerald_plus&region=all",
        )
        self.assertIsNone(query.to_dict()["keystone"])

    def test_filter_is_in_url_key_and_dict(self):
        query = Query("jinx", mode="aram", tier="all", keystone=8008)
        self.assertIn("keystone=8008", query.url)
        self.assertEqual(query.key, query.url)
        self.assertEqual(query.to_dict()["keystone"], 8008)
        self.assertNotEqual(query.key, Query("jinx", mode="aram", tier="all").key)

    def test_new_argument_is_positional_at_end(self):
        query = Query("ahri", "ranked", None, "middle", "gold", "br", 8112)
        self.assertEqual(query.keystone, 8112)
        self.assertEqual(query.lane, "middle")

    def test_keystone_requires_positive_non_boolean_integer_and_supported_mode(self):
        for value in (True, False, 0, -1, 8.0, "8008"):
            with self.subTest(value=value), self.assertRaises(QueryError):
                Query("ahri", keystone=value)
        with self.assertRaises(QueryError):
            Query("jinx", mode="arena", keystone=8008)

    def test_cache_keys_separate_keystone_patch_and_mode(self):
        baseline = Query("ahri", patch="16.20", lane="middle")
        self.assertNotEqual(baseline.key, Query("ahri", patch="16.20", lane="middle", keystone=8992).key)
        self.assertNotEqual(baseline.key, Query("ahri", patch="16.19", lane="middle").key)
        self.assertNotEqual(baseline.key, Query("ahri", patch="16.20", mode="aram").key)


class KeystoneParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry = next(x for x in MANIFEST if x["fixture"] == "ahri-ranked.json")
        body = (FIXTURES / entry["fixture"]).read_bytes()
        cls.nav, cls.payload = decode_page(body)

    def parse(self, nav, query):
        return parse_payload(deepcopy(nav), deepcopy(self.payload), query, "test", "now")

    def test_filtered_navigation_must_match_exact_integer(self):
        query = Query("ahri", patch="16.20", lane="all", keystone=8992)
        nav = deepcopy(self.nav)
        nav["keystone"] = 8992
        snapshot = self.parse(nav, query)
        self.assertEqual(snapshot.resolved["keystone"], 8992)
        for wrong in (8112, True, 8992.0, "8992", None):
            nav = deepcopy(self.nav)
            nav["keystone"] = wrong
            with self.subTest(wrong=wrong), self.assertRaises(SchemaError):
                self.parse(nav, query)

    def test_unfiltered_accepts_legacy_sentinel_or_missing_only(self):
        query = Query("ahri", patch="16.20")
        legacy = deepcopy(self.nav)
        legacy["keystone"] = -1
        missing = deepcopy(self.nav)
        missing.pop("keystone", None)
        for nav in (missing, legacy):
            snapshot = self.parse(nav, query)
            self.assertIsNone(snapshot.resolved["keystone"])
        for unexpected in (8992, 8112, True, -1.0, "-1", None):
            nav = deepcopy(self.nav)
            nav["keystone"] = unexpected
            with self.subTest(unexpected=unexpected), self.assertRaises(SchemaError):
                self.parse(nav, query)

    def test_real_keystone_fixtures_decode_and_resolve_requested_filters(self):
        for entry in KEYSTONE_MANIFEST:
            with self.subTest(fixture=entry["fixture"]):
                query = Query(**entry["filters"])
                body = (KEYSTONE_FIXTURES / entry["fixture"]).read_bytes()
                nav, payload = decode_page(body)
                snapshot = parse_payload(nav, payload, query, entry["source_url"], entry["collected_on"])
                self.assertEqual(
                    {key: snapshot.query[key] for key in entry["filters"]},
                    entry["filters"],
                )
                self.assertEqual(snapshot.resolved["keystone"], entry["filters"]["keystone"])
                request_filters = {**entry["filters"], "patch": None}
                self.assertEqual(Query(**request_filters).url, entry["source_url"])

    def test_filtered_query_rejects_legacy_unfiltered_sentinel(self):
        entry = next(x for x in KEYSTONE_MANIFEST if x["fixture"] == "ahri-ranked-win.json")
        nav, payload = decode_page((KEYSTONE_FIXTURES / entry["fixture"]).read_bytes())
        nav["keystone"] = -1
        with self.assertRaises(SchemaError):
            parse_payload(nav, payload, Query(**entry["filters"]), entry["source_url"], entry["collected_on"])


if __name__ == "__main__":
    unittest.main()
