import unittest
from pathlib import Path

from lolalytics.builds import BuildPage, ItemBlock, ItemChoice, build_page
from lolalytics.matchups import build_matchup_page
from lolalytics.errors import QueryError
from lolalytics.item_pages import PreparedItemPage, plan_item_pages
from lolalytics.parsing import parse_page
from lolalytics.query import Query


def make_page(
    selection="win",
    *,
    champion="ahri",
    patch="16.20",
    mode="ranked",
    tier="emerald_plus",
    region="all",
    lane="middle",
    blocks=5,
    label=None,
):
    label = label or {"win": "WR", "pick": "Common", "vs": "vs Annie"}.get(selection, selection)
    conditioning = "opponent" if selection == "vs" else "keystone"
    return BuildPage(
        selection=selection,
        label=label,
        title=f"ignored full title for {label}",
        keystone=8992,
        runes={"pri": ["8992"]},
        blocks=[
            ItemBlock(
                "core" if i == 0 else f"item{i}",
                [ItemChoice("1001", 1, {"win_rate": 55.0, "games": 23}, {"raw": i})],
                {"win_rate": 60.0, "games": 5},
                f"payload.block{i}",
                True,
            )
            for i in range(blocks)
        ],
        core_metrics={"win_rate": 60.0, "games": 5},
        source_url="https://example.invalid/build",
        query={"champion": champion, "mode": mode, "patch": patch, "tier": tier, "region": region, "lane": lane},
        resolved={
            "champion": champion,
            "mode": mode,
            "patch": patch,
            "tier": tier,
            "region": region,
            "effective_lane": lane,
            "champion_name": champion.title(),
        },
        collected_at="2026-10-16T00:00:00Z",
        cache_hit=False,
        warnings=["source-warning"],
        conditioning=conditioning,
        matchup_metrics={"scope": "champion_matchup", "win_rate": 49.5, "games": 321} if selection == "vs" else None,
    )


