"""Execute the BodyShield non-hardware workflow end to end."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.bodybreak_search import compare_search_modes, find_minimal_breaking_perturbation
from bodyshield.bodyshield_repair import repair_policy
from bodyshield.artifact_inventory_audit import write_artifact_inventory_audit_reports
from bodyshield.claim_boundary_audit import write_claim_boundary_reports
from bodyshield.command_surface_audit import write_command_surface_reports
from bodyshield.config_schema_audit import write_config_schema_audit_reports
from bodyshield.corrective_adaptation import fit_corrective_trace_adapter
from bodyshield.corrective_trace_readiness import (
    readiness_summary as corrective_trace_readiness_summary,
    run_corrective_trace_readiness,
    write_corrective_trace_readiness_report,
)
from bodyshield.external_policy_benchmark import (
    readiness_summary as external_policy_readiness_summary,
    run_external_policy_benchmark,
    write_external_policy_benchmark_report,
)
from bodyshield.evidence_consistency import write_evidence_consistency_reports
from bodyshield.derived_results_audit import write_derived_results_audit_reports
from bodyshield.environment_audit import write_environment_dependency_reports
from bodyshield.results_integrity import write_results_integrity_reports
from bodyshield.source_import_audit import write_source_import_audit_reports
from bodyshield.high_fidelity import run_maniskill_task_suite, run_mujoco_planar_arm_suite, run_mujoco_task_suite
from bodyshield.high_fidelity_learning import fit_mujoco_planar_residual_policy
from bodyshield.learned_outcome_model import fit_learned_outcome_model
from bodyshield.neural_wam import fit_neural_latent_wam
from bodyshield.paper_source_audit import write_paper_source_audit_reports
from bodyshield.perturbations import (
    AXES,
    Perturbation,
    axis_level_perturbations,
    candidate_grid,
    dedupe_perturbations,
    heldout_perturbations,
    random_candidates,
)
from bodyshield.plotting import (
    plot_bodybreak_minimality_audit,
    plot_corrective_adaptation_summary,
    plot_high_fidelity_summary,
    plot_mechanism_diagram,
    plot_mujoco_residual_gate_ablation,
    plot_mujoco_residual_policy_summary,
    plot_neural_wam_summary,
    plot_nominal_vs_radius,
    plot_repair_summary,
    plot_search_comparison,
    plot_trajectory_wam_summary,
    plot_visual_wam_summary,
)
from bodyshield.policies import default_policies
from bodyshield.pack_verification import write_verification_reports
from bodyshield.portable_hygiene_audit import write_portable_hygiene_audit_reports
from bodyshield.real_video_wam_readiness import (
    readiness_summary as real_video_wam_readiness_summary,
    run_real_video_wam_readiness,
    write_real_video_wam_readiness_report,
)
from bodyshield.release_bundle import write_release_bundle
from bodyshield.release_determinism_audit import write_release_determinism_audit_reports
from bodyshield.release_payload_audit import write_release_payload_audit_reports
from bodyshield.release_runtime_audit import write_release_runtime_audit_reports
from bodyshield.schema import TRIAL_JSON_SCHEMA, validate_trial, validate_trial_jsonschema
from bodyshield.sim import ROBOTS, TASKS, evaluate_rate, stable_seed, success_probability, trial_records
from bodyshield.sim_envs import check_sim_envs
from bodyshield.sim_videos import export_synthetic_rollout_videos
from bodyshield.stats import bootstrap_mean_ci, profile_auc, wilson_interval
from bodyshield.trajectory_wam import fit_trajectory_wam_proxy
from bodyshield.visual_artifact_audit import write_visual_artifact_reports
from bodyshield.visual_wam import fit_visual_wam_proxy
from bodyshield.tasks import task_cards_as_rows


RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
VIDEOS = RESULTS / "videos"
REPORTS = ROOT / "reports"
PAPER = ROOT / "paper"
CONFIGS = ROOT / "configs"
RELEASE = ROOT / "release"
JSONL_SAMPLE_LIMIT = 2000
SEARCH_EVALUATOR = "deterministic analytic success probability"
SEARCH_BUDGET_CAP = 200
THRESHOLD_SEARCH_BUDGET_CAP = 150
DENSE_AUDIT_CONFIRM_TRIALS = 320

COMPLETION_MESSAGE = (
    "NON-HARDWARE COMPLETE: BodyShield software, simulation, baselines, perturbation search, repair algorithms, "
    "analysis scripts, paper skeleton, verified citation table, and reviewer-defense reports are finished. Hardware "
    "phase is next. Do not proceed until the user confirms the SO-ARM101/SO-101 robot setup, safety gate, camera "
    "verifier, and emergency stop are ready."
)


def tree_hash() -> str:
    digest = hashlib.sha256()
    include_roots = [ROOT / "bodyshield", ROOT / "scripts", ROOT / "tests", ROOT / "configs", ROOT / "pyproject.toml"]
    files: list[Path] = []
    for item in include_roots:
        if item.is_file():
            files.append(item)
        elif item.exists():
            files.extend(
                path
                for path in item.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and ".pytest_cache" not in path.parts
                and path.suffix not in {".pyc", ".pyo"}
            )
    for path in sorted(files):
        digest.update(str(path.relative_to(ROOT)).replace("\\", "/").encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def condition_set() -> list[dict[str, Any]]:
    seen_axes = {
        "nominal",
        "latency_ms",
        "action_noise_std",
        "joint_range_scale",
        "gripper_limit_scale",
        "speed_cap_scale",
        "acceleration_cap_scale",
        "calibration_offset_mm",
        "controller_rate_scale",
    }
    conditions = []
    for family, level, perturbation in axis_level_perturbations():
        if family in seen_axes:
            bucket = "nominal" if family == "nominal" else "seen"
        else:
            bucket = "heldout"
        conditions.append({"family": family, "level": level, "bucket": bucket, "perturbation": perturbation})
    for family, level, perturbation in heldout_perturbations():
        conditions.append({"family": family, "level": level, "bucket": "heldout", "perturbation": perturbation})
    conditions.append(
        {
            "family": "compound_train",
            "level": "seen_compound",
            "bucket": "seen",
            "perturbation": Perturbation({"latency_ms": 80, "action_noise_std": 0.01, "calibration_offset_mm": 10}),
        }
    )
    return conditions


def flatten_trial(record: dict[str, Any], family: str, level: str, bucket: str, cost: float) -> dict[str, Any]:
    return {
        "trial_id": record["trial_id"],
        "phase": record["phase"],
        "task_id": record["task_id"],
        "robot_id": record["robot_id"],
        "method_id": record["method_id"],
        "perturbation_family": family,
        "level": level,
        "bucket": bucket,
        "perturbation_cost": cost,
        "success": int(record["result"]["success"]),
        "failure_category": record["result"]["failure_category"] or "",
        "execution_time_s": record["result"]["execution_time_s"],
        "path_length_m": record["result"]["path_length_m"],
        "retries": record["result"]["retries"],
        "max_tracking_error": record["safety"]["max_tracking_error"],
        "max_current_or_load": record["safety"]["max_current_or_load"],
        "workspace_violation": int(record["safety"]["workspace_violation"]),
        "latency_ms": record["perturbation"]["latency_ms"],
        "action_noise_std": record["perturbation"]["action_noise_std"],
        "joint_range_scale": record["perturbation"]["joint_range_scale"],
        "gripper_limit_scale": record["perturbation"]["gripper_limit_scale"],
        "speed_cap_scale": record["perturbation"]["speed_cap_scale"],
        "acceleration_cap_scale": record["perturbation"]["acceleration_cap_scale"],
        "calibration_offset_mm": record["perturbation"]["calibration_offset_mm"],
        "camera_shift_px": record["perturbation"]["camera_shift_px"],
        "controller_rate_scale": record["perturbation"]["controller_rate_scale"],
        "payload_g": record["perturbation"]["payload_g"],
        "tool_extension_cm": record["perturbation"]["tool_extension_cm"],
        "physical_gripper_restriction_mm": record["perturbation"]["physical_gripper_restriction_mm"],
        "obstacle_clearance_cm": record["perturbation"]["obstacle_clearance_cm"],
        "friction_surface": record["perturbation"]["friction_surface"] or "",
        "verifier_confidence": record["verifier"]["confidence"],
        "notes": record["metadata"]["notes"],
    }


def run_searches(policies: dict[str, Any]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    breaking_cases: list[dict[str, Any]] = []
    search_robots = [robot for robot in ROBOTS if robot.robot_id in {"so101_urdf", "widowx250_like", "franka_panda"}]
    search_methods = ["nominal", "human_effect_prior", "epec"]
    for method_id in search_methods:
        policy = policies[method_id]
        for task in TASKS:
            for robot in search_robots:
                def evaluator(z: Perturbation, policy=policy, task=task, robot=robot) -> float:
                    return success_probability(policy, task, robot, z)

                results = compare_search_modes(
                    evaluator,
                    threshold=0.50,
                    seed=stable_seed(method_id, task.task_id, robot.robot_id),
                    budget=SEARCH_BUDGET_CAP,
                )
                for mode, result in results.items():
                    rows.append(
                        {
                            "method_id": method_id,
                            "task_id": task.task_id,
                            "robot_id": robot.robot_id,
                            "search_mode": mode,
                            "breaking_cost": result.cost,
                            "success_rate": result.success_rate,
                            "trials": result.trials,
                            "perturbation": result.perturbation.label(),
                            "active_axes": ",".join(result.perturbation.active_axes()),
                            "notes": result.notes,
                        }
                    )
                bodybreak = results["bodybreak"]
                if method_id == "nominal" and bodybreak.success_rate <= 0.55:
                    breaking_cases.append(
                        {
                            "task_id": task.task_id,
                            "robot_id": robot.robot_id,
                            "perturbation": bodybreak.perturbation,
                            "success_rate": bodybreak.success_rate,
                            "cost": bodybreak.cost,
                        }
                    )
    return pd.DataFrame(rows), breaking_cases


def parse_perturbation_label(label: str) -> Perturbation:
    if not label or label == "nominal":
        return Perturbation()
    values: dict[str, Any] = {}
    for part in str(label).split(";"):
        if not part:
            continue
        axis, raw = part.split("=", 1)
        if axis not in AXES:
            raise ValueError(f"unknown perturbation axis in label: {axis}")
        if raw in {"", "None", "none", "null"}:
            values[axis] = None
        elif axis in {"joint_lock", "friction_surface"}:
            values[axis] = raw
        else:
            values[axis] = float(raw)
    return Perturbation(values)


def scale_perturbation_toward_nominal(z: Perturbation, factor: float) -> Perturbation:
    values: dict[str, Any] = {}
    for axis in z.active_axes():
        value = z.canonical()[axis]
        if axis in {"joint_range_scale", "gripper_limit_scale", "speed_cap_scale", "acceleration_cap_scale", "controller_rate_scale"}:
            values[axis] = 1.0 - (1.0 - float(value)) * factor
        elif axis in {"joint_lock", "friction_surface"}:
            values[axis] = value if factor >= 1.0 else None
        else:
            values[axis] = float(value) * factor
    return Perturbation(values)


def dense_bodybreak_candidates(anchor: Perturbation, seed: int, random_budget: int = 192, scale_steps: int = 32) -> list[Perturbation]:
    factors = [float(value) for value in pd.Series([i / scale_steps for i in range(1, scale_steps + 1)]).unique()]
    candidates = list(candidate_grid())
    candidates.append(anchor)
    candidates.extend(scale_perturbation_toward_nominal(anchor, factor) for factor in factors)
    for axis in anchor.active_axes():
        axis_only = Perturbation({axis: anchor.canonical()[axis]})
        candidates.extend(scale_perturbation_toward_nominal(axis_only, factor) for factor in factors)
    candidates.extend(random_candidates(np.random.default_rng(seed), random_budget))
    return dedupe_perturbations(candidates)


def audit_bodybreak_minimality(
    search: pd.DataFrame,
    policies: dict[str, Any],
    threshold: float = 0.50,
    cases_per_method: int = 4,
    random_budget: int = 192,
    scale_steps: int = 32,
    confirm_trials: int = DENSE_AUDIT_CONFIRM_TRIALS,
) -> pd.DataFrame:
    """Challenge representative BodyBreak breaks with a larger deterministic candidate pool."""

    bodybreak = search[(search["search_mode"] == "bodybreak") & (search["notes"] == "found_break")].copy()
    if bodybreak.empty:
        return pd.DataFrame(
            columns=[
                "method_id",
                "task_id",
                "robot_id",
                "bodybreak_cost",
                "bodybreak_reported_success_rate",
                "bodybreak_audit_success_rate",
                "bodybreak_confirmed_success_rate",
                "bodybreak_perturbation",
                "dense_best_cost",
                "dense_best_success_rate",
                "dense_best_confirmed_success_rate",
                "dense_best_perturbation",
                "dense_candidate_count",
                "search_evaluator",
                "confirm_trials",
                "bodybreak_cost_regret",
                "bodybreak_relative_regret",
                "lower_cost_break_found",
                "audit_status",
            ]
        )
    selected = (
        bodybreak.sort_values(["method_id", "breaking_cost", "task_id", "robot_id"])
        .groupby("method_id", group_keys=False)
        .head(cases_per_method)
    )
    tasks = {task.task_id: task for task in TASKS}
    robots = {robot.robot_id: robot for robot in ROBOTS}
    rows: list[dict[str, Any]] = []
    for _, case in selected.iterrows():
        method_id = str(case["method_id"])
        task_id = str(case["task_id"])
        robot_id = str(case["robot_id"])
        policy = policies[method_id]
        task = tasks[task_id]
        robot = robots[robot_id]
        anchor = parse_perturbation_label(str(case["perturbation"]))
        seed = stable_seed("dense-bodybreak-candidates", method_id, task_id, robot_id)
        candidates = dense_bodybreak_candidates(anchor, seed=seed, random_budget=random_budget, scale_steps=scale_steps)
        best_break: tuple[float, Perturbation, float] | None = None
        for candidate in sorted(candidates, key=lambda z: z.cost()):
            rate = success_probability(policy, task, robot, candidate)
            confirmed_rate = evaluate_rate(
                policy,
                task,
                robot,
                candidate,
                n_trials=confirm_trials,
                seed=stable_seed("dense-bodybreak-confirm", method_id, task_id, robot_id, candidate.label()),
            )
            cost = candidate.cost()
            if rate <= threshold and confirmed_rate <= threshold and (best_break is None or cost < best_break[0]):
                best_break = (cost, candidate, confirmed_rate)
        bodybreak_audit_rate = success_probability(policy, task, robot, anchor)
        bodybreak_confirmed_rate = evaluate_rate(
            policy,
            task,
            robot,
            anchor,
            n_trials=confirm_trials,
            seed=stable_seed("dense-bodybreak-confirm", method_id, task_id, robot_id, anchor.label()),
        )
        bodybreak_cost = float(case["breaking_cost"])
        if best_break is None:
            dense_cost = float("nan")
            dense_rate = float("nan")
            dense_confirmed_rate = float("nan")
            dense_label = ""
            regret = float("nan")
            relative_regret = float("nan")
            lower_cost_break_found = False
            audit_status = "no_confirmed_dense_break_found"
        else:
            dense_cost, dense_candidate, dense_confirmed_rate = best_break
            dense_rate = success_probability(policy, task, robot, dense_candidate)
            dense_label = dense_candidate.label()
            regret = bodybreak_cost - dense_cost
            relative_regret = regret / max(bodybreak_cost, 1e-9)
            lower_cost_break_found = bool(dense_cost + 1e-12 < bodybreak_cost)
            if lower_cost_break_found:
                audit_status = "confirmed_lower_cost_break_found"
            elif bodybreak_confirmed_rate > threshold:
                audit_status = "no_lower_confirmed_break_bodybreak_not_confirmed"
            else:
                audit_status = "bodybreak_matches_confirmed_dense_pool"
        rows.append(
            {
                "method_id": method_id,
                "task_id": task_id,
                "robot_id": robot_id,
                "bodybreak_cost": bodybreak_cost,
                "bodybreak_reported_success_rate": float(case["success_rate"]),
                "bodybreak_audit_success_rate": float(bodybreak_audit_rate),
                "bodybreak_confirmed_success_rate": float(bodybreak_confirmed_rate),
                "bodybreak_perturbation": anchor.label(),
                "dense_best_cost": float(dense_cost),
                "dense_best_success_rate": float(dense_rate),
                "dense_best_confirmed_success_rate": float(dense_confirmed_rate),
                "dense_best_perturbation": dense_label,
                "dense_candidate_count": int(len(candidates)),
                "search_evaluator": SEARCH_EVALUATOR,
                "confirm_trials": int(confirm_trials),
                "bodybreak_cost_regret": float(regret),
                "bodybreak_relative_regret": float(relative_regret),
                "lower_cost_break_found": lower_cost_break_found,
                "audit_status": audit_status,
            }
        )
    return pd.DataFrame(rows)


def repair_bodyshield(policies: dict[str, Any], breaking_cases: list[dict[str, Any]]) -> tuple[dict[str, Any], pd.DataFrame]:
    if not breaking_cases:
        breaking_cases = [
            {
                "task_id": "push_block",
                "robot_id": "so101_urdf",
                "perturbation": Perturbation({"latency_ms": 120, "action_noise_std": 0.02}),
                "success_rate": 0.45,
                "cost": Perturbation({"latency_ms": 120, "action_noise_std": 0.02}).cost(),
            }
        ]
    train_tasks = [task for task in TASKS if task.task_id in {"push_block", "press_button", "pick_place_bin", "constrained_place"}]
    train_robots = [robot for robot in ROBOTS if robot.robot_id in {"so101_urdf", "widowx250_like"}]

    def evaluator(candidate, z: Perturbation) -> float:
        rates = [
            evaluate_rate(
                candidate,
                task,
                robot,
                z,
                n_trials=35,
                seed=stable_seed("repair", candidate.method_id, task.task_id, robot.robot_id, z.label()),
            )
            for task in train_tasks
            for robot in train_robots
        ]
        return float(sum(rates) / len(rates))

    result = repair_policy(policies["nominal"], breaking_cases, evaluator=evaluator, budget=160, seed=17)
    policies = dict(policies)
    policies["bodyshield"] = result.policy
    history = pd.DataFrame(result.history)
    axis_rows = pd.DataFrame(
        [{"axis": axis, "importance": value, "bodyshield_sensitivity": result.policy.sensitivity[axis]} for axis, value in result.axis_importance.items()]
    )
    history.to_csv(RESULTS / "repair_history.csv", index=False)
    axis_rows.to_csv(RESULTS / "repair_axis_importance.csv", index=False)
    return policies, history


def run_trials(policies: dict[str, Any], code_version: str) -> tuple[pd.DataFrame, Path]:
    conditions = condition_set()
    flat_rows: list[dict[str, Any]] = []
    stale_full_jsonl = RESULTS / "trials.jsonl"
    if stale_full_jsonl.exists():
        stale_full_jsonl.unlink()
    jsonl_path = RESULTS / "trials_sample.jsonl"
    sample_written = 0
    jsonschema_checked = 0
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for method_id, policy in policies.items():
            for task in TASKS:
                for robot in ROBOTS:
                    for condition in conditions:
                        perturbation = condition["perturbation"]
                        records = trial_records(
                            policy,
                            task,
                            robot,
                            perturbation,
                            n_trials=50,
                            seed=stable_seed("trial", method_id, task.task_id, robot.robot_id, perturbation.label()),
                        )
                        for record in records:
                            record["metadata"]["code_commit_hash"] = code_version
                            validate_trial(record)
                            if sample_written < JSONL_SAMPLE_LIMIT:
                                if jsonschema_checked < 200:
                                    validate_trial_jsonschema(record)
                                    jsonschema_checked += 1
                                handle.write(json.dumps(record, sort_keys=True) + "\n")
                                sample_written += 1
                            flat_rows.append(
                                flatten_trial(
                                    record,
                                    condition["family"],
                                    condition["level"],
                                    condition["bucket"],
                                    perturbation.cost(),
                                )
                            )
    df = pd.DataFrame(flat_rows)
    df.to_csv(RESULTS / "trials.csv", index=False)
    try:
        df.to_parquet(RESULTS / "trials.parquet", index=False, compression="zstd")
        parquet_status = "written"
    except Exception as exc:  # pragma: no cover - depends on pyarrow install
        parquet_status = f"failed: {type(exc).__name__}: {exc}"
    (RESULTS / "schema_validation_summary.json").write_text(
        json.dumps(
            {
                "lightweight_validated_records": int(len(flat_rows)),
                "jsonschema_validated_sample_records": jsonschema_checked,
                "trial_json_schema_path": "trial_schema.schema.json",
                "parquet_status": parquet_status,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return df, jsonl_path


def summarize_trials(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for keys, group in df.groupby(["method_id", "bucket"]):
        method_id, bucket = keys
        successes = int(group["success"].sum())
        n = int(len(group))
        lo, hi = wilson_interval(successes, n)
        rows.append(
            {
                "method_id": method_id,
                "bucket": bucket,
                "n": n,
                "successes": successes,
                "success_rate": successes / n,
                "ci_low": lo,
                "ci_high": hi,
                "mean_execution_time_s": group["execution_time_s"].mean(),
                "mean_path_length_m": group["path_length_m"].mean(),
                "mean_retries": group["retries"].mean(),
                "workspace_violation_rate": group["workspace_violation"].mean(),
            }
        )
    summary = pd.DataFrame(rows)
    summary.to_csv(RESULTS / "summary_by_method_bucket.csv", index=False)

    profile_rows = []
    for keys, group in df.groupby(["method_id", "perturbation_family"]):
        method_id, family = keys
        by_cost = group.groupby("perturbation_cost")["success"].mean().reset_index()
        auc = profile_auc(by_cost["perturbation_cost"], by_cost["success"])
        lo, hi = bootstrap_mean_ci(by_cost["success"], seed=stable_seed("auc", method_id, family))
        profile_rows.append({"method_id": method_id, "perturbation_family": family, "profile_auc": auc, "bootstrap_low": lo, "bootstrap_high": hi})
    profiles = pd.DataFrame(profile_rows)
    profiles.to_csv(RESULTS / "robustness_profiles.csv", index=False)
    return summary, profiles


def summarize_secondary_metrics(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    for method_id, group in df.groupby("method_id"):
        metric_rows.append(
            {
                "method_id": method_id,
                "mean_execution_time_s": group["execution_time_s"].mean(),
                "mean_path_length_m": group["path_length_m"].mean(),
                "mean_retries": group["retries"].mean(),
                "mean_tracking_error": group["max_tracking_error"].mean(),
                "mean_current_or_load": group["max_current_or_load"].mean(),
                "workspace_violation_rate": group["workspace_violation"].mean(),
                "verifier_confidence": group["verifier_confidence"].mean(),
            }
        )
    failure_counts = (
        df[df["success"] == 0]
        .groupby(["method_id", "failure_category"], as_index=False)
        .size()
        .rename(columns={"size": "failures"})
    )
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(RESULTS / "secondary_metrics_by_method.csv", index=False)
    failure_counts.to_csv(RESULTS / "failure_taxonomy_counts.csv", index=False)
    return metrics, failure_counts


def compute_radius(policies: dict[str, Any]) -> pd.DataFrame:
    task = next(t for t in TASKS if t.task_id == "push_block")
    robot = next(r for r in ROBOTS if r.robot_id == "so101_urdf")
    rows = []
    for method_id, policy in policies.items():
        def evaluator(z: Perturbation, policy=policy) -> float:
            return evaluate_rate(
                policy,
                task,
                robot,
                z,
                n_trials=60,
                seed=stable_seed("radius", method_id, z.label()),
            )

        result = find_minimal_breaking_perturbation(
            policy,
            task,
            evaluator,
            threshold=0.50,
            budget=90,
            mode="bodybreak",
            seed=stable_seed("radius", method_id),
        )
        rows.append(
            {
                "method_id": method_id,
                "nominal_success": evaluator(Perturbation()),
                "robustness_radius": result.cost,
                "breaking_success_rate": result.success_rate,
                "breaking_perturbation": result.perturbation.label(),
            }
        )
    radius = pd.DataFrame(rows)
    radius.to_csv(RESULTS / "nominal_vs_robustness_radius.csv", index=False)
    return radius


def compute_threshold_sensitivity(policies: dict[str, Any]) -> pd.DataFrame:
    rows = []
    methods = ["nominal", "random_tuning", "domain_randomization", "grid_worstcase", "bodyshield"]
    search_robots = [robot for robot in ROBOTS if robot.robot_id in {"so101_urdf", "widowx250_like", "franka_panda"}]
    for method_id in methods:
        policy = policies[method_id]
        for task in TASKS:
            for robot in search_robots:
                nominal = evaluate_rate(
                    policy,
                    task,
                    robot,
                    Perturbation(),
                    n_trials=50,
                    seed=stable_seed("threshold-nominal", method_id, task.task_id, robot.robot_id),
                )
                thresholds = {
                    "absolute_50": 0.50,
                    "relative_drop_20": nominal * 0.80,
                    "relative_drop_30": nominal * 0.70,
                }
                for threshold_name, threshold in thresholds.items():
                    def evaluator(z: Perturbation, policy=policy, task=task, robot=robot, threshold_name=threshold_name) -> float:
                        del threshold_name
                        return success_probability(policy, task, robot, z)

                    result = find_minimal_breaking_perturbation(
                        policy,
                        task,
                        evaluator,
                        threshold=threshold,
                        budget=THRESHOLD_SEARCH_BUDGET_CAP,
                        mode="bodybreak",
                        seed=stable_seed("threshold", method_id, task.task_id, robot.robot_id, threshold_name),
                    )
                    rows.append(
                        {
                            "method_id": method_id,
                            "task_id": task.task_id,
                            "robot_id": robot.robot_id,
                            "threshold": threshold_name,
                            "threshold_value": threshold,
                            "nominal_success": nominal,
                            "breaking_cost": result.cost,
                            "breaking_success_rate": result.success_rate,
                            "trials": result.trials,
                            "notes": result.notes,
                            "perturbation": result.perturbation.label(),
                        }
                    )
    threshold_df = pd.DataFrame(rows)
    threshold_df.to_csv(RESULTS / "threshold_sensitivity.csv", index=False)
    return threshold_df


def compute_oracle_feasibility(search: pd.DataFrame, policies: dict[str, Any]) -> pd.DataFrame:
    rows = []
    oracle = policies["oracle"]
    task_by_id = {task.task_id: task for task in TASKS}
    robot_by_id = {robot.robot_id: robot for robot in ROBOTS}
    for _, row in search[(search["search_mode"] == "bodybreak") & (search["notes"] == "found_break")].iterrows():
        values: dict[str, Any] = {}
        for part in str(row["perturbation"]).split(";"):
            if not part or part == "nominal" or "=" not in part:
                continue
            key, value = part.split("=", 1)
            if value in {"None", "none", ""}:
                values[key] = None
            elif key == "friction_surface":
                values[key] = value
            else:
                values[key] = float(value)
        perturbation = Perturbation(values)
        task = task_by_id[row["task_id"]]
        robot = robot_by_id[row["robot_id"]]
        oracle_rate = evaluate_rate(
            oracle,
            task,
            robot,
            perturbation,
            n_trials=60,
            seed=stable_seed("oracle-feasibility", row["method_id"], task.task_id, robot.robot_id, perturbation.label()),
        )
        rows.append(
            {
                "broken_method": row["method_id"],
                "task_id": task.task_id,
                "robot_id": robot.robot_id,
                "perturbation": perturbation.label(),
                "broken_success_rate": row["success_rate"],
                "oracle_success_rate": oracle_rate,
                "feasible": oracle_rate >= 0.70,
            }
        )
    oracle_df = pd.DataFrame(rows)
    oracle_df.to_csv(RESULTS / "oracle_feasibility.csv", index=False)
    return oracle_df


def write_markdown_table(path: Path, df: pd.DataFrame, float_digits: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rounded = df.copy()
    for column in rounded.select_dtypes(include=["float"]).columns:
        rounded[column] = rounded[column].map(lambda x: f"{x:.{float_digits}f}")
    path.write_text(rounded.to_markdown(index=False), encoding="utf-8")


def write_artifact_manifest(code_version: str, include_release: bool = True) -> pd.DataFrame:
    roots = [RESULTS, REPORTS, PAPER]
    if include_release:
        roots.append(RELEASE)
    root_artifacts = [
        ROOT / "trial_schema.schema.json",
        ROOT / "data_schema.json",
        ROOT / "README_EXECUTION.md",
    ]
    rows = []
    excluded = {
        "ARTIFACT_MANIFEST.csv",
        "ARTIFACT_MANIFEST.md",
        "ARTIFACT_INVENTORY_AUDIT.md",
        "PACK_VERIFICATION.json",
        "PACK_VERIFICATION.md",
        "PORTABLE_HYGIENE_AUDIT.md",
        "RELEASE_DETERMINISM_AUDIT.md",
        "RELEASE_PAYLOAD_AUDIT.md",
        "RELEASE_RUNTIME_AUDIT.md",
        "artifact_inventory_audit.csv",
        "portable_hygiene_audit.csv",
        "release_determinism_audit.csv",
        "release_payload_audit.csv",
        "release_runtime_audit.csv",
    }

    def add_row(path: Path) -> None:
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
                "code_version": code_version,
                "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            }
        )

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path.name in excluded:
                continue
            add_row(path)
    for path in root_artifacts:
        if path.exists():
            add_row(path)
    df = pd.DataFrame(rows)
    df.to_csv(REPORTS / "ARTIFACT_MANIFEST.csv", index=False)
    write_markdown_table(REPORTS / "ARTIFACT_MANIFEST.md", df)
    return df


def _run_paper_command(cmd: list[str], log_parts: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180)
    log_parts.append(f"$ ({cwd}) " + " ".join(cmd))
    log_parts.append(completed.stdout)
    log_parts.append(completed.stderr)
    return completed


def _redact_local_paths(text: str) -> str:
    redacted = text
    replacements: list[tuple[str, str]] = []
    for path, token in ((ROOT, "<PACK_ROOT>"), (Path.home(), "<USER_HOME>")):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        replacements.append((str(resolved), token))
        replacements.append((resolved.as_posix(), token))
    for raw, token in sorted(set(replacements), key=lambda item: len(item[0]), reverse=True):
        if raw:
            redacted = redacted.replace(raw, token)
    redacted = re.sub(r"[A-Za-z]:[\\/]+Users[\\/][A-Za-z0-9_.-]+", "<USER_HOME>", redacted)
    redacted = re.sub(r"/home/[A-Za-z0-9_.-]+", "<USER_HOME>", redacted)
    redacted = re.sub(r"/Users/[A-Za-z0-9_.-]+", "<USER_HOME>", redacted)
    return redacted


def _write_paper_build_log(build_dir: Path, log_parts: list[str], success_message: str | None = None) -> None:
    final_log = build_dir / "main.log"
    if success_message and final_log.exists():
        log_text = final_log.read_text(encoding="utf-8", errors="ignore") + f"\n\n{success_message}\n"
        (REPORTS / "PAPER_BUILD_LOG.txt").write_text(_redact_local_paths(log_text), encoding="utf-8")
    else:
        (REPORTS / "PAPER_BUILD_LOG.txt").write_text(_redact_local_paths("\n".join(log_parts)), encoding="utf-8")


def _build_paper_with_pdflatex(build_dir: Path, output_pdf: Path, log_parts: list[str]) -> dict[str, str] | None:
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if not pdflatex:
        return None

    tex_path = PAPER / "main.tex"
    pdflatex_cmd = [pdflatex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build_dir}", str(tex_path)]
    passes = [pdflatex_cmd]
    if bibtex:
        shutil.copy2(PAPER / "references.bib", build_dir / "references.bib")
        passes.append([bibtex, "main"])
    passes.extend([pdflatex_cmd, pdflatex_cmd])

    for cmd in passes:
        cwd = build_dir if bibtex and cmd[0] == bibtex else ROOT
        completed = _run_paper_command(cmd, log_parts, cwd=cwd)
        if completed.returncode != 0:
            _write_paper_build_log(build_dir, log_parts)
            return {
                "status": "failed",
                "reason": f"{Path(cmd[0]).name} returned nonzero",
                "output": str(output_pdf.relative_to(ROOT)),
            }

    built_pdf = build_dir / "main.pdf"
    if built_pdf.exists():
        shutil.copy2(built_pdf, output_pdf)
        _write_paper_build_log(build_dir, log_parts, "PDF build succeeded with pdflatex/bibtex.")
        return {"status": "written", "reason": "pdflatex/bibtex succeeded", "output": str(output_pdf.relative_to(ROOT))}
    _write_paper_build_log(build_dir, log_parts)
    return {"status": "failed", "reason": "pdflatex fallback succeeded but main.pdf missing", "output": str(output_pdf.relative_to(ROOT))}


def build_paper_pdf() -> dict[str, str]:
    build_dir = PAPER / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    output_pdf = PAPER / "bodyshield_non_hardware_draft.pdf"
    log_parts: list[str] = []
    for generated in build_dir.glob("main.*"):
        generated.unlink()
    if output_pdf.exists():
        output_pdf.unlink()
    direct_build = _build_paper_with_pdflatex(build_dir, output_pdf, log_parts)
    if direct_build is not None:
        return direct_build

    latexmk = shutil.which("latexmk")
    if latexmk:
        cmd = [
            latexmk,
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-outdir={build_dir}",
            str(PAPER / "main.tex"),
        ]
        completed = _run_paper_command(cmd, log_parts)
        if completed.returncode == 0:
            built_pdf = build_dir / "main.pdf"
            if built_pdf.exists():
                shutil.copy2(built_pdf, output_pdf)
                _write_paper_build_log(build_dir, log_parts, "PDF build succeeded with latexmk.")
                return {"status": "written", "reason": "latexmk succeeded", "output": str(output_pdf.relative_to(ROOT))}
            log_parts.append("latexmk exited successfully but paper/build/main.pdf was not found.")

    _write_paper_build_log(build_dir, log_parts)
    return {"status": "skipped", "reason": "latexmk and pdflatex unavailable", "output": str(output_pdf.relative_to(ROOT))}


def completion_audit_rows() -> list[dict[str, str]]:
    return [
        {
            "phase": "phase_0_literature_and_claim_lock",
            "task": "verify_sources_and_citations",
            "status": "complete for planning sources",
            "evidence": "reports/CITATION_VERIFICATION_TABLE.md",
            "residual_risk": "Individual paper versions still require final citation refresh before submission.",
        },
        {
            "phase": "phase_0_literature_and_claim_lock",
            "task": "build_related_work_table",
            "status": "complete",
            "evidence": "reports/RELATED_WORK_TABLE.md",
            "residual_risk": "Related work is a scaffold, not a full final related-work section.",
        },
        {
            "phase": "phase_0_literature_and_claim_lock",
            "task": "write_claim_boundary_doc",
            "status": "complete",
            "evidence": "reports/CLAIM_BOUNDARY.md and reports/CLAIM_LEDGER.md",
            "residual_risk": "Claims remain analytic-simulation-only until high-fidelity/hardware evidence exists.",
        },
        {
            "phase": "phase_1_software_stack",
            "task": "implement_data_schema",
            "status": "complete",
            "evidence": "data_schema.json, trial_schema.schema.json, bodyshield/schema.py, results/schema_validation_summary.json",
            "residual_risk": "JSON Schema validates sampled nested records; full flat CSV is validated by the lightweight schema during generation.",
        },
        {
            "phase": "phase_1_software_stack",
            "task": "implement_perturbation_library",
            "status": "complete",
            "evidence": "bodyshield/perturbations.py",
            "residual_risk": "Real-world scale calibration awaits hardware measurements.",
        },
        {
            "phase": "phase_1_software_stack",
            "task": "implement_bodybreak_search",
            "status": "complete",
            "evidence": "bodyshield/bodybreak_search.py, results/breaking_search.csv, results/bodybreak_minimality_audit.csv, reports/BODYBREAK_MINIMALITY_AUDIT.md",
            "residual_risk": "Dense analytic audit challenges representative cases, but this is still not a mathematical global minimality proof or high-fidelity/hardware evaluator.",
        },
        {
            "phase": "phase_1_software_stack",
            "task": "implement_bodyshield_repair",
            "status": "complete",
            "evidence": "bodyshield/bodyshield_repair.py, results/repair_history.csv",
            "residual_risk": "Repair parameterization is CPU-friendly, not a learned neural policy update.",
        },
        {
            "phase": "phase_1_software_stack",
            "task": "implement_baselines",
            "status": "complete",
            "evidence": "bodyshield/policies.py includes 10 methods",
            "residual_risk": "Baselines are analytic policy families, not external controller implementations.",
        },
        {
            "phase": "phase_1_software_stack",
            "task": "implement_plotting",
            "status": "complete",
            "evidence": "bodyshield/plotting.py, results/figures/*.pdf",
            "residual_risk": "Figures are clean programmatic plots, not manually polished final-paper art.",
        },
        {
            "phase": "phase_1_software_stack",
            "task": "implement_stats",
            "status": "complete",
            "evidence": "bodyshield/stats.py, results/threshold_sensitivity.csv, results/robustness_profiles.csv",
            "residual_risk": "No paired hardware statistical tests until hardware logs exist.",
        },
        {
            "phase": "phase_2_simulation",
            "task": "setup_sim_envs",
            "status": "complete for local availability plus bounded simulator benchmark",
            "evidence": "reports/SIM_ENV_AVAILABILITY.md and results/high_fidelity_benchmark.csv",
            "residual_risk": "Bounded probes do not replace a full robot-policy benchmark suite.",
        },
        {
            "phase": "phase_2_simulation",
            "task": "external_policy_benchmark_readiness",
            "status": "complete for spec validation, checkpoint detection, and deterministic interface smoke",
            "evidence": "bodyshield/external_policy_benchmark.py, configs/external_policy_benchmark.example.json, results/external_policy_benchmark_readiness.csv, reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md",
            "residual_risk": "The included external checkpoint template is missing by design; no external trained-policy rollout benchmark evidence is claimed.",
        },
        {
            "phase": "phase_2_simulation",
            "task": "real_video_wam_readiness",
            "status": "complete for frame-manifest validation, missing-dataset detection, and deterministic fit smoke",
            "evidence": "bodyshield/real_video_wam_readiness.py, configs/real_video_wam_readiness.example.json, results/real_video_wam_readiness.csv, reports/REAL_VIDEO_WAM_READINESS.md",
            "residual_risk": "The included real-video dataset template is missing by design; no real-video or foundation-scale WAM evidence is claimed.",
        },
        {
            "phase": "phase_2_simulation",
            "task": "corrective_trace_readiness",
            "status": "complete for corrective-trace manifest validation, missing-dataset detection, and deterministic residual-fit smoke",
            "evidence": "bodyshield/corrective_trace_readiness.py, configs/corrective_trace_readiness.example.json, results/corrective_trace_readiness.csv, reports/CORRECTIVE_TRACE_READINESS.md",
            "residual_risk": "The included corrective-trace dataset template is missing by design; no real or external corrective-trace adaptation evidence is claimed.",
        },
        {
            "phase": "phase_2_simulation",
            "task": "train_mujoco_residual_policy",
            "status": "complete for local MuJoCo planar gated residual-policy audit",
            "evidence": "bodyshield/high_fidelity_learning.py, results/mujoco_residual_policy_eval.csv, results/mujoco_residual_policy_gate_ablation.csv, reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md",
            "residual_risk": "Still not an external neural checkpoint, full ManiSkill trained-policy suite, or hardware result.",
        },
        {
            "phase": "phase_2_simulation",
            "task": "run simulation/baseline/epec/bodyshield jobs",
            "status": "complete for analytic surrogate",
            "evidence": "results/trials.csv, results/summary_by_method_bucket.csv",
            "residual_risk": "Not high-fidelity physics evidence.",
        },
        {
            "phase": "phase_3_non_hardware_completion",
            "task": "generate paper/reviewer/citation/completion reports",
            "status": "complete",
            "evidence": "paper/main.tex, reports/*.md",
            "residual_risk": "Final paper must wait for hardware or a deliberate no-hardware submission decision.",
        },
        {
            "phase": "phase_7_submission_pack",
            "task": "final_tables",
            "status": "complete for analytic and bounded high-fidelity evidence",
            "evidence": "reports/*_TABLE.md",
            "residual_risk": "Hardware and full robot-policy benchmark tables are still absent.",
        },
        {
            "phase": "phase_7_submission_pack",
            "task": "final_figures",
            "status": "complete for programmatic draft figures",
            "evidence": "results/figures/*.pdf and reports/FIGURE_CAPTIONS.md",
            "residual_risk": "Manual top-conference figure polish remains a future presentation pass.",
        },
        {
            "phase": "phase_7_submission_pack",
            "task": "final_videos",
            "status": "complete for synthetic simulation rollout media",
            "evidence": "results/videos/bodyshield_synthetic_*.gif, results/simulation_rollout_videos.csv, reports/SIMULATION_ROLLOUT_VIDEOS.md",
            "residual_risk": "Real camera videos and hardware verifier videos still require hardware.",
        },
        {
            "phase": "phase_7_submission_pack",
            "task": "final_paper",
            "status": "paper draft complete with generated result tables",
            "evidence": "paper/main.tex, paper/bodyshield_non_hardware_draft.pdf, reports/PAPER_BUILD_STATUS.json, reports/PAPER_REVIEWER_RISK_AUDIT.md",
            "residual_risk": "Full final paper awaits hardware or a no-hardware submission decision.",
        },
        {
            "phase": "phase_7_submission_pack",
            "task": "reproducibility_package",
            "status": "complete for local non-hardware run plus portable release bundle",
            "evidence": "reports/REPRODUCIBILITY_MANIFEST.md, reports/ARTIFACT_MANIFEST.csv, reports/RELEASE_BUNDLE.md, release/bodyshield_non_hardware_release.zip, release/RELEASE_BUNDLE_CHECKSUMS.txt, reports/PACK_VERIFICATION.md, results/trials.parquet",
            "residual_risk": "No external archival upload or public repository release yet.",
        },
        {
            "phase": "phase_7_submission_pack",
            "task": "final_reviewer_response_prebuttal",
            "status": "complete",
            "evidence": "reports/PREBUTTAL.md",
            "residual_risk": "Should be revised after hardware or full high-fidelity robot-policy results change the evidence.",
        },
    ]


def format_table_float(value: Any) -> str:
    if pd.isna(value):
        return "--"
    return f"{float(value):.3f}"


def paper_analytic_success_table(summary: pd.DataFrame) -> str:
    labels = {
        "nominal": "Nominal",
        "domain_randomization": "Domain rand.",
        "sysid_retune": "SysID+retune",
        "bodyshield": "BodyShield",
        "oracle": "Oracle",
    }
    pivot = summary.pivot(index="method_id", columns="bucket", values="success_rate")
    rows = []
    for method_id, label in labels.items():
        if method_id not in pivot.index:
            continue
        rows.append(
            f"{label} & {format_table_float(pivot.loc[method_id].get('nominal'))} "
            f"& {format_table_float(pivot.loc[method_id].get('seen'))} "
            f"& {format_table_float(pivot.loc[method_id].get('heldout'))} \\\\"
        )
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\caption{Analytic success rates by perturbation bucket.}",
            r"\label{tab:analytic-success}",
            r"\centering",
            r"\footnotesize",
            r"\begin{tabular}{lccc}",
            r"\toprule",
            r"Method & Nominal & Seen & Held-out \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )


def paper_search_table(search_summary: pd.DataFrame) -> str:
    labels = {
        "bodybreak": "BodyBreak",
        "grid": "Grid",
        "one_axis": "One-axis",
        "random": "Random",
    }
    indexed = search_summary.set_index("search_mode")
    rows = []
    for mode, label in labels.items():
        if mode not in indexed.index:
            continue
        row = indexed.loc[mode]
        rows.append(
            f"{label} & {format_table_float(row['found_break_rate'])} "
            f"& {format_table_float(row['found_break_avg_cost'])} "
            f"& {format_table_float(row['avg_trials'])} \\\\"
        )
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\caption{Equal-budget BodyBreak search comparison. Cost is averaged over found-break cases only.}",
            r"\label{tab:bodybreak-search}",
            r"\centering",
            r"\footnotesize",
            r"\begin{tabular}{lccc}",
            r"\toprule",
            r"Search & Break rate & Cost & Calls \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )


def paper_mujoco_table(mujoco_method_summary: pd.DataFrame) -> str:
    labels = {
        "nominal": "Nominal",
        "domain_randomization": "Domain rand.",
        "bodyshield": "BodyShield",
        "oracle": "Oracle",
    }
    indexed = mujoco_method_summary.set_index("method_id") if not mujoco_method_summary.empty else pd.DataFrame()
    rows = []
    for method_id, label in labels.items():
        if method_id not in indexed.index:
            continue
        row = indexed.loc[method_id]
        rows.append(
            f"{label} & {format_table_float(row['mean_success_rate'])} "
            f"& {int(row['tasks'])} & {int(row['conditions'])} \\\\"
        )
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\caption{Bounded MuJoCo probe summary. These are dynamics sanity checks, not full robot-policy benchmarks.}",
            r"\label{tab:mujoco-probe}",
            r"\centering",
            r"\footnotesize",
            r"\begin{tabular}{lccc}",
            r"\toprule",
            r"Method & Success & Tasks & Pert. \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )


def paper_stress_test_table(summary: pd.DataFrame) -> str:
    labels = {
        "human_effect_prior": "Human/effect",
        "epec": "EPEC",
        "bodyshield": "BodyShield",
    }
    pivot = summary.pivot(index="method_id", columns="bucket", values="success_rate")
    rows = []
    for method_id, label in labels.items():
        if method_id not in pivot.index:
            continue
        rows.append(
            f"{label} & {format_table_float(pivot.loc[method_id].get('nominal'))} "
            f"& {format_table_float(pivot.loc[method_id].get('seen'))} "
            f"& {format_table_float(pivot.loc[method_id].get('heldout'))} \\\\"
        )
    return "\n".join(
        [
            r"\begin{table}[t]",
            r"\caption{Human/effect-prior stress-test family in the analytic surrogate.}",
            r"\label{tab:stress-family}",
            r"\centering",
            r"\footnotesize",
            r"\begin{tabular}{lccc}",
            r"\toprule",
            r"Method & Nominal & Seen & Held-out \\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )


def success_delta_interval(successes_a: int, n_a: int, successes_b: int, n_b: int, z: float = 1.96) -> tuple[float, float, float]:
    if n_a == 0 or n_b == 0:
        return (float("nan"), float("nan"), float("nan"))
    p_a = successes_a / n_a
    p_b = successes_b / n_b
    delta = p_a - p_b
    se = math.sqrt((p_a * (1.0 - p_a) / n_a) + (p_b * (1.0 - p_b) / n_b))
    return (delta, delta - z * se, delta + z * se)


def compute_method_deltas(summary: pd.DataFrame) -> pd.DataFrame:
    bodyshield = summary[summary["method_id"] == "bodyshield"].set_index("bucket")
    rows = []
    for _, row in summary[summary["method_id"] != "bodyshield"].iterrows():
        bucket = row["bucket"]
        if bucket not in bodyshield.index:
            continue
        bs = bodyshield.loc[bucket]
        delta, low, high = success_delta_interval(
            int(bs["successes"]),
            int(bs["n"]),
            int(row["successes"]),
            int(row["n"]),
        )
        rows.append(
            {
                "baseline_method": row["method_id"],
                "bucket": bucket,
                "bodyshield_success_rate": float(bs["success_rate"]),
                "baseline_success_rate": float(row["success_rate"]),
                "delta_success_rate": delta,
                "delta_ci_low": low,
                "delta_ci_high": high,
                "bodyshield_n": int(bs["n"]),
                "baseline_n": int(row["n"]),
                "bodyshield_execution_time_s": float(bs["mean_execution_time_s"]),
                "baseline_execution_time_s": float(row["mean_execution_time_s"]),
                "delta_execution_time_s": float(bs["mean_execution_time_s"] - row["mean_execution_time_s"]),
                "bodyshield_path_length_m": float(bs["mean_path_length_m"]),
                "baseline_path_length_m": float(row["mean_path_length_m"]),
                "delta_path_length_m": float(bs["mean_path_length_m"] - row["mean_path_length_m"]),
            }
        )
    return pd.DataFrame(rows)


def write_method_delta_reports(deltas: pd.DataFrame) -> None:
    deltas.to_csv(RESULTS / "method_deltas_vs_bodyshield.csv", index=False)
    report = deltas[deltas["baseline_method"].isin(["domain_randomization", "sysid_retune", "epec", "human_effect_prior", "nominal"])][
        [
            "baseline_method",
            "bucket",
            "bodyshield_success_rate",
            "baseline_success_rate",
            "delta_success_rate",
            "delta_ci_low",
            "delta_ci_high",
            "delta_execution_time_s",
            "delta_path_length_m",
        ]
    ].sort_values(["baseline_method", "bucket"])
    write_markdown_table(REPORTS / "METHOD_DELTA_TABLE.md", report)


def write_budget_fairness_audit(search_summary: pd.DataFrame, summary: pd.DataFrame, threshold_df: pd.DataFrame, oracle_df: pd.DataFrame) -> None:
    bucket_rows = []
    for bucket, group in summary.groupby("bucket"):
        bucket_rows.append(
            {
                "evaluation_bucket": bucket,
                "methods": group["method_id"].nunique(),
                "unique_n_values": ", ".join(str(int(v)) for v in sorted(group["n"].unique())),
                "all_methods_same_n": bool(group["n"].nunique() == 1),
            }
        )
    write_markdown_table(REPORTS / "EVALUATION_BUDGET_TABLE.md", pd.DataFrame(bucket_rows))

    search_rows = search_summary.copy()
    search_rows["configured_budget_cap"] = SEARCH_BUDGET_CAP
    write_markdown_table(
        REPORTS / "SEARCH_BUDGET_TABLE.md",
        search_rows[["search_mode", "configured_budget_cap", "avg_trials", "found_break_rate", "found_break_avg_cost"]],
    )

    threshold_cases = int(len(threshold_df))
    oracle_cases = int(len(oracle_df))
    (REPORTS / "BUDGET_AND_FAIRNESS_AUDIT.md").write_text(
        f"""# Budget And Fairness Audit

