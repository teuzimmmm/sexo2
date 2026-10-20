"""Augment catalog, statistics, offer tracking and recognition on real captures."""

import sys
import unittest
from pathlib import Path

from PIL import Image

from sexo2.augments.catalog import build_catalog
from sexo2.augments.offers import CardRead, OfferTracker
from sexo2.augments.stats import (
    AugmentStat,
    aramkit_champion_url,
    aramkit_data_path,
    parse_aramkit_champion,
    parse_lolalytics_arena,
)
from sexo2.augments.view import card_views
from sexo2.augments.vision import IconMatcher, Layout, card_area, cards_present, crops, read_offer

CAPTURES = Path(__file__).parent / "fixtures" / "augments"

CHERRY = [
    {
        "id": 1205,
        "augmentNameId": "ARAM_ADAPt",
        "nameTRA": "ADAPt",
        "augmentSmallIconPath": "/a.png",
        "rarity": "kSilver",
    },
    {"id": 1141, "augmentNameId": "ARAM_AllForYou", "nameTRA": "Tudo por Você", "rarity": "kGold"},
    {"id": 1004, "augmentNameId": "ARAM_BacktoBasics", "nameTRA": "De Volta ao Básico", "rarity": "kPrismatic"},
    {"id": 99, "augmentNameId": "ArenaOnly", "nameTRA": "Só na Arena", "rarity": "kSilver"},
    {"id": 98, "augmentNameId": "", "nameTRA": ""},
]
LISTS = [
    {"modeName": "CHERRY", "augmentList": ["Maps/ModeSpecificData/Augments/ArenaOnly", "Maps/x/ARAM_ADAPt"]},
    {
        "modeName": "KIWI",
        "augmentList": ["Maps/x/ARAM_ADAPt", "Maps/x/ARAM_AllForYou", "Maps/x/ARAM_BacktoBasics", "Maps/x/Missing"],
    },
]


def stat(augment_id, wr, games, mode="mayhem", pr=5.0):
    return AugmentStat(augment_id, mode, "aramkit", "16.20", "champion", wr, pr, games)


class CatalogTests(unittest.TestCase):
    def test_pools_are_separate_per_mode(self):
        mayhem = build_catalog(CHERRY, LISTS, "mayhem")
        arena = build_catalog(CHERRY, LISTS, "arena")
        self.assertEqual([a.id for a in mayhem.augments], [1205, 1141, 1004])
        self.assertEqual(mayhem.unmatched, ("Missing",))
        self.assertEqual([a.id for a in arena.augments], [99, 1205])
        self.assertEqual(mayhem.by_id(1004).rarity, "prismatic")
        self.assertIsNone(mayhem.by_id(99))

    def test_unknown_mode_or_pool_fails(self):
        with self.assertRaises(ValueError):
            build_catalog(CHERRY, LISTS, "urf")
        with self.assertRaises(ValueError):
            build_catalog(CHERRY, [], "mayhem")
        with self.assertRaises(ValueError):
            build_catalog([], [], "arena")

    def test_arena_also_takes_augments_missing_from_its_pool(self):
        # Queue 1750 (20/10/2026): the cards offered were not in the CHERRY pool
        new = CHERRY + [{"id": 2001, "augmentNameId": "NewArena", "nameTRA": "Nova", "rarity": "kGold"}]
        arena = build_catalog(new, LISTS, "arena")
        self.assertEqual([a.id for a in arena.augments], [99, 1205, 2001])  # pool first, Mayhem-only left out
        self.assertEqual([a.id for a in build_catalog(new, [], "arena").augments], [1205, 1141, 1004, 99, 2001])


