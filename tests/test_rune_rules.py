"""Rune page rules judged against a representative styles payload."""

import copy
import json
import unittest
from pathlib import Path

from sexo2.services.rune_rules import PageSpec, StyleCatalog, StylesError, page_from_layout, validate_page

FIXTURE = Path(__file__).parent / "fixtures" / "lcu" / "perks-styles-representative.json"
STYLES = json.loads(FIXTURE.read_text())["styles"]

# Electrocute, Taste of Blood, Grisly Mementos, Ultimate Hunter | Manaflow Band, Transcendence | stat mods.
DOMINATION_SORCERY = PageSpec(8100, 8200, (8112, 8139, 8140, 8106, 8226, 8210, 5005, 5008, 5001))


def codes(spec, catalog):
    return [violation.code for violation in validate_page(spec, catalog)]


def with_perk(spec, position, perk):
    perks = list(spec.perk_ids)
    perks[position] = perk
    return PageSpec(spec.primary_style_id, spec.sub_style_id, tuple(perks))


class ValidatePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = StyleCatalog.from_payload(STYLES)

    def test_a_complete_page_is_valid(self):
        self.assertEqual(validate_page(DOMINATION_SORCERY, self.catalog), [])

    def test_keystone_must_come_from_the_primary_keystone_row(self):
        self.assertEqual(codes(with_perk(DOMINATION_SORCERY, 0, 8010), self.catalog), ["keystone_not_in_primary"])
        # A regular Domination perk is not a keystone either.
        self.assertEqual(codes(with_perk(DOMINATION_SORCERY, 0, 8126), self.catalog), ["keystone_not_in_primary"])

    def test_each_primary_row_takes_its_own_perk(self):
        swapped = with_perk(with_perk(DOMINATION_SORCERY, 1, 8140), 2, 8139)
        violations = validate_page(swapped, self.catalog)
        self.assertEqual(
            [(v.code, v.position) for v in violations], [("primary_row_mismatch", 1), ("primary_row_mismatch", 2)]
        )

    def test_sub_style_rules(self):
        same = PageSpec(8100, 8100, DOMINATION_SORCERY.perk_ids)
        self.assertEqual(codes(same, self.catalog), ["sub_style_same_as_primary"])
        unknown = PageSpec(8100, 9999, DOMINATION_SORCERY.perk_ids)
        self.assertEqual(codes(unknown, self.catalog), ["unknown_sub_style"])
        restricted = copy.deepcopy(STYLES)
        next(style for style in restricted if style["id"] == 8100)["allowedSubStyles"] = [8000]
        self.assertEqual(codes(DOMINATION_SORCERY, StyleCatalog.from_payload(restricted)), ["sub_style_not_allowed"])

    def test_secondary_perks_come_from_two_different_sub_style_rows(self):
        same_row = with_perk(DOMINATION_SORCERY, 5, 8224)  # 8226 and 8224 share a row
        self.assertEqual(codes(same_row, self.catalog), ["secondary_same_row"])
        keystone = with_perk(DOMINATION_SORCERY, 4, 8229)  # Arcane Comet is a keystone
        self.assertEqual(codes(keystone, self.catalog), ["secondary_not_in_sub_style"])
        other_tree = with_perk(DOMINATION_SORCERY, 4, 8444)
        self.assertEqual(codes(other_tree, self.catalog), ["secondary_not_in_sub_style"])

    def test_stat_mods_follow_their_row_order(self):
        self.assertEqual(codes(with_perk(DOMINATION_SORCERY, 6, 5011), self.catalog), ["stat_mod_row_mismatch"])
        self.assertEqual(codes(with_perk(DOMINATION_SORCERY, 8, 5007), self.catalog), ["stat_mod_row_mismatch"])
        # 5008 is valid in the first two rows only.
        self.assertEqual(codes(with_perk(DOMINATION_SORCERY, 6, 5008), self.catalog), [])

    def test_shape_errors(self):
        short = PageSpec(8100, 8200, DOMINATION_SORCERY.perk_ids[:8])
        self.assertEqual(codes(short, self.catalog), ["perk_count"])
        self.assertEqual(codes(PageSpec(1, 8200, DOMINATION_SORCERY.perk_ids), self.catalog), ["unknown_primary_style"])
        self.assertEqual(codes(with_perk(DOMINATION_SORCERY, 3, True), self.catalog), ["perk_not_integer"])

    def test_malformed_styles_payload_is_an_error(self):
        for payload in ({}, [], [{"id": 1}], [{"id": "8100", "slots": [], "allowedSubStyles": []}]):
            with self.subTest(payload=payload), self.assertRaises(StylesError):
                StyleCatalog.from_payload(payload)


class PageFromLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = StyleCatalog.from_payload(STYLES)

    def test_lolalytics_layouts_from_fixtures_become_valid_pages(self):
        # Layouts read from tests/fixtures/lolalytics/keystone/ahri-ranked-base.json.
        pick = page_from_layout(
            self.catalog, ["8112", "8139", "8140", "8106"], ["8226", "8210"], ["5005", "5008", "5001"]
        )
        self.assertEqual(pick, DOMINATION_SORCERY)
        win = page_from_layout(
            self.catalog, ["8992", "8226", "8210", "8237"], ["8451", "8444"], ["5008", "5010", "5011"]
        )
        self.assertEqual((win.primary_style_id, win.sub_style_id), (8200, 8400))
        self.assertEqual(validate_page(win, self.catalog), [])

    def test_unknown_or_ambiguous_layout_is_an_error(self):
        with self.assertRaises(StylesError):
            page_from_layout(self.catalog, [1, 2, 3, 4], [8226, 8210], [5005, 5008, 5001])
        with self.assertRaises(StylesError):
            page_from_layout(self.catalog, [8112, 8139, 8140, 8106], [8226, 8444], [5005, 5008, 5001])
        with self.assertRaises(StylesError):
            page_from_layout(self.catalog, ["x"], [], [])


if __name__ == "__main__":
    unittest.main()