## Main Analytic Evaluation

- Every method is evaluated on the same task, robot, perturbation-family, and trial grid.
- Each condition uses 50 simulator trials.
- Bucket-level sample parity is reported in `reports/EVALUATION_BUDGET_TABLE.md`.
- This is an evaluation-budget match. It is not evidence that external neural-policy training compute is matched.

## BodyBreak Search

- `compare_search_modes` configures the same {SEARCH_BUDGET_CAP}-evaluator-call cap for random, one-axis, grid, and BodyBreak modes.
- Some modes use fewer calls when their finite candidate set is exhausted or when BodyBreak stops after finding and refining a breaking perturbation.
- Search budget accounting is reported in `reports/SEARCH_BUDGET_TABLE.md` and `results/breaking_search.csv`.
- Dense post-hoc minimality challenge rows are reported in `results/bodybreak_minimality_audit.csv`; this uses a larger deterministic local candidate pool and does not claim global optimality.

## Repair And Feasibility

- BodyShield repair samples 160 candidate repairs in this CPU analytic implementation.
- Each repair candidate is scored on discovered breaking perturbations through the same evaluator path used by the analytic simulator.
- Threshold sensitivity contains {threshold_cases} search rows with {THRESHOLD_SEARCH_BUDGET_CAP}-call caps and the same deterministic analytic success-probability evaluator used by BodyBreak search.
- Oracle feasibility contains {oracle_cases} BodyBreak failure rows, each evaluated with 60 simulator trials.

