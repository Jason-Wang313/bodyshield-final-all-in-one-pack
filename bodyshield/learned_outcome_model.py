"""Lightweight learned outcome model for non-hardware BodyShield audits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .perturbations import AXES, Perturbation
from .policies import Policy
from .sim import ROBOTS, TASKS, RobotSpec, TaskSpec, evaluate_rate, stable_seed


@dataclass(frozen=True)
class OutcomeModelResult:
    metrics: pd.DataFrame
    axis_weights: pd.DataFrame
    predictions: pd.DataFrame


def _logit(p: float) -> float:
    p = min(0.995, max(0.005, p))
    return math.log(p / (1.0 - p))


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def _feature_names(policy_ids: list[str], task_ids: list[str], robot_ids: list[str]) -> list[str]:
    return (
        ["bias", "policy_base_success", "policy_nominal_penalty", "policy_time_scale", "task_difficulty", "robot_fragility"]
        + [f"policy={method_id}" for method_id in policy_ids]
        + [f"task={task_id}" for task_id in task_ids]
        + [f"robot={robot_id}" for robot_id in robot_ids]
        + [f"severity={axis}" for axis in AXES]
    )


def _features(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    policy_ids: list[str],
    task_ids: list[str],
    robot_ids: list[str],
) -> list[float]:
    severities = perturbation.severity_vector()
    return (
        [1.0, policy.base_success, policy.nominal_penalty, policy.time_scale, task.difficulty, robot.fragility]
        + [1.0 if policy.method_id == method_id else 0.0 for method_id in policy_ids]
        + [1.0 if task.task_id == task_id else 0.0 for task_id in task_ids]
        + [1.0 if robot.robot_id == robot_id else 0.0 for robot_id in robot_ids]
        + [severities[axis] for axis in AXES]
    )


def _auc(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=float)
    scores = np.asarray(scores, dtype=float)
    positives = int(labels.sum())
    negatives = int(len(labels) - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1, dtype=float)
    pos_rank_sum = float(ranks[labels == 1].sum())
    return float((pos_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives))


def _metrics(split: str, frame: pd.DataFrame) -> dict[str, Any]:
    y = frame["success_rate"].to_numpy(dtype=float)
    pred = np.clip(frame["predicted_success_rate"].to_numpy(dtype=float), 1e-4, 1.0 - 1e-4)
    labels = (y >= 0.5).astype(float)
    return {
        "split": split,
        "n_conditions": int(len(frame)),
        "mean_success_rate": float(y.mean()),
        "mean_predicted_success_rate": float(pred.mean()),
        "mae": float(np.mean(np.abs(pred - y))),
        "brier": float(np.mean((pred - y) ** 2)),
        "log_loss": float(-np.mean(y * np.log(pred) + (1.0 - y) * np.log(1.0 - pred))),
        "auc_at_50": _auc(labels, pred),
    }


def fit_learned_outcome_model(
    policies: dict[str, Policy],
    conditions: list[dict[str, Any]],
    n_trials: int = 80,
    ridge: float = 2.0,
) -> OutcomeModelResult:
    """Train a CPU ridge-logit outcome predictor and evaluate held-out buckets.

    This is deliberately lightweight: it is not a policy, and it is not a
    visual world model.  It checks whether the local artifact can learn a
    reusable action-outcome predictor over task, robot, policy, and
    perturbation features, then report where that predictor generalizes.
    """

    policy_ids = sorted(policies)
    task_ids = [task.task_id for task in TASKS]
    robot_ids = [robot.robot_id for robot in ROBOTS]
    names = _feature_names(policy_ids, task_ids, robot_ids)

    rows: list[dict[str, Any]] = []
    features: list[list[float]] = []
    targets: list[float] = []
    for method_id in policy_ids:
        policy = policies[method_id]
        for task in TASKS:
            for robot in ROBOTS:
                for condition in conditions:
                    perturbation = condition["perturbation"]
                    rate = evaluate_rate(
                        policy,
                        task,
                        robot,
                        perturbation,
                        n_trials=n_trials,
                        seed=stable_seed("learned-outcome", method_id, task.task_id, robot.robot_id, perturbation.label()),
                    )
                    features.append(_features(policy, task, robot, perturbation, policy_ids, task_ids, robot_ids))
                    targets.append(_logit(rate))
                    rows.append(
                        {
                            "method_id": method_id,
                            "task_id": task.task_id,
                            "robot_id": robot.robot_id,
                            "bucket": condition["bucket"],
                            "perturbation_family": condition["family"],
                            "perturbation_cost": perturbation.cost(),
                            "success_rate": rate,
                        }
                    )

    x = np.asarray(features, dtype=float)
    y = np.asarray(targets, dtype=float)
    train_mask = np.asarray([row["bucket"] in {"nominal", "seen"} for row in rows], dtype=bool)
    regularizer = ridge * np.eye(x.shape[1])
    regularizer[0, 0] = 0.0
    beta = np.linalg.solve(x[train_mask].T @ x[train_mask] + regularizer, x[train_mask].T @ y[train_mask])
    pred = _sigmoid(x @ beta)

    predictions = pd.DataFrame(rows)
    predictions["predicted_success_rate"] = pred
    predictions["absolute_error"] = (predictions["predicted_success_rate"] - predictions["success_rate"]).abs()
    predictions["split"] = np.where(train_mask, "train_seen_or_nominal", "heldout")

    metric_rows = [_metrics("all", predictions)]
    metric_rows.append(_metrics("train_seen_or_nominal", predictions[predictions["split"] == "train_seen_or_nominal"]))
    metric_rows.append(_metrics("heldout", predictions[predictions["split"] == "heldout"]))
    for bucket, group in predictions.groupby("bucket"):
        metric_rows.append(_metrics(f"bucket={bucket}", group))

    axis_rows = []
    coef = dict(zip(names, beta))
    for axis in AXES:
        axis_rows.append(
            {
                "axis": axis,
                "coefficient": float(coef.get(f"severity={axis}", 0.0)),
                "interpretation": "negative means predicted success decreases as severity increases",
            }
        )
    axis_weights = pd.DataFrame(axis_rows).sort_values("coefficient")
    return OutcomeModelResult(pd.DataFrame(metric_rows), axis_weights, predictions)
