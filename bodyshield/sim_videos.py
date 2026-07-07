"""Synthetic rollout video exports for non-hardware BodyShield reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

from .perturbations import Perturbation
from .policies import Policy
from .sim import ROBOTS, TASKS, RobotSpec, TaskSpec, success_probability
from .trajectory_wam import generate_synthetic_trajectory
from .visual_wam import render_synthetic_visual_frame


def _frame_to_image(frame: np.ndarray, label: str, scale: int = 6) -> Image.Image:
    """Convert the tiny synthetic two-channel observation into a labeled RGB frame."""

    object_channel = np.clip(frame[0], 0.0, 1.0)
    target_channel = np.clip(frame[1], 0.0, 1.0)
    height, width = object_channel.shape
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[:, :, 0] = np.clip(248 - 90 * object_channel + 5 * target_channel, 0, 255).astype(np.uint8)
    rgb[:, :, 1] = np.clip(250 - 35 * object_channel - 105 * target_channel, 0, 255).astype(np.uint8)
    rgb[:, :, 2] = np.clip(250 - 80 * target_channel + 25 * object_channel, 0, 255).astype(np.uint8)
    image = Image.fromarray(rgb).resize((width * scale, height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (image.width, image.height + 24), (255, 255, 255))
    canvas.paste(image, (0, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((6, 6), label[:76], fill=(17, 24, 39))
    draw.rectangle((6, canvas.height - 16, 70, canvas.height - 9), fill=(15, 118, 110))
    draw.text((76, canvas.height - 19), "object", fill=(17, 24, 39))
    draw.rectangle((142, canvas.height - 16, 206, canvas.height - 9), fill=(204, 102, 119))
    draw.text((212, canvas.height - 19), "target/obstacle", fill=(17, 24, 39))
    return canvas


def _case_task_robot(case: dict[str, Any]) -> tuple[TaskSpec, RobotSpec, Perturbation]:
    tasks = {task.task_id: task for task in TASKS}
    robots = {robot.robot_id: robot for robot in ROBOTS}
    task = tasks.get(str(case.get("task_id", "constrained_place")), tasks["constrained_place"])
    robot = robots.get(str(case.get("robot_id", "so101_urdf")), robots["so101_urdf"])
    perturbation = case.get("perturbation")
    if not isinstance(perturbation, Perturbation):
        perturbation = Perturbation({"calibration_offset_mm": 20, "action_noise_std": 0.02})
    return task, robot, perturbation


def export_synthetic_rollout_videos(
    policies: dict[str, Policy],
    breaking_cases: list[dict[str, Any]],
    out_dir: Path,
    steps: int = 18,
    frame_size: int = 40,
) -> pd.DataFrame:
    """Write small synthetic GIF rollouts and return an auditable manifest.

    These media files are generated observations from the local trajectory and
    visual proxy, not real camera video or hardware evidence.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("bodyshield_synthetic_*.gif"):
        stale.unlink()

    break_case = min(breaking_cases, key=lambda row: float(row.get("cost", float("inf")))) if breaking_cases else {}
    break_task, break_robot, break_perturbation = _case_task_robot(break_case)
    nominal_task = next(task for task in TASKS if task.task_id == "push_block")
    nominal_robot = next(robot for robot in ROBOTS if robot.robot_id == "so101_urdf")
    specs = [
        ("nominal_reference", "nominal", nominal_task, nominal_robot, Perturbation(), "Nominal synthetic reference"),
        ("bodybreak_failure", "nominal", break_task, break_robot, break_perturbation, "Nominal policy under BodyBreak perturbation"),
        ("bodyshield_repair", "bodyshield", break_task, break_robot, break_perturbation, "BodyShield policy under same perturbation"),
    ]

    rows: list[dict[str, Any]] = []
    for artifact_id, method_id, task, robot, perturbation, description in specs:
        if method_id not in policies:
            continue
        policy = policies[method_id]
        trajectory = generate_synthetic_trajectory(policy, task, robot, perturbation, steps=steps)
        success = success_probability(policy, task, robot, perturbation)
        initial_error = float(np.linalg.norm(trajectory["states"][0, :2] - trajectory["target"]))
        images: list[Image.Image] = []
        for index, state in enumerate(trajectory["states"]):
            frame = render_synthetic_visual_frame(state, trajectory["target"], task, perturbation, frame_size=frame_size)
            label = f"{artifact_id} | t={index:02d}/{steps} | p={success:.3f} | err={trajectory['final_error']:.3f}"
            images.append(_frame_to_image(frame, label))
        gif_path = out_dir / f"bodyshield_synthetic_{artifact_id}.gif"
        images[0].save(gif_path, save_all=True, append_images=images[1:], duration=120, loop=0)
        try:
            report_path = gif_path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            report_path = gif_path.as_posix()
        rows.append(
            {
                "artifact_id": artifact_id,
                "path": report_path,
                "method_id": method_id,
                "task_id": task.task_id,
                "robot_id": robot.robot_id,
                "perturbation": perturbation.label(),
                "frames": len(images),
                "frame_size_px": frame_size,
                "success_probability": float(success),
                "initial_error": initial_error,
                "final_error": float(trajectory["final_error"]),
                "progress": float(trajectory["progress"]),
                "description": description,
                "evidence_boundary": "Synthetic generated rollout only; not real video, camera verification, hardware, or physical transfer evidence.",
            }
        )
    return pd.DataFrame(rows)
