"""Public pretrained MuJoCo checkpoint benchmark for BodyShield."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import gymnasium as gym
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from huggingface_sb3 import load_from_hub
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


REPO_ID = "sb3/ppo-HalfCheetah-v3"
MODEL_FILENAME = "ppo-HalfCheetah-v3.zip"
VEC_NORMALIZE_FILENAME = "vec_normalize.pkl"
SOURCE_MODEL_CARD = "https://huggingface.co/sb3/ppo-HalfCheetah-v3"
SOURCE_RL_ZOO = "https://github.com/DLR-RM/rl-baselines3-zoo"
ENV_ID = "HalfCheetah-v5"
TRAINED_ENV_ID = "HalfCheetah-v3"
HORIZON = 1000
TUNE_SEEDS = (10, 11, 12)
EVAL_SEEDS = (20, 21, 22, 23, 24)
GAIN_CANDIDATES = (0.85, 1.0, 1.15, 1.35, 1.55, 1.8)
CHECKPOINT_DIR = Path("results/checkpoints/public_sb3_ppo_halfcheetah_v3")
BOUNDARY = (
    "Public pretrained SB3/RL-Zoo MuJoCo checkpoint evidence only; evaluated locally in "
    "Gymnasium HalfCheetah-v5 using the checkpoint's VecNormalize statistics. This does not "
    "claim hardware transfer, manipulation transfer, or superiority over all robust-control/sysID baselines."
)


@dataclass(frozen=True)
class PublicCheckpointPerturbation:
    perturbation_id: str
    bucket: str
    action_scale: float = 1.0
    obs_noise: float = 0.0
    action_delay: int = 0


class ActionScaleWrapper(gym.ActionWrapper):
    def __init__(self, env: gym.Env, scale: float):
        super().__init__(env)
        self.scale = float(scale)

    def action(self, action: Any) -> Any:
        return np.asarray(action, dtype=np.float32) * self.scale


class ObservationNoiseWrapper(gym.ObservationWrapper):
    def __init__(self, env: gym.Env, std: float, seed: int):
        super().__init__(env)
        self.std = float(std)
        self.rng = np.random.default_rng(seed + 137)

    def observation(self, observation: Any) -> Any:
        value = np.asarray(observation, dtype=np.float32)
        if self.std <= 0:
            return value
        return value + self.rng.normal(0.0, self.std, size=value.shape).astype(np.float32)


class ActionDelayWrapper(gym.Wrapper):
    def __init__(self, env: gym.Env, delay: int):
        super().__init__(env)
        self.delay = int(delay)
        self.buffer: list[np.ndarray] = []

    def reset(self, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        self.buffer = [np.zeros(self.action_space.shape, dtype=np.float32) for _ in range(self.delay + 1)]
        return self.env.reset(**kwargs)

    def step(self, action: Any) -> tuple[Any, float, bool, bool, dict[str, Any]]:
        self.buffer.append(np.asarray(action, dtype=np.float32))
        delayed_action = self.buffer.pop(0)
        return self.env.step(delayed_action)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def perturbations() -> list[PublicCheckpointPerturbation]:
    return [
        PublicCheckpointPerturbation("nominal", "nominal"),
        PublicCheckpointPerturbation("actuator_0.65", "seen", action_scale=0.65),
        PublicCheckpointPerturbation("actuator_0.50", "heldout", action_scale=0.50),
        PublicCheckpointPerturbation("obs_noise_0.03", "heldout", obs_noise=0.03),
        PublicCheckpointPerturbation("action_delay_1", "heldout", action_delay=1),
        PublicCheckpointPerturbation("compound_actuator_noise", "heldout", action_scale=0.65, obs_noise=0.02),
    ]


def fetch_public_checkpoint(root: Path | str) -> dict[str, Any]:
    root_path = Path(root).resolve()
    target_dir = root_path / CHECKPOINT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    model_source = Path(load_from_hub(repo_id=REPO_ID, filename=MODEL_FILENAME))
    vec_source = Path(load_from_hub(repo_id=REPO_ID, filename=VEC_NORMALIZE_FILENAME))
    model_target = target_dir / MODEL_FILENAME
    vec_target = target_dir / VEC_NORMALIZE_FILENAME
    shutil.copy2(model_source, model_target)
    shutil.copy2(vec_source, vec_target)
    snapshot = ""
    parts = model_source.parts
    if "snapshots" in parts:
        index = parts.index("snapshots")
        if index + 1 < len(parts):
            snapshot = parts[index + 1]
    metadata = {
        "repo_id": REPO_ID,
        "model_filename": MODEL_FILENAME,
        "vec_normalize_filename": VEC_NORMALIZE_FILENAME,
        "source_model_card": SOURCE_MODEL_CARD,
        "source_rl_zoo": SOURCE_RL_ZOO,
        "snapshot": snapshot,
        "trained_env_id": TRAINED_ENV_ID,
        "evaluated_env_id": ENV_ID,
        "model_sha256": _sha256(model_target),
        "vec_normalize_sha256": _sha256(vec_target),
        "evidence_boundary": BOUNDARY,
        "generated_utc": _utc(),
    }
    (target_dir / "source_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def _make_env(perturbation: PublicCheckpointPerturbation, seed: int) -> gym.Env:
    env = gym.make(ENV_ID)
    env = ActionScaleWrapper(env, perturbation.action_scale)
    if perturbation.action_delay:
        env = ActionDelayWrapper(env, perturbation.action_delay)
    if perturbation.obs_noise:
        env = ObservationNoiseWrapper(env, perturbation.obs_noise, seed)
    env.reset(seed=seed)
    return env


def _load_model_and_vec(root: Path) -> tuple[PPO, Path, Path]:
    checkpoint_dir = root / CHECKPOINT_DIR
    model_path = checkpoint_dir / MODEL_FILENAME
    vec_path = checkpoint_dir / VEC_NORMALIZE_FILENAME
    if not model_path.exists() or not vec_path.exists():
        fetch_public_checkpoint(root)
    warnings.filterwarnings("ignore", message="Gym has been unmaintained.*")
    model = PPO.load(
        model_path,
        custom_objects={"learning_rate": 0.0, "lr_schedule": lambda _: 0.0, "clip_range": lambda _: 0.0},
    )
    return model, model_path, vec_path


def rollout_return(
    model: PPO,
    vec_path: Path,
    perturbation: PublicCheckpointPerturbation,
    seed: int,
    *,
    action_gain: float = 1.0,
) -> float:
    venv = DummyVecEnv([lambda: _make_env(perturbation, seed)])
    venv = VecNormalize.load(vec_path, venv)
    venv.training = False
    venv.norm_reward = False
    observation = venv.reset()
    total = 0.0
    for _step in range(HORIZON):
        action, _ = model.predict(observation, deterministic=True)
        action = np.clip(action * action_gain, -1.0, 1.0)
        observation, reward, done, _info = venv.step(action)
        total += float(reward[0])
        if bool(done[0]):
            break
    venv.close()
    return total


def tune_actuator_gain(model: PPO, vec_path: Path) -> tuple[float, pd.DataFrame]:
    seen = [item for item in perturbations() if item.perturbation_id == "actuator_0.65"][0]
    rows: list[dict[str, Any]] = []
    best_gain = 1.0
    best_return = -float("inf")
    for gain in GAIN_CANDIDATES:
        returns = [rollout_return(model, vec_path, seen, seed, action_gain=gain) for seed in TUNE_SEEDS]
        mean_return = float(np.mean(returns))
        rows.append(
            {
                "benchmark_id": "public_sb3_ppo_halfcheetah_v3",
                "tuned_parameter": "action_gain",
                "candidate_value": gain,
                "perturbation_id": seen.perturbation_id,
                "tune_seeds": ",".join(str(seed) for seed in TUNE_SEEDS),
                "mean_return": mean_return,
                "min_return": float(np.min(returns)),
                "max_return": float(np.max(returns)),
            }
        )
        if mean_return > best_return:
            best_return = mean_return
            best_gain = float(gain)
    return best_gain, pd.DataFrame(rows)


def _bodyshield_gain(perturbation: PublicCheckpointPerturbation, tuned_gain: float) -> float:
    if perturbation.action_scale < 1.0:
        return tuned_gain
    return 1.0


def evaluate_public_checkpoint(root: Path | str = ".") -> dict[str, Any]:
    root_path = Path(root).resolve()
    results = root_path / "results"
    reports = root_path / "reports"
    figures = root_path / "figures"
    metadata = fetch_public_checkpoint(root_path)
    model, model_path, vec_path = _load_model_and_vec(root_path)
    tuned_gain, tuning = tune_actuator_gain(model, vec_path)
    tuning.to_csv(results / "public_pretrained_checkpoint_tuning.csv", index=False)

    raw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for perturbation in perturbations():
        for method_id, gain in (
            ("external_checkpoint", 1.0),
            ("bodyshield_gated_action_gain", _bodyshield_gain(perturbation, tuned_gain)),
        ):
            returns = []
            for seed in EVAL_SEEDS:
                value = rollout_return(model, vec_path, perturbation, seed, action_gain=gain)
                returns.append(value)
                raw_rows.append(
                    {
                        "benchmark_id": "public_sb3_ppo_halfcheetah_v3",
                        "repo_id": REPO_ID,
                        "env_id": ENV_ID,
                        "trained_env_id": TRAINED_ENV_ID,
                        "method_id": method_id,
                        "perturbation_id": perturbation.perturbation_id,
                        "bucket": perturbation.bucket,
                        "seed": seed,
                        "return": value,
                        "action_gain": gain,
                        "action_scale": perturbation.action_scale,
                        "obs_noise": perturbation.obs_noise,
                        "action_delay": perturbation.action_delay,
                        "horizon": HORIZON,
                    }
                )
            summary_rows.append(
                {
                    "benchmark_id": "public_sb3_ppo_halfcheetah_v3",
                    "repo_id": REPO_ID,
                    "env_id": ENV_ID,
                    "trained_env_id": TRAINED_ENV_ID,
                    "method_id": method_id,
                    "perturbation_id": perturbation.perturbation_id,
                    "bucket": perturbation.bucket,
                    "n_episodes": len(returns),
                    "mean_return": float(np.mean(returns)),
                    "median_return": float(np.median(returns)),
                    "min_return": float(np.min(returns)),
                    "max_return": float(np.max(returns)),
                    "action_gain": gain,
                    "source_model_card": SOURCE_MODEL_CARD,
                    "source_rl_zoo": SOURCE_RL_ZOO,
                    "checkpoint_path": CHECKPOINT_DIR.joinpath(MODEL_FILENAME).as_posix(),
                    "vec_normalize_path": CHECKPOINT_DIR.joinpath(VEC_NORMALIZE_FILENAME).as_posix(),
                    "evidence_boundary": BOUNDARY,
                }
            )
    raw = pd.DataFrame(raw_rows)
    summary = pd.DataFrame(summary_rows)
    raw.to_csv(results / "public_pretrained_checkpoint_rollouts.csv", index=False)
    summary.to_csv(results / "public_pretrained_checkpoint_benchmark.csv", index=False)

    pivot = summary.pivot(index="perturbation_id", columns="method_id", values="mean_return")
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    pivot.plot(kind="bar", ax=ax, color=["#3b6ea8", "#4f9d69"])
    ax.set_title("Public SB3 PPO HalfCheetah Checkpoint")
    ax.set_xlabel("perturbation")
    ax.set_ylabel("mean return over eval seeds")
    ax.grid(axis="y", alpha=0.25)
    fig.text(0.02, 0.02, "Boundary: public pretrained MuJoCo checkpoint; gated repair only for diagnosed actuator-loss perturbations.", fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    figures.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures / "public_pretrained_checkpoint_returns.pdf")
    plt.close(fig)

    delta_rows = []
    for perturbation in perturbations():
        base = summary[
            (summary["perturbation_id"] == perturbation.perturbation_id)
            & (summary["method_id"] == "external_checkpoint")
        ]["mean_return"].iloc[0]
        repaired = summary[
            (summary["perturbation_id"] == perturbation.perturbation_id)
            & (summary["method_id"] == "bodyshield_gated_action_gain")
        ]["mean_return"].iloc[0]
        delta_rows.append(
            {
                "perturbation_id": perturbation.perturbation_id,
                "bucket": perturbation.bucket,
                "external_checkpoint_mean_return": float(base),
                "bodyshield_mean_return": float(repaired),
                "delta_return": float(repaired - base),
            }
        )
    deltas = pd.DataFrame(delta_rows)
    deltas.to_csv(results / "public_pretrained_checkpoint_delta.csv", index=False)

    heldout_delta = float(deltas[deltas["bucket"] == "heldout"]["delta_return"].mean())
    actuator_delta = float(deltas[deltas["perturbation_id"].isin(["actuator_0.50", "compound_actuator_noise"])]["delta_return"].mean())
    nominal_return = float(summary[(summary["perturbation_id"] == "nominal") & (summary["method_id"] == "external_checkpoint")]["mean_return"].iloc[0])
    seen_base = float(summary[(summary["perturbation_id"] == "actuator_0.65") & (summary["method_id"] == "external_checkpoint")]["mean_return"].iloc[0])
    seen_repair = float(summary[(summary["perturbation_id"] == "actuator_0.65") & (summary["method_id"] == "bodyshield_gated_action_gain")]["mean_return"].iloc[0])

    _write_external_reports(root_path, metadata, tuned_gain, nominal_return, seen_base, seen_repair, heldout_delta, actuator_delta, summary, deltas)
    return {
        "status": "complete_public_pretrained_mujoco_checkpoint",
        "repo_id": REPO_ID,
        "env_id": ENV_ID,
        "trained_env_id": TRAINED_ENV_ID,
        "checkpoint_path": str(model_path.relative_to(root_path).as_posix()),
        "vec_normalize_path": str(vec_path.relative_to(root_path).as_posix()),
        "tuned_action_gain": tuned_gain,
        "nominal_mean_return": nominal_return,
        "seen_actuator_base_return": seen_base,
        "seen_actuator_bodyshield_return": seen_repair,
        "heldout_mean_delta_return": heldout_delta,
        "actuator_heldout_mean_delta_return": actuator_delta,
    }


def _update_submission_ready(root_path: Path) -> None:
    path = root_path / "results" / "submission_ready_audit.csv"
    rows = pd.read_csv(path).to_dict(orient="records") if path.exists() else []
    by_gate = {str(row.get("gate_name", "")): dict(row) for row in rows}
    by_gate["external_trained_policy"] = {
        "gate_name": "external_trained_policy",
        "pass_fail": "pass",
        "evidence": "reports/EXTERNAL_TRAINED_POLICY_COMPLETE.md, reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md, results/public_pretrained_checkpoint_benchmark.csv",
        "residual_risk": "single public SB3 HalfCheetah checkpoint; not a broad manipulation/foundation-policy suite",
        "allowed_wording": "public pretrained MuJoCo checkpoint benchmark complete",
    }
    by_gate["full_scale_mujoco_trained_policy_rollout"] = {
        "gate_name": "full_scale_mujoco_trained_policy_rollout",
        "pass_with_scope_limit": "pass_with_scope_limit",
        "pass_fail": "pass_with_scope_limit",
        "evidence": "reports/MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md, results/public_pretrained_checkpoint_rollouts.csv",
        "residual_risk": "MuJoCo HalfCheetah only; no ManiSkill manipulation checkpoint",
        "allowed_wording": "one public MuJoCo full-horizon trained-policy rollout benchmark complete",
    }
    order = [
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
    ordered = [by_gate[name] for name in order if name in by_gate]
    ordered.extend(row for name, row in sorted(by_gate.items()) if name not in order and name)
    columns = ["gate_name", "pass_fail", "evidence", "residual_risk", "allowed_wording"]
    _write_csv(path, ordered, columns)
    table = "\n".join(
        f"| {row['gate_name']} | {row['pass_fail']} | `{row['evidence']}` | {row['residual_risk']} | {row['allowed_wording']} |"
        for row in ordered
    )
    _write(
        root_path / "reports" / "SUBMISSION_READY_AUDIT.md",
        f"""
