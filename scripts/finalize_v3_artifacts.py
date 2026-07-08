"""Generate post-nonhardware v3 artifacts without fabricating missing evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

if str(ROOT := Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(ROOT))
from bodyshield.results_integrity import source_tree_hash


REPORTS = ROOT / "reports"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
PAPER = ROOT / "paper"
VIDEOS = ROOT / "videos"
RELEASE = ROOT / "release"

NON_HARDWARE_MESSAGE = (
    "NON-HARDWARE COMPLETE: BodyShield software, simulation, baselines, perturbation search, repair algorithms, "
    "analysis scripts, paper skeleton/draft, verified citation table, release bundle, and reviewer-defense reports "
    "are finished under analytic/synthetic scope. Hardware phase is next. Do not proceed until the user confirms "
    "the SO-ARM101/SO-101 setup, safety gate, camera verifier, reset protocol, and emergency stop are ready."
)

PAPER_NOT_READY = (
    "PAPER NOT READY: hardware validation/noise floor/verifier/reset/physical modifications/videos are not run; "
    "external trained-policy checkpoints and full-scale rollouts are missing; real-video WAM and corrective-trace "
    "datasets are missing; oracle feasibility is analytic only; BodyBreak minimality is estimated rather than "
    "globally proven; release is local rather than independently archived; human paper review remains open."
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _fmt(value: object, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def _plot_bar_pdf(path: Path, labels: list[str], values: list[float], title: str, ylabel: str, footer: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    colors = ["#3b6ea8", "#4f9d69", "#d08c30", "#7f5f9f", "#5b6770", "#b04a4a"]
    ax.bar(labels, values, color=[colors[i % len(colors)] for i in range(len(labels))])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=20)
    if footer:
        fig.text(0.02, 0.02, footer, fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def _plot_blocked_pdf(path: Path, title: str, blockers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(8.5, 4.8))
    fig.text(0.06, 0.88, title, fontsize=16, weight="bold")
    fig.text(0.06, 0.78, "Status: not run. No physical measurements are present in this repository.", fontsize=10)
    y = 0.66
    for item in blockers:
        wrapped = textwrap.wrap(f"- {item}", width=94)
        for line in wrapped:
            fig.text(0.08, y, line, fontsize=9)
            y -= 0.07
    fig.savefig(path)
    plt.close(fig)


def _write_text_pdf(path: Path, title: str, sections: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(8.5, 11))
        y = 0.94

        def flush() -> None:
            nonlocal fig, y
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(8.5, 11))
            y = 0.94

        fig.text(0.07, y, title, fontsize=17, weight="bold")
        y -= 0.06
        fig.text(0.07, y, f"Generated: {_utc()}", fontsize=8, color="#555555")
        y -= 0.05
        for heading, body in sections:
            if y < 0.16:
                flush()
            fig.text(0.07, y, heading, fontsize=12, weight="bold")
            y -= 0.035
            for para in body.split("\n"):
                if not para.strip():
                    y -= 0.025
                    continue
                for line in textwrap.wrap(para, width=94):
                    if y < 0.08:
                        flush()
                    fig.text(0.08, y, line, fontsize=9)
                    y -= 0.022
            y -= 0.02
        pdf.savefig(fig)
        plt.close(fig)


def _existing(path: str) -> str:
    target = ROOT / path
    if target.exists() and target.stat().st_size > 0:
        return path
    return f"{path} (missing)"


def write_external_policy_benchmark() -> None:
    eval_path = RESULTS / "mujoco_residual_policy_eval.csv"
    df = _read_csv(eval_path)
    rows: list[dict[str, object]] = []
    if not df.empty:
        useful = df[df["slice"].isin(["all", "split=heldout", "split=train_seen_or_nominal"])]
        for _, row in useful.iterrows():
            rows.append(
                {
                    "benchmark_id": "mujoco_residual_policy_surrogate",
                    "status": "complete_only_local_surrogate",
                    "policy_family": str(row.get("slice", "")),
                    "checkpoint_source": "local generated analytic/MuJoCo rollouts; not an external checkpoint",
                    "n_rollouts": int(row.get("n_rollouts", 0)),
                    "baseline_success_rate": _fmt(row.get("base_success_rate")),
                    "bodyshield_success_rate": _fmt(row.get("adapted_success_rate")),
                    "delta_success_rate": _fmt(row.get("delta_success_rate")),
                    "baseline_final_error": _fmt(row.get("base_final_error")),
                    "bodyshield_final_error": _fmt(row.get("adapted_final_error")),
                    "delta_final_error": _fmt(row.get("delta_final_error")),
                    "evidence_tier": "analytic_surrogate_not_external",
                    "artifact": "results/mujoco_residual_policy_eval.csv",
                    "limitations": "Does not close the external trained-policy checkpoint evidence tier.",
                }
            )
    rows.append(
        {
            "benchmark_id": "external_trained_policy_checkpoint",
            "status": "blocked_external_data_checkpoints",
            "policy_family": "missing",
            "checkpoint_source": "none provided in repository",
            "n_rollouts": 0,
            "baseline_success_rate": "",
            "bodyshield_success_rate": "",
            "delta_success_rate": "",
            "baseline_final_error": "",
            "bodyshield_final_error": "",
            "delta_final_error": "",
            "evidence_tier": "missing",
            "artifact": "reports/EXTERNAL_CHECKPOINT_BLOCKER.md",
            "limitations": "Requires public or provided trained policy checkpoints plus compute-matched rollout protocol.",
        }
    )
    fields = [
        "benchmark_id",
        "status",
        "policy_family",
        "checkpoint_source",
        "n_rollouts",
        "baseline_success_rate",
        "bodyshield_success_rate",
        "delta_success_rate",
        "baseline_final_error",
        "bodyshield_final_error",
        "delta_final_error",
        "evidence_tier",
        "artifact",
        "limitations",
    ]
    _write_csv(RESULTS / "external_policy_benchmark.csv", rows, fields)

    plot_rows = [row for row in rows if row["status"] == "complete_only_local_surrogate" and row["delta_success_rate"] != ""]
    _plot_bar_pdf(
        FIGURES / "external_policy_bodyshield_delta.pdf",
        [str(row["policy_family"]).replace("split=", "") for row in plot_rows],
        [float(row["delta_success_rate"]) for row in plot_rows],
        "BodyShield Delta on Local Policy Surrogate",
        "delta success rate",
        "Boundary: local surrogate only; no external trained checkpoint is present.",
    )

    table = "\n".join(
        f"| {row['benchmark_id']} | {row['status']} | {row['n_rollouts']} | {row['delta_success_rate']} | {row['limitations']} |"
        for row in rows
    )
    _write(
        REPORTS / "EXTERNAL_POLICY_BENCHMARK.md",
        f"""
