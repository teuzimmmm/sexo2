import unittest
from pathlib import Path

from lolalytics.builds import build_page
from lolalytics.errors import DataUnavailable, SchemaError
from lolalytics.models import Snapshot
from lolalytics.parsing import parse_page
from lolalytics.query import Query


def make_snapshot(mode="ranked"):
    return Snapshot(
        query={"champion": "ahri", "mode": mode, "lane": "middle"},
        resolved={"champion": "ahri", "mode": mode, "patch": "16.20", "keystone": 8992},
        source_url="https://example.invalid/filtered",
        collected_at="2026-10-16T00:00:00Z",
        overview={}, records=[], availability={}, raw={"summary": {
            "win": {"runes": {"page": {"pri": 2, "sec": 3}, "set": {
                "pri": [8992, 8226, 8210, 8237], "sec": [8473, 8451], "mod": [5008, 5010, 5011]}},
                "items": {"start": {"set": [1056, 2003, 2003], "wr": 53.25, "n": 19477,
                                     "future": "preserved"},
                          "core": {"set": [3118, 3020, 3100], "wr": 59.33, "n": 1077},
                          "item4": [{"id": 3041, "n": 711, "wr": 77.78}, {"id": 3089, "n": 2748, "wr": 60.23}],
                          "item5": [{"id": 3041, "n": 430, "wr": 73.72}],
                          "item6": [{"id": 3089, "n": 328, "wr": 62.5}]}},
            "pick": {"runes": {"page": {"pri": 2, "sec": 3}, "set": {
                "pri": [8992, 8226, 8210, 8237], "sec": [8473, 8451], "mod": [5008, 5010, 5011]}},
                "items": {"core": {"set": [3118, 3020, 4645], "wr": 52.67, "n": 1927},
                          "item4": [{"id": 3157, "n": 3318, "wr": 56.39}]}}}},
        warnings=[], cache_hit=True,
    )


