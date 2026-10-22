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
        self.ranked = {}
        self.ranked_calls = []
        self.history = {}
        self.history_calls = []
        self.region = {"region": "BR", "locale": "pt_BR"}

    def get(self, path, **kwargs):
        if path == "/lol-item-sets/v1/item-sets/7/sets":
            return copy.deepcopy(self.item_sets)
        if path == "/riotclient/region-locale":
            if isinstance(self.region, Exception):
                raise self.region
            return copy.deepcopy(self.region)
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

    def match_history(self, puuid, count=20, timeout=2.0):
        self.history_calls.append(puuid)
        value = self.history.get(puuid)
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def ranked_stats(self, puuid, timeout=1.0):
        self.ranked_calls.append(puuid)
        value = self.ranked.get(puuid)
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


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

    def alternatives(self, champion_id, mode, lane, keystones):
        from sexo2.services.stats import Alternatives, ItemCombo, KeystoneStat

        self.keystone_ids = keystones
        return Alternatives(
            (ItemCombo((3118, 3020, 4645), 53.64, 17.45, 29091), ItemCombo((2503, 3158, 3100), 56.8, 4.5, 7505)),
            (KeystoneStat(8112, 52.8, 60.0, 143965), KeystoneStat(8128, 54.0, 3.0, 4000)),
        )

    def keystone_layout(self, champion_id, mode, lane, keystone):
        self.calls.append(("keystone", champion_id, mode, lane, keystone))
        from dataclasses import replace

        return replace(layout("pick", keystone, 54.0, 4000), selection="keystone")


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
        self.assertFalse(self.published[-1]["supported"])
        self.queue = 3140  # Practice Tool uses the ranked statistics
        self.service.handle({"type": "assistant-request"})
        self.assertTrue(self.published[-1]["supported"])
        self.assertEqual(self.stats.calls[-1][2], "ranked")
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

    def test_lane_chosen_in_the_panel_holds_for_the_session(self):
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-lane", "lane": "top"})
        self.assertEqual(self.stats.calls[-1], ("runes", 103, "ranked", "top", None))
        self.assertEqual(self.published[-1]["lane"], "top")
        self.lcu.session = session(session_id="cs-2")
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(self.published[-1]["lane"], "middle")
        with self.assertRaises(ValueError):
            self.service.handle({"type": "assistant-lane", "lane": "mid"})

    def test_items_without_builds_report_it(self):
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-items-import"})
        self.assertEqual(self.published[-1]["items"], {"error": "no_builds"})


class AlternativeChoicesTests(unittest.TestCase):
    def setUp(self):
        FakeStats.with_builds = True
        self.addCleanup(setattr, FakeStats, "with_builds", False)
        self.lcu = FakeLCU()
        self.published = []
        self.controller = FakeController()
        self.service = AssistantService(
            self.lcu,
            self.published.append,
            queue_id=lambda: 420,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            controller=self.controller,
        )
        self.service.handle({"type": "assistant-request"})

    def managed(self):
        return next(s for s in self.lcu.item_sets["itemSets"] if s["uid"] == "sexo2-managed")

    def test_state_lists_other_builds_and_keystones(self):
        options = self.published[-1]["options"]
        self.assertEqual(
            options["builds"][0], {"items": [3118, 3020, 4645], "winRate": 53.64, "pickRate": 17.45, "games": 29091}
        )
        self.assertEqual([k["id"] for k in options["keystones"]], [8112, 8128])
        self.assertIn(8112, self.service._stats.keystone_ids)  # keystones are the first slot of each tree
        self.assertNotIn(5008, self.service._stats.keystone_ids)

    def test_a_chosen_build_heads_the_set_and_the_default_comes_back(self):
        default_blocks = None
        self.service.handle({"type": "assistant-items-import"})
        default_blocks = self.managed()["blocks"]
        self.service.handle({"type": "assistant-items-choose", "items": [2503, 3158, 3100]})
        blocks = self.managed()["blocks"]
        self.assertEqual(blocks[0]["type"], "56,8% — 7.505 partidas")
        self.assertEqual([i["id"] for i in blocks[0]["items"]], ["2503", "3158", "3100"])
        self.assertEqual(blocks[1:], default_blocks)
        self.assertEqual(self.published[-1]["items"]["chosen"], [2503, 3158, 3100])
        self.assertTrue(self.published[-1]["items"]["confirmed"])
        self.service.handle({"type": "assistant-items-default"})
        self.assertEqual(self.managed()["blocks"], default_blocks)
        self.assertIsNone(self.published[-1]["items"]["chosen"])

    def test_unknown_or_malformed_builds_are_refused(self):
        self.service.handle({"type": "assistant-items-choose", "items": [1, 2, 3]})
        self.assertEqual(self.published[-1]["items"]["error"], "unknown_build")
        for bad in ([], [True], ["3118"], list(range(1, 9))):
            with self.assertRaises(ValueError):
                self.service.handle({"type": "assistant-items-choose", "items": bad})

    def test_a_keystone_page_is_loaded_then_chosen_like_the_others(self):
        self.service.handle({"type": "assistant-runes-keystone", "keystone": 8128})
        runes = self.published[-1]["runes"]
        self.assertIsNone(runes["keystonePending"])
        self.assertEqual(runes["keystone"][0]["selection"], "keystone")
        self.assertEqual(runes["keystone"][0]["page"]["perks"][0], 8128)
        self.service.handle({"type": "assistant-runes-choose", "selection": "keystone"})
        self.assertEqual(self.controller.calls[-1][0], "choose")
        self.assertEqual(self.controller.calls[-1][1].perk_ids[0], 8128)
        with self.assertRaises(ValueError):
            self.service.handle({"type": "assistant-runes-keystone", "keystone": "8128"})


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
        self.assertEqual(self.published[-1]["items"]["title"], "SEXO2 — Ahri")
        self.assertEqual(len(self.published[-1]["items"]["blocks"]), 6)

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