## Remaining Budget Limits

- Domain randomization, robust control, SysID+retune, EPEC, and human/effect-prior policies are analytic parameterized baselines, not externally trained controllers.
- Full trained-policy compute matching is non-hardware future work if this becomes a simulation-only submission.
- Hardware budgets, reset costs, verifier audits, and physical intervention counts remain hardware-only.
""",
        encoding="utf-8",
    )


def write_requirement_trace(oracle_df: pd.DataFrame) -> None:
    oracle_total = int(len(oracle_df))
    oracle_feasible = int(oracle_df["feasible"].sum()) if oracle_total else 0
    rows = [
        {
            "requirement": "Embodiment falsification",
            "status": "complete for analytic surrogate",
            "evidence": "bodyshield/bodybreak_search.py, results/breaking_search.csv, results/bodybreak_minimality_audit.csv, reports/SEARCH_COMPARISON_TABLE.md, reports/BODYBREAK_MINIMALITY_AUDIT.md",
            "residual": "Dense analytic candidate-pool challenge is logged, but no mathematical global minimality proof; high-fidelity/hardware evaluators remain future tiers.",
        },
        {
            "requirement": "Embodiment-adversarial repair",
            "status": "complete for analytic surrogate",
            "evidence": "bodyshield/bodyshield_repair.py, results/repair_history.csv, reports/METHOD_DELTA_TABLE.md",
            "residual": "Repair is parameter-search over analytic policy sensitivities, not a neural policy update.",
        },
        {
            "requirement": "Synthetic corrective-trace adaptation",
            "status": "complete for residual action correction on generated traces",
            "evidence": "bodyshield/corrective_adaptation.py, results/corrective_adaptation_eval.csv, results/corrective_adaptation_rollouts.csv, results/corrective_adaptation_trace_sample.jsonl, reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md",
            "residual": "Not real-robot online learning, neural policy finetuning, or adaptation from physical corrective attempts.",
        },
        {
            "requirement": "Corrective-trace dataset readiness",
            "status": "complete for corrective-trace manifest validation, missing-dataset detection, and deterministic residual-fit smoke",
            "evidence": "bodyshield/corrective_trace_readiness.py, configs/corrective_trace_readiness.example.json, scripts/run_corrective_trace_readiness.py, results/corrective_trace_readiness.csv, reports/CORRECTIVE_TRACE_READINESS.md",
            "residual": "The included corrective-trace dataset row records a missing dataset, so no real/external corrective-trace adaptation evidence is claimed.",
        },
        {
            "requirement": "Simulation breadth",
            "status": "complete for local run plus bounded high-fidelity probes",
            "evidence": "8 task cards, 6 robot archetypes, 10 methods, 48 conditions/method, 1,152,000 validated records, MuJoCo 1-DOF suite, MuJoCo planar-effector suite, learned MuJoCo gated residual-policy audit, ManiSkill task availability suite",
            "residual": "Full trained robot-policy MuJoCo/ManiSkill benchmark with external policy checkpoints remains future non-hardware work.",
        },
        {
            "requirement": "External trained-policy benchmark readiness",
            "status": "complete for spec validation, checkpoint detection, and deterministic interface smoke",
            "evidence": "bodyshield/external_policy_benchmark.py, configs/external_policy_benchmark.example.json, scripts/run_external_policy_benchmark.py, results/external_policy_benchmark_readiness.csv, reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md",
            "residual": "The included external checkpoint row records a missing checkpoint, so no external/full-scale trained-policy MuJoCo/ManiSkill rollout benchmark evidence is claimed.",
        },
        {
            "requirement": "Learned high-fidelity gated residual policy",
            "status": "complete for local MuJoCo planar corrective traces with conservative residual gating",
            "evidence": "bodyshield/high_fidelity_learning.py, results/mujoco_residual_policy_eval.csv, results/mujoco_residual_policy_rollouts.csv, results/mujoco_residual_policy_gate_ablation.csv, results/mujoco_residual_policy_trace_sample.jsonl, reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md, reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md",
            "residual": "Not an external neural robot-policy checkpoint, full ManiSkill trained-policy benchmark, contact-rich hardware validation, or physical transfer result.",
        },
        {
            "requirement": "Learned outcome-model proxy",
            "status": "complete for tabular analytic predictor",
            "evidence": "bodyshield/learned_outcome_model.py, results/learned_outcome_model_eval.csv, reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md",
            "residual": "Not a visual world model or policy adaptation from real failed attempts.",
        },
        {
            "requirement": "Trajectory-level WAM proxy",
            "status": "complete for synthetic proprioceptive traces",
            "evidence": "bodyshield/trajectory_wam.py, results/trajectory_wam_eval.csv, results/trajectory_wam_rollouts.csv, results/trajectory_wam_trace_sample.jsonl, reports/TRAJECTORY_WAM_INTERPRETATION.md",
            "residual": "Not video prediction, real-video neural world-model training, or adaptation from real robot corrective traces.",
        },
        {
            "requirement": "Synthetic visual WAM proxy",
            "status": "complete for rendered-frame prediction",
            "evidence": "bodyshield/visual_wam.py, results/visual_wam_eval.csv, results/visual_wam_rollouts.csv, results/visual_wam_trace_sample.jsonl, reports/VISUAL_WAM_INTERPRETATION.md",
            "residual": "Not real camera video, neural foundation WAM training, or physical visual adaptation.",
        },
        {
            "requirement": "Real-video WAM readiness",
            "status": "complete for frame-manifest validation, missing-dataset detection, and deterministic fit smoke",
            "evidence": "bodyshield/real_video_wam_readiness.py, configs/real_video_wam_readiness.example.json, scripts/run_real_video_wam_readiness.py, results/real_video_wam_readiness.csv, reports/REAL_VIDEO_WAM_READINESS.md",
            "residual": "The included real-video dataset row records a missing dataset, so no real-video or foundation-scale WAM evidence is claimed.",
        },
        {
            "requirement": "Synthetic rollout media",
            "status": "complete for generated non-hardware GIF rollouts",
            "evidence": "bodyshield/sim_videos.py, results/videos/bodyshield_synthetic_*.gif, results/simulation_rollout_videos.csv, reports/SIMULATION_ROLLOUT_VIDEOS.md",
            "residual": "Generated frames are synthetic simulator media only, not real camera videos, human-verifier clips, or physical transfer evidence.",
        },
        {
            "requirement": "Neural visual-latent WAM proxy",
            "status": "complete for NumPy MLP dynamics on generated visual latents",
            "evidence": "bodyshield/neural_wam.py, results/neural_wam_eval.csv, results/neural_wam_rollouts.csv, results/neural_wam_training_curve.csv, reports/NEURAL_WAM_INTERPRETATION.md",
            "residual": "Not real-video WAM training, large-scale foundation-model training, high-fidelity robot-policy transfer, or physical visual adaptation.",
        },
        {
            "requirement": "EPEC/human-effect stress test",
            "status": "complete for analytic surrogate",
            "evidence": "human_effect_prior and epec methods in results/summary_by_method_bucket.csv and paper Table stress-family",
            "residual": "No real Pathak-style policy checkpoint or video-conditioned policy is run locally.",
        },
        {
            "requirement": "Held-out physical-style modifications",
            "status": "complete as analytic perturbation families",
            "evidence": "payload, tool extension, physical gripper restriction, obstacle clearance, camera shift, and friction families in results/trials.csv",
            "residual": "Physical modifications on the SO-ARM101/SO-101 remain hardware-only.",
        },
        {
            "requirement": "Oracle feasibility",
            "status": f"complete for analytic BodyBreak failures ({oracle_feasible}/{oracle_total})",
            "evidence": "results/oracle_feasibility.csv, reports/ORACLE_FEASIBILITY_TABLE.md",
            "residual": "Hardware oracle feasibility remains pending.",
        },
        {
            "requirement": "Metrics and statistics",
            "status": "complete for local run",
            "evidence": "Wilson intervals, bootstrap robustness profiles, threshold sensitivity, secondary metrics, failure taxonomy",
            "residual": "No paired physical statistical tests until hardware logs exist.",
        },
        {
            "requirement": "Paper and reviewer-defense pack",
            "status": "complete as non-hardware draft",
            "evidence": "paper/bodyshield_non_hardware_draft.pdf, reports/CLAIM_LEDGER.md, reports/PREBUTTAL.md, reports/PAPER_REVIEWER_RISK_AUDIT.md",
            "residual": "Final submission-quality paper requires hardware or an explicit no-hardware submission decision.",
        },
        {
            "requirement": "Paper source integrity",
            "status": "complete for local TeX/Bib/PDF/build consistency audit",
            "evidence": "bodyshield/paper_source_audit.py, scripts/run_paper_source_audit.py, results/paper_source_audit.csv, reports/PAPER_SOURCE_AUDIT.md, paper/main.tex, paper/references.bib, paper/bodyshield_non_hardware_draft.pdf",
            "residual": "Checks local source/output consistency and wording boundaries only; it does not add hardware, external trained-policy, real-video, or independent-review evidence.",
        },
        {
            "requirement": "Portable hygiene",
            "status": "complete for local text and final release ZIP hygiene audit",
            "evidence": "bodyshield/portable_hygiene_audit.py, scripts/run_portable_hygiene_audit.py, results/portable_hygiene_audit.csv, reports/PORTABLE_HYGIENE_AUDIT.md, release/bodyshield_non_hardware_release.zip, release/RELEASE_BUNDLE_MANIFEST.csv",
            "residual": "Checks local path leakage, temporary extraction traces, unsafe archive paths, and self-referential dynamic outputs only; it does not prove external archival upload or independent replication.",
        },
        {
            "requirement": "Portable release bundle",
            "status": "complete for local ZIP export with payload manifest, checksums, pack-side inspection, unpacked-payload verifier, extracted-payload audit, deterministic byte-rebuild audit, and extracted-release pytest smoke",
            "evidence": "bodyshield/release_bundle.py, bodyshield/release_payload_audit.py, bodyshield/release_determinism_audit.py, bodyshield/release_runtime_audit.py, scripts/build_release_bundle.py, scripts/verify_release_payload.py, scripts/run_release_payload_audit.py, scripts/run_release_determinism_audit.py, scripts/run_release_runtime_audit.py, release/bodyshield_non_hardware_release.zip, release/RELEASE_BUNDLE_MANIFEST.csv, release/RELEASE_BUNDLE_CHECKSUMS.txt, results/release_payload_audit.csv, results/release_determinism_audit.csv, results/release_runtime_audit.csv, reports/RELEASE_BUNDLE.md, reports/RELEASE_PAYLOAD_AUDIT.md, reports/RELEASE_DETERMINISM_AUDIT.md, reports/RELEASE_RUNTIME_AUDIT.md",
            "residual": "Not an external archival upload, public repository release, or independent replication.",
        },
        {
            "requirement": "Evidence-reference consistency",
            "status": "complete for local document-to-artifact reference audit",
            "evidence": "bodyshield/evidence_consistency.py, scripts/run_evidence_consistency_audit.py, results/evidence_consistency_audit.csv, reports/EVIDENCE_CONSISTENCY_AUDIT.md",
            "residual": "Only checks local artifact references; it does not validate external scientific correctness or independent replication.",
        },
        {
            "requirement": "Environment and dependency reproducibility",
            "status": "complete for local Python/package/system-tool snapshot and required-dependency declaration audit",
            "evidence": "bodyshield/environment_audit.py, scripts/run_environment_dependency_audit.py, results/environment_dependency_audit.csv, results/environment_snapshot.json, reports/ENVIRONMENT_DEPENDENCY_AUDIT.md, pyproject.toml",
            "residual": "Records this local environment and declared dependencies; it does not guarantee future package index availability or cross-platform simulator parity.",
        },
        {
            "requirement": "Config and schema integrity",
            "status": "complete for local TOML/JSON/YAML control-plane validation",
            "evidence": "bodyshield/config_schema_audit.py, scripts/run_config_schema_audit.py, results/config_schema_audit.csv, reports/CONFIG_SCHEMA_AUDIT.md, pyproject.toml, data_schema.json, trial_schema.schema.json, tasks.yaml, configs/*.json, configs/*.yaml",
            "residual": "Checks local config/schema contracts, ID synchronization, readiness boundaries, and safety-gated hardware placeholders only; it does not prove hardware readiness or external data availability.",
        },
        {
            "requirement": "Source and import health",
            "status": "complete for local source compile, module import, script guard, and hardware-stub safety audit",
            "evidence": "bodyshield/source_import_audit.py, scripts/run_source_import_audit.py, results/source_import_audit.csv, reports/SOURCE_IMPORT_AUDIT.md, bodyshield/robot/*.py, bodyshield/safe_robot_runner.py",
            "residual": "Checks shipped Python source/import safety and refusal-only hardware stubs only; it does not execute hardware, verify physical safety, or prove external runtime portability beyond this environment.",
        },
        {
            "requirement": "Artifact inventory synchronization",
            "status": "complete for local documented-output, artifact-manifest, and release-manifest synchronization audit",
            "evidence": "bodyshield/artifact_inventory_audit.py, scripts/run_artifact_inventory_audit.py, results/artifact_inventory_audit.csv, reports/ARTIFACT_INVENTORY_AUDIT.md, reports/ARTIFACT_MANIFEST.csv, release/RELEASE_BUNDLE_MANIFEST.csv, README_EXECUTION.md, reports/REPRODUCIBILITY_MANIFEST.md, reports/NON_HARDWARE_COMPLETE.md",
            "residual": "Checks local manifests and documented output references only; it does not prove external archival upload, independent replication, or physical transfer.",
        },
        {
            "requirement": "Derived-results recomputation",
            "status": "complete for local recomputation of summary, profile, secondary-metric, failure-taxonomy, and delta tables from primary trials",
            "evidence": "bodyshield/derived_results_audit.py, scripts/run_derived_results_audit.py, results/derived_results_audit.csv, reports/DERIVED_RESULTS_AUDIT.md, results/trials.csv, results/summary_by_method_bucket.csv, results/robustness_profiles.csv, results/secondary_metrics_by_method.csv, results/failure_taxonomy_counts.csv, results/method_deltas_vs_bodyshield.csv",
            "residual": "Checks deterministic table derivations from local analytic trials only; it does not add new physical evidence, external trained-policy rollouts, or independent replication.",
        },
        {
            "requirement": "Generated-results integrity",
            "status": "complete for local table-shape, row-count, key, range, JSONL, schema-summary, and Parquet consistency audit",
            "evidence": "bodyshield/results_integrity.py, scripts/run_results_integrity_audit.py, results/results_integrity_audit.csv, reports/RESULTS_INTEGRITY_AUDIT.md",
            "residual": "Checks generated artifact integrity only; it does not prove external scientific validity, physical transfer, or independent replication.",
        },
        {
            "requirement": "Claim-boundary enforcement",
            "status": "complete for local paper, report, readiness, and release boundary phrase and overclaim audit",
            "evidence": "bodyshield/claim_boundary_audit.py, scripts/run_claim_boundary_audit.py, results/claim_boundary_audit.csv, reports/CLAIM_BOUNDARY_AUDIT.md",
            "residual": "Checks local wording and readiness status boundaries only; it does not replace external review or new evidence.",
        },
        {
            "requirement": "Command-surface reproducibility",
            "status": "complete for local documented command synchronization, script target, py-compile, main-guard, and safe --help audit",
            "evidence": "bodyshield/command_surface_audit.py, scripts/run_command_surface_audit.py, results/command_surface_audit.csv, reports/COMMAND_SURFACE_AUDIT.md",
            "residual": "Checks documented local command surface only; it does not execute the full long workflow or external archival upload.",
        },
        {
            "requirement": "Visual artifact integrity",
            "status": "complete for local figure PDF/PNG pair, nonblank image, caption coverage, and synthetic GIF integrity audit",
            "evidence": "bodyshield/visual_artifact_audit.py, scripts/run_visual_artifact_audit.py, results/visual_artifact_audit.csv, reports/VISUAL_ARTIFACT_AUDIT.md, results/figures/*.pdf, results/figures/*.png, results/videos/bodyshield_synthetic_*.gif",
            "residual": "Checks local generated figures and synthetic media only; it does not provide real camera videos or manual final-art polish.",
        },
        {
            "requirement": "Release payload extraction integrity",
            "status": "complete for local safe ZIP extraction and bundled verifier execution from the extracted archive",
            "evidence": "bodyshield/release_payload_audit.py, scripts/run_release_payload_audit.py, results/release_payload_audit.csv, reports/RELEASE_PAYLOAD_AUDIT.md, scripts/verify_release_payload.py, release/bodyshield_non_hardware_release.zip",
            "residual": "Checks local archive extractability and payload checksums only; it does not prove an external archival upload or independent replication.",
        },
        {
            "requirement": "Release byte determinism",
            "status": "complete for current-payload hash sync, fixed ZIP metadata, deterministic entry order, and exact ZIP byte reconstruction",
            "evidence": "bodyshield/release_determinism_audit.py, scripts/run_release_determinism_audit.py, results/release_determinism_audit.csv, reports/RELEASE_DETERMINISM_AUDIT.md, release/bodyshield_non_hardware_release.zip, release/RELEASE_BUNDLE_MANIFEST.csv",
            "residual": "Checks local byte reproducibility only; it does not prove external archival upload, cross-platform compression equivalence, or independent replication.",
        },
        {
            "requirement": "Release runtime smoke",
            "status": "complete for safe ZIP extraction and pytest execution from inside the extracted release",
            "evidence": "bodyshield/release_runtime_audit.py, scripts/run_release_runtime_audit.py, results/release_runtime_audit.csv, reports/RELEASE_RUNTIME_AUDIT.md, tests/test_bodyshield.py, release/bodyshield_non_hardware_release.zip",
            "residual": "Checks local extracted-release runtime only; it does not prove future dependency availability, external archival upload, or independent replication.",
        },
        {
            "requirement": "Hardware validation, noise floor, verifier audit, videos",
            "status": "not run by design",
            "evidence": "reports/CLAIM_BOUNDARY.md, safety-gated bodyshield.robot stubs",
            "residual": "Requires explicit user confirmation of robot setup, safety gate, camera verifier, and emergency stop.",
        },
    ]
    df = pd.DataFrame(rows)
    write_markdown_table(REPORTS / "NON_HARDWARE_REQUIREMENTS_TRACE.md", df)


def write_agenda_fit_memo() -> None:
    (REPORTS / "AGENDA_FIT_MEMO.md").write_text(
        """# Jason Agenda Fit Memo