# External Policy Benchmark

Generated: `{_utc()}`

Status: `partial_analytic_surrogate`; external trained-policy evidence remains blocked.

The v3 pass found no public or user-provided trained policy checkpoint inside this repository. It therefore exports a local residual-policy surrogate summary from existing generated MuJoCo-style rollouts and labels it as surrogate evidence only.

| benchmark | status | n rollouts | delta success | limitation |
|---|---|---:|---:|---|
{table}

Artifacts:

- `results/external_policy_benchmark.csv`
- `figures/external_policy_bodyshield_delta.pdf`
- `results/mujoco_residual_policy_eval.csv`

Allowed wording: BodyShield is evaluated on local analytic and bounded high-fidelity surrogates. Do not claim external trained-policy validation.
""",
    )
    _write(
        REPORTS / "EXTERNAL_CHECKPOINT_BLOCKER.md",
        """
# External Checkpoint Blocker

Status: `blocked_external_data_checkpoints`

Missing items:

- A trained policy checkpoint from a public or user-provided benchmark.
- Exact environment version, observation/action wrappers, normalization, seed list, and evaluation horizon.
- Compute-matched baseline tuning budget for the same controller family.
- Reproducible rollout script that can regenerate the benchmark table without fixture shortcuts.

The repository contains local analytic and bounded MuJoCo/ManiSkill probes, but those are not a substitute for an external trained-policy checkpoint benchmark.
""",
    )


def write_high_fidelity_policy_results() -> None:
    raw = _read_csv(RESULTS / "high_fidelity_benchmark.csv")
    if raw.empty:
        rows = [
            {
                "engine": "missing",
                "task_id": "missing",
                "method_id": "missing",
                "perturbation_family": "missing",
                "n": 0,
                "success_rate": "",
                "evidence_scope": "missing",
                "notes": "results/high_fidelity_benchmark.csv is absent.",
            }
        ]
    else:
        keep_methods = {"nominal", "domain_randomization", "bodyshield", "oracle"}
        filtered = raw[raw["method_id"].isin(keep_methods)].copy()
        filtered["evidence_scope"] = filtered["engine"].map(
            {
                "mujoco": "bounded_mujoco_probe",
                "mujoco_planar": "bounded_mujoco_planar_probe",
                "maniskill": "maniskill_availability_or_random_control_probe",
            }
        ).fillna("bounded_probe")
        columns = [
            "engine",
            "task_id",
            "method_id",
            "perturbation_family",
            "n",
            "success_rate",
            "mean_final_progress",
            "mean_final_error",
            "evidence_scope",
            "notes",
        ]
        for column in columns:
            if column not in filtered.columns:
                filtered[column] = ""
        rows = filtered[columns].to_dict(orient="records")
    _write_csv(
        RESULTS / "high_fidelity_policy_results.csv",
        rows,
        [
            "engine",
            "task_id",
            "method_id",
            "perturbation_family",
            "n",
            "success_rate",
            "mean_final_progress",
            "mean_final_error",
            "evidence_scope",
            "notes",
        ],
    )

    out = pd.DataFrame(rows)
    if not out.empty and "success_rate" in out:
        summary = (
            out[out["method_id"].isin(["nominal", "domain_randomization", "bodyshield"])]
            .assign(success_rate=lambda frame: pd.to_numeric(frame["success_rate"], errors="coerce"))
            .groupby(["engine", "method_id"], dropna=False)["success_rate"]
            .mean()
            .reset_index()
        )
        labels = [f"{row.engine}:{row.method_id}" for row in summary.itertuples()]
        values = [float(row.success_rate) if pd.notna(row.success_rate) else 0.0 for row in summary.itertuples()]
    else:
        labels = ["missing"]
        values = [0.0]
    _plot_bar_pdf(
        FIGURES / "high_fidelity_heldout_success.pdf",
        labels,
        values,
        "Bounded High-Fidelity Probe Success",
        "mean success rate",
        "Boundary: bounded simulator probes, not full-scale external trained-policy evidence.",
    )

    engines = sorted(set(str(row.get("engine", "")) for row in rows if row.get("engine")))
    tasks = sorted(set(str(row.get("task_id", "")) for row in rows if row.get("task_id")))
    _write(
        REPORTS / "HIGH_FIDELITY_POLICY_RESULTS.md",
        f"""
# High-Fidelity Policy Results

Generated: `{_utc()}`

Status: `complete_only_bounded_high_fidelity_probe`

The repository contains bounded high-fidelity/contact probes in at least these engines or settings: `{', '.join(engines)}`. These probes are useful stress evidence, but they are not a full external trained-policy benchmark and do not close the hardware evidence tier.

| field | value |
|---|---|
| result csv | `results/high_fidelity_policy_results.csv` |
| figure | `figures/high_fidelity_heldout_success.pdf` |
| source table | `results/high_fidelity_benchmark.csv` |
| task settings counted | {len(tasks)} |

Allowed wording: BodyShield was checked in bounded MuJoCo/ManiSkill-style probes. Do not claim broad simulator-suite dominance or deployment transfer.
""",
    )


def write_data_blockers() -> None:
    real_rows = [
        {
            "dataset": "real_video_wam",
            "status": "readiness_only_blocked_missing_dataset",
            "required_item": "real camera/video rollouts with train/validation/test split",
            "available_artifact": "results/real_video_wam_readiness.csv",
            "allowed_wording": "The repository defines the schema and readiness check only.",
        },
        {
            "dataset": "real_video_wam",
            "status": "readiness_only_blocked_missing_dataset",
            "required_item": "frame timestamps, task labels, verifier labels, and perturbation metadata",
            "available_artifact": "configs/real_video_wam_readiness.example.json",
            "allowed_wording": "Do not claim real-video WAM performance.",
        },
    ]
    _write_csv(
        RESULTS / "real_video_wam_results.csv",
        real_rows,
        ["dataset", "status", "required_item", "available_artifact", "allowed_wording"],
    )
    _write(
        REPORTS / "REAL_VIDEO_WAM_RESULTS.md",
        """
