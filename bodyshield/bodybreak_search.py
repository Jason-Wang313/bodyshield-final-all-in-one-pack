"""BodyBreak adversarial embodiment-control perturbation search."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from itertools import combinations
from typing import Callable

import numpy as np

from .perturbations import Perturbation, candidate_grid, random_candidates


@dataclass(frozen=True)
class SearchResult:
    perturbation: Perturbation
    cost: float
    success_rate: float
    trials: int
    notes: str


Evaluator = Callable[[Perturbation], float]
CHALLENGE_POOL_MIN = 256
CHALLENGE_POOL_MULTIPLIER = 8


def perturbation_cost(z: Perturbation, scales: dict[str, float] | None = None) -> float:
    return z.cost(scales)


def _best_break(candidates: list[Perturbation], evaluator: Evaluator, threshold: float, budget: int) -> SearchResult:
    best_break: tuple[float, Perturbation, float] | None = None
    best_any: tuple[float, Perturbation, float] | None = None
    trials = 0
    for perturbation in sorted(candidates, key=lambda z: z.cost())[:budget]:
        rate = evaluator(perturbation)
        trials += 1
        cost = perturbation.cost()
        if best_any is None or rate < best_any[2] or (rate == best_any[2] and cost < best_any[0]):
            best_any = (cost, perturbation, rate)
        if rate <= threshold and (best_break is None or cost < best_break[0]):
            best_break = (cost, perturbation, rate)
    chosen = best_break or best_any
    assert chosen is not None
    note = "found_break" if best_break else "no_break_found_returned_lowest_success"
    return SearchResult(chosen[1], chosen[0], chosen[2], trials, note)


def _scale_toward_nominal(z: Perturbation, factor: float) -> Perturbation:
    values = {}
    for axis in z.active_axes():
        value = z.canonical()[axis]
        if axis in {"joint_range_scale", "gripper_limit_scale", "speed_cap_scale", "acceleration_cap_scale", "controller_rate_scale"}:
            values[axis] = 1.0 - (1.0 - float(value)) * factor
        elif axis in {"joint_lock", "friction_surface"}:
            values[axis] = value if factor >= 0.50 else None
        else:
            values[axis] = float(value) * factor
    return Perturbation(values)


def _local_refinement_seeds(z: Perturbation) -> list[Perturbation]:
    axes = z.active_axes()
    values = z.canonical()
    seeds = [z]
    max_subset_size = min(2, len(axes))
    for size in range(1, max_subset_size + 1):
        for subset in combinations(axes, size):
            seeds.append(Perturbation({axis: values[axis] for axis in subset}))
    seen: set[str] = set()
    out: list[Perturbation] = []
    for seed in sorted(seeds, key=lambda candidate: candidate.cost()):
        label = seed.label()
        if label in seen:
            continue
        seen.add(label)
        out.append(seed)
    return out


def find_minimal_breaking_perturbation(
    policy,
    task,
    evaluator,
    search_space: list[Perturbation] | None = None,
    threshold: float = 0.50,
    budget: int = 80,
    mode: str = "bodybreak",
    seed: int = 0,
) -> SearchResult:
    """Estimate the lowest-cost perturbation that drops success under threshold.

    The evaluator is intentionally injected so the same algorithm can be used
    against analytic simulation, high-fidelity simulation, or hardware logs.
    """

    rng = np.random.default_rng(seed)
    if mode == "grid":
        return _best_break(search_space or candidate_grid(), evaluator, threshold, budget)
    if mode == "random":
        return _best_break(random_candidates(rng, budget), evaluator, threshold, budget)
    if mode == "one_axis":
        one_axis = [z for z in candidate_grid() if len(z.active_axes()) <= 1]
        return _best_break(one_axis, evaluator, threshold, budget)
    if mode != "bodybreak":
        raise ValueError(f"unknown search mode: {mode}")

    cache: dict[str, float] = {}
    calls = 0

    def cached_eval(z: Perturbation) -> float:
        nonlocal calls
        key = z.label()
        if key not in cache:
            if calls >= budget:
                return cache.get(key, 1.0)
            cache[key] = evaluator(z)
            calls += 1
        return cache[key]

    grid = candidate_grid()
    best_break: tuple[float, Perturbation, float] | None = None
    best_any: tuple[float, Perturbation, float] | None = None
    for perturbation in sorted(grid, key=lambda z: z.cost()):
        if calls >= budget:
            break
        rate = cached_eval(perturbation)
        cost = perturbation.cost()
        if best_any is None or rate < best_any[2] or (rate == best_any[2] and cost < best_any[0]):
            best_any = (cost, perturbation, rate)
        if rate <= threshold and (best_break is None or cost < best_break[0]):
            best_break = (cost, perturbation, rate)
            break

    if best_break is None and calls < budget:
        random_pool = random_candidates(rng, budget - calls)
        for perturbation in sorted(random_pool, key=lambda z: z.cost()):
            if calls >= budget:
                break
            rate = cached_eval(perturbation)
            cost = perturbation.cost()
            if best_any is None or rate < best_any[2] or (rate == best_any[2] and cost < best_any[0]):
                best_any = (cost, perturbation, rate)
            if rate <= threshold and (best_break is None or cost < best_break[0]):
                best_break = (cost, perturbation, rate)
                break
    chosen = best_break or best_any
    assert chosen is not None
    if best_break is not None:
        refined = best_break

        def try_refine(seed_perturbation: Perturbation) -> None:
            nonlocal refined
            if calls >= budget or not seed_perturbation.active_axes():
                return
            seed_rate = cached_eval(seed_perturbation)
            if seed_rate > threshold:
                return
            seed_cost = seed_perturbation.cost()
            if seed_cost < refined[0]:
                refined = (seed_cost, seed_perturbation, seed_rate)
            low = 0.0
            high = 1.0
            for _ in range(12):
                if calls >= budget:
                    break
                mid = (low + high) / 2.0
                probe = _scale_toward_nominal(seed_perturbation, mid)
                if not probe.active_axes():
                    low = mid
                    continue
                rate = cached_eval(probe)
                cost = probe.cost()
                if rate <= threshold:
                    if cost < refined[0]:
                        refined = (cost, probe, rate)
                    high = mid
                else:
                    low = mid

        for seed_perturbation in _local_refinement_seeds(best_break[1]):
            try_refine(seed_perturbation)
            if calls >= budget:
                break
        if calls < budget:
            remaining = budget - calls
            challenge_count = max(CHALLENGE_POOL_MIN, CHALLENGE_POOL_MULTIPLIER * remaining)
            challenge_pool = random_candidates(rng, challenge_count)
            for salt in [104729, 130363, 155921]:
                challenge_pool.extend(random_candidates(np.random.default_rng((int(seed) + salt) % (2**32)), challenge_count // 2))
            lower_cost_pool = [perturbation for perturbation in challenge_pool if perturbation.cost() < refined[0]]
            budget_reachable = heapq.nsmallest(
                remaining,
                lower_cost_pool,
                key=lambda z: (z.cost(), z.label()),
            )
            for perturbation in budget_reachable:
                if calls >= budget:
                    break
                rate = cached_eval(perturbation)
                if rate <= threshold:
                    refined = (perturbation.cost(), perturbation, rate)
                    try_refine(perturbation)
        chosen = refined
    note = "found_break" if best_break else "no_break_found_returned_lowest_success"
    return SearchResult(chosen[1], chosen[0], chosen[2], calls, note)


def compare_search_modes(evaluator: Evaluator, threshold: float, seed: int = 0, budget: int = 80) -> dict[str, SearchResult]:
    return {
        mode: find_minimal_breaking_perturbation(
            policy=None,
            task=None,
            evaluator=evaluator,
            threshold=threshold,
            budget=budget,
            mode=mode,
            seed=seed,
        )
        for mode in ["random", "one_axis", "grid", "bodybreak"]
    }
