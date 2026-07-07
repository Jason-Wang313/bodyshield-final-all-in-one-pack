"""Statistics helpers for BodyShield experiments."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def bootstrap_mean_ci(values: Iterable[float], n_boot: int = 1000, seed: int = 7) -> tuple[float, float]:
    arr = np.asarray(list(values), dtype=float)
    if len(arr) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = [rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(n_boot)]
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def profile_auc(costs: Iterable[float], rates: Iterable[float]) -> float:
    x = np.asarray(list(costs), dtype=float)
    y = np.asarray(list(rates), dtype=float)
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    if len(x) < 2 or float(x[-1]) == 0.0:
        return float(y.mean()) if len(y) else float("nan")
    return float(np.trapz(y, x) / x[-1])
