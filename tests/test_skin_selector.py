"""Testes do skin_selector. Execute: python3 -m unittest test_skin_selector -v"""

import random
import unittest

from friends import skin_selector as selector


def skin(skin_id, rarity=None, name=None, **extra):
    data = {"skinId": skin_id, "name": name or str(skin_id)}
    if rarity is not None:
        data["rarity"] = rarity
    data.update(extra)
    return data


def chroma(chroma_id, base_skin_id, rarity=None, name=None, **extra):
    data = {
        "skinId": chroma_id,
        "name": name or str(chroma_id),
        "chroma": True,
        "baseSkinId": base_skin_id,
    }
    if rarity is not None:
        data["chromaRarity"] = rarity
    data.update(extra)
    return data


class FavoritePriorityTests(unittest.TestCase):
    def test_favorite_beats_highest_non_favorite(self):
        favorite = skin(11001, "kNoRarity")
        strongest_non_favorite = skin(99007, "kExalted")  # gacha + popular (99007)
        self.assertGreater(
            selector.skin_weight(favorite, favorite=True),
            selector.skin_weight(strongest_non_favorite),
        )

    def test_favorite_has_higher_probability_and_wins_more_often(self):
        skins = [
            skin(11001, "kNoRarity"),
            skin(11002, "kEpic"),
            skin(11003, "kLegendary"),
        ]
        favorites = {11002}
        probs = selector.probabilities(skins, favorites=favorites)
        self.assertEqual(len(probs), 3)
        self.assertGreater(probs[1], probs[0])
        self.assertGreater(probs[1], probs[2])

        rng = random.Random(1234)
        wins = {s["skinId"]: 0 for s in skins}
        for _ in range(4000):
            wins[selector.select_skin(skins, favorites=favorites, rng=rng)["skinId"]] += 1
        self.assertGreater(wins[11002], wins[11001])
        self.assertGreater(wins[11002], wins[11003])

    def test_favorite_still_not_exclusive(self):
        skins = [skin(11001, "kNoRarity"), skin(11002, "kNoRarity")]
        probs = selector.probabilities(skins, favorites={11001})
        self.assertLess(probs[1], probs[0])
        self.assertGreater(probs[1], 0.0)


class GachaHistoricEquivalenceTests(unittest.TestCase):
    def test_gacha_weight_equals_historic_weight(self):
        gacha = skin(25080, "kExalted")  # Exalted, fora da lista de populares
        historic = skin(4001, "kNoRarity")  # PAX Twisted Fate
        self.assertTrue(4001 in selector.HISTORIC_SKIN_IDS)
        self.assertEqual(selector.skin_weight(gacha), selector.skin_weight(historic))
        self.assertEqual(selector.skin_weight(gacha), selector.HISTORIC_WEIGHT)
        self.assertEqual(selector.skin_weight(gacha), selector.GACHA_WEIGHT)

    def test_transcendent_weight_equals_gacha(self):
        transcendent = skin(103085, "kTranscendent")  # Risen Legend Ahri
        gacha = skin(25080, "kExalted")  # Spirit Blossom Morgana (fora de populares)
        self.assertEqual(selector.skin_weight(transcendent), selector.skin_weight(gacha))
        self.assertEqual(selector.skin_weight(transcendent), selector.GACHA_WEIGHT)

    def test_all_required_historic_ids_present(self):
        required = {
            4001,
            24004,
            15005,
            12001,
            10001,
            13001,
            33001,
            10005,
            59004,
            27001,
            42001,
            53001,
        }
        self.assertTrue(required <= selector.HISTORIC_SKIN_IDS)


class RecentUseTests(unittest.TestCase):
    def test_recent_use_reduces_weight(self):
        s = skin(11001, "kEpic")
        self.assertLess(
            selector.skin_weight(s, recent_count=1),
            selector.skin_weight(s, recent_count=0),
        )

    def test_more_recent_uses_reduce_more(self):
        factors = [selector.recency_factor(n) for n in range(4)]
        self.assertEqual(factors, sorted(factors, reverse=True))

    def test_recent_list_lowers_probability(self):
        skins = [skin(11001, "kEpic"), skin(11002, "kEpic")]
        base = selector.probabilities(skins)
        with_recent = selector.probabilities(skins, recent=[11001])
        self.assertLess(with_recent[0], base[0])
        self.assertGreater(with_recent[1], base[1])

    def test_recent_chroma_is_decayed(self):
        skins = [skin(11000), chroma(11001, 11000, 1), chroma(11002, 11000, 1)]
        base = selector.probabilities(skins)
        with_recent = selector.probabilities(skins, recent=[11001])
        self.assertLess(with_recent[1], base[1])
        self.assertGreater(with_recent[2], base[2])


class RepetitionTests(unittest.TestCase):
    def test_recency_factor_never_reaches_zero(self):
        for count in range(0, 50):
            self.assertGreater(selector.recency_factor(count), 0.0)

    def test_recently_used_skin_can_still_be_picked(self):
        skins = [skin(11001, "kEpic"), skin(11002, "kEpic")]
        recent = [11001] * 20  # muito usada
        probs = selector.probabilities(skins, recent=recent)
        self.assertGreater(probs[0], 0.0)
        rng = random.Random(7)
        picked = {selector.select_skin(skins, recent=recent, rng=rng)["skinId"] for _ in range(2000)}
        self.assertIn(11001, picked)