def ranked_payload(queue, tier, division, league_points):
    return {
        "queueMap": {
            queue: {"queueType": queue, "tier": tier, "division": division, "leaguePoints": league_points},
        }
    }


def ranked_session(session_id, my_team, their_team=()):
    return {
        "id": session_id,
        "localPlayerCellId": 2,
        "myTeam": list(my_team),
        "theirTeam": list(their_team),
        "timer": {"phase": "BAN_PICK"},
    }


def player(cell_id, position, puuid, champion=1):
    return {"cellId": cell_id, "assignedPosition": position, "championId": champion, "puuid": puuid}


class RankedTeamTests(unittest.TestCase):
    def setUp(self):
        self.lcu = FakeLCU()
        self.published = []
        self.service = AssistantService(
            self.lcu,
            self.published.append,
            queue_id=lambda: 420,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            forms_worker=InlineWorker(),
            controller=FakeController(),
        )

    def test_team_prefers_solo_then_flex_and_caches_each_puuid(self):
        self.lcu.session = ranked_session(
            "cs-rank",
            [
                player(1, "top", "p-top", 86),
                player(2, "middle", "p-mid", 103),
                player(3, "utility", "p-sup", 1),
            ],
        )
        self.lcu.ranked = {
            "p-top": ranked_payload("RANKED_SOLO_5x5", "PLATINUM", "IV", 77),
            "p-mid": ranked_payload("RANKED_FLEX_SR", "GOLD", "II", 45),
        }
        self.service.handle({"type": "assistant-request"})
        rows = {row["position"]: row for row in self.published[-1]["ranked"]["team"]}
        self.assertEqual(
            rows["top"]["elo"],
            {
                "queue": "RANKED_SOLO_5x5",
                "tier": "PLATINUM",
                "division": "IV",
                "leaguePoints": 77,
                "wins": None,
                "losses": None,
            },
        )
        self.assertEqual(rows["middle"]["elo"]["queue"], "RANKED_FLEX_SR")
        self.assertIsNone(rows["support"]["elo"])  # no rank: the panel shows a dash
        calls = list(self.lcu.ranked_calls)
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(self.lcu.ranked_calls, calls)

    def service_for(self, queue_id):
        published = []
        service = AssistantService(
            self.lcu,
            published.append,
            queue_id=lambda: queue_id,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            forms_worker=InlineWorker(),
            controller=FakeController(),
        )
        return service, published

    def test_the_tab_exists_only_where_the_champion_select_shows_the_allies(self):
        self.lcu.session = ranked_session("cs-q", [player(i, "", f"p{i}", 1) for i in range(5)])
        shown = {}
        for queue_id in (400, 420, 430, 440, 450, 480, 1750, 2400, 3140):
            service, published = self.service_for(queue_id)
            service.handle({"type": "assistant-request"})
            shown[queue_id] = published[-1]["ranked"]["available"]
        # normal draft, blind, flex and ARAM show it; Solo/Duo hides the allies, the rest has no such roster
        self.assertEqual(
            shown,
            {400: True, 420: False, 430: True, 440: True, 450: True, 480: False, 1750: False, 2400: False, 3140: False},
        )

    def test_in_arena_the_team_is_the_duo_that_shares_the_team_id(self):
        roster = []
        for cell in range(16):
            entry = player(cell, "", f"p{cell}", 1)
            entry["teamId"] = cell // 2 + 1  # eight duos
            entry["gameName"] = f"N{cell}"
            roster.append(entry)
        session = ranked_session("cs-arena-duo", roster)
        session["localPlayerCellId"] = 5  # in duo 3, with cell 4
        self.lcu.session = session
        service, published = self.service_for(1750)
        service.handle({"type": "assistant-request"})
        ranked = published[-1]["ranked"]
        self.assertTrue(ranked["available"])
        self.assertEqual(sorted(row["cellId"] for row in ranked["team"]), [4, 5])
        self.assertEqual(sorted(self.lcu.ranked_calls), ["p4", "p5"])  # only the duo is asked about

    def test_in_arena_the_duo_is_found_whatever_the_team_field_is_called(self):
        for key in ("teamId", "subteamId", "subteamIndex", "subteam", "team"):
            with self.subTest(field=key):
                roster = []
                for cell in range(16):
                    entry = player(cell, "", f"p{cell}", 1)
                    entry[key] = cell // 2 + 1
                    roster.append(entry)
                session = ranked_session(f"cs-{key}", roster)
                session["localPlayerCellId"] = 7
                self.lcu.session = session
                service, published = self.service_for(1750)
                service.handle({"type": "assistant-request"})
                self.assertEqual(sorted(r["cellId"] for r in published[-1]["ranked"]["team"]), [6, 7])

    def test_in_arena_a_field_that_groups_more_than_a_duo_is_not_a_team(self):
        roster = []
        for cell in range(16):
            entry = player(cell, "", f"p{cell}", 1)
            entry["team"] = cell % 2 + 1  # two sides of eight, as in a 5v5 game: not a duo
            roster.append(entry)
        self.lcu.session = ranked_session("cs-sides", roster)
        service, published = self.service_for(1750)
        service.handle({"type": "assistant-request"})
        self.assertFalse(published[-1]["ranked"]["available"])

    def test_in_arena_without_a_team_id_the_tab_is_not_shown(self):
        self.lcu.session = ranked_session("cs-arena-none", [player(i, "", f"p{i}", 1) for i in range(16)])
        service, published = self.service_for(1750)
        service.handle({"type": "assistant-request"})
        self.assertFalse(published[-1]["ranked"]["available"])
        self.assertEqual(published[-1]["ranked"]["team"], [])

    def test_a_roster_of_sixteen_is_never_a_team(self):
        self.lcu.session = ranked_session("cs-arena", [player(i, "", f"p{i}", 1) for i in range(16)])
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        ranked = published[-1]["ranked"]
        self.assertFalse(ranked["available"])
        self.assertLessEqual(len(ranked["team"]), 5)

    def test_rows_carry_the_player_name_the_client_shows(self):
        top = player(1, "top", "p-top", 86)
        top.update({"gameName": "Fulano", "tagLine": "BR1"})
        hidden = player(2, "middle", "p-mid", 103)  # a name the client hides stays empty
        old = player(3, "utility", "p-sup", 1)
        old["summonerName"] = "Beltrano"
        self.lcu.session = ranked_session("cs-names", [top, hidden, old])
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        rows = {row["position"]: row for row in published[-1]["ranked"]["team"]}
        self.assertEqual((rows["top"]["name"], rows["top"]["tag"]), ("Fulano", "BR1"))
        self.assertEqual((rows["middle"]["name"], rows["middle"]["tag"]), ("", ""))
        self.assertEqual(rows["support"]["name"], "Beltrano")

    def form_team(self):
        local = player(2, "middle", "p-me", 103)
        top = player(1, "top", "p-top", 86)
        top.update({"gameName": "Fulano", "tagLine": "BR1"})
        jungle = player(3, "jungle", "p-jg", 0)  # has not picked yet
        jungle.update({"gameName": "Beltrano"})
        return [top, local, jungle]

    def top_games(self):
        from tests.test_player_form import game, payload

        return payload(
            game(3, 86, True, "TOP", puuid="p-top"),
            game(2, 86, True, "TOP", puuid="p-top"),
            game(1, 22, False, "TOP", puuid="p-top"),
        )

    def test_the_form_of_each_ally_is_read_apart_once_and_published(self):
        self.lcu.session = ranked_session("cs-form", self.form_team())
        self.lcu.history["p-top"] = self.top_games()
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        rows = {row["position"]: row for row in published[-1]["ranked"]["team"]}
        self.assertEqual(rows["top"]["form"]["recent"], [True, True, False])
        self.assertEqual(rows["top"]["form"]["role"], "top")
        self.assertEqual(rows["top"]["form"]["withChampion"], {"games": 2, "wins": 2})
        self.assertTrue(rows["top"]["canOpen"])  # name, tag and region are known
        # the local player is never compared with himself, and a player without history has no form
        self.assertIsNone(rows["middle"]["form"])
        self.assertFalse(rows["middle"]["canOpen"])
        self.assertIsNone(rows["jungle"]["form"])
        self.assertNotIn("p-me", self.lcu.history_calls)
        service.handle({"type": "assistant-request"})
        self.assertEqual(sorted(self.lcu.history_calls), ["p-jg", "p-top"])  # each read once per selection

    def test_a_champion_picked_later_changes_only_the_with_champion_part(self):
        team = self.form_team()
        team[2]["championId"] = 0
        self.lcu.session = ranked_session("cs-pick", team)
        self.lcu.history["p-jg"] = {"games": {"games": []}}
        from tests.test_player_form import game, payload

        self.lcu.history["p-jg"] = payload(
            game(1, 64, True, "JUNGLE", puuid="p-jg"), game(2, 64, False, "JUNGLE", puuid="p-jg")
        )
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        self.assertIsNone(published[-1]["ranked"]["team"][1]["form"]["withChampion"])
        team[2]["championId"] = 64
        self.lcu.session = ranked_session("cs-pick", team)
        calls = len(self.lcu.history_calls)
        service.handle({"type": "assistant-ranked"})
        jungle = published[-1]["ranked"]["team"][1]
        self.assertEqual(jungle["form"]["withChampion"], {"games": 2, "wins": 1})
        self.assertEqual(len(self.lcu.history_calls), calls)

    def test_a_failing_history_or_met_list_never_breaks_the_rows(self):
        self.lcu.session = ranked_session("cs-fail", self.form_team())
        self.lcu.history["p-top"] = RuntimeError("timeout")
        self.lcu.history["p-jg"] = "not a payload"
        self.lcu.region = RuntimeError("down")
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        rows = published[-1]["ranked"]["team"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["form"] is None and row["canOpen"] is False for row in rows))

    def test_nothing_about_the_form_is_read_where_the_tab_is_not_shown(self):
        self.lcu.session = ranked_session("cs-solo", self.form_team())
        for queue_id in (420, 480, 1750):
            service, _ = self.service_for(queue_id)
            service.handle({"type": "assistant-request"})
        self.assertEqual(self.lcu.history_calls, [])

    def service_with_opener(self, queue_id=440):
        opened = []
        service = AssistantService(
            self.lcu,
            lambda state: None,
            queue_id=lambda: queue_id,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            forms_worker=InlineWorker(),
            controller=FakeController(),
            open_url=opened.append,
        )
        return service, opened

    def test_the_profile_button_opens_the_site_for_that_ally_only(self):
        self.lcu.session = ranked_session("cs-open", self.form_team())
        service, opened = self.service_with_opener()
        service.handle({"type": "assistant-request"})
        service.handle({"type": "assistant-open-profile", "cellId": 1})
        self.assertEqual(opened, ["https://www.op.gg/summoners/br/Fulano-BR1"])

    def test_the_profile_button_never_opens_what_it_should_not(self):
        team = self.form_team()
        self.lcu.session = ranked_session("cs-no", team)
        service, opened = self.service_with_opener()
        service.handle({"type": "assistant-request"})
        for cell in (2, 3, 9, None, "1", True, 1.0, -1, [1], {"a": 1}):  # me, no tag, not in the team, junk
            service.handle({"type": "assistant-open-profile", "cellId": cell})
        self.assertEqual(opened, [])
        # a queue where the tab is not shown opens nothing either
        solo, opened_solo = self.service_with_opener(420)
        solo.handle({"type": "assistant-request"})
        solo.handle({"type": "assistant-open-profile", "cellId": 1})
        self.assertEqual(opened_solo, [])

    def test_the_profile_button_needs_the_clients_region(self):
        self.lcu.session = ranked_session("cs-region", self.form_team())
        for region in (None, {}, {"region": "MARS"}, RuntimeError("down")):
            self.lcu.region = region
            service, opened = self.service_with_opener()
            service.handle({"type": "assistant-request"})
            service.handle({"type": "assistant-open-profile", "cellId": 1})
            self.assertEqual(opened, [])

    def test_a_browser_that_fails_to_open_changes_nothing(self):
        self.lcu.session = ranked_session("cs-fail-open", self.form_team())
        service = AssistantService(
            self.lcu,
            lambda state: None,
            queue_id=lambda: 440,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            forms_worker=InlineWorker(),
            controller=FakeController(),
            open_url=lambda url: (_ for _ in ()).throw(OSError("no browser")),
        )
        service.handle({"type": "assistant-request"})
        service.handle({"type": "assistant-open-profile", "cellId": 1})  # logged, never raised

    def test_a_player_without_a_puuid_is_not_asked_about(self):
        hidden = player(1, "top", "", 0)
        self.lcu.session = ranked_session("cs-hidden", [hidden, player(2, "middle", "p-me", 103)])
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        self.assertEqual(self.lcu.history_calls, [])
        self.assertIsNone(published[-1]["ranked"]["team"][0]["form"])

    def test_the_form_of_one_selection_never_reaches_the_next(self):
        self.lcu.session = ranked_session("cs-a", self.form_team())
        self.lcu.history["p-top"] = self.top_games()
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        self.lcu.session = ranked_session("cs-b", self.form_team())
        self.lcu.history["p-top"] = None
        service.handle({"type": "assistant-request"})
        rows = {row["position"]: row for row in published[-1]["ranked"]["team"]}
        self.assertIsNone(rows["top"]["form"])  # read again for the new selection

    def test_the_win_and_loss_counts_of_the_ranked_queue_reach_the_row(self):
        self.lcu.session = ranked_session("cs-wl", self.form_team())
        payload = ranked_payload("RANKED_FLEX_SR", "GOLD", "II", 45)
        payload["queueMap"]["RANKED_FLEX_SR"].update({"wins": 70, "losses": 60})
        self.lcu.ranked["p-top"] = payload
        service, published = self.service_for(440)
        service.handle({"type": "assistant-request"})
        elo = {row["position"]: row for row in published[-1]["ranked"]["team"]}["top"]["elo"]
        self.assertEqual((elo["wins"], elo["losses"]), (70, 60))

    def test_enemies_are_read_only_when_the_client_exposes_a_puuid(self):
        self.lcu.session = ranked_session(
            "cs-enemy",
            [player(2, "middle", "p-mid", 103)],
            [{"cellId": 6, "assignedPosition": "top", "championId": 1}],
        )
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(self.published[-1]["ranked"]["enemies"], [])
        self.assertEqual(self.lcu.ranked_calls, ["p-mid"])

        self.lcu.session["theirTeam"][0]["puuid"] = "p-enemy"
        self.lcu.ranked["p-enemy"] = ranked_payload("RANKED_SOLO_5x5", "DIAMOND", "III", 4)
        self.service.handle({"type": "assistant-ranked"})
        enemies = self.published[-1]["ranked"]["enemies"]
        self.assertEqual(len(enemies), 1)
        self.assertEqual(enemies[0]["elo"]["tier"], "DIAMOND")
        self.assertIn("p-enemy", self.lcu.ranked_calls)

    def test_a_failed_read_is_a_dash_and_does_not_raise(self):
        self.lcu.session = ranked_session("cs-fail", [player(2, "middle", "p-mid", 103)])
        self.lcu.ranked["p-mid"] = RuntimeError("client closed")
        self.service.handle({"type": "assistant-request"})
        self.assertIsNone(self.published[-1]["ranked"]["team"][0]["elo"])

    def test_the_cap_is_five_players_per_side(self):
        team = [player(i, "", f"p{i}", 1) for i in range(1, 7)]
        team[1] = player(2, "middle", "p2", 103)  # local player
        enemies = [player(10 + i, "", f"e{i}", 1) for i in range(1, 7)]
        self.lcu.session = ranked_session("cs-cap", team, enemies)
        for i in range(1, 7):
            self.lcu.ranked[f"p{i}"] = ranked_payload("RANKED_SOLO_5x5", "GOLD", "I", i)
            self.lcu.ranked[f"e{i}"] = ranked_payload("RANKED_SOLO_5x5", "SILVER", "I", i)
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(len(self.lcu.ranked_calls), 10)
        self.assertNotIn("p6", self.lcu.ranked_calls)
        self.assertNotIn("e6", self.lcu.ranked_calls)
        self.assertEqual(
            len(self.published[-1]["ranked"]["team"]), 5
        )  # never more than a team, as the panel has no scroll

    def test_ranks_show_before_the_local_player_picks_a_champion(self):
        self.lcu.session = ranked_session("cs-pick", [player(2, "middle", "p-mid", 0)])
        self.lcu.ranked["p-mid"] = ranked_payload("RANKED_SOLO_5x5", "MASTER", None, 312)
        self.service.handle({"type": "assistant-request"})
        state = self.published[-1]
        self.assertIsNone(state["championId"])
        self.assertEqual(state["ranked"]["team"][0]["elo"]["tier"], "MASTER")
        self.assertIsNone(state["ranked"]["team"][0]["elo"]["division"])

    def test_a_new_champion_select_reads_the_same_player_again(self):
        self.lcu.session = ranked_session("cs-1", [player(2, "middle", "p-mid", 103)])
        self.lcu.ranked["p-mid"] = ranked_payload("RANKED_SOLO_5x5", "GOLD", "II", 10)
        self.service.handle({"type": "assistant-request"})
        self.lcu.session = ranked_session("cs-2", [player(2, "middle", "p-mid", 103)])
        self.service.handle({"type": "assistant-request"})
        self.assertEqual(self.lcu.ranked_calls, ["p-mid", "p-mid"])


