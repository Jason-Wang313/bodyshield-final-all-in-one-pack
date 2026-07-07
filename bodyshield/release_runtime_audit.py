"""Runtime smoke audit for an extracted release archive."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

from bodyshield.release_bundle import BUNDLE_NAME, MANIFEST_NAME


PYTEST_SUMMARY_RE = re.compile(r"(?P<count>\d+)\s+passed\b")


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


def _safe_extract(bundle: zipfile.ZipFile, destination: Path) -> list[str]:
    names = bundle.namelist()
    destination_resolved = destination.resolve()
    for name in names:
        normalized = name.replace("\\", "/")
        if not normalized or normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
            raise ValueError(f"unsafe zip path: {name}")
        target = (destination / normalized).resolve()
        if destination_resolved != target and destination_resolved not in target.parents:
            raise ValueError(f"zip path escapes destination: {name}")
    bundle.extractall(destination)
    return names


def _pytest_rows(extracted_root: Path, timeout_s: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    tests_dir = extracted_root / "tests"
    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
    rows.append(
        _row(
            "tests",
            "extracted_tests_present",
            "pass" if test_files else "fail",
            "extracted release contains pytest tests",
            str(len(test_files)),
            ">0",
        )
    )
    if not test_files:
        return rows
    command = [sys.executable, "-m", "pytest", "-q", "--tb=short", "--disable-warnings", "tests"]
    try:
        completed = subprocess.run(
            command,
            cwd=extracted_root,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return rows + [_fail("tests", "extracted_pytest_returncode", f"pytest timed out after {timeout_s}s", "timeout", "returncode=0")]
    output = (completed.stdout + "\n" + completed.stderr).strip()
    summary_match = PYTEST_SUMMARY_RE.search(output)
    passed_count = int(summary_match.group("count")) if summary_match else 0
    rows.append(
        _row(
            "tests",
            "extracted_pytest_returncode",
            "pass" if completed.returncode == 0 else "fail",
            "pytest exits successfully inside extracted release",
            f"returncode={completed.returncode}",
            "returncode=0",
        )
    )
    rows.append(
        _row(
            "tests",
            "extracted_pytest_passed_count",
            "pass" if completed.returncode == 0 and passed_count > 0 else "fail",
            "pytest output reports passing tests",
            str(passed_count),
            ">0",
        )
    )
    if completed.returncode != 0:
        rows.append(_fail("tests", "extracted_pytest_output", output[-1000:] or "no output"))
    return rows


def run_release_runtime_audit(root: Path | str = ".", timeout_s: int = 240) -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    zip_path = root_path / "release" / BUNDLE_NAME

    if not zip_path.exists():
        manifest_path = root_path / MANIFEST_NAME
        rows.append(
            _row(
                MANIFEST_NAME,
                "extracted_manifest_exists_nonempty",
                "pass" if manifest_path.exists() and manifest_path.stat().st_size > 0 else "fail",
                "root looks like an extracted release payload",
                str(manifest_path.exists()),
                "True",
            )
        )
        if manifest_path.exists():
            rows.extend(_pytest_rows(root_path, timeout_s))
        return pd.DataFrame(rows)

    rel_zip = f"release/{BUNDLE_NAME}"
    rows.append(
        _row(
            rel_zip,
            "release_zip_exists_nonempty",
            "pass" if zip_path.stat().st_size > 0 else "fail",
            "release ZIP exists and is nonempty",
            str(zip_path.stat().st_size if zip_path.exists() else 0),
            ">0 bytes",
        )
    )
    try:
        with tempfile.TemporaryDirectory(prefix="bodyshield_release_runtime_") as tmp:
            extracted = Path(tmp)
            with zipfile.ZipFile(zip_path) as bundle:
                names = _safe_extract(bundle, extracted)
            rows.append(_pass(rel_zip, "zip_extracts_safely", "release ZIP entries extract without unsafe paths", str(len(names)), ">0 entries"))
            rows.extend(_pytest_rows(extracted, timeout_s))
    except Exception as exc:  # pragma: no cover - defensive reporting path
        rows.append(_fail(rel_zip, "zip_extracts_safely", f"release ZIP could not be safely extracted: {exc}"))
        return pd.DataFrame(rows)
    rows.append(_pass("tmp", "temporary_runtime_extraction_cleaned", "temporary runtime extraction directory removed"))
    return pd.DataFrame(rows)


def release_runtime_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_release_runtime_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_release_runtime_audit_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = release_runtime_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_release_runtime_rows(rows)
    display = failures if not failures.empty else rows.head(80)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Release Runtime Audit

Status: `{status}`

This audit safely extracts the portable release ZIP and runs the bundled pytest suite from inside the extracted archive. It verifies that the release is not only checksum-valid and byte-reproducible, but also executable as a standalone local test payload.

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


def write_release_runtime_audit_reports(root: Path | str = ".", timeout_s: int = 240) -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_release_runtime_audit(root_path, timeout_s=timeout_s)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "release_runtime_audit.csv", index=False)
    write_release_runtime_audit_report(reports / "RELEASE_RUNTIME_AUDIT.md", rows)
    return rows
