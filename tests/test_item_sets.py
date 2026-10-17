"""Item sets from LoLalytics fixtures, merged into a fake client document."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from lcu.features.lcu_item_sets import ItemSetsError, LCUItemSets, sets_path
from lolalytics.client import Client
from lolalytics.query import Query
from sexo2.services.item_sets import (
    MANAGED_TITLE_PREFIX,
    build_item_sets,
    import_item_sets,
    is_managed,
    managed_uid,
    merge_item_sets,
)

KEYSTONE = Path(__file__).parent / "fixtures" / "lolalytics" / "keystone"
KEYSTONE_MANIFEST = json.loads((KEYSTONE / "manifest.json").read_text())
AHRI = 103


class FixtureTransport:
    def __init__(self, names):
        self.bodies = {}
        for row in KEYSTONE_MANIFEST:
            if row["fixture"] in names:
                body = (KEYSTONE / row["fixture"]).read_bytes()
                for patch in (row["filters"]["patch"], None):
                    self.bodies[Query(**{**row["filters"], "patch": patch}).url] = body

    def get(self, url):
        if url not in self.bodies:
            raise AssertionError(f"unexpected offline URL: {url}")
        return self.bodies[url]

    def close(self):
        pass


def ahri_pages():
    transport = FixtureTransport({"ahri-ranked-base.json", "ahri-ranked-win.json", "ahri-ranked-pick.json"})
    return Client(transport=transport, ttl=0).collect_builds(Query("ahri", lane="middle")).pages


PERSONAL = {
    "title": "Minha Ahri",
    "associatedChampions": [AHRI],
    "associatedMaps": [11],
    "blocks": [{"type": "Começo", "items": [{"id": "1056", "count": 1}], "hideIfSummonerSpell": ""}],
    "uid": "6f1e2d1c-0000-4000-8000-000000000001",
    "sortrank": 3,
    "type": "custom",
    "map": "SR",
    "mode": "CLASSIC",
    "startedFrom": "blank",
    "preferredItemSlots": [],
    "unknownFutureField": {"kept": True},
}
OTHER_CHAMPION_MANAGED = {**copy.deepcopy(PERSONAL), "uid": managed_uid(1, 1), "title": "SEXO2 Annie"}


def document(*sets):
    return {"accountId": 42, "itemSets": [copy.deepcopy(item) for item in sets], "timestamp": 1700000000000}


class BuildItemSetsTests(unittest.TestCase):
    def test_blocks_follow_the_observed_build_without_combined_win_rates(self):
        sets = build_item_sets(AHRI, ahri_pages(), map_ids=[11])
        self.assertEqual(len(sets), 1)
        item_set = sets[0]
        self.assertEqual(item_set["uid"], managed_uid(AHRI, 1))
        self.assertTrue(item_set["title"].startswith(MANAGED_TITLE_PREFIX))
        self.assertEqual(item_set["associatedChampions"], [AHRI])
        self.assertEqual(item_set["associatedMaps"], [11])
        self.assertEqual(
            {key: item_set[key] for key in ("type", "map", "mode", "startedFrom", "preferredItemSlots")},
            {"type": "custom", "map": "any", "mode": "any", "startedFrom": "blank", "preferredItemSlots": []},
        )
        labels = [block["type"] for block in item_set["blocks"]]
        self.assertIn("WR · Core", labels)
        self.assertIn("Common · Core", labels)
        self.assertFalse(any("%" in label for label in labels))
        core = next(block for block in item_set["blocks"] if block["type"] == "WR · Core")
        self.assertEqual(len(core["items"]), 3)
        self.assertTrue(all(isinstance(item["id"], str) and item["count"] == 1 for item in core["items"]))

    def test_invalid_champion_is_rejected(self):
        with self.assertRaises(ValueError):
            build_item_sets(0, ahri_pages())


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.new_sets = build_item_sets(AHRI, ahri_pages())

    def test_personal_and_other_champion_sets_stay_byte_for_byte(self):
        old_managed = {**copy.deepcopy(PERSONAL), "uid": managed_uid(AHRI, 1), "title": "SEXO2 old"}
        before = document(PERSONAL, old_managed, OTHER_CHAMPION_MANAGED)
        snapshot = json.dumps(before, sort_keys=False)
        merged = merge_item_sets(before, AHRI, self.new_sets)
        self.assertEqual(json.dumps(before, sort_keys=False), snapshot)  # input untouched
        kept = [item for item in merged["itemSets"] if not is_managed(item, AHRI)]
        self.assertEqual(json.dumps(kept), json.dumps([PERSONAL, OTHER_CHAMPION_MANAGED]))
        self.assertEqual((merged["accountId"], merged["timestamp"]), (42, 1700000000000))
        managed = [item for item in merged["itemSets"] if is_managed(item, AHRI)]
        self.assertEqual(managed, self.new_sets)

    def test_merging_twice_does_not_duplicate(self):
        once = merge_item_sets(document(PERSONAL), AHRI, self.new_sets)
        twice = merge_item_sets(once, AHRI, self.new_sets)
        self.assertEqual(once, twice)
        uids = [item["uid"] for item in twice["itemSets"]]
        self.assertEqual(len(uids), len(set(uids)))

    def test_rejects_unmanaged_or_duplicate_new_sets(self):
        with self.assertRaises(ValueError):
            merge_item_sets(document(), AHRI, [PERSONAL])
        with self.assertRaises(ValueError):
            merge_item_sets(document(), AHRI, self.new_sets + self.new_sets)
        with self.assertRaises(ItemSetsError):
            merge_item_sets({"itemSets": None}, AHRI, self.new_sets)


class FakeClientApi:
    """Stores the document like the client; ``mutate`` alters what is stored."""

    def __init__(self, stored, summoner=7, status=204):
        self.stored = stored
        self.summoner = summoner
        self.status = status
        self.puts = []
        self.mutate = None

    def get(self, path, timeout=1.0, cache_ttl=None, use_cache=True):
        assert use_cache is False
        if path == "/lol-summoner/v1/current-summoner":
            return {"summonerId": self.summoner}
        if path == sets_path(self.summoner):
            return copy.deepcopy(self.stored)
        return None

    def put(self, path, json_data, timeout, headers=None):
        self.puts.append((path, copy.deepcopy(json_data)))
        if 200 <= self.status < 300:
            self.stored = copy.deepcopy(json_data)
            if self.mutate:
                self.mutate(self.stored)
        return MagicMock(status_code=self.status)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.new_sets = build_item_sets(AHRI, ahri_pages())

    def test_import_writes_merge_and_confirms_by_read_back(self):
        api = FakeClientApi(document(PERSONAL))
        result = import_item_sets(LCUItemSets(api), AHRI, self.new_sets)
        self.assertEqual((result.confirmed, result.written, result.error), (True, True, None))
        self.assertEqual(api.puts[0][0], "/lol-item-sets/v1/item-sets/7/sets")
        self.assertEqual(api.stored["itemSets"][0], PERSONAL)

    def test_unchanged_document_is_not_rewritten(self):
        api = FakeClientApi(merge_item_sets(document(PERSONAL), AHRI, self.new_sets))
        result = import_item_sets(LCUItemSets(api), AHRI, self.new_sets)
        self.assertEqual((result.confirmed, result.written), (True, False))
        self.assertEqual(api.puts, [])

    def test_read_back_that_changed_a_personal_set_is_not_confirmed(self):
        api = FakeClientApi(document(PERSONAL))
        api.mutate = lambda stored: stored["itemSets"][0].update(title="changed")
        result = import_item_sets(LCUItemSets(api), AHRI, self.new_sets)
        self.assertEqual((result.confirmed, result.error), (False, "not_confirmed"))

    def test_read_back_without_the_managed_set_is_not_confirmed(self):
        api = FakeClientApi(document(PERSONAL))
        api.mutate = lambda stored: stored.update(itemSets=stored["itemSets"][:1])
        self.assertFalse(import_item_sets(LCUItemSets(api), AHRI, self.new_sets).confirmed)

    def test_rejected_write_or_missing_summoner_is_an_error(self):
        api = FakeClientApi(document(PERSONAL), status=500)
        result = import_item_sets(LCUItemSets(api), AHRI, self.new_sets)
        self.assertEqual((result.confirmed, result.error), (False, "lcu_rejected"))
        self.assertEqual(api.stored, document(PERSONAL))
        api = FakeClientApi(document(PERSONAL), summoner=0)
        self.assertEqual(import_item_sets(LCUItemSets(api), AHRI, self.new_sets).error, "lcu_schema")


if __name__ == "__main__":
    unittest.main()
