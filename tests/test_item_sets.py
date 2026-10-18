"""The SEXO2 item set from LoLalytics fixtures, merged into a fake client document."""

import copy
import json
import re
import unittest
from unittest import mock
from pathlib import Path
from unittest.mock import MagicMock

from lcu.features.lcu_item_sets import ItemSetsError, LCUItemSets, sets_path
from lolalytics.client import Client
from lolalytics.matchups import build_matchup_page
from lolalytics.parsing import parse_page
from lolalytics.query import Query
from sexo2.services.item_sets import MANAGED_UID, build_item_set, import_item_set, is_managed, merge_item_sets

LOLALYTICS = Path(__file__).parent / "fixtures" / "lolalytics"
KEYSTONE = LOLALYTICS / "keystone"
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


def annie_matchup():
    query = Query("ahri", lane="middle", opponent="annie", opponent_lane="middle")
    body = (LOLALYTICS / "matchups" / "ahri-vs-annie.json").read_bytes()
    return build_matchup_page(parse_page(body, query, query.url, "2026-10-16T00:00:00Z"))


def ahri_set(with_matchup=True):
    win, pick = ahri_pages()
    return build_item_set(AHRI, win, pick, annie_matchup() if with_matchup else None)


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
LEGACY_MANAGED = {**copy.deepcopy(PERSONAL), "uid": "sexo2-1-1", "title": "SEXO2 Builds de Annie"}
# Personal set whose title imitates ours: it stays, because only the uid counts.
LOOKALIKE = {**copy.deepcopy(PERSONAL), "uid": "6f1e2d1c-0000-4000-8000-000000000002", "title": "SEXO2 — Ahri"}


def document(*sets):
    return {"accountId": 42, "itemSets": [copy.deepcopy(item) for item in sets], "timestamp": 1700000000000}


class ItemPageTests(unittest.TestCase):
    def test_nine_sections_in_the_approved_order_and_titles(self):
        item_set = ahri_set()
        self.assertEqual(item_set["title"], "SEXO2 — Ahri")
        self.assertEqual(
            [block["type"] for block in item_set["blocks"]],
            [
                "59,3% — 1.077 partidas",
                "Itens iniciais",
                "Alternativas",
                "53,6% — 26.214 partidas",
                "Itens iniciais",
                "Alternativas",
                "Counter Annie — 49,57% — 1.852 partidas",
                "Itens iniciais",
                "Alternativas",
            ],
        )

    def test_no_forbidden_words_in_titles(self):
        forbidden = re.compile(r"Bloco|Build|Maior WR|Mais comum|Core|Item \d", re.IGNORECASE)
        for block in ahri_set()["blocks"]:
            self.assertIsNone(forbidden.search(block["type"]), block["type"])

    def test_sequence_keeps_the_core_trio_first_then_one_item_per_later_slot(self):
        blocks = ahri_set()["blocks"]
        ids = lambda block: [item["id"] for item in block["items"]]  # noqa: E731
        # Highest WR: core 3118 3020 3100, then the best WR per slot with >= 100 games, no repeats.
        self.assertEqual(ids(blocks[0]), ["3118", "3020", "3100", "3041", "4645", "3089"])
        # Most played: core 3118 3020 4645, then the most played free choice per slot.
        self.assertEqual(ids(blocks[3]), ["3118", "3020", "4645", "3157", "3089", "3135"])
        # Matchup: item1-3 of that summary, then slots 4-6 (most played when none reaches 100 games).
        self.assertEqual(ids(blocks[6]), ["6655", "3158", "3041", "4645", "3157", "3089"])
        self.assertEqual(blocks[1]["items"], [{"id": "1056", "count": 1}, {"id": "2003", "count": 2}])

    def test_alternatives_never_repeat_the_sequence(self):
        blocks = ahri_set()["blocks"]
        for sequence, alternatives in ((blocks[0], blocks[2]), (blocks[3], blocks[5]), (blocks[6], blocks[8])):
            self.assertFalse({i["id"] for i in sequence["items"]} & {i["id"] for i in alternatives["items"]})

    def test_without_a_matchup_the_counter_group_is_left_out(self):
        types = [block["type"] for block in ahri_set(with_matchup=False)["blocks"]]
        self.assertEqual(len(types), 6)
        self.assertFalse(any(t.startswith("Counter") for t in types))

    def test_single_managed_set_for_every_map(self):
        item_set = ahri_set()
        self.assertEqual(item_set["uid"], MANAGED_UID)
        self.assertEqual(item_set["associatedChampions"], [AHRI])
        self.assertEqual(item_set["associatedMaps"], [])
        self.assertEqual(
            {key: item_set[key] for key in ("type", "map", "mode", "startedFrom", "preferredItemSlots")},
            {"type": "custom", "map": "any", "mode": "any", "startedFrom": "blank", "preferredItemSlots": []},
        )

    def test_invalid_champion_is_rejected(self):
        win, pick = ahri_pages()
        with self.assertRaises(ValueError):
            build_item_set(0, win, pick)


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.new_set = ahri_set()

    def test_personal_sets_stay_byte_for_byte_and_legacy_sets_go(self):
        old = {**copy.deepcopy(PERSONAL), "uid": MANAGED_UID, "title": "SEXO2 — Annie"}
        before = document(PERSONAL, old, LEGACY_MANAGED, LOOKALIKE)
        snapshot = json.dumps(before)
        merged = merge_item_sets(before, self.new_set)
        self.assertEqual(json.dumps(before), snapshot)  # input untouched
        self.assertEqual(json.dumps(merged["itemSets"][0]), json.dumps(PERSONAL))
        self.assertEqual(merged["itemSets"][1], self.new_set)  # reused in place
        self.assertEqual(json.dumps(merged["itemSets"][2]), json.dumps(LOOKALIKE))
        self.assertEqual(len(merged["itemSets"]), 3)
        self.assertEqual((merged["accountId"], merged["timestamp"]), (42, 1700000000000))

    def test_merging_twice_or_for_another_champion_keeps_one_managed_set(self):
        once = merge_item_sets(document(PERSONAL), self.new_set)
        self.assertEqual(once, merge_item_sets(once, self.new_set))
        annie = {**self.new_set, "title": "SEXO2 — Annie", "associatedChampions": [1]}
        other = merge_item_sets(once, annie)
        self.assertEqual([is_managed(item) for item in other["itemSets"]], [False, True])

    def test_rejects_a_set_without_the_managed_uid(self):
        with self.assertRaises(ValueError):
            merge_item_sets(document(), PERSONAL)
        with self.assertRaises(ItemSetsError):
            merge_item_sets({"itemSets": None}, self.new_set)


