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


class DefaultCacheTests(unittest.TestCase):
    def test_default_cache_lives_in_the_user_data_dir(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("utils.core.paths.get_user_data_dir", return_value=Path(folder)):
                stats = StatsService(ChampionDirectory.from_summary(SUMMARY))
            self.assertEqual(stats._client.ttl, Client(transport=FixtureTransport([])).ttl)
            self.assertTrue((Path(folder) / "lolalytics-cache").is_dir())


if __name__ == "__main__":
    unittest.main()