Fit score: 8/10

Category: Strong bridge toward a core agenda paper.

Real contribution: BodyShield frames robot reliability as hidden embodiment-assumption falsification followed by failure-axis repair, synthetic visual/trajectory prediction, a NumPy neural visual-latent WAM audit, real-video WAM readiness, learned MuJoCo gated residual-policy adaptation, external-checkpoint readiness, synthetic corrective-trace adaptation, and corrective-trace dataset readiness.

Why it fits:
- The mechanism is failure diagnosis, targeted probing, learned scalar, visual, neural visual-latent, trajectory outcome prediction, simulator gated residual-policy adaptation, synthetic corrective-trace adaptation, corrective-trace dataset readiness, action-representation repair, and transfer under embodiment-control shift.
- The project stays focused on the robot brain rather than hardware design.
- The stress-test framing connects human/effect priors to physical execution failures without making video imitation the headline.

Why it is not fully core yet:
- The current evidence is analytic plus bounded simulator compatibility probes.
- It includes synthetic visual, neural visual-latent, trajectory, real-video WAM readiness, MuJoCo gated residual-policy, external-checkpoint readiness, synthetic corrective-trace adaptation, and corrective-trace dataset readiness, but does not yet train a world-action model from real video, run external high-fidelity policy checkpoints, or adapt from failed physical attempts.
- Hardware validation, verifier accuracy, reset reliability, and real physical modifications are still missing.

Best reframing:
Present BodyShield as a diagnostic and adaptation layer for world/action models: when execution diverges from the assumed body-control interface, actively identify the missing physical assumption and update the action representation or planner.

Next version:
Replace the synthetic visual/trajectory/neural-latent and local MuJoCo gated residual proxies with a neural real-video or external-checkpoint high-fidelity WAM, use BodyBreak perturbations as diagnostic interventions, and show that a small number of corrective real or high-fidelity traces improves future planning across tools, surfaces, and embodiments.

Final call:
Pursue as a strong bridge project. It is worth continuing if the next evidence tier moves from local synthetic scalar/visual/neural-latent/trajectory and MuJoCo gated residual-policy proxies toward real video, external high-fidelity policy checkpoints, or real corrective attempts.
""",
        encoding="utf-8",
    )


def write_reports(
    code_version: str,
    search: pd.DataFrame,
    search_minimality: pd.DataFrame,
    summary: pd.DataFrame,
    radius: pd.DataFrame,
    threshold_df: pd.DataFrame,
    oracle_df: pd.DataFrame,
    secondary_metrics: pd.DataFrame,
    failure_counts: pd.DataFrame,
    task_cards: pd.DataFrame,
    sim_envs: pd.DataFrame,
    high_fidelity: pd.DataFrame,
    external_policy_benchmark: pd.DataFrame,
    real_video_wam_readiness: pd.DataFrame,
    corrective_trace_readiness: pd.DataFrame,
    mujoco_residual_metrics: pd.DataFrame,
    mujoco_residual_rollouts: pd.DataFrame,
    mujoco_residual_weights: pd.DataFrame,
    mujoco_residual_gate_ablation: pd.DataFrame,
    mujoco_residual_trace_sample: list[dict[str, Any]],
    learned_metrics: pd.DataFrame,
    learned_axis_weights: pd.DataFrame,
    learned_predictions: pd.DataFrame,
    trajectory_metrics: pd.DataFrame,
    trajectory_axis_weights: pd.DataFrame,
    trajectory_rollouts: pd.DataFrame,
    trajectory_trace_sample: list[dict[str, Any]],
    corrective_metrics: pd.DataFrame,
    corrective_rollouts: pd.DataFrame,
    corrective_weights: pd.DataFrame,
    corrective_trace_sample: list[dict[str, Any]],
    visual_metrics: pd.DataFrame,
    visual_rollouts: pd.DataFrame,
    visual_weights: pd.DataFrame,
    visual_trace_sample: list[dict[str, Any]],
    neural_metrics: pd.DataFrame,
    neural_rollouts: pd.DataFrame,
    neural_training_curve: pd.DataFrame,
    neural_trace_sample: list[dict[str, Any]],
    simulation_videos: pd.DataFrame,
    jsonl_path: Path,
) -> None:
    REPORTS.mkdir(exist_ok=True)
    PAPER.mkdir(exist_ok=True)
    (ROOT / "trial_schema.schema.json").write_text(json.dumps(TRIAL_JSON_SCHEMA, indent=2, sort_keys=True), encoding="utf-8")

    found = search[search["notes"] == "found_break"]
    search_summary = search.groupby("search_mode", as_index=False).agg(
        avg_all_candidate_cost=("breaking_cost", "mean"),
        avg_success_rate=("success_rate", "mean"),
        avg_trials=("trials", "mean"),
        total_cases=("notes", "count"),
        found_breaks=("notes", lambda s: int((s == "found_break").sum())),
        found_break_rate=("notes", lambda s: float((s == "found_break").mean())),
    )
    found_cost = found.groupby("search_mode", as_index=False).agg(found_break_avg_cost=("breaking_cost", "mean"))
    search_summary = search_summary.merge(found_cost, on="search_mode", how="left")
    write_markdown_table(REPORTS / "SEARCH_COMPARISON_TABLE.md", search_summary)
    search_minimality.to_csv(RESULTS / "bodybreak_minimality_audit.csv", index=False)
    write_markdown_table(REPORTS / "BODYBREAK_MINIMALITY_AUDIT_TABLE.md", search_minimality)
    minimality_cases = int(len(search_minimality))
    lower_cost_dense_cases = int(search_minimality["lower_cost_break_found"].sum()) if minimality_cases else 0
    unconfirmed_bodybreak_cases = (
        int((search_minimality["bodybreak_confirmed_success_rate"] > 0.50).sum()) if minimality_cases else 0
    )
    positive_regrets = search_minimality.loc[search_minimality["bodybreak_cost_regret"] > 0, "bodybreak_cost_regret"] if minimality_cases else pd.Series(dtype=float)
    mean_positive_regret = float(positive_regrets.mean()) if len(positive_regrets) else 0.0
    max_positive_regret = float(positive_regrets.max()) if len(positive_regrets) else 0.0
    mean_candidate_count = float(search_minimality["dense_candidate_count"].mean()) if minimality_cases else 0.0
    search_evaluator_used = str(search_minimality["search_evaluator"].iloc[0]) if minimality_cases else SEARCH_EVALUATOR
    confirm_trials_used = int(search_minimality["confirm_trials"].max()) if minimality_cases else 0
    (REPORTS / "BODYBREAK_MINIMALITY_AUDIT.md").write_text(
        f"""# BodyBreak Dense Minimality Audit

This audit challenges representative BodyBreak found-break cases with a larger deterministic analytic search pool. It is a post-hoc stress test of estimated minimality, not a mathematical global proof.

## Audit protocol
- Cases: {minimality_cases} lowest-cost BodyBreak found-break cases, capped per search policy family.
- Candidate pool per case: compact search grid, the BodyBreak perturbation, interpolated lower-cost variants of the BodyBreak perturbation and its active axes, plus deterministic random candidates.
- Mean candidates per case: {mean_candidate_count:.1f}
- Evaluator: same {search_evaluator_used} used by the original search, followed by independent {confirm_trials_used}-trial confirmation before a dense candidate counts as a break.
- Threshold: success rate <= 0.50.

## Result
- Lower-cost independently confirmed dense breaks found: {lower_cost_dense_cases}/{minimality_cases}
- BodyBreak found breaks above threshold under independent confirmation: {unconfirmed_bodybreak_cases}/{minimality_cases}
- Mean positive confirmed BodyBreak cost regret: {mean_positive_regret:.4f}
- Max positive confirmed BodyBreak cost regret: {max_positive_regret:.4f}
- Table: `reports/BODYBREAK_MINIMALITY_AUDIT_TABLE.md`
- Raw CSV: `results/bodybreak_minimality_audit.csv`

## Safe claim
BodyBreak remains an estimated lowest-cost search procedure under a fixed evaluator budget. The dense audit makes the minimality boundary auditable by reporting whether a stronger local candidate pool finds lower-cost analytic breaks for representative cases.
""",
        encoding="utf-8",
    )
    write_markdown_table(REPORTS / "SIMULATION_BUCKET_SUMMARY_TABLE.md", summary)
    write_markdown_table(REPORTS / "NOMINAL_VS_RADIUS_TABLE.md", radius)
    write_markdown_table(
        REPORTS / "THRESHOLD_SENSITIVITY_TABLE.md",
        threshold_df.groupby(["method_id", "threshold"], as_index=False).agg(
            breaking_cost=("breaking_cost", "mean"),
            found_break_rate=("notes", lambda s: float((s == "found_break").mean())),
            trials=("trials", "mean"),
        ),
    )
    write_markdown_table(REPORTS / "ORACLE_FEASIBILITY_TABLE.md", oracle_df)
    write_markdown_table(REPORTS / "SECONDARY_METRICS_TABLE.md", secondary_metrics)
    write_markdown_table(REPORTS / "FAILURE_TAXONOMY_TABLE.md", failure_counts)
    write_markdown_table(REPORTS / "TASK_SUITE_CARDS.md", task_cards)
    write_markdown_table(REPORTS / "SIM_ENV_AVAILABILITY.md", sim_envs)
    external_policy_benchmark.to_csv(RESULTS / "external_policy_benchmark_readiness.csv", index=False)
    write_markdown_table(REPORTS / "EXTERNAL_POLICY_BENCHMARK_READINESS_TABLE.md", external_policy_benchmark)
    write_external_policy_benchmark_report(REPORTS / "EXTERNAL_POLICY_BENCHMARK_READINESS.md", external_policy_benchmark)
    real_video_wam_readiness.to_csv(RESULTS / "real_video_wam_readiness.csv", index=False)
    write_markdown_table(REPORTS / "REAL_VIDEO_WAM_READINESS_TABLE.md", real_video_wam_readiness)
    write_real_video_wam_readiness_report(REPORTS / "REAL_VIDEO_WAM_READINESS.md", real_video_wam_readiness)
    corrective_trace_readiness.to_csv(RESULTS / "corrective_trace_readiness.csv", index=False)
    write_markdown_table(REPORTS / "CORRECTIVE_TRACE_READINESS_TABLE.md", corrective_trace_readiness)
    write_corrective_trace_readiness_report(REPORTS / "CORRECTIVE_TRACE_READINESS.md", corrective_trace_readiness)
    simulation_videos.to_csv(RESULTS / "simulation_rollout_videos.csv", index=False)
    write_markdown_table(REPORTS / "SIMULATION_ROLLOUT_VIDEOS.md", simulation_videos)
    learned_metrics.to_csv(RESULTS / "learned_outcome_model_eval.csv", index=False)
    learned_axis_weights.to_csv(RESULTS / "learned_outcome_axis_weights.csv", index=False)
    learned_predictions.to_csv(RESULTS / "learned_outcome_predictions.csv", index=False)
    write_markdown_table(REPORTS / "LEARNED_OUTCOME_MODEL_TABLE.md", learned_metrics)
    write_markdown_table(REPORTS / "LEARNED_OUTCOME_AXIS_TABLE.md", learned_axis_weights)
    trajectory_metrics.to_csv(RESULTS / "trajectory_wam_eval.csv", index=False)
    trajectory_axis_weights.to_csv(RESULTS / "trajectory_wam_axis_weights.csv", index=False)
    trajectory_rollouts.to_csv(RESULTS / "trajectory_wam_rollouts.csv", index=False)
    trace_sample_path = RESULTS / "trajectory_wam_trace_sample.jsonl"
    with trace_sample_path.open("w", encoding="utf-8") as handle:
        for item in trajectory_trace_sample:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    write_markdown_table(REPORTS / "TRAJECTORY_WAM_TABLE.md", trajectory_metrics)
    write_markdown_table(REPORTS / "TRAJECTORY_WAM_AXIS_TABLE.md", trajectory_axis_weights)
    corrective_metrics.to_csv(RESULTS / "corrective_adaptation_eval.csv", index=False)
    corrective_rollouts.to_csv(RESULTS / "corrective_adaptation_rollouts.csv", index=False)
    corrective_weights.to_csv(RESULTS / "corrective_adaptation_residual_weights.csv", index=False)
    corrective_trace_path = RESULTS / "corrective_adaptation_trace_sample.jsonl"
    with corrective_trace_path.open("w", encoding="utf-8") as handle:
        for item in corrective_trace_sample:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    write_markdown_table(REPORTS / "CORRECTIVE_ADAPTATION_TABLE.md", corrective_metrics)
    write_markdown_table(REPORTS / "CORRECTIVE_ADAPTATION_WEIGHT_TABLE.md", corrective_weights.head(32))
    visual_metrics.to_csv(RESULTS / "visual_wam_eval.csv", index=False)
    visual_rollouts.to_csv(RESULTS / "visual_wam_rollouts.csv", index=False)
    visual_weights.to_csv(RESULTS / "visual_wam_feature_weights.csv", index=False)
    visual_trace_path = RESULTS / "visual_wam_trace_sample.jsonl"
    with visual_trace_path.open("w", encoding="utf-8") as handle:
        for item in visual_trace_sample:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    write_markdown_table(REPORTS / "VISUAL_WAM_TABLE.md", visual_metrics)
    write_markdown_table(REPORTS / "VISUAL_WAM_FEATURE_WEIGHT_TABLE.md", visual_weights.head(32))
    neural_metrics.to_csv(RESULTS / "neural_wam_eval.csv", index=False)
    neural_rollouts.to_csv(RESULTS / "neural_wam_rollouts.csv", index=False)
    neural_training_curve.to_csv(RESULTS / "neural_wam_training_curve.csv", index=False)
    neural_trace_path = RESULTS / "neural_wam_trace_sample.jsonl"
    with neural_trace_path.open("w", encoding="utf-8") as handle:
        for item in neural_trace_sample:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    write_markdown_table(REPORTS / "NEURAL_WAM_TABLE.md", neural_metrics)
    write_markdown_table(REPORTS / "NEURAL_WAM_TRAINING_CURVE.md", neural_training_curve)
    mujoco_residual_metrics.to_csv(RESULTS / "mujoco_residual_policy_eval.csv", index=False)
    mujoco_residual_rollouts.to_csv(RESULTS / "mujoco_residual_policy_rollouts.csv", index=False)
    mujoco_residual_weights.to_csv(RESULTS / "mujoco_residual_policy_weights.csv", index=False)
    mujoco_residual_gate_ablation.to_csv(RESULTS / "mujoco_residual_policy_gate_ablation.csv", index=False)
    mujoco_residual_trace_path = RESULTS / "mujoco_residual_policy_trace_sample.jsonl"
    with mujoco_residual_trace_path.open("w", encoding="utf-8") as handle:
        for item in mujoco_residual_trace_sample:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    write_markdown_table(REPORTS / "MUJOCO_RESIDUAL_POLICY_TABLE.md", mujoco_residual_metrics)
    write_markdown_table(REPORTS / "MUJOCO_RESIDUAL_POLICY_WEIGHT_TABLE.md", mujoco_residual_weights.head(32))
    write_markdown_table(REPORTS / "MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md", mujoco_residual_gate_ablation)
    method_deltas = compute_method_deltas(summary)
    write_method_delta_reports(method_deltas)
    write_budget_fairness_audit(search_summary, summary, threshold_df, oracle_df)
    write_requirement_trace(oracle_df)
    write_agenda_fit_memo()
    write_markdown_table(REPORTS / "HIGH_FIDELITY_BENCHMARK_TABLE.md", high_fidelity)
    write_markdown_table(
        REPORTS / "MUJOCO_PUSH_PROBE_TABLE.md",
        high_fidelity[high_fidelity["engine"] == "mujoco"][
            [
                "engine",
                "task_id",
                "method_id",
                "perturbation_family",
                "n",
                "success_rate",
                "mean_final_progress",
                "min_final_progress",
                "max_final_progress",
                "notes",
            ]
        ],
    )
    write_markdown_table(
        REPORTS / "MUJOCO_PLANAR_PROBE_TABLE.md",
        high_fidelity[high_fidelity["engine"] == "mujoco_planar"][
            [
                "engine",
                "task_id",
                "method_id",
                "perturbation_family",
                "n",
                "success_rate",
                "mean_final_error",
                "min_final_error",
                "max_final_error",
                "notes",
            ]
        ],
    )
    write_markdown_table(
        REPORTS / "MANISKILL_TASK_RUN_TABLE.md",
        high_fidelity[high_fidelity["engine"] == "maniskill"][
            ["engine", "task_id", "control_mode", "status", "steps", "mean_reward", "success_observed", "terminated_or_truncated", "notes"]
        ],
    )
    mujoco_method_summary = (
        high_fidelity[high_fidelity["engine"] == "mujoco"]
        .groupby("method_id", as_index=False)
        .agg(mean_success_rate=("success_rate", "mean"), tasks=("task_id", "nunique"), conditions=("perturbation_family", "nunique"))
    )
    mujoco_planar_method_summary = (
        high_fidelity[high_fidelity["engine"] == "mujoco_planar"]
        .groupby("method_id", as_index=False)
        .agg(
            mean_success_rate=("success_rate", "mean"),
            mean_final_error=("mean_final_error", "mean"),
            tasks=("task_id", "nunique"),
            conditions=("perturbation_family", "nunique"),
        )
    )
    mujoco_perturbation_summary = (
        high_fidelity[high_fidelity["engine"] == "mujoco"]
        .groupby("perturbation_family", as_index=False)
        .agg(mean_success_rate=("success_rate", "mean"), methods=("method_id", "nunique"), tasks=("task_id", "nunique"))
    )
    maniskill_task_summary = high_fidelity[high_fidelity["engine"] == "maniskill"][
        ["task_id", "control_mode", "status", "steps", "mean_reward", "success_observed", "terminated_or_truncated"]
    ]
    write_markdown_table(REPORTS / "MUJOCO_METHOD_SUMMARY_TABLE.md", mujoco_method_summary)
    write_markdown_table(REPORTS / "MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md", mujoco_planar_method_summary)
    write_markdown_table(REPORTS / "MUJOCO_PERTURBATION_SUMMARY_TABLE.md", mujoco_perturbation_summary)
    write_markdown_table(REPORTS / "MANISKILL_TASK_SUMMARY_TABLE.md", maniskill_task_summary)
    mujoco_methods = mujoco_method_summary.set_index("method_id") if not mujoco_method_summary.empty else pd.DataFrame()
    bodyshield_mujoco = float(mujoco_methods.loc["bodyshield", "mean_success_rate"]) if "bodyshield" in mujoco_methods.index else float("nan")
    domain_mujoco = (
        float(mujoco_methods.loc["domain_randomization", "mean_success_rate"])
        if "domain_randomization" in mujoco_methods.index
        else float("nan")
    )
    oracle_mujoco = float(mujoco_methods.loc["oracle", "mean_success_rate"]) if "oracle" in mujoco_methods.index else float("nan")
    planar_methods = mujoco_planar_method_summary.set_index("method_id") if not mujoco_planar_method_summary.empty else pd.DataFrame()
    bodyshield_planar = float(planar_methods.loc["bodyshield", "mean_success_rate"]) if "bodyshield" in planar_methods.index else float("nan")
    domain_planar = (
        float(planar_methods.loc["domain_randomization", "mean_success_rate"])
        if "domain_randomization" in planar_methods.index
        else float("nan")
    )
    maniskill_executed = int((maniskill_task_summary["status"] == "executed").sum()) if not maniskill_task_summary.empty else 0
    maniskill_total = int(len(maniskill_task_summary))
    external_readiness = external_policy_readiness_summary(external_policy_benchmark)
    real_video_readiness = real_video_wam_readiness_summary(real_video_wam_readiness)
    corrective_trace_readiness_summary_rows = corrective_trace_readiness_summary(corrective_trace_readiness)
    learned_heldout = learned_metrics[learned_metrics["split"] == "heldout"].iloc[0]
    trajectory_heldout = trajectory_metrics[trajectory_metrics["split"] == "heldout"].iloc[0]
    corrective_heldout = corrective_metrics[corrective_metrics["slice"] == "bucket=heldout"].iloc[0]
    visual_heldout = visual_metrics[visual_metrics["slice"] == "bucket=heldout"].iloc[0]
    neural_heldout = neural_metrics[neural_metrics["slice"] == "bucket=heldout"].iloc[0]
    neural_final_epoch = neural_training_curve.iloc[-1]
    mujoco_residual_heldout = mujoco_residual_metrics[mujoco_residual_metrics["slice"] == "bucket=heldout"].iloc[0]
    gate_ablation_heldout = mujoco_residual_gate_ablation[mujoco_residual_gate_ablation["slice"] == "bucket=heldout"].set_index("variant")
    gate_ablation_nominal = mujoco_residual_gate_ablation[mujoco_residual_gate_ablation["slice"] == "bucket=nominal"].set_index("variant")
    gated_heldout_reduction = float(gate_ablation_heldout.loc["gated_default", "delta_final_error"])
    off_heldout_reduction = float(gate_ablation_heldout.loc["residual_off", "delta_final_error"])
    always_on_nominal_delta = float(gate_ablation_nominal.loc["always_on", "delta_success_rate"])
    gated_nominal_delta = float(gate_ablation_nominal.loc["gated_default", "delta_success_rate"])
    (REPORTS / "HIGH_FIDELITY_INTERPRETATION.md").write_text(
        f"""# High-Fidelity Interpretation

