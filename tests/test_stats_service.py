"""Stats adapter over offline LoLalytics fixtures."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lolalytics.client import Client
from lolalytics.query import Query
from sexo2.services.rune_rules import StyleCatalog, validate_page
from sexo2.services.stats import ChampionDirectory, StatsError, StatsService, champion_slug

FIXTURES = Path(__file__).parent / "fixtures" / "lolalytics"
STYLES = json.loads((Path(__file__).parent / "fixtures" / "lcu" / "perks-styles-representative.json").read_text())
SUMMARY = [
    {"id": -1, "name": "None", "alias": "None"},
    {"id": 103, "name": "Ahri", "alias": "Ahri"},
    {"id": 1, "name": "Annie", "alias": "Annie"},
    {"id": 13, "name": "Ryze", "alias": "Ryze"},
    {"id": 62, "name": "Wukong", "alias": "MonkeyKing"},
    {"id": 20, "name": "Nunu & Willump", "alias": "Nunu"},
    {"id": 888, "name": "Renata Glasc", "alias": "Renata"},
    {"id": 36, "name": "Dr. Mundo", "alias": "DrMundo"},
    {"id": 897, "name": "K'Sante", "alias": "KSante"},
]


class FixtureTransport:
    def __init__(self, entries):
        self.bodies = {}
        self.calls = []
        for folder, name in entries:
            manifest = json.loads((FIXTURES / folder / "manifest.json").read_text())
            row = next(row for row in manifest if row["fixture"] == name)
            body = (FIXTURES / folder / name).read_bytes()
            for patch_value in (row["filters"]["patch"], None):
                self.bodies[Query(**{**row["filters"], "patch": patch_value}).url] = body

    def get(self, url):
        self.calls.append(url)
        if url not in self.bodies:
            raise AssertionError(f"unexpected offline URL: {url}")
        return self.bodies[url]

    def close(self):
        pass


AHRI_BUILD_FIXTURES = [
    ("keystone", "ahri-ranked-base.json"),
    ("keystone", "ahri-ranked-win.json"),
    ("keystone", "ahri-ranked-pick.json"),
    ("matchups", "ahri-vs-annie.json"),
]


def service(entries=AHRI_BUILD_FIXTURES):
    transport = FixtureTransport(entries)
    client = Client(transport=transport, ttl=0)
    return StatsService(ChampionDirectory.from_summary(SUMMARY), client=client), transport


class SlugTests(unittest.TestCase):
    def test_alias_lowercase_with_documented_exceptions(self):
        directory = ChampionDirectory.from_summary(SUMMARY)
        expected = {103: "ahri", 62: "wukong", 20: "nunu", 888: "renata", 36: "drmundo", 897: "ksante"}
        for champion_id, slug in expected.items():
            self.assertEqual(directory.slug(champion_id), slug)
        self.assertEqual(champion_slug(None, "Nunu & Willump"), "nunu")
        self.assertEqual(champion_slug(None, "Renata Glasc"), "renata")
        self.assertEqual(champion_slug(None, "Kai'Sa"), "kaisa")

    def test_unknown_champion_is_an_error(self):
        with self.assertRaises(StatsError) as raised:
            ChampionDirectory.from_summary(SUMMARY).slug(99999)
        self.assertEqual(raised.exception.code, "unknown_champion")
        with self.assertRaises(StatsError):
            champion_slug("", "")


class RuneStatsTests(unittest.TestCase):
    def test_two_layouts_with_keystone_level_metrics(self):
        stats, _ = service()
        result = stats.runes(103, lane="middle")
        self.assertEqual([layout.selection for layout in result.layouts], ["win", "pick"])
        win, pick = result.layouts
        self.assertEqual((win.keystone, win.keystone_win_rate, win.games), (8992, 53.42, 20160))
        self.assertEqual((pick.keystone, pick.keystone_win_rate, pick.games), (8112, 52.8, 143965))
        self.assertEqual(pick.primary, (8112, 8139, 8140, 8106))
        self.assertEqual(pick.stat_mods, (5005, 5008, 5001))
        self.assertTrue(all(layout.metric_scope == "keystone_observation" for layout in result.layouts))
        self.assertIn("keystone_level_metrics", result.warnings)
        self.assertEqual((result.lane, result.patch), ("middle", "16.20"))
        catalog = StyleCatalog.from_payload(STYLES["styles"])
        for layout in result.layouts:
            self.assertEqual(validate_page(layout.to_page(catalog), catalog), [])

    def test_matchup_runes_against_the_opponent(self):
        stats, transport = service()
        result = stats.runes(103, lane="middle", opponent_id=1)
        self.assertEqual(result.opponent, "annie")
        self.assertTrue(result.matchup)
        self.assertTrue(all(layout.metric_scope == "keystone_observation" for layout in result.matchup))
        self.assertTrue(any("/vs/annie/" in url for url in transport.calls))

    def test_arena_has_no_rune_statistics(self):
        stats, transport = service([])
        with self.assertRaises(StatsError) as raised:
            stats.runes(103, mode="arena")
        self.assertEqual(raised.exception.code, "unsupported_mode")
        self.assertEqual(transport.calls, [])


class BuildStatsTests(unittest.TestCase):
    def test_general_builds_and_matchup_page(self):
        stats, _ = service()
        result = stats.builds(103, lane="middle", opponent_id=1)
        self.assertEqual([page.selection for page in result.pages], ["win", "pick", "vs"])
        self.assertEqual(result.warnings, ())


class AlternativesTests(unittest.TestCase):
    def test_other_builds_are_the_observed_trios_most_played_first(self):
        stats, _ = service()
        found = stats.alternatives(103, "ranked", "middle", frozenset({8112, 8992}))
        self.assertEqual([c.items for c in found.builds][0], (3118, 3020, 4645))
        self.assertEqual([c.games for c in found.builds], sorted((c.games for c in found.builds), reverse=True))
        self.assertTrue(all(len(c.items) == 3 for c in found.builds))
        # The trimmed fixture keeps only stat shard rows: no keystone among them.
        self.assertEqual(found.keystones, ())

    def test_keystones_come_from_the_rune_rows_of_the_first_slot(self):
        from types import SimpleNamespace

        from sexo2.services.stats import alternatives_from

        def row(rune, slot, games, wr=50.0):
            return SimpleNamespace(
                category="rune_statistics",
                identifiers=[str(rune), str(slot)],
                metrics={"win_rate": wr, "pick_rate": 1.0, "games": games},
                source_path="payload.runes.stats",
            )

        snapshot = SimpleNamespace(records=[row(8112, 0, 900), row(8128, 0, 4000), row(8139, 0, 9999), row(8112, 1, 5)])
        found = alternatives_from(snapshot, frozenset({8112, 8128}))
        self.assertEqual([(k.keystone, k.games) for k in found.keystones], [(8128, 4000), (8112, 900)])

    def test_an_identifier_that_is_not_an_integer_skips_its_row_instead_of_failing(self):
        from types import SimpleNamespace

        from sexo2.services.stats import alternatives_from

        def row(category, identifiers, games, path="payload.runes.stats"):
            return SimpleNamespace(
                category=category,
                identifiers=identifiers,
                metrics={"win_rate": 50.0, "pick_rate": 1.0, "games": games},
                source_path=path,
            )

        snapshot = SimpleNamespace(
            records=[
                row("rune_statistics", ["5008f", "0"], 900),  # a shard id with a suffix, seen in Swiftplay data
                row("rune_statistics", ["8128", "0"], 4000),
                row("rune_statistics", ["8128"], 10),  # a row without a slot
            ]
        )
        found = alternatives_from(snapshot, frozenset({8112, 8128}))
        self.assertEqual([(k.keystone, k.games) for k in found.keystones], [(8128, 4000)])

    def test_page_with_a_chosen_keystone_is_its_most_played_one(self):
        stats, transport = service()
        layout = stats.keystone_layout(103, "ranked", "middle", 8112)
        self.assertEqual((layout.selection, layout.keystone, layout.primary[0]), ("keystone", 8112, 8112))
        self.assertTrue(any("keystone=8112" in url for url in transport.calls))
        with self.assertRaises(StatsError):
            stats.keystone_layout(103, "arena", "all", 8112)


class SoloQueueRuleTests(unittest.TestCase):
    """D-147: whatever the game mode, the statistics are the Solo/Duo queue ones."""

    MODES = ("ranked", "aram", "swift")

    def urls(self, call):
        stats, transport = service()
        call(stats)
        return transport.calls

    def assert_solo(self, urls):
        self.assertTrue(urls)
        for url in urls:
            self.assertTrue(url.startswith("https://lolalytics.com/lol/ahri/build/q-data.json?"), url)
            self.assertNotIn("/aram/", url)
            self.assertNotIn("/swift/", url)
            self.assertNotIn("/arena/", url)

    def test_runes_builds_and_alternatives_ask_for_solo_queue_data_in_every_mode(self):
        for mode in self.MODES:
            with self.subTest(mode=mode):
                self.assert_solo(self.urls(lambda s: s.runes(103, mode, "middle")))
                self.assert_solo(self.urls(lambda s: s.builds(103, mode, "middle")))
                self.assert_solo(self.urls(lambda s: s.alternatives(103, mode, "middle", frozenset({8112}))))

    def test_the_result_says_it_is_solo_queue_data(self):
        stats, _ = service()
        for mode in self.MODES:
            self.assertEqual(stats.runes(103, mode, "middle").mode, "ranked")

    def test_a_mode_without_solo_queue_statistics_is_still_unsupported(self):
        stats, transport = service()
        for call in (
            lambda: stats.runes(103, "arena", "all"),
            lambda: stats.builds(103, "arena", "all"),
            lambda: stats.alternatives(103, "arena", "all", frozenset()),
            lambda: stats.keystone_layout(103, "arena", "all", 8112),
        ):
            with self.assertRaises(StatsError):
                call()
        self.assertEqual(transport.calls, [])

    def test_every_mode_can_load_another_keystones_page(self):
        for mode in self.MODES:
            with self.subTest(mode=mode):
                stats, transport = service()
                stats.keystone_layout(103, mode, "middle", 8112)
                self.assertTrue(all("/aram/" not in u and "/swift/" not in u for u in transport.calls))
                self.assertTrue(any("keystone=8112" in u for u in transport.calls))


class DefaultCacheTests(unittest.TestCase):
    def test_default_cache_lives_in_the_user_data_dir(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("utils.core.paths.get_user_data_dir", return_value=Path(folder)):
                stats = StatsService(ChampionDirectory.from_summary(SUMMARY))
            self.assertEqual(stats._client.ttl, Client(transport=FixtureTransport([])).ttl)
            self.assertTrue((Path(folder) / "lolalytics-cache").is_dir())


if __name__ == "__main__":
    unittest.main()