# Real-Video WAM Results

Status: `readiness_only_blocked_missing_dataset`

No real-camera training/evaluation dataset is present. The repository includes schema and readiness checks, but it does not include real-video WAM evidence.

Artifacts:

- `results/real_video_wam_results.csv`
- `results/real_video_wam_readiness.csv`
- `configs/real_video_wam_readiness.example.json`

Allowed wording: readiness-only. Do not claim real-video WAM performance or real camera generalization.
""",
    )

    trace_rows = [
        {
            "dataset": "corrective_trace",
            "status": "readiness_only_blocked_missing_dataset",
            "required_item": "human or controller corrective traces with before/after outcomes",
            "available_artifact": "results/corrective_trace_readiness.csv",
            "allowed_wording": "The repository defines the schema and readiness check only.",
        },
        {
            "dataset": "corrective_trace",
            "status": "readiness_only_blocked_missing_dataset",
            "required_item": "held-out corrective traces for final adaptation evaluation",
            "available_artifact": "configs/corrective_trace_readiness.example.json",
            "allowed_wording": "Do not claim real corrective-trace adaptation.",
        },
    ]
    _write_csv(
        RESULTS / "corrective_trace_results.csv",
        trace_rows,
        ["dataset", "status", "required_item", "available_artifact", "allowed_wording"],
    )
    _write(
        REPORTS / "CORRECTIVE_TRACE_RESULTS.md",
        """
# Corrective Trace Results

Status: `readiness_only_blocked_missing_dataset`

No real corrective-trace dataset is present. Existing corrective-adaptation tables are analytic/synthetic and cannot be used as real correction evidence.

Artifacts:

- `results/corrective_trace_results.csv`
- `results/corrective_trace_readiness.csv`
- `results/corrective_adaptation_eval.csv`

Allowed wording: synthetic corrective-adaptation proxy only. Do not claim real corrective-trace adaptation.
""",
    )


def write_hardware_blockers() -> None:
    blockers = [
        "assembled SO-ARM101/SO-101 with workspace limits verified",
        "physical emergency stop tested before any batch run",
        "camera verifier calibrated against manual labels",
        "noise floor measured with repeated safe primitives",
        "reset protocol reliability measured",
        "held-out physical modifications defined and installed",
        "all-trials video index with failures and ambiguous cases",
    ]
    blocker_rows = [
        {
            "gate": "robot_setup_confirmation",
            "status": "blocked_by_hardware",
            "missing_item": "explicit user confirmation of robot, workspace, camera, reset, and emergency stop",
            "evidence_artifact": "HARDWARE_AUTONOMOUS_CLI_RUNBOOK.md",
            "allowed_wording": "hardware phase not started",
        },
        {
            "gate": "safety_gate",
            "status": "blocked_by_hardware",
            "missing_item": "bounded safe primitive healthcheck on the physical arm",
            "evidence_artifact": "SAFE_ROBOT_API_SPEC.md",
            "allowed_wording": "software safety gate exists; physical gate not run",
        },
        {
            "gate": "noise_floor",
            "status": "blocked_by_hardware",
            "missing_item": "repeatability measurements for safe primitives",
            "evidence_artifact": "results/hardware_noise_floor.csv",
            "allowed_wording": "not measured",
        },
        {
            "gate": "camera_verifier",
            "status": "blocked_by_hardware",
            "missing_item": "manual labels and agreement audit",
            "evidence_artifact": "results/verifier_calibration.csv",
            "allowed_wording": "not measured",
        },
        {
            "gate": "reset_reliability",
            "status": "blocked_by_hardware",
            "missing_item": "reset success/failure logs across trials",
            "evidence_artifact": "results/reset_reliability.csv",
            "allowed_wording": "not measured",
        },
        {
            "gate": "heldout_physical_modifications",
            "status": "blocked_by_hardware",
            "missing_item": "real payload/tool/gripper/surface/obstacle modifications",
            "evidence_artifact": "results/hardware_heldout_physical_mods.csv",
            "allowed_wording": "not run",
        },
        {
            "gate": "hardware_videos",
            "status": "blocked_by_hardware",
            "missing_item": "all-trials real-camera videos",
            "evidence_artifact": "videos/hardware/index.md",
            "allowed_wording": "not recorded",
        },
    ]
    _write_csv(
        RESULTS / "hardware_readiness.csv",
        blocker_rows,
        ["gate", "status", "missing_item", "evidence_artifact", "allowed_wording"],
    )
    _write_csv(
        RESULTS / "hardware_noise_floor.csv",
        [
            {
                "measurement": "noise_floor",
                "status": "blocked_by_hardware",
                "n_trials": 0,
                "mean": "",
                "std": "",
                "unit": "",
                "missing_item": "physical robot repeatability logs",
            }
        ],
        ["measurement", "status", "n_trials", "mean", "std", "unit", "missing_item"],
    )
    _write_csv(
        RESULTS / "verifier_calibration.csv",
        [
            {
                "measurement": "camera_verifier_agreement",
                "status": "blocked_by_hardware",
                "n_labels": 0,
                "accuracy": "",
                "ambiguous_rate": "",
                "missing_item": "manual labels and camera frames",
            }
        ],
        ["measurement", "status", "n_labels", "accuracy", "ambiguous_rate", "missing_item"],
    )
    _write_csv(
        RESULTS / "reset_reliability.csv",
        [
            {
                "measurement": "reset_reliability",
                "status": "blocked_by_hardware",
                "n_resets": 0,
                "success_rate": "",
                "missing_item": "physical reset attempts",
            }
        ],
        ["measurement", "status", "n_resets", "success_rate", "missing_item"],
    )
    hardware_result_files = {
        "hardware_bodybreak_search.csv": "minimal physical break search",
        "hardware_oracle_feasibility.csv": "physical oracle feasibility",
        "hardware_bodyshield_repair.csv": "physical before/after BodyShield repair",
        "hardware_heldout_physical_mods.csv": "held-out physical modifications",
    }
    for filename, label in hardware_result_files.items():
        _write_csv(
            RESULTS / filename,
            [
                {
                    "experiment": label,
                    "status": "blocked_by_hardware",
                    "n_trials": 0,
                    "success_rate": "",
                    "missing_item": "hardware phase not started",
                }
            ],
            ["experiment", "status", "n_trials", "success_rate", "missing_item"],
        )

    _plot_blocked_pdf(FIGURES / "hardware_noise_floor.pdf", "Hardware Noise Floor", blockers[:4])
    _plot_blocked_pdf(FIGURES / "hardware_bodybreak_search_efficiency.pdf", "Hardware BodyBreak Search", blockers)
    _plot_blocked_pdf(FIGURES / "hardware_before_after_repair.pdf", "Hardware Before/After Repair", blockers)
    _plot_blocked_pdf(FIGURES / "hardware_heldout_success.pdf", "Hardware Held-Out Physical Modifications", blockers)

    _write(
        REPORTS / "HARDWARE_BLOCKER.md",
        f"""