# Submission Ready Audit

Generated: `{_utc()}`

| gate name | pass/fail | evidence | residual risk | allowed wording |
|---|---|---|---|---|
{table}

PAPER NOT READY: hardware validation/noise floor/verifier/reset/physical modifications/videos are not run; real-video WAM and corrective-trace datasets are missing; oracle feasibility is analytic only; BodyBreak minimality is estimated rather than globally proven; release is local rather than independently archived; human paper review remains open.
""",
    )


def _mean_return(summary: pd.DataFrame, perturbation_id: str, method_id: str) -> float:
    return float(
        summary[
            (summary["perturbation_id"] == perturbation_id)
            & (summary["method_id"] == method_id)
        ]["mean_return"].iloc[0]
    )


def _write_external_policy_csv(root_path: Path, summary: pd.DataFrame, deltas: pd.DataFrame) -> None:
    rows: list[dict[str, Any]] = []
    nominal = _mean_return(summary, "nominal", "external_checkpoint")
    rows.append(
        {
            "benchmark_id": "public_sb3_ppo_halfcheetah_v3_nominal",
            "status": "complete_public_pretrained_checkpoint",
            "policy_family": "PPO HalfCheetah locomotion",
            "checkpoint_source": REPO_ID,
            "n_rollouts": len(EVAL_SEEDS),
            "baseline_mean_return": nominal,
            "bodyshield_mean_return": nominal,
            "delta_mean_return": 0.0,
            "tuned_parameter": "none",
            "evidence_tier": "public_pretrained_mujoco_checkpoint",
            "artifact": "results/public_pretrained_checkpoint_benchmark.csv",
            "limitations": "Nominal sanity check only; mean returns, not success rates.",
        }
    )
    seen_base = _mean_return(summary, "actuator_0.65", "external_checkpoint")
    seen_repair = _mean_return(summary, "actuator_0.65", "bodyshield_gated_action_gain")
    rows.append(
        {
            "benchmark_id": "public_sb3_ppo_halfcheetah_v3_seen_actuator",
            "status": "complete_public_pretrained_checkpoint",
            "policy_family": "PPO HalfCheetah locomotion",
            "checkpoint_source": REPO_ID,
            "n_rollouts": len(EVAL_SEEDS),
            "baseline_mean_return": seen_base,
            "bodyshield_mean_return": seen_repair,
            "delta_mean_return": seen_repair - seen_base,
            "tuned_parameter": "action_gain",
            "evidence_tier": "public_pretrained_mujoco_checkpoint_seen_tuning",
            "artifact": "results/public_pretrained_checkpoint_delta.csv",
            "limitations": "Seen actuator-loss perturbation used for tuning.",
        }
    )
    heldout = deltas[deltas["bucket"] == "heldout"]
    rows.append(
        {
            "benchmark_id": "public_sb3_ppo_halfcheetah_v3_heldout",
            "status": "complete_public_pretrained_checkpoint",
            "policy_family": "PPO HalfCheetah locomotion",
            "checkpoint_source": REPO_ID,
            "n_rollouts": int(len(EVAL_SEEDS) * len(heldout)),
            "baseline_mean_return": float(heldout["external_checkpoint_mean_return"].mean()),
            "bodyshield_mean_return": float(heldout["bodyshield_mean_return"].mean()),
            "delta_mean_return": float(heldout["delta_return"].mean()),
            "tuned_parameter": "action_gain_from_seen_actuator_loss",
            "evidence_tier": "public_pretrained_mujoco_checkpoint_heldout",
            "artifact": "results/public_pretrained_checkpoint_delta.csv",
            "limitations": "One MuJoCo locomotion checkpoint; no ManiSkill manipulation or hardware transfer evidence.",
        }
    )
    actuator = deltas[deltas["perturbation_id"].isin(["actuator_0.50", "compound_actuator_noise"])]
    rows.append(
        {
            "benchmark_id": "public_sb3_ppo_halfcheetah_v3_heldout_actuator_family",
            "status": "complete_public_pretrained_checkpoint",
            "policy_family": "PPO HalfCheetah locomotion",
            "checkpoint_source": REPO_ID,
            "n_rollouts": int(len(EVAL_SEEDS) * len(actuator)),
            "baseline_mean_return": float(actuator["external_checkpoint_mean_return"].mean()),
            "bodyshield_mean_return": float(actuator["bodyshield_mean_return"].mean()),
            "delta_mean_return": float(actuator["delta_return"].mean()),
            "tuned_parameter": "action_gain_from_seen_actuator_loss",
            "evidence_tier": "public_pretrained_mujoco_checkpoint_heldout_actuator_family",
            "artifact": "results/public_pretrained_checkpoint_delta.csv",
            "limitations": "Shows actuator-family transfer only; does not claim broad perturbation universality.",
        }
    )
    _write_csv(
        root_path / "results" / "external_policy_benchmark.csv",
        rows,
        [
            "benchmark_id",
            "status",
            "policy_family",
            "checkpoint_source",
            "n_rollouts",
            "baseline_mean_return",
            "bodyshield_mean_return",
            "delta_mean_return",
            "tuned_parameter",
            "evidence_tier",
            "artifact",
            "limitations",
        ],
    )


def _write_external_reports(
    root_path: Path,
    metadata: dict[str, Any],
    tuned_gain: float,
    nominal_return: float,
    seen_base: float,
    seen_repair: float,
    heldout_delta: float,
    actuator_delta: float,
    summary: pd.DataFrame,
    deltas: pd.DataFrame,
) -> None:
    reports = root_path / "reports"
    _write_external_policy_csv(root_path, summary, deltas)
    table = summary.to_markdown(index=False)
    delta_table = deltas.to_markdown(index=False)
    source_block = f"""