if __name__ == "__main__":
    unittest.main()


class FavoriteBuildTests(unittest.TestCase):
    """D-135: the build pinned for a champion, apart for SR and ARAM."""

    def setUp(self):
        from sexo2.services.favorite_builds import FavoriteBuilds
        from sexo2.services.rune_import import RuneImportSnapshot

        FakeStats.with_builds = True
        self.addCleanup(setattr, FakeStats, "with_builds", False)
        self.lcu = FakeLCU()
        self.published = []
        self.queue = 420
        self.timers = []
        self.controller = FakeController()
        self.page = PageSpec(8100, 8200, (8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001))
        self.controller.snap = RuneImportSnapshot(None, (), None, self.page, False, None)
        self.favorites = FavoriteBuilds()
        self.service = AssistantService(
            self.lcu,
            self.published.append,
            queue_id=lambda: self.queue,
            in_champ_select=lambda: True,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            controller=self.controller,
            schedule=lambda delay, action: self.timers.append(action),
            favorites=self.favorites,
        )

    def confirm(self, champion=103):
        self.service.champion_confirmed(champion)
        timers, self.timers = self.timers, []
        for action in timers:
            action()

    def top(self):
        managed = next(s for s in self.lcu.item_sets["itemSets"] if s.get("uid") == "sexo2-managed")
        return [int(i["id"]) for i in managed["blocks"][0]["items"][:3]]

    def test_pinned_runes_and_trio_are_applied_on_the_next_confirmation(self):
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-items-choose", "items": [2503, 3158, 3100]})
        self.service.handle({"type": "assistant-favorite", "what": "items", "action": "pin"})
        self.service.handle({"type": "assistant-favorite", "what": "runes", "action": "pin"})
        favorite = self.published[-1]["favorite"]
        self.assertEqual(favorite["items"], [2503, 3158, 3100])
        self.assertEqual(favorite["runes"]["perks"][0], 8112)
        # A new champion select with the same champion
        self.lcu.session = session(session_id="cs-2")
        self.service._chosen_build = None
        self.controller.calls.clear()
        self.confirm()
        self.assertEqual(self.top(), [2503, 3158, 3100])
        chosen = [c for c in self.controller.calls if c[0] == "choose"]
        self.assertEqual(chosen[-1][1], self.page)
        self.assertEqual(self.published[-1]["favorite"]["unavailable"], [])

    def test_the_default_build_can_be_pinned_too(self):
        self.confirm()
        default_top = self.top()
        self.service.handle({"type": "assistant-favorite", "what": "items", "action": "pin"})
        self.assertEqual(self.published[-1]["favorite"]["items"], default_top)
        self.lcu.session = session(session_id="cs-2")
        self.confirm()
        self.assertEqual(self.top(), default_top)
        self.assertEqual(self.published[-1]["favorite"]["unavailable"], [])

    def test_a_trio_gone_from_the_statistics_keeps_the_default_and_says_so(self):
        self.favorites.set_items("sr", 103, [1001, 1002, 1003], "middle")
        self.confirm()
        self.assertNotEqual(self.top(), [1001, 1002, 1003])
        self.assertEqual(self.published[-1]["favorite"]["unavailable"], ["items"])
        self.assertEqual(self.published[-1]["favorite"]["items"], [1001, 1002, 1003])  # kept

    def test_a_rune_page_the_client_refuses_is_reported(self):
        from sexo2.services.rune_import import RuneImportSnapshot

        self.favorites.set_runes("sr", 103, {"primary": 8100, "sub": 8200, "perks": [1, 2, 3]}, "middle")
        self.controller.snap = RuneImportSnapshot(None, (), None, None, False, "invalid_page")
        self.confirm()
        self.assertEqual(self.published[-1]["favorite"]["unavailable"], ["runes"])

    def test_sr_and_aram_are_apart(self):
        self.favorites.set_items("sr", 103, [2503, 3158, 3100], "middle")
        self.queue = 450
        self.confirm()
        self.assertIsNone(self.published[-1]["favorite"]["items"])
        self.assertNotEqual(self.top(), [2503, 3158, 3100])

    def test_unpin_and_malformed_requests(self):
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-favorite", "what": "runes", "action": "pin"})
        self.service.handle({"type": "assistant-favorite", "what": "runes", "action": "unpin"})
        self.assertIsNone(self.published[-1]["favorite"]["runes"])
        for bad in ({"what": "skins", "action": "pin"}, {"what": "runes", "action": "delete"}):
            with self.assertRaises(ValueError):
                self.service.handle({"type": "assistant-favorite", **bad})

    def test_a_later_confirmation_keeps_the_players_own_pick(self):
        self.favorites.set_items("sr", 103, [2503, 3158, 3100], "middle")
        self.confirm()
        self.service.handle({"type": "assistant-items-default"})
        self.service.handle({"type": "assistant-opponent", "championId": 1})
        timers, self.timers = self.timers, []
        for action in timers:
            action()
        self.assertNotEqual(self.top(), [2503, 3158, 3100])


