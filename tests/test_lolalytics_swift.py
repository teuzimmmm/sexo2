"""Swiftplay regression from real sanitized responses, without app adapters."""

import unittest
from pathlib import Path
from unittest.mock import Mock
from lolalytics import Client, Query, plan_item_pages
from lolalytics.errors import QueryError

DATA = Path(__file__).parent / "fixtures/lolalytics/swift"


class SwiftplayTests(unittest.TestCase):
    def test_real_summaries_preserve_mode_without_fake_keystone_conditioning(self):
        for champion, cid in [("ahri", 103), ("jinx", 222)]:
            with self.subTest(champion=champion):
                transport = Mock()
                transport.get.return_value = (DATA / (champion + "-swift.json")).read_bytes()
                with Client(transport=transport) as client:
                    pages = client.collect_builds(Query(champion, mode="swift")).pages
                    self.assertEqual(transport.get.call_count, 1)
                    self.assertEqual([p.selection for p in pages], ["win", "pick"])
                    self.assertTrue(
                        all(
                            p.conditioning == "mode" and p.query["mode"] == "swift" and p.resolved["cid"] == cid
                            for p in pages
                        )
                    )
                    self.assertTrue(all("mode_summary_unfiltered" in p.warnings for p in pages))
                    self.assertFalse(any(c.identifier == "0" for p in pages for b in p.blocks for c in b.choices))
                    self.assertEqual(len(plan_item_pages(pages)), 1)
                    with self.assertRaises(QueryError):
                        client.recommend(Query(champion, mode="swift"))

    def test_unsupported_filters_fail_before_network(self):
        for kwargs in [dict(keystone=8112), dict(lane="middle"), dict(region="br"), dict(tier="gold")]:
            with self.subTest(filters=kwargs), self.assertRaises(QueryError):
                Query("ahri", mode="swift", **kwargs)
