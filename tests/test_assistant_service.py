"""Champion-select assistant wiring (sexo2/services/assistant.py) with fake client and statistics."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from sexo2.services.assistant import AssistantService, page_from_json, read_context
from sexo2.services.rune_rules import PageSpec
from sexo2.services.stats import BuildStats, RuneLayout, RuneStats, StatsError

STYLES = json.loads((Path(__file__).parent / "fixtures" / "lcu" / "perks-styles-representative.json").read_text())


def layout(selection, keystone, wr, games):
    return RuneLayout(selection, keystone, (keystone, 8139, 8140, 8106), (8226, 8210), (5005, 5008, 5001), wr, games)


def session(champion=103, position="middle", phase="FINALIZATION", session_id="cs-1"):
    return {
        "id": session_id,
        "localPlayerCellId": 2,
        "myTeam": [
            {"cellId": 1, "championId": 86},
            {"cellId": 2, "championId": champion, "assignedPosition": position},
        ],
        "theirTeam": [{"cellId": 5, "championId": 1}, {"cellId": 6, "championId": 0}],
        "timer": {"phase": phase},
    }


PERSONAL = {"title": "Minha Ahri", "uid": "personal-1", "associatedChampions": [103], "blocks": []}


class FakeLCU:
    def __init__(self):
        self.session = session()
        self.item_sets = {"accountId": 1, "itemSets": [copy.deepcopy(PERSONAL)], "timestamp": 1}
        self.puts = []

    def get(self, path, **kwargs):
        if path == "/lol-item-sets/v1/item-sets/7/sets":
            return copy.deepcopy(self.item_sets)
        return {
            "/lol-champ-select/v1/session": self.session,
            "/lol-perks/v1/styles": STYLES["styles"],
            "/lol-summoner/v1/current-summoner": {"summonerId": 7},
            "/lol-game-data/assets/v1/champion-summary.json": [
                {"id": 103, "alias": "Ahri", "name": "Ahri"},
                {"id": 86, "alias": "Garen", "name": "Garen"},
            ],
        }.get(path)

    def put(self, path, json_data, timeout, headers=None):
        self.puts.append(copy.deepcopy(json_data))
        self.item_sets = copy.deepcopy(json_data)
        return MagicMock(status_code=204)


class FakeStats:
    with_builds = False

    def __init__(self, directory):
        self.calls = []
        self.fail = None

    def runes(self, champion_id, mode, lane, opponent_id=None):
        self.calls.append(("runes", champion_id, mode, lane, opponent_id))
        if self.fail:
            raise self.fail
        return RuneStats(
            "ahri",
            mode,
            lane,
            "16.20",
            "u",
            "t",
            False,
            (layout("win", 8112, 56.8, 7505), layout("pick", 9923, 52.1, 41212)),
            opponent="annie" if opponent_id else None,
            matchup=(layout("win", 8128, 55.9, 1606),) if opponent_id else (),
        )

    def builds(self, champion_id, mode, lane, opponent_id=None):
        self.calls.append(("builds", champion_id, mode, lane, opponent_id))
        if not self.with_builds:
            return BuildStats(pages=())
        from tests.test_item_sets import ahri_pages, annie_matchup

        pages = tuple(ahri_pages()) + ((annie_matchup(),) if opponent_id else ())
        return BuildStats(pages=pages)


class InlineWorker:
    def submit(self, work, on_error):
        try:
            work()
        except Exception as error:
            on_error(error)
        return True


class FakeController:
    def __init__(self):
        self.calls = []
        from sexo2.services.rune_import import RuneImportSnapshot

        self.snap = RuneImportSnapshot(None, (), None, None, False, None)

    def __getattr__(self, name):
        return lambda *args: (self.calls.append((name, *args)), self.snap)[1]

    def snapshot(self):
        return self.snap


class AssistantServiceTests(unittest.TestCase):
    def setUp(self):
        self.lcu = FakeLCU()
        self.published = []
        self.queue = 420
        self.stats = None

        def factory(directory):
            self.stats = FakeStats(directory)
            return self.stats

        self.controller = FakeController()
        self.service = AssistantService(
            self.lcu,
            self.published.append,
            queue_id=lambda: self.queue,
            in_champ_select=lambda: True,
            stats_factory=factory,
            worker=InlineWorker(),
            controller=self.controller,
        )

    def test_context_reads_the_local_player_and_maps_queue_and_position(self):
        context = read_context(session(position="utility"), 440)
        self.assertEqual(
            (context.champion_id, context.lane, context.mode, context.enemies), (103, "support", "ranked", (1,))
        )
        self.assertTrue(context.can_edit)
        self.assertFalse(read_context(session(phase="GAME_STARTING"), 420).can_edit)
        self.assertIsNone(read_context(session(champion=0), 420))
        self.assertIsNone(read_context(session(session_id=""), 420))
        self.assertIsNone(read_context(session(), 1700).mode)

    def test_request_shows_recommendations_without_importing(self):
        self.service.handle({"type": "assistant-request"})
        state = self.published[-1]
        self.assertEqual([r["selection"] for r in state["runes"]["general"]], ["win", "pick"])
        self.assertEqual(state["runes"]["general"][0]["keystoneWinRate"], 56.8)
        names = [c[0] for c in self.controller.calls]
        self.assertIn("display", names)
        self.assertNotIn("choose", names)
        self.assertEqual(self.stats.calls[-1], ("runes", 103, "ranked", "middle", None))

    def test_choosing_a_card_imports_that_layout(self):
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-runes-choose", "selection": "pick"})
        name, page = self.controller.calls[-1]
        self.assertEqual(name, "choose")
        self.assertEqual(page.perk_ids[0], 9923)

    def test_matchup_card_needs_a_chosen_opponent(self):
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-runes-choose", "selection": "win", "matchup": True})
        self.assertEqual(self.published[-1]["error"], "unknown_recommendation")
        self.service.handle({"type": "assistant-opponent", "championId": 1})
        self.service.handle({"type": "assistant-runes-choose", "selection": "win", "matchup": True})
        self.assertEqual(self.controller.calls[-1][1].perk_ids[0], 8128)

    def test_edit_parses_the_page(self):
        self.service.handle(
            {"type": "assistant-runes-edit", "page": {"primary": 8100, "sub": 8200, "perks": [1, 2, 3]}}
        )
        self.assertEqual(self.controller.calls[-1], ("edit", PageSpec(8100, 8200, (1, 2, 3))))
        with self.assertRaises(ValueError):
            page_from_json({"primary": True, "sub": 8200, "perks": []})

    def test_unsupported_queue_and_statistics_errors_are_reported(self):
        self.queue = 1700
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(self.published[-1]["error"], "unsupported_mode")
        self.queue = 420
        self.service.handle({"type": "assistant-request"})
        self.stats.fail = StatsError("unknown_champion", "x")
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(self.published[-1]["error"], "stats_unknown_champion")
        self.assertEqual(self.published[-1]["runes"]["general"], [])

    def test_leaving_champion_select_clears_the_session(self):
        self.service.handle({"type": "assistant-request"})
        self.lcu.session = None
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(self.controller.calls[-1], ("set_session", None))
        self.assertIsNone(self.published[-1]["championId"])

    def test_items_without_builds_report_it(self):
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-items-import"})
        self.assertEqual(self.published[-1]["items"], {"error": "no_builds"})


class AutomaticItemImportTests(unittest.TestCase):
    def setUp(self):
        FakeStats.with_builds = True
        self.addCleanup(setattr, FakeStats, "with_builds", False)
        self.lcu = FakeLCU()
        self.published = []
        self.queue = 420
        self.timers = []
        self.service = AssistantService(
            self.lcu,
            self.published.append,
            queue_id=lambda: self.queue,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            controller=FakeController(),
            schedule=lambda delay, action: self.timers.append(action),
        )

    def fire(self):
        timers, self.timers = self.timers, []
        for action in timers:
            action()

    def managed(self):
        return [s for s in self.lcu.item_sets["itemSets"] if s.get("uid") == "sexo2-managed"]

    def test_lock_imports_the_set_without_opening_the_panel(self):
        self.service.champion_confirmed(103)
        self.assertEqual(self.lcu.puts, [])  # debounced
        self.fire()
        self.assertEqual(len(self.lcu.puts), 1)
        (item_set,) = self.managed()
        self.assertEqual(item_set["title"], "SEXO2 — Ahri")
        self.assertEqual(len(item_set["blocks"]), 6)
        self.assertEqual(self.lcu.item_sets["itemSets"][0], PERSONAL)
        self.assertTrue(self.published[-1]["items"]["confirmed"])

    def test_repeated_confirmation_of_the_same_champion_does_not_rewrite(self):
        self.service.champion_confirmed(103)
        self.fire()
        self.service.champion_confirmed(103)
        self.fire()
        self.assertEqual(len(self.lcu.puts), 1)

    def test_quick_trade_writes_only_the_latest_champion(self):
        self.service.champion_confirmed(103)
        self.lcu.session = session(champion=86)
        self.service.champion_confirmed(86)
        self.fire()
        self.assertEqual(len(self.lcu.puts), 1)
        self.assertEqual(self.managed()[0]["title"], "SEXO2 — Garen")
        self.assertEqual(self.managed()[0]["associatedChampions"], [86])

    def test_champion_change_reuses_the_same_managed_set(self):
        self.service.champion_confirmed(103)
        self.fire()
        self.lcu.session = session(champion=86)
        self.service.champion_confirmed(86)
        self.fire()
        self.assertEqual(len(self.lcu.puts), 2)
        self.assertEqual(len(self.managed()), 1)
        self.assertEqual(self.managed()[0]["associatedChampions"], [86])

    def test_provisional_or_other_players_champion_is_not_imported(self):
        provisional = session(champion=0)
        provisional["myTeam"][1]["championPickIntent"] = 103
        self.lcu.session = provisional
        self.service.champion_confirmed(103)
        self.fire()
        self.lcu.session = session()
        self.service.champion_confirmed(86)  # not the local player's champion
        self.fire()
        self.assertEqual(self.lcu.puts, [])

    def test_swiftplay_choice_imports_without_a_champ_select_session(self):
        self.queue = 480
        self.lcu.session = None
        self.service.champion_confirmed(103, swiftplay=True)
        self.fire()
        self.assertEqual(len(self.lcu.puts), 1)
        self.assertEqual(self.service._stats.calls[-1], ("builds", 103, "swift", "all", None))

    def test_unsupported_mode_writes_nothing(self):
        self.queue = 1700
        self.service.champion_confirmed(103)
        self.fire()
        self.assertEqual(self.lcu.puts, [])
        self.assertEqual(self.published[-1]["items"], {"error": "unsupported_mode"})

    def test_choosing_an_opponent_rewrites_with_the_counter_group(self):
        self.service.champion_confirmed(103)
        self.fire()
        self.service.handle({"type": "assistant-opponent", "championId": 1})
        self.fire()
        self.assertEqual(len(self.lcu.puts), 2)
        types = [block["type"] for block in self.managed()[0]["blocks"]]
        self.assertEqual(types[6], "Counter Annie — 49,57% — 1.852 partidas")


if __name__ == "__main__":
    unittest.main()