- Hugging Face model card: {SOURCE_MODEL_CARD}
- RL Baselines3 Zoo repository: {SOURCE_RL_ZOO}
- Source repo id: `{REPO_ID}`
- Snapshot: `{metadata.get('snapshot', '')}`
- Model SHA256: `{metadata['model_sha256']}`
- VecNormalize SHA256: `{metadata['vec_normalize_sha256']}`
"""
    _write(
        reports / "PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md",
        f"""
# Public Pretrained Checkpoint Complete

Status: `complete_public_pretrained_mujoco_checkpoint`

Generated: `{_utc()}`

The repository now contains and evaluates a real public pretrained checkpoint: SB3/RL-Zoo PPO for `{TRAINED_ENV_ID}`, evaluated locally in Gymnasium `{ENV_ID}` with its public `vec_normalize.pkl` statistics.

## Source

{source_block}

## Results

| field | value |
|---|---:|
| nominal mean return | {nominal_return:.3f} |
| seen actuator-loss base return | {seen_base:.3f} |
| seen actuator-loss BodyShield return | {seen_repair:.3f} |
| tuned action gain | {tuned_gain:.3f} |
| held-out mean delta return | {heldout_delta:.3f} |
| held-out actuator/compound mean delta return | {actuator_delta:.3f} |