This evidence tier is bounded simulator evidence, not a full robot-policy result.

## MuJoCo
- Scope: 8 task-shaped 1-DOF probes, 7 perturbation families, 7 policy families, 4 seeds per condition.
- BodyShield mean success: {bodyshield_mujoco:.3f}
- Domain-randomization mean success: {domain_mujoco:.3f}
- Oracle mean success: {oracle_mujoco:.3f}
- Interpretation: the probes check whether perturbation/control logic produces stable MuJoCo dynamics and nontrivial robustness structure. They do not model full robot kinematics, perception, contact geometry, or reset.

## MuJoCo Planar Effector
- Scope: 4 two-axis closed-loop planar end-effector tasks, 7 perturbation families, 7 policy families, 4 seeds per condition.
- BodyShield mean success: {bodyshield_planar:.3f}
- Domain-randomization mean success: {domain_planar:.3f}
- Interpretation: this is a stronger local dynamics probe than the 1-DOF suite because it exercises two-axis delayed/noisy control. It remains a bounded benchmark, not a full robot-policy result.

## ManiSkill
- Scope: {maniskill_executed}/{maniskill_total} selected tabletop tasks executed with CPU `pd_joint_delta_pos` random actions.
- Interpretation: this verifies local ManiSkill task availability and control-mode compatibility. It is not a trained policy baseline.

## Learned MuJoCo Gated Residual Policy
- Scope: supervised residual controller trained on nominal/seen MuJoCo planar corrective labels and evaluated with conservative gating on held-out planar perturbations.
- Gate: residuals are disabled for nominal perturbations and suppressed when instantaneous error is within {float(mujoco_residual_heldout['min_error_multiple']):.1f}x the task tolerance.
- Held-out base final error: {float(mujoco_residual_heldout['base_final_error']):.4f}
- Held-out adapted final error: {float(mujoco_residual_heldout['adapted_final_error']):.4f}
- Held-out final-error reduction: {float(mujoco_residual_heldout['delta_final_error']):.4f}
- Gate ablation: selected gated reduction {gated_heldout_reduction:.4f} versus residual-off reduction {off_heldout_reduction:.4f}; always-on nominal success delta {always_on_nominal_delta:+.3f}; gated nominal success delta {gated_nominal_delta:+.3f}.
- Interpretation: this is a local trained high-fidelity gated residual-policy audit, not an external robot-policy checkpoint or real robot result.

## Safe claim
The local stack now has executable analytic, learned scalar outcome-model, synthetic visual-model, NumPy neural visual-latent WAM, real-video WAM readiness, synthetic trajectory-model, synthetic corrective-adaptation, MuJoCo 1-DOF, MuJoCo planar-effector, learned MuJoCo gated residual-policy, ManiSkill, and external-checkpoint readiness tiers. Only the analytic tier is currently used for the main BodyShield-vs-baseline claim; high-fidelity rows remain local simulator evidence until external trained checkpoints or hardware logs are integrated.
""",
        encoding="utf-8",
    )
    (REPORTS / "MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md").write_text(
        f"""# MuJoCo Gated Residual Policy Interpretation

This is a learned high-fidelity simulator audit with conservative residual gating, not hardware and not an external robot-policy checkpoint.

## Scope
- Environment: local MuJoCo 2-DOF planar end-effector tasks.
- Training data: simulator corrective labels collected on nominal and seen perturbation buckets.
- Model: CPU ridge residual controller over state, target, base command, policy metadata, task id, and perturbation severities.
- Gate: nominal residual scale {float(mujoco_residual_heldout['nominal_residual_scale']):.2f}; non-nominal residual scale {float(mujoco_residual_heldout['residual_scale']):.2f}; no residual when instantaneous error is within {float(mujoco_residual_heldout['min_error_multiple']):.1f}x task tolerance.
- Evaluation: base analytic command versus adapted gated residual command on nominal, seen, and held-out planar perturbations.
- Trace sample: `results/mujoco_residual_policy_trace_sample.jsonl`.

## Held-out performance
- Rollouts: {int(mujoco_residual_heldout['n_rollouts'])}
- Base success rate: {float(mujoco_residual_heldout['base_success_rate']):.3f}
- Adapted success rate: {float(mujoco_residual_heldout['adapted_success_rate']):.3f}
- Base final error: {float(mujoco_residual_heldout['base_final_error']):.4f}
- Adapted final error: {float(mujoco_residual_heldout['adapted_final_error']):.4f}
- Final-error reduction: {float(mujoco_residual_heldout['delta_final_error']):.4f}
- Mean residual norm: {float(mujoco_residual_heldout['mean_residual_norm']):.4f}

## Gate ablation
- Table: `results/mujoco_residual_policy_gate_ablation.csv`.
- Residual-off held-out final-error reduction: {off_heldout_reduction:.4f}
- Selected gated held-out final-error reduction: {gated_heldout_reduction:.4f}
- Always-on nominal success delta: {always_on_nominal_delta:+.3f}
- Selected gated nominal success delta: {gated_nominal_delta:+.3f}

## Safe claim
The package now trains and evaluates a local gated residual policy inside MuJoCo dynamics, reducing the gap between analytic repair and high-fidelity learned-policy evidence while avoiding always-on nominal residuals. It still does not establish performance for external neural robot checkpoints, ManiSkill trained policies, real cameras, resets, contact-rich hardware, or physical transfer.
""",
        encoding="utf-8",
    )
    (REPORTS / "LEARNED_OUTCOME_MODEL_INTERPRETATION.md").write_text(
        f"""# Learned Outcome Model Interpretation

This is a lightweight WAM-style proxy, not a visual world model and not a policy.

## Scope
- Inputs: task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: simulator success rate for a task/robot/policy/perturbation condition.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.

## Held-out performance
- Conditions: {int(learned_heldout['n_conditions'])}
- MAE: {float(learned_heldout['mae']):.3f}
- Brier score: {float(learned_heldout['brier']):.3f}
- AUC at 0.50 success threshold: {float(learned_heldout['auc_at_50']):.3f}

## Safe claim
The model shows that the local artifact can learn a reusable outcome predictor over tasks, robots, policies, and body/control perturbations. It does not establish video-based world modeling, real-robot adaptation, or policy learning from physical attempts.
""",
        encoding="utf-8",
    )
    (REPORTS / "TRAJECTORY_WAM_INTERPRETATION.md").write_text(
        f"""# Trajectory WAM Proxy Interpretation

This is a synthetic proprioceptive trajectory model, not video prediction, neural policy learning, or hardware adaptation.

## Scope
- Inputs: current 2-D state, action, target, task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: next synthetic state delta for action-conditioned traces generated from the analytic BodyShield setup.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/trajectory_wam_trace_sample.jsonl`.

## Held-out performance
- Transitions: {int(trajectory_heldout['n_transitions'])}
- Rollouts: {int(trajectory_heldout['n_rollouts'])}
- Transition state RMSE: {float(trajectory_heldout['transition_state_rmse']):.4f}
- Transition XY RMSE: {float(trajectory_heldout['transition_xy_rmse']):.4f}
- Final XY MAE: {float(trajectory_heldout['final_xy_mae']):.4f}
- Final progress MAE: {float(trajectory_heldout['final_progress_mae']):.4f}

## Safe claim
The package now includes an action-conditioned trajectory-level audit in addition to scalar, visual, and neural-latent prediction. It verifies that BodyShield perturbations can drive a learned next-state/rollout model over synthetic traces. It does not establish real-video WAM performance, real corrective-trace adaptation, or trained robot-policy transfer.
""",
        encoding="utf-8",
    )
    (REPORTS / "CORRECTIVE_ADAPTATION_INTERPRETATION.md").write_text(
        f"""# Corrective Adaptation Interpretation

This is a synthetic corrective-trace adaptation audit, not real-robot online learning, neural policy finetuning, or video-conditioned adaptation.

## Scope
- Source policies: nominal, domain randomization, and BodyShield when available.
- Teacher: analytic oracle-style corrective action target.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/corrective_adaptation_trace_sample.jsonl`.

## Held-out performance
- Rollouts: {int(corrective_heldout['n_rollouts'])}
- Base final error: {float(corrective_heldout['base_final_error']):.4f}
- Adapted final error: {float(corrective_heldout['adapted_final_error']):.4f}
- Final-error reduction: {float(corrective_heldout['delta_final_error']):.4f}
- Base success rate: {float(corrective_heldout['base_success_rate']):.3f}
- Adapted success rate: {float(corrective_heldout['adapted_success_rate']):.3f}
- Progress gain: {float(corrective_heldout['delta_progress']):.4f}

## Safe claim
The package now tests a closed local loop: BodyBreak-style perturbations expose synthetic failures, corrective traces produce a residual action adapter, and held-out rollouts measure whether the adapter reduces drift. This is useful evidence for the adaptation mechanism in the analytic trace world; it does not establish physical adaptation, neural policy learning, or visual WAM transfer.
""",
        encoding="utf-8",
    )
    (REPORTS / "VISUAL_WAM_INTERPRETATION.md").write_text(
        f"""# Visual WAM Proxy Interpretation

This is a synthetic rendered-frame WAM audit, not real camera video, neural foundation-model training, or physical visual adaptation.

## Scope
- Inputs: current two-channel rendered frame, action, task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: next rendered synthetic visual frame from the analytic trajectory generator.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/visual_wam_trace_sample.jsonl`.

## Held-out performance
- Transitions: {int(visual_heldout['n_transitions'])}
- Rollouts: {int(visual_heldout['n_rollouts'])}
- Transition frame MSE: {float(visual_heldout['transition_frame_mse']):.6f}
- Transition PSNR: {float(visual_heldout['transition_psnr_db']):.2f} dB
- Final frame MSE: {float(visual_heldout['final_frame_mse']):.6f}
- Final centroid error: {float(visual_heldout['final_centroid_error']):.4f}

## Safe claim
The package now includes an action-conditioned visual prediction proxy over generated pixel observations. It tests the software path from BodyBreak perturbations to rendered observations to held-out visual rollout prediction. It does not establish real-video WAM learning, neural visual dynamics, or physical transfer.
""",
        encoding="utf-8",
    )
    (REPORTS / "NEURAL_WAM_INTERPRETATION.md").write_text(
        f"""# Neural WAM Proxy Interpretation

This is a NumPy MLP visual-latent WAM audit over generated observations, not real camera video, a foundation video model, or physical visual adaptation.

## Scope
- Inputs: visual latents from the current rendered frame, action, task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: next visual latent extracted from the generated rendered-frame trajectory.
- Model: one-hidden-layer NumPy MLP trained on CPU with deterministic seeds.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/neural_wam_trace_sample.jsonl`.

## Training
- Hidden units: {int(neural_final_epoch['hidden_units'])}
- Max train samples: {int(neural_final_epoch['max_train_samples'])}
- Final epoch: {int(neural_final_epoch['epoch'])}
- Final train latent MSE: {float(neural_final_epoch['train_latent_mse']):.6f}
- Final held-out latent MSE: {float(neural_final_epoch['heldout_latent_mse']):.6f}

## Held-out performance
- Transitions: {int(neural_heldout['n_transitions'])}
- Rollouts: {int(neural_heldout['n_rollouts'])}
- Transition latent MSE: {float(neural_heldout['transition_latent_mse']):.6f}
- Transition centroid error: {float(neural_heldout['transition_centroid_error']):.4f}
- Final latent MSE: {float(neural_heldout['final_latent_mse']):.6f}
- Final centroid error: {float(neural_heldout['final_centroid_error']):.4f}

## Safe claim
The package now includes a trained nonlinear neural audit that predicts action-conditioned visual-state dynamics over synthetic rendered observations. This closes the local missing-neural-dynamics gap, but it still does not establish real-video WAM learning, large-scale foundation-model behavior, high-fidelity robot-policy transfer, or physical adaptation.
""",
        encoding="utf-8",
    )
    audit = pd.DataFrame(completion_audit_rows())
    write_markdown_table(REPORTS / "NON_HARDWARE_AUDIT.md", audit)

    bodyshield = summary[summary["method_id"] == "bodyshield"].set_index("bucket")
    domain_randomization = summary[summary["method_id"] == "domain_randomization"].set_index("bucket")
    heldout_delta = float(bodyshield.loc["heldout", "success_rate"] - domain_randomization.loc["heldout", "success_rate"])
    seen_delta = float(bodyshield.loc["seen", "success_rate"] - domain_randomization.loc["seen", "success_rate"])
    nominal_retention = float(bodyshield.loc["nominal", "success_rate"])
    oracle_total = int(len(oracle_df))
    oracle_feasible = int(oracle_df["feasible"].sum()) if oracle_total else 0
    analytic_table_tex = paper_analytic_success_table(summary)
    search_table_tex = paper_search_table(search_summary)
    mujoco_table_tex = paper_mujoco_table(mujoco_method_summary)
    stress_table_tex = paper_stress_test_table(summary)
    maniskill_sentence = (
        f"The ManiSkill compatibility tier executed {maniskill_executed}/{maniskill_total} selected tabletop tasks "
        r"with CPU \texttt{pd\_joint\_delta\_pos} random actions. It verifies environment availability and control-mode "
        "compatibility, not learned policy performance."
    )

    (RESULTS / "task_suite_cards.csv").write_text(task_cards.to_csv(index=False), encoding="utf-8")
    (RESULTS / "sim_env_availability.csv").write_text(sim_envs.to_csv(index=False), encoding="utf-8")
    (RESULTS / "high_fidelity_benchmark.csv").write_text(high_fidelity.to_csv(index=False), encoding="utf-8")

    (REPORTS / "CLAIM_BOUNDARY.md").write_text(
        f"""# BodyShield Claim Boundary

This non-hardware execution supports a software and analytic-simulation claim only.

Supported now:
- BodyBreak estimates minimal breaking perturbations in a CPU analytic simulator and includes a dense post-hoc minimality challenge for representative found breaks.
- BodyShield repair uses discovered failure axes to improve worst-case simulated success.
- Baseline comparisons, confidence intervals, plots, synthetic rollout GIFs, logs, and a paper draft with generated result tables are reproducible from this folder.

Not supported yet:
- No real SO-ARM101/SO-101 hardware result has been run.
- No external/full-scale robot-policy MuJoCo/ManiSkill benchmark suite has been run; bounded simulator probes, a local MuJoCo gated residual-policy audit, and an external-checkpoint readiness harness are logged.
- No real-camera or foundation-scale WAM training has been run; generated visual WAM audits and a real-video frame-manifest readiness harness are logged.
- No real/external corrective-trace adaptation has been run; synthetic corrective adaptation and a corrective-trace manifest readiness harness are logged.
- Camera verifier, reset reliability, noise floor, and safety-stop statistics are placeholders until hardware gates pass.

Agenda fit:
This remains a strong Jason-agenda project because the central mechanism is failure diagnosis, action-representation repair, and transfer under embodiment-control shift rather than hardware design.
""",
        encoding="utf-8",
    )

    (REPORTS / "SIMULATION_SUMMARY.md").write_text(
        f"""# Simulation Summary

Code version: `{code_version}`

Generated artifacts:
- Flat trial table: `results/trials.csv`
- Compressed trial table: `results/trials.parquet`
- Nested schema-compliant sample log: `{jsonl_path.relative_to(ROOT).as_posix()}` ({JSONL_SAMPLE_LIMIT} records; full trials are in the flat CSV)
- Formal JSON Schema: `trial_schema.schema.json`
- Schema validation summary: `results/schema_validation_summary.json`
- Search comparison: `results/breaking_search.csv`
- Dense BodyBreak minimality challenge: `results/bodybreak_minimality_audit.csv`, `reports/BODYBREAK_MINIMALITY_AUDIT.md`
- Repair history: `results/repair_history.csv`
- Robustness profiles: `results/robustness_profiles.csv`
- Threshold sensitivity: `results/threshold_sensitivity.csv`
- Oracle feasibility checks: `results/oracle_feasibility.csv`
- Secondary metrics and failure taxonomy: `results/secondary_metrics_by_method.csv`, `results/failure_taxonomy_counts.csv`
- Learned outcome-model audit: `results/learned_outcome_model_eval.csv`, `reports/LEARNED_OUTCOME_MODEL_TABLE.md`, `reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md`
- Synthetic visual WAM proxy audit: `results/visual_wam_eval.csv`, `results/visual_wam_rollouts.csv`, `results/visual_wam_trace_sample.jsonl`, `reports/VISUAL_WAM_INTERPRETATION.md`
- Neural visual-latent WAM proxy audit: `results/neural_wam_eval.csv`, `results/neural_wam_rollouts.csv`, `results/neural_wam_training_curve.csv`, `reports/NEURAL_WAM_INTERPRETATION.md`
- Real-video WAM readiness: `results/real_video_wam_readiness.csv`, `reports/REAL_VIDEO_WAM_READINESS.md`
- Learned MuJoCo gated residual-policy audit: `results/mujoco_residual_policy_eval.csv`, `results/mujoco_residual_policy_rollouts.csv`, `results/mujoco_residual_policy_gate_ablation.csv`, `results/mujoco_residual_policy_trace_sample.jsonl`, `reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md`, `reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md`
- Trajectory WAM proxy audit: `results/trajectory_wam_eval.csv`, `results/trajectory_wam_rollouts.csv`, `results/trajectory_wam_trace_sample.jsonl`, `reports/TRAJECTORY_WAM_INTERPRETATION.md`
- Corrective-adaptation audit: `results/corrective_adaptation_eval.csv`, `results/corrective_adaptation_rollouts.csv`, `results/corrective_adaptation_trace_sample.jsonl`, `reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md`
- Corrective-trace readiness: `results/corrective_trace_readiness.csv`, `reports/CORRECTIVE_TRACE_READINESS.md`
- High-fidelity bounded probes: `results/high_fidelity_benchmark.csv`, `reports/MUJOCO_METHOD_SUMMARY_TABLE.md`, `reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md`, `reports/MUJOCO_PLANAR_PROBE_TABLE.md`, `reports/MUJOCO_PERTURBATION_SUMMARY_TABLE.md`, `reports/MANISKILL_TASK_SUMMARY_TABLE.md`
- External trained-policy readiness: `results/external_policy_benchmark_readiness.csv`, `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md`
- Synthetic rollout media: `results/videos/bodyshield_synthetic_*.gif`, `results/simulation_rollout_videos.csv`, `reports/SIMULATION_ROLLOUT_VIDEOS.md`
- Figures: `results/figures/*.pdf` and `results/figures/*.png`

Headline analytic-simulation results:
- BodyShield nominal success retention: {nominal_retention:.3f}
- BodyShield vs domain randomization on seen perturbations: {seen_delta:+.3f}
- BodyShield vs domain randomization on held-out perturbations: {heldout_delta:+.3f}

Interpretation:
These are generated by a transparent CPU analytic surrogate. They are useful for validating the software stack, trial accounting, statistical machinery, and reviewer-defense workflow. They must not be presented as real robot or high-fidelity physics evidence.

External checkpoint readiness:
The readiness harness produced {external_readiness['rows']} rows, including {external_readiness['fixtures_passed']} passing deterministic fixture smoke row(s), {external_readiness['external_specs']} external checkpoint spec row(s), and {external_readiness['missing_checkpoints']} missing checkpoint row(s). It validates the interface path only; it is not external trained-policy benchmark evidence.

Real-video WAM readiness:
The readiness harness produced {real_video_readiness['rows']} rows, including {real_video_readiness['fixture_smokes']} passing deterministic fixture fit-smoke row(s), {real_video_readiness['real_dataset_specs']} real-video dataset spec row(s), and {real_video_readiness['missing_datasets']} missing real-video dataset row(s). It validates frame-manifest ingestion only; it is not real-video or foundation-scale WAM evidence.

Corrective-trace readiness:
The readiness harness produced {corrective_trace_readiness_summary_rows['rows']} rows, including {corrective_trace_readiness_summary_rows['fixture_smokes']} passing deterministic fixture fit-smoke row(s), {corrective_trace_readiness_summary_rows['trace_dataset_specs']} real/external corrective trace dataset spec row(s), and {corrective_trace_readiness_summary_rows['missing_datasets']} missing corrective trace dataset row(s). It validates trace-manifest ingestion only; it is not real corrective-trace adaptation evidence.
""",
        encoding="utf-8",
    )

    (REPORTS / "CLAIM_LEDGER.md").write_text(
        f"""# Claim Ledger

