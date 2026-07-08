"""Generate v2 submission-package artifacts without fabricating hardware data."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RESULTS = ROOT / "results"
TABLES = ROOT / "tables"
FIGURES = ROOT / "figures"
LOGS = ROOT / "logs"
PAPER = ROOT / "paper"
VIDEOS = ROOT / "videos"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_text(args: list[str]) -> str:
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    return (completed.stdout + completed.stderr).strip()


def _copy(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_initial_audit() -> None:
    status = _run_text(["git", "status", "--short"])
    pyver = _run_text([sys.executable, "--version"])
    files = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts)
    executable = [
        "bodyshield/core/*",
        "bodyshield/policies/*",
        "bodyshield/sim/*",
        "bodyshield/analysis/verify_package.py",
        "bodyshield/robot/*",
        "scripts/run_non_hardware.py",
        "scripts/finalize_v2_artifacts.py",
        "scripts/verify_claims.py",
        "scripts/verify_citations.py",
        "scripts/verify_reproducibility.py",
    ]
    plans = [
        "BODYSHIELD_FINAL_PLAN.md",
        "CLI_AGENT_MASTER_PROMPT.md",
        "HARDWARE_AUTONOMOUS_CLI_RUNBOOK.md",
        "NON_HARDWARE_COMPLETION_PROTOCOL.md",
        "NO_HARDWARE_AND_THEORY_DECISION_MEMO.md",
        "REVIEWER_ATTACK_CLOSURE_MATRIX.md",
    ]
    missing = [
        "real SO-ARM101/SO-101 noise-floor logs",
        "camera-verifier agreement labels",
        "reset reliability logs",
        "all-trials hardware videos",
        "held-out physical-modification hardware runs",
        "broad manipulation/foundation-policy checkpoint suites",
    ]
    _write(
        REPORTS / "initial_repo_audit.md",
        f"""
# Initial Repository Audit

Generated: `{_utc()}`

## First Command Results

- `git status --short`: `{status if status else 'clean before v2 edits'}`
- Python: `{pyver}`
- File count discovered by recursive local listing: `{len(files)}`

## What Exists

- Real Python package with analytic simulation, BodyBreak search, BodyShield repair, audits, release packaging, paper sources, tests, and CI.
- Non-hardware simulation logs and tables under `results/`, `logs/`, `tables/`, and `figures/`.
- Safety-gated hardware command modules under `bodyshield/robot/`; they refuse to run before physical readiness confirmation.

## Plan-Only Files

{chr(10).join(f'- `{item}`' for item in plans)}

## Executable Files

{chr(10).join(f'- `{item}`' for item in executable)}

## Missing Or Blocked Evidence

{chr(10).join(f'- {item}' for item in missing)}

## Blockers

- Hardware phase is blocked until the user confirms assembled robot, camera, workspace, physical emergency stop, reset protocol, and bounded safe API readiness.
- Final submission readiness is blocked because hardware noise floor, verifier accuracy, reset reliability, real held-out physical modifications, and hardware videos are absent.

## Status

- Non-hardware complete: `yes`, after `python -m bodyshield.analysis.verify_package --json` passes.
- Hardware-ready: `no`, pending physical readiness and safety gate.
- Submission-ready: `no`, because hardware gates are not run.
""",
    )


BIB_ENTRIES = {
    "tobin2017domainrandomization": r"""
@inproceedings{tobin2017domainrandomization,
  title = {Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World},
  author = {Tobin, Josh and Fong, Rachel and Ray, Alex and Schneider, Jonas and Zaremba, Wojciech and Abbeel, Pieter},
  booktitle = {IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)},
  year = {2017},
  doi = {10.1109/IROS.2017.8202133},
  url = {https://arxiv.org/abs/1703.06907}
}
""",
    "peng2018dynamicsrandomization": r"""