class OverlappingCategoriesTests(unittest.TestCase):
    def test_gacha_and_historic_do_not_stack(self):
        both = skin(4001, "kExalted")  # gacha e histórica ao mesmo tempo
        self.assertEqual(selector.skin_weight(both), selector.HISTORIC_WEIGHT)
        self.assertNotEqual(selector.skin_weight(both), selector.GACHA_WEIGHT + selector.HISTORIC_WEIGHT)

    def test_favorite_and_gacha_are_additive_not_multiplicative(self):
        fav_gacha = skin(25080, "kExalted")  # Sahn-Uzal... na verdade Exalted
        weight = selector.skin_weight(fav_gacha, favorite=True)
        self.assertEqual(weight, selector.GACHA_WEIGHT + selector.FAVORITE_BONUS)

    def test_popularity_bonus_is_moderate(self):
        plain = skin(11001, "kLegendary")
        famous = skin(157002, "kLegendary")  # PROJECT: Yasuo
        self.assertEqual(
            selector.skin_weight(famous) - selector.skin_weight(plain),
            selector.POPULARITY_BONUS,
        )
        self.assertLess(selector.POPULARITY_BONUS, selector.FAVORITE_BONUS)


class ChromaTests(unittest.TestCase):
    def test_chroma_rarity_increases_weight(self):
        low = chroma(11002, 11001, rarity=0)
        high = chroma(11003, 11001, rarity=7)
        self.assertGreater(selector.skin_weight(high), selector.skin_weight(low))

    def test_missing_chroma_rarity_is_baseline(self):
        self.assertEqual(selector.chroma_rarity_factor(None), 1.0)
        self.assertEqual(selector.chroma_rarity_factor("lixo"), 1.0)

    def test_chroma_rarity_orders_within_family(self):
        skins = [skin(11001), chroma(11002, 11001, rarity=0), chroma(11003, 11001, rarity=7)]
        probs = selector.probabilities(skins)
        self.assertGreater(probs[2], probs[1])
        self.assertGreater(probs[1], 0.0)

    def test_chroma_can_be_selected(self):
        skins = [skin(11000), chroma(11001, 11000, rarity=1)]
        rng = random.Random(3)
        picked = {selector.select_skin(skins, rng=rng)["skinId"] for _ in range(2000)}
        self.assertIn(11000, picked)
        self.assertIn(11001, picked)

    def test_chroma_availability_is_respected(self):
        skins = [skin(11000), chroma(11001, 11000, rarity=1), chroma(11002, 11000, rarity=1)]
        available = lambda sid: sid != 11001  # noqa: E731
        probs = selector.probabilities(skins, available=available)
        self.assertEqual(probs[1], 0.0)
        self.assertGreater(probs[2], 0.0)
        # orçamento da família vai todo para o croma disponível
        self.assertAlmostEqual(probs[2], selector.CHROMA_FAMILY_SHARE / (1.0 + selector.CHROMA_FAMILY_SHARE))

        rng = random.Random(9)
        picked = {selector.select_skin(skins, available=available, rng=rng)["skinId"] for _ in range(1500)}
        self.assertNotIn(11001, picked)

    def test_all_chromas_unavailable_leaves_only_base(self):
        skins = [skin(11000), chroma(11001, 11000, rarity=3)]
        probs = selector.probabilities(skins, available=lambda sid: sid == 11000)
        self.assertEqual(probs[0], 1.0)
        self.assertEqual(probs[1], 0.0)

    def test_many_variants_do_not_dominate(self):
        # Skin A: 1 croma. Skin B: 10 cromas, mesma raridade.
        one = [skin(11000), chroma(11001, 11000, rarity=1)]
        many = [skin(12000)] + [chroma(12001 + i, 12000, rarity=1) for i in range(10)]
        skins = one + many

        probs = selector.probabilities(skins)
        # skin-base não muda de peso por ter mais ou menos variantes
        self.assertAlmostEqual(probs[0], probs[len(one)])
        # peso total das famílias de cromas é igual
        self.assertAlmostEqual(sum(probs[1 : len(one)]), sum(probs[len(one) + 1 :]))
        # cada variante individual da skin "poluída" é mais rara
        self.assertLess(probs[len(one) + 1], probs[1])

    def test_variant_count_does_not_change_base_probability(self):
        one = [skin(11000), chroma(11001, 11000, rarity=2)]
        many = [skin(11000)] + [chroma(11001 + i, 11000, rarity=2) for i in range(20)]
        self.assertAlmostEqual(selector.probabilities(one)[0], selector.probabilities(many)[0])

    def test_family_total_matches_share_for_singleton(self):
        skins = [skin(11000, "kEpic"), chroma(11001, 11000, rarity=0)]
        weights = selector.weights(skins)
        self.assertAlmostEqual(weights[1], selector.CHROMA_FAMILY_SHARE * selector.RARITY_WEIGHT["kEpic"])

    def test_chroma_without_base_uses_fallback(self):
        only = chroma(11001, 11000, rarity=0)
        self.assertAlmostEqual(
            selector.skin_weight(only),
            selector.CHROMA_FAMILY_SHARE * selector.CHROMA_FAMILY_FALLBACK,
        )

    def test_favorite_chroma_still_wins(self):
        skins = [skin(11000), chroma(11001, 11000, rarity=0), skin(99008, "kExalted")]
        probs = selector.probabilities(skins, favorites={11001})
        self.assertGreater(probs[1], probs[2])
        self.assertGreater(probs[1], probs[0])

    def test_seed_reproducibility_with_chromas(self):
        skins = [skin(11000), chroma(11001, 11000, rarity=4), chroma(11002, 11000, rarity=0)]

        def sequence(seed):
            rng = random.Random(seed)
            return [selector.select_skin(skins, rng=rng)["skinId"] for _ in range(40)]

        self.assertEqual(sequence(11), sequence(11))
        self.assertNotEqual(sequence(11), sequence(12))


