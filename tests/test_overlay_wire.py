import json
import unittest

from sexo2.overlay.model import Card, View
from sexo2.overlay.runtime import Frame
from sexo2.overlay.wire import MAX_BYTES, ProtocolError, encode


class WireTests(unittest.TestCase):
    def frame(self, *cards, selected=0, active=True):
        return Frame(active, View('private-context-must-not-cross', cards, selected))

    def test_only_display_fields_cross_boundary(self):
        data = encode(self.frame(Card('Arena · popularidade', ('Escolha: 12.4%', '214 jogos'))), 1)
        row = json.loads(data)
        self.assertNotIn(b'private-context', data)
        self.assertEqual(set(row), {'v', 'seq', 'ttlMs', 'active', 'preview', 'selected', 'cards'})
        self.assertEqual(row['cards'][0]['title'], 'Arena · popularidade')
        self.assertTrue(data.endswith(b'\n'))
        self.assertEqual(data.count(b'\n'), 1)

    def test_disabled_discards_stale_view(self):
        data = json.loads(encode(self.frame(Card('Old', ('Old',)), active=False), 2))
        self.assertEqual(data['cards'], [])
        self.assertEqual(data['selected'], 0)

    def test_limits_do_not_truncate_a_recommendation(self):
        invalid = [self.frame(*([Card('x', ())] * 17)),
                   self.frame(Card('x', ('x',) * 257)),
                   self.frame(Card('x' * 513, ())),
                   self.frame(Card('x', ('x' * 513,))),
                   self.frame(Card('x', ('with\nnewline',))),
                   self.frame(Card('x', ('bad\ud800',))),
                   self.frame(Card('x', ('direction\u202e',))),
                   self.frame(Card('x', ()), selected=-1),
                   self.frame(Card('x', ()), selected=True),
                   self.frame(Card('x', ()), selected=1)]
        for frame in invalid:
            with self.subTest(frame=repr(frame)[:40]), self.assertRaises(ProtocolError):
                encode(frame, 1)

    def test_unicode_uses_byte_limit(self):
        frame = self.frame(*([Card('á', ('á' * 512,) * 256)] * 2))
        with self.assertRaisesRegex(ProtocolError, 'byte limit'):
            encode(frame, 1)
        self.assertLess(len(encode(self.frame(Card('á', ('á' * 512,) * 128)), 1)), MAX_BYTES)

    def test_sequence_and_ttl_are_strict(self):
        for seq in (True, 0, -1, 2**53, 1.5):
            with self.subTest(sequence=seq), self.assertRaises(ProtocolError):
                encode(Frame(), seq)
        for ttl in (True, 0, -1, 8001, 1.5):
            with self.subTest(ttl=ttl), self.assertRaises(ProtocolError):
                encode(Frame(), 1, ttl_ms=ttl)


if __name__ == '__main__':
    unittest.main()