class BuildPageTests(unittest.TestCase):
    def test_build_page_preserves_blocks_metrics_and_repeated_start_counts(self):
        page = build_page(make_snapshot(), "win", 8992)
        self.assertEqual(page.title, "WR 59.3% / 1.077 jogos")
        self.assertEqual(page.runes, {"pri": ["8992", "8226", "8210", "8237"], "sec": ["8473", "8451"],
                                     "mod": ["5008", "5010", "5011"], "page": {"pri": 2, "sec": 3}})
        blocks = {block.kind: block for block in page.blocks}
        self.assertEqual([(c.identifier, c.count) for c in blocks["starting"].choices], [("1056", 1), ("2003", 2)])
        self.assertEqual(blocks["starting"].choices[1].raw["future"], "preserved")
        self.assertEqual([c.identifier for c in blocks["core"].choices], ["3118", "3020", "3100"])
        self.assertEqual(blocks["core"].metrics, {"win_rate": 59.33, "games": 1077})
        self.assertEqual(blocks["core"].choices[0].metrics, {})
        self.assertEqual(blocks["item4"].choices[0].metrics, {"win_rate": 77.78, "games": 711})
        self.assertIn("not_full_rune_page_joint_sample", page.warnings)
        self.assertIn("keystone_conditioned", page.warnings)
        self.assertTrue(page.cache_hit)
        self.assertEqual(page.to_dict()["blocks"][1]["choices"][0]["count"], 1)

    def test_pick_titles_use_core_metrics_and_optional_empty_groups_warn(self):
        snapshot = make_snapshot()
        items = snapshot.raw["summary"]["pick"]["items"]
        items["start"] = {"set": []}
        items["item4"] = []
        page = build_page(snapshot, "pick", 8992)
        self.assertEqual(page.title, "Common 52.7% / 1.927 jogos")
        self.assertEqual([block.kind for block in page.blocks], ["core"])
        for warning in ("starting_items_unavailable", "item4_unavailable", "item5_unavailable", "item6_unavailable"):
            self.assertIn(warning, page.warnings)

    def test_missing_title_metrics_render_without_duplicate_prefix_or_zero(self):
        snapshot = make_snapshot()
        core = snapshot.raw["summary"]["win"]["items"]["core"]
        core["wr"] = None
        core["n"] = None
        self.assertEqual(build_page(snapshot, "win", 8992).title, "WR indisponível / jogos indisponíveis")
        pick_core = snapshot.raw["summary"]["pick"]["items"]["core"]
        pick_core["wr"] = "xx.xx"
        pick_core.pop("n")
        self.assertEqual(build_page(snapshot, "pick", 8992).title, "Common indisponível / jogos indisponíveis")

    def test_mismatch_missing_layout_and_bad_core_size_have_expected_errors(self):
        with self.assertRaisesRegex(DataUnavailable, "does not match"):
            build_page(make_snapshot(), "win", 8112)
        snapshot = make_snapshot()
        del snapshot.raw["summary"]["win"]["runes"]["set"]["mod"]
        with self.assertRaisesRegex(DataUnavailable, "missing mod"):
            build_page(snapshot, "win", 8992)
        snapshot = make_snapshot()
        snapshot.raw["summary"]["win"]["items"]["core"]["set"] = []
        with self.assertRaisesRegex(DataUnavailable, "exactly three"):
            build_page(snapshot, "win", 8992)

    def test_invalid_object_types_are_schema_errors_while_missing_values_are_unavailable(self):
        mutations = [
            (lambda s: s.raw.update(summary=[]), "summary must be an object"),
            (lambda s: s.raw["summary"].update(win=[]), "summary.win must be an object"),
            (lambda s: s.raw["summary"]["win"].update(runes=[]), "runes must be an object"),
            (lambda s: s.raw["summary"]["win"]["runes"].update(set=[]), "runes.set must be an object"),
            (lambda s: s.raw["summary"]["win"].update(items=[]), "items must be an object"),
            (lambda s: s.raw["summary"]["win"]["items"].update(core=[]), "items.core must be an object"),
        ]
        for mutate, message in mutations:
            with self.subTest(message=message):
                snapshot = make_snapshot()
                mutate(snapshot)
                with self.assertRaisesRegex(SchemaError, message):
                    build_page(snapshot, "win", 8992)
        for remove in (
            lambda s: s.raw.pop("summary"),
            lambda s: s.raw["summary"].pop("win"),
            lambda s: s.raw["summary"]["win"].pop("runes"),
            lambda s: s.raw["summary"]["win"]["runes"].pop("set"),
            lambda s: s.raw["summary"]["win"].pop("items"),
            lambda s: s.raw["summary"]["win"]["items"].pop("core"),
        ):
            with self.subTest(remove=remove):
                snapshot = make_snapshot()
                remove(snapshot)
                with self.assertRaises(DataUnavailable):
                    build_page(snapshot, "win", 8992)

    def test_ids_metrics_and_alternatives_are_validated(self):
        for bad_id in ("", "  ", True, None, 0, -1):
            with self.subTest(bad_id=bad_id):
                snapshot = make_snapshot()
                snapshot.raw["summary"]["win"]["items"]["core"]["set"][0] = bad_id
                with self.assertRaises(SchemaError):
                    build_page(snapshot, "win", 8992)
        for bad_wr in (-0.1, 100.1, True, float("inf"), "bad"):
            with self.subTest(bad_wr=bad_wr):
                snapshot = make_snapshot()
                snapshot.raw["summary"]["win"]["items"]["core"]["wr"] = bad_wr
                with self.assertRaises(SchemaError):
                    build_page(snapshot, "win", 8992)
        for bad_n in (-1, True, 1.5, "xx.xx"):
            with self.subTest(bad_n=bad_n):
                snapshot = make_snapshot()
                snapshot.raw["summary"]["win"]["items"]["core"]["n"] = bad_n
                with self.assertRaises(SchemaError):
                    build_page(snapshot, "win", 8992)
        snapshot = make_snapshot("arena")
        with self.assertRaisesRegex(DataUnavailable, "only for ranked and ARAM"):
            build_page(snapshot, "win", 8992)

    def test_real_filtered_fixtures_keep_each_suggestion_with_its_keystone(self):
        root = Path(__file__).parent / "fixtures" / "lolalytics" / "keystone"
        cases = [
            ("ahri-ranked-win.json", Query("ahri", lane="middle", keystone=8992), 8992, "win"),
            ("ahri-ranked-pick.json", Query("ahri", lane="middle", keystone=8112), 8112, "pick"),
            ("jinx-aram-filtered.json", Query("jinx", mode="aram", tier="all", keystone=8008), 8008, "win"),
        ]
        for fixture, query, keystone, selection in cases:
            with self.subTest(fixture=fixture):
                snapshot = parse_page((root / fixture).read_bytes(), query, query.url, "2026-10-16T00:00:00Z")
                page = build_page(snapshot, selection, keystone)
                self.assertEqual(page.keystone, keystone)
                self.assertEqual(page.runes["pri"][0], str(keystone))
                self.assertEqual(page.blocks[1].kind, "core")
                self.assertIsNotNone(page.core_metrics["games"])


if __name__ == "__main__":
    unittest.main()