| Claim | Mechanism | Evidence | Scope | Wording boundary |
|---|---|---|---|---|
| Nominal success can hide embodiment assumptions | Compare nominal success with estimated breaking radius under perturbations | `results/nominal_vs_robustness_radius.csv` | CPU analytic surrogate, 8 tasks, 6 robot archetypes | Say "in the analytic simulator"; do not claim real deployment yet. |
| BodyBreak finds low-cost failures under an evaluator budget | Cost-ordered grid scaffold plus active-axis subset refinement and leftover-budget lower-cost random challenges, plus dense post-hoc candidate-pool challenge for representative found breaks | `results/breaking_search.csv`, `results/bodybreak_minimality_audit.csv`, `reports/SEARCH_COMPARISON_TABLE.md`, `reports/BODYBREAK_MINIMALITY_AUDIT.md` | Search tasks for nominal, human/effect, and EPEC-style policies | Say "estimated minimal"; do not claim mathematically global minimality. |
| BodyShield improves repaired robustness | Repair sensitivities along discovered failure axes and evaluate seen/held-out buckets | `results/summary_by_method_bucket.csv` | Analytic surrogate with fixed perturbation library | Report deltas with confidence intervals; do not claim physical transfer. |
| Lightweight WAM-style outcome prediction is locally executable | Ridge-logit predictor over task, robot, policy, and perturbation features | `results/learned_outcome_model_eval.csv`, `reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md` | Tabular analytic outcome predictor | Do not present as visual world modeling or real adaptation. |
| Synthetic visual WAM proxy is locally executable | Ridge predictor over action-conditioned rendered two-channel frames | `results/visual_wam_eval.csv`, `results/visual_wam_rollouts.csv`, `reports/VISUAL_WAM_INTERPRETATION.md` | Generated pixel observations from analytic traces | Do not present as real video, neural foundation WAM training, or physical transfer. |
| Synthetic rollout media are locally executable | Three generated GIF rollouts compare nominal reference, nominal under BodyBreak perturbation, and BodyShield under the same perturbation | `results/videos/bodyshield_synthetic_*.gif`, `results/simulation_rollout_videos.csv`, `reports/SIMULATION_ROLLOUT_VIDEOS.md` | Synthetic renderer over analytic trajectory traces | Do not present as real camera video, verifier clips, hardware data, or physical transfer. |
| Neural visual-latent WAM proxy is locally executable | One-hidden-layer NumPy MLP over action-conditioned generated visual latents | `results/neural_wam_eval.csv`, `results/neural_wam_rollouts.csv`, `results/neural_wam_training_curve.csv`, `reports/NEURAL_WAM_INTERPRETATION.md` | Synthetic visual latents from analytic traces | Do not present as real-video WAM training, large-scale foundation modeling, or physical transfer. |
| Real-video WAM readiness is locally executable | JSON spec validation, frame-manifest/action-label detection, deterministic fixture fit smoke, and real-frame manifest smoke for present datasets | `configs/real_video_wam_readiness.example.json`, `results/real_video_wam_readiness.csv`, `reports/REAL_VIDEO_WAM_READINESS.md` | Harness/readiness only; current example real-video dataset is missing | Do not present as real-video WAM, foundation-scale training, camera-verifier evidence, or physical transfer. |
| Learned MuJoCo gated residual policy is locally executable | Ridge residual controller trained on simulator corrective labels inside 2-DOF MuJoCo planar tasks, with nominal and near-success residual suppression plus residual-off/always-on gate ablations | `results/mujoco_residual_policy_eval.csv`, `results/mujoco_residual_policy_rollouts.csv`, `results/mujoco_residual_policy_gate_ablation.csv`, `reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md`, `reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md` | Local MuJoCo planar tasks with nominal/seen training perturbations and held-out simulator perturbations | Do not present as an external robot-policy checkpoint, full ManiSkill benchmark, contact-rich hardware result, or physical transfer. |
| Synthetic trajectory-level WAM proxy is locally executable | Ridge next-state predictor over action-conditioned synthetic proprioceptive traces | `results/trajectory_wam_eval.csv`, `results/trajectory_wam_rollouts.csv`, `reports/TRAJECTORY_WAM_INTERPRETATION.md` | Analytic trajectory proxy with sampled traces | Do not present as video prediction, real-video WAM training, or physical corrective-trace adaptation. |
| Synthetic corrective-trace adaptation is locally executable | Ridge residual action adapter trained from generated corrective traces | `results/corrective_adaptation_eval.csv`, `results/corrective_adaptation_rollouts.csv`, `reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md` | Analytic trace-world adaptation proxy | Do not present as real online learning, neural policy finetuning, or hardware recovery. |
| Corrective-trace dataset readiness is locally executable | JSON spec validation, corrective-trace manifest detection, deterministic fixture residual-fit smoke, and residual-fit smoke for present datasets | `configs/corrective_trace_readiness.example.json`, `results/corrective_trace_readiness.csv`, `reports/CORRECTIVE_TRACE_READINESS.md` | Harness/readiness only; current example real/external corrective trace dataset is missing | Do not present as real corrective-trace adaptation, online learning, policy finetuning, hardware recovery, or physical transfer. |
| Local high-fidelity backends can execute bounded probes | MuJoCo 8-task 1-DOF probes, MuJoCo 4-task planar-effector probes, and ManiSkill 6-task CPU random-action suite | `results/high_fidelity_benchmark.csv` | Bounded simulator compatibility and dynamics benchmark | Do not present as full trained robot policy benchmark evidence. |
| External policy benchmark readiness is locally executable | JSON spec validation, checkpoint-path detection, deterministic fixture smoke, and adapter interface smoke for present checkpoints | `configs/external_policy_benchmark.example.json`, `results/external_policy_benchmark_readiness.csv`, `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md` | Harness/readiness only; current example external checkpoint is missing | Do not present as external/full-scale trained-policy MuJoCo/ManiSkill rollout evidence. |
| Claimed analytic failures are not all task impossibility | Oracle feasibility policy is evaluated at found BodyBreak perturbations | `results/oracle_feasibility.csv` ({oracle_feasible}/{oracle_total} marked feasible) | Analytic feasibility only | Hardware oracle remains pending. |
| Results include secondary costs | Execution time, path length, retries, tracking/load proxies, verifier confidence | `results/secondary_metrics_by_method.csv` | Simulated metrics only | Do not use these as hardware safety evidence. |
| Outputs are reproducible and auditable | Artifact hashes, compressed trials, portable release ZIP, release payload manifest/checksums, unpacked-payload verifier, release-payload extraction audit, release-byte determinism audit, extracted-release runtime audit, portable-hygiene audit, artifact-inventory audit, evidence-reference consistency audit, environment dependency audit, config/schema audit, source/import audit, derived-results recomputation audit, generated-results integrity audit, paper-source audit, claim-boundary audit, command-surface audit, visual-artifact audit, and automated pack verification are generated after each run | `reports/ARTIFACT_MANIFEST.csv`, `release/bodyshield_non_hardware_release.zip`, `release/RELEASE_BUNDLE_MANIFEST.csv`, `release/RELEASE_BUNDLE_CHECKSUMS.txt`, `scripts/verify_release_payload.py`, `scripts/run_release_payload_audit.py`, `scripts/run_release_determinism_audit.py`, `scripts/run_release_runtime_audit.py`, `scripts/run_portable_hygiene_audit.py`, `scripts/run_artifact_inventory_audit.py`, `scripts/run_derived_results_audit.py`, `scripts/run_config_schema_audit.py`, `scripts/run_source_import_audit.py`, `scripts/run_paper_source_audit.py`, `results/release_payload_audit.csv`, `results/release_determinism_audit.csv`, `results/release_runtime_audit.csv`, `results/portable_hygiene_audit.csv`, `results/artifact_inventory_audit.csv`, `results/derived_results_audit.csv`, `results/evidence_consistency_audit.csv`, `results/environment_dependency_audit.csv`, `results/environment_snapshot.json`, `results/config_schema_audit.csv`, `results/source_import_audit.csv`, `results/results_integrity_audit.csv`, `results/paper_source_audit.csv`, `results/claim_boundary_audit.csv`, `results/command_surface_audit.csv`, `results/visual_artifact_audit.csv`, `reports/RELEASE_PAYLOAD_AUDIT.md`, `reports/RELEASE_DETERMINISM_AUDIT.md`, `reports/RELEASE_RUNTIME_AUDIT.md`, `reports/PORTABLE_HYGIENE_AUDIT.md`, `reports/ARTIFACT_INVENTORY_AUDIT.md`, `reports/DERIVED_RESULTS_AUDIT.md`, `reports/EVIDENCE_CONSISTENCY_AUDIT.md`, `reports/ENVIRONMENT_DEPENDENCY_AUDIT.md`, `reports/CONFIG_SCHEMA_AUDIT.md`, `reports/SOURCE_IMPORT_AUDIT.md`, `reports/RESULTS_INTEGRITY_AUDIT.md`, `reports/PAPER_SOURCE_AUDIT.md`, `reports/CLAIM_BOUNDARY_AUDIT.md`, `reports/COMMAND_SURFACE_AUDIT.md`, `reports/VISUAL_ARTIFACT_AUDIT.md`, `reports/RELEASE_BUNDLE.md`, `reports/PACK_VERIFICATION.md`, `results/trials.parquet` | Local files only | Does not replace external archival upload, public repository release, or independent replication. |
""",
        encoding="utf-8",
    )

    (REPORTS / "REPRODUCIBILITY_MANIFEST.md").write_text(
        f"""# Reproducibility Manifest

Code version: `{code_version}`

Python: `{platform.python_version()}`

Primary commands:
```powershell
python -m pytest -q
python scripts\\run_external_policy_benchmark.py
python scripts\\run_real_video_wam_readiness.py
python scripts\\run_corrective_trace_readiness.py
python scripts\\run_artifact_inventory_audit.py
python scripts\\run_claim_boundary_audit.py
python scripts\\run_command_surface_audit.py
python scripts\\run_config_schema_audit.py
python scripts\\run_derived_results_audit.py
python scripts\\run_environment_dependency_audit.py
python scripts\\run_results_integrity_audit.py
python scripts\\run_source_import_audit.py
python scripts\\run_paper_source_audit.py
python scripts\\run_portable_hygiene_audit.py
python scripts\\run_visual_artifact_audit.py
python scripts\\run_evidence_consistency_audit.py
python scripts\\build_release_bundle.py
python scripts\\run_release_payload_audit.py
python scripts\\run_release_determinism_audit.py
python scripts\\run_release_runtime_audit.py
python scripts\\run_non_hardware.py
python scripts\\verify_non_hardware_pack.py --write-reports
```

Inputs:
- `configs/simulation_bodyshield_maxout.yaml`
- `configs/external_policy_benchmark.example.json`
- `configs/real_video_wam_readiness.example.json`
- `configs/corrective_trace_readiness.example.json`
- `tasks.yaml`
- `data_schema.json`

Generated tables:
- `results/trials.csv`
- `results/trials.parquet`
- `results/trials_sample.jsonl`
- `results/schema_validation_summary.json`
- `results/breaking_search.csv`
- `results/bodybreak_minimality_audit.csv`
- `results/summary_by_method_bucket.csv`
- `results/robustness_profiles.csv`
- `results/threshold_sensitivity.csv`
- `results/oracle_feasibility.csv`
- `results/method_deltas_vs_bodyshield.csv`
- `results/learned_outcome_model_eval.csv`
- `results/learned_outcome_axis_weights.csv`
- `results/learned_outcome_predictions.csv`
- `results/visual_wam_eval.csv`
- `results/visual_wam_feature_weights.csv`
- `results/visual_wam_rollouts.csv`
- `results/visual_wam_trace_sample.jsonl`
- `results/neural_wam_eval.csv`
- `results/neural_wam_rollouts.csv`
- `results/neural_wam_training_curve.csv`
- `results/neural_wam_trace_sample.jsonl`
- `results/real_video_wam_readiness.csv`
- `results/mujoco_residual_policy_eval.csv`
- `results/mujoco_residual_policy_rollouts.csv`
- `results/mujoco_residual_policy_weights.csv`
- `results/mujoco_residual_policy_gate_ablation.csv`
- `results/mujoco_residual_policy_trace_sample.jsonl`
- `results/trajectory_wam_eval.csv`
- `results/trajectory_wam_axis_weights.csv`
- `results/trajectory_wam_rollouts.csv`
- `results/trajectory_wam_trace_sample.jsonl`
- `results/corrective_adaptation_eval.csv`
- `results/corrective_adaptation_residual_weights.csv`
- `results/corrective_adaptation_rollouts.csv`
- `results/corrective_adaptation_trace_sample.jsonl`
- `results/corrective_trace_readiness.csv`
- `results/artifact_inventory_audit.csv`
- `results/claim_boundary_audit.csv`
- `results/command_surface_audit.csv`
- `results/evidence_consistency_audit.csv`
- `results/environment_dependency_audit.csv`
- `results/environment_snapshot.json`
- `results/config_schema_audit.csv`
- `results/derived_results_audit.csv`
- `results/source_import_audit.csv`
- `results/results_integrity_audit.csv`
- `results/paper_source_audit.csv`
- `results/portable_hygiene_audit.csv`
- `results/visual_artifact_audit.csv`
- `results/release_payload_audit.csv`
- `results/release_determinism_audit.csv`
- `results/release_runtime_audit.csv`
- `results/simulation_rollout_videos.csv`
- `results/secondary_metrics_by_method.csv`
- `results/failure_taxonomy_counts.csv`
- `results/nominal_vs_robustness_radius.csv`
- `results/high_fidelity_benchmark.csv`
- `results/external_policy_benchmark_readiness.csv`
- `trial_schema.schema.json`

Generated reports:
- `reports/ARTIFACT_MANIFEST.csv`
- `reports/ARTIFACT_MANIFEST.md`
- `reports/RELEASE_BUNDLE.md`
- `reports/ARTIFACT_INVENTORY_AUDIT.md`
- `reports/CLAIM_BOUNDARY_AUDIT.md`
- `reports/COMMAND_SURFACE_AUDIT.md`
- `reports/EVIDENCE_CONSISTENCY_AUDIT.md`
- `reports/ENVIRONMENT_DEPENDENCY_AUDIT.md`
- `reports/CONFIG_SCHEMA_AUDIT.md`
- `reports/DERIVED_RESULTS_AUDIT.md`
- `reports/SOURCE_IMPORT_AUDIT.md`
- `reports/RESULTS_INTEGRITY_AUDIT.md`
- `reports/PAPER_SOURCE_AUDIT.md`
- `reports/PORTABLE_HYGIENE_AUDIT.md`
- `reports/VISUAL_ARTIFACT_AUDIT.md`
- `reports/RELEASE_PAYLOAD_AUDIT.md`
- `reports/RELEASE_DETERMINISM_AUDIT.md`
- `reports/RELEASE_RUNTIME_AUDIT.md`
- `reports/PACK_VERIFICATION.json`
- `reports/PACK_VERIFICATION.md`
- `reports/NON_HARDWARE_AUDIT.md`
- `reports/CLAIM_LEDGER.md`
- `reports/NON_HARDWARE_REQUIREMENTS_TRACE.md`
- `reports/BUDGET_AND_FAIRNESS_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT_TABLE.md`
- `reports/METHOD_DELTA_TABLE.md`
- `reports/AGENDA_FIT_MEMO.md`
- `reports/LEARNED_OUTCOME_MODEL_TABLE.md`
- `reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md`
- `reports/VISUAL_WAM_TABLE.md`
- `reports/VISUAL_WAM_FEATURE_WEIGHT_TABLE.md`
- `reports/VISUAL_WAM_INTERPRETATION.md`
- `reports/NEURAL_WAM_TABLE.md`
- `reports/NEURAL_WAM_TRAINING_CURVE.md`
- `reports/NEURAL_WAM_INTERPRETATION.md`
- `reports/REAL_VIDEO_WAM_READINESS.md`
- `reports/REAL_VIDEO_WAM_READINESS_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_WEIGHT_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md`
- `reports/TRAJECTORY_WAM_TABLE.md`
- `reports/TRAJECTORY_WAM_AXIS_TABLE.md`
- `reports/TRAJECTORY_WAM_INTERPRETATION.md`
- `reports/CORRECTIVE_ADAPTATION_TABLE.md`
- `reports/CORRECTIVE_ADAPTATION_WEIGHT_TABLE.md`
- `reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md`
- `reports/CORRECTIVE_TRACE_READINESS.md`
- `reports/CORRECTIVE_TRACE_READINESS_TABLE.md`
- `reports/SIMULATION_ROLLOUT_VIDEOS.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS_TABLE.md`
- `reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md`
- `reports/MUJOCO_PLANAR_PROBE_TABLE.md`
- `reports/REVIEWER_ATTACK_CLOSURE.md`
- `reports/CITATION_VERIFICATION_TABLE.md`
- `reports/PREBUTTAL.md`
- `reports/PAPER_REVIEWER_RISK_AUDIT.md`
- `reports/FIGURE_CAPTIONS.md`
- `reports/HIGH_FIDELITY_INTERPRETATION.md`
- `paper/bodyshield_non_hardware_draft.pdf`

Generated media:
- `results/videos/bodyshield_synthetic_nominal_reference.gif`
- `results/videos/bodyshield_synthetic_bodybreak_failure.gif`
- `results/videos/bodyshield_synthetic_bodyshield_repair.gif`

Release bundle:
- `release/bodyshield_non_hardware_release.zip`
- `release/RELEASE_BUNDLE_MANIFEST.csv`
- `release/RELEASE_BUNDLE_CHECKSUMS.txt`
- `release/RELEASE_README.md`

After unpacking the release ZIP:
```powershell
python scripts\\verify_release_payload.py
```

Determinism:
All analytic evaluations use stable SHA-256-derived seeds through `bodyshield.sim.stable_seed`.

Verification:
`reports/PACK_VERIFICATION.md`, `reports/RELEASE_PAYLOAD_AUDIT.md`, `reports/RELEASE_DETERMINISM_AUDIT.md`, and `reports/RELEASE_RUNTIME_AUDIT.md` are pack-side verifier outputs. They are intentionally excluded from `reports/ARTIFACT_MANIFEST.csv` and from the release payload to avoid self-referential manifest hash churn. `release/RELEASE_BUNDLE_MANIFEST.csv` is the authoritative archive inventory. The release bundle is local export evidence only; it is not an external archival upload.
""",
        encoding="utf-8",
    )

    (REPORTS / "PREBUTTAL.md").write_text(
        """# Reviewer Prebuttal

## This is just domain randomization.
BodyShield is framed as falsification-guided repair, not broad random sampling. The current analytic evidence reports BodyBreak search separately from domain randomization and random tuning, then evaluates repair on seen and held-out buckets.

## Minimal perturbation is overclaimed.
The paper draft and claim ledger use "estimated minimal" and report search budget, break-found rate, threshold sensitivity, and a dense post-hoc candidate-pool challenge for representative BodyBreak cases. Global optimality is not claimed.

## The simulator is too synthetic.
Correct for the current local execution. Reports explicitly label the main claim as analytic-simulation-only, add tabular outcome, synthetic visual, synthetic rollout GIF media, NumPy neural visual-latent, synthetic trajectory, synthetic corrective-adaptation, learned MuJoCo gated residual-policy audits with gate ablation against residual-off and always-on variants, external-checkpoint readiness, real-video WAM frame-manifest readiness, and corrective-trace dataset readiness. Real-video/foundation-scale WAM training, external/full-scale trained-policy MuJoCo/ManiSkill rollouts, real corrective traces, and real robot results remain missing evidence slots.

## The repair might be too conservative.
Nominal retention, execution time, path length, retries, and secondary safety proxies are logged and summarized. A method that wins only by slowing down should be visible in `results/secondary_metrics_by_method.csv`.

## Failures may be impossible tasks.
`results/oracle_feasibility.csv` checks oracle success at BodyBreak perturbations. Hardware oracle evidence is still required before physical claims.
""",
        encoding="utf-8",
    )

    (REPORTS / "FIGURE_CAPTIONS.md").write_text(
        """# Figure Captions

## `results/figures/bodyshield_mechanism.pdf`
Conceptual pipeline: nominal policy evaluation, BodyBreak failure search, failure-axis attribution, and BodyShield repair. This is a schematic, not empirical evidence.

## `results/figures/breaking_search_comparison.pdf`
Search comparison across random, one-axis, grid, and BodyBreak modes. Panel 1 reports found-break-only estimated costs, Panel 2 reports break-found rate, and Panel 3 reports evaluator calls used under the fixed search budget.

## `results/figures/bodybreak_minimality_audit.pdf`
Dense BodyBreak minimality challenge. Compares representative BodyBreak found-break costs against a larger deterministic local candidate pool with independent sampled confirmation and reports cost regret. This is an audit of estimated minimality, not a mathematical proof of global optimality.

## `results/figures/repair_seen_heldout.pdf`
Success rate by method and perturbation bucket. Wilson confidence intervals are reported in `reports/SIMULATION_BUCKET_SUMMARY_TABLE.md`.

## `results/figures/nominal_vs_radius.pdf`
Nominal success versus estimated robustness radius on the SO101-style push-block analytic probe. This supports the limited claim that nominal success and robustness radius can decouple in the analytic simulator.

## `results/figures/high_fidelity_summary.pdf`
Bounded MuJoCo and ManiSkill simulator checks. The first MuJoCo panel averages success over task-shaped 1-DOF probes, the second MuJoCo panel reports 2-DOF planar-effector probes, and the ManiSkill panel reports random-action reward over installed CPU tabletop tasks. This figure verifies simulator execution and bounded dynamics behavior; the separate residual-policy figure covers local MuJoCo gated residual learning. Neither is external/full-scale trained-policy evidence.

## `results/figures/trajectory_wam_summary.pdf`
Synthetic trajectory WAM proxy audit. The first panel compares true and predicted final rollout error; the second reports autoregressive final-XY drift by perturbation bucket. This verifies a local action-conditioned trajectory-modeling path, not visual prediction or real corrective-trace adaptation.

## `results/figures/visual_wam_summary.pdf`
Synthetic visual WAM proxy audit. The first panel reports final rendered-object centroid drift by perturbation bucket; the second reports one-step rendered-frame PSNR by split. This verifies a generated-frame prediction path, not real camera video or neural foundation-WAM training.

## `results/figures/neural_wam_summary.pdf`
Neural visual-latent WAM proxy audit. The first panel shows NumPy MLP train/held-out latent prediction error over epochs; the second reports autoregressive final-centroid drift by perturbation bucket. This verifies a local nonlinear visual-latent dynamics path, not real-video foundation-model training or physical transfer.

