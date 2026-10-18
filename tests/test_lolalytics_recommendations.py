"""Offline recommendation API tests against captured LoLalytics responses."""

import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from lolalytics.client import Client
from lolalytics.errors import DataUnavailable, HTTPStatusError, QueryError, SchemaError
from lolalytics.models import Snapshot
from lolalytics.parsing import parse_page
from lolalytics.query import Query
from lolalytics.recommendations import item_rankings
from lolalytics.models import Record

FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
KEYSTONE = FIXTURES / "keystone"
KEYSTONE_MANIFEST = json.loads((KEYSTONE / "manifest.json").read_text())
MATCHUPS = FIXTURES / "matchups"
MATCHUP_MANIFEST = json.loads((MATCHUPS / "manifest.json").read_text())


def _entry(manifest, filename):
    return next(row for row in manifest if row["fixture"] == filename)


def _snapshot(root, manifest, filename):
    row = _entry(manifest, filename)
    query = Query(**row["filters"])
    return parse_page((root / filename).read_bytes(), query, row["source_url"], "2026-10-16T00:00:00Z")


class FixtureTransport:
    def __init__(self, entries):
        self.bodies = {}
        for root, manifest, filename in entries:
            row = _entry(manifest, filename)
            self.bodies[Query(**row["filters"]).url] = (root / filename).read_bytes()
        self.errors = {}
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if url in self.errors:
            raise self.errors[url]
        if url not in self.bodies:
            raise AssertionError(f"unexpected offline URL: {url}")
        return self.bodies[url]

    def close(self):
        pass


