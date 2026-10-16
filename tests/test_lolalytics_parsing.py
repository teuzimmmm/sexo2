"""Contract tests for decoding, validation, normalization, and Arena redaction."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from lolalytics.decoding import decode_page
from lolalytics.errors import DataUnavailable, SchemaError
from lolalytics.parsing import parse_page, parse_payload, sanitize_payload
from lolalytics.query import Query


FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def fixture_query(entry):
    return Query(**entry["filters"])


def fixture_bytes(entry):
    return (FIXTURES / entry["fixture"]).read_bytes()


class ParsingFixtureTests(unittest.TestCase):
    def test_real_fixture_pages_parse_with_resolved_filters(self):
        for entry in MANIFEST:
            with self.subTest(fixture=entry["fixture"]):
                snapshot = parse_page(
                    fixture_bytes(entry), fixture_query(entry), entry["source_url"],
                    entry["collected_on"],
                )
                self.assertEqual(snapshot.resolved["champion"], entry["filters"]["champion"])
                self.assertEqual(snapshot.resolved["mode"], entry["filters"]["mode"])
                self.assertEqual(snapshot.resolved["patch"], entry["filters"]["patch"])
                self.assertGreater(snapshot.overview["games"], 0)
                self.assertTrue(snapshot.availability)

    def test_ranked_suggestions_are_separate_from_page_metrics(self):
        entry = next(x for x in MANIFEST if x["fixture"] == "ahri-ranked.json")
        snapshot = parse_page(fixture_bytes(entry), fixture_query(entry), "test", "now")
        suggestions = [r for r in snapshot.records if r.category == "rune_suggestion"]
        self.assertEqual(len(suggestions), 2)
        self.assertEqual([len(r.identifiers) for r in suggestions], [9, 9])
        self.assertEqual(suggestions[0].metric_scope, "suggested_layout_not_joint_sample")
        self.assertEqual(suggestions[0].metrics, {"win_rate": None, "pick_rate": None, "games": None})
        self.assertEqual(len(suggestions[0].raw["selection"]), 9)
        self.assertEqual(set(suggestions[0].raw), {"selection", "page", "set"})
        self.assertTrue(any("do not establish a joint sample" in warning for warning in snapshot.warnings))
        self.assertTrue(any(r.category == "rune_statistics" for r in snapshot.records))

    def test_arena_rates_are_suppressed_and_pick_rate_kept(self):
        for name in ("ahri-arena.json", "jinx-arena.json"):
            entry = next(x for x in MANIFEST if x["fixture"] == name)
            nav, payload = decode_page(fixture_bytes(entry))
            before = deepcopy(payload)
            sanitized = sanitize_payload(payload, "arena")
            self.assertEqual(payload, before)
            for key in ("builtItemSet3", "item", "item1", "item2", "item3", "item4", "item5", "item6", "startItem", "prismatic"):
                for row in sanitized.get(key, []):
                    self.assertIsNone(row[1], (name, key, row))
            for rows in sanitized.get("augment", {}).values():
                for row in rows:
                    self.assertIsNone(row[1], (name, row))
            snapshot = parse_payload(nav, payload, fixture_query(entry), "test", "now")
            augment_records = [r for r in snapshot.records if r.category == "augment_statistics"]
            self.assertTrue(augment_records)
            self.assertTrue(all(r.metrics["win_rate"] is None for r in augment_records))
            self.assertTrue(all(r.metrics["pick_rate"] is not None for r in augment_records))
            self.assertTrue(all(r.metrics["games"] is not None for r in augment_records))
            self.assertTrue(all(r.raw[1] is None for r in augment_records))
            self.assertTrue(any("win rates are suppressed" in warning for warning in snapshot.warnings))
            self.assertNotIn("sidebar", snapshot.raw)
            self.assertEqual(snapshot.availability["rune_statistics"], "not_applicable")
            self.assertEqual(snapshot.availability["rune_suggestion"], "not_applicable")
            self.assertEqual(snapshot.availability["augment_statistics"], "available")
            self.assertIn("average_win_rate", snapshot.overview)
            self.assertTrue(snapshot.overview["placement_rates"])


class ParsingValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry = next(x for x in MANIFEST if x["fixture"] == "ahri-ranked.json")
        cls.nav, cls.payload = decode_page(fixture_bytes(entry))
        cls.query = fixture_query(entry)

    def parse_copy(self, *, nav=None, payload=None, query=None):
        return parse_payload(
            deepcopy(self.nav if nav is None else nav),
            deepcopy(self.payload if payload is None else payload),
            self.query if query is None else query,
            "https://example.invalid/source", "2026-10-16T00:00:00Z",
        )

    def test_rejects_query_filter_ignored_by_server(self):
        nav = deepcopy(self.nav)
        nav["tier"] = "all"
        with self.assertRaises(SchemaError):
            self.parse_copy(nav=nav)

    def test_rejects_champion_identity_mismatch(self):
        payload = deepcopy(self.payload)
        payload["header"]["cid"] += 1
        with self.assertRaises(SchemaError):
            self.parse_copy(payload=payload)

    def test_rejects_zero_games_and_invalid_response(self):
        payload = deepcopy(self.payload)
        payload["header"]["n"] = 0
        with self.assertRaises(DataUnavailable):
            self.parse_copy(payload=payload)
        payload = deepcopy(self.payload)
        payload["response"]["valid"] = False
        with self.assertRaises(DataUnavailable):
            self.parse_copy(payload=payload)

    def test_requires_header_games_and_true_response_validity(self):
        payload = deepcopy(self.payload)
        payload["header"]["n"] = None
        with self.assertRaises(SchemaError):
            self.parse_copy(payload=payload)
        for response in (None, [], {}, {"valid": 1}):
            payload = deepcopy(self.payload)
            payload["response"] = response
            with self.subTest(response=response), self.assertRaises(SchemaError):
                self.parse_copy(payload=payload)

    def test_validates_nav_status_cid_patch_and_mode_queue(self):
        cases = []
        nav = deepcopy(self.nav); nav["status"] = 403; cases.append((nav, deepcopy(self.payload)))
        nav = deepcopy(self.nav); nav["cid"] = 0; cases.append((nav, deepcopy(self.payload)))
        nav = deepcopy(self.nav); nav["patch"] = "current"; cases.append((nav, deepcopy(self.payload)))
        payload = deepcopy(self.payload); payload["header"]["queue"] = 450; cases.append((deepcopy(self.nav), payload))
        for nav, payload in cases:
            with self.subTest(nav=nav, queue=payload["header"].get("queue")), self.assertRaises(SchemaError):
                self.parse_copy(nav=nav, payload=payload)

    def test_rejects_malformed_rows_and_types(self):
        payload = deepcopy(self.payload)
        payload["item"][0] = [123, "bad", 2.0, 3, 4]
        with self.assertRaises(SchemaError):
            self.parse_copy(payload=payload)
        payload = deepcopy(self.payload)
        payload["item"][0][3] = None
        with self.assertRaises(SchemaError):
            self.parse_copy(payload=payload)

    def test_rejects_scalar_rows_and_nonfinite_raw_timing(self):
        payload = deepcopy(self.payload)
        payload["item"][0] = 12
        with self.assertRaises(SchemaError):
            self.parse_copy(payload=payload)
        arena = {
            "header": {"cid": 103, "n": 2, "wr": 61},
            "response": {"valid": True},
            "item": [[220000, 70, 20, 11, float("inf")]],
        }
        # Use the Arena route so sanitizer validation is exercised.
        entry = next(x for x in MANIFEST if x["fixture"] == "ahri-arena.json")
        nav, _ = decode_page(fixture_bytes(entry))
        arena["header"]["cid"] = nav["cid"]
        with self.assertRaises(SchemaError):
            parse_payload(nav, arena, fixture_query(entry), "test", "now")

    def test_incomplete_rune_layout_is_unavailable(self):
        payload = deepcopy(self.payload)
        payload["summary"]["pick"]["runes"]["set"]["pri"] = [1, 2]
        snapshot = self.parse_copy(payload=payload)
        self.assertEqual(snapshot.availability["rune_suggestion:pick"], "unavailable")
        self.assertFalse(any(r.category == "rune_suggestion" and r.raw.get("result") == "pick" for r in snapshot.records))

    def test_rejects_boolean_header_games(self):
        payload = deepcopy(self.payload)
        payload["header"]["n"] = True
        with self.assertRaises(SchemaError):
            self.parse_copy(payload=payload)

    def test_unknown_and_unsupported_fields_do_not_become_records(self):
        payload = deepcopy(self.payload)
        payload["unconfirmed"] = [[1, 99, 99, 999]]
        snapshot = self.parse_copy(payload=payload)
        self.assertIn("unconfirmed", snapshot.raw)
        self.assertFalse(any("unconfirmed" in r.source_path for r in snapshot.records))

    def test_arena_sanitizer_removes_unknown_fields_and_redacts_in_new_copy(self):
        payload = {
            "header": {"cid": 103, "n": 2, "wr": 61},
            "graph": {"wr": {"all": [61]}},
            "avgWr": 52.1,
            "augment": {"augment0": [[0, 71.2, 14.0, 10]]},
            "item": [[220000, 70, 20, 11, 1]],
            "secret_unknown": {"some_rate": 70},
        }
        result = sanitize_payload(payload, "arena")
        self.assertIsNot(result, payload)
        self.assertIsNone(result["augment"]["augment0"][0][1])
        self.assertIsNone(result["item"][0][1])
        self.assertEqual(result["header"]["wr"], 61)
        self.assertEqual(result["avgWr"], 52.1)
        self.assertEqual(result["graph"]["wr"]["all"], [61])
        self.assertNotIn("secret_unknown", result)
        self.assertEqual(payload["augment"]["augment0"][0][1], 71.2)

    def test_zero_and_repeated_item_ids_are_preserved(self):
        payload = deepcopy(self.payload)
        payload["startSet"] = [["0_100_100", "xx.xx", 1.25, 8]]
        snapshot = self.parse_copy(payload=payload)
        record = next(r for r in snapshot.records if r.category == "item_combination" and r.source_path.startswith("payload.startSet"))
        self.assertEqual(record.identifiers, ["0", "100", "100"])
        self.assertIsNone(record.metrics["win_rate"])


if __name__ == "__main__":
    unittest.main()
