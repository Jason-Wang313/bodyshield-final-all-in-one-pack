"""Bounded high-fidelity non-hardware probes.

These probes are intentionally small.  They do not replace a full robot
benchmark, but they provide executable MuJoCo and ManiSkill evidence tiers
above the analytic surrogate.
"""

from __future__ import annotations

import contextlib
import io
import re
from typing import Any

import numpy as np

from .perturbations import Perturbation
from .policies import Policy


MUJOCO_XML = """
<mujoco model="bodyshield_{task_id}">
  <option timestep="0.005" gravity="0 0 0" integrator="Euler"/>
  <worldbody>
    <body name="body" pos="0 0 0">
      <joint name="progress" type="{joint_type}" axis="{axis}" damping="{damping}" armature="0.05" limited="true" range="-5 5"/>
      <geom name="block_geom" type="box" size="0.03 0.03 0.03" mass="{mass}" rgba="0.1 0.5 0.7 1"/>
    </body>
  </worldbody>
  <actuator>
    <motor name="motor" joint="progress" gear="0.25"/>
  </actuator>
</mujoco>
"""

MUJOCO_TASKS = [
    {"task_id": "push_block_probe", "joint_type": "slide", "axis": "1 0 0", "target": 0.030, "horizon": 260, "base": 0.22},
    {"task_id": "press_button_probe", "joint_type": "slide", "axis": "1 0 0", "target": 0.013, "horizon": 180, "base": 0.20},
    {"task_id": "slide_track_probe", "joint_type": "slide", "axis": "1 0 0", "target": 0.033, "horizon": 280, "base": 0.21},
    {"task_id": "pick_place_bin_probe", "joint_type": "slide", "axis": "0 0 1", "target": 0.019, "horizon": 220, "base": 0.19},
    {"task_id": "pull_ring_probe", "joint_type": "slide", "axis": "1 0 0", "target": 0.021, "horizon": 240, "base": 0.18},
    {"task_id": "constrained_place_probe", "joint_type": "slide", "axis": "1 0 0", "target": 0.017, "horizon": 220, "base": 0.17},
    {"task_id": "tool_push_probe", "joint_type": "slide", "axis": "1 0 0", "target": 0.027, "horizon": 260, "base": 0.20},
    {"task_id": "rotate_object_probe", "joint_type": "hinge", "axis": "0 0 1", "target": 0.065, "horizon": 260, "base": 0.28},
]

MUJOCO_PLANAR_XML = """
<mujoco model="bodyshield_planar_effector">
  <option timestep="0.004" gravity="0 0 0" integrator="Euler"/>
  <worldbody>
    <body name="ee" pos="0 0 0">
      <joint name="x" type="slide" axis="1 0 0" damping="{damping}" armature="{armature}" limited="true" range="{joint_min} {joint_max}"/>
      <joint name="y" type="slide" axis="0 1 0" damping="{damping}" armature="{armature}" limited="true" range="{joint_min} {joint_max}"/>
      <geom name="ee_geom" type="sphere" size="0.02" mass="{mass}" rgba="0.1 0.45 0.75 1"/>
    </body>
  </worldbody>
  <actuator>
    <motor name="x_motor" joint="x" gear="1.0"/>
    <motor name="y_motor" joint="y" gear="1.0"/>
  </actuator>
</mujoco>
"""

MUJOCO_PLANAR_TASKS = [
    {"task_id": "planar_reach_left", "target": np.array([0.24, 0.18]), "horizon": 260, "tolerance": 0.115},
    {"task_id": "planar_reach_right", "target": np.array([-0.22, 0.20]), "horizon": 260, "tolerance": 0.115},
    {"task_id": "planar_diagonal_reach", "target": np.array([0.26, -0.21]), "horizon": 300, "tolerance": 0.125},
    {"task_id": "planar_obstacle_reach", "target": np.array([0.32, 0.10]), "horizon": 300, "tolerance": 0.105},
]