def _ahri_entries():
    return [
        (KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-base.json"),
        (KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-win.json"),
        (KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-pick.json"),
    ]


class RecommendationClientTests(unittest.TestCase):
    def test_real_ranked_fixture_selects_complete_layout_then_keystone_page(self):
        transport = FixtureTransport(_ahri_entries())
        client = Client(transport=transport)
        query = Query("ahri", patch="16.20", lane="middle")
        result = client.recommend(query)
        data = result.to_dict()

        self.assertEqual(result.recommended_selection, "win")
        self.assertEqual(result.build_page.selection, "win")
        self.assertEqual(result.build_page.keystone, 8992)
        self.assertEqual(len(result.rune_candidates), 2)
        self.assertTrue(all(len(row["runes"]["pri"]) == 4 for row in result.rune_candidates))
        self.assertTrue(all(len(row["runes"]["sec"]) == 2 for row in result.rune_candidates))
        self.assertTrue(all(len(row["runes"]["mod"]) == 3 for row in result.rune_candidates))
        self.assertEqual(len(transport.calls), 2)
        self.assertIsNone(Query("ahri", patch="16.20", lane="middle").to_dict()["keystone"])
        self.assertEqual(data["query"]["keystone"], None)
        self.assertEqual(data["build_page"]["conditioning"], "keystone")
        self.assertIn("rune_scope_primary_not_joint_page", result.warnings)
        self.assertEqual(result.policy["baseline"], 52.9)
        self.assertEqual(result.policy["item_baseline"], 53.23)
        first_item = result.item_rankings[next(iter(result.item_rankings))][0]
        self.assertEqual(first_item["risk"]["baseline"], 53.23)
        metrics = first_item["metrics"]
        if metrics["win_rate"] is not None and metrics["games"]:
            expected = (metrics["win_rate"] * metrics["games"] + 53.23 * 1000) / (metrics["games"] + 1000)
            self.assertAlmostEqual(first_item["risk"]["score"], expected)
        client.close()

    def test_explicit_keystone_is_one_source_call_and_keeps_filtered_baseline(self):
        transport = FixtureTransport(_ahri_entries())
        client = Client(transport=transport)
        query = Query("ahri", patch="16.20", lane="middle", keystone=8112)
        result = client.recommend(query, risk_level="high")
        self.assertEqual(len(transport.calls), 1)
        self.assertIn("keystone=8112", transport.calls[0])
        self.assertEqual(result.build_page.keystone, 8112)
        self.assertEqual(
            result.policy["item_baseline"],
            result.item_rankings[next(iter(result.item_rankings))][0]["risk"]["baseline"],
        )
        self.assertEqual(result.policy["item_baseline_source"], "item_source.champion_query_overview")
        self.assertEqual(result.policy["baseline"], 52.67)
        self.assertEqual(result.policy["item_baseline"], 52.67)
        self.assertEqual(result.item_source["query"]["keystone"], 8112)
        self.assertIn("keystone=8112", result.item_source["source_url"])
        self.assertEqual(query.keystone, result.query["keystone"])
        client.close()

    def test_opponent_recommendation_uses_one_unfiltered_opponent_query(self):
        transport = FixtureTransport([(MATCHUPS, MATCHUP_MANIFEST, "ahri-vs-annie.json")])
        client = Client(transport=transport)
        query = Query("ahri", patch="16.20", lane="middle", opponent="annie", opponent_lane="middle")
        result = client.recommend(query)
        self.assertEqual(len(transport.calls), 1)
        self.assertIn("/vs/annie/", transport.calls[0])
        self.assertNotIn("keystone=", transport.calls[0])
        self.assertEqual(result.recommended_selection, "win")
        self.assertEqual(result.build_page.selection, "vs")
        self.assertEqual(result.build_page.conditioning, "opponent")
        self.assertEqual(result.query["keystone"], None)
        self.assertEqual(result.rune_candidates[0]["risk"]["score"], result.rune_candidates[1]["risk"]["score"])
        client.close()

    def test_opponent_pick_winner_uses_pick_source_and_never_adds_keystone(self):
        snapshot = _snapshot(MATCHUPS, MATCHUP_MANIFEST, "ahri-vs-annie.json")
        snapshot.raw["summary"]["win"]["runes"]["wr"] = 49.0
        snapshot.raw["summary"]["win"]["runes"]["n"] = 1000
        snapshot.raw["summary"]["pick"]["runes"]["wr"] = 80.0
        snapshot.raw["summary"]["pick"]["runes"]["n"] = 50
        client = Client(transport=FixtureTransport([]))
        calls = []

        def collect(query):
            calls.append(query)
            return copy.deepcopy(snapshot)

        with patch.object(client, "collect", side_effect=collect):
            result = client.recommend(
                Query("ahri", patch="16.20", lane="middle", opponent="annie", opponent_lane="middle")
            )
        pick = next(row for row in result.rune_candidates if row["selection"] == "pick")
        self.assertEqual(result.recommended_selection, "pick")
        self.assertEqual(pick["source_path"], "payload.summary.pick.runes")
        self.assertEqual(result.build_page.selection, "vs")
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0].keystone)
        client.close()

    def test_arena_uses_pick_rate_without_rune_or_winrate_risk(self):
        transport = FixtureTransport([(FIXTURES, MANIFEST, "jinx-arena.json")])
        client = Client(transport=transport)
        result = client.recommend(
            Query("jinx", mode="arena", patch="16.20", tier="emerald_plus"), risk_level="very-high"
        )
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(result.recommended_selection, None)
        self.assertEqual(result.rune_candidates, [])
        self.assertEqual(result.policy["method"], "pick_rate")
        self.assertIsNone(result.policy["baseline"])
        self.assertIn("risk_not_applicable_to_arena_popularity", result.warnings)
        for rows in result.item_rankings.values():
            pick_rates = [row["metrics"]["pick_rate"] for row in rows]
            self.assertEqual(pick_rates, sorted(pick_rates, key=lambda value: (value is None, -(value or 0))))
            for row in rows:
                self.assertIsNone(row["metrics"]["win_rate"])
                self.assertEqual(row["risk"]["criterion"], "pick_rate")
                self.assertIsNone(row["risk"]["score"])
        client.close()

    def test_aram_runes_and_pick_page_use_captured_fixture(self):
        transport = FixtureTransport(
            [
                (KEYSTONE, KEYSTONE_MANIFEST, "jinx-aram-base.json"),
                (KEYSTONE, KEYSTONE_MANIFEST, "jinx-aram-filtered.json"),
            ]
        )
        client = Client(transport=transport)
        result = client.recommend(Query("jinx", mode="aram", patch="16.20", tier="all"), risk_level="low")
        self.assertEqual(result.recommended_selection, "win")
        self.assertEqual(result.build_page.keystone, 8008)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_validation_and_unavailable_baseline_fail_without_fabricating_scores(self):
        query = Query("ahri", lane="middle")
        transport = FixtureTransport(_ahri_entries())
        client = Client(transport=transport)
        with self.assertRaises(QueryError):
            client.recommend(query, risk_level="MEDIUM")
        self.assertEqual(transport.calls, [])
        client.close()

        snapshot = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-base.json")
        snapshot.overview.pop("win_rate")
        client = Client(transport=transport)
        with patch.object(client, "collect", return_value=snapshot):
            with self.assertRaises(DataUnavailable):
                client.recommend(query)
        client.close()

    def test_missing_keystone_metrics_remain_unavailable_and_other_candidate_can_win(self):
        snapshot = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-base.json")
        snapshot.raw["summary"]["win"]["runes"]["wr"] = None
        snapshot.raw["summary"]["win"]["runes"]["n"] = None
        filtered_pick = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-pick.json")

        class SnapshotClient(Client):
            def __init__(self):
                super().__init__(transport=FixtureTransport([]))

            def collect(self, query):
                return copy.deepcopy(snapshot if query.keystone is None else filtered_pick)

        client = SnapshotClient()
        with self.subTest("missing sample"):
            result = client.recommend(Query("ahri", lane="middle"))
        win = next(row for row in result.rune_candidates if row["selection"] == "win")
        self.assertIsNone(win["risk"]["score"])
        self.assertEqual(win["risk"]["reason"], "missing_win_rate")
        self.assertEqual(result.recommended_selection, "pick")
        client.close()

    def test_source_failure_propagates_and_malformed_candidate_is_schema_error(self):
        query = Query("ahri", patch="16.20", lane="middle")
        transport = FixtureTransport(_ahri_entries())
        transport.errors[query.url] = HTTPStatusError(503)
        client = Client(transport=transport)
        with self.assertRaises(HTTPStatusError):
            client.recommend(query)
        client.close()

        snapshot = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-base.json")
        snapshot.raw["summary"]["win"]["runes"]["wr"] = "not-a-rate"
        client = Client(transport=transport)
        with patch.object(client, "collect", return_value=snapshot):
            with self.assertRaises(SchemaError):
                client.recommend(Query("ahri", lane="middle"))
        client.close()

    def test_recommendation_reuses_prepopulated_base_and_filtered_cache(self):
        transport = FixtureTransport(_ahri_entries())
        client = Client(transport=transport)
        base = Query("ahri", patch="16.20", lane="middle")
        filtered = Query("ahri", patch="16.20", lane="middle", keystone=8992)
        client.collect(base)
        client.collect(filtered)
        self.assertEqual(len(transport.calls), 2)
        result = client.recommend(base)
        self.assertTrue(result.cache_hit)
        self.assertEqual(len(transport.calls), 2)
        client.close()

    def test_warm_base_and_cold_selected_key_reports_aggregate_cache_miss(self):
        transport = FixtureTransport(_ahri_entries())
        client = Client(transport=transport)
        base = Query("ahri", patch="16.20", lane="middle")
        client.collect(base)
        self.assertEqual(len(transport.calls), 1)
        result = client.recommend(base)
        self.assertEqual(len(transport.calls), 2)
        self.assertFalse(result.cache_hit)
        self.assertFalse(result.item_source["cache_hit"])
        self.assertEqual(result.item_source["query"]["keystone"], 8992)
        client.close()

    def test_all_unavailable_rune_samples_raise_data_unavailable(self):
        snapshot = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-base.json")
        for selection in ("win", "pick"):
            snapshot.raw["summary"][selection]["runes"]["wr"] = None
            snapshot.raw["summary"][selection]["runes"]["n"] = None
        client = Client(transport=FixtureTransport([]))
        with patch.object(client, "collect", return_value=snapshot):
            with self.assertRaises(DataUnavailable):
                client.recommend(Query("ahri", lane="middle"))
        client.close()

    def test_item_rankings_keep_category_and_source_parent_groups_separate(self):
        snapshot = Snapshot(
            query={"mode": "ranked"},
            resolved={},
            source_url="fixture",
            collected_at="now",
            overview={},
            raw={},
            availability={},
            records=[
                Record(
                    "item_statistics",
                    ["1001"],
                    {"win_rate": 52, "pick_rate": 10, "games": 20},
                    "payload.item1[0]",
                    [1001, 52, 10, 20],
                    "item_observation",
                ),
                Record(
                    "item_combination",
                    ["1001", "2003"],
                    {"win_rate": 60, "pick_rate": 1, "games": 5},
                    "payload.item1[0]",
                    ["1001_2003", 60, 1, 5],
                    "joint_build_sample",
                ),
                Record(
                    "item_statistics",
                    ["3006"],
                    {"win_rate": 55, "pick_rate": 20, "games": 100},
                    "payload.boots[0]",
                    [3006, 55, 20, 100],
                    "item_observation",
                ),
            ],
        )
        groups = item_rankings(snapshot, 50, "medium")
        self.assertEqual(len(groups), 3)
        self.assertEqual(
            {row["category"] for rows in groups.values() for row in rows}, {"item_statistics", "item_combination"}
        )
        self.assertEqual(
            {row["source_path"] for rows in groups.values() for row in rows}, {"payload.item1[0]", "payload.boots[0]"}
        )
        self.assertEqual(sum(len(rows) for rows in groups.values()), 3)


class RecommendationMutationTests(unittest.TestCase):
    def test_item_tables_remain_separate_and_source_metrics_are_unchanged(self):
        snapshot = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-base.json")
        snapshot.records = [
            Record(
                "item_statistics",
                ["3118"],
                {"win_rate": 80, "games": 50},
                "payload.item1[0]",
                [3118, 80, None, 50],
                "item_observation",
            ),
            Record(
                "item_statistics",
                ["2503"],
                {"win_rate": 53, "games": 2000},
                "payload.item1[1]",
                [2503, 53, None, 2000],
                "item_observation",
            ),
            Record(
                "item_statistics",
                ["3118"],
                {"win_rate": 90, "games": 300},
                "payload.item2[0]",
                [3118, 90, None, 300],
                "item_observation",
            ),
        ]
        original = copy.deepcopy(snapshot.records)
        conservative = item_rankings(snapshot, 50, "very-low")
        aggressive = item_rankings(snapshot, 50, "very-high")
        key = "item_statistics:item_observation:payload.item1"
        self.assertEqual(conservative[key][0]["identifiers"], ["2503"])
        self.assertEqual(aggressive[key][0]["identifiers"], ["3118"])
        self.assertEqual(len(conservative["item_statistics:item_observation:payload.item2"]), 1)
        conservative[key][0]["raw"][0] = "changed"
        self.assertEqual(snapshot.records, original)

    def test_risk_level_changes_winner_with_synthetic_metrics_without_mutation(self):
        base = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-base.json")
        original = copy.deepcopy(base.raw["summary"])
        win = base.raw["summary"]["win"]
        pick = base.raw["summary"]["pick"]
        win["runes"]["wr"], win["runes"]["n"] = 80.0, 50
        pick["runes"]["wr"], pick["runes"]["n"] = 53.0, 2000
        base.overview["win_rate"] = 50.0

        class SnapshotClient(Client):
            def __init__(self, snapshots):
                super().__init__(transport=FixtureTransport([]))
                self.snapshots = snapshots
                self.collected = []

            def collect(self, query):
                self.collected.append(query)
                selected = self.snapshots.get(query.keystone, self.snapshots[None])
                return copy.deepcopy(selected)

        win_snapshot = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-win.json")
        pick_snapshot = _snapshot(KEYSTONE, KEYSTONE_MANIFEST, "ahri-ranked-pick.json")
        client = SnapshotClient({None: base, 8992: win_snapshot, 8112: pick_snapshot})
        query = Query("ahri", patch="16.20", lane="middle")
        low_risk = client.recommend(query, risk_level="very-low")
        high_risk = client.recommend(query, risk_level="very-high")
        self.assertEqual(low_risk.recommended_selection, "pick")
        self.assertEqual(high_risk.recommended_selection, "win")
        self.assertEqual(base.raw["summary"]["win"]["runes"]["wr"], 80.0)
        self.assertEqual(base.raw["summary"]["pick"]["runes"]["n"], 2000)
        self.assertEqual(original["win"]["runes"]["set"], base.raw["summary"]["win"]["runes"]["set"])
        self.assertEqual(client.collected[0].keystone, None)
        self.assertEqual(client.collected[1].keystone, 8112)
        self.assertEqual(client.collected[2].keystone, None)
        self.assertEqual(client.collected[3].keystone, 8992)
        client.close()


class RecommendationCliTests(unittest.TestCase):
    def test_recommend_flags_emit_json_and_risk_requires_recommend(self):
        from lolalytics.__main__ import main

        transport = FixtureTransport(_ahri_entries())
        factory = lambda **kwargs: Client(transport=transport, **kwargs)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("lolalytics.__main__.Client", side_effect=factory):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["ahri", "--patch", "16.20", "--lane", "middle", "--recommend", "--risk-level", "high"])
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["recommended_selection"], "win")
        self.assertEqual(stderr.getvalue(), "")

        with patch("lolalytics.__main__.Client") as client_cls:
            for args in (
                ["--risk-level", "high"],
                ["--recommend", "--builds"],
                ["--recommend", "--item-sets"],
                ["--recommend", "--matchup", "--opponent", "annie"],
                ["--recommend", "--risk-level", "invalid"],
            ):
                with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        main(["ahri", *args])
                    self.assertEqual(error.exception.code, 2)
            client_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
