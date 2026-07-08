"""Self-trained public Gymnasium environment benchmark for the external-policy tier."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import gymnasium as gym
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ENV_ID = "CartPole-v1"
MAX_STEPS = 300
TRAIN_SEEDS = (100, 101)
EVAL_SEEDS = (200, 201, 202, 203)
CHECKPOINT_PATH = Path("results/checkpoints/self_trained_cartpole_linear_policy.json")
BOUNDARY = (
    "Self-trained public Gymnasium environment evidence only; not a user-provided external "
    "checkpoint, not MuJoCo/ManiSkill full-scale trained-policy evidence, and not hardware evidence."
)


@dataclass(frozen=True)
class PublicEnvPerturbation:
    name: str
    bucket: str
    cost: float
    force_scale: float = 1.0
    length_scale: float = 1.0
    masspole_scale: float = 1.0
    obs_noise: float = 0.0
    action_delay: int = 0
    obs_delay: int = 0


@dataclass(frozen=True)
class CEMConfig:
    policy_id: str
    training_scope: str
    seed: int
    iterations: int
    population: int
    elite: int
    init_std: float

    @property
    def evaluator_calls(self) -> int:
        return self.iterations * self.population * len(TRAIN_SEEDS)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _make_env(seed: int, perturbation: PublicEnvPerturbation) -> gym.Env:
    env = gym.make(ENV_ID)
    unwrapped = env.unwrapped
    unwrapped.force_mag *= perturbation.force_scale
    unwrapped.length *= perturbation.length_scale
    unwrapped.masspole *= perturbation.masspole_scale
    unwrapped.total_mass = unwrapped.masspole + unwrapped.masscart
    unwrapped.polemass_length = unwrapped.masspole * unwrapped.length
    env.action_space.seed(seed)
    return env


def _policy_action(weights: np.ndarray, observation: np.ndarray) -> int:
    features = np.append(observation, 1.0)
    return int(float(np.dot(weights, features)) > 0.0)


def rollout_return(
    weights: np.ndarray,
    perturbation: PublicEnvPerturbation,
    seed: int,
    *,
    max_steps: int = MAX_STEPS,
) -> float:
    rng = np.random.default_rng(seed + 12345)
    env = _make_env(seed, perturbation)
    observation, _ = env.reset(seed=seed)
    obs_buffer = [observation.copy() for _ in range(perturbation.obs_delay + 1)]
    action_buffer = [0 for _ in range(perturbation.action_delay + 1)]
    total = 0.0
    for _step in range(max_steps):
        policy_obs = obs_buffer[0].copy()
        if perturbation.obs_noise > 0:
            policy_obs += rng.normal(0.0, perturbation.obs_noise, size=policy_obs.shape)
        chosen_action = _policy_action(weights, policy_obs)
        action_buffer.append(chosen_action)
        executed_action = action_buffer.pop(0)
        observation, reward, terminated, truncated, _ = env.step(executed_action)
        obs_buffer.append(observation.copy())
        obs_buffer.pop(0)
        total += float(reward)
        if terminated or truncated:
            break
    env.close()
    return total


def evaluate_policy(
    weights: np.ndarray,
    perturbations: Iterable[PublicEnvPerturbation],
    seeds: Iterable[int],
) -> dict[str, float]:
    returns = [rollout_return(weights, perturbation, seed) for perturbation in perturbations for seed in seeds]
    values = np.asarray(returns, dtype=float)
    return {
        "mean_return": float(np.mean(values)),
        "median_return": float(np.median(values)),
        "min_return": float(np.min(values)),
        "max_return": float(np.max(values)),
        "success_rate_at_250": float(np.mean(values >= 250.0)),
        "n_episodes": int(values.size),
    }


def cem_train(
    perturbations: list[PublicEnvPerturbation],
    config: CEMConfig,
    *,
    init_weights: np.ndarray | None = None,
) -> tuple[np.ndarray, pd.DataFrame]:
    rng = np.random.default_rng(config.seed)
    mean = np.zeros(5, dtype=float) if init_weights is None else init_weights.copy()
    std = np.ones(5, dtype=float) * config.init_std
    best_weights = mean.copy()
    best_score = -1.0
    rows: list[dict[str, object]] = []
    for iteration in range(config.iterations):
        candidates = rng.normal(mean, std, size=(config.population, 5))
        candidates[0] = mean
        if init_weights is not None and config.population > 1:
            candidates[1] = init_weights
        scores = np.asarray(
            [
                evaluate_policy(candidate, perturbations, TRAIN_SEEDS)["mean_return"]
                for candidate in candidates
            ],
            dtype=float,
        )
        elite_idx = np.argsort(scores)[-config.elite :]
        elite_weights = candidates[elite_idx]
        if float(scores[elite_idx[-1]]) > best_score:
            best_score = float(scores[elite_idx[-1]])
            best_weights = candidates[elite_idx[-1]].copy()
        rows.append(
            {
                "policy_id": config.policy_id,
                "training_scope": config.training_scope,
                "iteration": iteration,
                "best_return_so_far": best_score,
                "iteration_best_return": float(np.max(scores)),
                "iteration_mean_return": float(np.mean(scores)),
                "population": config.population,
                "elite": config.elite,
                "train_seeds": ",".join(str(seed) for seed in TRAIN_SEEDS),
            }
        )
        mean = elite_weights.mean(axis=0)
        std = elite_weights.std(axis=0) + 0.08
    return best_weights, pd.DataFrame(rows)


def perturbation_sets() -> dict[str, list[PublicEnvPerturbation]]:
    return {
        "nominal": [PublicEnvPerturbation("nominal", "nominal", 0.0)],
        "repair_train": [
            PublicEnvPerturbation("nominal", "nominal", 0.0),
            PublicEnvPerturbation("force_0.55", "seen", 0.45, force_scale=0.55),
            PublicEnvPerturbation("length_1.7", "seen", 0.70, length_scale=1.70),
            PublicEnvPerturbation("action_delay_1", "seen", 0.40, action_delay=1),
        ],
        "heldout": [
            PublicEnvPerturbation("force_0.45", "heldout", 0.55, force_scale=0.45),
            PublicEnvPerturbation("masspole_2.0", "heldout", 1.00, masspole_scale=2.00),
            PublicEnvPerturbation("length_2.0", "heldout", 1.00, length_scale=2.00),
            PublicEnvPerturbation("obs_noise_0.05", "heldout", 0.50, obs_noise=0.05),
            PublicEnvPerturbation("compound_force_length_obs_delay", "heldout", 1.25, force_scale=0.55, length_scale=1.50, obs_delay=1),
        ],
    }


def _policy_rows(policy_id: str, weights: np.ndarray, perturbations: list[PublicEnvPerturbation]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    grouped = {
        "nominal": [p for p in perturbations if p.bucket == "nominal"],
        "seen": [p for p in perturbations if p.bucket == "seen"],
        "heldout": [p for p in perturbations if p.bucket == "heldout"],
        "all": list(perturbations),
    }
    for bucket, bucket_perturbations in grouped.items():
        if not bucket_perturbations:
            continue
        metrics = evaluate_policy(weights, bucket_perturbations, EVAL_SEEDS)
        rows.append(
            {
                "benchmark_id": "self_trained_public_env_cartpole",
                "env_id": ENV_ID,
                "policy_id": policy_id,
                "bucket": bucket,
                "n_episodes": metrics["n_episodes"],
                "mean_return": metrics["mean_return"],
                "median_return": metrics["median_return"],
                "min_return": metrics["min_return"],
                "max_return": metrics["max_return"],
                "success_rate_at_250": metrics["success_rate_at_250"],
                "checkpoint_path": CHECKPOINT_PATH.as_posix(),
                "evidence_tier": "self_trained_public_env",
                "evidence_boundary": BOUNDARY,
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def _public_checkpoint_artifacts_exist(root_path: Path) -> bool:
    return (
        (root_path / "reports" / "PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md").exists()
        and (root_path / "reports" / "MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md").exists()
        and (root_path / "results" / "public_pretrained_checkpoint_benchmark.csv").exists()
    )


def _update_submission_ready_audit(root_path: Path) -> None:
    results_path = root_path / "results" / "submission_ready_audit.csv"
    report_path = root_path / "reports" / "SUBMISSION_READY_AUDIT.md"
    public_checkpoint_exists = _public_checkpoint_artifacts_exist(root_path)
    paper_not_ready = (
        "PAPER NOT READY: hardware validation/noise floor/verifier/reset/physical modifications/videos are not run; "
        + ("" if public_checkpoint_exists else "external pretrained checkpoint/full-scale rollouts remain missing; ")
        + "real-video WAM and corrective-trace datasets "
        "are missing; oracle feasibility is analytic only; BodyBreak minimality is estimated rather than globally proven; "
        "release is local rather than independently archived; human paper review remains open."
    )
    columns = ["gate_name", "pass_fail", "evidence", "residual_risk", "allowed_wording"]
    if results_path.exists():
        rows = pd.read_csv(results_path).to_dict(orient="records")
    else:
        rows = []
    by_gate = {str(row.get("gate_name", "")): dict(row) for row in rows}
    by_gate["self_trained_public_env_policy"] = {
        "gate_name": "self_trained_public_env_policy",
        "pass_fail": "pass_with_scope_limit",
        "evidence": "reports/SELF_TRAINED_PUBLIC_ENV_COMPLETE.md, results/self_trained_public_env_benchmark.csv, results/checkpoints/self_trained_cartpole_linear_policy.json",
        "residual_risk": "small CartPole public-env evidence only",
        "allowed_wording": "self-trained public Gymnasium policy benchmark complete",
    }
    if public_checkpoint_exists:
        by_gate["external_trained_policy"] = {
            "gate_name": "external_trained_policy",
            "pass_fail": "pass",
            "evidence": "reports/EXTERNAL_TRAINED_POLICY_COMPLETE.md, reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md, results/public_pretrained_checkpoint_benchmark.csv",
            "residual_risk": "single public SB3 HalfCheetah checkpoint; not a broad manipulation/foundation-policy suite",
            "allowed_wording": "public pretrained MuJoCo checkpoint benchmark complete",
        }
        by_gate["full_scale_mujoco_trained_policy_rollout"] = {
            "gate_name": "full_scale_mujoco_trained_policy_rollout",
            "pass_fail": "pass_with_scope_limit",
            "evidence": "reports/MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md, results/public_pretrained_checkpoint_rollouts.csv",
            "residual_risk": "MuJoCo HalfCheetah only; no ManiSkill manipulation checkpoint",
            "allowed_wording": "one public MuJoCo full-horizon trained-policy rollout benchmark complete",
        }
    else:
        by_gate["external_trained_policy"] = {
            "gate_name": "external_trained_policy",
            "pass_fail": "fail",
            "evidence": "reports/EXTERNAL_CHECKPOINT_STILL_BLOCKED.md, reports/EXTERNAL_POLICY_INTEGRATION_PLAN.md",
            "residual_risk": "pretrained external checkpoint missing; self-trained public env does not close this gate",
            "allowed_wording": "do not claim external checkpoint validation",
        }
    ordered_names = [
        "software_package",
        "analytic_simulation",
        "budget_fairness",
        "claim_citation_repro",
        "high_fidelity_bounded",
        "self_trained_public_env_policy",
        "external_trained_policy",
        "full_scale_mujoco_trained_policy_rollout",
        "real_video_wam",
        "corrective_trace",
        "hardware_safety_noise_verifier_reset",
        "heldout_physical_modifications",
        "hardware_videos",
        "paper_human_review",
        "external_archive",
    ]
    ordered = [by_gate[name] for name in ordered_names if name in by_gate]
    extras = [row for name, row in by_gate.items() if name not in ordered_names and name]
    ordered.extend(sorted(extras, key=lambda row: str(row.get("gate_name", ""))))
    _write_csv(results_path, ordered, columns)
    table = "\n".join(
        f"| {row['gate_name']} | {row['pass_fail']} | `{row['evidence']}` | {row['residual_risk']} | {row['allowed_wording']} |"
        for row in ordered
    )
    _write_report(
        report_path,
        f"""
