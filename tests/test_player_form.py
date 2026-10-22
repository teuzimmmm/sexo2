"""A player's recent form from the client's match history (D-153), in every shape the client may answer."""

import unittest

from sexo2.services import player_form


def game(created, champion, win, lane="MIDDLE", role="SOLO", puuid="p1", extra=None):
    """A game of the list endpoint: only the asked player's own participant."""
    entry = {
        "gameCreation": created,
        "queueId": 440,
        "participants": [
            {
                "participantId": 1,
                "championId": champion,
                "stats": {"win": win},
                "timeline": {"lane": lane, "role": role},
            }
        ],
        "participantIdentities": [{"participantId": 1, "player": {"puuid": puuid}}],
    }
    entry.update(extra or {})
    return entry


def payload(*games):
    return {"games": {"games": list(games)}}


class SummarizeTests(unittest.TestCase):
    def test_results_are_newest_first_and_counted(self):
        summary = player_form.summarize(
            payload(game(1, 103, False), game(3, 103, True), game(2, 103, True), game(4, 86, True)), "p1"
        )
        self.assertEqual(summary["recent"], [True, True, True, False])  # games 4, 3, 2, 1
        self.assertEqual((summary["games"], summary["wins"]), (4, 3))

    def test_only_five_recent_results_are_kept_but_all_games_count(self):
        summary = player_form.summarize(payload(*[game(i, 1, i % 2 == 0) for i in range(20)]), "p1")
        self.assertEqual(len(summary["recent"]), 5)
        self.assertEqual(summary["games"], 20)

    def test_the_main_role_needs_two_games(self):
        once = player_form.summarize(payload(game(1, 1, True, lane="TOP", role="SOLO")), "p1")
        self.assertIsNone(once["role"])
        twice = player_form.summarize(
            payload(game(1, 1, True, "TOP"), game(2, 1, False, "TOP"), game(3, 1, True, "JUNGLE", "NONE")), "p1"
        )
        self.assertEqual(twice["role"], "top")

    def test_roles_from_lane_and_role_or_from_position(self):
        cases = [
            (("BOTTOM", "DUO_CARRY"), "bottom"),
            (("BOTTOM", "DUO_SUPPORT"), "support"),
            (("BOTTOM", "SUPPORT"), "support"),
            (("MIDDLE", "SOLO"), "middle"),
            (("JUNGLE", "NONE"), "jungle"),
            (("NONE", "NONE"), None),
        ]
        for (lane, role), expected in cases:
            with self.subTest(lane=lane, role=role):
                summary = player_form.summarize(
                    payload(game(1, 1, True, lane, role), game(2, 1, True, lane, role)), "p1"
                )
                self.assertEqual(summary["role"], expected)
        by_position = game(1, 1, True, lane="NONE", role="NONE", extra={})
        by_position["participants"][0]["teamPosition"] = "UTILITY"
        self.assertEqual(player_form.summarize(payload(by_position, by_position), "p1")["role"], "support")

    def test_per_champion_record_and_most_played(self):
        summary = player_form.summarize(
            payload(
                *[game(i, 22, i % 3 != 0) for i in range(6)],
                game(10, 202, True),
                game(11, 202, False),
                game(12, 51, True),
            ),
            "p1",
        )
        self.assertEqual(player_form.with_champion(summary, 22), {"games": 6, "wins": 4})
        self.assertIsNone(player_form.with_champion(summary, 999))  # never played it recently
        self.assertEqual(summary["top"], [{"id": 22, "games": 6}, {"id": 202, "games": 2}, {"id": 51, "games": 1}])

    def test_public_form_carries_the_champion_of_the_moment_only(self):
        summary = player_form.summarize(payload(game(1, 22, True), game(2, 22, False)), "p1")
        shown = player_form.public(summary, 22)
        self.assertEqual(shown["withChampion"], {"games": 2, "wins": 1})
        self.assertNotIn("champions", shown)
        self.assertIsNone(player_form.public(summary, 0)["withChampion"])  # no champion picked yet
        self.assertIsNone(player_form.public(None, 22))

    def test_the_players_own_entry_is_found_among_several(self):
        crowded = game(1, 103, True)
        crowded["participants"].append({"participantId": 2, "championId": 1, "stats": {"win": False}})
        crowded["participantIdentities"].append({"participantId": 2, "player": {"puuid": "other"}})
        self.assertEqual(player_form.summarize(payload(crowded), "p1")["recent"], [True])
        self.assertEqual(player_form.summarize(payload(crowded), "other")["recent"], [False])
        self.assertIsNone(player_form.summarize(payload(crowded), "nobody"))  # several entries, none his

    def test_wins_written_as_words(self):
        words = game(1, 1, "Win")
        lost = game(2, 1, "Fail")
        self.assertEqual(player_form.summarize(payload(words, lost), "p1")["recent"], [False, True])

    def test_whatever_the_client_leaves_out_gives_nothing_never_a_guess(self):
        for name, bad in {
            "none": None,
            "empty": {},
            "text": "error",
            "a list of numbers": [1, 2],
            "games not a list": {"games": {"games": "x"}},
            "no stats": payload({"participants": [{"participantId": 1, "championId": 1}]}),
            "win unknown": payload(game(1, 1, None)),
        }.items():
            with self.subTest(case=name):
                self.assertIsNone(player_form.summarize(bad, "p1"))

    def test_a_game_without_a_champion_still_counts_as_a_result(self):
        entry = game(1, 0, True)
        summary = player_form.summarize(payload(entry), "p1")
        self.assertEqual(summary["recent"], [True])
        self.assertEqual(summary["champions"], {})

    def test_a_flat_list_of_games_is_read_too(self):
        self.assertEqual(player_form.summarize([game(1, 1, True)], "p1")["recent"], [True])


class ProfileTests(unittest.TestCase):
    def test_the_address_comes_from_the_clients_region_name_and_tag(self):
        region = player_form.profile_region({"region": "BR", "locale": "pt_BR"})
        self.assertEqual(region, "br")
        self.assertEqual(player_form.profile_url(region, "Fulano", "BR1"), "https://www.op.gg/summoners/br/Fulano-BR1")

    def test_names_are_encoded_so_nothing_can_leave_the_address(self):
        url = player_form.profile_url("br", "A B/ü?x#y", "T&G")
        self.assertEqual(url, "https://www.op.gg/summoners/br/A%20B%2F%C3%BC%3Fx%23y-T%26G")
        self.assertTrue(url.startswith("https://www.op.gg/summoners/br/"))

    def test_without_a_region_a_name_or_a_tag_there_is_no_address(self):
        for args in ((None, "A", "B"), ("br", "", "B"), ("br", "A", ""), ("", "A", "B")):
            with self.subTest(args=args):
                self.assertIsNone(player_form.profile_url(*args))

    def test_unknown_or_malformed_regions_give_no_region(self):
        for payload in (None, {}, [], "BR", {"region": 3}, {"region": "MARS"}, {"region": ""}):
            with self.subTest(payload=payload):
                self.assertIsNone(player_form.profile_region(payload))
        self.assertEqual(player_form.profile_region({"region": " euw "}), "euw")


if __name__ == "__main__":
    unittest.main()
