"""Contracts for explicit ranked matchup queries and resolved navigation."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from lolalytics.decoding import decode_page
from lolalytics.errors import QueryError, SchemaError
from lolalytics.parsing import parse_payload
from lolalytics.query import Query


FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics" / "matchups"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


class MatchupQueryTests(unittest.TestCase):
    def test_matchup_url_omits_region_and_uses_vslane(self):
        query = Query("ahri", lane="middle", opponent="annie", opponent_lane="middle")
        self.assertEqual(
            query.url,
            "https://lolalytics.com/lol/ahri/vs/annie/build/q-data.json?lane=middle&vslane=middle&tier=emerald_plus",
        )
        self.assertEqual(query.key, query.url)
        self.assertNotIn("region", query.url)
        self.assertIn("tier=all", Query("ahri", tier="all", opponent="annie").url)

    def test_existing_root_url_is_unchanged_without_opponent(self):
        query = Query("ahri")
        self.assertEqual(
            query.url,
            "https://lolalytics.com/lol/ahri/build/q-data.json?lane=all&tier=emerald_plus&region=all",
        )
        self.assertIsNone(query.to_dict()["opponent"])
        self.assertEqual(query.to_dict()["opponent_lane"], "all")

    def test_opponent_and_lane_separate_cache_keys(self):
        annie_mid = Query("ahri", lane="middle", opponent="annie", opponent_lane="middle")
        annie_top = Query("ahri", lane="middle", opponent="annie", opponent_lane="top")
        ryze_mid = Query("ahri", lane="middle", opponent="ryze", opponent_lane="middle")
        self.assertEqual(len({annie_mid.key, annie_top.key, ryze_mid.key}), 3)

    def test_rejects_invalid_opponent_and_lane_contracts(self):
        for opponent in ("Annie", "", "bad slug", "a" * 41, 3):
            with self.subTest(opponent=opponent), self.assertRaises(QueryError):
                Query("ahri", opponent=opponent)
        for opponent_lane in ("mid", "", True, None):
            with self.subTest(opponent_lane=opponent_lane), self.assertRaises(QueryError):
                Query("ahri", opponent="annie", opponent_lane=opponent_lane)
        with self.assertRaises(QueryError):
            Query("ahri", opponent_lane="middle")
        with self.assertRaises(QueryError):
            Query("ahri", opponent="annie", region="br")
        with self.assertRaises(QueryError):
            Query("ahri", opponent="annie", keystone=8112)

    def test_arena_and_aram_reject_opponent_before_network(self):
        for mode in ("aram", "arena"):
            with self.subTest(mode=mode), self.assertRaises(QueryError):
                Query("ahri", mode=mode, opponent="annie")


class MatchupParsingTests(unittest.TestCase):
    def test_real_matchup_fixtures_resolve_identity_and_filters(self):
        for entry in MANIFEST:
            with self.subTest(fixture=entry["fixture"]):
                query = Query(**entry["filters"])
                body = (FIXTURES / entry["fixture"]).read_bytes()
                nav, payload = decode_page(body)
                snapshot = parse_payload(nav, payload, query, entry["source_url"], entry["collected_on"])
                self.assertIn(f"/vs/{entry['filters']['opponent']}/build/q-data.json?", query.url)
                self.assertNotIn("region", query.url)
                self.assertNotIn("region=", entry["source_url"])
                self.assertEqual(snapshot.resolved["opponent"], entry["filters"]["opponent"])
                self.assertEqual(snapshot.resolved["opponent_id"], nav["vsCid"])
                self.assertEqual(snapshot.resolved["opponent_name"], nav["vsName"])
                self.assertEqual(snapshot.resolved["opponent_lane"], "middle")
                self.assertEqual(snapshot.resolved["effective_opponent_lane"], "middle")

    def test_rejects_wrong_opponent_and_ids(self):
        entry = MANIFEST[0]
        query = Query(**entry["filters"])
        nav, payload = decode_page((FIXTURES / entry["fixture"]).read_bytes())
        cases = []
        wrong_nav = deepcopy(nav); wrong_nav["vs"] = "ryze"; cases.append((wrong_nav, deepcopy(payload)))
        wrong_nav = deepcopy(nav); wrong_nav["vsCid"] = True; cases.append((wrong_nav, deepcopy(payload)))
        wrong_header = deepcopy(payload); wrong_header["header"]["vs"] = 13; cases.append((deepcopy(nav), wrong_header))
        wrong_header = deepcopy(payload); wrong_header["header"]["vs"] = True; cases.append((deepcopy(nav), wrong_header))
        for bad_nav, bad_payload in cases:
            with self.subTest(vs=bad_nav.get("vs"), vsCid=bad_nav.get("vsCid"), header_vs=bad_payload["header"].get("vs")), self.assertRaises(SchemaError):
                parse_payload(bad_nav, bad_payload, query, entry["source_url"], entry["collected_on"])

    def test_rejects_ignored_or_mismatched_opponent_lane(self):
        entry = MANIFEST[0]
        query = Query(**entry["filters"])
        nav, payload = decode_page((FIXTURES / entry["fixture"]).read_bytes())
        bad_nav = deepcopy(nav); bad_nav["vsLane"] = "top"
        with self.assertRaises(SchemaError):
            parse_payload(bad_nav, payload, query, entry["source_url"], entry["collected_on"])
        bad_payload = deepcopy(payload); bad_payload["header"]["vsLane"] = "top"
        with self.assertRaises(SchemaError):
            parse_payload(nav, bad_payload, query, entry["source_url"], entry["collected_on"])
        bad_payload = deepcopy(payload); bad_payload["header"]["vsLane"] = "middle-ish"
        with self.assertRaises(SchemaError):
            parse_payload(nav, bad_payload, query, entry["source_url"], entry["collected_on"])
        missing_payload = deepcopy(payload); del missing_payload["header"]["vsLane"]
        with self.assertRaises(SchemaError):
            parse_payload(nav, missing_payload, query, entry["source_url"], entry["collected_on"])

    def test_effective_opponent_lane_falls_back_to_default_for_all(self):
        entry = MANIFEST[0]
        filters = {**entry["filters"], "opponent_lane": "all"}
        query = Query(**filters)
        for raw_lane in (None, "all"):
            nav, payload = decode_page((FIXTURES / entry["fixture"]).read_bytes())
            nav["vsLane"] = "all"
            payload["header"]["vsLane"] = raw_lane
            payload["header"]["defaultVsLane"] = "middle"
            snapshot = parse_payload(nav, payload, query, entry["source_url"], entry["collected_on"])
            self.assertEqual(snapshot.resolved["opponent_lane"], "all")
            self.assertEqual(snapshot.resolved["effective_opponent_lane"], "middle")

        nav, payload = decode_page((FIXTURES / entry["fixture"]).read_bytes())
        nav["vsLane"] = "all"
        payload["header"]["vsLane"] = "all"
        payload["header"]["defaultVsLane"] = "middle"
        bad_payload = deepcopy(payload)
        bad_payload["header"]["defaultVsLane"] = "mid"
        with self.assertRaises(SchemaError):
            parse_payload(nav, bad_payload, query, entry["source_url"], entry["collected_on"])

    def test_no_opponent_rejects_unexpected_matchup_and_lane_is_not_inferred(self):
        base_entry = next(x for x in json.loads((Path(__file__).parent / "fixtures/lolalytics/manifest.json").read_text()) if x["fixture"] == "ahri-ranked.json")
        base_nav, base_payload = decode_page((Path(__file__).parent / "fixtures/lolalytics" / base_entry["fixture"]).read_bytes())
        query = Query(**base_entry["filters"])
        base_nav["vs"] = "annie"
        with self.assertRaises(SchemaError):
            parse_payload(base_nav, base_payload, query, "test", "now")

        entry = MANIFEST[0]
        query = Query(**entry["filters"])
        nav, payload = decode_page((FIXTURES / entry["fixture"]).read_bytes())
        payload["header"]["lane"] = None
        payload["header"]["defaultLane"] = None
        snapshot = parse_payload(nav, payload, query, entry["source_url"], entry["collected_on"])
        self.assertNotIn("effective_lane", snapshot.resolved)

        conflicting_payload = deepcopy(payload)
        conflicting_payload["header"]["lane"] = "bottom"
        with self.assertRaises(SchemaError):
            parse_payload(nav, conflicting_payload, query, entry["source_url"], entry["collected_on"])


if __name__ == "__main__":
    unittest.main()
