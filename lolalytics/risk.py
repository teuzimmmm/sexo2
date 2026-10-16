"""Local risk adjustment for LoLalytics win-rate observations.

Risk levels control the strength of a prior centered on the caller-provided
contextual baseline. This is a smoothing heuristic, not a confidence interval.
"""

from __future__ import annotations

from copy import deepcopy
import math
from numbers import Real
from typing import Any

from .errors import DataUnavailable, QueryError, SchemaError

RISK_LEVELS = ("very-low", "low", "medium", "high", "very-high")
DEFAULT_RISK_LEVEL = "medium"
BUILD_PRIOR_GAMES = {
    "very-low": 3000,
    "low": 2000,
    "medium": 1000,
    "high": 750,
    "very-high": 500,
}


def validate_risk_level(value: Any) -> str:
    """Return a supported risk level, rejecting implicit coercions."""
    if not isinstance(value, str) or value not in RISK_LEVELS:
        raise QueryError(
            f"risk_level must be one of: {', '.join(RISK_LEVELS)}"
        )
    return value


def _numeric(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise SchemaError(f"{label} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise SchemaError(f"{label} must be a finite number") from None
    if not math.isfinite(number):
        raise SchemaError(f"{label} must be a finite number")
    return number


def _optional_win_rate(value: Any) -> float | None:
    if value is None or value == "xx.xx":
        return None
    rate = _numeric(value, "win_rate")
    if rate < 0 or rate > 100:
        raise SchemaError("win_rate must be between 0 and 100")
    return rate


def _validated_baseline(value: Any) -> float:
    if value is None:
        raise DataUnavailable("baseline is unavailable")
    base = _numeric(value, "baseline")
    if base < 0 or base > 100:
        raise SchemaError("baseline must be between 0 and 100")
    return base


def _optional_games(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError("games must be a non-negative integer")
    if value < 0:
        raise SchemaError("games must be a non-negative integer")
    return value


def score_observation(
    win_rate: Any,
    games: Any,
    baseline: Any,
    risk_level: Any = DEFAULT_RISK_LEVEL,
) -> dict[str, Any]:
    """Shrink an observed percent win rate toward a contextual baseline."""
    level = validate_risk_level(risk_level)
    base = _validated_baseline(baseline)

    rate = _optional_win_rate(win_rate)
    count = _optional_games(games)
    prior = BUILD_PRIOR_GAMES[level]

    reason = None
    score = None
    weight = None
    if rate is None:
        reason = "missing_win_rate"
    elif count is None:
        reason = "missing_games"
    elif count == 0:
        reason = "no_games"
    else:
        # Weighted form avoids overflow in rate*games + baseline*prior.
        weight = count / (count + prior)
        score = rate * weight + base * (1.0 - weight)

    return {
        "score": score,
        "prior_games": prior,
        "observed_weight": weight,
        "reason": reason,
        "baseline": base,
        "risk_level": level,
    }


def rank_candidates(
    candidates: Any,
    baseline: Any,
    risk_level: Any = DEFAULT_RISK_LEVEL,
) -> list[dict[str, Any]]:
    """Copy candidates, attach their risk scores, and rank without mutation."""
    level = validate_risk_level(risk_level)
    # Validate baseline even when the input has no candidates.
    base = _validated_baseline(baseline)
    if not isinstance(candidates, list):
        raise SchemaError("candidates must be a list")

    ranked: list[tuple[int, dict[str, Any], float | None, int | None]] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise SchemaError("each candidate must be an object")
        metrics = candidate.get("metrics")
        if not isinstance(metrics, dict):
            raise SchemaError("each candidate must contain a metrics object")
        if "win_rate" not in metrics:
            raise SchemaError("candidate metrics must contain win_rate")
        if "games" not in metrics:
            raise SchemaError("candidate metrics must contain games")

        copied = deepcopy(candidate)
        score = score_observation(
            metrics["win_rate"], metrics["games"], base, level
        )
        copied["risk"] = score
        ranked.append((index, copied, score["score"], metrics["games"]))

    ranked.sort(
        key=lambda row: (
            row[2] is None,
            -(row[2] if row[2] is not None else 0.0),
            -(row[3] if row[3] is not None else 0),
            row[0],
        )
    )
    return [candidate for _, candidate, _, _ in ranked]