class StatsTests(unittest.TestCase):
    def test_aramkit_rates_become_percent_and_bad_rows_are_skipped(self):
        path, version = aramkit_data_path(
            {"latest": "16.20", "versions": [{"version": "16.20", "dataPath": "/v/16.20/"}]}
        )
        self.assertEqual((path, version), ("v/16.20", "16.20"))
        self.assertEqual(
            aramkit_champion_url(path, 103), "https://data.aramkit.com/data/v/16.20/stats/all/champion-details/103.json"
        )
        stats = parse_aramkit_champion(
            {
                "augments": {
                    "all": [
                        {"id": 1205, "winRate": 0.5312, "pickRate": 0.041, "sampleCount": 812},
                        {"id": 1141, "winRate": 1.7, "pickRate": None, "sampleCount": -1},
                        {"id": "x"},
                    ]
                }
            },
            "16.20",
        )
        self.assertEqual((stats[1205].win_rate, stats[1205].pick_rate, stats[1205].games), (53.12, 4.1, 812))
        self.assertEqual((stats[1141].win_rate, stats[1141].pick_rate, stats[1141].games), (None, None, None))
        self.assertEqual(stats[1205].mode, "mayhem")
        with self.assertRaises(ValueError):
            parse_aramkit_champion({"augments": {}}, "16.20")

    def test_arena_keeps_pick_rate_and_games_without_win_rate(self):
        sys.path.insert(0, str(Path(__file__).parent))
        from test_lolalytics_client import FixtureTransport, query_for
        from lolalytics.client import Client

        query = query_for("ahri-arena.json")
        snapshot = Client(transport=FixtureTransport(("ahri-arena.json",)), ttl=0).collect(query)
        stats = parse_lolalytics_arena(snapshot, 0)
        self.assertNotIn(0, stats)  # "no augment" row
        first = stats[133]
        self.assertEqual(
            (first.mode, first.source, first.patch, first.scope), ("arena", "lolalytics", "16.20", "champion_choice_1")
        )
        self.assertIsNone(first.win_rate)
        self.assertEqual((first.pick_rate, first.games), (17.74, 9777))
        with self.assertRaises(ValueError):
            parse_lolalytics_arena(snapshot, 5)


def reads(*ids):
    return [CardRead(i, 0.9) for i in ids]


class OfferTrackerTests(unittest.TestCase):
    def test_opens_after_two_frames_and_closes_after_three_empty(self):
        tracker = OfferTracker()
        self.assertFalse(tracker.observe(reads(1, 2, 3)))
        self.assertTrue(tracker.observe(reads(1, 2, 3)))
        self.assertEqual([c.augment_id for c in tracker.offer.cards], [1, 2, 3])
        self.assertFalse(tracker.observe(None))
        self.assertFalse(tracker.observe(None))
        self.assertTrue(tracker.observe(None))
        self.assertIsNone(tracker.offer)

    def test_one_bad_frame_changes_nothing_and_a_reroll_is_followed(self):
        tracker = OfferTracker()
        tracker.observe(reads(1, 2, 3))
        tracker.observe(reads(1, 2, 3))
        sequence = tracker.offer.sequence
        self.assertFalse(tracker.observe(reads(1, 9, 3)))  # one frame only
        self.assertFalse(tracker.observe(reads(1, 2, 3)))
        self.assertFalse(tracker.observe(None))  # one missing frame does not close
        self.assertFalse(tracker.observe(reads(1, 4, 3)))
        self.assertTrue(tracker.observe(reads(1, 4, 3)))
        self.assertEqual([c.augment_id for c in tracker.offer.cards], [1, 4, 3])
        self.assertEqual(tracker.offer.sequence, sequence)  # a reroll is the same offer

    def test_a_correction_survives_the_wrong_reading_but_not_a_reroll(self):
        tracker = OfferTracker()
        tracker.observe(reads(1, 2, 3))
        tracker.observe(reads(1, 2, 3))
        tracker.correct(1, 7)
        for _ in range(3):
            tracker.observe(reads(1, 2, 3))
        self.assertEqual(tracker.offer.cards[1].augment_id, 7)
        self.assertTrue(tracker.offer.cards[1].manual)
        tracker.observe(reads(1, 5, 3))
        tracker.observe(reads(1, 5, 3))
        self.assertEqual(tracker.offer.cards[1].augment_id, 5)
        self.assertFalse(tracker.offer.cards[1].manual)

    def test_new_offer_after_close_gets_a_new_sequence(self):
        tracker = OfferTracker()
        for _ in range(2):
            tracker.observe(reads(1, 2, 3))
        first = tracker.offer.sequence
        for _ in range(3):
            tracker.observe(None)
        for _ in range(2):
            tracker.observe(reads(4, 5, 6))
        self.assertEqual(tracker.offer.sequence, first + 1)