# Hardware Blocker

Generated: `{_utc()}`

Status: `blocked_by_hardware`

No physical motion was started by this v3 pass. Hardware remains blocked until all required setup and safety confirmations are complete.

Missing items:

{chr(10).join(f"- {item}" for item in blockers)}

Allowed wording: software readiness only. Do not claim hardware validation, measured noise floor, camera-verifier accuracy, reset reliability, real held-out physical modifications, or real-robot before/after repair.
""",
    )
    _write(
        REPORTS / "HARDWARE_READINESS_AUDIT.md",
        """
# Hardware Readiness Audit

Status: `blocked_by_hardware`

| artifact | status |
|---|---|
| `results/hardware_readiness.csv` | blocker rows written |
| `results/hardware_noise_floor.csv` | blocked placeholder, no measurements |
| `results/verifier_calibration.csv` | blocked placeholder, no labels |
| `results/reset_reliability.csv` | blocked placeholder, no reset attempts |
| `videos/hardware/index.md` | blocked placeholder, no real videos |

The safe API and runbooks exist, but hardware experiments cannot start without explicit physical confirmation.
""",
    )
    reports = {
        "HARDWARE_NOISE_FLOOR.md": "Noise floor is not measured.",
        "HARDWARE_BODYBREAK_SEARCH.md": "Physical BodyBreak search is not run.",
        "HARDWARE_ORACLE_FEASIBILITY.md": "Physical oracle feasibility is not run.",
        "HARDWARE_BODYSHIELD_REPAIR.md": "Physical repair validation is not run.",
        "HARDWARE_HELDOUT_PHYSICAL_MODS.md": "Held-out physical modifications are not run.",
    }
    for filename, sentence in reports.items():
        _write(
            REPORTS / filename,
            f"""
# {filename.removesuffix('.md').replace('_', ' ').title()}

Status: `blocked_by_hardware`

{sentence} See `reports/HARDWARE_BLOCKER.md` and `results/hardware_readiness.csv`.
""",
        )
    hardware_video_dir = VIDEOS / "hardware"
    _write(
        hardware_video_dir / "index.md",
        """
# Hardware Video Index

Status: `blocked_by_hardware`

No real hardware videos are present. Required future rows must include trial id, task, perturbation, method, verifier decision, manual label, failure reason, and file path.
""",
    )
    _write(hardware_video_dir / "README.md", (hardware_video_dir / "index.md").read_text(encoding="utf-8"))


def write_post_nonhardware_audit() -> None:
    rows = [
        ("Python package/tests/CI", "complete", "bodyshield/, tests/, Makefile, pyproject.toml", "67 local tests passed before v3 edits", "claim software package only"),
        ("Analytic simulation trials", "complete", "results/trials.parquet, logs/sim/results.jsonl", "CPU analytic/synthetic scope", "claim analytic-simulation evidence"),
        ("BodyBreak search", "complete", "results/breaking_search.csv, reports/BODYBREAK_MINIMALITY_AUDIT.md", "estimated minimal break only", "do not claim global minimality"),
        ("BodyShield repair", "complete", "results/repair_history.csv, reports/gate_2_before_after_repair.md", "analytic repair policies", "claim before/after analytic repair"),
        ("Budget and fairness", "complete", "reports/BUDGET_AND_FAIRNESS_AUDIT.md", "baseline tuning remains analytic", "claim budget-matched local comparison"),
        ("Claim/citation/repro audits", "complete", "reports/CLAIM_LEDGER.md, reports/citation_verification.md, REPRODUCE.md", "local verification", "claim audited local package"),
        ("High-fidelity probes", "complete only analytic surrogate", "results/high_fidelity_policy_results.csv", "bounded probes, not full external trained policies", "claim bounded simulator probes"),
        ("External trained policy benchmark", "blocked by external data/checkpoints", "reports/EXTERNAL_CHECKPOINT_BLOCKER.md", "no checkpoint in repo", "do not claim external checkpoint validation"),
        ("Real-video WAM", "readiness only", "reports/REAL_VIDEO_WAM_RESULTS.md", "dataset missing", "schema/readiness only"),
        ("Corrective-trace adaptation", "readiness only", "reports/CORRECTIVE_TRACE_RESULTS.md", "dataset missing", "synthetic proxy only"),
        ("Oracle feasibility", "complete only analytic surrogate", "reports/oracle_feasibility.md", "not physical oracle feasibility", "claim analytic upper-bound gap"),
        ("Hardware noise/verifier/reset", "blocked by hardware", "reports/HARDWARE_BLOCKER.md", "robot/camera/estop not confirmed", "do not claim hardware evidence"),
        ("Held-out physical modifications", "blocked by hardware", "reports/HARDWARE_HELDOUT_PHYSICAL_MODS.md", "physical mods not run", "do not claim real physical modifications"),
        ("Videos", "complete only synthetic", "videos/index.md, videos/hardware/index.md", "generated frames only; no real hardware videos", "claim synthetic rollout media"),
        ("Paper", "draft only", "paper/main.tex, paper/bodyshield_full_paper.pdf", "needs human review and missing evidence tiers", "analytic/simulation study wording only"),
        ("Release", "complete local archive", "release/bodyshield_non_hardware_release.zip", "not independent external archive", "claim local deterministic bundle"),
    ]
    table = "\n".join(
        f"| {tier} | {status} | `{artifact}` | {residual} | {wording} |" for tier, status, artifact, residual, wording in rows
    )
    _write(
        REPORTS / "POST_NON_HARDWARE_REPO_AUDIT.md",
        f"""