def _policy_control(policy: Policy, perturbation: Perturbation, step: int, rng: np.random.Generator, base_control: float) -> float:
    sev = perturbation.severity_vector()
    stress = sum(policy.sensitivity.get(axis, 1.0) * value for axis, value in sev.items())
    base = base_control / (1.0 + 0.70 * stress)
    speed_cap = max(0.20, float(perturbation.canonical()["speed_cap_scale"]))
    accel_cap = max(0.20, float(perturbation.canonical()["acceleration_cap_scale"]))
    controller_rate = max(0.20, float(perturbation.canonical()["controller_rate_scale"]))
    if controller_rate < 1.0 and step % max(1, int(round(1.0 / controller_rate))) != 0:
        base *= 0.65
    noise = rng.normal(0.0, perturbation.canonical()["action_noise_std"] * 2.5)
    return float(np.clip((base + noise) * speed_cap * accel_cap, 0.0, 0.25))


def _planar_command(
    policy: Policy,
    perturbation: Perturbation,
    qpos: np.ndarray,
    target: np.ndarray,
    previous: np.ndarray,
    step: int,
    rng: np.random.Generator,
) -> np.ndarray:
    sev = perturbation.severity_vector()
    stress = sum(policy.sensitivity.get(axis, 1.0) * value for axis, value in sev.items())
    rate_scale = max(0.20, float(perturbation.canonical()["controller_rate_scale"]))
    update_period = max(1, int(round(1.0 / rate_scale)))
    if step % update_period != 0:
        return previous

    target = np.asarray(target, dtype=float).copy()
    target += perturbation.severity("calibration_offset_mm") * np.array([0.22, -0.16])
    target += perturbation.severity("camera_shift_px") * np.array([-0.18, 0.12])
    speed = max(0.18, float(perturbation.canonical()["speed_cap_scale"]))
    accel = max(0.18, float(perturbation.canonical()["acceleration_cap_scale"]))
    max_delta = (0.040 * speed * accel) / (1.0 + 0.55 * stress)
    desired = qpos + np.clip(target - qpos, -max_delta, max_delta)
    noise = rng.normal(0.0, perturbation.canonical()["action_noise_std"] * 5.0, size=2)
    command = desired + noise
    return command


def run_mujoco_task_suite(policies: dict[str, Policy], seeds: int = 4, task_ids: set[str] | None = None) -> list[dict[str, Any]]:
    import mujoco

    perturbations = [
        ("nominal", Perturbation()),
        ("latency", Perturbation({"latency_ms": 80})),
        ("action_noise", Perturbation({"action_noise_std": 0.02})),
        ("speed_accel_cap", Perturbation({"speed_cap_scale": 0.5, "acceleration_cap_scale": 0.5})),
        ("payload", Perturbation({"payload_g": 250})),
        ("obstacle", Perturbation({"obstacle_clearance_cm": 5})),
        ("compound", Perturbation({"latency_ms": 80, "action_noise_std": 0.01, "controller_rate_scale": 0.5})),
    ]
    methods = [
        method_id
        for method_id in ["nominal", "random_tuning", "domain_randomization", "grid_worstcase", "robust_control", "bodyshield", "oracle"]
        if method_id in policies
    ]
    rows: list[dict[str, Any]] = []
    selected_tasks = [task for task in MUJOCO_TASKS if task_ids is None or task["task_id"] in task_ids]
    for task in selected_tasks:
        for method_id in methods:
            policy = policies[method_id]
            for family, perturbation in perturbations:
                successes = 0
                final_progress: list[float] = []
                for seed in range(seeds):
                    rng = np.random.default_rng(seed + len(method_id) * 101 + len(task["task_id"]) * 17)
                    mass = 1.0 + perturbation.severity("payload_g") * 0.9
                    damping = (
                        0.25
                        + perturbation.severity("friction_surface") * 1.5
                        + perturbation.severity("obstacle_clearance_cm") * 0.6
                    )
                    model = mujoco.MjModel.from_xml_string(
                        MUJOCO_XML.format(
                            task_id=task["task_id"],
                            joint_type=task["joint_type"],
                            axis=task["axis"],
                            mass=mass,
                            damping=damping,
                        )
                    )
                    data = mujoco.MjData(model)
                    latency_steps = int(round(float(perturbation.canonical()["latency_ms"]) / 10.0))
                    queue = [0.0 for _ in range(latency_steps + 1)]
                    for step in range(int(task["horizon"])):
                        command = _policy_control(policy, perturbation, step, rng, float(task["base"]))
                        queue.append(command)
                        data.ctrl[0] = queue.pop(0)
                        mujoco.mj_step(model, data)
                    progress = abs(float(data.qpos[0]))
                    final_progress.append(progress)
                    successes += int(progress >= float(task["target"]))
                rows.append(
                    {
                        "engine": "mujoco",
                        "task_id": task["task_id"],
                        "method_id": method_id,
                        "perturbation_family": family,
                        "n": seeds,
                        "success_rate": successes / seeds,
                        "mean_final_progress": float(np.mean(final_progress)),
                        "min_final_progress": float(np.min(final_progress)),
                        "max_final_progress": float(np.max(final_progress)),
                        "notes": "Bounded MuJoCo 1-DOF task-shaped dynamics probe; not a full robot benchmark.",
                    }
                )
    return rows


