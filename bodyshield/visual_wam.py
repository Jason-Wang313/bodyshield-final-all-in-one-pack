"""Synthetic visual WAM proxy for BodyShield non-hardware audits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .perturbations import AXES, Perturbation
from .policies import Policy
from .sim import ROBOTS, TASKS, RobotSpec, TaskSpec
from .trajectory_wam import _unit_from_seed, generate_synthetic_trajectory


@dataclass(frozen=True)
class VisualWAMResult:
    metrics: pd.DataFrame
    rollouts: pd.DataFrame
    feature_weights: pd.DataFrame
    trace_sample: list[dict[str, Any]]


def _world_grid(frame_size: int) -> tuple[np.ndarray, np.ndarray]:
    axis = np.linspace(-1.45, 1.45, frame_size, dtype=float)
    return np.meshgrid(axis, axis)


def _gaussian_channel(x_grid: np.ndarray, y_grid: np.ndarray, center: np.ndarray, sigma: float) -> np.ndarray:
    dist2 = (x_grid - center[0]) ** 2 + (y_grid - center[1]) ** 2
    channel = np.exp(-0.5 * dist2 / max(sigma * sigma, 1e-6))
    peak = float(channel.max())
    return channel / peak if peak > 0 else channel


def render_synthetic_visual_frame(
    state: np.ndarray,
    target: np.ndarray,
    task: TaskSpec,
    perturbation: Perturbation,
    frame_size: int = 12,
) -> np.ndarray:
    """Render a tiny two-channel synthetic observation.

    Channel 0 is the object/end-effector proxy and channel 1 is the target.
    This is a generated pixel audit, not real camera data.
    """

    x_grid, y_grid = _world_grid(frame_size)
    camera_shift = 0.10 * perturbation.severity("camera_shift_px") * _unit_from_seed("visual-camera", task.task_id)
    object_center = state[:2] + camera_shift
    target_center = target + 0.35 * camera_shift
    object_sigma = 0.105 + 0.035 * perturbation.severity("action_noise_std")
    target_sigma = 0.090
    object_channel = _gaussian_channel(x_grid, y_grid, object_center, object_sigma)
    target_channel = 0.70 * _gaussian_channel(x_grid, y_grid, target_center, target_sigma)
    obstacle = perturbation.severity("obstacle_clearance_cm")
    if obstacle > 0:
        obstacle_dir = _unit_from_seed("visual-obstacle", task.task_id)
        obstacle_center = 0.5 * (object_center + target_center) + 0.22 * obstacle_dir
        target_channel = np.maximum(target_channel, 0.35 * obstacle * _gaussian_channel(x_grid, y_grid, obstacle_center, 0.16))
    frame = np.stack([object_channel, target_channel], axis=0)
    return np.clip(frame, 0.0, 1.0)


def _centroid_from_frame(frame: np.ndarray) -> np.ndarray:
    object_channel = np.clip(frame[0], 0.0, None)
    mass = float(object_channel.sum())
    if mass <= 1e-9:
        return np.asarray([0.0, 0.0], dtype=float)
    x_grid, y_grid = _world_grid(object_channel.shape[0])
    return np.asarray(
        [
            float((object_channel * x_grid).sum() / mass),
            float((object_channel * y_grid).sum() / mass),
        ],
        dtype=float,
    )


def _feature_names(policy_ids: list[str], task_ids: list[str], robot_ids: list[str], frame_pixels: int) -> list[str]:
    return (
        [f"pixel_{idx}" for idx in range(frame_pixels)]
        + [
            "action_x",
            "action_y",
            "action_norm",
            "step_fraction",
            "policy_base_success",
            "policy_nominal_penalty",
            "policy_time_scale",
            "task_difficulty",
            "robot_fragility",
        ]
        + [f"policy={method_id}" for method_id in policy_ids]
        + [f"task={task_id}" for task_id in task_ids]
        + [f"robot={robot_id}" for robot_id in robot_ids]
        + [f"severity={axis}" for axis in AXES]
    )


def _features(
    frame: np.ndarray,
    action: np.ndarray,
    step_index: int,
    steps: int,
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
        frame.reshape(-1).astype(float).tolist()
        + [
            float(action[0]),
            float(action[1]),
            float(np.linalg.norm(action)),
            step_index / max(1, steps - 1),
            policy.base_success,
            policy.nominal_penalty,
            policy.time_scale,
            task.difficulty,
            robot.fragility,
        ]
        + [1.0 if policy.method_id == method_id else 0.0 for method_id in policy_ids]
        + [1.0 if task.task_id == task_id else 0.0 for task_id in task_ids]
        + [1.0 if robot.robot_id == robot_id else 0.0 for robot_id in robot_ids]
        + [severities[axis] for axis in AXES]
    )


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a - b) ** 2))


def _psnr(mse: float) -> float:
    return float(10.0 * math.log10(1.0 / max(mse, 1e-9)))


def _metrics(label: str, transition_frame: pd.DataFrame, rollouts: pd.DataFrame) -> dict[str, Any]:
    return {
        "slice": label,
        "n_transitions": int(len(transition_frame)),
        "n_rollouts": int(len(rollouts)),
        "transition_frame_mse": float(transition_frame["frame_mse"].mean()),
        "transition_psnr_db": _psnr(float(transition_frame["frame_mse"].mean())),
        "transition_centroid_error": float(transition_frame["centroid_error"].mean()),
        "final_frame_mse": float(rollouts["final_frame_mse"].mean()),
        "final_psnr_db": _psnr(float(rollouts["final_frame_mse"].mean())),
        "final_centroid_error": float(rollouts["final_centroid_error"].mean()),
    }


def fit_visual_wam_proxy(
    policies: dict[str, Policy],
    conditions: list[dict[str, Any]],
    source_method_ids: tuple[str, ...] = ("nominal", "domain_randomization", "bodyshield"),
    steps: int = 14,
    frame_size: int = 12,
    ridge: float = 8.0,
    trace_sample_limit: int = 36,
) -> VisualWAMResult:
    """Fit a CPU ridge predictor over synthetic visual frames."""

    source_methods = [method_id for method_id in source_method_ids if method_id in policies]
    if not source_methods:
        raise ValueError("fit_visual_wam_proxy requires at least one source policy")
    policy_ids = sorted(source_methods)
    task_ids = [task.task_id for task in TASKS]
    robot_ids = [robot.robot_id for robot in ROBOTS]

    x_rows: list[list[float]] = []
    y_rows: list[np.ndarray] = []
    transition_meta: list[dict[str, Any]] = []
    rollout_specs: list[dict[str, Any]] = []

    for method_id in policy_ids:
        policy = policies[method_id]
        for task in TASKS:
            for robot in ROBOTS:
                for condition in conditions:
                    perturbation = condition["perturbation"]
                    trajectory = generate_synthetic_trajectory(policy, task, robot, perturbation, steps=steps)
                    frames = [
                        render_synthetic_visual_frame(state, trajectory["target"], task, perturbation, frame_size=frame_size)
                        for state in trajectory["states"]
                    ]
                    rollout_specs.append(
                        {
                            "method_id": method_id,
                            "task": task,
                            "robot": robot,
                            "condition": condition,
                            "trajectory": trajectory,
                            "frames": frames,
                        }
                    )
                    split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
                    for step in range(steps):
                        x_rows.append(
                            _features(
                                frames[step],
                                trajectory["actions"][step],
                                step,
                                steps,
                                policy,
                                task,
                                robot,
                                perturbation,
                                policy_ids,
                                task_ids,
                                robot_ids,
                            )
                        )
                        y_rows.append(frames[step + 1].reshape(-1))
                        transition_meta.append(
                            {
                                "method_id": method_id,
                                "task_id": task.task_id,
                                "robot_id": robot.robot_id,
                                "bucket": condition["bucket"],
                                "perturbation_family": condition["family"],
                                "split": split,
                                "true_next_frame": frames[step + 1],
                            }
                        )

    x = np.asarray(x_rows, dtype=float)
    y = np.asarray(y_rows, dtype=float)
    train_mask = np.asarray([row["split"] == "train_seen_or_nominal" for row in transition_meta], dtype=bool)
    regularizer = ridge * np.eye(x.shape[1])
    beta = np.linalg.solve(x[train_mask].T @ x[train_mask] + regularizer, x[train_mask].T @ y[train_mask])
    pred_next = np.clip(x @ beta, 0.0, 1.0)

    transition_rows: list[dict[str, Any]] = []
    for index, meta in enumerate(transition_meta):
        true_frame = meta.pop("true_next_frame")
        pred_frame = pred_next[index].reshape(2, frame_size, frame_size)
        transition_rows.append(
            {
                **meta,
                "frame_mse": _mse(pred_frame, true_frame),
                "centroid_error": float(np.linalg.norm(_centroid_from_frame(pred_frame) - _centroid_from_frame(true_frame))),
            }
        )
    transitions = pd.DataFrame(transition_rows)

    rollout_rows: list[dict[str, Any]] = []
    trace_sample: list[dict[str, Any]] = []
    for spec in rollout_specs:
        method_id = spec["method_id"]
        policy = policies[method_id]
        task = spec["task"]
        robot = spec["robot"]
        condition = spec["condition"]
        perturbation = condition["perturbation"]
        trajectory = spec["trajectory"]
        true_frames = spec["frames"]
        pred_frame = true_frames[0].copy()
        for step in range(steps):
            features = np.asarray(
                _features(
                    pred_frame,
                    trajectory["actions"][step],
                    step,
                    steps,
                    policy,
                    task,
                    robot,
                    perturbation,
                    policy_ids,
                    task_ids,
                    robot_ids,
                ),
                dtype=float,
            )
            pred_frame = np.clip((features @ beta).reshape(2, frame_size, frame_size), 0.0, 1.0)
        true_final = true_frames[-1]
        true_centroid = _centroid_from_frame(true_final)
        pred_centroid = _centroid_from_frame(pred_frame)
        split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
        rollout_rows.append(
            {
                "method_id": method_id,
                "task_id": task.task_id,
                "robot_id": robot.robot_id,
                "bucket": condition["bucket"],
                "perturbation_family": condition["family"],
                "split": split,
                "final_frame_mse": _mse(pred_frame, true_final),
                "final_centroid_error": float(np.linalg.norm(pred_centroid - true_centroid)),
                "true_final_x": float(true_centroid[0]),
                "true_final_y": float(true_centroid[1]),
                "pred_final_x": float(pred_centroid[0]),
                "pred_final_y": float(pred_centroid[1]),
            }
        )
        if len(trace_sample) < trace_sample_limit and condition["bucket"] == "heldout" and method_id in {"nominal", "bodyshield"}:
            trace_sample.append(
                {
                    "method_id": method_id,
                    "task_id": task.task_id,
                    "robot_id": robot.robot_id,
                    "bucket": condition["bucket"],
                    "perturbation_family": condition["family"],
                    "perturbation": perturbation.label(),
                    "true_final_centroid_xy": [round(float(value), 5) for value in true_centroid],
                    "pred_final_centroid_xy": [round(float(value), 5) for value in pred_centroid],
                    "final_frame_mse": round(_mse(pred_frame, true_final), 8),
                    "true_start_frame": np.round(true_frames[0], 4).tolist(),
                    "true_final_frame": np.round(true_final, 4).tolist(),
                    "pred_final_frame": np.round(pred_frame, 4).tolist(),
                    "notes": "Synthetic rendered visual WAM trace; not real video or camera data.",
                }
            )

    rollouts = pd.DataFrame(rollout_rows)
    metric_rows = [_metrics("all", transitions, rollouts)]
    for split, group in transitions.groupby("split"):
        metric_rows.append(_metrics(f"split={split}", group, rollouts[rollouts["split"] == split]))
    for bucket, group in transitions.groupby("bucket"):
        metric_rows.append(_metrics(f"bucket={bucket}", group, rollouts[rollouts["bucket"] == bucket]))
    for method_id, group in transitions.groupby("method_id"):
        metric_rows.append(_metrics(f"method={method_id}", group, rollouts[rollouts["method_id"] == method_id]))
    metrics = pd.DataFrame(metric_rows)

    names = _feature_names(policy_ids, task_ids, robot_ids, frame_pixels=2 * frame_size * frame_size)
    weight_rows = []
    for name, values in zip(names, beta):
        weight_rows.append(
            {
                "feature": name,
                "weight_l2": float(np.linalg.norm(values)),
                "mean_abs_weight": float(np.mean(np.abs(values))),
            }
        )
    feature_weights = pd.DataFrame(weight_rows).sort_values("weight_l2", ascending=False)
    return VisualWAMResult(metrics, rollouts, feature_weights, trace_sample)