class CardViewTests(unittest.TestCase):
    def setUp(self):
        self.catalog = build_catalog(CHERRY, LISTS, "mayhem")
        self.tracker = OfferTracker()

    def offer(self, *cards):
        for _ in range(2):
            self.tracker.observe(list(cards))
        return self.tracker.offer

    def test_highlights_the_best_win_rate_among_known_cards_with_enough_games(self):
        offer = self.offer(CardRead(1205, 0.9), CardRead(1141, 0.9), CardRead(1004, 0.9))
        views = card_views(
            offer, self.catalog, {1205: stat(1205, 52.0, 900), 1141: stat(1141, 55.0, 600), 1004: stat(1004, 60.0, 50)}
        )
        self.assertEqual([v.highlight for v in views], [False, True, False])  # 60% has too few games
        self.assertEqual([v.state for v in views], ["ok", "ok", "ok"])

    def test_unsure_or_foreign_cards_are_unknown_and_never_highlighted(self):
        offer = self.offer(CardRead(1205, 0.3), CardRead(99, 0.95), CardRead(1141, 0.9))
        views = card_views(offer, self.catalog, {1205: stat(1205, 70.0, 900), 1141: stat(1141, 50.0, 900)})
        self.assertEqual([v.state for v in views], ["unknown", "unknown", "ok"])
        self.assertFalse(any(v.highlight for v in views))  # one figure alone decides nothing

    def test_no_data_and_other_mode_figures_show_no_numbers(self):
        offer = self.offer(CardRead(1205, 0.9), CardRead(1141, 0.9), CardRead(1004, 0.9))
        views = card_views(offer, self.catalog, {1205: stat(1205, None, 900, mode="arena", pr=9.0)})
        self.assertEqual([v.state for v in views], ["no_data", "no_data", "no_data"])

    def test_pick_rate_only_is_never_highlighted(self):
        offer = self.offer(CardRead(1205, 0.9), CardRead(1141, 0.9), CardRead(1004, 0.9))
        figures = {i: stat(i, None, 5000, pr=pr) for i, pr in ((1205, 20.0), (1141, 30.0), (1004, 1.0))}
        self.assertFalse(any(v.highlight for v in card_views(offer, self.catalog, figures)))


# Augments on the captures, by position; templates come from the 600 px captures.
LABELS = {
    "1920x1080_gold": "ABC",
    "1920x1080_rerolls": "GHI",
    "1920x1200_wrapped_fr": "DEF",
    "2000x837_prismatic": "PQR",
    "2000x837_silver": "STU",
    "1024x768_gold": "ABC",
    "1024x768_wrapped_fr": "DEF",
    "1280x1024_rerolls": "GHI",
    "1440x900_rerolls": "GHI",
    "1600x900_gold": "ABC",
    "1680x1050_rerolls": "GHI",
    "2000x844_gold": "ABC",
    "3424x1401_wrapped_fr": "DEF",
    "3440x1440_rerolls": "GHI",
}
TEMPLATES = ("1920x1080_gold", "1920x1080_rerolls", "1920x1200_wrapped_fr", "2000x837_prismatic", "2000x837_silver")
IDS = {letter: index for index, letter in enumerate("ABCDEFGHIPQRSTU")}


def capture(name):
    return Image.open(CAPTURES / f"{name}.jpg").convert("RGB")


class VisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        templates = {}
        for name in TEMPLATES:
            for letter, icon in zip(LABELS[name], crops(capture(name))):
                templates[IDS[letter]] = icon
        cls.matcher = IconMatcher(templates)

    def test_card_boxes_scale_with_height_and_stay_centred(self):
        boxes = Layout().cards(1920, 1080)
        self.assertEqual(len(boxes), 3)
        centres = [(left + right) / 2 for left, _, right, _ in boxes]
        self.assertAlmostEqual(centres[0], 598.6, delta=1)
        self.assertAlmostEqual(centres[2], 1334.8, delta=1)
        self.assertEqual(boxes[0][1], 194)

    def test_every_card_is_named_at_other_resolutions_and_scales(self):
        for name, letters in LABELS.items():
            if name in TEMPLATES:
                continue
            with self.subTest(capture=name):
                reading = read_offer(capture(name), self.matcher)
                self.assertIsNotNone(reading)
                self.assertEqual([r.augment_id for r in reading], [IDS[letter] for letter in letters])

    def test_reading_only_the_card_area_gives_the_same_result(self):
        frame = capture("1440x900_rerolls")
        area = card_area(*frame.size)
        part = frame.crop(area)
        self.assertLess(part.size[0] * part.size[1], frame.size[0] * frame.size[1] * 0.5)
        reading = read_offer(part, self.matcher, screen=frame.size, origin=area[:2])
        self.assertEqual([r.augment_id for r in reading], [IDS["G"], IDS["H"], IDS["I"]])

    def test_frames_without_cards_give_no_reading(self):
        self.assertFalse(cards_present(capture("no_cards_champ_select")))
        self.assertIsNone(read_offer(capture("no_cards_champ_select"), self.matcher))

    def test_an_icon_outside_the_pool_stays_unknown(self):
        pool = {i: t for i, t in self.matcher._templates.items() if i != IDS["H"]}
        reading = read_offer(capture("1280x1024_rerolls"), IconMatcher(pool))
        self.assertIsNone(reading[1].augment_id)  # Ravenous Bind is not in this pool
        self.assertEqual(reading[0].augment_id, IDS["G"])
        # Known limit: an icon drawn like another one in a different tint (Overflow and the
        # silver T) is taken for it when the real augment is missing from the pool. The pool
        # must be the full one of the mode being played.

    def test_a_hand_named_card_teaches_the_matcher(self):
        pool = {i: t for i, t in self.matcher._templates.items() if i != IDS["G"]}
        matcher = IconMatcher(pool)
        matcher.add(IDS["G"], crops(capture("1440x900_rerolls"))[0])
        self.assertEqual(read_offer(capture("3440x1440_rerolls"), matcher)[0].augment_id, IDS["G"])


