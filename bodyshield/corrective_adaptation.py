"""Synthetic corrective-trace adaptation audit for BodyShield."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .perturbations import AXES, Perturbation
from .policies import Policy
from .sim import ROBOTS, TASKS, RobotSpec, TaskSpec, stable_seed
from .trajectory_wam import _severity_features, _target, _trajectory_action, _unit_from_seed


@dataclass(frozen=True)
class CorrectiveAdaptationResult:
    metrics: pd.DataFrame
    rollouts: pd.DataFrame
    residual_weights: pd.DataFrame
    trace_sample: list[dict[str, Any]]


def _correction_features(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    state: np.ndarray,
    base_action: np.ndarray,
    step_index: int,
    steps: int,
    policy_ids: list[str],
    task_ids: list[str],
    robot_ids: list[str],
) -> list[float]:
    target = _target(task)
    severities, severity_l1, severity_l2, weighted_stress = _severity_features(task, robot, policy, perturbation)
    distance = float(np.linalg.norm(target - state[:2]))
    return (
        [
            1.0,
            step_index / max(1, steps - 1),
            float(state[0]),
            float(state[1]),
            float(state[2]),
            float(state[3]),
            float(base_action[0]),
            float(base_action[1]),
            float(np.linalg.norm(base_action)),
            float(target[0]),
            float(target[1]),
            distance,
            policy.base_success,
            policy.nominal_penalty,
            policy.time_scale,
            task.difficulty,
            robot.fragility,
            severity_l1,
            severity_l2,
            weighted_stress,
        ]
        + [1.0 if policy.method_id == method_id else 0.0 for method_id in policy_ids]
        + [1.0 if task.task_id == task_id else 0.0 for task_id in task_ids]
        + [1.0 if robot.robot_id == robot_id else 0.0 for robot_id in robot_ids]
        + [severities[axis] for axis in AXES]
    )


def _feature_names(policy_ids: list[str], task_ids: list[str], robot_ids: list[str]) -> list[str]:
    return (
        [
            "bias",
            "step_fraction",
            "state_x",
            "state_y",
            "state_vx",
            "state_vy",
            "base_action_x",
            "base_action_y",
            "base_action_norm",
            "target_x",
            "target_y",
            "distance_to_target",
            "policy_base_success",
            "policy_nominal_penalty",
            "policy_time_scale",
            "task_difficulty",
            "robot_fragility",
            "severity_l1",
            "severity_l2",
            "weighted_stress",
        ]
        + [f"policy={method_id}" for method_id in policy_ids]
        + [f"task={task_id}" for task_id in task_ids]
        + [f"robot={robot_id}" for robot_id in robot_ids]
        + [f"severity={axis}" for axis in AXES]
    )


def _limit_action(action: np.ndarray, limit: float = 0.36) -> np.ndarray:
    norm = float(np.linalg.norm(action))
    if norm <= limit:
        return action
    return action * (limit / max(norm, 1e-9))


def _teacher_corrected_action(
    source_policy: Policy,
    teacher_policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    state: np.ndarray,
    step_index: int,
) -> np.ndarray:
    severities, _, _, _ = _severity_features(task, robot, source_policy, perturbation)
    target = _target(task)
    ideal = _trajectory_action(teacher_policy, task, robot, Perturbation(), state, step_index)
    to_goal = target - state[:2]
    ideal = ideal + 0.030 * to_goal - 0.055 * state[2:]

    calibration_dir = _unit_from_seed("calibration", task.task_id, robot.robot_id, source_policy.method_id)
    obstacle_dir = _unit_from_seed("obstacle", task.task_id)
    calibration_bias = 0.050 * severities["calibration_offset_mm"] * calibration_dir
    perception_bias = 0.035 * severities["camera_shift_px"] * np.asarray([-calibration_dir[1], calibration_dir[0]])
    obstacle_deflection = 0.045 * severities["obstacle_clearance_cm"] * obstacle_dir
    drag = 1.0 - min(
        0.62,
        0.20 * severities["friction_surface"]
        + 0.16 * severities["payload_g"]
        + 0.12 * severities["tool_extension_cm"]
        + 0.10 * severities["physical_gripper_restriction_mm"],
    )
    bias_cancel = -(calibration_bias + perception_bias + obstacle_deflection) / max(drag, 0.35)
    drag_boost = (1.0 / max(drag, 0.35) - 1.0) * ideal
    latency_lead = 0.035 * (severities["latency_ms"] + severities["controller_rate_scale"]) * state[2:]
    return _limit_action(ideal + bias_cancel + drag_boost + latency_lead)


def _dynamics_step(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    state: np.ndarray,
    action: np.ndarray,
    prev_action: np.ndarray,
    prev_effective: np.ndarray,
    step_index: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    severities, _, _, weighted_stress = _severity_features(task, robot, policy, perturbation)
    latency_blend = min(0.82, 0.78 * severities["latency_ms"])
    rate_hold = min(0.72, 0.62 * severities["controller_rate_scale"])
    effective = (1.0 - latency_blend) * action + latency_blend * prev_action
    effective = (1.0 - rate_hold) * effective + rate_hold * prev_effective

    accel_cap = max(0.045, 0.24 * max(0.20, perturbation.canonical()["acceleration_cap_scale"]))
    accel_delta = effective - prev_effective
    accel_norm = float(np.linalg.norm(accel_delta))
    if accel_norm > accel_cap:
        effective = prev_effective + accel_delta * (accel_cap / accel_norm)

    calibration_dir = _unit_from_seed("calibration", task.task_id, robot.robot_id, policy.method_id)
    obstacle_dir = _unit_from_seed("obstacle", task.task_id)
    calibration_bias = 0.050 * severities["calibration_offset_mm"] * calibration_dir
    noise = rng.normal(0.0, 0.025 * severities["action_noise_std"], size=2)
    perception_bias = 0.035 * severities["camera_shift_px"] * np.asarray([-calibration_dir[1], calibration_dir[0]])
    obstacle_deflection = 0.045 * severities["obstacle_clearance_cm"] * obstacle_dir
    drag = 1.0 - min(
        0.62,
        0.20 * severities["friction_surface"]
        + 0.16 * severities["payload_g"]
        + 0.12 * severities["tool_extension_cm"]
        + 0.10 * severities["physical_gripper_restriction_mm"],
    )
    effective = drag * effective + calibration_bias + perception_bias + obstacle_deflection + noise
    next_vel = 0.52 * state[2:] + effective
    joint_limit = max(0.45, 1.36 - 0.42 * severities["joint_range_scale"] - 0.18 * severities["joint_lock"])
    next_pos = state[:2] + next_vel
    clipped = np.clip(next_pos, -joint_limit, joint_limit)
    if not np.allclose(clipped, next_pos):
        next_vel = 0.28 * (clipped - state[:2])
        next_pos = clipped
    instability = 0.012 * weighted_stress * _unit_from_seed("stress", step_index, policy.method_id, task.task_id)
    next_pos = next_pos + instability
    return np.asarray([next_pos[0], next_pos[1], next_vel[0], next_vel[1]], dtype=float), effective


def _rollout(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    steps: int,
    policy_ids: list[str],
    task_ids: list[str],
    robot_ids: list[str],
    beta: np.ndarray | None = None,
) -> dict[str, Any]:
    seed = stable_seed("corrective-rollout", policy.method_id, task.task_id, robot.robot_id, perturbation.label())
    rng = np.random.default_rng(seed)
    start_offset = 0.08 * _unit_from_seed("start", task.task_id, robot.robot_id)
    state = np.asarray([start_offset[0], start_offset[1], 0.0, 0.0], dtype=float)
    states = [state.copy()]
    base_actions: list[np.ndarray] = []
    applied_actions: list[np.ndarray] = []
    prev_action = np.zeros(2, dtype=float)
    prev_effective = np.zeros(2, dtype=float)
    target = _target(task)
    for step in range(steps):
        base_action = _trajectory_action(policy, task, robot, perturbation, state, step)
        action = base_action.copy()
        if beta is not None:
            features = np.asarray(
                _correction_features(policy, task, robot, perturbation, state, base_action, step, steps, policy_ids, task_ids, robot_ids),
                dtype=float,
            )
            action = _limit_action(base_action + features @ beta)
        state, prev_effective = _dynamics_step(policy, task, robot, perturbation, state, action, prev_action, prev_effective, step, rng)
        states.append(state.copy())
        base_actions.append(base_action.copy())
        applied_actions.append(action.copy())
        prev_action = action
    states_array = np.vstack(states)
    initial_error = float(np.linalg.norm(states_array[0, :2] - target))
    final_error = float(np.linalg.norm(states_array[-1, :2] - target))
    progress = float(1.0 - final_error / max(initial_error, 1e-6))
    return {
        "states": states_array,
        "base_actions": np.vstack(base_actions),
        "applied_actions": np.vstack(applied_actions),
        "target": target,
        "final_error": final_error,
        "progress": progress,
    }


def fit_corrective_trace_adapter(
    policies: dict[str, Policy],
    conditions: list[dict[str, Any]],
    source_method_ids: tuple[str, ...] = ("nominal", "domain_randomization", "bodyshield"),
    teacher_method_id: str = "oracle",
    steps: int = 18,
    ridge: float = 2.5,
    success_threshold: float = 0.12,
    trace_sample_limit: int = 48,
) -> CorrectiveAdaptationResult:
    """Fit a residual action adapter from synthetic corrective traces."""

    source_methods = [method_id for method_id in source_method_ids if method_id in policies]
    if not source_methods:
        raise ValueError("fit_corrective_trace_adapter requires at least one source policy")
    if teacher_method_id not in policies:
        raise ValueError(f"teacher policy missing: {teacher_method_id}")

    policy_ids = sorted(source_methods)
    task_ids = [task.task_id for task in TASKS]
    robot_ids = [robot.robot_id for robot in ROBOTS]
    feature_names = _feature_names(policy_ids, task_ids, robot_ids)
    teacher = policies[teacher_method_id]

    x_rows: list[list[float]] = []
    y_rows: list[np.ndarray] = []
    weight_rows: list[float] = []
    for method_id in policy_ids:
        policy = policies[method_id]
        for task in TASKS:
            for robot in ROBOTS:
                for condition in conditions:
                    if condition["bucket"] not in {"nominal", "seen"}:
                        continue
                    perturbation = condition["perturbation"]
                    base = _rollout(policy, task, robot, perturbation, steps, policy_ids, task_ids, robot_ids)
                    states = base["states"]
                    trace_weight = 1.0 + 2.0 * max(0.0, base["final_error"] - success_threshold)
                    for step in range(steps):
                        state = states[step]
                        base_action = _trajectory_action(policy, task, robot, perturbation, state, step)
                        teacher_action = _teacher_corrected_action(policy, teacher, task, robot, perturbation, state, step)
                        x_rows.append(_correction_features(policy, task, robot, perturbation, state, base_action, step, steps, policy_ids, task_ids, robot_ids))
                        y_rows.append(teacher_action - base_action)
                        weight_rows.append(trace_weight)

    x = np.asarray(x_rows, dtype=float)
    y = np.asarray(y_rows, dtype=float)
    weights = np.sqrt(np.asarray(weight_rows, dtype=float))[:, None]
    xw = x * weights
    yw = y * weights
    regularizer = ridge * np.eye(x.shape[1])
    regularizer[0, 0] = 0.0
    beta = np.linalg.solve(xw.T @ xw + regularizer, xw.T @ yw)

    rollout_rows: list[dict[str, Any]] = []
    trace_sample: list[dict[str, Any]] = []
    for method_id in policy_ids:
        policy = policies[method_id]
        for task in TASKS:
            for robot in ROBOTS:
                for condition in conditions:
                    perturbation = condition["perturbation"]
                    base = _rollout(policy, task, robot, perturbation, steps, policy_ids, task_ids, robot_ids)
                    adapted = _rollout(policy, task, robot, perturbation, steps, policy_ids, task_ids, robot_ids, beta=beta)
                    split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
                    rollout_rows.append(
                        {
                            "method_id": method_id,
                            "task_id": task.task_id,
                            "robot_id": robot.robot_id,
                            "bucket": condition["bucket"],
                            "perturbation_family": condition["family"],
                            "split": split,
                            "base_final_error": float(base["final_error"]),
                            "adapted_final_error": float(adapted["final_error"]),
                            "delta_final_error": float(base["final_error"] - adapted["final_error"]),
                            "base_progress": float(base["progress"]),
                            "adapted_progress": float(adapted["progress"]),
                            "delta_progress": float(adapted["progress"] - base["progress"]),
                            "base_success": bool(base["final_error"] <= success_threshold),
                            "adapted_success": bool(adapted["final_error"] <= success_threshold),
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
                                "target_xy": [round(float(value), 5) for value in base["target"]],
                                "base_final_error": round(float(base["final_error"]), 5),
                                "adapted_final_error": round(float(adapted["final_error"]), 5),
                                "base_states_xy_v": np.round(base["states"], 5).tolist(),
                                "adapted_states_xy_v": np.round(adapted["states"], 5).tolist(),
                                "applied_actions_xy": np.round(adapted["applied_actions"], 5).tolist(),
                                "notes": "Synthetic corrective-trace adaptation sample; not hardware or video.",
                            }
                        )

    rollouts = pd.DataFrame(rollout_rows)
    metric_rows: list[dict[str, Any]] = []
    grouped = [("all", rollouts)]
    grouped.extend((f"split={split}", group) for split, group in rollouts.groupby("split"))
    grouped.extend((f"bucket={bucket}", group) for bucket, group in rollouts.groupby("bucket"))
    grouped.extend((f"method={method_id}", group) for method_id, group in rollouts.groupby("method_id"))
    grouped.extend((f"heldout_method={method_id}", group) for method_id, group in rollouts[rollouts["bucket"] == "heldout"].groupby("method_id"))
    for label, group in grouped:
        metric_rows.append(
            {
                "slice": label,
                "n_rollouts": int(len(group)),
                "base_final_error": float(group["base_final_error"].mean()),
                "adapted_final_error": float(group["adapted_final_error"].mean()),
                "delta_final_error": float(group["delta_final_error"].mean()),
                "base_success_rate": float(group["base_success"].mean()),
                "adapted_success_rate": float(group["adapted_success"].mean()),
                "delta_success_rate": float(group["adapted_success"].mean() - group["base_success"].mean()),
                "base_progress": float(group["base_progress"].mean()),
                "adapted_progress": float(group["adapted_progress"].mean()),
                "delta_progress": float(group["delta_progress"].mean()),
            }
        )
    metrics = pd.DataFrame(metric_rows)

    weight_rows_out = []
    for name, values in zip(feature_names, beta):
        weight_rows_out.append(
            {
                "feature": name,
                "weight_l2": float(np.linalg.norm(values)),
                "delta_action_x": float(values[0]),
                "delta_action_y": float(values[1]),
            }
        )
    residual_weights = pd.DataFrame(weight_rows_out).sort_values("weight_l2", ascending=False)
    return CorrectiveAdaptationResult(metrics, rollouts, residual_weights, trace_sample)