def run_mujoco_planar_arm_suite(policies: dict[str, Policy], seeds: int = 4) -> list[dict[str, Any]]:
    import mujoco

    perturbations = [
        ("nominal", Perturbation()),
        ("latency", Perturbation({"latency_ms": 80})),
        ("action_noise", Perturbation({"action_noise_std": 0.02})),
        ("joint_range", Perturbation({"joint_range_scale": 0.65})),
        ("speed_accel_cap", Perturbation({"speed_cap_scale": 0.5, "acceleration_cap_scale": 0.5})),
        ("payload", Perturbation({"payload_g": 250})),
        ("compound", Perturbation({"latency_ms": 80, "action_noise_std": 0.01, "joint_range_scale": 0.75})),
    ]
    methods = [
        method_id
        for method_id in ["nominal", "random_tuning", "domain_randomization", "grid_worstcase", "robust_control", "bodyshield", "oracle"]
        if method_id in policies
    ]
    rows: list[dict[str, Any]] = []
    for task in MUJOCO_PLANAR_TASKS:
        target = np.asarray(task["target"], dtype=float)
        for method_id in methods:
            policy = policies[method_id]
            for family, perturbation in perturbations:
                successes = 0
                final_errors: list[float] = []
                for seed in range(seeds):
                    rng = np.random.default_rng(7000 + seed + len(method_id) * 113 + len(task["task_id"]) * 19)
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
                    data = mujoco.MjData(model)
                    latency_steps = int(round(float(perturbation.canonical()["latency_ms"]) / 12.0))
                    previous = np.zeros(2, dtype=float)
                    queue = [previous.copy() for _ in range(latency_steps + 1)]
                    for step in range(int(task["horizon"])):
                        command = _planar_command(
                            policy,
                            perturbation,
                            np.asarray(data.qpos[:2], dtype=float),
                            target,
                            previous,
                            step,
                            rng,
                        )
                        previous = command
                        queue.append(command.copy())
                        delayed = queue.pop(0)
                        qpos = np.asarray(data.qpos[:2], dtype=float)
                        qvel = np.asarray(data.qvel[:2], dtype=float)
                        gain = 5.2 / (1.0 + 0.55 * perturbation.severity("payload_g"))
                        damping_gain = 1.1 + 0.6 * perturbation.severity("friction_surface")
                        data.ctrl[:] = np.clip(gain * (delayed - qpos) - damping_gain * qvel, -2.5, 2.5)
                        mujoco.mj_step(model, data)
                    final_error = float(np.linalg.norm(np.asarray(data.qpos[:2], dtype=float) - target))
                    final_errors.append(final_error)
                    successes += int(final_error <= float(task["tolerance"]))
                rows.append(
                    {
                        "engine": "mujoco_planar",
                        "task_id": task["task_id"],
                        "method_id": method_id,
                        "perturbation_family": family,
                        "n": seeds,
                        "success_rate": successes / seeds,
                        "mean_final_error": float(np.mean(final_errors)),
                        "min_final_error": float(np.min(final_errors)),
                        "max_final_error": float(np.max(final_errors)),
                        "notes": "Bounded MuJoCo 2-DOF closed-loop planar end-effector probe; not a full robot benchmark.",
                    }
                )
    return rows