class SessionTests(unittest.TestCase):
    """Catalog and icons from a fake client, readings from a real capture."""

    def setUp(self):
        import io

        from sexo2.augments.session import AugmentSession, load_catalog, load_templates

        icons = {}
        cherry, names = [], []
        for name in ("1920x1080_rerolls", "1920x1080_gold"):
            for letter, icon in zip(LABELS[name], crops(capture(name))):
                buffer = io.BytesIO()
                icon.save(buffer, format="PNG")
                path = f"/lol-game-data/assets/ASSETS/UX/Kiwi/Augments/Icons/{letter}_small.png"
                icons[path] = buffer.getvalue()
                cherry.append(
                    {
                        "id": 100 + IDS[letter],
                        "augmentNameId": f"A_{letter}",
                        "nameTRA": letter,
                        "augmentSmallIconPath": path,
                        "rarity": "kGold",
                    }
                )
                names.append(f"Maps/x/A_{letter}")
        cherry.append(
            {"id": 999, "augmentNameId": "A_noicon", "nameTRA": "Sem ícone", "augmentSmallIconPath": "/missing.png"}
        )
        names.append("Maps/x/A_noicon")

        class FakeLCU:
            def get(self, path, timeout=1.0):
                return {
                    "/lol-game-data/assets/v1/cherry-augments.json": cherry,
                    "/lol-game-data/assets/v1/augment-lists.json": [{"modeName": "KIWI", "augmentList": names}],
                }.get(path)

            def get_bytes(self, path, timeout=2.0):
                return icons.get(path)

        lcu = FakeLCU()
        self.catalog = load_catalog(lcu, "mayhem")
        templates = load_templates(lcu, self.catalog)
        self.assertEqual(len(templates), 6)  # the augment without an icon is left out
        figures = {100 + IDS["G"]: stat(100 + IDS["G"], 51.0, 800), 100 + IDS["I"]: stat(100 + IDS["I"], 54.0, 900)}
        self.session = AugmentSession(self.catalog, IconMatcher(templates), figures)

    def feed(self, name, times=2):
        frame = capture(name)
        for _ in range(times):
            self.session.observe(read_offer(frame, self.session.matcher), crops(frame))

    def test_offer_on_screen_becomes_three_cards_with_their_figures(self):
        self.feed("3440x1440_rerolls")
        cards = self.session.cards()
        self.assertEqual([c.name for c in cards], ["G", "H", "I"])
        self.assertEqual([c.state for c in cards], ["ok", "no_data", "ok"])
        self.assertEqual([c.highlight for c in cards], [False, False, True])
        for _ in range(3):
            self.session.observe(read_offer(capture("no_cards_champ_select"), self.session.matcher))
        self.assertEqual(self.session.cards(), ())

    def test_correction_names_the_card_and_is_refused_outside_the_pool(self):
        self.feed("1440x900_rerolls")
        self.assertFalse(self.session.correct(0, 12345))
        self.assertTrue(self.session.correct(1, 100 + IDS["A"]))
        self.assertEqual(self.session.cards()[1].name, "A")
        self.assertTrue(self.session.cards()[1].manual)


