"""Item value comparison for the scoreboard overlay (sexo2/services/gold.py)."""

import unittest

from sexo2.services.gold import CHAOS, ORDER, Unsupported, compare, for_player_team, item_prices

# Representative shapes of /lol-game-data/assets/v1/items.json and Live Client /playerlist.
ITEMS = [
    {"id": 1001, "priceTotal": 300},
    {"id": 3020, "priceTotal": 1100},
    {"id": 6655, "priceTotal": 2750},
    {"id": 2003, "priceTotal": 50},
    {"id": 3340, "priceTotal": 0},
    {"id": 3071, "priceTotal": 3000},
    {"id": "bad", "priceTotal": 10},
    {"id": 9999, "priceTotal": True},
]


def player(team, champion, *items):
    return {
        "team": team,
        "championName": champion,
        "items": [{"itemID": item_id, "count": count} for item_id, count in items],
    }


class GoldComparisonTests(unittest.TestCase):
    def setUp(self):
        self.prices = item_prices(ITEMS)

    def test_prices_ignore_malformed_entries(self):
        self.assertEqual(self.prices, {1001: 300, 3020: 1100, 6655: 2750, 2003: 50, 3340: 0, 3071: 3000})

    def test_rows_pair_players_in_list_order_and_total_each_team(self):
        result = compare(
            [
                player(ORDER, "Ahri", (3020, 1), (6655, 1), (2003, 2), (3340, 1)),
                player(ORDER, "Garen", (1001, 1)),
                player(CHAOS, "Annie", (3020, 1), (3340, 1)),
                player(CHAOS, "Darius", (3071, 1), (1001, 1)),
            ],
            self.prices,
        )
        self.assertEqual(
            [(r.order_champion, r.chaos_champion) for r in result.rows], [("Ahri", "Annie"), ("Garen", "Darius")]
        )
        self.assertEqual(result.rows[0].order_value, 1100 + 2750 + 2 * 50)
        self.assertEqual(result.rows[0].difference, 3950 - 1100)
        self.assertEqual(result.rows[1].difference, 300 - 3300)
        self.assertEqual((result.order_total, result.chaos_total), (4250, 4400))
        self.assertEqual(result.difference, -150)

    def test_unknown_price_hides_the_row_and_the_totals_instead_of_guessing(self):
        result = compare(
            [player(ORDER, "Ahri", (3020, 1), (123456, 1)), player(CHAOS, "Annie", (3020, 1))], self.prices
        )
        self.assertIsNone(result.rows[0].order_value)
        self.assertIsNone(result.rows[0].difference)
        self.assertIsNone(result.order_total)
        self.assertEqual(result.chaos_total, 1100)
        self.assertEqual(result.unknown_items, frozenset({123456}))

    def test_empty_inventories_are_zero(self):
        result = compare([player(ORDER, "Ahri"), player(CHAOS, "Annie")], self.prices)
        self.assertEqual(result.difference, 0)

    def test_arena_or_unpaired_teams_are_unsupported(self):
        with self.assertRaises(Unsupported):
            compare([player("TEAM3", "Ahri")], self.prices)
        with self.assertRaises(Unsupported):
            compare([player(ORDER, "Ahri"), player(ORDER, "Garen"), player(CHAOS, "Annie")], self.prices)
        with self.assertRaises(Unsupported):
            compare([], self.prices)

    def test_view_from_the_red_side_flips_the_sign(self):
        result = compare([player(ORDER, "Ahri", (3020, 1)), player(CHAOS, "Annie", (6655, 1))], self.prices)
        mine = for_player_team(result, CHAOS)
        self.assertEqual(mine.rows[0].order_champion, "Annie")
        self.assertEqual(mine.difference, 2750 - 1100)


if __name__ == "__main__":
    unittest.main()