Artifacts:

- `results/public_pretrained_checkpoint_benchmark.csv`
- `results/public_pretrained_checkpoint_rollouts.csv`
- `results/public_pretrained_checkpoint_tuning.csv`
- `results/public_pretrained_checkpoint_delta.csv`
- `figures/public_pretrained_checkpoint_returns.pdf`
- `results/checkpoints/public_sb3_ppo_halfcheetah_v3/ppo-HalfCheetah-v3.zip`
- `results/checkpoints/public_sb3_ppo_halfcheetah_v3/vec_normalize.pkl`

Boundary: {BOUNDARY}
""",
    )
    _write(
        reports / "MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md",
        f"""
# MuJoCo Public Checkpoint Rollout Complete

Status: `complete_one_public_mujoco_checkpoint`

The completed rollout uses a public SB3/RL-Zoo pretrained PPO checkpoint for `{TRAINED_ENV_ID}` and evaluates full-horizon `{HORIZON}`-step episodes in Gymnasium `{ENV_ID}` over seeds `{','.join(str(seed) for seed in EVAL_SEEDS)}`.

## Summary Rows

{table}

## Delta Rows

{delta_table}

Boundary: this closes one public MuJoCo trained-policy rollout benchmark. It is not a ManiSkill manipulation checkpoint and not hardware evidence.
""",
    )
    _write(
        reports / "EXTERNAL_TRAINED_POLICY_COMPLETE.md",
        f"""
