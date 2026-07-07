"""Embodiment-control perturbation definitions.

All distances are dimensionless after normalization.  For scale-like fields,
the zero point is the nominal value of 1.0 and lower values are more severe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Iterable

import numpy as np


NUMERIC_DEFAULTS: dict[str, float] = {
    "latency_ms": 0.0,
    "action_noise_std": 0.0,
    "joint_range_scale": 1.0,
    "gripper_limit_scale": 1.0,
    "speed_cap_scale": 1.0,
    "acceleration_cap_scale": 1.0,
    "calibration_offset_mm": 0.0,
    "camera_shift_px": 0.0,
    "controller_rate_scale": 1.0,
    "payload_g": 0.0,
    "tool_extension_cm": 0.0,
    "physical_gripper_restriction_mm": 0.0,
    "obstacle_clearance_cm": 0.0,
}

TEXT_DEFAULTS: dict[str, str | None] = {
    "joint_lock": None,
    "friction_surface": None,
}

AXES: tuple[str, ...] = tuple(NUMERIC_DEFAULTS) + tuple(TEXT_DEFAULTS)

SEVERITY_SCALES: dict[str, float] = {
    "latency_ms": 240.0,
    "action_noise_std": 0.04,
    "joint_range_scale": 0.45,
    "joint_lock": 1.0,
    "gripper_limit_scale": 0.60,
    "speed_cap_scale": 0.70,
    "acceleration_cap_scale": 0.70,
    "calibration_offset_mm": 35.0,
    "camera_shift_px": 80.0,
    "controller_rate_scale": 0.75,
    "payload_g": 500.0,
    "tool_extension_cm": 20.0,
    "physical_gripper_restriction_mm": 20.0,
    "obstacle_clearance_cm": 10.0,
    "friction_surface": 1.0,
}

FRICTION_SEVERITY: dict[str | None, float] = {
    None: 0.0,
    "nominal": 0.0,
    "rubber": 0.15,
    "paper": 0.25,
    "low_friction": 0.70,
    "felt": 0.50,
    "incline": 0.85,
}


@dataclass(frozen=True)
class Perturbation:
    """Canonical perturbation with explicit nominal defaults."""

    values: dict[str, Any] = field(default_factory=dict)

    def canonical(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        out.update(NUMERIC_DEFAULTS)
        out.update(TEXT_DEFAULTS)
        out.update(self.values)
        return out

    def severity(self, axis: str) -> float:
        values = self.canonical()
        value = values.get(axis)
        if axis in {
            "joint_range_scale",
            "gripper_limit_scale",
            "speed_cap_scale",
            "acceleration_cap_scale",
            "controller_rate_scale",
        }:
            return max(0.0, 1.0 - float(value)) / SEVERITY_SCALES[axis]
        if axis == "joint_lock":
            return 0.0 if value in {None, "", "none"} else 1.0
        if axis == "friction_surface":
            return FRICTION_SEVERITY.get(value, 0.5)
        return abs(float(value)) / SEVERITY_SCALES.get(axis, 1.0)

    def severity_vector(self) -> dict[str, float]:
        return {axis: self.severity(axis) for axis in AXES}

    def active_axes(self, min_severity: float = 1e-9) -> list[str]:
        return [axis for axis, sev in self.severity_vector().items() if sev > min_severity]

    def cost(self, weights: dict[str, float] | None = None) -> float:
        weights = weights or {}
        total = 0.0
        for axis, sev in self.severity_vector().items():
            total += (weights.get(axis, 1.0) * sev) ** 2
        return float(total**0.5)

    def label(self) -> str:
        parts: list[str] = []
        for axis in self.active_axes():
            parts.append(f"{axis}={self.canonical()[axis]}")
        return "nominal" if not parts else ";".join(parts)


def make_perturbation(**kwargs: Any) -> Perturbation:
    return Perturbation(kwargs)


def nominal_perturbation() -> Perturbation:
    return Perturbation()


def axis_level_perturbations() -> list[tuple[str, str, Perturbation]]:
    """Representative one-axis perturbations used for profile plots."""

    levels: dict[str, list[tuple[str, Any]]] = {
        "latency_ms": [("low", 40), ("medium", 80), ("high", 160), ("extreme", 240)],
        "action_noise_std": [("low", 0.005), ("medium", 0.01), ("high", 0.02), ("extreme", 0.04)],
        "joint_range_scale": [("low", 0.85), ("medium", 0.70), ("high", 0.55)],
        "gripper_limit_scale": [("low", 0.80), ("medium", 0.60), ("high", 0.40)],
        "speed_cap_scale": [("low", 0.75), ("medium", 0.50), ("high", 0.30)],
        "acceleration_cap_scale": [("low", 0.75), ("medium", 0.50), ("high", 0.30)],
        "calibration_offset_mm": [("low", 5), ("medium", 10), ("high", 20), ("extreme", 35)],
        "camera_shift_px": [("medium", 40), ("high", 80)],
        "controller_rate_scale": [("low", 0.75), ("medium", 0.50), ("high", 0.25)],
        "payload_g": [("medium", 250), ("high", 500)],
        "tool_extension_cm": [("medium", 10), ("high", 20)],
        "physical_gripper_restriction_mm": [("medium", 10), ("high", 20)],
        "obstacle_clearance_cm": [("medium", 5), ("high", 10)],
        "friction_surface": [("medium", "felt"), ("high", "low_friction")],
    }
    out: list[tuple[str, str, Perturbation]] = [("nominal", "none", nominal_perturbation())]
    for axis, axis_levels in levels.items():
        for level, value in axis_levels:
            out.append((axis, level, Perturbation({axis: value})))
    return out


def heldout_perturbations() -> list[tuple[str, str, Perturbation]]:
    return [
        ("camera_shift_px", "heldout_medium", Perturbation({"camera_shift_px": 40})),
        ("payload_g", "heldout_medium", Perturbation({"payload_g": 250})),
        ("tool_extension_cm", "heldout_medium", Perturbation({"tool_extension_cm": 10})),
        ("physical_gripper_restriction_mm", "heldout_medium", Perturbation({"physical_gripper_restriction_mm": 10})),
        ("obstacle_clearance_cm", "heldout_medium", Perturbation({"obstacle_clearance_cm": 5})),
        ("friction_surface", "heldout_medium", Perturbation({"friction_surface": "felt"})),
        (
            "compound",
            "heldout_compound",
            Perturbation({"latency_ms": 80, "action_noise_std": 0.02, "calibration_offset_mm": 10}),
        ),
    ]


def candidate_grid(axes: Iterable[str] | None = None) -> list[Perturbation]:
    """Compact grid for search baselines and local refinement."""

    axis_values: dict[str, list[Any]] = {
        "latency_ms": [0, 40, 80, 120, 160, 240],
        "action_noise_std": [0, 0.005, 0.01, 0.02, 0.04],
        "joint_range_scale": [1.0, 0.85, 0.70, 0.55],
        "gripper_limit_scale": [1.0, 0.8, 0.6, 0.4],
        "speed_cap_scale": [1.0, 0.75, 0.5, 0.3],
        "acceleration_cap_scale": [1.0, 0.75, 0.5, 0.3],
        "calibration_offset_mm": [0, 5, 10, 20, 35],
        "camera_shift_px": [0, 40, 80],
        "controller_rate_scale": [1.0, 0.75, 0.5, 0.25],
        "payload_g": [0, 250, 500],
        "tool_extension_cm": [0, 10, 20],
        "physical_gripper_restriction_mm": [0, 10, 20],
        "obstacle_clearance_cm": [0, 5, 10],
        "friction_surface": [None, "felt", "low_friction"],
    }
    selected = list(axes or axis_values)
    out = [nominal_perturbation()]
    for axis in selected:
        for value in axis_values[axis]:
            out.append(Perturbation({axis: value}))
    for first, second in combinations(selected[:8], 2):
        first_values = axis_values[first][1:3]
        second_values = axis_values[second][1:3]
        for a in first_values:
            for b in second_values:
                out.append(Perturbation({first: a, second: b}))
    return dedupe_perturbations(out)


def random_candidates(rng: np.random.Generator, budget: int, axes: Iterable[str] | None = None) -> list[Perturbation]:
    axes = list(axes or NUMERIC_DEFAULTS)
    out: list[Perturbation] = []
    for _ in range(budget):
        n_axes = int(rng.choice([1, 1, 2, 2, 3]))
        active = list(rng.choice(axes, size=min(n_axes, len(axes)), replace=False))
        values: dict[str, Any] = {}
        for axis in active:
            sev = float(rng.beta(1.2, 2.0))
            if axis in {
                "joint_range_scale",
                "gripper_limit_scale",
                "speed_cap_scale",
                "acceleration_cap_scale",
                "controller_rate_scale",
            }:
                values[axis] = max(0.1, 1.0 - sev * SEVERITY_SCALES[axis])
            elif axis == "action_noise_std":
                values[axis] = sev * SEVERITY_SCALES[axis]
            elif axis == "latency_ms":
                values[axis] = round(sev * SEVERITY_SCALES[axis], 1)
            elif axis == "friction_surface":
                values[axis] = rng.choice(["paper", "felt", "low_friction"])
            else:
                values[axis] = round(sev * SEVERITY_SCALES.get(axis, 1.0), 3)
        out.append(Perturbation(values))
    return dedupe_perturbations(out)


def dedupe_perturbations(candidates: Iterable[Perturbation]) -> list[Perturbation]:
    seen: set[tuple[tuple[str, str], ...]] = set()
    out: list[Perturbation] = []
    for candidate in candidates:
        key = tuple(sorted((k, str(v)) for k, v in candidate.canonical().items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out
