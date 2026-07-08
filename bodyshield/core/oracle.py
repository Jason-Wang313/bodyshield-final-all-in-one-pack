"""Oracle-feasibility helpers for BodyShield reports."""

from __future__ import annotations

from bodyshield.perturbations import Perturbation
from bodyshield.policies import default_policies
from bodyshield.sim import ROBOTS, TASKS, success_probability


def oracle_success_rate(task_id: str, robot_id: str, perturbation: Perturbation) -> float:
    tasks = {task.task_id: task for task in TASKS}
    robots = {robot.robot_id: robot for robot in ROBOTS}
    oracle = default_policies()["oracle"]
    return success_probability(oracle, tasks[task_id], robots[robot_id], perturbation)


def is_oracle_feasible(task_id: str, robot_id: str, perturbation: Perturbation, threshold: float = 0.70) -> bool:
    return oracle_success_rate(task_id, robot_id, perturbation) >= threshold


__all__ = ["oracle_success_rate", "is_oracle_feasible"]