class OverlayTextTests(unittest.TestCase):
    def test_texts_never_invent_a_figure(self):
        from sexo2.overlay.augment_overlay import HIGHLIGHT, MUTED, card_text, text_positions

        catalog = build_catalog(CHERRY, LISTS, "mayhem")
        tracker = OfferTracker()
        for _ in range(2):
            tracker.observe([CardRead(1205, 0.9), CardRead(1141, 0.9), CardRead(None, 0.2)])
        views = card_views(tracker.offer, catalog, {1205: stat(1205, 53.12, 812, pr=4.1), 1141: stat(1141, 50.0, 300)})
        self.assertEqual(card_text(views[0]), ("WR 53,1% · PR 4,1% · 812", HIGHLIGHT))
        self.assertEqual(card_text(views[2]), ("Não reconhecida", MUTED))
        arena = AugmentStat(1205, "mayhem", "lolalytics", "16.20", "champion_choice_1", None, 17.74, 9777)
        views = card_views(tracker.offer, catalog, {1205: arena})
        self.assertEqual(card_text(views[0])[0], "PR 17,7% · 9.777")
        self.assertEqual(card_text(views[1]), ("Sem dados", MUTED))
        positions = text_positions(1920, 1080)
        self.assertEqual(len(positions), 3)
        self.assertGreater(positions[0][1], Layout().cards(1920, 1080)[0][3])


class ArenaMatchTests(unittest.TestCase):
    def test_arena_layout_matches_a_1920x1080_arena_offer(self):
        from sexo2.augments.vision import ARENA_LAYOUT

        measured = [(447, 181, 763, 693), (801, 181, 1118, 693), (1155, 181, 1472, 693)]
        for box, expected in zip(ARENA_LAYOUT.cards(1920, 1080), measured):
            for got, want in zip(box, expected):
                self.assertLessEqual(abs(got - want), 3)
        for left, top, right, bottom in ARENA_LAYOUT.icons(1920, 1080):
            self.assertLessEqual(top, 250)
            self.assertGreaterEqual(bottom, 380)

    def test_queue_and_champion_when_sexo2_joins_a_running_game(self):
        from sexo2.overlay.augment_overlay import champion_from_live, queue_from_gameflow

        self.assertEqual(queue_from_gameflow({"gameData": {"queue": {"id": 1700}}}), 1700)
        self.assertIsNone(queue_from_gameflow({"gameData": {}}))
        self.assertIsNone(queue_from_gameflow(None))
        players = [
            {"riotId": "Outro#BR1", "rawChampionName": "game_character_displayname_Annie"},
            {"riotId": "Eu#BR1", "rawChampionName": "game_character_displayname_MonkeyKing"},
        ]
        summary = [{"id": -1, "alias": "None"}, {"id": 1, "alias": "Annie"}, {"id": 62, "alias": "MonkeyKing"}]
        self.assertEqual(champion_from_live(players, "Eu#BR1", summary), 62)
        self.assertIsNone(champion_from_live(players, "Ninguém#BR1", summary))
        self.assertIsNone(champion_from_live(players, "", summary))

    def test_the_overlay_finds_the_match_from_the_clients(self):
        from types import SimpleNamespace
        from unittest import mock

        from sexo2.augments.vision import ARENA_LAYOUT
        from sexo2.overlay.augment_overlay import AugmentOverlayThread

        class Lcu:
            def get(self, path, **_):
                if path == "/lol-gameflow/v1/session":
                    return {"gameData": {"queue": {"id": 1700}}}
                return [{"id": 62, "alias": "MonkeyKing"}]

        live = {
            "/playerlist": [{"riotId": "Eu#BR1", "rawChampionName": "game_character_displayname_MonkeyKing"}],
            "/activeplayername": "Eu#BR1",
        }
        state = SimpleNamespace(phase="InProgress", current_queue_id=None, locked_champ_id=None)
        overlay = AugmentOverlayThread(state, Lcu())
        with (
            mock.patch.object(overlay, "_live", side_effect=live.__getitem__),
            mock.patch.object(overlay, "_prepare", return_value="session") as prepare,
        ):
            self.assertEqual(overlay._session_for_match(), "session")
            self.assertEqual(overlay._session_for_match(), "session")
        prepare.assert_called_once_with("arena", 62)
        self.assertIs(overlay.layout_for("arena"), ARENA_LAYOUT)
        self.assertEqual(overlay.layout_for("mayhem"), Layout())

    def test_arena_under_a_new_queue_id_is_still_arena(self):
        from types import SimpleNamespace
        from unittest import mock

        from sexo2.augments.session import augment_mode
        from sexo2.overlay.augment_overlay import AugmentOverlayThread

        # The user's Arena on 20/10/2026: queue 1750, game mode CHERRY
        self.assertEqual(augment_mode(1750), "arena")
        self.assertEqual(augment_mode(1799, "CHERRY"), "arena")
        self.assertEqual(augment_mode(2400, "ARAM"), "mayhem")
        self.assertIsNone(augment_mode(420, "CLASSIC"))
        state = SimpleNamespace(
            phase="InProgress", current_queue_id=1799, locked_champ_id=134, current_game_mode="CHERRY"
        )
        overlay = AugmentOverlayThread(state, object())
        with mock.patch.object(overlay, "_prepare", return_value="session") as prepare:
            self.assertEqual(overlay._session_for_match(), "session")
        prepare.assert_called_once_with("arena", 134)


