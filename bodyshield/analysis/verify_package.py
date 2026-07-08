"""Verify the v2 BodyShield package boundary and evidence ledger."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from bodyshield.analysis.claim_ledger import REQUIRED_COLUMNS, validate_claim_ledger


ROOT = Path(__file__).resolve().parents[2]

NONHARDWARE_REQUIRED = (
    "reports/initial_repo_audit.md",
    "reports/prior_work_hardening.md",
    "reports/citation_verification.md",
    "reports/claim_ledger.csv",
    "reports/final_artifact_manifest.json",
    "reports/gate_1_domain_randomization.md",
    "reports/gate_2_before_after_repair.md",
    "reports/oracle_feasibility.md",
    "reports/heldout_physical_modifications.md",
    "reports/heldout_generalization.md",
    "reports/baseline_fairness.md",
    "reports/conservatism_analysis.md",
    "reports/verifier_audit.md",
    "paper/main.tex",
    "paper/bodyshield.pdf",
    "paper/references.bib",
    "paper/supplement.tex",
    "paper/supplement.pdf",
    "paper/appendix_claim_ledger.tex",
    "paper/appendix_reviewer_prebuttal.tex",
    "logs/sim/results.jsonl",
    "logs/sim/results_flat.csv",
    "tables/sim_main_results.csv",
    "tables/sim_budget_matched_results.csv",
    "tables/sim_heldout_results.csv",
    "figures/bodyshield_before_after.png",
    "videos/index.md",
)

HARDWARE_REQUIRED = (
    "reports/hardware_noise_floor.md",
    "reports/verifier_audit.md",
    "reports/HARDWARE_COMPLETE.md",
    "reports/SUBMISSION_READY_AUDIT.md",
)

FORBIDDEN_HARDWARE_CLAIMS = (
    "hardware results show",
    "real robot experiments demonstrate",
    "camera verifier achieved",
    "noise floor measured",
    "submission ready",
)

RAW_MOTOR_TOKENS = (
    "serial.Serial(",
    "write_goal_position(",
    "set_servo_angle(",
    "movej(",
    "movel(",
    "raw torque",
    "raw joint velocity",
)


def _exists_nonempty(root: Path, rel_path: str) -> bool:
    path = root / rel_path
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _bib_keys(text: str) -> set[str]:
    import re

    return set(re.findall(r"@\w+\{\s*([^,\s]+)", text))


def _citation_rows(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [line for line in text.splitlines() if line.startswith("|") and "Verified" in line]
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 6:
            rows.append({"key": cells[0], "status": cells[4]})
    return rows


def _raw_motor_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in (root / "bodyshield" / "robot").glob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in RAW_MOTOR_TOKENS:
            if token in text:
                hits.append(f"{path.relative_to(root).as_posix()}:{token}")
    return hits


def _paper_overclaim_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for rel_path in ("paper/main.tex", "reports/final_submission_readiness_report.md", "reports/submission_readiness_gate.md"):
        path = root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for phrase in FORBIDDEN_HARDWARE_CLAIMS:
            if phrase in text and "not_" not in text and "not ready" not in text:
                hits.append(f"{rel_path}:{phrase}")
    return hits


def verify(root: Path = ROOT, require_submission_ready: bool = False) -> dict[str, object]:
    problems: list[str] = []
    for rel_path in NONHARDWARE_REQUIRED:
        if not _exists_nonempty(root, rel_path):
            problems.append(f"missing_or_empty:{rel_path}")

    problems.extend(f"claim_ledger:{item}" for item in validate_claim_ledger(root / "reports" / "claim_ledger.csv"))

    bib = root / "paper" / "references.bib"
    citation_audit = root / "reports" / "citation_verification.md"
    if bib.exists() and citation_audit.exists():
        keys = _bib_keys(bib.read_text(encoding="utf-8", errors="ignore"))
        required = {
            "tobin2017domainrandomization",
            "peng2018dynamicsrandomization",
            "openai2018dexterous",
            "gupta2025umionair",
            "wang2026embodisteer",
            "le2025verificationguided",
            "zeng2021mpccbf",
            "jiang2024transic",
        }
        missing_keys = sorted(required - keys)
        if missing_keys:
            problems.append(f"bib_missing_required:{missing_keys}")
        if "unverified" in citation_audit.read_text(encoding="utf-8", errors="ignore").lower():
            problems.append("citation_audit_contains_unverified")
    else:
        problems.append("missing bibliography or citation audit")

    problems.extend(f"raw_motor_path:{hit}" for hit in _raw_motor_hits(root))
    problems.extend(f"overclaim:{hit}" for hit in _paper_overclaim_hits(root))

    readiness = (root / "reports" / "submission_readiness_gate.md").read_text(encoding="utf-8", errors="ignore").lower()
    hardware_blocked = "not_ready_for_final_hardware_submission" in readiness or "blocked" in readiness
    if require_submission_ready:
        for rel_path in HARDWARE_REQUIRED:
            if not _exists_nonempty(root, rel_path):
                problems.append(f"missing_submission_artifact:{rel_path}")
        if hardware_blocked:
            problems.append("hardware gates are blocked; final submission readiness is false")

    return {
        "status": "pass" if not problems else "fail",
        "phase": "submission" if require_submission_ready else "nonhardware",
        "submission_ready": bool(require_submission_ready and not problems),
        "hardware_blocked": hardware_blocked,
        "required_columns": list(REQUIRED_COLUMNS),
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--require-submission-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = verify(args.root.resolve(), require_submission_ready=args.require_submission_ready)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"PACKAGE_VERIFY_STATUS={payload['status']}")
        print(f"PHASE={payload['phase']}")
        print(f"HARDWARE_BLOCKED={payload['hardware_blocked']}")
        for problem in payload["problems"]:
            print(f"FAIL={problem}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

