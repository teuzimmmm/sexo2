import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from sexo2.overlay.offers import Choice, Matcher, Offer, OfferState, offer_view
from sexo2.overlay.reader import OfferReader
from sexo2.overlay.screen import title_rects


NAMES = {'1': 'Critical Rhythm', '2': 'Fire Power', '3': 'Ice Shield', '4': 'Quick Feet'}


class OffersTests(unittest.TestCase):
    def test_names_accents_wrapping_and_ambiguity(self):
        match = Matcher(dict(NAMES, **{'5': 'Ímpeto de Aço'}))
        self.assertEqual(match.match('Critical\nRhythm').identifier, '1')
        self.assertEqual(match.match('impeto de aco').identifier, '5')
        self.assertIsNone(match.match('Unknown player name').identifier)
        self.assertIsNone(Matcher({'1': 'A-b', '2': 'Ab'}).match('Ab').identifier)
        self.assertEqual(match.match('Ice Shied').match, 'fuzzy')
        self.assertIsNone(match.match('Ice Sh').identifier)
        self.assertIsNone(Matcher({'1': 'Ice Shield', '2': 'Ice Shields'}).match('Ice Shied').identifier)

    def test_confirm_expire_reroll_partial_and_changed_game(self):
        matcher = Matcher(NAMES); state = OfferState(); context = ('game', 222, 'arena')
        a = tuple(matcher.match(n) for n in ('Critical Rhythm', 'Fire Power', 'Ice Shield'))
        state.observe(context, a, 0)
        self.assertIsNone(state.current(context, .1))
        state.observe(context, a, 1)
        self.assertEqual(state.current(context, 1).choices, a)
        self.assertIsNone(state.current(('other', 222, 'arena'), 1))
        self.assertIsNone(state.current(context, 3))
        changed = (a[0], matcher.match('Quick Feet'), Choice(None, None))
        state.observe(context, changed, 1.5)
        self.assertIsNone(state.current(context, 1.5))
        state.observe(context, changed, 2)
        self.assertEqual(state.current(context, 2).choices[1].identifier, '4')
        state.observe(context, (a[0], a[0], a[2]), 2.5)
        self.assertIsNone(state.current(context, 2.5))
        state.observe(context, (a[0], Choice(None, None), Choice(None, None)), 3)
        self.assertIsNone(state.current(context, 3))

    def test_only_offered_ids_and_allowed_metrics_are_projected_in_screen_order(self):
        offer = Offer(('g', 222, 'arena'), 1, 1, (Choice('3', 'Ice Shield'), Choice('1', 'Critical Rhythm'), Choice(None, None)))
        view = offer_view('g', offer, {'3': {'pick_rate': 10, 'games': 100, 'win_rate': 99.99},
                                     '1': {'pick_rate': 20, 'games': 200},
                                     '2': {'pick_rate': 98, 'games': 999}})
        value = str(view)
        self.assertLess(value.index('Ice Shield'), value.index('Critical Rhythm'))
        self.assertNotIn('99.99', value)
        self.assertNotIn('999', value)
        self.assertIn('Carta não identificada', value)
        self.assertNotIn('NaN', str(offer_view('g', offer, {'3': {'pick_rate': float('nan')}})))

    def test_title_crops_are_bounded_at_supported_resolutions(self):
        for w, h in ((1024, 768), (1280, 1024), (1920, 1080), (3440, 1440), (3840, 2160)):
            rows = title_rects(w, h)
            self.assertEqual(len(rows), 3)
            for x, y, cw, ch in rows:
                self.assertTrue(0 <= x < x + cw <= w)
                self.assertTrue(0 <= y < y + ch <= h)
        with self.assertRaises(ValueError):
            title_rects(200, 100)

    def test_reader_discards_result_after_context_change_and_closes(self):
        from tests.test_build_workflow import FakeLCU
        lcu = FakeLCU()
        screen = Mock()
        screen.capture.return_value = ('target', (1, 2, 3))
        screen.valid.return_value = True
        ocr = Mock()
        reader = OfferReader(lcu, screen_factory=lambda: screen, ocr_factory=lambda: ocr)
        reader.catalog.names = lambda name: NAMES
        first, second = ('a', 222, 'arena'), ('b', 222, 'arena')
        def recognize(images):
            reader.ensure(second)
            return ['Critical Rhythm', 'Fire Power', 'Ice Shield']
        ocr.recognize.side_effect = recognize
        reader.ensure(first)
        until = time.monotonic() + 2
        while not ocr.recognize.called and time.monotonic() < until:
            time.sleep(.01)
        self.assertTrue(ocr.recognize.called)
        self.assertIsNone(reader.current(first))
        self.assertIsNone(reader.current(second))
        reader.close()
        self.assertTrue(reader._stop.is_set())
        self.assertIsNone(reader.current(second))


if __name__ == '__main__':
    unittest.main()
