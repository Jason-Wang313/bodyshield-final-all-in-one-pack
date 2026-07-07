"""Learned high-fidelity MuJoCo gated residual policy audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .high_fidelity import MUJOCO_PLANAR_TASKS, MUJOCO_PLANAR_XML, _planar_command
from .perturbations import AXES, Perturbation
from .policies import Policy
from .sim import stable_seed


@dataclass(frozen=True)
class MujocoResidualPolicyResult:
    metrics: pd.DataFrame
    rollouts: pd.DataFrame
    residual_weights: pd.DataFrame
    gate_ablation: pd.DataFrame
    trace_sample: list[dict[str, Any]]


PLANAR_RESIDUAL_CONDITIONS: list[dict[str, Any]] = [
    {"bucket": "nominal", "family": "nominal", "perturbation": Perturbation()},
    {"bucket": "seen", "family": "latency", "perturbation": Perturbation({"latency_ms": 80})},
    {"bucket": "seen", "family": "action_noise", "perturbation": Perturbation({"action_noise_std": 0.02})},
    {"bucket": "seen", "family": "joint_range", "perturbation": Perturbation({"joint_range_scale": 0.65})},
    {"bucket": "seen", "family": "speed_accel_cap", "perturbation": Perturbation({"speed_cap_scale": 0.5, "acceleration_cap_scale": 0.5})},
    {"bucket": "heldout", "family": "payload", "perturbation": Perturbation({"payload_g": 250})},
    {
        "bucket": "heldout",
        "family": "compound",
        "perturbation": Perturbation({"latency_ms": 80, "action_noise_std": 0.01, "joint_range_scale": 0.75}),
    },
]


def _make_planar_model(task: dict[str, Any], perturbation: Perturbation):
    import mujoco

    joint_limit = 0.36 * max(0.45, float(perturbation.canonical()["joint_range_scale"]))
    damping = 0.18 + 1.10 * perturbation.severity("friction_surface") + 0.35 * perturbation.severity("payload_g")
    mass = 0.05 + 0.12 * perturbation.severity("payload_g")
    model = mujoco.MjModel.from_xml_string(
        MUJOCO_PLANAR_XML.format(
            damping=damping,
            armature=0.04 + 0.03 * perturbation.severity("payload_g"),
            joint_min=-joint_limit,
            joint_max=joint_limit,
            mass=mass,
        )
    )
    return model


def _teacher_command(
    perturbation: Perturbation,
    qpos: np.ndarray,
    qvel: np.ndarray,
    target: np.ndarray,
    previous: np.ndarray,
    step: int,
    horizon: int,
) -> np.ndarray:
    del previous
    speed = max(0.24, float(perturbation.canonical()["speed_cap_scale"]))
    accel = max(0.24, float(perturbation.canonical()["acceleration_cap_scale"]))
    severity_values = np.asarray([perturbation.severity(axis) for axis in AXES], dtype=float)
    stress = float(np.linalg.norm(severity_values))
    del horizon
    correction = 0.42 * (target - qpos)
    damping = 0.18 * qvel
    max_delta = (0.058 * speed * accel) / (1.0 + 0.18 * stress)
    delta = correction - damping
    norm = float(np.linalg.norm(delta))
    if norm > max_delta:
        delta = delta * (max_delta / norm)
    return qpos + delta


def _feature_names(method_ids: list[str], task_ids: list[str]) -> list[str]:
    return (
        [
            "bias",
            "qpos_x",
            "qpos_y",
            "qvel_x",
            "qvel_y",
            "target_x",
            "target_y",
            "error_x",
            "error_y",
            "error_norm",
            "base_command_x",
            "base_command_y",
            "base_delta_norm",
            "previous_command_x",
            "previous_command_y",
            "step_fraction",
            "policy_base_success",
            "policy_nominal_penalty",
            "policy_time_scale",
            "task_tolerance",
            "severity_l1",
            "severity_l2",
        ]
        + [f"method={method_id}" for method_id in method_ids]
        + [f"task={task_id}" for task_id in task_ids]
        + [f"severity={axis}" for axis in AXES]
    )


def _features(
    policy: Policy,
    task: dict[str, Any],
    perturbation: Perturbation,
    qpos: np.ndarray,
    qvel: np.ndarray,
    target: np.ndarray,
    base_command: np.ndarray,
    previous: np.ndarray,
    step: int,
    horizon: int,
    method_ids: list[str],
    task_ids: list[str],
) -> list[float]:
    error = target - qpos
    severities = perturbation.severity_vector()
    severity_values = [float(severities[axis]) for axis in AXES]
    return (
        [
            1.0,
            float(qpos[0]),
            float(qpos[1]),
            float(qvel[0]),
            float(qvel[1]),
            float(target[0]),
            float(target[1]),
            float(error[0]),
            float(error[1]),
            float(np.linalg.norm(error)),
            float(base_command[0]),
            float(base_command[1]),
            float(np.linalg.norm(base_command - qpos)),
            float(previous[0]),
            float(previous[1]),
            step / max(1, horizon - 1),
            policy.base_success,
            policy.nominal_penalty,
            policy.time_scale,
            float(task["tolerance"]),
            float(sum(severity_values)),
            float(np.linalg.norm(severity_values)),
        ]
        + [1.0 if policy.method_id == method_id else 0.0 for method_id in method_ids]
        + [1.0 if task["task_id"] == task_id else 0.0 for task_id in task_ids]
        + severity_values
    )


def _ridge_fit(x: np.ndarray, y: np.ndarray, ridge: float) -> np.ndarray:
    return np.linalg.solve(x.T @ x + ridge * np.eye(x.shape[1]), x.T @ y)


def _clip_residual(residual: np.ndarray, scale: float = 0.060) -> np.ndarray:
    norm = float(np.linalg.norm(residual))
    if norm <= scale:
        return residual
    return residual * (scale / max(norm, 1e-9))


def _gate_residual(
    residual: np.ndarray,
    perturbation: Perturbation,
    qpos: np.ndarray,
    target: np.ndarray,
    tolerance: float,
    residual_scale: float,
    nominal_residual_scale: float,
    min_error_multiple: float,
) -> np.ndarray:
    error_norm = float(np.linalg.norm(target - qpos))
    if error_norm <= tolerance * min_error_multiple:
        return np.zeros_like(residual)
    severity_l1 = float(sum(perturbation.severity(axis) for axis in AXES))
    scale = nominal_residual_scale if severity_l1 <= 1e-9 else residual_scale
    return residual * scale


def _step_planar(model, data, delayed_command: np.ndarray, perturbation: Perturbation) -> None:
    import mujoco

    qpos = np.asarray(data.qpos[:2], dtype=float)
    qvel = np.asarray(data.qvel[:2], dtype=float)
    gain = 5.2 / (1.0 + 0.55 * perturbation.severity("payload_g"))
    damping_gain = 1.1 + 0.6 * perturbation.severity("friction_surface")
    data.ctrl[:] = np.clip(gain * (delayed_command - qpos) - damping_gain * qvel, -2.5, 2.5)
    mujoco.mj_step(model, data)


def _collect_training_rows(
    policies: dict[str, Policy],
    method_ids: list[str],
    tasks: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    train_seeds: int,
    sample_stride: int,
    residual_clip: float,
) -> tuple[np.ndarray, np.ndarray]:
    import mujoco

    task_ids = [task["task_id"] for task in tasks]
    x_rows: list[list[float]] = []
    y_rows: list[np.ndarray] = []
    for method_id in method_ids:
        policy = policies[method_id]
        for task in tasks:
            target = np.asarray(task["target"], dtype=float)
            horizon = int(task["horizon"])
            for condition in conditions:
                if condition["bucket"] == "heldout":
                    continue
                perturbation = condition["perturbation"]
                for seed in range(train_seeds):
                    rng = np.random.default_rng(stable_seed("mujoco-residual-train", method_id, task["task_id"], condition["family"], seed))
                    model = _make_planar_model(task, perturbation)
                    data = mujoco.MjData(model)
                    previous = np.zeros(2, dtype=float)
                    latency_steps = int(round(float(perturbation.canonical()["latency_ms"]) / 12.0))
                    queue = [previous.copy() for _ in range(latency_steps + 1)]
                    for step in range(horizon):
                        qpos = np.array(data.qpos[:2], dtype=float, copy=True)
                        qvel = np.array(data.qvel[:2], dtype=float, copy=True)
                        base_command = _planar_command(policy, perturbation, qpos, target, previous, step, rng)
                        teacher = _teacher_command(perturbation, qpos, qvel, target, previous, step, horizon)
                        if step % sample_stride == 0:
                            x_rows.append(
                                _features(
                                    policy,
                                    task,
                                    perturbation,
                                    qpos,
                                    qvel,
                                    target,
                                    base_command,
                                    previous,
                                    step,
                                    horizon,
                                    method_ids,
                                    task_ids,
                                )
                            )
                            y_rows.append(_clip_residual(teacher - base_command, residual_clip))
                        previous = base_command
                        queue.append(base_command.copy())
                        _step_planar(model, data, queue.pop(0), perturbation)
    return np.asarray(x_rows, dtype=float), np.asarray(y_rows, dtype=float)


def _rollout(
    policy: Policy,
    task: dict[str, Any],
    condition: dict[str, Any],
    seed: int,
    weights: np.ndarray | None,
    method_ids: list[str],
    task_ids: list[str],
    residual_clip: float,
    residual_scale: float = 1.0,
    nominal_residual_scale: float = 0.0,
    min_error_multiple: float = 2.0,
) -> dict[str, Any]:
    import mujoco

    perturbation = condition["perturbation"]
    target = np.asarray(task["target"], dtype=float)
    horizon = int(task["horizon"])
    rng = np.random.default_rng(stable_seed("mujoco-residual-eval", policy.method_id, task["task_id"], condition["family"], seed))
    model = _make_planar_model(task, perturbation)
    data = mujoco.MjData(model)
    previous = np.zeros(2, dtype=float)
    latency_steps = int(round(float(perturbation.canonical()["latency_ms"]) / 12.0))
    queue = [previous.copy() for _ in range(latency_steps + 1)]
    xy_trace: list[list[float]] = []
    commands: list[list[float]] = []
    path_length = 0.0
    prev_qpos = np.array(data.qpos[:2], dtype=float, copy=True)
    residual_norms: list[float] = []
    for step in range(horizon):
        qpos = np.array(data.qpos[:2], dtype=float, copy=True)
        qvel = np.array(data.qvel[:2], dtype=float, copy=True)
        base_command = _planar_command(policy, perturbation, qpos, target, previous, step, rng)
        command = base_command.copy()
        if weights is not None:
            features = np.asarray(
                _features(policy, task, perturbation, qpos, qvel, target, base_command, previous, step, horizon, method_ids, task_ids),
                dtype=float,
            )
            residual = _clip_residual(features @ weights, residual_clip)
            residual = _gate_residual(
                residual,
                perturbation,
                qpos,
                target,
                float(task["tolerance"]),
                residual_scale,
                nominal_residual_scale,
                min_error_multiple,
            )
            command = base_command + residual
            residual_norms.append(float(np.linalg.norm(residual)))
        previous = command
        queue.append(command.copy())
        _step_planar(model, data, queue.pop(0), perturbation)
        new_qpos = np.array(data.qpos[:2], dtype=float, copy=True)
        path_length += float(np.linalg.norm(new_qpos - prev_qpos))
        prev_qpos = new_qpos
        if step % max(1, horizon // 12) == 0 or step == horizon - 1:
            xy_trace.append([round(float(new_qpos[0]), 5), round(float(new_qpos[1]), 5)])
            commands.append([round(float(command[0]), 5), round(float(command[1]), 5)])
    final_qpos = np.asarray(data.qpos[:2], dtype=float)
    final_error = float(np.linalg.norm(final_qpos - target))
    return {
        "final_error": final_error,
        "success": final_error <= float(task["tolerance"]),
        "path_length": path_length,
        "mean_residual_norm": float(np.mean(residual_norms)) if residual_norms else 0.0,
        "xy_trace": xy_trace,
        "commands": commands,
    }


def _metric_row(label: str, frame: pd.DataFrame) -> dict[str, Any]:
    row = {
        "slice": label,
        "n_rollouts": int(len(frame)),
        "base_success_rate": float(frame["base_success"].mean()),
        "adapted_success_rate": float(frame["adapted_success"].mean()),
        "delta_success_rate": float(frame["adapted_success"].mean() - frame["base_success"].mean()),
        "base_final_error": float(frame["base_final_error"].mean()),
        "adapted_final_error": float(frame["adapted_final_error"].mean()),
        "delta_final_error": float(frame["base_final_error"].mean() - frame["adapted_final_error"].mean()),
        "base_path_length": float(frame["base_path_length"].mean()),
        "adapted_path_length": float(frame["adapted_path_length"].mean()),
        "mean_residual_norm": float(frame["mean_residual_norm"].mean()),
    }
    for column in ["residual_scale", "nominal_residual_scale", "min_error_multiple"]:
        if column in frame.columns:
            row[column] = float(frame[column].iloc[0])
    return row


def _variant_metric_rows(variant: str, frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for label, group in [("all", frame)]:
        row = _metric_row(label, group)
        row["variant"] = variant
        rows.append(row)
    for bucket, group in frame.groupby("bucket"):
        row = _metric_row(f"bucket={bucket}", group)
        row["variant"] = variant
        rows.append(row)
    return rows


def _build_gate_ablation(
    base_rollouts: pd.DataFrame,
    policies: dict[str, Policy],
    method_ids: list[str],
    tasks: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    eval_seeds: int,
    weights: np.ndarray,
    task_ids: list[str],
    residual_clip: float,
    residual_scale: float,
    nominal_residual_scale: float,
    min_error_multiple: float,
) -> pd.DataFrame:
    base_lookup = {
        (row.method_id, row.task_id, row.perturbation_family, int(row.seed)): row
        for row in base_rollouts.itertuples(index=False)
    }
    variant_specs = [
        ("residual_off", 0.0, 0.0, 0.0),
        ("always_on", residual_scale, residual_scale, 0.0),
        ("non_nominal_only", residual_scale, 0.0, 0.0),
        ("gated_default", residual_scale, nominal_residual_scale, min_error_multiple),
    ]
    metric_rows: list[dict[str, Any]] = []
    for variant, variant_scale, variant_nominal_scale, variant_min_error in variant_specs:
        rows: list[dict[str, Any]] = []
        for method_id in method_ids:
            policy = policies[method_id]
            for task in tasks:
                for condition in conditions:
                    split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
                    for seed in range(eval_seeds):
                        key = (method_id, task["task_id"], condition["family"], seed)
                        base = base_lookup[key]
                        if variant == "gated_default":
                            adapted_success = bool(base.adapted_success)
                            adapted_final_error = float(base.adapted_final_error)
                            adapted_path_length = float(base.adapted_path_length)
                            mean_residual_norm = float(base.mean_residual_norm)
                        elif variant == "residual_off":
                            adapted_success = bool(base.base_success)
                            adapted_final_error = float(base.base_final_error)
                            adapted_path_length = float(base.base_path_length)
                            mean_residual_norm = 0.0
                        else:
                            adapted = _rollout(
                                policy,
                                task,
                                condition,
                                seed,
                                weights,
                                method_ids,
                                task_ids,
                                residual_clip,
                                residual_scale=variant_scale,
                                nominal_residual_scale=variant_nominal_scale,
                                min_error_multiple=variant_min_error,
                            )
                            adapted_success = bool(adapted["success"])
                            adapted_final_error = float(adapted["final_error"])
                            adapted_path_length = float(adapted["path_length"])
                            mean_residual_norm = float(adapted["mean_residual_norm"])
                        rows.append(
                            {
                                "variant": variant,
                                "method_id": method_id,
                                "task_id": task["task_id"],
                                "bucket": condition["bucket"],
                                "perturbation_family": condition["family"],
                                "split": split,
                                "seed": seed,
                                "base_success": bool(base.base_success),
                                "adapted_success": adapted_success,
                                "base_final_error": float(base.base_final_error),
                                "adapted_final_error": adapted_final_error,
                                "delta_final_error": float(base.base_final_error) - adapted_final_error,
                                "base_path_length": float(base.base_path_length),
                                "adapted_path_length": adapted_path_length,
                                "mean_residual_norm": mean_residual_norm,
                                "residual_scale": float(variant_scale),
                                "nominal_residual_scale": float(variant_nominal_scale),
                                "min_error_multiple": float(variant_min_error),
                            }
                        )
        metric_rows.extend(_variant_metric_rows(variant, pd.DataFrame(rows)))
    ablation = pd.DataFrame(metric_rows)
    return ablation[["variant"] + [column for column in ablation.columns if column != "variant"]]


def fit_mujoco_planar_residual_policy(
    policies: dict[str, Policy],
    source_method_ids: tuple[str, ...] = ("nominal", "domain_randomization", "bodyshield"),
    train_seeds: int = 2,
    eval_seeds: int = 3,
    sample_stride: int = 6,
    ridge: float = 4.0,
    residual_clip: float = 0.060,
    residual_scale: float = 1.0,
    nominal_residual_scale: float = 0.0,
    min_error_multiple: float = 2.0,
    trace_sample_limit: int = 24,
) -> MujocoResidualPolicyResult:
    """Train and evaluate a learned gated residual controller in MuJoCo planar tasks."""

    method_ids = [method_id for method_id in source_method_ids if method_id in policies]
    if not method_ids:
        raise ValueError("fit_mujoco_planar_residual_policy requires at least one policy")
    tasks = list(MUJOCO_PLANAR_TASKS)
    task_ids = [task["task_id"] for task in tasks]
    x, y = _collect_training_rows(
        policies,
        method_ids,
        tasks,
        PLANAR_RESIDUAL_CONDITIONS,
        train_seeds=train_seeds,
        sample_stride=sample_stride,
        residual_clip=residual_clip,
    )
    weights = _ridge_fit(x, y, ridge=ridge)
    rollouts: list[dict[str, Any]] = []
    trace_sample: list[dict[str, Any]] = []
    for method_id in method_ids:
        policy = policies[method_id]
        for task in tasks:
            for condition in PLANAR_RESIDUAL_CONDITIONS:
                for seed in range(eval_seeds):
                    base = _rollout(policy, task, condition, seed, None, method_ids, task_ids, residual_clip)
                    adapted = _rollout(
                        policy,
                        task,
                        condition,
                        seed,
                        weights,
                        method_ids,
                        task_ids,
                        residual_clip,
                        residual_scale=residual_scale,
                        nominal_residual_scale=nominal_residual_scale,
                        min_error_multiple=min_error_multiple,
                    )
                    split = "train_seen_or_nominal" if condition["bucket"] in {"nominal", "seen"} else "heldout"
                    row = {
                        "method_id": method_id,
                        "task_id": task["task_id"],
                        "bucket": condition["bucket"],
                        "perturbation_family": condition["family"],
                        "split": split,
                        "seed": seed,
                        "base_success": bool(base["success"]),
                        "adapted_success": bool(adapted["success"]),
                        "base_final_error": float(base["final_error"]),
                        "adapted_final_error": float(adapted["final_error"]),
                        "delta_final_error": float(base["final_error"] - adapted["final_error"]),
                        "base_path_length": float(base["path_length"]),
                        "adapted_path_length": float(adapted["path_length"]),
                        "mean_residual_norm": float(adapted["mean_residual_norm"]),
                        "residual_scale": float(residual_scale),
                        "nominal_residual_scale": float(nominal_residual_scale),
                        "min_error_multiple": float(min_error_multiple),
                    }
                    rollouts.append(row)
                    if (
                        len(trace_sample) < trace_sample_limit
                        and condition["bucket"] == "heldout"
                        and method_id in {"nominal", "bodyshield"}
                        and seed == 0
                    ):
                        trace_sample.append(
                            {
                                "method_id": method_id,
                                "task_id": task["task_id"],
                                "bucket": condition["bucket"],
                                "perturbation_family": condition["family"],
                                "target_xy": [round(float(value), 5) for value in np.asarray(task["target"], dtype=float)],
                                "base_final_error": round(float(base["final_error"]), 6),
                                "adapted_final_error": round(float(adapted["final_error"]), 6),
                                "base_xy_trace": base["xy_trace"],
                                "adapted_xy_trace": adapted["xy_trace"],
                                "adapted_commands": adapted["commands"],
                                "notes": "MuJoCo planar gated residual-policy trace; trained on simulator corrective labels, not hardware.",
                            }
                        )
    rollout_frame = pd.DataFrame(rollouts)
    metric_rows = [_metric_row("all", rollout_frame)]
    for split, group in rollout_frame.groupby("split"):
        metric_rows.append(_metric_row(f"split={split}", group))
    for bucket, group in rollout_frame.groupby("bucket"):
        metric_rows.append(_metric_row(f"bucket={bucket}", group))
    for method_id, group in rollout_frame.groupby("method_id"):
        metric_rows.append(_metric_row(f"method={method_id}", group))
    feature_names = _feature_names(method_ids, task_ids)
    weight_rows = [
        {
            "feature": name,
            "residual_l2": float(np.linalg.norm(vector)),
            "residual_x": float(vector[0]),
            "residual_y": float(vector[1]),
        }
        for name, vector in zip(feature_names, weights)
    ]
    residual_weights = pd.DataFrame(weight_rows).sort_values("residual_l2", ascending=False)
    gate_ablation = _build_gate_ablation(
        rollout_frame,
        policies,
        method_ids,
        tasks,
        PLANAR_RESIDUAL_CONDITIONS,
        eval_seeds,
        weights,
        task_ids,
        residual_clip,
        residual_scale,
        nominal_residual_scale,
        min_error_multiple,
    )
    return MujocoResidualPolicyResult(pd.DataFrame(metric_rows), rollout_frame, residual_weights, gate_ablation, trace_sample)