# Submission Ready Audit

Generated: `{_utc()}`

| gate name | pass/fail | evidence | residual risk | allowed wording |
|---|---|---|---|---|
{table}

{paper_not_ready}
""",
    )


def _plot_training_curve(path: Path, curve: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for policy_id, group in curve.groupby("policy_id"):
        ax.plot(group["iteration"], group["best_return_so_far"], marker="o", label=policy_id)
    ax.set_title("Self-Trained Public-Env CEM Training")
    ax.set_xlabel("iteration")
    ax.set_ylabel("best mean return so far")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_returns(path: Path, rows: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pivot = rows.pivot(index="bucket", columns="policy_id", values="mean_return")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    pivot.plot(kind="bar", ax=ax)
    ax.set_title("Self-Trained Public-Env Evaluation")
    ax.set_ylabel("mean return over eval seeds")
    ax.grid(axis="y", alpha=0.25)
    fig.text(0.02, 0.02, "Boundary: self-trained Gymnasium CartPole only; see public checkpoint report for external-policy evidence.", fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def _format_metric(df: pd.DataFrame, policy_id: str, bucket: str) -> float:
    row = df[(df["policy_id"] == policy_id) & (df["bucket"] == bucket)]
    if row.empty:
        return float("nan")
    return float(row.iloc[0]["mean_return"])


def write_self_trained_public_env_artifacts(root: Path | str = ".") -> dict[str, object]:
    root_path = Path(root).resolve()
    results = root_path / "results"
    reports = root_path / "reports"
    figures = root_path / "figures"
    sets = perturbation_sets()
    all_eval_perturbations = sets["repair_train"] + sets["heldout"]

    nominal_cfg = CEMConfig("nominal_self_trained_checkpoint", "nominal_only", seed=1, iterations=6, population=28, elite=5, init_std=1.2)
    repair_cfg = CEMConfig("bodyshield_repaired_checkpoint", "bodybreak_seen_perturbations", seed=2, iterations=4, population=24, elite=5, init_std=0.4)
    domain_cfg = CEMConfig("domain_randomization_checkpoint", "same_seen_perturbation_family", seed=3, iterations=4, population=24, elite=5, init_std=1.2)

    nominal_weights, nominal_curve = cem_train(sets["nominal"], nominal_cfg)
    repaired_weights, repair_curve = cem_train(sets["repair_train"], repair_cfg, init_weights=nominal_weights)
    domain_weights, domain_curve = cem_train(sets["repair_train"], domain_cfg)
    curve = pd.concat([nominal_curve, repair_curve, domain_curve], ignore_index=True)

    eval_rows = (
        _policy_rows("nominal_self_trained_checkpoint", nominal_weights, all_eval_perturbations)
        + _policy_rows("bodyshield_repaired_checkpoint", repaired_weights, all_eval_perturbations)
        + _policy_rows("domain_randomization_checkpoint", domain_weights, all_eval_perturbations)
    )
    eval_df = pd.DataFrame(eval_rows)

    bodybreak_rows: list[dict[str, object]] = []
    for perturbation in sets["repair_train"][1:] + sets["heldout"]:
        metrics = evaluate_policy(nominal_weights, [perturbation], EVAL_SEEDS)
        bodybreak_rows.append(
            {
                "benchmark_id": "self_trained_public_env_cartpole",
                "policy_id": "nominal_self_trained_checkpoint",
                "perturbation": perturbation.name,
                "bucket": perturbation.bucket,
                "cost": perturbation.cost,
                "mean_return": metrics["mean_return"],
                "success_rate_at_250": metrics["success_rate_at_250"],
                "break_status": "break_found" if metrics["mean_return"] < 250.0 else "not_broken_under_threshold",
            }
        )

    budget_rows = [
        {
            "policy_id": cfg.policy_id,
            "training_scope": cfg.training_scope,
            "iterations": cfg.iterations,
            "population": cfg.population,
            "elite": cfg.elite,
            "train_seeds": ",".join(str(seed) for seed in TRAIN_SEEDS),
            "evaluator_calls": cfg.evaluator_calls,
        }
        for cfg in (nominal_cfg, repair_cfg, domain_cfg)
    ]

    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    (root_path / CHECKPOINT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root_path / CHECKPOINT_PATH).write_text(
        json.dumps(
            {
                "policy_id": "bodyshield_repaired_checkpoint",
                "env_id": ENV_ID,
                "gymnasium_version": getattr(gym, "__version__", "unknown"),
                "weights": repaired_weights.tolist(),
                "nominal_weights": nominal_weights.tolist(),
                "domain_randomization_weights": domain_weights.tolist(),
                "max_steps": MAX_STEPS,
                "train_seeds": list(TRAIN_SEEDS),
                "eval_seeds": list(EVAL_SEEDS),
                "training_budgets": budget_rows,
                "perturbations": {name: [asdict(item) for item in values] for name, values in sets.items()},
                "evidence_boundary": BOUNDARY,
                "generated_utc": _utc(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    eval_df.to_csv(results / "self_trained_public_env_benchmark.csv", index=False)
    curve.to_csv(results / "self_trained_public_env_training_curve.csv", index=False)
    _write_csv(
        results / "self_trained_public_env_bodybreak.csv",
        bodybreak_rows,
        ["benchmark_id", "policy_id", "perturbation", "bucket", "cost", "mean_return", "success_rate_at_250", "break_status"],
    )
    _write_csv(
        results / "self_trained_public_env_budget.csv",
        budget_rows,
        ["policy_id", "training_scope", "iterations", "population", "elite", "train_seeds", "evaluator_calls"],
    )
    _plot_training_curve(figures / "self_trained_public_env_training_curve.pdf", curve)
    _plot_returns(figures / "self_trained_public_env_returns.pdf", eval_df)

    nominal_heldout = _format_metric(eval_df, "nominal_self_trained_checkpoint", "heldout")
    repaired_heldout = _format_metric(eval_df, "bodyshield_repaired_checkpoint", "heldout")
    domain_heldout = _format_metric(eval_df, "domain_randomization_checkpoint", "heldout")
    delta = repaired_heldout - nominal_heldout
    domain_delta = repaired_heldout - domain_heldout
    completion_status = "complete_self_trained_public_env_only"
    reviewer_boundary = (
        "This closes only a small self-trained public Gymnasium environment evidence slot. "
        "It does not close the user-provided or public pretrained checkpoint slot."
    )
    table = eval_df.to_markdown(index=False)
    _write_report(
        reports / "SELF_TRAINED_PUBLIC_ENV_COMPLETE.md",
        f"""
