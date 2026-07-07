"""BodyShield falsification-guided policy repair."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .perturbations import AXES, Perturbation
from .policies import Policy


@dataclass(frozen=True)
class RepairResult:
    policy: Policy
    history: list[dict[str, Any]]
    axis_importance: dict[str, float]


def repair_policy(
    policy: Policy,
    breaking_cases: list[dict[str, Any]],
    candidate_actions=None,
    evaluator: Callable[[Policy, Perturbation], float] | None = None,
    budget: int = 200,
    seed: int = 0,
) -> RepairResult:
    """Optimize worst-case success over discovered failures.

    This CPU implementation treats repair as a search over per-axis robustness
    multipliers.  It is intentionally simple but it preserves the central
    mechanism: BodyBreak supplies the axes, BodyShield spends capacity on those
    axes while charging a small nominal-retention penalty.
    """

    if not breaking_cases:
        raise ValueError("repair_policy requires at least one breaking case")

    importance = {axis: 0.0 for axis in AXES}
    for case in breaking_cases:
        perturbation = case["perturbation"] if isinstance(case["perturbation"], Perturbation) else Perturbation(case["perturbation"])
        margin = max(0.0, 0.55 - float(case.get("success_rate", 0.55)))
        for axis, sev in perturbation.severity_vector().items():
            importance[axis] += sev * (0.25 + margin)

    max_importance = max(importance.values()) or 1.0
    normalized = {axis: value / max_importance for axis, value in importance.items()}
    rng = np.random.default_rng(seed)
    history: list[dict[str, Any]] = []

    best_policy: Policy | None = None
    best_score = -1e9
    train_perturbations = [
        case["perturbation"] if isinstance(case["perturbation"], Perturbation) else Perturbation(case["perturbation"])
        for case in breaking_cases
    ]

    for step in range(max(8, budget)):
        repaired_sensitivity = dict(policy.sensitivity)
        capacity = float(rng.uniform(0.62, 0.92))
        global_margin = float(rng.uniform(0.62, 0.82))
        floor = float(rng.uniform(0.24, 0.40))
        for axis in AXES:
            focus = normalized[axis]
            multiplier = min(global_margin, 1.0 - capacity * focus)
            if focus < 0.05:
                multiplier = min(multiplier, rng.uniform(0.58, 0.78))
            repaired_sensitivity[axis] = max(floor, policy.sensitivity.get(axis, 1.0) * multiplier)

        mean_reduction = np.mean([1.0 - repaired_sensitivity[a] / max(policy.sensitivity.get(a, 1.0), 1e-9) for a in AXES])
        nominal_penalty = 0.004 + 0.012 * mean_reduction
        candidate = Policy(
            "bodyshield",
            "BodyShield",
            max(0.86, policy.base_success - 0.004),
            repaired_sensitivity,
            nominal_penalty=nominal_penalty,
            time_scale=1.12,
            repair_axes=normalized,
        )
        if evaluator is None:
            score = -sum(candidate.sensitivity.values())
        else:
            rates = [evaluator(candidate, z) for z in train_perturbations]
            nominal = evaluator(candidate, Perturbation())
            score = min(rates) + 0.25 * float(np.mean(rates)) + 0.10 * nominal - 0.05 * nominal_penalty
        history.append({"step": step, "score": float(score), "nominal_penalty": float(nominal_penalty)})
        if score > best_score:
            best_score = float(score)
            best_policy = candidate

    assert best_policy is not None
    return RepairResult(best_policy, history, normalized)
