"""Synthetic trajectory-level WAM proxy for BodyShield non-hardware audits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .perturbations import AXES, Perturbation
from .policies import Policy
from .sim import ROBOTS, TASKS, RobotSpec, TaskSpec, stable_seed, success_probability


TASK_TARGETS: dict[str, tuple[float, float]] = {
    "push_block": (1.0, 0.0),
    "press_button": (0.72, 0.42),
    "slide_track": (1.16, -0.18),
    "pick_place_bin": (0.84, 0.74),
    "pull_ring": (-0.58, 0.82),
    "constrained_place": (0.58, 1.02),
    "tool_push": (1.26, 0.34),
    "rotate_object": (0.32, -0.92),
}


@dataclass(frozen=True)
class TrajectoryWAMResult:
    metrics: pd.DataFrame
    axis_weights: pd.DataFrame
    rollouts: pd.DataFrame
    trace_sample: list[dict[str, Any]]


def _target(task: TaskSpec) -> np.ndarray:
    return np.asarray(TASK_TARGETS.get(task.task_id, (1.0, 0.0)), dtype=float)


def _unit_from_seed(*parts: Any) -> np.ndarray:
    seed = stable_seed("trajectory-direction", *parts)
    angle = (seed / float(2**32)) * 2.0 * math.pi
    return np.asarray([math.cos(angle), math.sin(angle)], dtype=float)


def _severity_features(task: TaskSpec, robot: RobotSpec, policy: Policy, perturbation: Perturbation) -> tuple[dict[str, float], float, float, float]:
    severities = perturbation.severity_vector()
    severity_l1 = float(sum(severities.values()))
    severity_l2 = float(math.sqrt(sum(value * value for value in severities.values())))
    weighted_stress = 0.0
    for axis, value in severities.items():
        weighted_stress += (
            value
            * task.weights.get(axis, 0.40)
            * robot.axis_modifiers.get(axis, 1.0)
            * robot.fragility
            * policy.sensitivity.get(axis, 1.0)
        )
    return severities, severity_l1, severity_l2, float(weighted_stress)


def generate_synthetic_trajectory(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    steps: int = 18,
) -> dict[str, Any]:
    """Generate a compact action/state trajectory from the analytic setup.

    The states are a transparent 2-D proprioceptive proxy, not rendered video.
    They are useful for testing whether the package can learn a dynamics model
    over action-conditioned traces while preserving the no-hardware boundary.
    """

    seed = stable_seed("trajectory-wam", policy.method_id, task.task_id, robot.robot_id, perturbation.label())
    rng = np.random.default_rng(seed)
    severities, _, _, weighted_stress = _severity_features(task, robot, policy, perturbation)
    goal = _target(task)
    start_offset = 0.08 * _unit_from_seed("start", task.task_id, robot.robot_id)
    state = np.asarray([start_offset[0], start_offset[1], 0.0, 0.0], dtype=float)
    states = [state.copy()]
    actions: list[np.ndarray] = []
    prev_action = np.zeros(2, dtype=float)
    prev_effective = np.zeros(2, dtype=float)
    calibration_dir = _unit_from_seed("calibration", task.task_id, robot.robot_id, policy.method_id)
    obstacle_dir = _unit_from_seed("obstacle", task.task_id)
    success_p = success_probability(policy, task, robot, perturbation)

    for step in range(steps):
        pos = state[:2]
        vel = state[2:]
        to_goal = goal - pos
        progress_gain = 0.18 + 0.05 * success_p - 0.015 * task.difficulty
        damping = 0.42 + 0.06 * policy.time_scale
        desired = progress_gain * to_goal - damping * vel
        speed_limit = 0.26 * max(0.30, perturbation.canonical()["speed_cap_scale"]) / max(policy.time_scale, 0.4)
        desired_norm = float(np.linalg.norm(desired))
        if desired_norm > speed_limit:
            desired = desired * (speed_limit / desired_norm)

        latency_blend = min(0.82, 0.78 * severities["latency_ms"])
        rate_hold = min(0.72, 0.62 * severities["controller_rate_scale"])
        effective = (1.0 - latency_blend) * desired + latency_blend * prev_action
        effective = (1.0 - rate_hold) * effective + rate_hold * prev_effective

        accel_cap = max(0.045, 0.24 * max(0.20, perturbation.canonical()["acceleration_cap_scale"]))
        accel_delta = effective - prev_effective
        accel_norm = float(np.linalg.norm(accel_delta))
        if accel_norm > accel_cap:
            effective = prev_effective + accel_delta * (accel_cap / accel_norm)

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

        next_vel = 0.52 * vel + effective
        joint_limit = max(0.45, 1.36 - 0.42 * severities["joint_range_scale"] - 0.18 * severities["joint_lock"])
        next_pos = pos + next_vel
        clipped = np.clip(next_pos, -joint_limit, joint_limit)
        if not np.allclose(clipped, next_pos):
            next_vel = 0.28 * (clipped - pos)
            next_pos = clipped

        instability = 0.012 * weighted_stress * _unit_from_seed("stress", step, policy.method_id, task.task_id)
        next_pos = next_pos + instability
        state = np.asarray([next_pos[0], next_pos[1], next_vel[0], next_vel[1]], dtype=float)
        states.append(state.copy())
        actions.append(desired.copy())
        prev_action = desired
        prev_effective = effective

    states_array = np.vstack(states)
    actions_array = np.vstack(actions)
    final_error = float(np.linalg.norm(states_array[-1, :2] - goal))
    initial_error = float(np.linalg.norm(states_array[0, :2] - goal))
    progress = float(1.0 - final_error / max(initial_error, 1e-6))
    return {
        "method_id": policy.method_id,
        "task_id": task.task_id,
        "robot_id": robot.robot_id,
        "perturbation": perturbation.label(),
        "target": goal,
        "states": states_array,
        "actions": actions_array,
        "final_error": final_error,
        "progress": progress,
    }


def _feature_names(policy_ids: list[str], task_ids: list[str], robot_ids: list[str]) -> list[str]:
    return (
        [
            "bias",
            "step_fraction",
            "state_x",
            "state_y",
            "state_vx",
            "state_vy",
            "action_x",
            "action_y",
            "action_norm",
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


def _features(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    state: np.ndarray,
    action: np.ndarray,
    target: np.ndarray,
    step_index: int,
    steps: int,
    policy_ids: list[str],
    task_ids: list[str],
    robot_ids: list[str],
) -> list[float]:
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
            float(action[0]),
            float(action[1]),
            float(np.linalg.norm(action)),
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


def _trajectory_action(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    state: np.ndarray,
    step_index: int,
) -> np.ndarray:
    del step_index
    goal = _target(task)
    to_goal = goal - state[:2]
    desired = (0.18 + 0.05 * success_probability(policy, task, robot, perturbation)) * to_goal - 0.44 * state[2:]
    speed_limit = 0.26 * max(0.30, perturbation.canonical()["speed_cap_scale"]) / max(policy.time_scale, 0.4)
    norm = float(np.linalg.norm(desired))
    if norm > speed_limit:
        desired = desired * (speed_limit / norm)
    return desired


def _split_metrics(split: str, frame: pd.DataFrame, transition_errors: pd.DataFrame) -> dict[str, Any]:
    transitions = transition_errors[transition_errors["split"] == split] if split not in {"all"} else transition_errors
    rollouts = frame[frame["split"] == split] if split not in {"all"} else frame
    return {
        "split": split,
        "n_transitions": int(len(transitions)),
        "n_rollouts": int(len(rollouts)),
        "transition_state_rmse": float(math.sqrt(np.mean(transitions["state_sq_error"]))),
        "transition_xy_rmse": float(math.sqrt(np.mean(transitions["xy_sq_error"]))),
        "transition_velocity_rmse": float(math.sqrt(np.mean(transitions["velocity_sq_error"]))),
        "final_xy_mae": float(rollouts["final_xy_error"].mean()),
        "final_error_mae": float((rollouts["pred_final_error"] - rollouts["true_final_error"]).abs().mean()),
        "final_progress_mae": float((rollouts["pred_progress"] - rollouts["true_progress"]).abs().mean()),
    }


def fit_trajectory_wam_proxy(
    policies: dict[str, Policy],
    conditions: list[dict[str, Any]],
    steps: int = 18,
    ridge: float = 3.0,
    trace_sample_limit: int = 96,
) -> TrajectoryWAMResult:
    """Train and evaluate a transparent trajectory-level dynamics proxy.

    The model is a CPU ridge next-state predictor over synthetic proprioceptive
    traces. It is closer to a WAM audit than the scalar outcome predictor, but
    it is still not video modeling, neural policy learning, or real adaptation.
    """

    policy_ids = sorted(policies)
    task_ids = [task.task_id for task in TASKS]
    robot_ids = [robot.robot_id for robot in ROBOTS]
    feature_names = _feature_names(policy_ids, task_ids, robot_ids)

    x_rows: list[list[float]] = []
    y_rows: list[np.ndarray] = []
    transition_meta: list[dict[str, Any]] = []
    trajectories: list[dict[str, Any]] = []
    trace_sample: list[dict[str, Any]] = []
    task_by_id = {task.task_id: task for task in TASKS}
    robot_by_id = {robot.robot_id: robot for robot in ROBOTS}

    for method_id in policy_ids:
        policy = policies[method_id]
        for task in TASKS:
            for robot in ROBOTS:
                for condition in conditions:
                    perturbation = condition["perturbation"]
                    trajectory = generate_synthetic_trajectory(policy, task, robot, perturbation, steps=steps)
                    trajectory.update(
                        {
                            "bucket": condition["bucket"],
                            "family": condition["family"],
                            "level": condition.get("level", ""),
                        }
                    )
                    trajectories.append(trajectory)
                    if len(trace_sample) < trace_sample_limit and (
                        condition["bucket"] in {"nominal", "heldout"} or method_id in {"bodyshield", "domain_randomization"}
                    ):
                        trace_sample.append(
                            {
                                "method_id": method_id,
                                "task_id": task.task_id,
                                "robot_id": robot.robot_id,
                                "bucket": condition["bucket"],
                                "perturbation_family": condition["family"],
                                "perturbation": perturbation.label(),
                                "target_xy": [round(float(value), 5) for value in trajectory["target"]],
                                "states_xy_v": np.round(trajectory["states"], 5).tolist(),
                                "actions_xy": np.round(trajectory["actions"], 5).tolist(),
                                "final_error": round(float(trajectory["final_error"]), 5),
                                "progress": round(float(trajectory["progress"]), 5),
                                "notes": "Synthetic proprioceptive trajectory trace; not video or hardware.",
                            }
                        )

                    states = trajectory["states"]
                    actions = trajectory["actions"]
                    target = trajectory["target"]
                    for step in range(steps):
                        x_rows.append(
                            _features(
                                policy,
                                task,
                                robot,
                                perturbation,
                                states[step],
                                actions[step],
                                target,
                                step,
                                steps,
                                policy_ids,
                                task_ids,
                                robot_ids,
                            )
                        )
                        y_rows.append(states[step + 1] - states[step])
                        split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
                        transition_meta.append(
                            {
                                "method_id": method_id,
                                "task_id": task.task_id,
                                "robot_id": robot.robot_id,
                                "bucket": condition["bucket"],
                                "perturbation_family": condition["family"],
                                "split": split,
                            }
                        )

    x = np.asarray(x_rows, dtype=float)
    y = np.asarray(y_rows, dtype=float)
    train_mask = np.asarray([row["split"] == "train_seen_or_nominal" for row in transition_meta], dtype=bool)
    regularizer = ridge * np.eye(x.shape[1])
    regularizer[0, 0] = 0.0
    beta = np.linalg.solve(x[train_mask].T @ x[train_mask] + regularizer, x[train_mask].T @ y[train_mask])
    transition_pred = x @ beta
    transition_target = y
    transition_delta = transition_pred - transition_target
    transition_errors = pd.DataFrame(transition_meta)
    transition_errors["state_sq_error"] = np.sum(transition_delta**2, axis=1)
    transition_errors["xy_sq_error"] = np.sum(transition_delta[:, :2] ** 2, axis=1)
    transition_errors["velocity_sq_error"] = np.sum(transition_delta[:, 2:] ** 2, axis=1)

    rollout_rows: list[dict[str, Any]] = []
    for trajectory in trajectories:
        policy = policies[trajectory["method_id"]]
        task = task_by_id[trajectory["task_id"]]
        robot = robot_by_id[trajectory["robot_id"]]
        perturbation = next(
            condition["perturbation"]
            for condition in conditions
            if condition["family"] == trajectory["family"] and condition["bucket"] == trajectory["bucket"] and condition.get("level", "") == trajectory["level"]
        )
        pred_state = trajectory["states"][0].copy()
        target = trajectory["target"]
        for step in range(steps):
            action = _trajectory_action(policy, task, robot, perturbation, pred_state, step)
            features = np.asarray(
                _features(
                    policy,
                    task,
                    robot,
                    perturbation,
                    pred_state,
                    action,
                    target,
                    step,
                    steps,
                    policy_ids,
                    task_ids,
                    robot_ids,
                ),
                dtype=float,
            )
            pred_state = pred_state + features @ beta
        true_final = trajectory["states"][-1]
        pred_final_error = float(np.linalg.norm(pred_state[:2] - target))
        true_final_error = float(trajectory["final_error"])
        initial_error = float(np.linalg.norm(trajectory["states"][0, :2] - target))
        pred_progress = float(1.0 - pred_final_error / max(initial_error, 1e-6))
        split = "train_seen_or_nominal" if trajectory["bucket"] in {"nominal", "seen"} else "heldout"
        rollout_rows.append(
            {
                "method_id": trajectory["method_id"],
                "task_id": trajectory["task_id"],
                "robot_id": trajectory["robot_id"],
                "bucket": trajectory["bucket"],
                "perturbation_family": trajectory["family"],
                "split": split,
                "true_final_x": float(true_final[0]),
                "true_final_y": float(true_final[1]),
                "pred_final_x": float(pred_state[0]),
                "pred_final_y": float(pred_state[1]),
                "true_final_error": true_final_error,
                "pred_final_error": pred_final_error,
                "final_xy_error": float(np.linalg.norm(pred_state[:2] - true_final[:2])),
                "true_progress": float(trajectory["progress"]),
                "pred_progress": pred_progress,
            }
        )

    rollouts = pd.DataFrame(rollout_rows)
    metric_rows = [_split_metrics("all", rollouts, transition_errors)]
    metric_rows.append(_split_metrics("train_seen_or_nominal", rollouts, transition_errors))
    metric_rows.append(_split_metrics("heldout", rollouts, transition_errors))
    for bucket, _ in rollouts.groupby("bucket"):
        bucket_rollouts = rollouts.copy()
        bucket_transitions = transition_errors.copy()
        metric_rows.append(
            _split_metrics(
                f"bucket={bucket}",
                bucket_rollouts.assign(split=np.where(bucket_rollouts["bucket"] == bucket, f"bucket={bucket}", "other")),
                bucket_transitions.assign(split=np.where(bucket_transitions["bucket"] == bucket, f"bucket={bucket}", "other")),
            )
        )

    coef = dict(zip(feature_names, beta))
    axis_rows = []
    for axis in AXES:
        values = coef.get(f"severity={axis}", np.zeros(4))
        axis_rows.append(
            {
                "axis": axis,
                "coefficient_l2": float(np.linalg.norm(values)),
                "delta_x": float(values[0]),
                "delta_y": float(values[1]),
                "delta_vx": float(values[2]),
                "delta_vy": float(values[3]),
                "interpretation": "larger l2 means the trajectory model uses this severity more strongly",
            }
        )
    axis_weights = pd.DataFrame(axis_rows).sort_values("coefficient_l2", ascending=False)
    return TrajectoryWAMResult(pd.DataFrame(metric_rows), axis_weights, rollouts, trace_sample)