class FavoriteLaneTests(FavoriteBuildTests):
    """D-148: in Summoner's Rift modes a favourite is pinned for one lane."""

    def pin(self, what):
        self.service.handle({"type": "assistant-favorite", "what": what, "action": "pin"})

    def test_a_favourite_is_for_one_lane_only(self):
        self.service.handle({"type": "assistant-request"})  # the session is middle
        self.service.handle({"type": "assistant-items-choose", "items": [2503, 3158, 3100]})
        self.pin("items")
        self.assertEqual(self.published[-1]["favorite"]["items"], [2503, 3158, 3100])
        self.assertEqual(self.favorites.get("sr", 103, "middle")["items"], [2503, 3158, 3100])
        self.assertIsNone(self.favorites.get("sr", 103, "top")["items"])
        self.assertIsNone(self.favorites.get("sr", 103)["items"])
        # the same champion on another lane has no favourite
        self.lcu.session = session(position="top", session_id="cs-2")
        self.service.handle({"type": "assistant-request"})
        self.assertIsNone(self.published[-1]["favorite"]["items"])

    def test_each_lane_keeps_its_own_runes_and_trio(self):
        self.service.handle({"type": "assistant-request"})
        self.pin("runes")
        self.lcu.session = session(position="top", session_id="cs-2")
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-items-choose", "items": [2503, 3158, 3100]})
        self.pin("items")
        self.assertIsNotNone(self.favorites.get("sr", 103, "middle")["runes"])
        self.assertIsNone(self.favorites.get("sr", 103, "middle")["items"])
        self.assertEqual(self.favorites.get("sr", 103, "top")["items"], [2503, 3158, 3100])
        self.assertIsNone(self.favorites.get("sr", 103, "top")["runes"])

    def test_the_next_champion_select_applies_the_favourite_of_its_lane(self):
        self.favorites.set_items("sr", 103, [2503, 3158, 3100], "top")
        self.lcu.session = session(position="top")
        self.confirm()
        self.assertEqual(self.top(), [2503, 3158, 3100])

    def test_pinning_needs_a_known_lane_in_summoners_rift(self):
        self.lcu.session = session(position="")  # a blind pick: the lane is not known
        self.service.handle({"type": "assistant-request"})
        self.pin("runes")
        self.assertEqual(self.published[-1]["error"], "no_lane")
        self.pin("items")
        self.assertEqual(self.published[-1]["error"], "no_lane")
        self.assertEqual(self.favorites.get("sr", 103), {"runes": None, "items": None})

    def test_choosing_the_lane_in_the_panel_lets_the_player_pin(self):
        self.lcu.session = session(position="")
        self.service.handle({"type": "assistant-request"})
        self.service.handle({"type": "assistant-lane", "lane": "jungle"})
        self.pin("runes")
        self.assertIsNone(self.published[-1]["error"])
        self.assertIsNotNone(self.favorites.get("sr", 103, "jungle")["runes"])
        self.assertEqual(self.published[-1]["favorite"]["runes"], self.favorites.get("sr", 103, "jungle")["runes"])

    def test_aram_has_no_lanes(self):
        self.queue = 450
        self.confirm()
        self.pin("items")
        self.assertIsNone(self.published[-1]["error"])
        self.assertIsNotNone(self.favorites.get("aram", 103)["items"])