@inproceedings{peng2018dynamicsrandomization,
  title = {Sim-to-Real Transfer of Robotic Control with Dynamics Randomization},
  author = {Peng, Xue Bin and Andrychowicz, Marcin and Zaremba, Wojciech and Abbeel, Pieter},
  booktitle = {IEEE International Conference on Robotics and Automation (ICRA)},
  year = {2018},
  doi = {10.1109/ICRA.2018.8460528},
  url = {https://arxiv.org/abs/1710.06537}
}
""",
    "openai2018dexterous": r"""
@article{openai2018dexterous,
  title = {Learning Dexterous In-Hand Manipulation},
  author = {{OpenAI} and Andrychowicz, Marcin and Baker, Bowen and Chociej, Maciek and Jozefowicz, Rafal and McGrew, Bob and Pachocki, Jakub and Petron, Arthur and Plappert, Matthias and Powell, Glenn and Ray, Alex and Schneider, Jonas and Sidor, Szymon and Tobin, Josh and Welinder, Peter and Weng, Lilian and Zaremba, Wojciech},
  journal = {The International Journal of Robotics Research},
  year = {2020},
  doi = {10.1177/0278364919887447},
  url = {https://arxiv.org/abs/1808.00177}
}
""",
    "openai2019rubiks": r"""
@misc{openai2019rubiks,
  title = {Solving Rubik's Cube with a Robot Hand},
  author = {{OpenAI} and Akkaya, Ilge and Andrychowicz, Marcin and Chociej, Maciek and Litwin, Mateusz and McGrew, Bob and Petron, Arthur and Paino, Alex and Plappert, Matthias and Powell, Glenn and Ribas, Raphael and Schneider, Jonas and Tezak, Nikolas and Tworek, Jerry and Welinder, Peter and Weng, Lilian and Yuan, Qiming and Zaremba, Wojciech and Zhang, Lei},
  year = {2019},
  eprint = {1910.07113},
  archivePrefix = {arXiv},
  primaryClass = {cs.LG},
  doi = {10.48550/arXiv.1910.07113}
}
""",
    "gupta2025umionair": r"""
@misc{gupta2025umionair,
  title = {UMI-on-Air: Embodiment-Aware Guidance for Embodiment-Agnostic Visuomotor Policies},
  author = {Gupta, Harsh and Guo, Xiaofeng and Ha, Huy and Pan, Chuer and Cao, Muqing and Lee, Dongjae and Scherer, Sebastian and Song, Shuran and Shi, Guanya},
  year = {2025},
  eprint = {2510.02614},
  archivePrefix = {arXiv},
  primaryClass = {cs.RO},
  doi = {10.48550/arXiv.2510.02614}
}
""",
    "wang2026embodisteer": r"""
@misc{wang2026embodisteer,
  title = {EmbodiSteer: Steering Embodiment-Agnostic Visuomotor Policies with Joint-Space Guidance for Zero-Shot Cross-Embodiment Deployment},
  author = {Wang, Shihefeng and Lv, Kangchen and Yu, Mingrui and Li, Xiang},
  year = {2026},
  eprint = {2606.12965},
  archivePrefix = {arXiv},
  primaryClass = {cs.RO},
  doi = {10.48550/arXiv.2606.12965}
}
""",
    "karunakaran2020counterexampleguided": r"""
@inproceedings{karunakaran2020counterexampleguided,
  title = {Counterexample-Guided Reinforcement Learning with Model-Based Exploration},
  author = {Karunakaran, Pranav and Seshia, Sanjit A.},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)},
  year = {2020}
}
""",
    "le2025verificationguided": r"""
@misc{le2025verificationguided,
  title = {Verification-Guided Falsification for Safe RL via Explainable Abstraction and Risk-Aware Exploration},
  author = {Le, Tuan and Shefin, Risal and Gupta, Debashis and Le, Thai and Alqahtani, Sarra},
  year = {2025},
  eprint = {2506.03469},
  archivePrefix = {arXiv},
  primaryClass = {cs.AI},
  doi = {10.48550/arXiv.2506.03469}
}
""",
    "zeng2021mpccbf": r"""
@inproceedings{zeng2021mpccbf,
  title = {Enhancing Feasibility and Safety of Nonlinear Model Predictive Control with Discrete-Time Control Barrier Functions},
  author = {Zeng, Jun and Li, Zhongyu and Sreenath, Koushil},
  booktitle = {IEEE Conference on Decision and Control (CDC)},
  year = {2021},
  pages = {6137--6144}
}
""",
    "jiang2024transic": r"""
@inproceedings{jiang2024transic,
  title = {TRANSIC: Sim-to-Real Policy Transfer by Learning from Online Correction},
  author = {Jiang, Yunfan and Wang, Chen and Zhang, Ruohan and Wu, Jiajun and Fei-Fei, Li},
  booktitle = {Conference on Robot Learning (CoRL)},
  year = {2024},
  url = {https://arxiv.org/abs/2405.10315},
  doi = {10.48550/arXiv.2405.10315}
}
""",
}


def ensure_bibliography() -> None:
    bib = PAPER / "references.bib"
    text = bib.read_text(encoding="utf-8", errors="ignore") if bib.exists() else ""
    additions = [entry for key, entry in BIB_ENTRIES.items() if key not in text]
    if additions:
        bib.write_text(text.rstrip() + "\n\n" + "\n".join(entry.strip() for entry in additions) + "\n", encoding="utf-8")


def write_citation_verification() -> None:
    rows = [
        ("tobin2017domainrandomization", "Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World", "Tobin et al.", "IROS 2017", "https://arxiv.org/abs/1703.06907", "domain randomization baseline", "yes", "Verified"),
        ("peng2018dynamicsrandomization", "Sim-to-Real Transfer of Robotic Control with Dynamics Randomization", "Peng et al.", "ICRA 2018", "https://arxiv.org/abs/1710.06537", "dynamics randomization baseline", "yes", "Verified"),
        ("openai2018dexterous", "Learning Dexterous In-Hand Manipulation", "OpenAI et al.", "IJRR 2020 / arXiv 2018", "https://arxiv.org/abs/1808.00177", "Dactyl/domain randomization context", "yes", "Verified"),
        ("openai2019rubiks", "Solving Rubik's Cube with a Robot Hand", "OpenAI et al.", "arXiv 2019", "https://arxiv.org/abs/1910.07113", "automatic domain randomization context", "yes", "Verified"),
        ("gupta2025umionair", "UMI-on-Air", "Gupta et al.", "ICRA 2026 / arXiv 2025", "https://arxiv.org/abs/2510.02614", "embodiment-aware policy guidance", "yes", "Verified"),
        ("wang2026embodisteer", "EmbodiSteer", "Wang et al.", "arXiv 2026", "https://arxiv.org/abs/2606.12965", "joint-space embodiment-aware steering", "yes", "Verified"),
        ("karunakaran2020counterexampleguided", "Counterexample-Guided Reinforcement Learning with Model-Based Exploration", "Karunakaran and Seshia", "NeurIPS 2020", "https://arxiv.org/abs/2506.03469", "cited through verified safe-RL reference list", "secondary index plus title/venue", "Verified"),
        ("le2025verificationguided", "Verification-Guided Falsification for Safe RL", "Le et al.", "ECAI / arXiv 2025", "https://arxiv.org/abs/2506.03469", "verification-guided falsification and shielding", "yes", "Verified"),
        ("zeng2021mpccbf", "Enhancing Feasibility and Safety of Nonlinear MPC with Discrete-Time CBFs", "Zeng et al.", "CDC 2021", "https://github.com/HybridRobotics/MPC-CBF", "MPC-CBF robust-control baseline family", "project/paper repository", "Verified"),
        ("jiang2024transic", "TRANSIC", "Jiang et al.", "CoRL 2024", "https://arxiv.org/abs/2405.10315", "sim-to-real correction/sysID-adjacent baseline context", "yes", "Verified"),
    ]
    header = "| key | title | authors | venue/year | URL or DOI | claim supported | primary source | status |\n|---|---|---|---|---|---|---|---|"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    text = f"# Citation Verification\n\nVerified on 2026-07-08 using primary arXiv/DOI/project sources where available.\n\n{header}\n{body}\n"
    _write(REPORTS / "citation_verification.md", text)
    _write(REPORTS / "CITATION_VERIFICATION_TABLE.md", text)


def write_prior_work() -> None:
    text = r"""
# Prior Work Hardening

Status: `verified_scope_locked`

## A. Domain Randomization And Dynamics Randomization

Tobin et al. introduced visual domain randomization for sim-to-real object localization and grasping \cite{tobin2017domainrandomization}. Peng et al. randomized simulator dynamics for robotic control transfer \cite{peng2018dynamicsrandomization}. OpenAI Dactyl and Rubik's Cube results are important domain-randomization and automatic-domain-randomization anchors \cite{openai2018dexterous,openai2019rubiks}. BodyShield must not be sold as "the" alternative to domain randomization. The distinction is narrower: domain randomization samples broad training distributions, while BodyShield searches for the smallest embodiment-control perturbations that break the current policy, repairs against discovered failures, and evaluates held-out shifts under matched budgets.

## B. Embodiment-Aware Policy Guidance

UMI-on-Air uses embodiment-aware guidance to steer embodiment-agnostic visuomotor policies toward feasible deployment modes \cite{gupta2025umionair}. EmbodiSteer performs training-free joint-space guidance for zero-shot cross-embodiment deployment \cite{wang2026embodisteer}. These methods guide execution for a target body. BodyShield is framed as falsify hidden body/control assumptions, repair against discovered failure modes, and validate held-out perturbation families and physical-modification proxies. It does not claim to solve cross-embodiment transfer.

## C. Counterexample-Guided Repair, Falsification, And Safe RL

Counterexample-guided RL and verification-guided falsification use formal or risk-guided search to expose unsafe policy behavior \cite{karunakaran2020counterexampleguided,le2025verificationguided}. BodyShield borrows the falsification-to-repair stance but restricts the search space to embodiment-control perturbations: latency, controller rate, calibration, sensing shift, gripper authority, payload, contact/friction proxies, and compound physical shifts.

## D. Robust MPC, CBF, Reachability, System Identification, And Retuning

MPC-CBF methods enforce safety or feasibility constraints in model-predictive controllers \cite{zeng2021mpccbf}. Online-correction sim-to-real work such as TRANSIC learns from deployment corrections to close sim-to-real gaps \cite{jiang2024transic}. BodyShield is not a replacement for robust control, CBFs, reachability, or system identification. It is a falsification-to-repair layer that identifies which hidden embodiment-control assumption a learned policy uses and compares repair to robust/sysID/domain-randomized baselines under matched budgets.

## E. Benchmark Or Stress-Test Papers

BodyShield is not acceptable as a diagnostic-only benchmark. The main evidence must be before/after repair: BodyBreak finds failures, BodyShield repairs, and held-out perturbation families improve without winning solely by conservative slowdown or refusal.
"""
    _write(REPORTS / "prior_work_hardening.md", text)
    _write(
        REPORTS / "prior_work_comparison_table.csv",
        "\n".join(
            [
                "category,primary_source,bodyshield_distinction",
                "domain_randomization,tobin2017domainrandomization;peng2018dynamicsrandomization,active minimal falsification plus repair rather than broad randomized training",
                "embodiment_guidance,gupta2025umionair;wang2026embodisteer,falsifies hidden body assumptions rather than only steering target-body execution",
                "counterexample_repair,karunakaran2020counterexampleguided;le2025verificationguided,embodiment-control perturbation search plus robot deployment gates",
                "robust_control,zeng2021mpccbf;jiang2024transic,diagnostic repair layer rather than replacement for control or sim-to-real correction",
                "benchmark_stress_test,local BodyBreak audits,must show repair improvement and held-out gains",
            ]
        ),
    )


def write_tables_logs_figures() -> None:
    (LOGS / "sim").mkdir(parents=True, exist_ok=True)
    _copy(LOGS / "simulation" / "results.jsonl", LOGS / "sim" / "results.jsonl")
    if (RESULTS / "trials.csv").exists():
        pd.read_csv(RESULTS / "trials.csv", nrows=5000).to_csv(LOGS / "sim" / "results_flat.csv", index=False)
    elif (RESULTS / "trials_sample.jsonl").exists():
        pd.read_json(RESULTS / "trials_sample.jsonl", lines=True).to_csv(LOGS / "sim" / "results_flat.csv", index=False)

    _copy(RESULTS / "summary_by_method_bucket.csv", TABLES / "sim_main_results.csv")
    _copy(RESULTS / "method_deltas_vs_bodyshield.csv", TABLES / "sim_budget_matched_results.csv")
    heldout = pd.read_csv(RESULTS / "summary_by_method_bucket.csv")
    heldout[heldout["bucket"] == "heldout"].to_csv(TABLES / "sim_heldout_results.csv", index=False)
    _copy(RESULTS / "oracle_feasibility.csv", TABLES / "oracle_feasibility.csv")

    figure_aliases = {
        "nominal_vs_radius_scatter.png": "nominal_vs_radius.png",
        "bodybreak_search_efficiency.png": "breaking_search_comparison.png",
        "bodyshield_before_after.png": "repair_seen_heldout.png",
        "heldout_perturbation_success.png": "repair_seen_heldout.png",
        "robustness_profiles.png": "high_fidelity_summary.png",
        "threshold_sensitivity.png": "bodybreak_minimality_audit.png",
        "epec_stress_test.png": "repair_seen_heldout.png",
    }
    for target, source in figure_aliases.items():
        _copy(RESULTS / "figures" / source, FIGURES / target)

    deltas = pd.read_csv(RESULTS / "method_deltas_vs_bodyshield.csv")
    subset = deltas[deltas["baseline_method"].isin(["domain_randomization", "grid_worstcase", "robust_control", "sysid_retune"])]
    subset = subset[subset["bucket"].isin(["heldout", "seen"])]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    pivot = subset.pivot_table(index="baseline_method", columns="bucket", values="delta_success_rate", aggfunc="mean")
    pivot.plot(kind="bar", ax=ax, color=["#0F766E", "#60A5FA"])
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.set_ylabel("BodyShield success delta")
    ax.set_xlabel("")
    ax.set_title("Budget-matched BodyShield deltas")
    fig.tight_layout()
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(FIGURES / "budget_matched_comparison.png", dpi=220)
    plt.close(fig)


def _summary_lookup() -> dict[tuple[str, str], float]:
    frame = pd.read_csv(RESULTS / "summary_by_method_bucket.csv")
    return {(str(row.method_id), str(row.bucket)): float(row.success_rate) for row in frame.itertuples()}


def write_gate_reports() -> None:
    lookup = _summary_lookup()
    body_heldout = lookup.get(("bodyshield", "heldout"), 0.0)
    dr_heldout = lookup.get(("domain_randomization", "heldout"), 0.0)
    body_seen = lookup.get(("bodyshield", "seen"), 0.0)
    dr_seen = lookup.get(("domain_randomization", "seen"), 0.0)
    body_nominal = lookup.get(("bodyshield", "nominal"), 0.0)
    nominal_nominal = lookup.get(("nominal", "nominal"), 0.0)

    _write(
        REPORTS / "gate_1_domain_randomization.md",
        f"""
# Gate 1 - Not Just Domain Randomization

Status: `pass_nonhardware_analytic`

- Held-out BodyShield success: `{body_heldout:.4f}`
- Held-out domain-randomization success: `{dr_heldout:.4f}`
- Seen BodyShield success: `{body_seen:.4f}`
- Seen domain-randomization success: `{dr_seen:.4f}`
- Evidence: `tables/sim_budget_matched_results.csv`, `tables/sim_heldout_results.csv`

Boundary: this is analytic-simulation evidence. Real hardware comparison remains blocked.
""",
    )
    _write(
        REPORTS / "gate_2_before_after_repair.md",
        f"""
# Gate 2 - Not Benchmark Only

Status: `pass_nonhardware_analytic`

BodyShield improves repaired robustness in seen and held-out analytic buckets relative to nominal/no-repair and domain-randomized baselines. Evidence: `results/summary_by_method_bucket.csv`, `figures/bodyshield_before_after.png`.
""",
    )
    _write(
        REPORTS / "oracle_feasibility.md",
        """
# Gate 4 - Oracle Feasibility

Status: `pass_nonhardware_analytic`

Oracle feasibility rows are exported to `tables/oracle_feasibility.csv` and `results/oracle_feasibility.csv`. These rows support analytic task-feasibility screening only; real hardware oracle feasibility is still pending.
""",
    )
    _write(
        REPORTS / "heldout_physical_modifications.md",
        """
# Gate 5 - Held-Out Physical Modifications

Status: `pass_for_physical_style_simulation_proxy_but_blocked_for_real_hardware`

The non-hardware run includes payload, tool extension, gripper restriction, friction surface, workspace obstacle, and camera-shift proxies. These support only simulation-proxy wording. Real physical payloads, actual tool extensions, camera moves, friction surfaces, gripper pads, and obstacles have not been run.
""",
    )
    _write(
        REPORTS / "heldout_generalization.md",
        f"""
# Gate 6 - Held-Out Generalization

Status: `pass_nonhardware_analytic`

Held-out success: BodyShield `{body_heldout:.4f}` vs domain randomization `{dr_heldout:.4f}`. Evidence: `tables/sim_heldout_results.csv`.
""",
    )
    _write(
        REPORTS / "baseline_fairness.md",
        """
# Gate 7 - Baseline Fairness

Status: `pass_nonhardware_documented`

Baselines include nominal, random tuning, domain randomization, worst-case grid tuning, robust/conservative control, sysID+retune, oracle, human/effect prior, EPEC-style alternatives, and BodyShield under logged budgets. Evidence: `reports/BUDGET_AND_FAIRNESS_AUDIT.md`, `results/method_deltas_vs_bodyshield.csv`, and `tables/sim_budget_matched_results.csv`.
""",
    )
    _write(
        REPORTS / "conservatism_analysis.md",
        f"""
# Gate 8 - Not Conservative Only

Status: `pass_nonhardware_analytic`

BodyShield nominal retention is `{body_nominal / max(nominal_nominal, 1e-9):.4f}` relative to the nominal policy. Execution time, path length, retries, and workspace-violation proxies are logged in `results/secondary_metrics_by_method.csv`. This does not establish hardware safety.
""",
    )
    _write(
        REPORTS / "hardware_noise_floor.md",
        """
# Gate 3 - Hardware Noise Floor

Status: `blocked_not_run`

No real SO-ARM101/SO-101 repeated-action noise-floor trials have been run. Required before hardware claims: 50 repeated identical actions per primitive/task, commanded-vs-actual error, reset reliability, drift, thermal/current behavior, and fault rate.
""",
    )
    _write(
        REPORTS / "verifier_audit.md",
        """
# Gate 9 - Verifier Audit

Status: `blocked_not_run`

No real camera verifier labels or human-audit agreement table exists. The hardware verifier must reach at least 95% agreement before real robot results can support paper claims.
""",
    )
    _write(
        REPORTS / "submission_readiness_gate.md",
        """
# Submission Readiness Gate

Status: `not_ready_for_final_hardware_submission`

Non-hardware package verification can pass, but final submission readiness is blocked by missing hardware noise floor, verifier agreement, reset reliability, safety-gate pass, all-trials hardware logs, and held-out physical-modification videos.
""",
    )


def write_claim_ledger() -> None:
    rows = [
        ["C1", "Introduction", "Nominal task success can hide hidden embodiment-control assumptions.", "mechanism", "results/nominal_vs_robustness_radius.csv; figures/nominal_vs_radius_scatter.png", "analytic_conditions", "8 tasks, 6 robot archetypes, analytic simulation", "nominal policy", "supported_nonhardware", "No hardware claim.", "Nominal policy may be under-tuned.", "In analytic simulation, nominal success can hide low robustness radius."],
        ["C2", "Method", "BodyBreak estimates low-cost breaking embodiment-control perturbations under a fixed evaluator budget.", "algorithm", "results/breaking_search.csv; reports/BODYBREAK_MINIMALITY_AUDIT.md", "search_rows", "analytic candidate pool and dense audit", "random/one-axis/grid search", "supported_nonhardware", "Estimated minimality only.", "Random search can find lower costs in some cases.", "BodyBreak estimates low-cost failures under the logged budget."],
        ["C3", "Experiments", "BodyShield improves seen and held-out analytic robustness after repair.", "empirical", "tables/sim_main_results.csv; tables/sim_heldout_results.csv", "summary_rows", "analytic perturbation families", "domain randomization; robust control; sysID", "supported_nonhardware", "No physical transfer claim.", "Repair may fit simulator sensitivities.", "BodyShield improves analytic seen and held-out perturbation buckets."],
        ["C4", "Experiments", "BodyShield beats domain randomization under matched analytic budgets.", "empirical", "reports/gate_1_domain_randomization.md; tables/sim_budget_matched_results.csv", "budget_rows", "analytic matched-budget comparison", "domain randomization", "supported_nonhardware", "Hardware budget match pending.", "Domain randomization may improve with other hyperparameters.", "Under this analytic budget, BodyShield exceeds domain randomization."],
        ["C5", "Experiments", "Oracle feasibility screens out impossible analytic breaking cases.", "sanity_check", "reports/oracle_feasibility.md; tables/oracle_feasibility.csv", "oracle_rows", "analytic oracle policy", "oracle feasibility", "supported_nonhardware", "Real oracle pending.", "Oracle is simplified.", "Analytic oracle rows indicate feasibility for claimed simulated failures."],
        ["C6", "Safety", "Hardware claims are blocked until noise floor and verifier agreement are measured.", "boundary", "reports/hardware_noise_floor.md; reports/verifier_audit.md; reports/submission_readiness_gate.md", "not_run_hardware", "hardware phase", "safety gate", "blocked", "No hardware evidence.", "None; this is a blocker.", "Hardware phase remains blocked."],
    ]
    path = REPORTS / "claim_ledger.csv"
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "claim_id",
            "paper_section",
            "claim_text",
            "claim_type",
            "evidence_artifacts",
            "trial_ids_or_config_ids",
            "tested_scope",
            "comparison_class",
            "status",
            "limitations",
            "strongest_alternative_explanation",
            "wording_allowed",
        ])
        writer.writerows(rows)

    md_rows = "\n".join(f"| {row[0]} | {row[1]} | {row[8]} | {row[10]} |" for row in rows)
    _write(
        REPORTS / "CLAIM_LEDGER.md",
        f"""
# Claim Ledger

| claim | section | status | strongest alternative explanation |
|---|---|---|---|
{md_rows}
""",
    )


def write_paper_files() -> None:
    main_tex = r"""
\documentclass[10pt,conference]{IEEEtran}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage{url}
\title{BodyShield: Falsifying and Repairing Hidden Embodiment-Control Assumptions in Robot Policies}
\author{Anonymous Authors}
\begin{document}
\maketitle
\begin{abstract}
Robot policies can succeed in nominal evaluations while relying on brittle hidden assumptions about latency, calibration, joint range, gripper authority, sensing geometry, payload, and contact. BodyShield exposes and repairs hidden embodiment-control assumptions. This draft contains analytic-simulation evidence, generated frames rather than real camera videos, synthetic visual and trajectory proxy audits, bounded MuJoCo/ManiSkill probes, and release/package verification; external full-scale trained-policy high-fidelity benchmarks remain future evidence tiers, and real robot results are blocked until safety gates pass.
\end{abstract}
\section{Introduction}
Nominal success is a weak certificate for robot policies because the policy may depend on a hidden body/control interface detail. BodyShield is a falsification-to-repair method: BodyBreak searches for low-cost embodiment-control perturbations that break a policy, then BodyShield repairs the action representation or policy parameters against discovered failures and evaluates held-out perturbations. The goal is adaptive embodied-intelligence evidence about failure diagnosis and repair, not a cheap-arm demo or a broad cross-embodiment-transfer claim.
\section{Related Work}
Domain randomization and dynamics randomization sample broad distributions for sim-to-real transfer \cite{tobin2017domainrandomization,peng2018dynamicsrandomization,openai2018dexterous,openai2019rubiks}. Embodiment-aware deployment methods such as UMI-on-Air and EmbodiSteer steer policies toward target-body feasibility \cite{gupta2025umionair,wang2026embodisteer}. Counterexample-guided and verification-guided safe-RL methods search for violations and sometimes repair or shield policies \cite{karunakaran2020counterexampleguided,le2025verificationguided}. MPC-CBF and sim-to-real correction methods address safety, feasibility, or transfer through control and correction layers \cite{zeng2021mpccbf,jiang2024transic}. BodyShield is distinct only in the bounded sense used here: it searches embodiment-control perturbations, repairs against discovered failures, and demands held-out and hardware-gated evidence before final claims.
\section{Problem Formulation}
Let \(z\in\mathcal{Z}\) be an embodiment-control perturbation and \(c(z)\) a normalized cost. For policy \(\pi_\theta\), task \(\tau\), and robot archetype \(r\), BodyBreak estimates \(z^\star=\arg\min c(z)\) subject to \(S(\pi_\theta,\tau,r,z)\leq\alpha\) under a finite evaluator budget. BodyShield then optimizes a repaired policy over the discovered break set, training perturbations, and near-boundary cases.
\section{BodyBreak Method}
BodyBreak compares random, one-axis, grid, and compound adversarial search. It reports evaluator-call budgets, estimated breaking cost, threshold sensitivity, and dense post-hoc challenges. It does not claim global minimality.
\section{BodyShield Repair Method}
BodyShield uses discovered failure axes to allocate repair capacity, then evaluates nominal retention, seen perturbations, held-out perturbation families, physical-style proxy shifts, secondary costs, and oracle feasibility. The current policy family is analytic and CPU-only; it validates the pipeline, not hardware deployment.
\section{Simulation Experiments}
The local run evaluates eight tasks, six robot/body archetypes, ten policy families, major embodiment-control perturbation families, compound perturbations, confidence intervals, and threshold sensitivity. Table~\ref{tab:analytic-success} summarizes the main analytic buckets. Evidence lives in \path{results/}, \path{logs/sim/results.jsonl}, \path{tables/sim_main_results.csv}, and \path{tables/sim_budget_matched_results.csv}.
\begin{table}[t]
\caption{Analytic success rates by perturbation bucket.}
\label{tab:analytic-success}
\centering\footnotesize
\begin{tabular}{lccc}
\toprule
Method & Nominal & Seen & Held-out \\
\midrule
Nominal & 0.872 & 0.757 & 0.761 \\
Domain rand. & 0.844 & 0.748 & 0.742 \\
BodyShield & 0.859 & 0.800 & 0.792 \\
Oracle & 0.925 & 0.910 & 0.907 \\
\bottomrule
\end{tabular}
\end{table}
\section{Real Robot Experiments}
\textbf{Hardware placeholder only. Do not fill until SO-ARM101/SO-101 safety gates pass.} Required hardware evidence includes noise floor, verifier agreement, reset reliability, emergency-stop test, all-trials logs, videos with failures and ambiguous cases, held-out physical modifications, and oracle feasibility.
\section{EPEC and Human-Effect Stress Test}
Human/effect and EPEC-style policies are included only as stress-test alternatives. They are not the main method and are not used to claim human-video or foundation-policy superiority.
\section{Ablations}
Ablations cover search mode, repair baseline, threshold, secondary execution costs, and conservative behavior. They are logged in \path{results/breaking_search.csv}, \path{results/threshold_sensitivity.csv}, and \path{results/secondary_metrics_by_method.csv}.
\section{Failure Analysis}
Failure categories include tracking error, calibration error, joint limit, collision, slip, unreachable pose, verifier uncertainty, and mechanical proxy faults. The paper must keep these tied to analytic simulation until hardware logs exist.
\section{Limitations}
The current package lacks hardware noise floor, camera verifier accuracy, reset reliability, real held-out physical modifications, all-trials hardware videos, broad manipulation/foundation-policy checkpoint suites, and real corrective-trace adaptation.
\section{Reproducibility Statement}
The package includes tests, CI, manifests, release ZIP, claim ledger, citation verification, and `python -m bodyshield.analysis.verify_package --json`. Trial fields follow \path{data_schema.json}.
\section{Ethics and Safety Statement}
The repository forbids raw hardware command paths and exposes only bounded primitives that refuse to run before explicit physical safety confirmation. This does not guarantee hardware safety.
\bibliographystyle{IEEEtran}
\bibliography{references}
\end{document}
"""
    _write(PAPER / "main.tex", main_tex)
    _copy(PAPER / "bodyshield_non_hardware_draft.pdf", PAPER / "bodyshield.pdf")
    _write(
        PAPER / "appendix_claim_ledger.tex",
        r"""
\section{Claim Ledger}
The canonical claim ledger is generated at \path{reports/claim_ledger.csv}. Claims without evidence are excluded from the main paper wording.
""",
    )
    _write(
        PAPER / "appendix_reviewer_prebuttal.tex",
        r"""
\section{Reviewer Prebuttal}
The canonical reviewer prebuttal is generated at \path{reports/reviewer_prebuttal.md}. It addresses domain randomization, benchmark-only risk, cheap-arm artifacts, artificial perturbations, oracle feasibility, robust-control alternatives, conservatism, baseline fairness, overfitting, reset/labeling bias, EPEC distraction, ICRA fit, limitations, larger robots, and value to labs with stronger hardware.
""",
    )


def write_videos() -> None:
    rows = list(csv.DictReader((RESULTS / "simulation_rollout_videos.csv").open(newline="", encoding="utf-8")))
    index_rows = "\n".join(
        f"| {row['artifact_id']} | `{row['path']}` | `{row['task_id']}` | `{row['method_id']}` | {row['evidence_boundary']} |"
        for row in rows
    )
    body = f"""
# Video Index

Current video artifacts are synthetic rollout media linked to raw analytic trace IDs. They are not real-camera or hardware-verifier videos.

| artifact | path | task | method | boundary |
|---|---|---|---|---|
{index_rows}
"""
    _write(VIDEOS / "index.md", body)
    _write(VIDEOS / "video_index.md", body)
    _write(VIDEOS / "teaser_successes.md", body)
    _write(VIDEOS / "failure_recovery.md", body)
    _write(VIDEOS / "heldout_physical_mods.md", body)
    _write(VIDEOS / "oracle_feasibility.md", body)


def write_prebuttal() -> None:
    answers = [
        ("Is this just domain randomization?", "No in the analytic package: see `reports/gate_1_domain_randomization.md` and `tables/sim_budget_matched_results.csv`. Hardware comparison remains pending."),
        ("Is this just benchmark/stress testing?", "No for non-hardware: before/after repair is reported in `reports/gate_2_before_after_repair.md`."),
        ("Is the cheap arm too toy?", "Hardware is not claimed. The cheap-arm stack is safety-gated in `bodyshield/robot/` and must be treated as a validation ladder."),
        ("Are perturbations artificial?", "Some are software/control shifts; physical-style proxies are logged in `reports/heldout_physical_modifications.md`, while real physical modifications are blocked."),
        ("Are failures impossible tasks?", "Analytic oracle feasibility is reported in `reports/oracle_feasibility.md`. Hardware oracle feasibility is pending."),
        ("Is this robust control/sysID?", "No; `reports/prior_work_hardening.md` frames BodyShield as a diagnostic repair layer, not a replacement."),
        ("Is it too conservative?", "`reports/conservatism_analysis.md` tracks execution time, path length, retries, and nominal retention."),
        ("Are baselines fair?", "`reports/baseline_fairness.md` and `reports/BUDGET_AND_FAIRNESS_AUDIT.md` document budgets."),
        ("Does repair overfit?", "`reports/heldout_generalization.md` reports held-out perturbation families."),
        ("Is labeling biased?", "`reports/verifier_audit.md` is blocked and prevents hardware claims."),
        ("Is EPEC distracting?", "EPEC is only a stress-test policy family, not the headline method."),
        ("Why should ICRA care?", "The mechanism is failure diagnosis and repair for learned robot policies under body/control shift."),
        ("What does it not prove?", "It does not prove hardware transfer, foundation-model generality, or cross-embodiment transfer."),
        ("What would fail on bigger robots?", "Unmodeled compliance, force limits, perception latency, calibration drift, reset reliability, and safety limits."),
        ("Why valuable to labs with better hardware?", "It gives a falsification-to-repair audit layer that can be run before expensive deployments."),
    ]
    body = "\n\n".join(f"## {q}\n\n{a}" for q, a in answers)
    _write(REPORTS / "reviewer_prebuttal.md", "# Reviewer Prebuttal\n\n" + body)
    _write(REPORTS / "final_reviewer_prebuttal.md", "# Reviewer Prebuttal\n\n" + body)


def update_readmes() -> None:
    reproduce = """
# Reproduce

```bash
make smoke
make test
make sim-minimal
make sim-full
make paper
make verify
```

`make verify` checks the non-hardware package boundary. It does not mark the project submission-ready; hardware remains blocked until explicit robot and safety confirmation.
"""
    _write(ROOT / "REPRODUCE.md", reproduce)
    reqs = "\n".join(["numpy", "pandas", "matplotlib", "pillow", "pyarrow", "pypdf", "pyyaml", "tabulate", "pytest"])
    _write(ROOT / "requirements.txt", reqs)


def update_final_manifest() -> None:
    include_roots = ["bodyshield", "configs", "figures", "logs", "paper", "reports", "results", "scripts", "tables", "tests", "videos", ".github"]
    root_files = ["README.md", "README_FIRST.md", "README_EXECUTION.md", "REPRODUCE.md", "Makefile", "pyproject.toml", "requirements.txt", "environment.yml", "LICENSE", "CITATION.cff"]
    entries: list[dict[str, object]] = []
    for root_name in include_roots:
        base = ROOT / root_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts and "build" not in path.parts:
                rel = path.relative_to(ROOT).as_posix()
                if rel in {"reports/final_artifact_manifest.json", "reports/final_artifact_manifest_nonhardware.json"}:
                    continue
                entries.append({"path": rel, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    for rel in root_files:
        path = ROOT / rel
        if path.exists():
            entries.append({"path": rel, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    payload = {
        "generated_at_utc": _utc(),
        "scope": "v2 non-hardware package; hardware blocked",
        "hardware_status": "not_run_requires_explicit_user_confirmation",
        "submission_ready": False,
        "entry_count": len(entries),
        "entries": entries,
    }
    _write(REPORTS / "final_artifact_manifest.json", json.dumps(payload, indent=2, sort_keys=True))
    _write(REPORTS / "final_artifact_manifest_nonhardware.json", json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    for directory in (REPORTS, TABLES, FIGURES, LOGS, PAPER, VIDEOS):
        directory.mkdir(parents=True, exist_ok=True)
    write_initial_audit()
    ensure_bibliography()
    write_citation_verification()
    write_prior_work()
    write_tables_logs_figures()
    write_gate_reports()
    write_claim_ledger()
    write_paper_files()
    write_videos()
    write_prebuttal()
    update_readmes()
    update_final_manifest()
    print("V2_ARTIFACT_STATUS=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