# Self-Trained Public Environment Complete

Status: `{completion_status}`

Generated: `{_utc()}`

The repository now contains a real CPU-only trained checkpoint for a public Gymnasium environment: `{ENV_ID}`. The policy is a linear CartPole controller trained by cross-entropy search, saved at `{CHECKPOINT_PATH.as_posix()}`, and evaluated under nominal, seen BodyBreak-style perturbations, and held-out perturbations.

| field | value |
|---|---|
| benchmark csv | `results/self_trained_public_env_benchmark.csv` |
| training curve | `results/self_trained_public_env_training_curve.csv` |
| bodybreak csv | `results/self_trained_public_env_bodybreak.csv` |
| budget csv | `results/self_trained_public_env_budget.csv` |
| returns figure | `figures/self_trained_public_env_returns.pdf` |
| training figure | `figures/self_trained_public_env_training_curve.pdf` |
| repaired checkpoint | `{CHECKPOINT_PATH.as_posix()}` |
| heldout nominal mean return | {nominal_heldout:.3f} |
| heldout BodyShield-repaired mean return | {repaired_heldout:.3f} |
| heldout domain-randomization mean return | {domain_heldout:.3f} |
| BodyShield minus nominal heldout delta | {delta:.3f} |
| BodyShield minus domain-randomization heldout delta | {domain_delta:.3f} |