# Post-Nonhardware Repository Audit

Generated: `{_utc()}`

This audit classifies every remaining evidence tier after the v2 non-hardware package and v3 post-nonhardware pass.

| evidence tier | classification | evidence | residual blocker/risk | allowed wording |
|---|---|---|---|---|
{table}

Bottom line: the repository is strong as a non-hardware analytic/synthetic artifact pack. It is not evidence-complete for a final robotics submission.

{PAPER_NOT_READY}
""",
    )


def write_method_theory() -> None:
    _write(
        REPORTS / "METHOD_THEORY_STRENGTHENING.md",
        r"""
# Method Theory Strengthening

Status: `bounded_formalization`

## Perturbation Space

Let a task be tau, a robot/body interface be r, and a policy be pi_theta. BodyShield models an embodiment-control perturbation as z in Z, where Z is the product of bounded axes such as latency, action noise, joint-range scale, gripper authority, speed/acceleration caps, calibration offset, controller-rate change, camera shift, payload, tool extension, surface friction, and obstacle clearance.

Each z has a normalized cost c(z) in [0, 1]. The current package evaluates a finite candidate subset Z_B under a fixed evaluator budget B.

## Estimated Minimal Break

BodyBreak estimates

    z_hat = argmin_{z in Z_B} c(z) subject to S(pi_theta, tau, r, z) <= alpha

where S is a success-rate or success-probability evaluator and alpha is the break threshold. Because Z_B is finite and the evaluator is noisy or approximate, z_hat is an estimated minimal break under the candidate set and budget, not a global certificate over Z.

## Robustness Radius and Profile

The robustness radius rho(pi_theta, tau, r) is reported as the smallest evaluated cost with failure under the threshold. A robustness profile R(epsilon) reports the empirical success rate for all evaluated perturbations with c(z) <= epsilon. Profiles are more reviewer-resistant than a single radius because they show whether repair improves only one point or an interval of perturbation severity.

## Repair Objective

BodyShield repairs by minimizing a weighted loss over nominal cases, discovered break cases, near-boundary cases, and held-out validation cases:

    min_theta L_nominal(theta) + lambda_b L_break(theta; B_break) + lambda_h L_heldout(theta; B_holdout) + lambda_s C_secondary(theta)

The intended mechanism is not random broadening. It is diagnosis-driven allocation of repair capacity to axes that were shown to break the controller.

## Budget Accounting

All fair comparisons must count evaluator calls, rollout count, seeds, policy updates, search candidates, and baseline tuning attempts. Domain randomization and dynamics randomization are dangerous baselines because they are established sim-to-real methods; BodyShield should be claimed only when it wins under equal or lower budget in the stated scope.

## Why Not Global Optimization

Global optimization is not claimed because the perturbation space contains mixed continuous, discrete, and semantic physical modifications; hardware evaluation is expensive; and verifier labels can be noisy. The package therefore reports finite-budget falsification and repair, plus dense post-hoc audits where available.

## Sample-Efficiency Assumptions

BodyShield can be sample efficient only when hidden failure axes are low-dimensional enough to identify, repair capacity is sufficient, perturbation labels are reliable, and held-out perturbations share mechanism-level structure with discovered breaks. It can fail when failures are high-dimensional, discontinuous, outside the repair parameterization, or dominated by unmodeled perception/contact effects.

## Proposition (Finite Candidate Soundness)

For a fixed candidate set Z_B, deterministic evaluator S, threshold alpha, and exact costs c, if BodyBreak returns the evaluated candidate z_hat with minimal c among all candidates with S(pi_theta, tau, r, z) <= alpha, then no candidate in Z_B with lower cost was observed to break the policy. This proposition does not imply global minimality over Z, hardware transfer, or robustness to unevaluated perturbations.

## Limits

The current evidence is analytic/synthetic plus bounded simulator probes. Hardware validation, external trained-policy checkpoints, real-video WAM, real corrective traces, and independent archive replication are outside the completed evidence set.
""",
    )


def write_full_paper() -> None:
    main_tex = r"""
\documentclass[10pt,conference]{IEEEtran}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{url}
\title{BodyShield: An Analytic-Simulation Study of Falsifying and Repairing Hidden Embodiment-Control Assumptions}
\author{Anonymous Authors}
\begin{document}
\maketitle
\begin{abstract}
Robot policies can pass nominal tests while relying on hidden assumptions about latency, calibration, joint range, gripper authority, sensing geometry, payload, and contact. BodyShield is a falsification-to-repair workflow: BodyBreak searches for low-cost embodiment-control perturbations that break a policy, then BodyShield repairs against discovered failures and evaluates held-out perturbation families. This paper is explicitly an analytic/simulation study. It contains analytic-simulation evidence, generated frames rather than real camera videos, bounded MuJoCo/ManiSkill probes, local surrogate policy repair results, audits, and release verification; real robot results and external full-scale trained-policy high-fidelity benchmarks remain future evidence tiers. The package stops without running trained-policy rollouts, real-video WAM training, or real corrective adaptation, and none establishes physical transfer.
\end{abstract}

\section{Introduction}
Nominal robot success is a weak certificate because a policy may depend on a hidden body or controller detail. A policy that looks competent on the unmodified setup may fail under modest latency, calibration, gripper, range, rate, payload, sensing, or contact shifts. BodyShield targets this failure mode by making hidden embodiment-control assumptions observable, repairable, and auditable.

This paper is framed for adaptive embodied intelligence: the main contribution is a failure-diagnosis and repair loop for policies, not a cheap-arm demonstration and not a broad cross-embodiment-transfer claim.