class AutomaticRuneImportTests(FavoriteBuildTests):
    """D-136: without a favourite, the highest win rate page is imported on confirmation."""

    def chosen_pages(self):
        return [c[1] for c in self.controller.calls if c[0] == "choose"]

    def test_the_highest_win_rate_page_is_imported_when_nothing_was_chosen(self):
        from sexo2.services.rune_import import RuneImportSnapshot

        self.controller.snap = RuneImportSnapshot(None, (), None, None, False, None)
        self.confirm()
        (page,) = self.chosen_pages()
        self.assertEqual(page.perk_ids[0], 8112)  # "win" layout of FakeStats

    def test_a_page_the_player_chose_is_kept(self):
        self.confirm()  # the snapshot already has a page applied
        self.assertEqual(self.chosen_pages(), [])

    def test_the_favourite_wins_over_the_default(self):
        from sexo2.services.rune_import import RuneImportSnapshot

        self.controller.snap = RuneImportSnapshot(None, (), None, None, False, None)
        self.favorites.set_runes("sr", 103, {"primary": 8000, "sub": 8100, "perks": [9923, 1, 2]}, "middle")
        self.confirm()
        self.assertEqual([p.perk_ids[0] for p in self.chosen_pages()], [9923])

    def test_a_favourite_the_client_refuses_falls_back_to_the_default(self):
        from sexo2.services.rune_import import RuneImportSnapshot

        self.controller.snap = RuneImportSnapshot(None, (), None, None, False, "invalid_page")
        self.favorites.set_runes("sr", 103, {"primary": 8000, "sub": 8100, "perks": [1, 2, 3]}, "middle")
        self.confirm()
        self.assertEqual([p.perk_ids[0] for p in self.chosen_pages()], [1, 8112])

    def test_swiftplay_imports_no_runes(self):
        from sexo2.services.rune_import import RuneImportSnapshot

        self.controller.snap = RuneImportSnapshot(None, (), None, None, False, None)
        self.queue = 480
        self.lcu.session = None
        self.service.champion_confirmed(103, swiftplay=True)
        for action in self.timers:
            action()
        self.assertEqual(self.chosen_pages(), [])


