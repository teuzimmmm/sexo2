"""Offline matchup collection and page-shaping tests."""

import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from lolalytics.builds import BuildPage
from lolalytics.client import Client
from lolalytics.errors import DataUnavailable, HTTPStatusError, QueryError, SchemaError
from lolalytics.parsing import parse_page
from lolalytics.query import Query

FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics" / "matchups"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def entry(filename):
    return next(row for row in MANIFEST if row["fixture"] == filename)


def snapshot(filename):
    row = entry(filename)
    query = Query(**row["filters"])
    return parse_page((FIXTURES / filename).read_bytes(), query, row["source_url"], "2026-10-16T00:00:00Z")


class FixtureTransport:
    def __init__(self, names=(), errors=None):
        self.bodies = {entry(name)["source_url"]: (FIXTURES / name).read_bytes() for name in names}
        self.errors = errors or {}
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        # Captured q-data URLs omit the default tier and patch while Query.url
        # deliberately spells those filters out; match the fixture identity.
        source_url = url.replace("&patch=16.20", "").replace("?patch=16.20&", "?")
        source_url = source_url.replace("&tier=emerald_plus", "").replace("?tier=emerald_plus&", "?")
        if source_url in self.errors:
            raise self.errors[source_url]
        if source_url not in self.bodies:
            raise AssertionError(f"unexpected offline URL: {url}")
        return self.bodies[source_url]

    def close(self):
        pass


class MatchupPageTests(unittest.TestCase):
    def test_page_preserves_source_items_and_separates_matchup_metrics(self):
        from lolalytics.matchups import build_matchup_page

        snap = snapshot("ahri-vs-annie.json")
        page = build_matchup_page(snap)
        self.assertIsInstance(page, BuildPage)
        self.assertEqual(page.selection, "vs")
        self.assertEqual(page.label, "vs Annie")
        self.assertEqual(page.title, "WR vs Annie / taxa conjunta indisponível")
        self.assertEqual(page.conditioning, "opponent")
        self.assertEqual(page.keystone, snap.raw["summary"]["win"]["runes"]["set"]["pri"][0])
        self.assertIsNone(page.query["keystone"])
        self.assertIsNone(page.resolved["keystone"])
        self.assertEqual(page.core_metrics, {"win_rate": None, "games": None})
        self.assertEqual(
            page.matchup_metrics,
            {
                "scope": "champion_matchup",
                "win_rate": 49.57,
                "games": 1852,
            },
        )
        self.assertEqual(
            [block.kind for block in page.blocks], ["starting", "item1", "item2", "item3", "item4", "item5", "item6"]
        )
        self.assertEqual(len(page.blocks[1].choices), 1)
        self.assertEqual(page.blocks[1].choices[0].identifier, "6655")
        self.assertEqual(page.blocks[1].choices[0].metrics, {"win_rate": 52.19, "games": 228})
        self.assertEqual(page.blocks[1].metrics, {})
        self.assertEqual(page.blocks[1].choices[0].raw, snap.raw["summary"]["win"]["items"]["item1"])
        self.assertEqual(page.source_url, snap.source_url)
        self.assertEqual(page.query, snap.query)
        self.assertIn("opponent_conditioned", page.warnings)
        self.assertIn("keystone_filter_unavailable", page.warnings)
        self.assertIn("not_joint_build_sample", page.warnings)
        self.assertIn("low_item_sample", page.warnings)

    def test_low_sample_threshold_and_missing_sample_policy(self):
        from lolalytics.matchups import build_matchup_page

        snap = snapshot("ahri-vs-annie.json")
        snap.raw["summary"]["win"]["items"]["item1"]["n"] = None
        no_threshold = build_matchup_page(snap, min_games=0)
        self.assertIn("missing_item_sample", no_threshold.warnings)
        self.assertNotIn("low_item_sample", no_threshold.warnings)
        self.assertEqual(build_matchup_page(snapshot("ahri-vs-annie.json"), min_games=0).conditioning, "opponent")
        for invalid in (True, -1, 1.5, "100"):
            with self.subTest(invalid=invalid), self.assertRaises(SchemaError):
                build_matchup_page(snapshot("ahri-vs-annie.json"), min_games=invalid)

    def test_missing_layout_or_all_items_fails_and_bad_types_are_schema_errors(self):
        from lolalytics.matchups import build_matchup_page

        snap = snapshot("ahri-vs-annie.json")
        del snap.raw["summary"]["win"]["runes"]["set"]["mod"]
        with self.assertRaises(DataUnavailable):
            build_matchup_page(snap)
        snap = snapshot("ahri-vs-annie.json")
        for key in ("start", "item1", "item2", "item3", "item4", "item5", "item6"):
            snap.raw["summary"]["win"]["items"].pop(key)
        with self.assertRaises(DataUnavailable):
            build_matchup_page(snap)
        snap = snapshot("ahri-vs-annie.json")
        snap.raw["summary"]["win"]["items"]["item1"] = []
        with self.assertRaises(SchemaError):
            build_matchup_page(snap)

    def test_opponent_metadata_must_match_and_keystone_must_be_absent(self):
        from lolalytics.matchups import build_matchup_page

        snap = snapshot("ahri-vs-annie.json")
        snap.resolved["opponent"] = "ryze"
        with self.assertRaises(SchemaError):
            build_matchup_page(snap)
        snap = snapshot("ahri-vs-annie.json")
        snap.query["keystone"] = 8112
        with self.assertRaises(DataUnavailable):
            build_matchup_page(snap)
        snap = snapshot("ahri-vs-annie.json")
        snap.query = None
        with self.assertRaises(SchemaError):
            build_matchup_page(snap)