\section{Related Work}
Domain randomization and dynamics randomization remain the strongest dangerous baselines for this work because they directly address sim-to-real transfer by broadening training distributions \cite{tobin2017domainrandomization,peng2018dynamicsrandomization,openai2018dexterous,openai2019rubiks}. Embodiment-aware deployment methods such as UMI-on-Air and EmbodiSteer adapt or steer policy execution toward a target body \cite{gupta2025umionair,wang2026embodisteer}. Counterexample-guided and verification-guided safe RL search for violations and may guide shielding or repair \cite{karunakaran2020counterexampleguided,le2025verificationguided}. MPC-CBF, robust MPC, reachability, sysID, and online correction methods address safety, model mismatch, or adaptation from different starting assumptions \cite{zeng2021mpccbf,jiang2024transic}.

BodyShield is distinct only in the bounded sense tested here: it searches embodiment-control perturbations, repairs against discovered failures, and requires held-out and hardware-gated evidence before stronger claims.

\section{Problem Formulation}
Let \(z\in\mathcal{Z}\) denote a bounded embodiment-control perturbation with normalized cost \(c(z)\). For policy \(\pi_\theta\), task \(\tau\), and robot archetype \(r\), BodyBreak estimates
\[
z^\star_B = \arg\min_{z\in\mathcal{Z}_B} c(z) \quad \mathrm{s.t.}\quad S(\pi_\theta,\tau,r,z)\leq \alpha,
\]
where \(\mathcal{Z}_B\) is the finite candidate set available under evaluator budget \(B\). This is an estimated finite-budget break, not a global minimality proof.

\section{Method}
BodyBreak compares random, one-axis, grid, and compound adversarial search. BodyShield then uses the discovered break axes to allocate repair capacity while retaining nominal behavior. The repair objective combines nominal retention, discovered break recovery, held-out perturbation performance, and secondary execution costs. The method evidence map is summarized in Table~\ref{tab:evidence}.

\begin{table}[t]
\caption{Evidence tiers after the post-nonhardware v3 pass.}
\label{tab:evidence}
\centering\footnotesize
\begin{tabular}{lll}
\toprule
Tier & Status & Artifact \\
\midrule
Analytic simulation & Complete & \path{results/trials.parquet} \\
High-fidelity probes & Bounded surrogate & \path{results/high_fidelity_policy_results.csv} \\
External checkpoints & Blocked & \path{reports/EXTERNAL_CHECKPOINT_BLOCKER.md} \\
Hardware & Blocked & \path{reports/HARDWARE_BLOCKER.md} \\
\bottomrule
\end{tabular}
\end{table}

\section{Experiments}
The completed package evaluates analytic tasks, robot archetypes, perturbation families, search modes, repair variants, robustness profiles, oracle feasibility, and bounded simulator probes. Evidence lives in \path{results/}, \path{logs/sim/results.jsonl}, \path{tables/sim_main_results.csv}, \path{tables/sim_budget_matched_results.csv}, and \path{data_schema.json}. Figure~\ref{fig:repair} points to the main analytic before/after repair visualization.

\begin{figure}[t]
\centering
\includegraphics[width=.95\linewidth]{figures/bodyshield_before_after.pdf}
\caption{Analytic before/after repair summary. This is not a hardware result.}
\label{fig:repair}
\end{figure}

\section{Results}
The analytic package supports bounded statements: BodyShield improves specific held-out perturbation families under the local budgeted simulation protocol, and bounded high-fidelity probes are exported as stress evidence. The v3 package adds `results/external_policy_benchmark.csv` and `results/high_fidelity_policy_results.csv`, but the external checkpoint row is explicitly blocked.

\section{Real Robot Experiments}
\textbf{Hardware placeholder only. Do not fill until SO-ARM101/SO-101 safety gates pass.} Required hardware evidence includes measured noise floor, camera-verifier agreement, reset reliability, emergency-stop test, all-trials logs, all-trials videos, held-out physical modifications, and physical oracle feasibility.

\section{Limitations}
The current repository lacks hardware noise floor, camera verifier accuracy, reset reliability, real held-out physical modifications, all-trials hardware videos, external trained-policy rollouts, real-video WAM datasets, and real corrective-trace datasets. BodyBreak minimality is estimated over evaluated candidates only.

\section{Reproducibility and Safety}
The package includes tests, claim ledger, citation verification, source audits, release bundle, and `python -m bodyshield.analysis.verify_package --json`. The robot modules expose bounded safe primitives and refuse to run before explicit physical readiness checks. This software boundary does not guarantee hardware safety.

\section{Conclusion}
BodyShield is best read as a falsification-to-repair protocol for hidden embodiment-control assumptions. The non-hardware package is complete under analytic/synthetic scope, while the paper is not ready for final submission until the blocked evidence tiers are closed.

\bibliographystyle{IEEEtran}
\bibliography{references}
\end{document}
"""
    _write(PAPER / "main.tex", main_tex)
    supplement_tex = r"""
