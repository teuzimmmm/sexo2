"""The favourite builds file (sexo2/services/favorite_builds.py)."""

import json
import tempfile
import unittest
from pathlib import Path

from sexo2.services.favorite_builds import FavoriteBuilds, group_for

PAGE = {"primary": 8100, "sub": 8200, "perks": [8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001]}


class FavoriteBuildsTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(self.enterContext(tempfile.TemporaryDirectory())) / "assistant-favorites.json"

    def test_saved_per_mode_and_read_back_by_a_new_process(self):
        favorites = FavoriteBuilds(self.path)
        favorites.set_runes("sr", 103, PAGE)
        favorites.set_items("aram", 103, [3118, 3020, 4645])
        again = FavoriteBuilds(self.path)
        self.assertEqual(again.get("sr", 103), {"runes": PAGE, "items": None})
        self.assertEqual(again.get("aram", 103), {"runes": None, "items": [3118, 3020, 4645]})
        self.assertEqual(again.get("sr", 86), {"runes": None, "items": None})

    def test_unpinning_removes_the_entry(self):
        favorites = FavoriteBuilds(self.path)
        favorites.set_items("sr", 103, [3118, 3020, 4645])
        favorites.set_items("sr", 103, None)
        self.assertEqual(json.loads(self.path.read_text())["sr"], {})

    def test_malformed_values_are_not_stored(self):
        favorites = FavoriteBuilds(self.path)
        favorites.set_items("sr", 103, ["3118", True])
        favorites.set_runes("sr", 103, {"primary": 8100})
        self.assertEqual(favorites.get("sr", 103), {"runes": None, "items": None})

    def test_an_unreadable_file_starts_empty(self):
        self.path.write_text("{", encoding="utf-8")
        self.assertEqual(FavoriteBuilds(self.path).get("sr", 103), {"runes": None, "items": None})

    def test_mode_groups(self):
        self.assertEqual([group_for(m) for m in ("ranked", "swift", "aram", None)], ["sr", "sr", "aram", None])


if __name__ == "__main__":
    unittest.main()
