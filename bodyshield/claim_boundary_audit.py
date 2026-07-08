"""Claim-boundary audit for the local non-hardware BodyShield pack."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


@dataclass(frozen=True)
class DocumentRequirement:
    path: str
    required_phrases: tuple[str, ...]


@dataclass(frozen=True)
class CsvBoundaryRequirement:
    path: str
    status_column: str
    required_statuses: tuple[str, ...]
    boundary_column: str
    required_boundary_phrases: tuple[str, ...]


DOCUMENT_REQUIREMENTS: tuple[DocumentRequirement, ...] = (
    DocumentRequirement(
        "reports/CLAIM_BOUNDARY.md",
        (
            "software and analytic-simulation claim only",
            "No real SO-ARM101/SO-101 hardware result has been run",
            "One public pretrained MuJoCo checkpoint benchmark has been run",
            "No broad external/full-scale robot-policy MuJoCo/ManiSkill benchmark suite has been run",
            "No real-camera or foundation-scale WAM training has been run",
            "No real/external corrective-trace adaptation has been run",
        ),
    ),
    DocumentRequirement(
        "reports/CLAIM_LEDGER.md",
        (
            "do not claim physical transfer",
            "Do not present as real-video",
            "one public pretrained MuJoCo checkpoint benchmark",
            "Do not present as broad external/full-scale trained-policy MuJoCo/ManiSkill suite evidence",
            "does not replace external archival upload",
        ),
    ),
    DocumentRequirement(
        "reports/SIMULATION_SUMMARY.md",
        (
            "must not be presented as real robot or high-fidelity physics evidence",
            "not broad external/full-scale MuJoCo or ManiSkill suite evidence",
            "not real-video or foundation-scale WAM evidence",
            "not real corrective-trace adaptation evidence",
        ),
    ),
    DocumentRequirement(
        "reports/RELEASE_BUNDLE.md",
        (
            "does not prove an external archival upload",
            "public pretrained MuJoCo checkpoint benchmark",
            "real-video WAM training",
            "real corrective-trace adaptation",
            "hardware transfer",
        ),
    ),
    DocumentRequirement(
        "reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md",
        (
            "not external/full-scale MuJoCo or ManiSkill trained-policy evidence",
            "example ManiSkill checkpoint is not present",
            "public SB3/RL-Zoo HalfCheetah checkpoint benchmark is complete",
        ),
    ),
    DocumentRequirement(
        "reports/REAL_VIDEO_WAM_READINESS.md",
        (
            "not real-video WAM evidence",
            "no real camera dataset is present",
            "no real-video or foundation-scale WAM claim is supported",
        ),
    ),
    DocumentRequirement(
        "reports/CORRECTIVE_TRACE_READINESS.md",
        (
            "not real corrective-trace adaptation",
            "no real/external corrective trace dataset is present",
            "no real corrective-trace adaptation claim is supported",
        ),
    ),
    DocumentRequirement(
        "paper/main.tex",
        (
            "one public SB3/RL-Zoo HalfCheetah checkpoint rollout",
            "generated frames rather than real camera videos",
            "broader trained-policy suites, manipulation/foundation-policy checkpoints, real robot results, real-video WAM training, and real corrective adaptation remain future evidence tiers",
            "none establishes physical transfer",
        ),
    ),
    DocumentRequirement(
        "README_EXECUTION.md",
        (
            "This pack stops before hardware",
            "safety gate",
            "camera verifier",
            "emergency stop",
        ),
    ),
)


PDF_REQUIREMENTS: tuple[DocumentRequirement, ...] = (
    DocumentRequirement(
        "paper/bodyshield_non_hardware_draft.pdf",
        (
            "real robot results",
            "generated frames",
            "real camera",
            "public SB3/RL-Zoo HalfCheetah checkpoint",
            "none establishes physical transfer",
        ),
    ),
)


CSV_BOUNDARY_REQUIREMENTS: tuple[CsvBoundaryRequirement, ...] = (
    CsvBoundaryRequirement(
        "results/external_policy_benchmark_readiness.csv",
        "status",
        ("fixture_smoke_passed", "missing_checkpoint"),
        "evidence_boundary",
        ("not external checkpoint evidence", "No example ManiSkill trained-policy evidence was generated"),
    ),
    CsvBoundaryRequirement(
        "results/real_video_wam_readiness.csv",
        "status",
        ("fixture_training_smoke_passed", "missing_dataset"),
        "evidence_boundary",
        ("not real camera video", "No real-video WAM evidence was generated"),
    ),
    CsvBoundaryRequirement(
        "results/corrective_trace_readiness.csv",
        "status",
        ("fixture_fit_smoke_passed", "missing_dataset"),
        "evidence_boundary",
        ("not real robot", "No real corrective-trace evidence was generated"),
    ),
    CsvBoundaryRequirement(
        "results/simulation_rollout_videos.csv",
        "artifact_id",
        ("nominal_reference", "bodybreak_failure", "bodyshield_repair"),
        "evidence_boundary",
        ("Synthetic generated rollout only", "not real video", "not real video, camera verification, hardware"),
    ),
)


FORBIDDEN_CLAIM_PHRASES: tuple[str, ...] = (
    "hardware validation complete",
    "hardware results complete",
    "real robot validation complete",
    "real robot results complete",
    "generated real-video WAM evidence",
    "generated external trained-policy benchmark evidence",
    "generated real corrective-trace adaptation evidence",
    "external archival upload complete",
    "public repository release complete",
    "physical transfer is established",
    "deployed robot policy evidence",
)


TEXT_SCAN_ROOTS: tuple[str, ...] = ("paper", "reports", "README_EXECUTION.md")
TEXT_SKIP_SUFFIXES = {".pdf", ".png", ".gif", ".zip", ".parquet"}
TEXT_SKIP_PARTS = {"tmp", "__pycache__", ".pytest_cache"}


def _row(artifact: str, check: str, status: str, detail: str, observed: str = "", expected: str = "") -> dict[str, str]:
    return {
        "artifact": artifact,
        "check": check,
        "status": status,
        "detail": detail,
        "observed": observed,
        "expected": expected,
    }


def _pass(artifact: str, check: str, detail: str, observed: str = "", expected: str = "") -> dict[str, str]:
    return _row(artifact, check, "pass", detail, observed, expected)


def _fail(artifact: str, check: str, detail: str, observed: str = "", expected: str = "") -> dict[str, str]:
    return _row(artifact, check, "fail", detail, observed, expected)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _contains(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def _text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in TEXT_SCAN_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else list(base.rglob("*"))
        for path in candidates:
            if not path.is_file():
                continue
            if any(part in TEXT_SKIP_PARTS for part in path.parts):
                continue
            if path.suffix.lower() in TEXT_SKIP_SUFFIXES:
                continue
            files.append(path)
    return sorted(files)


def _document_rows(root: Path, requirements: tuple[DocumentRequirement, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in requirements:
        path = root / spec.path
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(spec.path, "document_exists_nonempty", "required claim-boundary document is missing or empty"))
            continue
        text = _read_text(path)
        rows.append(_pass(spec.path, "document_exists_nonempty", "document exists and is nonempty", str(path.stat().st_size), ">0 bytes"))
        for phrase in spec.required_phrases:
            if _contains(text, phrase):
                rows.append(_pass(spec.path, "required_boundary_phrase", "required boundary phrase present", phrase))
            else:
                rows.append(_fail(spec.path, "required_boundary_phrase", "required boundary phrase missing", "", phrase))
    return rows


def _pdf_rows(root: Path, requirements: tuple[DocumentRequirement, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in requirements:
        path = root / spec.path
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(spec.path, "pdf_exists_nonempty", "required PDF is missing or empty"))
            continue
        try:
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # pragma: no cover - defensive reporting path
            rows.append(_fail(spec.path, "pdf_extract_text", f"could not extract PDF text: {exc}"))
            continue
        rows.append(_pass(spec.path, "pdf_extract_text", "PDF text extracted", f"{len(reader.pages)} pages"))
        for phrase in spec.required_phrases:
            if _contains(text, phrase):
                rows.append(_pass(spec.path, "required_pdf_boundary_phrase", "required PDF boundary phrase present", phrase))
            else:
                rows.append(_fail(spec.path, "required_pdf_boundary_phrase", "required PDF boundary phrase missing", "", phrase))
    return rows


def _csv_rows(root: Path, requirements: tuple[CsvBoundaryRequirement, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in requirements:
        path = root / spec.path
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(spec.path, "csv_exists_nonempty", "required boundary CSV is missing or empty"))
            continue
        try:
            records = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
        except Exception as exc:  # pragma: no cover - defensive reporting path
            rows.append(_fail(spec.path, "csv_parse", f"could not parse CSV: {exc}"))
            continue
        if not records:
            rows.append(_fail(spec.path, "csv_nonempty_rows", "CSV has no rows"))
            continue
        statuses = {str(row.get(spec.status_column, "")) for row in records}
        missing_statuses = sorted(set(spec.required_statuses) - statuses)
        rows.append(
            _row(
                spec.path,
                "required_statuses",
                "pass" if not missing_statuses else "fail",
                "required status/artifact values present",
                ",".join(sorted(statuses)),
                ",".join(spec.required_statuses),
            )
        )
        boundaries = "\n".join(str(row.get(spec.boundary_column, "")) for row in records)
        for phrase in spec.required_boundary_phrases:
            rows.append(
                _row(
                    spec.path,
                    "required_boundary_phrase",
                    "pass" if _contains(boundaries, phrase) else "fail",
                    "required CSV boundary phrase present",
                    phrase if _contains(boundaries, phrase) else "",
                    phrase,
                )
            )
    return rows


def _forbidden_phrase_rows(root: Path, forbidden_phrases: tuple[str, ...]) -> list[dict[str, str]]:
    hits: list[str] = []
    for path in _text_files(root):
        text = _read_text(path)
        for phrase in forbidden_phrases:
            if _contains(text, phrase):
                hits.append(f"{path.relative_to(root).as_posix()}::{phrase}")
    if hits:
        return [_fail("text_claim_scan", "forbidden_overclaim_phrases", "unsupported overclaim phrase found", "; ".join(hits[:20]))]
    return [_pass("text_claim_scan", "forbidden_overclaim_phrases", "no unsupported overclaim phrases found", str(len(_text_files(root))))]


def run_claim_boundary_audit(
    root: Path | str = ".",
    document_requirements: tuple[DocumentRequirement, ...] = DOCUMENT_REQUIREMENTS,
    csv_requirements: tuple[CsvBoundaryRequirement, ...] = CSV_BOUNDARY_REQUIREMENTS,
    pdf_requirements: tuple[DocumentRequirement, ...] = PDF_REQUIREMENTS,
    forbidden_phrases: tuple[str, ...] = FORBIDDEN_CLAIM_PHRASES,
) -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    rows.extend(_document_rows(root_path, document_requirements))
    rows.extend(_pdf_rows(root_path, pdf_requirements))
    rows.extend(_csv_rows(root_path, csv_requirements))
    rows.extend(_forbidden_phrase_rows(root_path, forbidden_phrases))
    return pd.DataFrame(rows)


def claim_boundary_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_claim_boundary_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_claim_boundary_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = claim_boundary_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_claim_boundary_rows(rows)
    display = failures if not failures.empty else rows.head(100)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Claim Boundary Audit

Status: `{status}`

This audit checks that the local non-hardware pack preserves the evidence boundary between analytic/synthetic/local-simulator results and missing hardware, external trained-policy, real-video WAM, real corrective-trace, and external archival evidence.

| metric | value |
|---|---:|
| checks | {summary['checks']} |
| passed | {summary['passed']} |
| failed | {summary['failed']} |
| artifacts audited | {summary['artifacts']} |

## Display Rows

{body}
""",
        encoding="utf-8",
    )


def write_claim_boundary_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_claim_boundary_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "claim_boundary_audit.csv", index=False)
    write_claim_boundary_report(reports / "CLAIM_BOUNDARY_AUDIT.md", rows)
    return rows
