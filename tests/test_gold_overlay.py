"""Layout and reading of the scoreboard overlay (sexo2/overlay/gold_overlay.py), without a window."""

import unittest

from sexo2.overlay.gold_overlay import ALLY, ENEMY, Geometry, layout, my_team, read_comparison
from sexo2.services.gold import Unsupported

PRICES = {3020: 1100, 6655: 2750, 3071: 3000}


def player(team, name, champion, *items):
    return {"team": team, "riotId": name, "championName": champion, "items": [{"itemID": i, "count": 1} for i in items]}


PLAYERS = [
    player("ORDER", "Eu#BR1", "Ahri", 3020, 6655),
    player("ORDER", "Kaio#BR1", "Garen", 3020),
    player("CHAOS", "X#BR1", "Annie", 3071),
    player("CHAOS", "Y#BR1", "Darius", 3020, 3071),
]


class GoldOverlayTests(unittest.TestCase):
    def fetch(self, me):
        return lambda path: {"/playerlist": PLAYERS, "/activeplayername": me}[path]

    def test_blue_side_behind_points_right_in_red_and_rows_follow_each_pair(self):
        comparison = read_comparison(self.fetch("Eu#BR1"), PRICES)
        marks = layout(comparison, 1920, 1080, Geometry())
        total = marks[0]
        self.assertEqual((total.kind, total.text, total.color, total.arrow), ("total", "-2.150", ENEMY, "right"))
        self.assertEqual((total.left, total.right), ("", ""))
        rows = [m for m in marks if m.kind == "row"]
        self.assertEqual([(m.text, m.arrow) for m in rows], [("850", "left"), ("3.000", "right")])
        self.assertEqual(rows[0].color, ALLY)
        self.assertEqual(rows[1].y - rows[0].y, round(1080 * Geometry().row_step))

    def test_red_side_sees_the_same_match_from_its_side(self):
        comparison = read_comparison(self.fetch("X#BR1"), PRICES)
        self.assertEqual(comparison.difference, 2150)
        self.assertEqual(layout(comparison, 1920, 1080)[0].arrow, "left")

    def test_unknown_items_hide_the_numbers(self):
        players = [player("ORDER", "Eu#BR1", "Ahri", 9999), player("CHAOS", "X#BR1", "Annie", 3020)]
        comparison = read_comparison(lambda p: {"/playerlist": players, "/activeplayername": "Eu#BR1"}[p], PRICES)
        self.assertEqual(layout(comparison, 1920, 1080), [])

    def test_unknown_player_is_unsupported(self):
        with self.assertRaises(Unsupported):
            my_team(PLAYERS, "Ninguem#BR1")


if __name__ == "__main__":
    unittest.main()