class FakeClientApi:
    """Stores the document like the client; ``mutate`` alters what is stored."""

    def __init__(self, stored, summoner=7, status=204):
        self.stored = stored
        self.summoner = summoner
        self.status = status
        self.puts = []
        self.mutate = None
        self.on_read = None
        self.reads = 0

    def get(self, path, timeout=1.0, cache_ttl=None, use_cache=True):
        assert use_cache is False
        if path == "/lol-summoner/v1/current-summoner":
            return {"summonerId": self.summoner}
        if path == sets_path(self.summoner):
            self.reads += 1
            if self.on_read:
                self.on_read(self)
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
        self.new_set = ahri_set()
        patcher = mock.patch("sexo2.services.item_sets.sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def test_defaults_the_client_adds_on_storing_still_confirm(self):
        api = FakeClientApi(document(PERSONAL))

        def client_defaults(stored):
            for item_set in stored["itemSets"]:
                for block in item_set["blocks"]:
                    block.setdefault("hideIfSummonerSpell", "")
                    block.setdefault("showIfSummonerSpell", "")
                    for item in block["items"]:
                        item["id"] = str(item["id"])
                item_set["associatedChampions"] = [int(c) for c in item_set["associatedChampions"]]

        api.mutate = client_defaults
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertEqual((result.confirmed, result.error), (True, None))

    def test_a_stale_read_right_after_the_write_is_read_again(self):
        api = FakeClientApi(document(PERSONAL))

        def stale_once(fake):
            if fake.puts and fake.reads == 3:  # first read after the write
                fake.stale, fake.stored = fake.stored, document(PERSONAL)
            elif getattr(fake, "stale", None):
                fake.stored, fake.stale = fake.stale, None

        api.on_read = stale_once
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertTrue(result.confirmed)
        self.sleep.assert_called_once()

    def test_import_writes_merge_and_confirms_by_read_back(self):
        api = FakeClientApi(document(PERSONAL))
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertEqual((result.confirmed, result.written, result.error), (True, True, None))
        self.assertEqual(api.puts[0][0], "/lol-item-sets/v1/item-sets/7/sets")
        self.assertEqual(api.stored["itemSets"][0], PERSONAL)

    def test_unchanged_document_is_not_rewritten(self):
        api = FakeClientApi(merge_item_sets(document(PERSONAL), self.new_set))
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertEqual((result.confirmed, result.written), (True, False))
        self.assertEqual(api.puts, [])

    def test_an_edit_between_reads_restarts_the_merge_from_the_newer_document(self):
        api = FakeClientApi(document(PERSONAL))
        edited = {**copy.deepcopy(PERSONAL), "title": "Minha Ahri 2"}

        def user_edits(fake):
            if fake.reads == 2:
                fake.stored = document(edited)

        api.on_read = user_edits
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertTrue(result.confirmed)
        self.assertEqual(api.stored["itemSets"][0], edited)

    def test_constant_edits_give_up_without_writing(self):
        api = FakeClientApi(document(PERSONAL))

        def user_edits(fake):
            fake.stored = document({**copy.deepcopy(PERSONAL), "title": f"edição {fake.reads}"})

        api.on_read = user_edits
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertEqual((result.confirmed, result.written, result.error), (False, False, "concurrent_edit"))
        self.assertEqual(api.puts, [])

    def test_read_back_that_changed_a_personal_set_is_not_confirmed(self):
        api = FakeClientApi(document(PERSONAL))
        api.mutate = lambda stored: stored["itemSets"][0].update(title="changed")
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertEqual((result.confirmed, result.error), (False, "not_confirmed"))

    def test_read_back_without_the_managed_set_is_not_confirmed(self):
        api = FakeClientApi(document(PERSONAL))
        api.mutate = lambda stored: stored.update(itemSets=stored["itemSets"][:1])
        self.assertFalse(import_item_set(LCUItemSets(api), self.new_set).confirmed)

    def test_rejected_write_or_missing_summoner_is_an_error_and_deletes_nothing(self):
        api = FakeClientApi(document(PERSONAL), status=500)
        result = import_item_set(LCUItemSets(api), self.new_set)
        self.assertEqual((result.confirmed, result.error), (False, "lcu_rejected"))
        self.assertEqual(api.stored, document(PERSONAL))
        api = FakeClientApi(document(PERSONAL), summoner=0)
        self.assertEqual(import_item_set(LCUItemSets(api), self.new_set).error, "lcu_schema")


if __name__ == "__main__":
    unittest.main()
