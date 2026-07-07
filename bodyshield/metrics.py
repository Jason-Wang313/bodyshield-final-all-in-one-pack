"""Small metric helpers used by reports and tests."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from bodyshield.stats import bootstrap_mean_ci, wilson_interval


def success_rate(outcomes: Sequence[bool | int | float]) -> float:
    if not outcomes:
        return 0.0
    return float(np.mean([bool(value) for value in outcomes]))


def success_interval(successes: int, total: int) -> tuple[float, float]:
    return wilson_interval(successes, total)


def retention(repaired_success: float, nominal_success: float) -> float:
    return 0.0 if nominal_success <= 0 else float(repaired_success / nominal_success)


def mean_ci(values: Sequence[float], seed: int = 0) -> tuple[float, float]:
    return bootstrap_mean_ci(list(values), seed=seed)


__all__ = ["success_rate", "success_interval", "retention", "mean_ci"]
