"""Small simulation runner helpers."""

from __future__ import annotations

from bodyshield.perturbations import Perturbation
from bodyshield.policies import Policy
from bodyshield.sim import RobotSpec, TaskSpec, evaluate_rate, trial_records


def run_condition(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    n_trials: int = 50,
    seed: int | None = None,
) -> dict[str, object]:
    return {
        "success_rate": evaluate_rate(policy, task, robot, perturbation, n_trials=n_trials, seed=seed),
        "records": trial_records(policy, task, robot, perturbation, n_trials=n_trials, seed=seed),
    }


__all__ = ["run_condition"]