## `results/figures/mujoco_residual_policy_summary.pdf`
Learned MuJoCo gated residual-policy audit. The first panel compares base and adapted planar final error by bucket; the second reports held-out final-error reduction by source policy. This verifies a local simulator residual-action learning path with nominal and near-success residual suppression, not an external robot-policy checkpoint, full ManiSkill benchmark, or hardware transfer.

## `results/figures/mujoco_residual_gate_ablation.pdf`
MuJoCo residual gate ablation. Compares residual-off, always-on, non-nominal-only, and selected gated residual variants; the left panel reports held-out final-error reduction, and the right panel reports nominal success delta. This justifies the conservative gate as local simulator evidence, not external-policy transfer.

## `results/figures/corrective_adaptation_summary.pdf`
Synthetic corrective-trace adaptation audit. The first panel compares base and adapted final error by bucket; the second reports held-out final-error reduction by source policy. This verifies a local residual-action adaptation path over generated traces, not real online learning or neural policy finetuning.

## `results/videos/bodyshield_synthetic_*.gif`
Synthetic rollout media for visual inspection of a nominal reference, the nominal policy under a BodyBreak perturbation, and BodyShield under the same perturbation. These GIFs use generated visual frames from the analytic trajectory proxy; they are not real camera video, verifier clips, or hardware evidence.
""",
        encoding="utf-8",
    )

    (REPORTS / "PAPER_REVIEWER_RISK_AUDIT.md").write_text(
        """# Paper Reviewer Risk Audit

| Severity | Location | Likely complaint | Fix already applied | Remaining evidence slot |
|---|---|---|---|---|
| High | Simulation Results | Evidence is mostly analytic and may not transfer to real contact dynamics. | Claim boundary, ledger, learned scalar/visual/neural-latent/trajectory/corrective audits, learned MuJoCo gated residual-policy audit with gate ablation, bounded high-fidelity benchmark tables, and external-checkpoint readiness reporting separate evidence tiers. | Real-video WAM, external/full-scale trained-policy MuJoCo/ManiSkill rollout benchmark, or hardware. |
| High | BodyBreak | Minimal perturbation sounds globally optimal. | Paper uses "estimated" and reports budgets, fallback rows, threshold sensitivity, and a dense post-hoc minimality challenge. | Formal global proof or stronger high-fidelity optimizer if making stronger claims. |
| High | BodyShield | Repair could win by being conservative. | Secondary metrics include execution time, path length, retries, and nominal retention. | Physical execution-time/path-length measurements. |
| Medium | MuJoCo residual policy | The residual gate could look arbitrary. | Gate ablation compares residual-off, always-on, non-nominal-only, and selected gated variants for held-out gain and nominal preservation. | External trained-policy checkpoints or hardware traces. |
| Medium | External policy benchmarks | A reader may expect imported trained-policy checkpoints. | `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md` records fixture smoke and missing-checkpoint rows explicitly. | Real external checkpoints plus full task-rollout adapters. |
| Medium | Media artifacts | Synthetic GIFs might be mistaken for real videos. | `reports/SIMULATION_ROLLOUT_VIDEOS.md` and the claim ledger label them as generated rollout media only. | Real camera/verifier videos from hardware. |
| Medium | Real-video WAM | A reader may expect camera sequences or foundation-video training. | `reports/REAL_VIDEO_WAM_READINESS.md` records fixture smoke and missing-dataset rows explicitly. | Real camera frame manifests plus substantive real-video/foundation WAM training. |
| Medium | Corrective traces | A reader may expect real failed-attempt corrections or online adaptation. | `reports/CORRECTIVE_TRACE_READINESS.md` records fixture smoke and missing-dataset rows explicitly. | Real robot or external high-fidelity corrective trace datasets plus substantive adaptation. |
| Medium | Baselines | Domain randomization and sysID baselines may be too stylized. | Separate random tuning, domain randomization, grid, robust control, sysID, oracle, EPEC, and human/effect policies are implemented. | External controller baselines in physics/hardware. |
| Medium | Feasibility | Perturbations may make tasks impossible. | Oracle feasibility passes for all analytic BodyBreak failures. | Hardware oracle feasibility. |

## Safer Wording

| Risky wording | Safer wording |
|---|---|
| BodyBreak finds the minimal perturbation. | BodyBreak estimates the lowest-cost breaking perturbation found under a fixed evaluator budget. |
| BodyShield transfers to held-out physical modifications. | BodyShield improves held-out analytic perturbation families; physical transfer remains untested until hardware. |
| The method is simulator independent. | The software stack separates analytic, learned scalar/visual/neural-latent/trajectory/corrective proxy, learned MuJoCo gated residual-policy, bounded MuJoCo, bounded ManiSkill, and future hardware evidence tiers. |
""",
        encoding="utf-8",
    )

    (ROOT / "README_EXECUTION.md").write_text(
        f"""# BodyShield Non-Hardware Execution

Current code version: `{code_version}`

Run:
```powershell
python -m pytest -q
python scripts\\run_external_policy_benchmark.py
python scripts\\run_real_video_wam_readiness.py
python scripts\\run_corrective_trace_readiness.py
python scripts\\run_artifact_inventory_audit.py
python scripts\\run_claim_boundary_audit.py
python scripts\\run_command_surface_audit.py
python scripts\\run_config_schema_audit.py
python scripts\\run_derived_results_audit.py
python scripts\\run_environment_dependency_audit.py
python scripts\\run_results_integrity_audit.py
python scripts\\run_source_import_audit.py
python scripts\\run_paper_source_audit.py
python scripts\\run_portable_hygiene_audit.py
python scripts\\run_visual_artifact_audit.py
python scripts\\run_evidence_consistency_audit.py
python scripts\\build_release_bundle.py
python scripts\\run_release_payload_audit.py
python scripts\\run_release_determinism_audit.py
python scripts\\run_release_runtime_audit.py
python scripts\\run_non_hardware.py
python scripts\\verify_non_hardware_pack.py --write-reports
```

Primary outputs:
- `reports/NON_HARDWARE_COMPLETE.md`
- `reports/NON_HARDWARE_AUDIT.md`
- `reports/NON_HARDWARE_REQUIREMENTS_TRACE.md`
- `reports/BUDGET_AND_FAIRNESS_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT.md`
- `reports/CLAIM_LEDGER.md`
- `reports/REPRODUCIBILITY_MANIFEST.md`
- `reports/RELEASE_BUNDLE.md`
- `reports/ARTIFACT_INVENTORY_AUDIT.md`
- `reports/CLAIM_BOUNDARY_AUDIT.md`
- `reports/COMMAND_SURFACE_AUDIT.md`
- `reports/EVIDENCE_CONSISTENCY_AUDIT.md`
- `reports/ENVIRONMENT_DEPENDENCY_AUDIT.md`
- `reports/CONFIG_SCHEMA_AUDIT.md`
- `reports/DERIVED_RESULTS_AUDIT.md`
- `reports/SOURCE_IMPORT_AUDIT.md`
- `reports/RESULTS_INTEGRITY_AUDIT.md`
- `reports/PAPER_SOURCE_AUDIT.md`
- `reports/PORTABLE_HYGIENE_AUDIT.md`
- `reports/VISUAL_ARTIFACT_AUDIT.md`
- `reports/RELEASE_PAYLOAD_AUDIT.md`
- `reports/RELEASE_DETERMINISM_AUDIT.md`
- `reports/RELEASE_RUNTIME_AUDIT.md`
- `reports/PACK_VERIFICATION.md`
- `reports/METHOD_DELTA_TABLE.md`
- `reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md`
- `reports/VISUAL_WAM_INTERPRETATION.md`
- `reports/SIMULATION_ROLLOUT_VIDEOS.md`
- `reports/NEURAL_WAM_INTERPRETATION.md`
- `reports/REAL_VIDEO_WAM_READINESS.md`
- `reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md`
- `reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md`
- `reports/TRAJECTORY_WAM_INTERPRETATION.md`
- `reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md`
- `reports/CORRECTIVE_TRACE_READINESS.md`
- `reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md`
- `reports/MUJOCO_PLANAR_PROBE_TABLE.md`
- `results/trials.csv`
- `results/bodybreak_minimality_audit.csv`
- `results/visual_wam_rollouts.csv`
- `results/simulation_rollout_videos.csv`
- `results/neural_wam_rollouts.csv`
- `results/real_video_wam_readiness.csv`
- `results/mujoco_residual_policy_rollouts.csv`
- `results/mujoco_residual_policy_gate_ablation.csv`
- `results/external_policy_benchmark_readiness.csv`
- `results/trajectory_wam_rollouts.csv`
- `results/corrective_adaptation_rollouts.csv`
- `results/corrective_trace_readiness.csv`
- `results/artifact_inventory_audit.csv`
- `results/claim_boundary_audit.csv`
- `results/command_surface_audit.csv`
- `results/config_schema_audit.csv`
- `results/derived_results_audit.csv`
- `results/source_import_audit.csv`
- `results/results_integrity_audit.csv`
- `results/paper_source_audit.csv`
- `results/portable_hygiene_audit.csv`
- `results/visual_artifact_audit.csv`
- `results/release_payload_audit.csv`
- `results/release_determinism_audit.csv`
- `results/release_runtime_audit.csv`
- `results/high_fidelity_benchmark.csv`
- `results/videos/bodyshield_synthetic_*.gif`
- `release/bodyshield_non_hardware_release.zip`
- `release/RELEASE_BUNDLE_MANIFEST.csv`
- `release/RELEASE_BUNDLE_CHECKSUMS.txt`

After unpacking `release/bodyshield_non_hardware_release.zip`, validate the extracted payload with:
```powershell
python scripts\\verify_release_payload.py
```

Boundary:
This pack stops before hardware. The robot healthcheck, safety gate, camera verifier, and emergency stop must be confirmed before any hardware batch command is meaningful.
""",
        encoding="utf-8",
    )

    (REPORTS / "RELATED_WORK_TABLE.md").write_text(
        """# Related Work Table

| Area | Verified source | BodyShield positioning |
|---|---|---|
| ICRA review expectations | IEEE RAS ICRA reviewer/editor guidance | No-hardware is not an automatic summary-rejection reason, but BodyShield still needs strong validation. |
| Learning/control fit | Guanya Shi RI page and LeCAR lab page | BodyShield is framed as reliable/adaptive learning and control under embodiment uncertainty. |
| Robot software stack | Hugging Face LeRobot and SO-101 docs | Hardware phase should use bounded LeRobot-compatible interfaces after safety gates. |
| Human-video/effect priors | VRB and ViPRA arXiv pages | Human/effect-prior policies are a stress-test family, not the main novelty. |
| Sim-to-real and active system ID | Current LeCAR publications, including SPI-Active/PLD/FALCON entries | BodyShield must compare to sysID/retune, residual-repair, and robust-control baselines. |
""",
        encoding="utf-8",
    )

    (REPORTS / "REVIEWER_ATTACK_CLOSURE.md").write_text(
        """# Reviewer Attack Closure Report

| Attack | Closure status after this execution |
|---|---|
| Just domain randomization | Equal-budget analytic comparison generated in `results/breaking_search.csv` and `results/summary_by_method_bucket.csv`. |
| Benchmark not method | Before/after repair implemented through `bodyshield.bodyshield_repair` and summarized in `reports/SIMULATION_SUMMARY.md`. |
| Cheap hardware artifact | Not closed yet; hardware noise floor remains hardware-only. |
| Perturbation makes task impossible | Oracle feasibility baseline is implemented in simulation; hardware oracle remains pending. |
| Artificial perturbations not real transfer | Held-out analytic families are generated; held-out physical modifications remain pending. |
| Metrics arbitrary | Wilson intervals, bootstrap profile summaries, and robustness radius are generated. |
| Adversarial search trivial | Random, one-axis, grid, and BodyBreak comparisons are generated; found-break-only accounting is reported separately from no-break fallback rows; dense minimality challenge rows audit representative BodyBreak found breaks. |
| Repair overfits | Held-out perturbation-family summary is generated; physical held-out tests remain pending. |
| Baselines weak | Nominal, random perturbation tuning, domain-randomization, grid, robust-control, sysID+retune, oracle, human/effect-prior, EPEC, and BodyShield methods are implemented. |
| Too conservative | Execution time, path length, retries, and nominal retention are logged and summarized. |
| No media artifact | Synthetic rollout GIFs are generated and listed in `reports/SIMULATION_ROLLOUT_VIDEOS.md`; real-video WAM readiness validates a future frame-manifest path; real camera/verifier videos remain hardware-only. |
| Manual labeling/reset bias | Not closed yet; verifier audit and reset protocol are hardware-only. |
| AI-generated citation risk | Verified citation table created in `reports/CITATION_VERIFICATION_TABLE.md`; unverified claims are excluded from the paper draft. |
| LLM raw hardware control unsafe | Hardware entry points refuse to run before safety confirmation and do not expose raw motor commands. |
""",
        encoding="utf-8",
    )

    (REPORTS / "CITATION_VERIFICATION_TABLE.md").write_text(
        """# Citation Verification Table

Verified on 2026-07-05 by Codex browser checks.

| Claim/source | Status | URL | Notes |
|---|---|---|---|
| ICRA reviewer scoring: A / 5.0 is definitely accept and top 15 percent of accepted ICRA papers | Verified | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/icra/information-for-icra-reviewers/ | Checked reviewer scoring table around lines 600-610. Use only for venue-strategy discussion. |
| ICRA editor guidance: lack of real-world experiments alone should not trigger rejection without review | Verified | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/icra/information-for-icra-editors/ | Checked summary-rejection guidance around lines 606-613. Does not imply acceptance without strong evidence. |
| Guanya Shi research scope spans ML, control theory, foundations, algorithms, robotics/autonomy | Verified | https://www.ri.cmu.edu/ri-faculty/guanya-shi/ | Checked RI profile lines 88-89. Supports advisor-fit framing. |
| LeCAR lab develops reliable, adaptive, efficient learning/control for generalist agile robots | Verified | https://lecar-lab.github.io/ | Checked lab homepage lines 3-5. Supports LeCAR-fit framing. |
| LeRobot provides hardware-agnostic Python-native robotics interfaces and SO-101 documentation | Verified | https://github.com/huggingface/lerobot and https://huggingface.co/docs/lerobot/en/so101 | Checked LeRobot README lines 319-341 and SO-101 docs lines 123-140. Use for future hardware integration only. |
| VRB / Affordances from Human Videos | Verified | https://arxiv.org/abs/2304.08488 | Checked title/authors/abstract lines 12-24. Accepted-at-CVPR note should be refreshed before final camera-ready. |
| ViPRA / Video Prediction for Robot Actions | Verified | https://arxiv.org/abs/2511.07732 | Checked arXiv v2 status and title/abstract lines 12-24. |
| Domain randomization theory baseline | Verified | https://arxiv.org/abs/2110.03239 | Checked title and abstract lines 12-24. |
| Domain randomization parameter-selection baseline | Verified | https://arxiv.org/abs/1903.11774 | Checked title and abstract lines 12-25. |
| Randomized simulation review | Verified | https://arxiv.org/abs/2111.00956 | Checked title and abstract lines 12-24. |
| Current LeCAR publications include PLD, FALCON, SPI-Active, ENPIRE, LUCID, etc. | Verified | https://lecar-lab.github.io/publications.html | Checked publication entries around lines 145-167; cite individual paper pages/arXiv before final submission. |
""",
        encoding="utf-8",
    )

    paper_tex = r"""\documentclass[10pt,conference]{IEEEtran}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{url}
\title{BodyShield: Falsifying and Repairing Hidden Embodiment Assumptions in Robot Policies}
\author{Anonymous Authors}
\begin{document}
\maketitle
\begin{abstract}
Robot policies can succeed in nominal evaluations while relying on brittle hidden assumptions about latency, calibration, joint range, gripper authority, sensing geometry, payload, and contact. We introduce BodyBreak, an active falsification procedure that estimates the lowest-cost embodiment-control perturbation that breaks a policy under a fixed evaluator budget, and BodyShield, a falsification-guided repair method that optimizes robustness over discovered failures while tracking nominal retention and execution cost. This draft contains analytic-simulation evidence, tabular scalar, synthetic visual, NumPy neural visual-latent, synthetic trajectory, synthetic corrective-adaptation, learned MuJoCo gated residual-policy audits, bounded MuJoCo/ManiSkill probes, and external-checkpoint, real-video WAM, and corrective-trace readiness harnesses; real robot results and external full-scale trained-policy high-fidelity benchmarks remain future evidence tiers.
\end{abstract}
\section{Introduction}
Nominal task success is not enough evidence that a robot policy has learned a transferable action representation. BodyShield treats embodiment-control shift as a diagnostic probe: find the smallest observed failure, attribute the failure axis, and repair the policy against the discovered assumption. The goal is not to replace system identification or domain randomization, but to test whether an apparently successful policy depends on a hidden body/control interface detail.
\section{Related Work}
This draft will cite verified sources only, including domain randomization and sim-to-real work~\cite{chen2022domainrandomization,vuong2019pickdr,muratore2022randomizedsim}, LeRobot/SO-101 infrastructure~\cite{cadene2024lerobot}, and human-video affordance policies such as VRB~\cite{bahl2023vrb} and ViPRA~\cite{routray2025vipra}.
\section{Problem Formulation}
Let $z \in \mathcal{Z}$ denote an embodiment-control perturbation and $\pi_\theta$ a policy. Each perturbation has a normalized cost $c(z)$ and an estimated success rate $S(\pi_\theta, \tau, r, z)$ for task $\tau$ and robot archetype $r$. BodyBreak estimates
\[
  z^\star = \arg\min_{z \in \mathcal{Z}} c(z)\quad \text{s.t.}\quad S(\pi_\theta,\tau,r,z) \leq \alpha,
\]
under a finite evaluator budget. BodyShield then optimizes a repaired policy against the discovered breaking set and predeclared training perturbations.
\section{BodyBreak}
BodyBreak compares random search, one-axis search, grid search, and adaptive compound search under a shared evaluator-call cap. The current CPU implementation uses a cost-ordered grid scaffold, then spends remaining calls on active-axis subset refinement, local scaling toward the nominal body, and lower-cost random challenges to refine the estimated radius. We report both found-break-only costs and no-break fallback rows, and include a post-hoc dense candidate-pool challenge for representative found breaks.
\section{BodyShield}
BodyShield repairs policy sensitivities along discovered failure axes and evaluates nominal retention, seen perturbations, held-out perturbation families, threshold sensitivity, secondary costs, and oracle feasibility. In this non-hardware execution, the policy family is analytic rather than neural; this is sufficient to test the software pipeline and claim accounting, not to claim physical deployment.
\section{Experimental Setup}
The local non-hardware run evaluates 10 policy families across 8 task cards, 6 robot archetypes, software/control perturbations, held-out physical-style perturbations, and compound perturbations. Trial logs follow \path{data_schema.json}; full flat logs, sampled nested JSONL records, confidence intervals, bootstrap profile summaries, threshold sensitivity, and failure taxonomy counts are emitted under \path{results/}. We also train a lightweight tabular outcome predictor, a rendered-frame visual predictor, a NumPy neural visual-latent dynamics predictor, a synthetic trajectory next-state predictor, and a residual corrective-action adapter on nominal/seen perturbation buckets and evaluate them on held-out buckets as WAM-style proxy audits. The pack exports three synthetic rollout GIFs for local visual inspection of nominal, BodyBreak, and repaired behavior, but these are generated frames rather than real camera videos. Separately, a local MuJoCo planar audit trains a ridge residual controller from simulator corrective labels, while external-checkpoint, real-video frame-manifest, and corrective-trace readiness harnesses validate future data interfaces without running trained-policy rollouts, real-video WAM training, or real corrective adaptation. These audits are not real-video world models or deployed robot policies.
\section{WAM-Style Proxy Audits}
The scalar audit predicts condition-level success from task, robot, policy, and perturbation features. The visual audit predicts next rendered observation frames under action-conditioned rollouts, and the neural audit trains a small nonlinear visual-latent dynamics model. The trajectory audit predicts next synthetic proprioceptive state and reports autoregressive held-out drift. The corrective audit trains a residual action adapter from generated corrective traces and evaluates whether held-out rollouts reduce drift. The MuJoCo gated residual-policy audit repeats the residual-action idea inside local 2-DOF MuJoCo dynamics with supervised corrective labels and a conservative application gate. These audits test whether BodyBreak perturbations can support learned outcome, visual, neural-latent dynamics, and adaptation machinery inside the local package, while leaving real-video WAM training, external robot-policy checkpoints, and real corrective-trace adaptation as future evidence tiers.
\section{Simulation Results}
\textbf{Main claim uses the analytic surrogate.} Table~\ref{tab:analytic-success} reports the main non-hardware success rates. BodyShield improves seen and held-out analytic perturbation success over domain randomization while retaining high nominal success; oracle rows estimate feasibility rather than deployable performance.
<<ANALYTIC_TABLE>>
Table~\ref{tab:bodybreak-search} compares active search against equal-budget alternatives. BodyBreak is not optimized to maximize the number of failures found; it estimates low-cost breaking perturbations under a fixed evaluator budget. The report pack also logs a dense candidate-pool challenge that audits representative found breaks without claiming global optimality.
<<SEARCH_TABLE>>
\section{EPEC and Human-Effect Stress Test}
Table~\ref{tab:stress-family} reports the planned human/effect-prior stress family. In this local execution these methods are analytic stress-test policies, not video-conditioned neural policies. The point is to check whether effect-preserving or human-prior action choices still expose hidden embodiment assumptions that BodyShield can repair against.
<<STRESS_TABLE>>
\section{Bounded High-Fidelity Probes}
Table~\ref{tab:mujoco-probe} reports bounded MuJoCo 1-DOF probes. The report pack additionally includes a 2-DOF MuJoCo planar end-effector suite and a learned gated residual-policy audit trained on simulator corrective labels. These checks exercise perturbation and control logic in a physics engine, but they do not model full robot perception, contact geometry, or reset.
<<MUJOCO_TABLE>>
<<MANISKILL_SENTENCE>>
\section{Ablations and Failure Analysis}
The analysis pack separates robustness gains from conservatism, path-length growth, verifier uncertainty, and task-impossibility artifacts through generated failure-taxonomy, secondary-metric, and repair-axis summaries under \path{results/}.
\section{Real Robot Results}
\textbf{Hardware placeholder only. Do not fill until SO-ARM101/SO-101 safety gates pass.}
\clearpage
\section{Limitations}
The current local run lacks hardware evidence, camera-verifier accuracy, reset reliability, noise-floor estimates, real-video or foundation-scale WAM training, real corrective-trace adaptation, and external/full-scale trained-policy MuJoCo/ManiSkill benchmarks. The scalar, visual, neural-latent, trajectory, corrective, local MuJoCo gated residual-policy, bounded simulator, external-checkpoint readiness, real-video WAM readiness, and corrective-trace readiness audits validate software execution only; none establishes physical transfer.
\bibliographystyle{IEEEtran}
\bibliography{references}
\end{document}
"""
    paper_tex = paper_tex.replace("<<ANALYTIC_TABLE>>", analytic_table_tex)
    paper_tex = paper_tex.replace("<<SEARCH_TABLE>>", search_table_tex)
    paper_tex = paper_tex.replace("<<STRESS_TABLE>>", stress_table_tex)
    paper_tex = paper_tex.replace("<<MUJOCO_TABLE>>", mujoco_table_tex)
    paper_tex = paper_tex.replace("<<MANISKILL_SENTENCE>>", maniskill_sentence)
    (PAPER / "main.tex").write_text(paper_tex, encoding="utf-8")

    (PAPER / "references.bib").write_text(
        r"""@misc{bahl2023vrb,
  title = {Affordances from Human Videos as a Versatile Representation for Robotics},
  author = {Bahl, Shikhar and Mendonca, Russell and Chen, Lili and Jain, Unnat and Pathak, Deepak},
  year = {2023},
  eprint = {2304.08488},
  archivePrefix = {arXiv},
  primaryClass = {cs.RO},
  doi = {10.48550/arXiv.2304.08488}
}