class SwiftplayRuneTests(unittest.TestCase):
    """D-137: in Swiftplay each lobby slot gets its rune page once per champion and lobby."""

    PERKS = '{"perkIds":[8005,9111,9104,8014,8226,8210,5005,5008,5001],"perkStyle":8000,"perkSubStyle":8200}'

    def setUp(self):
        from sexo2.services.favorite_builds import FavoriteBuilds

        self.lcu = FakeLCU()
        self.lcu.session = None
        self.lobby = {
            "partyId": "p-1",
            "localMember": {
                "playerSlots": [
                    {"championId": 103, "skinId": 103000, "perks": self.PERKS, "spell1": 4},
                    {"championId": 86, "skinId": 86000, "perks": self.PERKS, "spell1": 4},
                ]
            },
        }
        get = self.lcu.get
        self.lcu.get = lambda path, **kw: (
            copy.deepcopy(self.lobby) if path == "/lol-lobby/v2/lobby" else get(path, **kw)
        )
        self.timers = []
        self.favorites = FavoriteBuilds()
        self.service = AssistantService(
            self.lcu,
            lambda state: None,
            queue_id=lambda: 480,
            in_champ_select=lambda: False,
            stats_factory=FakeStats,
            worker=InlineWorker(),
            controller=FakeController(),
            schedule=lambda delay, action: self.timers.append(action),
            favorites=self.favorites,
        )

    def confirm(self):
        self.service.champion_confirmed(103, swiftplay=True)
        timers, self.timers = self.timers, []
        for action in timers:
            action()

    def slot_puts(self):
        return [p for p in self.lcu.puts if isinstance(p, list)]

    def test_both_champions_get_the_highest_win_rate_page_in_the_clients_format(self):
        self.confirm()
        (slots,) = self.slot_puts()
        for slot in slots:
            perks = json.loads(slot["perks"])
            self.assertEqual(perks["perkIds"][0], 8112)  # "win" layout
            self.assertEqual((perks["perkStyle"], perks["perkSubStyle"]), (8100, 8200))
            self.assertEqual(slot["spell1"], 4)  # the rest of the slot untouched

    def test_a_valid_favourite_wins(self):
        page = {"primary": 8100, "sub": 8200, "perks": [8128, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001]}
        self.favorites.set_runes("sr", 103, page)
        self.confirm()
        (slots,) = self.slot_puts()
        self.assertEqual(json.loads(slots[0]["perks"])["perkIds"][0], 8128)
        self.assertEqual(json.loads(slots[1]["perks"])["perkIds"][0], 8112)

    def test_each_champion_is_filled_once_per_lobby(self):
        self.confirm()
        self.lobby["localMember"]["playerSlots"][1] = {"championId": 1, "skinId": 1000, "perks": self.PERKS}
        self.confirm()  # only the new champion is written; the first keeps what the player set
        self.assertEqual(len(self.slot_puts()), 2)
        self.assertEqual(self.slot_puts()[1][0]["perks"], self.PERKS)
        self.assertEqual(json.loads(self.slot_puts()[1][1]["perks"])["perkIds"][0], 8112)

    def test_an_unknown_perks_format_is_left_alone(self):
        for slot in self.lobby["localMember"]["playerSlots"]:
            slot["perks"] = "something else"
        self.confirm()
        self.assertEqual(self.slot_puts(), [])


