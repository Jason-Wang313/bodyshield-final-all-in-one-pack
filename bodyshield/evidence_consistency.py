"""Audit report claims against local evidence artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd


AUDITED_DOCS: tuple[str, ...] = (
    "README_EXECUTION.md",
    "reports/CLAIM_LEDGER.md",
    "reports/NON_HARDWARE_REQUIREMENTS_TRACE.md",
    "reports/REPRODUCIBILITY_MANIFEST.md",
    "reports/NON_HARDWARE_COMPLETE.md",
    "reports/SIMULATION_SUMMARY.md",
    "reports/RELEASE_BUNDLE.md",
)

PATH_ROOTS = (
    "bodyshield",
    "configs",
    "paper",
    "release",
    "reports",
    "results",
    "scripts",
    "tests",
)
ROOT_FILES = {
    "README_EXECUTION.md",
    "README_FIRST.md",
    "data_schema.json",
    "pyproject.toml",
    "tasks.yaml",
    "trial_schema.schema.json",
}
COMMAND_PREFIXES = ("python ", "pip ", "uv ", "pytest ", "pdftoppm ", "pdfinfo ")
PATH_TOKEN_RE = re.compile(
    r"(?:(?:bodyshield|configs|paper|release|reports|results|scripts|tests)[/\\][A-Za-z0-9_./\\*\-]+|"
    r"(?:README_EXECUTION\.md|README_FIRST\.md|data_schema\.json|pyproject\.toml|tasks\.yaml|trial_schema\.schema\.json))"
)
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")


def _normalise_reference(raw: str) -> str:
    return raw.strip().strip(".,;:()[]{}").replace("\\", "/")


def _looks_like_local_path(reference: str) -> bool:
    if not reference or reference.startswith(("http://", "https://")):
        return False
    lowered = reference.lower()
    if any(lowered.startswith(prefix) for prefix in COMMAND_PREFIXES):
        return False
    if " " in reference:
        return False
    if reference in ROOT_FILES:
        return True
    first = reference.split("/", 1)[0]
    return first in PATH_ROOTS


def extract_local_references(text: str) -> list[str]:
    references: list[str] = []
    for match in CODE_SPAN_RE.finditer(text):
        reference = _normalise_reference(match.group(1))
        if _looks_like_local_path(reference):
            references.append(reference)
    for match in PATH_TOKEN_RE.finditer(text):
        reference = _normalise_reference(match.group(0))
        if _looks_like_local_path(reference):
            references.append(reference)
    seen: set[str] = set()
    out: list[str] = []
    for reference in references:
        if reference in seen:
            continue
        seen.add(reference)
        out.append(reference)
    return out


def _check_reference(root: Path, reference: str) -> tuple[str, str, int]:
    if "*" in reference:
        matches = sorted(path for path in root.glob(reference) if path.exists())
        if not matches:
            return "missing", "glob matched 0 files", 0
        files = [path for path in matches if path.is_file()]
        if not files:
            return "missing", "glob matched no files", 0
        return "ok", f"glob matched {len(files)} file(s)", len(files)
    path = root / reference
    if path.exists() and path.is_file() and path.stat().st_size > 0:
        return "ok", "file exists and is nonempty", 1
    if path.exists() and path.is_dir():
        return "ok", "directory exists", 1
    return "missing", "path missing or empty", 0


def run_evidence_consistency_audit(root: Path | str = ".") -> pd.DataFrame:
    root = Path(root).resolve()
    rows: list[dict[str, object]] = []
    for doc_rel in AUDITED_DOCS:
        doc_path = root / doc_rel
        if not doc_path.exists():
            rows.append(
                {
                    "document": doc_rel,
                    "reference": doc_rel,
                    "status": "missing_document",
                    "detail": "audited document is missing",
                    "matches": 0,
                }
            )
            continue
        text = doc_path.read_text(encoding="utf-8", errors="ignore")
        references = extract_local_references(text)
        if not references:
            rows.append(
                {
                    "document": doc_rel,
                    "reference": "",
                    "status": "no_references_found",
                    "detail": "no local evidence references extracted",
                    "matches": 0,
                }
            )
            continue
        for reference in references:
            status, detail, matches = _check_reference(root, reference)
            rows.append(
                {
                    "document": doc_rel,
                    "reference": reference,
                    "status": status,
                    "detail": detail,
                    "matches": matches,
                }
            )
    return pd.DataFrame(rows)


def evidence_consistency_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"rows": 0, "ok": 0, "missing": 0, "documents": 0}
    statuses = rows["status"].astype(str)
    return {
        "rows": int(len(rows)),
        "ok": int((statuses == "ok").sum()),
        "missing": int((statuses != "ok").sum()),
        "documents": int(rows["document"].nunique()),
    }


def _markdown_table(rows: pd.DataFrame) -> str:
    display = rows.copy()
    if len(display) > 80:
        missing = display[display["status"] != "ok"]
        ok = display[display["status"] == "ok"].head(max(0, 80 - len(missing)))
        display = pd.concat([missing, ok], ignore_index=True)
    return display.to_markdown(index=False)


def write_evidence_consistency_reports(root: Path | str = ".") -> pd.DataFrame:
    root = Path(root).resolve()
    results = root / "results"
    reports = root / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows = run_evidence_consistency_audit(root)
    rows.to_csv(results / "evidence_consistency_audit.csv", index=False)
    summary = evidence_consistency_summary(rows)
    status = "pass" if summary["missing"] == 0 and summary["rows"] > 0 else "fail"
    (reports / "EVIDENCE_CONSISTENCY_AUDIT.md").write_text(
        f"""# Evidence Consistency Audit

Status: `{status}`

This audit scans the main claim, trace, reproducibility, completion, simulation-summary, README, and release-bundle documents for local evidence references, then verifies that each referenced file or glob exists in the pack.

| metric | value |
|---|---:|
| audited documents | {summary['documents']} |
| references checked | {summary['rows']} |
| passing references | {summary['ok']} |
| missing references | {summary['missing']} |

## Checked References

{_markdown_table(rows)}
""",
        encoding="utf-8",
    )
    return rows


def failed_references(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "ok"].copy()