Boundary: {reviewer_boundary}

Allowed wording: a self-trained public-environment policy benchmark was completed. Do not call this a MuJoCo/ManiSkill pretrained-policy benchmark, hardware transfer evidence, or proof that BodyShield beats domain randomization.
""",
    )
    public_checkpoint_exists = _public_checkpoint_artifacts_exist(root_path)
    if not public_checkpoint_exists:
        _write_report(
            reports / "EXTERNAL_TRAINED_POLICY_COMPLETE.md",
            f"""
# External Trained Policy Tier

Status: `partial_complete_self_trained_public_env`; `external_checkpoint_still_blocked`

Completed:

- A real self-trained public Gymnasium `{ENV_ID}` policy checkpoint exists at `{CHECKPOINT_PATH.as_posix()}`.
- The benchmark is reproducible with `python scripts\\run_self_trained_public_env_benchmark.py`.
- Results are written to `results/self_trained_public_env_benchmark.csv`.

Still blocked:

- No user-provided or public pretrained external checkpoint is present.
- No full-scale MuJoCo/ManiSkill trained-policy rollout benchmark is completed.

Reviewer-safe interpretation: the repo now has one small public-env trained-policy benchmark, but the stronger external checkpoint claim remains blocked.
""",
        )
        _write_report(
            reports / "EXTERNAL_CHECKPOINT_STILL_BLOCKED.md",
            """