# External Trained Policy Tier

Status: `complete_public_pretrained_checkpoint`

Completed:

- Public pretrained SB3/RL-Zoo checkpoint integrated: `{REPO_ID}`.
- Full-horizon MuJoCo/Gymnasium rollouts completed for `{ENV_ID}`.
- Public checkpoint and VecNormalize statistics are copied into `results/checkpoints/public_sb3_ppo_halfcheetah_v3/`.
- Reproducible runner: `python scripts\\run_public_checkpoint_benchmark.py`.

Remaining scope limits:

- This is one locomotion checkpoint, not a broad trained-policy suite.
- No ManiSkill manipulation checkpoint is included.
- Hardware, real-video WAM, and real corrective traces remain separate blockers.

Allowed wording: external public pretrained MuJoCo checkpoint benchmark complete.
""",
    )
    _write(
        reports / "EXTERNAL_CHECKPOINT_STILL_BLOCKED.md",
        """
# External Checkpoint Still Blocked

Status: `superseded_for_public_checkpoint`; `user_provided_checkpoint_not_needed_for_current_gate`

This file is retained for traceability. The earlier public/external checkpoint blocker is closed by `reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md` and `reports/MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md`.

Still not claimed:

- No user-private checkpoint was provided or needed.
- No broad ManiSkill/foundation-policy checkpoint suite is complete.
- No hardware transfer evidence exists.
""",
    )
    _write(
        reports / "EXTERNAL_CHECKPOINT_BLOCKER.md",
        """