class MatchupClientTests(unittest.TestCase):
    def test_one_validated_request_per_opponent_and_cache_identity_is_distinct(self):
        transport = FixtureTransport(("ahri-vs-annie.json", "ahri-vs-ryze.json"))
        client = Client(transport=transport, ttl=300)
        annie = Query(**entry("ahri-vs-annie.json")["filters"])
        ryze = Query(**entry("ahri-vs-ryze.json")["filters"])
        annie_page = client.collect_matchup(annie)
        ryze_page = client.collect_matchup(ryze)
        cached_annie_page = client.collect_matchup(annie)
        self.assertEqual(len(transport.calls), 2)
        self.assertNotEqual(annie.key, ryze.key)
        self.assertEqual(annie_page.resolved["opponent"], "annie")
        self.assertEqual(ryze_page.resolved["opponent"], "ryze")
        self.assertEqual(cached_annie_page.resolved["opponent"], "annie")
        self.assertTrue(cached_annie_page.cache_hit)
        self.assertEqual(annie_page.source_url, transport.calls[0])
        self.assertEqual(ryze_page.source_url, transport.calls[1])

    def test_opponent_builds_and_lazy_item_sets_reject_before_transport(self):
        transport = FixtureTransport(())
        client = Client(transport=transport)
        query = Query(**entry("ahri-vs-annie.json")["filters"])
        with self.assertRaises(QueryError):
            client.collect_builds(query)
        with self.assertRaises(QueryError):
            client.collect_item_sets(query)
        self.assertEqual(transport.calls, [])

    def test_http_error_propagates_without_fallback_or_page(self):
        query = Query(**entry("ahri-vs-annie.json")["filters"])
        transport = FixtureTransport(errors={entry("ahri-vs-annie.json")["source_url"]: HTTPStatusError(404)})
        with self.assertRaises(HTTPStatusError):
            Client(transport=transport, ttl=0).collect_matchup(query)
        self.assertEqual(transport.calls, [query.url])

    def test_invalid_min_games_fails_before_transport(self):
        query = Query(**entry("ahri-vs-annie.json")["filters"])
        transport = FixtureTransport(("ahri-vs-annie.json",))
        client = Client(transport=transport)
        for invalid in (True, -1, 1.5):
            with self.subTest(invalid=invalid), self.assertRaises(QueryError):
                client.collect_matchup(query, min_games=invalid)
        self.assertEqual(transport.calls, [])


class MatchupCliTests(unittest.TestCase):
    def test_matchup_requires_opponent_and_conflicts_fail_before_client(self):
        from lolalytics.__main__ import main

        for args in (
            ["ahri", "--matchup"],
            ["ahri", "--opponent", "annie", "--builds"],
            ["ahri", "--opponent", "annie", "--item-sets"],
        ):
            with self.subTest(args=args), patch("lolalytics.__main__.Client") as client_class:
                with self.assertRaises(SystemExit):
                    main(args)
                client_class.assert_not_called()

    def test_matchup_cli_emits_page_with_source(self):
        from lolalytics.__main__ import main

        transport = FixtureTransport(("ahri-vs-annie.json",))
        output = io.StringIO()
        with patch("lolalytics.__main__.Client", lambda **_kwargs: Client(transport=transport, ttl=0)):
            with contextlib.redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "ahri",
                            "--lane",
                            "middle",
                            "--opponent",
                            "annie",
                            "--opponent-lane",
                            "middle",
                            "--matchup",
                            "--min-games",
                            "0",
                        ]
                    ),
                    0,
                )
        data = json.loads(output.getvalue())
        self.assertEqual(data["selection"], "vs")
        self.assertEqual(data["resolved"]["opponent"], "annie")
        self.assertEqual(data["source_url"], transport.calls[0])


if __name__ == "__main__":
    unittest.main()
