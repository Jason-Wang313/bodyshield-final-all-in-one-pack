"""CPU-only analytic simulator for BodyShield non-hardware execution.

This is not a MuJoCo or ManiSkill physics replacement.  It is a deterministic,
stochastic surrogate for exercising BodyBreak search, BodyShield repair,
logging, statistics, and reviewer-facing analysis before hardware is ready.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from .perturbations import Perturbation
from .policies import Policy


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    difficulty: float
    weights: dict[str, float]
    compound_sensitivity: float = 0.18


@dataclass(frozen=True)
class RobotSpec:
    robot_id: str
    fragility: float
    nominal_bonus: float
    axis_modifiers: dict[str, float]


TASKS: list[TaskSpec] = [
    TaskSpec(
        "push_block",
        0.02,
        {
            "latency_ms": 0.65,
            "action_noise_std": 0.72,
            "calibration_offset_mm": 0.85,
            "speed_cap_scale": 0.45,
            "acceleration_cap_scale": 0.50,
            "controller_rate_scale": 0.60,
            "friction_surface": 0.70,
            "payload_g": 0.25,
            "obstacle_clearance_cm": 0.52,
        },
    ),
    TaskSpec(
        "press_button",
        0.04,
        {
            "latency_ms": 0.55,
            "action_noise_std": 0.88,
            "calibration_offset_mm": 1.15,
            "joint_range_scale": 0.62,
            "camera_shift_px": 0.82,
            "controller_rate_scale": 0.72,
            "obstacle_clearance_cm": 0.60,
        },
    ),
    TaskSpec(
        "slide_track",
        0.05,
        {
            "latency_ms": 0.75,
            "action_noise_std": 0.80,
            "speed_cap_scale": 0.62,
            "acceleration_cap_scale": 0.70,
            "controller_rate_scale": 0.66,
            "friction_surface": 0.95,
            "calibration_offset_mm": 0.60,
        },
    ),
    TaskSpec(
        "pick_place_bin",
        0.08,
        {
            "gripper_limit_scale": 1.20,
            "physical_gripper_restriction_mm": 1.15,
            "joint_range_scale": 0.92,
            "calibration_offset_mm": 0.72,
            "action_noise_std": 0.62,
            "payload_g": 0.70,
            "camera_shift_px": 0.85,
        },
        compound_sensitivity=0.25,
    ),
    TaskSpec(
        "pull_ring",
        0.07,
        {
            "speed_cap_scale": 0.72,
            "acceleration_cap_scale": 0.68,
            "payload_g": 0.88,
            "joint_range_scale": 0.82,
            "tool_extension_cm": 0.65,
            "friction_surface": 0.58,
        },
    ),
    TaskSpec(
        "constrained_place",
        0.09,
        {
            "calibration_offset_mm": 1.10,
            "camera_shift_px": 1.00,
            "joint_range_scale": 1.05,
            "action_noise_std": 0.80,
            "gripper_limit_scale": 0.65,
            "obstacle_clearance_cm": 1.20,
            "controller_rate_scale": 0.70,
        },
        compound_sensitivity=0.30,
    ),
    TaskSpec(
        "tool_push",
        0.06,
        {
            "tool_extension_cm": 1.12,
            "payload_g": 0.68,
            "calibration_offset_mm": 0.72,
            "friction_surface": 0.74,
            "speed_cap_scale": 0.62,
            "physical_gripper_restriction_mm": 0.70,
            "obstacle_clearance_cm": 0.55,
        },
    ),
    TaskSpec(
        "rotate_object",
        0.08,
        {
            "friction_surface": 1.15,
            "action_noise_std": 0.86,
            "calibration_offset_mm": 0.80,
            "gripper_limit_scale": 0.92,
            "physical_gripper_restriction_mm": 0.82,
            "latency_ms": 0.62,
            "controller_rate_scale": 0.72,
        },
        compound_sensitivity=0.27,
    ),
]

ROBOTS: list[RobotSpec] = [
    RobotSpec("franka_panda", 0.82, 0.025, {"joint_range_scale": 0.90, "payload_g": 0.85}),
    RobotSpec("ur5e", 0.86, 0.018, {"payload_g": 0.80, "tool_extension_cm": 0.90, "obstacle_clearance_cm": 0.92}),
    RobotSpec("xarm6", 0.92, 0.010, {"calibration_offset_mm": 0.95, "latency_ms": 0.98}),
    RobotSpec("widowx250_like", 1.12, -0.010, {"gripper_limit_scale": 1.12, "payload_g": 1.20, "physical_gripper_restriction_mm": 1.15}),
    RobotSpec("so101_urdf", 1.22, -0.020, {"speed_cap_scale": 1.12, "calibration_offset_mm": 1.18, "controller_rate_scale": 1.12}),
    RobotSpec("aloha_single_arm", 0.98, 0.005, {"camera_shift_px": 1.10, "gripper_limit_scale": 0.95}),
]

FAILURE_BY_AXIS = {
    "latency_ms": "tracking_error",
    "action_noise_std": "tracking_error",
    "joint_range_scale": "joint_limit",
    "joint_lock": "joint_limit",
    "gripper_limit_scale": "unreachable",
    "speed_cap_scale": "tracking_error",
    "acceleration_cap_scale": "tracking_error",
    "calibration_offset_mm": "other",
    "camera_shift_px": "verifier_uncertain",
    "controller_rate_scale": "tracking_error",
    "payload_g": "mechanical_fault",
    "tool_extension_cm": "collision",
    "physical_gripper_restriction_mm": "unreachable",
    "obstacle_clearance_cm": "collision",
    "friction_surface": "slip",
}


def stable_seed(*parts: Any) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**32)


def logit(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return math.log(p / (1.0 - p))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def success_probability(policy: Policy, task: TaskSpec, robot: RobotSpec, perturbation: Perturbation) -> float:
    sev = perturbation.severity_vector()
    stress = 0.0
    for axis, value in sev.items():
        task_weight = task.weights.get(axis, 0.40)
        robot_weight = robot.axis_modifiers.get(axis, 1.0) * robot.fragility
        stress += value * task_weight * robot_weight * policy.sensitivity.get(axis, 1.0)

    active = [axis for axis, value in sev.items() if value > 0.05]
    synergy = max(0, len(active) - 1) * task.compound_sensitivity
    if {"latency_ms", "action_noise_std", "calibration_offset_mm"}.issubset(active):
        synergy += 0.18
    if {"gripper_limit_scale", "payload_g"}.issubset(active):
        synergy += 0.12
    if {"controller_rate_scale", "latency_ms"}.issubset(active):
        synergy += 0.10
    if {"obstacle_clearance_cm", "calibration_offset_mm"}.issubset(active):
        synergy += 0.14

    base = policy.base_success + robot.nominal_bonus - task.difficulty - policy.nominal_penalty
    probability = sigmoid(logit(base) - 2.05 * stress - 0.95 * synergy)
    return float(min(0.995, max(0.005, probability)))


def dominant_failure_axis(task: TaskSpec, robot: RobotSpec, policy: Policy, perturbation: Perturbation) -> str | None:
    sev = perturbation.severity_vector()
    scored = []
    for axis, value in sev.items():
        scored.append(
            (
                value
                * task.weights.get(axis, 0.40)
                * robot.axis_modifiers.get(axis, 1.0)
                * policy.sensitivity.get(axis, 1.0),
                axis,
            )
        )
    score, axis = max(scored, key=lambda item: item[0])
    return axis if score > 0.01 else None


def evaluate_rate(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    n_trials: int = 50,
    seed: int | None = None,
) -> float:
    rng = np.random.default_rng(seed if seed is not None else stable_seed(policy.method_id, task.task_id, robot.robot_id, perturbation.label()))
    p = success_probability(policy, task, robot, perturbation)
    return float(rng.binomial(1, p, size=n_trials).mean())


def trial_records(
    policy: Policy,
    task: TaskSpec,
    robot: RobotSpec,
    perturbation: Perturbation,
    n_trials: int = 50,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    seed = seed if seed is not None else stable_seed(policy.method_id, task.task_id, robot.robot_id, perturbation.label())
    rng = np.random.default_rng(seed)
    p = success_probability(policy, task, robot, perturbation)
    values = perturbation.canonical()
    fail_axis = dominant_failure_axis(task, robot, policy, perturbation)
    failure_category = FAILURE_BY_AXIS.get(fail_axis, "other") if fail_axis else None
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    records: list[dict[str, Any]] = []
    for index, success_bool in enumerate(rng.binomial(1, p, size=n_trials).astype(bool)):
        trial_id = f"{task.task_id}-{robot.robot_id}-{policy.method_id}-{seed}-{index:03d}"
        execution_time = policy.time_scale * (
            2.0
            + 0.6 * perturbation.severity("latency_ms")
            + 0.8 * perturbation.severity("speed_cap_scale")
            + 0.5 * perturbation.severity("acceleration_cap_scale")
            + 0.4 * perturbation.severity("controller_rate_scale")
        )
        path_length = (
            0.42
            * policy.time_scale
            * (
                1.0
                + 0.15 * perturbation.severity("calibration_offset_mm")
                + 0.20 * perturbation.severity("obstacle_clearance_cm")
                + 0.12 * perturbation.severity("tool_extension_cm")
            )
        )
        records.append(
            {
                "trial_id": trial_id,
                "timestamp": timestamp,
                "phase": "simulation",
                "task_id": task.task_id,
                "robot_id": robot.robot_id,
                "policy_id": policy.method_id,
                "method_id": policy.method_id,
                "perturbation": values,
                "initial_state": {
                    "object_pose": None,
                    "robot_joint_state": None,
                    "camera_frame_path": None,
                },
                "action_trace_path": f"results/action_traces/{trial_id}.json",
                "joint_log_path": None,
                "video_path": None,
                "verifier": {
                    "label": "success" if success_bool else "failure",
                    "confidence": round(0.82 + 0.13 * abs(float(success_bool) - 0.5), 3),
                    "raw_measurement": {"synthetic_success_probability": round(p, 4)},
                    "verifier_version": "analytic-sim-v0.1",
                },
                "human_audit": {"label": None, "auditor_id": None, "notes": None},
                "safety": {
                    "stop_triggered": False,
                    "stop_reason": None,
                    "max_tracking_error": round(perturbation.severity("action_noise_std") * 0.025, 5),
                    "max_current_or_load": round(perturbation.severity("payload_g") * 0.40, 5),
                    "workspace_violation": bool(perturbation.severity("obstacle_clearance_cm") > 0.8 and not success_bool),
                },
                "result": {
                    "success": bool(success_bool),
                    "failure_category": None if success_bool else failure_category,
                    "execution_time_s": round(execution_time, 3),
                    "path_length_m": round(path_length, 4),
                    "retries": 0 if success_bool else int(rng.choice([0, 1, 1, 2])),
                },
                "metadata": {
                    "config_hash": "simulation_bodyshield_maxout.yaml",
                    "code_commit_hash": "tree-hash-filled-in-report",
                    "notes": "CPU analytic surrogate; not hardware or MuJoCo/ManiSkill evidence.",
                },
            }
        )
    return records