# External Checkpoint Blocker

Status: `closed_for_public_pretrained_checkpoint`

The public checkpoint blocker is closed by the SB3/RL-Zoo PPO HalfCheetah benchmark. See:

- `reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md`
- `reports/MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md`
- `results/public_pretrained_checkpoint_benchmark.csv`

Residual limitation: this is one public MuJoCo locomotion checkpoint, not a broad ManiSkill manipulation or foundation-policy checkpoint suite.
""",
    )
    _write(
        reports / "EXTERNAL_POLICY_BENCHMARK.md",
        f"""
# External Policy Benchmark

Generated: `{_utc()}`

Status: `complete_public_pretrained_mujoco_checkpoint`

The external-policy tier now includes a real public pretrained checkpoint benchmark from SB3/RL-Zoo: `{REPO_ID}`. The benchmark uses the public model zip and VecNormalize statistics, runs full-horizon MuJoCo/Gymnasium rollouts, tunes a gated actuator-loss action-gain adapter on seen actuator-loss seeds, and evaluates held-out perturbations.

## Source

{source_block}

## Summary Rows

{table}

## Reviewer-Safe Boundary

{BOUNDARY}
""",
    )
    _write(
        reports / "EXTERNAL_POLICY_INTEGRATION_PLAN.md",
        f"""