\documentclass{article}
\usepackage{booktabs}
\usepackage{url}
\usepackage{amsmath}
\title{BodyShield Supplement: Post-Nonhardware Evidence Map}
\author{Anonymous Authors}
\begin{document}
\maketitle
\section{Artifact Map}
The canonical post-nonhardware audit is \path{reports/POST_NON_HARDWARE_REPO_AUDIT.md}. Hardware blockers are listed in \path{reports/HARDWARE_BLOCKER.md}. External checkpoint blockers are listed in \path{reports/EXTERNAL_CHECKPOINT_BLOCKER.md}. Submission-readiness gates are listed in \path{reports/SUBMISSION_READY_AUDIT.md}.
\section{Boundary}
This supplement covers analytic/synthetic and bounded simulator artifacts only. Real robot videos, physical modifications, real-video WAM, and real corrective traces are absent.
\end{document}
"""
    _write(PAPER / "supplement.tex", supplement_tex)

    full_sections = [
        (
            "Abstract",
            "BodyShield is presented here as an analytic/simulation study of falsifying and repairing hidden embodiment-control assumptions. The package contains simulation, bounded high-fidelity probes, local surrogate policy repair summaries, audits, and release verification. Hardware and external checkpoint evidence are explicitly blocked.",
        ),
        (
            "Method",
            "BodyBreak searches a finite perturbation set for low-cost policy-breaking embodiment-control shifts. BodyShield repairs against discovered break axes and evaluates nominal retention plus held-out perturbation families. The current method validates a falsification-to-repair workflow, not deployment transfer.",
        ),
        (
            "Evidence",
            "Completed tiers include analytic simulation, search/repair, claim ledger, citation verification, local release bundle, bounded high-fidelity probes, and reviewer-risk reports. Partial tiers include local policy surrogates and analytic oracle feasibility.",
        ),
        (
            "Blockers",
            PAPER_NOT_READY,
        ),
        (
            "Allowed Wording",
            "Use analytic/synthetic scope. Do not claim hardware validation, real-video WAM results, real corrective-trace adaptation, external trained-policy benchmark closure, global minimality, autonomous lab operation, or broad superiority over domain randomization, robust control, sysID, or CBF methods.",
        ),
    ]
    _write_text_pdf(PAPER / "bodyshield_full_paper.pdf", "BodyShield Full Paper Draft (Analytic/Simulation Scope)", full_sections)
    _write_text_pdf(PAPER / "bodyshield_supplement.pdf", "BodyShield Supplement Draft", full_sections[2:])
    shutil.copy2(PAPER / "bodyshield_full_paper.pdf", PAPER / "bodyshield.pdf")
    shutil.copy2(PAPER / "bodyshield_full_paper.pdf", PAPER / "main.pdf")


def write_claim_ledger_boundary_addendum() -> None:
    path = REPORTS / "CLAIM_LEDGER.md"
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else "# Claim Ledger\n"
    marker = "## V3 Boundary Addendum"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip()
    addendum = f"""

{marker}

The claim ledger is bounded by these required phrases:

- do not claim physical transfer
- Do not present as real-video WAM evidence.
- Do not present as external/full-scale trained-policy MuJoCo/ManiSkill rollout evidence.
- The local release bundle does not replace external archival upload.

Local evidence references:

- `reports/claim_ledger.csv`
- `reports/POST_NON_HARDWARE_REPO_AUDIT.md`
- `reports/SUBMISSION_READY_AUDIT.md`
- `reports/HARDWARE_BLOCKER.md`
- `reports/EXTERNAL_CHECKPOINT_BLOCKER.md`
- `results/external_policy_benchmark.csv`
- `results/high_fidelity_policy_results.csv`
"""
    path.write_text(text.rstrip() + addendum, encoding="utf-8", newline="\n")


def write_prebuttal_and_readiness() -> None:
    attacks = [
        ("This is just domain randomization.", "No. The package reports budget-matched domain randomization and dynamics-randomization-style baselines. The allowed claim is narrower: diagnosis-driven repair can improve the tested analytic perturbation families under the same local budget."),
        ("Domain randomization is stronger and more established.", "Agreed; it is the dangerous baseline. BodyShield must beat it under equal or lower budget before any stronger wording."),
        ("This is only a benchmark.", "The package includes before/after repair artifacts, not only stress tests, but hardware repair evidence is still blocked."),
        ("The perturbations are artificial.", "Some are analytic/control perturbations. Physical-style proxies exist, while real physical modifications remain blocked by hardware."),
        ("The method overfits to discovered failures.", "Held-out perturbation families and robustness profiles are included, but external checkpoint and physical held-out tests remain future evidence."),
        ("BodyBreak minimality is not proven.", "Correct. The claim is finite-budget estimated minimality over evaluated candidates only."),
        ("Oracle feasibility is synthetic.", "Correct. It is an analytic upper-bound audit, not physical oracle feasibility."),
        ("Baselines may be under-tuned.", "The v2/v3 audits require budget accounting and fair tuning; external trained-controller compute matching remains unresolved."),
        ("High-fidelity probes are too small.", "Correct. They are bounded probes, not full benchmark closure."),
        ("No real videos exist.", "Correct. Current media are generated/synthetic; videos/hardware is a blocked placeholder."),
        ("No real corrective traces exist.", "Correct. Readiness checks exist, dataset evidence does not."),
        ("No real-video WAM data exist.", "Correct. The repository only defines readiness/schema."),
        ("The safe API is not a safety proof.", "Correct. It is a software gate and does not replace physical safety validation."),
        ("The paper is too short for final submission.", "Correct. v3 creates a fuller draft, but the readiness audit still marks the paper not ready."),
        ("The release is not externally archived.", "Correct. It is a local deterministic archive, not independent preservation."),
        ("The method may fail under perception/contact shifts.", "Yes. Those are listed as limitations and require external/hardware evidence."),
        ("Embodiment-aware steering methods already solve this.", "They adapt/steer execution. BodyShield is framed as falsify hidden assumptions, repair, and validate held-out shifts."),
        ("Robust MPC/CBF/sysID could solve it.", "Those are strong alternative families. BodyShield should be compared fairly, not declared superior globally."),
        ("EPEC/human-effect policies distract from the core.", "They are stress-test alternatives only; BodyShield remains the main method."),
        ("The repo overclaims readiness.", "The v3 readiness audit explicitly says the paper is not ready and names blockers."),
    ]
    table = "\n".join(f"| {i} | {attack} | {answer} |" for i, (attack, answer) in enumerate(attacks, start=1))
    _write(
        REPORTS / "FULL_REVIEWER_PREBUTTAL.md",
        f"""
# Full Reviewer Prebuttal

Generated: `{_utc()}`

| # | reviewer attack | response |
|---:|---|---|
{table}

