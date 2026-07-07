"""NumPy neural latent WAM audit for BodyShield non-hardware runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .perturbations import AXES, Perturbation
from .policies import Policy
from .sim import ROBOTS, TASKS, RobotSpec, TaskSpec, stable_seed
from .trajectory_wam import generate_synthetic_trajectory
from .visual_wam import _world_grid, render_synthetic_visual_frame


@dataclass(frozen=True)
class NeuralWAMResult:
    metrics: pd.DataFrame
    rollouts: pd.DataFrame
    training_curve: pd.DataFrame
    trace_sample: list[dict[str, Any]]


def _channel_stats(frame: np.ndarray, channel_index: int) -> list[float]:
    channel = np.clip(frame[channel_index], 0.0, None)
    mass = float(channel.sum())
    if mass <= 1e-9:
        return [0.0, 0.0, 0.0, 0.0, 0.0]
    x_grid, y_grid = _world_grid(channel.shape[0])
    cx = float((channel * x_grid).sum() / mass)
    cy = float((channel * y_grid).sum() / mass)
    dist2 = (x_grid - cx) ** 2 + (y_grid - cy) ** 2
    spread = float(np.sqrt((channel * dist2).sum() / mass))
    normalized_mass = float(mass / channel.size)
    peak = float(channel.max())
    return [cx, cy, normalized_mass, spread, peak]


def visual_latent_from_frame(frame: np.ndarray) -> np.ndarray:
    """Compress a generated two-channel observation into visual state latents."""

    object_stats = _channel_stats(frame, 0)
    target_stats = _channel_stats(frame, 1)
    distance = float(np.linalg.norm(np.asarray(object_stats[:2]) - np.asarray(target_stats[:2])))
    return np.asarray(object_stats + target_stats + [distance], dtype=float)


def _clip_latent(latent: np.ndarray) -> np.ndarray:
    clipped = latent.astype(float).copy()
    clipped[[0, 1, 5, 6]] = np.clip(clipped[[0, 1, 5, 6]], -1.55, 1.55)
    clipped[[2, 7]] = np.clip(clipped[[2, 7]], 0.0, 1.0)
    clipped[[3, 8, 10]] = np.clip(clipped[[3, 8, 10]], 0.0, 3.2)
    clipped[[4, 9]] = np.clip(clipped[[4, 9]], 0.0, 1.0)
    clipped[10] = float(np.linalg.norm(clipped[:2] - clipped[5:7]))
    return clipped


def _feature_names(policy_ids: list[str], task_ids: list[str], robot_ids: list[str]) -> list[str]:
    return (
        [
            "bias",
            "object_x",
            "object_y",
            "object_mass",
            "object_spread",
            "object_peak",
            "target_x",
            "target_y",
            "target_mass",
            "target_spread",
            "target_peak",
            "object_target_distance",
            "action_x",
            "action_y",
            "action_norm",
            "step_fraction",
            "policy_base_success",
            "policy_nominal_penalty",
            "policy_time_scale",
            "task_difficulty",
            "robot_fragility",
            "severity_l1",
            "severity_l2",
        ]
        + [f"policy={method_id}" for method_id in policy_ids]
        + [f"task={task_id}" for task_id in task_ids]
        + [f"robot={robot_id}" for robot_id in robot_ids]
        + [f"severity={axis}" for axis in AXES]
    )


def _features(
    latent: np.ndarray,
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
    severity_values = [float(severities[axis]) for axis in AXES]
    return (
        [1.0]
        + latent.astype(float).tolist()
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
            float(sum(severity_values)),
            float(np.linalg.norm(severity_values)),
        ]
        + [1.0 if policy.method_id == method_id else 0.0 for method_id in policy_ids]
        + [1.0 if task.task_id == task_id else 0.0 for task_id in task_ids]
        + [1.0 if robot.robot_id == robot_id else 0.0 for robot_id in robot_ids]
        + severity_values
    )


def _standardize(values: np.ndarray, reference: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = reference.mean(axis=0)
    std = reference.std(axis=0)
    std[std < 1e-6] = 1.0
    return (values - mean) / std, mean, std


def _predict_z(x_z: np.ndarray, weights: dict[str, np.ndarray]) -> np.ndarray:
    hidden = np.tanh(x_z @ weights["w1"] + weights["b1"])
    return hidden @ weights["w2"] + weights["b2"]


def _adam_update(
    params: dict[str, np.ndarray],
    grads: dict[str, np.ndarray],
    moments: dict[str, np.ndarray],
    velocities: dict[str, np.ndarray],
    step: int,
    learning_rate: float,
) -> None:
    beta1 = 0.9
    beta2 = 0.999
    eps = 1e-8
    for name, grad in grads.items():
        moments[name] = beta1 * moments[name] + (1.0 - beta1) * grad
        velocities[name] = beta2 * velocities[name] + (1.0 - beta2) * (grad * grad)
        m_hat = moments[name] / (1.0 - beta1**step)
        v_hat = velocities[name] / (1.0 - beta2**step)
        params[name] -= learning_rate * m_hat / (np.sqrt(v_hat) + eps)


def _fit_mlp(
    x: np.ndarray,
    y: np.ndarray,
    train_indices: np.ndarray,
    heldout_indices: np.ndarray,
    hidden_units: int,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    l2: float,
    seed: int,
    max_train_samples: int,
) -> tuple[dict[str, np.ndarray], pd.DataFrame, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(seed)
    if len(train_indices) > max_train_samples:
        train_indices = np.sort(rng.choice(train_indices, size=max_train_samples, replace=False))
    x_z, x_mean, x_std = _standardize(x, x[train_indices])
    y_z, y_mean, y_std = _standardize(y, y[train_indices])
    input_dim = x.shape[1]
    output_dim = y.shape[1]
    params = {
        "w1": rng.normal(0.0, np.sqrt(2.0 / (input_dim + hidden_units)), size=(input_dim, hidden_units)),
        "b1": np.zeros(hidden_units, dtype=float),
        "w2": rng.normal(0.0, np.sqrt(2.0 / (hidden_units + output_dim)), size=(hidden_units, output_dim)),
        "b2": np.zeros(output_dim, dtype=float),
    }
    moments = {name: np.zeros_like(value) for name, value in params.items()}
    velocities = {name: np.zeros_like(value) for name, value in params.items()}
    train_metric = train_indices[: min(2048, len(train_indices))]
    heldout_metric = heldout_indices[: min(2048, len(heldout_indices))]
    curve_rows: list[dict[str, float | int]] = []
    step = 0

    def metric_row(epoch: int) -> dict[str, float | int]:
        train_pred = _predict_z(x_z[train_metric], params) * y_std + y_mean
        train_pred[:, 5:10] = x[train_metric, 6:11]
        train_pred = np.vstack([_clip_latent(row) for row in train_pred])
        if len(heldout_metric):
            heldout_pred = _predict_z(x_z[heldout_metric], params) * y_std + y_mean
            heldout_pred[:, 5:10] = x[heldout_metric, 6:11]
            heldout_pred = np.vstack([_clip_latent(row) for row in heldout_pred])
            heldout_mse = float(np.mean((heldout_pred - y[heldout_metric]) ** 2))
        else:
            heldout_mse = float("nan")
        return {
            "epoch": epoch,
            "train_latent_mse": float(np.mean((train_pred - y[train_metric]) ** 2)),
            "heldout_latent_mse": heldout_mse,
        }

    curve_rows.append(metric_row(0))
    for epoch in range(1, epochs + 1):
        for start in range(0, len(train_indices), batch_size):
            batch = train_indices[start : start + batch_size]
            xb = x_z[batch]
            yb = y_z[batch]
            hidden = np.tanh(xb @ params["w1"] + params["b1"])
            pred = hidden @ params["w2"] + params["b2"]
            grad_pred = (2.0 / pred.size) * (pred - yb)
            grad_w2 = hidden.T @ grad_pred + l2 * params["w2"]
            grad_b2 = grad_pred.sum(axis=0)
            grad_hidden = (grad_pred @ params["w2"].T) * (1.0 - hidden * hidden)
            grad_w1 = xb.T @ grad_hidden + l2 * params["w1"]
            grad_b1 = grad_hidden.sum(axis=0)
            step += 1
            _adam_update(
                params,
                {"w1": grad_w1, "b1": grad_b1, "w2": grad_w2, "b2": grad_b2},
                moments,
                velocities,
                step,
                learning_rate,
            )
        if epoch == epochs or epoch % max(1, epochs // 8) == 0:
            curve_rows.append(metric_row(epoch))
    return params, pd.DataFrame(curve_rows), (x_mean, x_std, y_mean, y_std)


def _predict_latent(
    features: list[float],
    weights: dict[str, np.ndarray],
    scalers: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    current_latent: np.ndarray,
) -> np.ndarray:
    x_mean, x_std, y_mean, y_std = scalers
    x_z = (np.asarray(features, dtype=float)[None, :] - x_mean) / x_std
    pred = (_predict_z(x_z, weights)[0] * y_std) + y_mean
    pred[5:10] = current_latent[5:10]
    return _clip_latent(pred)


def _metrics(label: str, transitions: pd.DataFrame, rollouts: pd.DataFrame) -> dict[str, Any]:
    return {
        "slice": label,
        "n_transitions": int(len(transitions)),
        "n_rollouts": int(len(rollouts)),
        "transition_latent_mse": float(transitions["latent_mse"].mean()),
        "transition_centroid_error": float(transitions["centroid_error"].mean()),
        "transition_target_error": float(transitions["target_error"].mean()),
        "final_latent_mse": float(rollouts["final_latent_mse"].mean()),
        "final_centroid_error": float(rollouts["final_centroid_error"].mean()),
        "final_target_error": float(rollouts["final_target_error"].mean()),
    }


def fit_neural_latent_wam(
    policies: dict[str, Policy],
    conditions: list[dict[str, Any]],
    source_method_ids: tuple[str, ...] = ("nominal", "domain_randomization", "bodyshield"),
    steps: int = 14,
    frame_size: int = 12,
    hidden_units: int = 48,
    epochs: int = 64,
    batch_size: int = 256,
    learning_rate: float = 0.008,
    l2: float = 1e-4,
    max_train_samples: int = 12000,
    trace_sample_limit: int = 36,
) -> NeuralWAMResult:
    """Train a small CPU neural latent dynamics model over generated visual traces."""

    source_methods = [method_id for method_id in source_method_ids if method_id in policies]
    if not source_methods:
        raise ValueError("fit_neural_latent_wam requires at least one source policy")
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
                    latents = [visual_latent_from_frame(frame) for frame in frames]
                    split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
                    rollout_specs.append(
                        {
                            "method_id": method_id,
                            "policy": policy,
                            "task": task,
                            "robot": robot,
                            "condition": condition,
                            "trajectory": trajectory,
                            "latents": latents,
                        }
                    )
                    for step_index in range(steps):
                        x_rows.append(
                            _features(
                                latents[step_index],
                                trajectory["actions"][step_index],
                                step_index,
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
                        y_rows.append(latents[step_index + 1])
                        transition_meta.append(
                            {
                                "method_id": method_id,
                                "task_id": task.task_id,
                                "robot_id": robot.robot_id,
                                "bucket": condition["bucket"],
                                "perturbation_family": condition["family"],
                                "split": split,
                                "true_next_latent": latents[step_index + 1],
                            }
                        )

    x = np.asarray(x_rows, dtype=float)
    y = np.asarray(y_rows, dtype=float)
    train_indices = np.asarray([i for i, row in enumerate(transition_meta) if row["split"] == "train_seen_or_nominal"], dtype=int)
    heldout_indices = np.asarray([i for i, row in enumerate(transition_meta) if row["split"] == "heldout"], dtype=int)
    weights, training_curve, scalers = _fit_mlp(
        x,
        y,
        train_indices,
        heldout_indices,
        hidden_units=hidden_units,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        l2=l2,
        seed=stable_seed("neural-latent-wam", len(x_rows), hidden_units, epochs),
        max_train_samples=max_train_samples,
    )
    x_mean, x_std, y_mean, y_std = scalers
    pred_all = (_predict_z((x - x_mean) / x_std, weights) * y_std) + y_mean
    pred_all[:, 5:10] = x[:, 6:11]
    pred_all = np.vstack([_clip_latent(row) for row in pred_all])

    transition_rows: list[dict[str, Any]] = []
    for index, meta in enumerate(transition_meta):
        true_latent = meta.pop("true_next_latent")
        pred_latent = pred_all[index]
        transition_rows.append(
            {
                **meta,
                "latent_mse": float(np.mean((pred_latent - true_latent) ** 2)),
                "centroid_error": float(np.linalg.norm(pred_latent[:2] - true_latent[:2])),
                "target_error": float(np.linalg.norm(pred_latent[5:7] - true_latent[5:7])),
            }
        )
    transitions = pd.DataFrame(transition_rows)

    rollout_rows: list[dict[str, Any]] = []
    trace_sample: list[dict[str, Any]] = []
    for spec in rollout_specs:
        method_id = spec["method_id"]
        policy = spec["policy"]
        task = spec["task"]
        robot = spec["robot"]
        condition = spec["condition"]
        perturbation = condition["perturbation"]
        trajectory = spec["trajectory"]
        true_latents = spec["latents"]
        pred_latent = true_latents[0].copy()
        for step_index in range(steps):
            features = _features(
                pred_latent,
                trajectory["actions"][step_index],
                step_index,
                steps,
                policy,
                task,
                robot,
                perturbation,
                policy_ids,
                task_ids,
                robot_ids,
            )
            pred_latent = _predict_latent(features, weights, scalers, pred_latent)
        true_final = true_latents[-1]
        split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
        rollout_rows.append(
            {
                "method_id": method_id,
                "task_id": task.task_id,
                "robot_id": robot.robot_id,
                "bucket": condition["bucket"],
                "perturbation_family": condition["family"],
                "split": split,
                "final_latent_mse": float(np.mean((pred_latent - true_final) ** 2)),
                "final_centroid_error": float(np.linalg.norm(pred_latent[:2] - true_final[:2])),
                "final_target_error": float(np.linalg.norm(pred_latent[5:7] - true_final[5:7])),
                "true_final_x": float(true_final[0]),
                "true_final_y": float(true_final[1]),
                "pred_final_x": float(pred_latent[0]),
                "pred_final_y": float(pred_latent[1]),
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
                    "true_final_visual_latent": np.round(true_final, 5).tolist(),
                    "pred_final_visual_latent": np.round(pred_latent, 5).tolist(),
                    "final_latent_mse": round(float(np.mean((pred_latent - true_final) ** 2)), 8),
                    "notes": "NumPy MLP visual-latent WAM trace; synthetic only, not real video.",
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
    training_curve.insert(1, "hidden_units", hidden_units)
    training_curve.insert(2, "max_train_samples", max_train_samples)
    training_curve.insert(3, "feature_count", len(_feature_names(policy_ids, task_ids, robot_ids)))
    return NeuralWAMResult(metrics, rollouts, training_curve, trace_sample)
