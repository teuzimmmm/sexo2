"""Champion-select assistant wiring (sexo2/services/assistant.py) with fake client and statistics."""

import json
import unittest
from pathlib import Path

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


class FakeLCU:
    def __init__(self):
        self.session = session()

    def get(self, path, **kwargs):
        return {
            "/lol-champ-select/v1/session": self.session,
            "/lol-perks/v1/styles": STYLES["styles"],
            "/lol-game-data/assets/v1/champion-summary.json": [{"id": 103, "alias": "Ahri", "name": "Ahri"}],
        }.get(path)


class FakeStats:
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
        return BuildStats(pages=())


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
        self.service.handle({"type": "assistant-items-import", "selections": ["win"]})
        self.assertEqual(self.published[-1]["items"], {"error": "no_builds"})

    def test_builds_are_published_for_display_only_when_requested(self):
        from lolalytics.builds import BuildPage, ItemBlock, ItemChoice

        block = ItemBlock(
            "starting",
            [ItemChoice("1055", 1, {"win_rate": 51.0, "games": 90}, {})],
            {"win_rate": 52.0, "games": 100},
            "p",
            False,
        )
        page = BuildPage("win", "WR", "t", 8112, {}, [block], {}, "u", {}, {}, "now", False, [])
        self.stats = None
        self.service.handle({"type": "assistant-request"})
        self.assertIsNone(self.published[-1]["builds"])
        self.stats.builds = lambda *args, **kwargs: BuildStats(pages=(page,))
        self.service.handle({"type": "assistant-items-request"})
        build = self.published[-1]["builds"][0]
        self.assertEqual(build["selection"], "win")
        self.assertEqual(
            build["blocks"][0],
            {"kind": "starting", "winRate": 52.0, "games": 100, "items": [{"id": "1055", "count": 1, "winRate": 51.0}]},
        )


if __name__ == "__main__":
    unittest.main()