# External Checkpoint Still Blocked

Status: `blocked_external_checkpoint_missing`

The self-trained public-env benchmark is complete, but it does not provide a public pretrained or user-provided external checkpoint. The following are still missing:

- Trained external checkpoint file or URL with redistribution/license status.
- Exact environment version, wrappers, observation/action normalization, and checkpoint loader.
- Seed list, horizon, success metric, and evaluation protocol.
- Compute-matched tuning budget for BodyShield, domain randomization, robust-control/sysID alternatives, and the original policy.
- Reproducible rollout script for the external checkpoint in its intended environment.

Allowed wording: external checkpoint integration remains blocked.
""",
        )
        _write_report(
            reports / "EXTERNAL_CHECKPOINT_BLOCKER.md",
            """
# External Checkpoint Blocker

Status: `blocked_external_checkpoint_missing`

The self-trained public-env benchmark is complete, but no user-provided or public pretrained external checkpoint is present. The controlling status file is `reports/EXTERNAL_CHECKPOINT_STILL_BLOCKED.md`.

Still missing:

- Trained external checkpoint file or URL with redistribution/license status.
- Exact environment version, wrappers, observation/action normalization, and checkpoint loader.
- Seed list, horizon, success metric, and evaluation protocol.
- Compute-matched tuning budget for BodyShield, domain randomization, robust-control/sysID alternatives, and the original policy.
- Reproducible rollout script for the external checkpoint in its intended environment.

