"""Layout and reading of the scoreboard overlay (sexo2/overlay/gold_overlay.py), without a window."""

import queue
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

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
        self.assertEqual((total.kind, total.text, total.color, total.arrow), ("total", "2.150", ENEMY, "right"))
        self.assertEqual((total.left, total.right), ("4.950", "7.100"))
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

    def test_default_marks_fit_the_actual_1080p_scoreboard_rows(self):
        # Measured in the user's game capture: header 237..306, then five rows.
        from sexo2.services.gold import Comparison, Row

        comparison = Comparison(tuple(Row("ally", "enemy", 2000, 1000) for _ in range(5)), 10000, 5000, frozenset())
        marks = layout(comparison, 1920, 1080)
        self.assertAlmostEqual(marks[0].y, 234, delta=2)
        row_boxes = [(307, 384), (384, 461), (461, 537), (537, 614), (614, 691)]
        for mark, (top, bottom) in zip(marks[1:], row_boxes):
            self.assertAlmostEqual(mark.y, (top + bottom) / 2, delta=2)

    def test_window_covers_only_the_gold_column_and_keeps_every_mark_inside(self):
        from sexo2.overlay.gold_overlay import overlay_bounds

        comparison = read_comparison(self.fetch("Eu#BR1"), PRICES)
        for width, height in ((1920, 1080), (2560, 1440), (1280, 720)):
            with self.subTest(size=(width, height)):
                left, top, right, bottom = overlay_bounds(width, height, Geometry())
                self.assertLess((right - left) * (bottom - top), width * height * 0.12)
                for mark in layout(comparison, width, height):
                    self.assertTrue(left < mark.x < right)
                    self.assertTrue(top < mark.y < bottom)

    def test_first_tab_does_not_create_the_window_or_load_the_item_catalog(self):
        from sexo2.overlay.gold_overlay import GoldOverlayThread

        lcu = Mock()
        lcu.get.return_value = [{"id": 3020, "priceTotal": 1100}]
        thread = GoldOverlayThread(SimpleNamespace(phase="InProgress"), lcu)
        window = Mock()

        def check_prepared():
            self.assertIs(thread._window, window)
            self.assertEqual(thread._prices, {3020: 1100})
            thread.stop()
            return False

        with (
            patch("sexo2.overlay.gold_overlay._Window", return_value=window),
            patch("sexo2.overlay.gold_overlay._tab_down", side_effect=check_prepared),
        ):
            thread.run()
        lcu.get.assert_called_once_with("/lol-game-data/assets/v1/items.json")

    def test_repeated_readings_reuse_the_drawing_and_do_not_raise_the_window_again(self):
        from sexo2.overlay.gold_overlay import _Window

        comparison = read_comparison(self.fetch("Eu#BR1"), PRICES)
        window = object.__new__(_Window)
        window._geometry = Geometry()
        window._queue = queue.Queue()
        for item in (comparison, comparison, None, comparison, False):
            window._queue.put(item)
        root, canvas = Mock(), Mock()
        root.winfo_screenwidth.return_value = 1920
        root.winfo_screenheight.return_value = 1080
        callbacks = []
        root.after.side_effect = lambda delay, callback: callbacks.append(callback)
        root.mainloop.side_effect = lambda: callbacks.pop(0)()
        tkinter = SimpleNamespace(Tk=Mock(return_value=root), Canvas=Mock(return_value=canvas))
        with patch.dict("sys.modules", tkinter=tkinter), patch.object(_Window, "_click_through"):
            window._run()
        # Same readings and re-opening Tab reuse the existing canvas contents.
        canvas.delete.assert_called_once_with("all")
        self.assertEqual(root.deiconify.call_count, 2)
        root.attributes.assert_any_call("-topmost", True)
        self.assertEqual(len([c for c in root.attributes.call_args_list if c.args == ("-topmost", True)]), 1)
        for call in canvas.create_text.call_args_list:
            size = call.kwargs["font"][1]
            self.assertLess(size, 0)  # Pixel sizes, independent of Windows text scaling.
            self.assertLessEqual(abs(size), 12)
        root.destroy.assert_called_once()

    def test_overlay_thread_can_stop_and_join_normally(self):
        from sexo2.overlay.gold_overlay import GoldOverlayThread

        thread = GoldOverlayThread(SimpleNamespace(phase="Lobby"), Mock())
        thread.stop()
        thread.start()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