@misc{routray2025vipra,
  title = {ViPRA: Video Prediction for Robot Actions},
  author = {Routray, Sandeep and Pan, Hengkai and Jain, Unnat and Bahl, Shikhar and Pathak, Deepak},
  year = {2025},
  eprint = {2511.07732},
  archivePrefix = {arXiv},
  primaryClass = {cs.RO}
}

@misc{cadene2024lerobot,
  title = {LeRobot: State-of-the-art Machine Learning for Real-World Robotics in PyTorch},
  author = {Cadene, Remi and Alibert, Simon and Soare, Alexander and Gallouedec, Quentin and Zouitine, Adil and Palma, Steven and Kooijmans, Pepijn and Aractingi, Michel and Shukor, Mustafa and Aubakirova, Dana and Russi, Martino and Capuano, Francesco and Pascal, Caroline and Choghari, Jade and Meftah, Khalil and Ellerbach, Maxime and Moss, Jess and Wolf, Thomas},
  year = {2024},
  howpublished = {\url{https://github.com/huggingface/lerobot}}
}

@misc{chen2022domainrandomization,
  title = {Understanding Domain Randomization for Sim-to-real Transfer},
  author = {Chen, Xiaoyu and Hu, Jiachen and Jin, Chi and Li, Lihong and Wang, Liwei},
  year = {2022},
  eprint = {2110.03239},
  archivePrefix = {arXiv},
  primaryClass = {cs.LG},
  doi = {10.48550/arXiv.2110.03239}
}

@misc{vuong2019pickdr,
  title = {How to pick the domain randomization parameters for sim-to-real transfer of reinforcement learning policies?},
  author = {Vuong, Quan and Vikram, Sharad and Su, Hao and Gao, Sicun and Christensen, Henrik I.},
  year = {2019},
  eprint = {1903.11774},
  archivePrefix = {arXiv},
  primaryClass = {cs.LG},
  doi = {10.48550/arXiv.1903.11774}
}

@misc{muratore2022randomizedsim,
  title = {Robot Learning from Randomized Simulations: A Review},
  author = {Muratore, Fabio and Ramos, Fabio and Turk, Greg and Yu, Wenhao and Gienger, Michael and Peters, Jan},
  year = {2022},
  eprint = {2111.00956},
  archivePrefix = {arXiv},
  primaryClass = {cs.RO},
  doi = {10.48550/arXiv.2111.00956}
}
""",
        encoding="utf-8",
    )

    (REPORTS / "NON_HARDWARE_COMPLETE.md").write_text(
        f"""# Non-Hardware Complete

Code version: `{code_version}`

## Completed software modules
- `bodyshield.perturbations`
- `bodyshield.sim`
- `bodyshield.bodybreak_search`
- `bodyshield.bodyshield_repair`
- `bodyshield.stats`
- `bodyshield.plotting`
- `bodyshield.schema`
- `bodyshield.claim_boundary_audit`
- `bodyshield.command_surface_audit`
- `bodyshield.corrective_trace_readiness`
- `bodyshield.evidence_consistency`
- `bodyshield.environment_audit`
- `bodyshield.config_schema_audit`
- `bodyshield.source_import_audit`
- `bodyshield.artifact_inventory_audit`
- `bodyshield.derived_results_audit`
- `bodyshield.results_integrity`
- `bodyshield.paper_source_audit`
- `bodyshield.portable_hygiene_audit`
- `bodyshield.high_fidelity_learning`
- `bodyshield.external_policy_benchmark`
- `bodyshield.real_video_wam_readiness`
- `bodyshield.release_bundle`
- `bodyshield.release_determinism_audit`
- `bodyshield.release_payload_audit`
- `bodyshield.release_runtime_audit`
- `bodyshield.sim_videos`
- `bodyshield.visual_artifact_audit`
- `bodyshield.pack_verification`
- `bodyshield.robot.*` safety-gated hardware stubs

## Completed simulation experiments
- Hidden brittleness profiles across 8 tasks, 6 robot archetypes, 10 methods, and one-axis/compound perturbation families.
- Added explicit acceleration-cap, controller-update-rate, physical gripper restriction, and workspace-obstacle perturbations.
- BodyBreak adversarial search compared with random, one-axis, and grid baselines, plus dense post-hoc minimality challenge for representative found breaks.
- BodyShield repair evaluated on nominal, seen, and held-out perturbation buckets.
- Oracle feasibility baseline included for analytic-simulation perturbations.
- Threshold sensitivity generated for absolute and relative success-drop definitions.
- Corrective-trace readiness harness validates manifest ingestion, residual labels, missing dataset detection, and deterministic residual-fit smoke without claiming real corrective adaptation.
- External trained-policy readiness harness validates specs, checkpoint presence, and deterministic interface smoke without claiming external rollout evidence.
- Real-video WAM readiness harness validates frame manifests, action labels, missing dataset detection, and deterministic fit smoke without claiming real-camera or foundation-scale evidence.
- Portable release bundle generated with payload manifest, checksums, and verifier inspection; external archival upload remains separate.
- Release-payload audit safely extracts the portable ZIP and runs the bundled verifier from the extracted archive.
- Release-determinism audit rebuilds the portable ZIP from current payload files and verifies exact byte equality, fixed timestamps, fixed permissions, and deterministic entry order.
- Release-runtime audit safely extracts the portable ZIP and runs the bundled pytest suite from inside the extracted archive.
- Evidence-consistency audit validates that the main claim, trace, reproducibility, completion, simulation-summary, README, and release-bundle documents cite existing local artifacts.
- Environment dependency audit records Python/platform state, required packages, output-format packages, bounded-simulator packages, test package, and PDF/system-tool availability.
- Config-schema audit checks TOML/JSON/YAML parseability, code/config ID synchronization, readiness spec boundaries, and safety-gated hardware placeholders.
- Source/import audit checks Python compileability, bodyshield module imports in a fresh subprocess, script entry-point guards, and refusal-only hardware stubs.
- Artifact-inventory audit checks documented output references, artifact-manifest coverage, and release-manifest coverage after final bundle creation.
- Derived-results audit recomputes summary, robustness-profile, secondary-metric, failure-taxonomy, and BodyShield delta tables from primary trial rows.
- Results-integrity audit checks generated tables, JSONL samples, schema-summary counts, and Parquet row-count agreement.
- Paper-source audit checks TeX/Bib/PDF/build consistency, citations, labels, local evidence paths, table captions, and paper boundary wording.
- Portable-hygiene audit checks local absolute path leakage, temporary extraction traces, unsafe archive paths, and dynamic verifier-output exclusion from the release ZIP.
- Claim-boundary audit checks paper, report, readiness, and release wording against unsupported hardware, real-video, external-checkpoint, corrective-trace, and archival overclaims.
- Command-surface audit checks README/repro/release command synchronization, script targets, py-compile, guarded entry points, and safe CLI `--help` behavior.
- Visual-artifact audit checks generated figure PDF/PNG pairs, nonblank PNGs, safe one-page PDFs, caption coverage, and synthetic GIF frame count/dimensions/motion.

## Baselines completed
- nominal
- random perturbation tuning
- domain randomization
- worst-case grid tuning
- robust/conservative control
- sysID+retune
- oracle feasibility
- Pathak-style human/effect-prior stress-test policy
- EPEC-style effect-preserving alternatives
- BodyShield

## Tables and plots generated
- `results/trials.csv`
- `results/trials.parquet`
- `results/trials_sample.jsonl`
- `results/schema_validation_summary.json`
- `results/breaking_search.csv`
- `results/bodybreak_minimality_audit.csv`
- `results/summary_by_method_bucket.csv`
- `results/robustness_profiles.csv`
- `results/threshold_sensitivity.csv`
- `results/oracle_feasibility.csv`
- `results/method_deltas_vs_bodyshield.csv`
- `results/learned_outcome_model_eval.csv`
- `results/learned_outcome_axis_weights.csv`
- `results/learned_outcome_predictions.csv`
- `results/visual_wam_eval.csv`
- `results/visual_wam_feature_weights.csv`
- `results/visual_wam_rollouts.csv`
- `results/visual_wam_trace_sample.jsonl`
- `results/neural_wam_eval.csv`
- `results/neural_wam_rollouts.csv`
- `results/neural_wam_training_curve.csv`
- `results/neural_wam_trace_sample.jsonl`
- `results/real_video_wam_readiness.csv`
- `results/mujoco_residual_policy_eval.csv`
- `results/mujoco_residual_policy_rollouts.csv`
- `results/mujoco_residual_policy_weights.csv`
- `results/mujoco_residual_policy_gate_ablation.csv`
- `results/mujoco_residual_policy_trace_sample.jsonl`
- `results/trajectory_wam_eval.csv`
- `results/trajectory_wam_axis_weights.csv`
- `results/trajectory_wam_rollouts.csv`
- `results/trajectory_wam_trace_sample.jsonl`
- `results/corrective_adaptation_eval.csv`
- `results/corrective_adaptation_residual_weights.csv`
- `results/corrective_adaptation_rollouts.csv`
- `results/corrective_adaptation_trace_sample.jsonl`
- `results/corrective_trace_readiness.csv`
- `results/evidence_consistency_audit.csv`
- `results/artifact_inventory_audit.csv`
- `results/claim_boundary_audit.csv`
- `results/command_surface_audit.csv`
- `results/environment_dependency_audit.csv`
- `results/environment_snapshot.json`
- `results/config_schema_audit.csv`
- `results/derived_results_audit.csv`
- `results/source_import_audit.csv`
- `results/results_integrity_audit.csv`
- `results/paper_source_audit.csv`
- `results/portable_hygiene_audit.csv`
- `results/visual_artifact_audit.csv`
- `results/release_payload_audit.csv`
- `results/release_determinism_audit.csv`
- `results/release_runtime_audit.csv`
- `results/simulation_rollout_videos.csv`
- `results/videos/bodyshield_synthetic_nominal_reference.gif`
- `results/videos/bodyshield_synthetic_bodybreak_failure.gif`
- `results/videos/bodyshield_synthetic_bodyshield_repair.gif`
- `results/secondary_metrics_by_method.csv`
- `results/failure_taxonomy_counts.csv`
- `results/task_suite_cards.csv`
- `results/sim_env_availability.csv`
- `results/high_fidelity_benchmark.csv`
- `results/external_policy_benchmark_readiness.csv`
- `trial_schema.schema.json`
- `results/nominal_vs_robustness_radius.csv`
- `results/figures/bodyshield_mechanism.pdf`
- `results/figures/breaking_search_comparison.pdf`
- `results/figures/bodybreak_minimality_audit.pdf`
- `results/figures/repair_seen_heldout.pdf`
- `results/figures/nominal_vs_radius.pdf`
- `results/figures/high_fidelity_summary.pdf`
- `results/figures/visual_wam_summary.pdf`
- `results/figures/neural_wam_summary.pdf`
- `results/figures/mujoco_residual_policy_summary.pdf`
- `results/figures/mujoco_residual_gate_ablation.pdf`
- `results/figures/trajectory_wam_summary.pdf`
- `results/figures/corrective_adaptation_summary.pdf`
- `reports/FIGURE_CAPTIONS.md`
- `reports/PACK_VERIFICATION.md`
- `reports/PACK_VERIFICATION.json`
- `reports/RELEASE_BUNDLE.md`
- `reports/RELEASE_DETERMINISM_AUDIT.md`
- `reports/RELEASE_PAYLOAD_AUDIT.md`
- `reports/RELEASE_RUNTIME_AUDIT.md`
- `reports/EVIDENCE_CONSISTENCY_AUDIT.md`
- `reports/ARTIFACT_INVENTORY_AUDIT.md`
- `reports/ENVIRONMENT_DEPENDENCY_AUDIT.md`
- `reports/CONFIG_SCHEMA_AUDIT.md`
- `reports/DERIVED_RESULTS_AUDIT.md`
- `reports/SOURCE_IMPORT_AUDIT.md`
- `reports/PAPER_SOURCE_AUDIT.md`
- `reports/PORTABLE_HYGIENE_AUDIT.md`
- `reports/HIGH_FIDELITY_INTERPRETATION.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS_TABLE.md`
- `reports/NON_HARDWARE_REQUIREMENTS_TRACE.md`
- `reports/BUDGET_AND_FAIRNESS_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT_TABLE.md`
- `reports/METHOD_DELTA_TABLE.md`
- `reports/AGENDA_FIT_MEMO.md`
- `reports/LEARNED_OUTCOME_MODEL_TABLE.md`
- `reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md`
- `reports/VISUAL_WAM_TABLE.md`
- `reports/VISUAL_WAM_INTERPRETATION.md`
- `reports/SIMULATION_ROLLOUT_VIDEOS.md`
- `reports/NEURAL_WAM_TABLE.md`
- `reports/NEURAL_WAM_TRAINING_CURVE.md`
- `reports/NEURAL_WAM_INTERPRETATION.md`
- `reports/REAL_VIDEO_WAM_READINESS.md`
- `reports/REAL_VIDEO_WAM_READINESS_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_WEIGHT_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md`
- `reports/TRAJECTORY_WAM_TABLE.md`
- `reports/TRAJECTORY_WAM_INTERPRETATION.md`
- `reports/CORRECTIVE_ADAPTATION_TABLE.md`
- `reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md`
- `reports/CORRECTIVE_TRACE_READINESS.md`
- `reports/CORRECTIVE_TRACE_READINESS_TABLE.md`
- `reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md`
- `reports/MUJOCO_PLANAR_PROBE_TABLE.md`
- `paper/bodyshield_non_hardware_draft.pdf`
- `release/bodyshield_non_hardware_release.zip`
- `release/RELEASE_BUNDLE_MANIFEST.csv`
- `release/RELEASE_BUNDLE_CHECKSUMS.txt`
- `release/RELEASE_README.md`

## Citation verification status
Verified citation/source table created at `reports/CITATION_VERIFICATION_TABLE.md`.

## Remaining hardware-only tasks
- SO-ARM101/SO-101 assembly confirmation.
- Physical emergency stop confirmation.
- `python -m bodyshield.robot.healthcheck`.
- `python -m bodyshield.robot.safety_gate --check-all`.
- Camera verifier calibration and human-label agreement audit.
- Hardware noise-floor, reset reliability, safety-event, and real failure/recovery logs.

## Known risks before hardware execution
- The main experiment matrix used a CPU analytic surrogate; the learned outcome model is tabular, the visual/trajectory WAM and corrective-adaptation proxies are synthetic only, and the learned MuJoCo gated residual policy plus external-policy, real-video, and corrective-trace readiness harnesses are not external/full-scale trained robot-policy, real-video WAM, or real corrective-trace evidence.
- The rollout GIFs are generated synthetic media for local inspection only, not real camera/video-verifier evidence.
- Real held-out physical modification evidence remains uncollected; analytic physical-style perturbation families are generated.
- Automatic verifier and reset protocol are not validated.
- The paper must clearly distinguish software/simulation evidence from real robot evidence.
- High-fidelity simulator packages are probed in `reports/SIM_ENV_AVAILABILITY.md`; bounded benchmark runs are logged in `reports/HIGH_FIDELITY_BENCHMARK_TABLE.md`.
""",
        encoding="utf-8",
    )


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    VIDEOS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    code_version = tree_hash()

    policies = default_policies()
    search, breaking_cases = run_searches(policies)
    search_minimality = audit_bodybreak_minimality(search, policies)
    search.to_csv(RESULTS / "breaking_search.csv", index=False)
    policies, _ = repair_bodyshield(policies, breaking_cases)
    simulation_videos = export_synthetic_rollout_videos(policies, breaking_cases, VIDEOS)
    trials, jsonl_path = run_trials(policies, code_version)
    summary, _ = summarize_trials(trials)
    secondary_metrics, failure_counts = summarize_secondary_metrics(trials)
    radius = compute_radius(policies)
    threshold_df = compute_threshold_sensitivity(policies)
    oracle_df = compute_oracle_feasibility(search, policies)
    task_cards = pd.DataFrame(task_cards_as_rows())
    sim_envs = pd.DataFrame(check_sim_envs())
    external_policy_benchmark = run_external_policy_benchmark(CONFIGS / "external_policy_benchmark.example.json", root=ROOT)
    real_video_wam = run_real_video_wam_readiness(CONFIGS / "real_video_wam_readiness.example.json", root=ROOT)
    corrective_trace_readiness = run_corrective_trace_readiness(CONFIGS / "corrective_trace_readiness.example.json", root=ROOT)
    high_fidelity = pd.DataFrame(run_mujoco_task_suite(policies) + run_mujoco_planar_arm_suite(policies) + run_maniskill_task_suite())
    learned_outcome = fit_learned_outcome_model(policies, condition_set())
    visual_wam = fit_visual_wam_proxy(policies, condition_set())
    neural_wam = fit_neural_latent_wam(policies, condition_set())
    mujoco_residual = fit_mujoco_planar_residual_policy(policies)
    trajectory_wam = fit_trajectory_wam_proxy(policies, condition_set())
    corrective_adapter = fit_corrective_trace_adapter(policies, condition_set())

    plot_search_comparison(search, FIGURES)
    plot_bodybreak_minimality_audit(search_minimality, FIGURES)
    plot_repair_summary(summary, FIGURES)
    plot_nominal_vs_radius(radius, FIGURES)
    plot_mechanism_diagram(FIGURES)
    plot_high_fidelity_summary(high_fidelity, FIGURES)
    plot_visual_wam_summary(visual_wam.metrics, visual_wam.rollouts, FIGURES)
    plot_neural_wam_summary(neural_wam.metrics, neural_wam.training_curve, neural_wam.rollouts, FIGURES)
    plot_mujoco_residual_policy_summary(mujoco_residual.rollouts, FIGURES)
    plot_mujoco_residual_gate_ablation(mujoco_residual.gate_ablation, FIGURES)
    plot_trajectory_wam_summary(trajectory_wam.rollouts, FIGURES)
    plot_corrective_adaptation_summary(corrective_adapter.rollouts, FIGURES)

    write_reports(
        code_version,
        search,
        search_minimality,
        summary,
        radius,
        threshold_df,
        oracle_df,
        secondary_metrics,
        failure_counts,
        task_cards,
        sim_envs,
        high_fidelity,
        external_policy_benchmark,
        real_video_wam,
        corrective_trace_readiness,
        mujoco_residual.metrics,
        mujoco_residual.rollouts,
        mujoco_residual.residual_weights,
        mujoco_residual.gate_ablation,
        mujoco_residual.trace_sample,
        learned_outcome.metrics,
        learned_outcome.axis_weights,
        learned_outcome.predictions,
        trajectory_wam.metrics,
        trajectory_wam.axis_weights,
        trajectory_wam.rollouts,
        trajectory_wam.trace_sample,
        corrective_adapter.metrics,
        corrective_adapter.rollouts,
        corrective_adapter.residual_weights,
        corrective_adapter.trace_sample,
        visual_wam.metrics,
        visual_wam.rollouts,
        visual_wam.feature_weights,
        visual_wam.trace_sample,
        neural_wam.metrics,
        neural_wam.rollouts,
        neural_wam.training_curve,
        neural_wam.trace_sample,
        simulation_videos,
        jsonl_path,
    )
    paper_build = build_paper_pdf()
    (REPORTS / "PAPER_BUILD_STATUS.json").write_text(json.dumps(paper_build, indent=2, sort_keys=True), encoding="utf-8")
    write_environment_dependency_reports(ROOT)
    write_config_schema_audit_reports(ROOT)
    write_source_import_audit_reports(ROOT)
    write_derived_results_audit_reports(ROOT)
    write_results_integrity_reports(ROOT)
    write_paper_source_audit_reports(ROOT)
    write_claim_boundary_reports(ROOT)
    write_command_surface_reports(ROOT)
    write_visual_artifact_reports(ROOT)
    write_artifact_manifest(code_version, include_release=False)
    write_release_bundle(ROOT)
    write_release_payload_audit_reports(ROOT)
    write_release_determinism_audit_reports(ROOT)
    write_release_runtime_audit_reports(ROOT)
    write_portable_hygiene_audit_reports(ROOT)
    write_environment_dependency_reports(ROOT)
    write_config_schema_audit_reports(ROOT)
    write_source_import_audit_reports(ROOT)
    write_derived_results_audit_reports(ROOT)
    write_results_integrity_reports(ROOT)
    write_paper_source_audit_reports(ROOT)
    write_claim_boundary_reports(ROOT)
    write_command_surface_reports(ROOT)
    write_visual_artifact_reports(ROOT)
    write_evidence_consistency_reports(ROOT)
    write_artifact_manifest(code_version, include_release=False)
    write_release_bundle(ROOT)
    write_release_payload_audit_reports(ROOT)
    write_release_determinism_audit_reports(ROOT)
    write_release_runtime_audit_reports(ROOT)
    write_portable_hygiene_audit_reports(ROOT)
    write_artifact_manifest(code_version)
    write_artifact_inventory_audit_reports(ROOT)
    verification = write_verification_reports(ROOT)
    if verification["status"] != "pass":
        return 1
    print(COMPLETION_MESSAGE, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