class FormToggleChromaTests(unittest.TestCase):
    def test_affected_chroma_is_excluded(self):
        skins = [skin(99007, "kUltimate"), chroma(99008, 99007, rarity=5)]
        probs = selector.probabilities(skins)
        self.assertEqual(probs[1], 0.0)
        self.assertGreater(probs[0], 0.0)

    def test_exclusion_beats_favorite(self):
        favorite_chroma = chroma(99008, 99007, rarity=5, favorite=True)
        self.assertEqual(selector.skin_weight(favorite_chroma, favorite=True), 0.0)
        skins = [skin(99007, "kUltimate"), favorite_chroma]
        self.assertEqual(selector.probabilities(skins, favorites={99008})[1], 0.0)
        rng = random.Random(5)
        picked = {selector.select_skin(skins, favorites={99008}, rng=rng)["skinId"] for _ in range(1000)}
        self.assertNotIn(99008, picked)

    def test_unaffected_exalted_is_not_excluded(self):
        # Arcane Fractured Jinx é Exalted mas não está na lista: cromas seguem válidos.
        self.assertNotIn(222060, selector.FORM_TOGGLE_SKIN_IDS)
        skins = [skin(222060, "kExalted"), chroma(222061, 222060, rarity=0)]
        self.assertGreater(selector.probabilities(skins)[1], 0.0)

    def test_normal_skin_chroma_is_kept(self):
        skins = [skin(11000), chroma(11001, 11000, rarity=0)]
        self.assertGreater(selector.probabilities(skins)[1], 0.0)

    def test_all_form_toggle_ids_are_skins_not_chromas(self):
        self.assertTrue(all(type(sid) is int for sid in selector.FORM_TOGGLE_SKIN_IDS))


class SingleSkinTests(unittest.TestCase):
    def test_single_skin_is_returned(self):
        only = skin(11001, "kNoRarity")
        self.assertIs(selector.select_skin([only]), only)

    def test_single_skin_probability_is_one(self):
        self.assertEqual(selector.probabilities([skin(11001)]), [1.0])

    def test_single_chroma_is_returned(self):
        only = chroma(11001, 11000, rarity=3)
        self.assertIs(selector.select_skin([only]), only)
        self.assertEqual(selector.probabilities([only]), [1.0])

    def test_single_skin_with_favorite_and_recent(self):
        only = skin(4001, "kNoRarity")
        self.assertIs(
            selector.select_skin([only], favorites={4001}, recent=[4001] * 5),
            only,
        )

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            selector.select_skin([])


class SeedReproducibilityTests(unittest.TestCase):
    def setUp(self):
        self.skins = [
            skin(11001, "kNoRarity"),
            skin(11002, "kEpic"),
            skin(11003, "kMythic"),
            skin(4001, "kNoRarity"),
        ]

    def sequence(self, seed):
        rng = random.Random(seed)
        return [selector.select_skin(self.skins, favorites={11002}, rng=rng)["skinId"] for _ in range(50)]

    def test_same_seed_same_sequence(self):
        self.assertEqual(self.sequence(42), self.sequence(42))

    def test_different_seed_generally_differs(self):
        self.assertNotEqual(self.sequence(1), self.sequence(2))

    def test_selection_stays_within_candidates(self):
        valid = {s["skinId"] for s in self.skins}
        self.assertTrue(set(self.sequence(99)) <= valid)


class CategoryOrderingTests(unittest.TestCase):
    def test_progressive_ordering(self):
        base = selector.skin_weight(skin(11, "kNoRarity"))
        epic = selector.skin_weight(skin(12, "kEpic"))
        legendary = selector.skin_weight(skin(13, "kLegendary"))
        mythic = selector.skin_weight(skin(14, "kMythic"))
        gacha = selector.skin_weight(skin(15, "kExalted"))
        transcendent = selector.skin_weight(skin(16, "kTranscendent"))
        self.assertLess(base, epic)
        self.assertLess(epic, legendary)
        self.assertLess(legendary, mythic)
        self.assertLess(mythic, gacha)
        self.assertEqual(gacha, transcendent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