class PlanItemPagesTests(unittest.TestCase):
    def test_three_suggestions_fit_one_page_with_prefixed_labels_and_source(self):
        pages = [make_page("win", blocks=5), make_page("pick", blocks=5), make_page("vs", blocks=7)]
        prepared = plan_item_pages(pages)
        self.assertEqual(len(prepared), 1)
        self.assertIsInstance(prepared[0], PreparedItemPage)
        self.assertEqual(prepared[0].title, "Builds de Ahri")
        labels = [block.label for block in prepared[0].blocks]
        self.assertEqual(labels[0], "WR · Core")
        self.assertEqual(labels[5], "Common · Core")
        self.assertEqual(labels[10], "vs Annie · Core")
        self.assertEqual(prepared[0].blocks[10].source["scope"], "opponent_conditioned")
        self.assertEqual(prepared[0].blocks[10].source["conditioning"], "opponent")
        self.assertEqual(prepared[0].blocks[10].source["matchup_metrics"], pages[2].matchup_metrics)
        self.assertEqual(prepared[0].blocks[0].source["core_metrics"], pages[0].core_metrics)
        self.assertEqual(prepared[0].blocks[0].source["title"], pages[0].title)
        self.assertEqual(prepared[0].blocks[0].source["resolved"], pages[0].resolved)
        self.assertEqual(prepared[0].to_dict()["blocks"][0]["block"]["choices"][0]["identifier"], "1001")

    def test_capacity_is_prevalidated_and_can_be_raised_explicitly(self):
        pages = [
            make_page("win", blocks=6),
            make_page("pick", blocks=6),
            make_page("vs", blocks=6),
            make_page("vs", blocks=6, label="vs Ryze"),
        ]
        with self.assertRaisesRegex(QueryError, "require 2 pages"):
            plan_item_pages(pages)
        prepared = plan_item_pages(pages, max_pages=2)
        self.assertEqual([len(page.blocks) for page in prepared], [20, 4])
        self.assertEqual([page.title for page in prepared], ["Builds de Ahri · 1/2", "Builds de Ahri · 2/2"])
        self.assertEqual(prepared[1].blocks[0].label, "vs Ryze · Item 2")

    def test_duplicate_item_ids_keep_context_order_metrics_and_counts(self):
        first = make_page("win", blocks=1)
        second = make_page("vs", blocks=1)
        first.blocks[0].choices[0].count = 2
        first.blocks[0].choices[0].metrics = {"win_rate": 61.1, "games": 900}
        second.blocks[0].choices[0].count = 1
        second.blocks[0].choices[0].metrics = {"win_rate": 48.2, "games": 12}
        planned = plan_item_pages([first, second])[0].blocks
        self.assertEqual([block.block.choices[0].identifier for block in planned], ["1001", "1001"])
        self.assertEqual([block.block.choices[0].count for block in planned], [2, 1])
        self.assertEqual([block.block.choices[0].metrics["win_rate"] for block in planned], [61.1, 48.2])

    def test_sources_and_blocks_are_independent_deep_copies(self):
        original = make_page("win", blocks=1)
        prepared = plan_item_pages([original, original])[0]
        self.assertEqual(len(prepared.blocks), 2)
        prepared.blocks[0].block.choices[0].raw["raw"] = "changed"
        prepared.blocks[0].source["warnings"].append("changed")
        self.assertEqual(original.blocks[0].choices[0].raw, {"raw": 0})
        self.assertEqual(original.warnings, ["source-warning"])
        self.assertEqual(prepared.blocks[1].block.choices[0].raw, {"raw": 0})
        self.assertEqual(prepared.blocks[1].source["warnings"], ["source-warning"])

    def test_mismatched_champion_patch_or_filters_are_rejected(self):
        cases = [
            (make_page("pick", champion="annie"), "champion"),
            (make_page("pick", patch="16.19"), "patch"),
            (make_page("pick", mode="aram"), "mode"),
            (make_page("pick", tier="gold"), "tier"),
            (make_page("pick", region="br"), "region"),
            (make_page("pick", lane="top"), "effective lane"),
        ]
        for other, mismatch in cases:
            with self.subTest(mismatch=mismatch):
                with self.assertRaisesRegex(QueryError, mismatch):
                    plan_item_pages([make_page("win"), other])

    def test_malformed_metadata_and_empty_suggestions_are_rejected(self):
        for field, value in (("query", []), ("resolved", None)):
            with self.subTest(field=field):
                page = make_page(blocks=1)
                setattr(page, field, value)
                with self.assertRaisesRegex(QueryError, field):
                    plan_item_pages([page])
        page = make_page(blocks=1)
        page.blocks = []
        with self.assertRaisesRegex(QueryError, "each build suggestion"):
            plan_item_pages([page, make_page("pick", blocks=1)])
        page = make_page(blocks=1)
        page.blocks[0].choices = []
        with self.assertRaisesRegex(QueryError, "at least one choice"):
            plan_item_pages([page])

    def test_bad_inputs_and_limits_are_rejected(self):
        for kwargs in (
            {"max_pages": True},
            {"max_pages": 0},
            {"max_pages": 21},
            {"max_blocks_per_page": True},
            {"max_blocks_per_page": 0},
            {"max_blocks_per_page": 101},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(QueryError):
                    plan_item_pages([make_page(blocks=1)], **kwargs)
        with self.assertRaises(QueryError):
            plan_item_pages([])
        with self.assertRaises(QueryError):
            plan_item_pages([make_page(blocks=0)])
        with self.assertRaises(QueryError):
            plan_item_pages([make_page(blocks=1)] * 21)
        with self.assertRaises(QueryError):
            plan_item_pages([object()])

    def test_real_win_common_and_matchup_fixtures_keep_separate_sources(self):
        fixture_root = Path(__file__).parent / "fixtures" / "lolalytics"
        query_cases = [
            ("keystone/ahri-ranked-win.json", Query("ahri", lane="middle", keystone=8992), "win", 8992),
            ("keystone/ahri-ranked-pick.json", Query("ahri", lane="middle", keystone=8112), "pick", 8112),
        ]
        pages = []
        for filename, query, selection, key in query_cases:
            snapshot = parse_page((fixture_root / filename).read_bytes(), query, query.url, "2026-10-16T00:00:00Z")
            pages.append(build_page(snapshot, selection, key))
        matchup_query = Query("ahri", lane="middle", opponent="annie", opponent_lane="middle")
        matchup_snapshot = parse_page(
            (fixture_root / "matchups" / "ahri-vs-annie.json").read_bytes(),
            matchup_query,
            matchup_query.url,
            "2026-10-16T00:00:00Z",
        )
        matchup = build_matchup_page(matchup_snapshot)
        pages.append(matchup)

        planned = plan_item_pages(pages)
        self.assertEqual(len(planned), 1)
        self.assertEqual(planned[0].title, "Builds de Ahri")
        self.assertEqual(len(planned[0].blocks), 17)
        self.assertEqual(
            [block.label for block in planned[0].blocks[10:]],
            [
                "vs Annie · Starting",
                "vs Annie · Item 1",
                "vs Annie · Item 2",
                "vs Annie · Item 3",
                "vs Annie · Item 4",
                "vs Annie · Item 5",
                "vs Annie · Item 6",
            ],
        )
        for entry in planned[0].blocks[10:]:
            self.assertEqual(entry.source["conditioning"], "opponent")
            self.assertEqual(entry.source["resolved"]["opponent"], "annie")
            self.assertEqual(entry.source["matchup_metrics"], matchup.matchup_metrics)
            self.assertIsNone(entry.source["core_metrics"]["win_rate"])
        self.assertFalse(any("Core" in entry.label for entry in planned[0].blocks[10:]))

    def test_real_filtered_general_fixtures_can_be_planned_together(self):
        fixture_root = Path(__file__).parent / "fixtures" / "lolalytics" / "keystone"
        cases = [
            ("ahri-ranked-win.json", Query("ahri", lane="middle", keystone=8992), "win", 8992),
            ("ahri-ranked-pick.json", Query("ahri", lane="middle", keystone=8112), "pick", 8112),
        ]
        pages = []
        for filename, query, selection, key in cases:
            snapshot = parse_page((fixture_root / filename).read_bytes(), query, query.url, "2026-10-16T00:00:00Z")
            page = build_page(snapshot, selection, key)
            pages.append(page)
        prepared = plan_item_pages(pages)
        self.assertEqual(len(prepared), 1)
        self.assertEqual(len(prepared[0].blocks), 10)
        self.assertEqual(prepared[0].blocks[0].label, "WR · Starting")
        self.assertEqual(prepared[0].blocks[5].label, "Common · Starting")


if __name__ == "__main__":
    unittest.main()