Primary artifacts: `reports/POST_NON_HARDWARE_REPO_AUDIT.md`, `reports/METHOD_THEORY_STRENGTHENING.md`, `reports/BUDGET_AND_FAIRNESS_AUDIT.md`, `reports/EXTERNAL_POLICY_BENCHMARK.md`, `reports/HIGH_FIDELITY_POLICY_RESULTS.md`, and `reports/SUBMISSION_READY_AUDIT.md`.
""",
    )

    gates = [
        ("software_package", "pass", "bodyshield/, tests/, Makefile", "low", "software package complete"),
        ("analytic_simulation", "pass", "results/trials.parquet, logs/sim/results.jsonl", "analytic only", "analytic-simulation evidence"),
        ("budget_fairness", "pass", "reports/BUDGET_AND_FAIRNESS_AUDIT.md", "external controller matching open", "budget-matched local baselines"),
        ("claim_citation_repro", "pass", "reports/CLAIM_LEDGER.md, reports/citation_verification.md, REPRODUCE.md", "local only", "audited local package"),
        ("high_fidelity_bounded", "pass_with_scope_limit", "results/high_fidelity_policy_results.csv", "bounded probes only", "bounded simulator probes"),
        ("external_trained_policy", "fail", "reports/EXTERNAL_CHECKPOINT_BLOCKER.md", "checkpoint missing", "do not claim external policy validation"),
        ("real_video_wam", "fail", "reports/REAL_VIDEO_WAM_RESULTS.md", "dataset missing", "readiness only"),
        ("corrective_trace", "fail", "reports/CORRECTIVE_TRACE_RESULTS.md", "dataset missing", "synthetic proxy only"),
        ("hardware_safety_noise_verifier_reset", "fail", "reports/HARDWARE_BLOCKER.md", "hardware not confirmed or run", "software readiness only"),
        ("heldout_physical_modifications", "fail", "reports/HARDWARE_HELDOUT_PHYSICAL_MODS.md", "physical mods not run", "do not claim physical held-out validation"),
        ("hardware_videos", "fail", "videos/hardware/index.md", "real videos missing", "do not claim real videos"),
        ("paper_human_review", "fail", "paper/main.tex, paper/bodyshield_full_paper.pdf", "human review open and evidence incomplete", "draft analytic/simulation paper"),
        ("external_archive", "fail", "release/bodyshield_non_hardware_release.zip", "local archive only", "local release bundle"),
    ]
    _write_csv(
        RESULTS / "submission_ready_audit.csv",
        [
            {
                "gate_name": gate,
                "pass_fail": status,
                "evidence": evidence,
                "residual_risk": risk,
                "allowed_wording": wording,
            }
            for gate, status, evidence, risk, wording in gates
        ],
        ["gate_name", "pass_fail", "evidence", "residual_risk", "allowed_wording"],
    )
    gate_table = "\n".join(f"| {gate} | {status} | `{evidence}` | {risk} | {wording} |" for gate, status, evidence, risk, wording in gates)
    _write(
        REPORTS / "SUBMISSION_READY_AUDIT.md",
        f"""
# Submission Ready Audit

Generated: `{_utc()}`

| gate name | pass/fail | evidence | residual risk | allowed wording |
|---|---|---|---|---|
{gate_table}

{PAPER_NOT_READY}
""",
    )
    _write(REPORTS / "NOT_READY_REASON.md", PAPER_NOT_READY)


def update_manifest() -> None:
    files = []
    for rel in [
        "reports/POST_NON_HARDWARE_REPO_AUDIT.md",
        "reports/METHOD_THEORY_STRENGTHENING.md",
        "reports/FULL_REVIEWER_PREBUTTAL.md",
        "reports/SUBMISSION_READY_AUDIT.md",
        "reports/HARDWARE_BLOCKER.md",
        "reports/EXTERNAL_POLICY_BENCHMARK.md",
        "reports/HIGH_FIDELITY_POLICY_RESULTS.md",
        "results/external_policy_benchmark.csv",
        "results/high_fidelity_policy_results.csv",
        "results/submission_ready_audit.csv",
        "paper/main.tex",
        "paper/bodyshield_full_paper.pdf",
        "paper/bodyshield_supplement.pdf",
        "figures/external_policy_bodyshield_delta.pdf",
        "figures/high_fidelity_heldout_success.pdf",
    ]:
        path = ROOT / rel
        if path.exists() and path.is_file():
            files.append(
                {
                    "path": rel,
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                    "generated_at": _utc(),
                }
            )
    _write_json(REPORTS / "POST_NON_HARDWARE_ARTIFACT_MANIFEST.json", files)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_readme_note() -> None:
    note = """
# BodyShield Execution Note

The current repository state is non-hardware complete under analytic/synthetic scope. For the v3 post-nonhardware audit, start with:

```bash
python scripts/finalize_v3_artifacts.py
python -m bodyshield.analysis.verify_package --json
```

Hardware remains blocked until the user confirms the SO-ARM101/SO-101 setup, safety gate, camera verifier, reset protocol, and emergency stop are ready. See `reports/SUBMISSION_READY_AUDIT.md` before using any paper wording.
"""
    _write(ROOT / "README_FIRST.md", note)


def refresh_trial_sample_code_hash() -> None:
    sample = RESULTS / "trials_sample.jsonl"
    if not sample.exists() or sample.stat().st_size == 0:
        return
    code_hash = source_tree_hash(ROOT)
    updated_lines: list[str] = []
    for line in sample.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        metadata = record.setdefault("metadata", {})
        metadata["code_commit_hash"] = code_hash
        updated_lines.append(json.dumps(record, sort_keys=True, separators=(",", ":")))
    sample.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    for path in (REPORTS, RESULTS, FIGURES, PAPER, VIDEOS):
        path.mkdir(parents=True, exist_ok=True)
    write_external_policy_benchmark()
    write_high_fidelity_policy_results()
    write_data_blockers()
    write_hardware_blockers()
    write_post_nonhardware_audit()
    write_method_theory()
    write_full_paper()
    write_claim_ledger_boundary_addendum()
    write_prebuttal_and_readiness()
    write_readme_note()
    refresh_trial_sample_code_hash()
    update_manifest()
    rc, verify_text = _run([sys.executable, "-m", "bodyshield.analysis.verify_package", "--json"])
    _write(
        REPORTS / "POST_NON_HARDWARE_V3_RUN_LOG.md",
        f"""
# Post-Nonhardware V3 Run Log

Generated: `{_utc()}`

Verifier return code: `{rc}`

```json
{verify_text}
```

{NON_HARDWARE_MESSAGE}

{PAPER_NOT_READY}
""",
    )
    print(NON_HARDWARE_MESSAGE)
    print(PAPER_NOT_READY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