TITLES = {
    "1920x1080_gold": ("Scopier Weapons", "Vulnerability", "Combusting Interest"),
    "1920x1080_rerolls": ("Overflow", "Ravenous Bind", "Upgrade Sheen"),
    "1280x1024_rerolls": ("Overflow", "Ravenous Bind", "Upgrade Sheen"),
    "3440x1440_rerolls": ("Overflow", "Ravenous Bind", "Upgrade Sheen"),
    "2000x837_prismatic": ("Ultimate Revolution", "Blade Waltz", "Overloaded"),
    "2000x837_silver": ("Infernal Soul", "Juiced", "FireFox"),
    "1920x1200_wrapped_fr": ("Gros cerveau", "Expertise en omnivampirisme", "Machine à rétrécir"),
}
TITLE_NAMES = sorted({name for names in TITLES.values() for name in names})


def title_catalog():
    from sexo2.augments.catalog import Augment, Catalog

    return Catalog("mayhem", tuple(Augment(i, f"A{i}", name, "gold", "") for i, name in enumerate(TITLE_NAMES)))


class TitleMatchTests(unittest.TestCase):
    def test_close_readings_name_the_card_and_others_stay_unknown(self):
        from sexo2.augments.ocr import match_name

        catalog = title_catalog()
        by_name = {a.name: a.id for a in catalog.augments}
        self.assertEqual(match_name("Ravenous Bind", catalog).augment_id, by_name["Ravenous Bind"])
        self.assertEqual(
            match_name("Expertise en\nomnivampirisme", catalog).augment_id, by_name["Expertise en omnivampirisme"]
        )
        self.assertEqual(match_name("Machine a retrecir", catalog).augment_id, by_name["Machine à rétrécir"])
        self.assertEqual(match_name("Upgrade Sheen.", catalog).augment_id, by_name["Upgrade Sheen"])
        self.assertIsNone(match_name("Something Else", catalog).augment_id)
        self.assertIsNone(match_name("", catalog).augment_id)

    def test_title_wins_and_icon_backs_it_up(self):
        from sexo2.augments.ocr import combine

        self.assertEqual(
            [
                r.augment_id
                for r in combine([CardRead(5, 0.9), CardRead(None, 0.3)], [CardRead(7, 0.8), CardRead(8, 0.8)])
            ],
            [5, 8],
        )

    def test_title_boxes_sit_inside_the_card_area(self):
        from sexo2.augments.ocr import title_boxes

        for size in ((1920, 1080), (1280, 1024), (3440, 1440)):
            area = card_area(*size)
            for left, top, right, bottom in title_boxes(*size):
                self.assertTrue(area[0] <= left < right <= area[2] and area[1] <= top < bottom <= area[3])


class WindowsOcrTests(unittest.TestCase):
    """Runs where the Windows OCR exists (the Windows CI); skipped elsewhere."""

    def test_titles_on_real_captures_are_read_and_named(self):
        from sexo2.augments import ocr

        reader = ocr.windows_reader()
        if reader is None:
            print(f"Windows OCR unavailable ({ocr.UNAVAILABLE_REASON})")
            self.skipTest(f"Windows OCR unavailable ({ocr.UNAVAILABLE_REASON})")
        read_titles = ocr.read_titles
        catalog = title_catalog()
        by_name = {a.name: a.id for a in catalog.augments}
        named = total = 0
        for name, titles in TITLES.items():
            reads = read_titles(capture(name), reader, catalog)
            for read, title in zip(reads, titles):
                total += 1
                if read.augment_id is not None:
                    self.assertEqual(read.augment_id, by_name[title], (name, title))  # never a wrong name
                    named += 1
        print(f"Windows OCR named {named} of {total} card titles")
        self.assertGreaterEqual(named, total * 0.8)


if __name__ == "__main__":
    unittest.main()