class SwiftplayPanelTests(unittest.TestCase):
    """The Hub's Swiftplay screen opens one lobby champion in the assistant: runes go into its slot."""

    PERKS = '{"perkIds":[8005,9111,9104,8014,8226,8210,5005,5008,5001],"perkStyle":8000,"perkSubStyle":8200}'

    def setUp(self):
        from sexo2.services.favorite_builds import FavoriteBuilds

        self.lcu = FakeLCU()
        self.lcu.session = None  # a lobby: there is no champion select
        self.lobby = {
            "partyId": "p-1",
            "localMember": {
                "playerSlots": [
                    {"championId": 103, "skinId": 103000, "perks": self.PERKS, "spell1": 4},
                    {"championId": 86, "skinId": 86000, "perks": self.PERKS, "spell1": 4},
                ]
            },
        }
        get = self.lcu.get
        self.lcu.get = lambda path, **kw: (
            copy.deepcopy(self.lobby) if path == "/lol-lobby/v2/lobby" else get(path, **kw)
        )
        self.published = []
        self.controller = FakeController()
        self.favorites = FavoriteBuilds()

        class WithBuilds(FakeStats):
            with_builds = True

            def alternatives(self, champion_id, mode, lane, keystones):
                self.calls.append(("alternatives", mode, lane))
                return super().alternatives(champion_id, mode, lane, keystones)

        self.service = AssistantService(
            self.lcu,
            self.published.append,
            queue_id=lambda: 480,
            in_champ_select=lambda: False,
            stats_factory=WithBuilds,
            worker=InlineWorker(),
            controller=self.controller,
            schedule=lambda delay, action: None,
            favorites=self.favorites,
        )

    def slot_puts(self):
        return [p for p in self.lcu.puts if isinstance(p, list)]

    def open(self, champion=103):
        self.service.handle({"type": "assistant-swiftplay-open", "championId": champion})
        return self.published[-1]

    def test_opening_a_champion_publishes_its_swiftplay_state_with_the_slot_page(self):
        state = self.open()
        self.assertTrue(state["swiftplay"])
        self.assertEqual((state["championId"], state["mode"], state["lane"]), (103, "swift", "all"))
        self.assertEqual([r["selection"] for r in state["runes"]["general"]], ["win", "pick"])
        applied = state["runes"]["applied"]
        self.assertEqual((applied["primary"], applied["sub"], applied["perks"][0]), (8000, 8200, 8005))
        self.assertEqual(self.controller.calls, [("set_catalog", self.service._catalog), ("set_session", None)])

    def test_choosing_a_recommendation_writes_only_that_champions_slot(self):
        self.open()
        self.service.handle({"type": "assistant-runes-choose", "selection": "win", "matchup": False})
        (slots,) = self.slot_puts()
        self.assertEqual(json.loads(slots[0]["perks"])["perkIds"][0], 8112)
        self.assertEqual(slots[1]["perks"], self.PERKS)  # the other champion keeps its page
        self.assertEqual(slots[0]["spell1"], 4)
        state = self.published[-1]
        self.assertEqual(state["runes"]["applied"]["perks"][0], 8112)
        self.assertFalse(state["runes"]["pending"])
        self.assertIsNone(state["runes"]["error"])
        self.assertNotIn("choose", [call[0] for call in self.controller.calls])  # no live rune page

    def test_an_edited_page_is_written_when_valid_and_refused_when_not(self):
        self.open()
        valid = {"primary": 8100, "sub": 8200, "perks": [8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001]}
        self.service.handle({"type": "assistant-runes-edit", "page": valid})
        self.assertEqual(len(self.slot_puts()), 1)
        broken = {"primary": 8100, "sub": 8100, "perks": [8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001]}
        self.service.handle({"type": "assistant-runes-edit", "page": broken})
        self.assertEqual(len(self.slot_puts()), 1)  # nothing sent for an invalid page
        state = self.published[-1]
        self.assertEqual(state["runes"]["error"], "invalid_page")
        self.assertEqual(state["runes"]["applied"]["perks"][0], 8112)  # the last good page stays

    def test_a_champion_that_left_the_lobby_has_no_slot(self):
        self.open(1)
        self.service.handle({"type": "assistant-runes-choose", "selection": "win", "matchup": False})
        self.assertEqual(self.slot_puts(), [])
        self.assertEqual(self.published[-1]["runes"]["error"], "no_swiftplay_slot")

    def test_an_unknown_slot_format_is_not_overwritten(self):
        for slot in self.lobby["localMember"]["playerSlots"]:
            slot["perks"] = "something else"
        self.open()
        self.service.handle({"type": "assistant-runes-choose", "selection": "win", "matchup": False})
        self.assertEqual(self.slot_puts(), [])
        self.assertEqual(self.published[-1]["runes"]["error"], "slot_format")

    def test_the_players_pick_is_never_filled_over_by_the_automatic_import(self):
        self.open()
        self.service.handle({"type": "assistant-runes-choose", "selection": "pick", "matchup": False})
        self.assertIn(("p-1", 103), self.service._swift_runes_done)

    def test_opening_a_champion_imports_its_item_set_like_a_lock_does(self):
        state = self.open()
        self.assertTrue(state["items"]["confirmed"])
        self.assertEqual(state["items"]["championId"], 103)
        self.assertTrue([p for p in self.lcu.puts if isinstance(p, dict) and "itemSets" in p])

    def test_items_are_imported_for_the_opened_champion(self):
        self.open()
        self.service.handle({"type": "assistant-items-import"})
        sets = [p for p in self.lcu.puts if isinstance(p, dict) and "itemSets" in p]
        self.assertTrue(sets)
        self.assertTrue(self.published[-1]["items"]["confirmed"])
        self.assertEqual(self.published[-1]["items"]["championId"], 103)

    def test_a_favourite_page_can_be_pinned_from_the_swiftplay_screen(self):
        self.open()
        self.service.handle({"type": "assistant-runes-choose", "selection": "win", "matchup": False})
        self.service.handle({"type": "assistant-favorite", "what": "runes", "action": "pin"})
        self.assertEqual(self.favorites.get("sr", 103)["runes"]["perks"][0], 8112)

    def test_other_builds_and_other_runes_are_offered_in_swiftplay(self):
        state = self.open()
        self.assertTrue(state["options"]["builds"])
        self.assertEqual([k["id"] for k in state["options"]["keystones"]], [8112, 8128])
        # the service asks with the game mode; the stats service turns it into Solo/Duo data (D-147)
        self.assertIn(("alternatives", "swift", "all"), self.service._stats.calls)

    def test_another_keystone_loads_its_page_and_goes_into_the_slot(self):
        self.open()
        self.service.handle({"type": "assistant-runes-keystone", "keystone": 8128})
        self.assertIn(("keystone", 103, "swift", "all", 8128), self.service._stats.calls)
        self.assertEqual(self.published[-1]["runes"]["keystone"][0]["page"]["perks"][0], 8128)
        self.service.handle({"type": "assistant-runes-choose", "selection": "keystone", "matchup": False})
        (slots,) = self.slot_puts()
        self.assertEqual(json.loads(slots[0]["perks"])["perkIds"][0], 8128)

    def test_closing_goes_back_to_no_session(self):
        self.open()
        self.service.handle({"type": "assistant-swiftplay-close"})
        state = self.published[-1]
        self.assertFalse(state["swiftplay"])
        self.assertIsNone(state["championId"])

    def test_an_invalid_champion_is_rejected(self):
        for bad in (0, -3, True, "103", None):
            with self.assertRaises(ValueError):
                self.service.handle({"type": "assistant-swiftplay-open", "championId": bad})