Allowed wording: self-trained public-env benchmark complete; external checkpoint integration remains blocked.
""",
        )
        _write_report(
            reports / "EXTERNAL_POLICY_INTEGRATION_PLAN.md",
            """
# External Policy Integration Plan

Status: `ready_for_checkpoint_when_available`

1. Place a redistributable checkpoint under `external_checkpoints/` or record an immutable download URL.
2. Add a spec row to `configs/external_policy_benchmark.example.json` with checkpoint path, adapter module, expected observation/action dimensions, wrappers, seeds, horizon, and metric.
3. Implement the adapter as `module:function`, returning a callable policy or object with `predict()`/`act()`.
4. Run `python scripts\\run_external_policy_benchmark.py --spec <spec>` for interface validation.
5. Run a task-rollout benchmark that logs raw episode returns/successes, BodyBreak perturbation search, BodyShield repair, domain-randomization baseline, budget accounting, and held-out perturbations.
6. Update `reports/SUBMISSION_READY_AUDIT.md` only after the real checkpoint rollout passes.

Until then, `reports/EXTERNAL_CHECKPOINT_STILL_BLOCKED.md` is the controlling status.
""",
        )
        _write_report(
            reports / "EXTERNAL_POLICY_BENCHMARK.md",
            f"""
# External Policy Benchmark

Generated: `{_utc()}`

Status: `self_trained_public_env_complete`; `external_checkpoint_still_blocked`

The repository now contains one completed self-trained public-environment benchmark and still lacks a user-provided or public pretrained external checkpoint.

## Self-Trained Public-Env Rows

{table}

## Boundary

{BOUNDARY}

Allowed wording: BodyShield has a completed self-trained public Gymnasium policy benchmark. Do not claim external checkpoint validation, full-scale MuJoCo/ManiSkill trained-policy validation, hardware transfer, or dominance over domain randomization.
""",
        )
    _update_submission_ready_audit(root_path)
    return {
        "status": completion_status,
        "env_id": ENV_ID,
        "checkpoint_path": CHECKPOINT_PATH.as_posix(),
        "heldout_nominal_mean_return": nominal_heldout,
        "heldout_bodyshield_mean_return": repaired_heldout,
        "heldout_domain_randomization_mean_return": domain_heldout,
        "bodyshield_minus_nominal_heldout_delta": delta,
        "bodyshield_minus_domain_randomization_heldout_delta": domain_delta,
        "boundary": BOUNDARY,
    }
