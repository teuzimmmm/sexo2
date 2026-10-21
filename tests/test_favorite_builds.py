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

    def test_a_favourite_belongs_to_its_lane(self):
        favorites = FavoriteBuilds(self.path)
        favorites.set_items("sr", 103, [1001, 1002, 1003], "middle")
        favorites.set_items("sr", 103, [2001, 2002, 2003], "top")
        again = FavoriteBuilds(self.path)
        self.assertEqual(again.get("sr", 103, "middle")["items"], [1001, 1002, 1003])
        self.assertEqual(again.get("sr", 103, "top")["items"], [2001, 2002, 2003])
        self.assertIsNone(again.get("sr", 103, "jungle")["items"])
        self.assertIsNone(again.get("sr", 103)["items"])  # no lane is a different slot
        self.assertEqual(sorted(json.loads(self.path.read_text())["sr"]), ["103:middle", "103:top"])

    def test_unpinning_one_lane_keeps_the_others(self):
        favorites = FavoriteBuilds(self.path)
        favorites.set_runes("sr", 103, PAGE, "middle")
        favorites.set_runes("sr", 103, PAGE, "top")
        favorites.set_runes("sr", 103, None, "middle")
        self.assertIsNone(favorites.get("sr", 103, "middle")["runes"])
        self.assertEqual(favorites.get("sr", 103, "top")["runes"], PAGE)

    def test_favourites_saved_before_lanes_still_read_as_no_lane(self):
        self.path.write_text(json.dumps({"version": 1, "sr": {"103": {"items": [1001, 1002, 1003]}}}))
        favorites = FavoriteBuilds(self.path)
        self.assertEqual(favorites.get("sr", 103)["items"], [1001, 1002, 1003])
        self.assertIsNone(favorites.get("sr", 103, "middle")["items"])

    def test_an_unknown_lane_name_is_the_slot_without_a_lane(self):
        favorites = FavoriteBuilds(self.path)
        favorites.set_items("sr", 103, [1001, 1002, 1003], "everywhere")
        self.assertEqual(favorites.get("sr", 103)["items"], [1001, 1002, 1003])

    def test_mode_groups(self):
        self.assertEqual([group_for(m) for m in ("ranked", "swift", "aram", None)], ["sr", "sr", "aram", None])


if __name__ == "__main__":
    unittest.main()