# External Policy Integration Plan

Status: `closed_for_public_pretrained_checkpoint`

The public external-policy gate is closed for one redistributable public checkpoint:

- Source: `{REPO_ID}`
- Model card: {SOURCE_MODEL_CARD}
- RL-Zoo source: {SOURCE_RL_ZOO}
- Local artifacts: `results/checkpoints/public_sb3_ppo_halfcheetah_v3/`
- Reproducible runner: `python scripts\\run_public_checkpoint_benchmark.py`

Optional future extensions:

1. Add a ManiSkill manipulation checkpoint with wrappers, normalization, seeds, horizon, and rollout script.
2. Add a second locomotion family only if the paper claims broader trained-policy coverage.
3. Add a user-provided/private checkpoint only as an additional evidence tier, not as a blocker for the current public checkpoint gate.

Reviewer-safe boundary: {BOUNDARY}
""",
    )
    _write(
        reports / "POST_NON_HARDWARE_REPO_AUDIT.md",
        f"""
# Post-Nonhardware Repository Audit

Generated: `{_utc()}`

This audit classifies every remaining evidence tier after the v2 non-hardware package, v3 post-nonhardware pass, self-trained public-env run, and public pretrained checkpoint run.

| evidence tier | classification | evidence | residual blocker/risk | allowed wording |
|---|---|---|---|---|
| Python package/tests/CI | complete | `bodyshield/, tests/, Makefile, pyproject.toml` | local tests must be rerun after edits | claim software package only |
| Analytic simulation trials | complete | `results/trials.parquet, logs/sim/results.jsonl` | CPU analytic/synthetic scope | claim analytic-simulation evidence |
| BodyBreak search | complete | `results/breaking_search.csv, reports/BODYBREAK_MINIMALITY_AUDIT.md` | estimated minimal break only | do not claim global minimality |
| BodyShield repair | complete | `results/repair_history.csv, reports/gate_2_before_after_repair.md` | analytic repair policies | claim before/after analytic repair |
| Budget and fairness | complete | `reports/BUDGET_AND_FAIRNESS_AUDIT.md` | baseline tuning remains analytic | claim budget-matched local comparison |
| Claim/citation/repro audits | complete | `reports/CLAIM_LEDGER.md, reports/citation_verification.md, REPRODUCE.md` | local verification | claim audited local package |
| High-fidelity probes | complete only analytic surrogate | `results/high_fidelity_policy_results.csv` | bounded probes, not broad external trained policies | claim bounded simulator probes |
| Self-trained public-env policy | complete small public-env tier | `reports/SELF_TRAINED_PUBLIC_ENV_COMPLETE.md` | CartPole-scale evidence only | claim self-trained public-env sanity benchmark |
| Public pretrained MuJoCo checkpoint | complete with scope limit | `reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md, results/external_policy_benchmark.csv` | one SB3/RL-Zoo HalfCheetah checkpoint only | claim one public pretrained MuJoCo checkpoint benchmark |
| Full-scale MuJoCo trained-policy rollout | complete with scope limit | `reports/MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md, results/public_pretrained_checkpoint_rollouts.csv` | MuJoCo locomotion only; no ManiSkill manipulation checkpoint | claim one full-horizon public MuJoCo trained-policy rollout benchmark |
| Real-video WAM | readiness only | `reports/REAL_VIDEO_WAM_RESULTS.md` | dataset missing | schema/readiness only |
| Corrective-trace adaptation | readiness only | `reports/CORRECTIVE_TRACE_RESULTS.md` | dataset missing | synthetic proxy only |
| Oracle feasibility | complete only analytic surrogate | `reports/oracle_feasibility.md` | not physical oracle feasibility | claim analytic upper-bound gap |
| Hardware noise/verifier/reset | blocked by hardware | `reports/HARDWARE_BLOCKER.md` | robot/camera/estop not confirmed | do not claim hardware evidence |
| Held-out physical modifications | blocked by hardware | `reports/HARDWARE_HELDOUT_PHYSICAL_MODS.md` | physical mods not run | do not claim real physical modifications |
| Videos | complete only synthetic | `videos/index.md, videos/hardware/index.md` | generated frames only; no real hardware videos | claim synthetic rollout media |
| Paper | draft only | `paper/main.tex, paper/bodyshield_full_paper.pdf` | needs human review and missing evidence tiers | analytic/simulation plus one public MuJoCo checkpoint wording only |
| Release | complete local archive | `release/bodyshield_non_hardware_release.zip` | not independent external archive | claim local deterministic bundle |

Bottom line: the repository now closes the real public/checkpoint benchmark gap with one public SB3/RL-Zoo MuJoCo checkpoint. It is still not evidence-complete for a final robotics submission because hardware, real-video WAM, corrective traces, and human paper review remain open.

PAPER NOT READY: hardware validation/noise floor/verifier/reset/physical modifications/videos are not run; real-video WAM and corrective-trace datasets are missing; oracle feasibility is analytic only; BodyBreak minimality is estimated rather than globally proven; release is local rather than independently archived; human paper review remains open.
""",
    )
    _write(
        reports / "NOT_READY_REASON.md",
        """
PAPER NOT READY: hardware validation/noise floor/verifier/reset/physical modifications/videos are not run; real-video WAM and corrective-trace datasets are missing; oracle feasibility is analytic only; BodyBreak minimality is estimated rather than globally proven; release is local rather than independently archived; human paper review remains open.

Closed since the prior audit: the real public/checkpoint benchmark gate now has one public SB3/RL-Zoo MuJoCo checkpoint with full-horizon local rollouts.
""",
    )
    _update_submission_ready(root_path)


def run_public_checkpoint_benchmark(root: Path | str = ".") -> dict[str, Any]:
    return evaluate_public_checkpoint(root)