def run_mujoco_push_probe(policies: dict[str, Policy], seeds: int = 8) -> list[dict[str, Any]]:
    return run_mujoco_task_suite(policies, seeds=seeds, task_ids={"push_block_probe"})


def run_maniskill_task_suite(seed: int = 0, steps: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stderr_buffer = io.StringIO()
    task_ids = ["PushCube-v1", "PickCube-v1", "PullCube-v1", "PullCubeTool-v1", "PokeCube-v1", "StackCube-v1"]
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            import gymnasium as gym
            import mani_skill.envs  # noqa: F401

            for task_id in task_ids:
                rewards = []
                success_flags = []
                env = gym.make(task_id, obs_mode="state", control_mode="pd_joint_delta_pos", render_mode=None, num_envs=1)
                env.reset(seed=seed)
                terminated_any = False
                truncated_any = False
                for _ in range(steps):
                    _, reward, terminated, truncated, info = env.step(env.action_space.sample())
                    rewards.append(float(np.asarray(reward).mean()))
                    terminated_any = terminated_any or bool(np.asarray(terminated).any())
                    truncated_any = truncated_any or bool(np.asarray(truncated).any())
                    if isinstance(info, dict) and "success" in info:
                        success_flags.append(bool(np.asarray(info["success"]).any()))
                env.close()
                rows.append(
                    {
                        "engine": "maniskill",
                        "task_id": task_id,
                        "control_mode": "pd_joint_delta_pos",
                        "status": "executed",
                        "steps": steps,
                        "mean_reward": float(np.mean(rewards)),
                        "success_observed": bool(any(success_flags)) if success_flags else False,
                        "terminated_or_truncated": bool(terminated_any or truncated_any),
                        "notes": "CPU random-action compatibility benchmark; not a trained policy result.",
                    }
                )
        captured = " ".join(stderr_buffer.getvalue().split())
        captured = re.sub(r"\x1b\[[0-9;]*m", "", captured)
        warning_summary: list[str] = []
        if "pinnochio" in captured.lower() or "pinocchio" in captured.lower():
            warning_summary.append("pinocchio package unavailable for IK controllers")
        if "cuda" in captured.lower() and "cpu" in captured.lower():
            warning_summary.append("CUDA unavailable; CPU fallback used")
        if warning_summary:
            for row in rows:
                row["notes"] += f" Warning summary: {'; '.join(warning_summary)}."
    except Exception as exc:  # pragma: no cover - depends on local simulator install
        rows.append(
            {
                "engine": "maniskill",
                "task_id": "PushCube-v1",
                "control_mode": "pd_joint_delta_pos",
                "status": "failed",
                "steps": 0,
                "mean_reward": float("nan"),
                "success_observed": False,
                "terminated_or_truncated": False,
                "notes": f"{type(exc).__name__}: {exc}",
            }
        )
    return rows


def run_maniskill_pushcube_probe(seed: int = 0, steps: int = 5) -> list[dict[str, Any]]:
    return [row for row in run_maniskill_task_suite(seed=seed, steps=steps) if row["task_id"] == "PushCube-v1"]
