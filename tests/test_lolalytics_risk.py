"""Offline contract tests for LoLalytics risk adjustment."""

import unittest

from lolalytics.errors import DataUnavailable, QueryError, SchemaError
from lolalytics.risk import (
    BUILD_PRIOR_GAMES,
    DEFAULT_RISK_LEVEL,
    RISK_LEVELS,
    rank_candidates,
    score_observation,
    validate_risk_level,
)


class RiskTests(unittest.TestCase):
    def test_levels_priors_and_validation(self):
        self.assertEqual(RISK_LEVELS, ("very-low", "low", "medium", "high", "very-high"))
        self.assertEqual(DEFAULT_RISK_LEVEL, "medium")
        self.assertEqual(list(BUILD_PRIOR_GAMES.values()), [3000, 2000, 1000, 750, 500])
        self.assertEqual(validate_risk_level("low"), "low")
        for invalid in (None, True, 1, "LOW", "unknown"):
            with self.subTest(invalid=invalid), self.assertRaises(QueryError):
                validate_risk_level(invalid)

    def test_more_conservative_prior_can_change_winner(self):
        candidates = [
            {"id": "spiky", "metrics": {"win_rate": 80.0, "games": 50}},
            {"id": "steady", "metrics": {"win_rate": 53.0, "games": 2000}},
        ]
        conservative = rank_candidates(candidates, 50, "very-low")
        aggressive = rank_candidates(candidates, 50, "very-high")
        self.assertEqual(conservative[0]["id"], "steady")
        self.assertEqual(aggressive[0]["id"], "spiky")
        self.assertEqual(candidates[0]["metrics"]["win_rate"], 80.0)

    def test_smoothing_formula_and_extreme_counts(self):
        result = score_observation(80, 50, 50, "medium")
        self.assertAlmostEqual(result["score"], (80 * 50 + 50 * 1000) / 1050)
        self.assertAlmostEqual(result["observed_weight"], 50 / 1050)
        huge = score_observation(80, 10**300, 50)
        self.assertAlmostEqual(huge["score"], 80)
        self.assertAlmostEqual(huge["observed_weight"], 1)

    def test_unavailable_winrate_games_and_zero_games(self):
        for wr in (None, "xx.xx"):
            with self.subTest(wr=wr):
                result = score_observation(wr, 10, 50)
                self.assertIsNone(result["score"])
                self.assertEqual(result["reason"], "missing_win_rate")
        result = score_observation(50, None, 50)
        self.assertIsNone(result["score"])
        self.assertEqual(result["reason"], "missing_games")
        result = score_observation(50, 0, 50)
        self.assertIsNone(result["score"])
        self.assertEqual(result["reason"], "no_games")

    def test_missing_baseline_is_unavailable(self):
        with self.assertRaises(DataUnavailable):
            score_observation(50, 10, None)
        with self.assertRaises(DataUnavailable):
            rank_candidates([], None)

    def test_rate_boundaries_and_invalid_shapes(self):
        self.assertEqual(score_observation(0, 10, 50)["score"] >= 0, True)
        self.assertEqual(score_observation(100, 10, 50)["score"] <= 100, True)
        for invalid in (True, "oops", "", " XX.XX ", float("nan"), float("inf"), 10**1000, -0.1, 100.1):
            with self.subTest(win_rate=invalid), self.assertRaises(SchemaError):
                score_observation(invalid, 10, 50)
        for invalid in (True, 1.5, "10", -1):
            with self.subTest(games=invalid), self.assertRaises(SchemaError):
                score_observation(50, invalid, 50)
        for invalid_baseline in (True, "50", float("nan"), float("inf"), 10**1000, -0.1, 100.1):
            with self.subTest(baseline=invalid_baseline), self.assertRaises(SchemaError):
                score_observation(50, 1, invalid_baseline)

    def test_rank_is_stable_for_ties_and_unavailable_last(self):
        rows = [
            {"id": "first", "metrics": {"win_rate": 60, "games": 10}},
            {"id": "more_games", "metrics": {"win_rate": 60, "games": 20}},
            {"id": "missing", "metrics": {"win_rate": None, "games": 900}},
        ]
        ranked = rank_candidates(rows, 50)
        self.assertEqual([r["id"] for r in ranked], ["more_games", "first", "missing"])
        self.assertIsNone(ranked[-1]["risk"]["score"])

    def test_equal_score_uses_games_then_stable_input_order(self):
        rows = [
            {"id": "same_a", "metrics": {"win_rate": 50, "games": 20}},
            {"id": "same_b", "metrics": {"win_rate": 50, "games": 20}},
            {"id": "more_games", "metrics": {"win_rate": 50, "games": 30}},
        ]
        ranked = rank_candidates(rows, 50)
        self.assertEqual([row["id"] for row in ranked], ["more_games", "same_a", "same_b"])

    def test_deep_copy_isolation_and_schema_checks(self):
        source = [{"id": "x", "metrics": {"win_rate": 51, "games": 100}, "extra": [1]}]
        ranked = rank_candidates(source, 50)
        ranked[0]["metrics"]["win_rate"] = -500
        ranked[0]["extra"].append(2)
        self.assertEqual(source[0]["metrics"]["win_rate"], 51)
        self.assertEqual(source[0]["extra"], [1])
        for bad in (None, {}, [{"metrics": []}], [{"metrics": {"games": 4}}]):
            with self.subTest(candidates=bad), self.assertRaises(SchemaError):
                rank_candidates(bad, 50)


if __name__ == "__main__":
    unittest.main()
