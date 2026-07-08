"""Simulation package required by the v2 submission-grade layout."""

from __future__ import annotations

from bodyshield._legacy import load_legacy_module

_legacy = load_legacy_module("sim", "sim.py")

TaskSpec = _legacy.TaskSpec
RobotSpec = _legacy.RobotSpec
TASKS = _legacy.TASKS
ROBOTS = _legacy.ROBOTS
FAILURE_BY_AXIS = _legacy.FAILURE_BY_AXIS
stable_seed = _legacy.stable_seed
logit = _legacy.logit
sigmoid = _legacy.sigmoid
success_probability = _legacy.success_probability
dominant_failure_axis = _legacy.dominant_failure_axis
evaluate_rate = _legacy.evaluate_rate
trial_records = _legacy.trial_records

__all__ = [
    "TaskSpec",
    "RobotSpec",
    "TASKS",
    "ROBOTS",
    "FAILURE_BY_AXIS",
    "stable_seed",
    "logit",
    "sigmoid",
    "success_probability",
    "dominant_failure_axis",
    "evaluate_rate",
    "trial_records",
]

