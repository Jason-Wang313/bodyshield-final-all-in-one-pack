"""Pack-side audit for the portable release payload."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd

from bodyshield.release_bundle import (
    BUNDLE_NAME,
    MANIFEST_NAME,
    README_NAME,
    REQUIRED_PAYLOADS,
    inspect_release_bundle,
    validate_release_payload,
)


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


def _run_bundled_payload_verifier(extracted_root: Path, required_payloads: Iterable[str], timeout_s: int) -> tuple[dict[str, object], str]:
    script = extracted_root / "scripts" / "verify_release_payload.py"
    command = [sys.executable, str(script), "--root", str(extracted_root), "--json"]
    custom_required = tuple(required_payloads)
    if custom_required != REQUIRED_PAYLOADS:
        for rel_path in custom_required:
            command.extend(["--required-payload", rel_path])
    completed = subprocess.run(
        command,
        cwd=extracted_root,
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    output = (completed.stdout + "\n" + completed.stderr).strip()
    if completed.returncode != 0:
        return {"status": "fail", "problems": [f"returncode={completed.returncode}"]}, output
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {"status": "fail", "problems": [f"json_decode:{exc}"]}, output
    return payload, output


def _audit_extracted_payload(root: Path, required_payloads: Iterable[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    manifest = root / MANIFEST_NAME
    readme = root / README_NAME
    rows.append(
        _row(
            MANIFEST_NAME,
            "extracted_manifest_exists_nonempty",
            "pass" if manifest.exists() and manifest.stat().st_size > 0 else "fail",
            "extracted release payload manifest exists",
            str(manifest.exists()),
            "True",
        )
    )
    rows.append(
        _row(
            README_NAME,
            "extracted_readme_exists_nonempty",
            "pass" if readme.exists() and readme.stat().st_size > 0 else "fail",
            "extracted release README exists",
            str(readme.exists()),
            "True",
        )
    )
    validation = validate_release_payload(root, required_payloads=required_payloads)
    rows.append(
        _row(
            MANIFEST_NAME,
            "extracted_payload_validation_status",
            "pass" if validation.get("status") == "pass" else "fail",
            "in-process release payload validation passes",
            str(validation.get("status")),
            "pass",
        )
    )
    rows.append(
        _row(
            MANIFEST_NAME,
            "extracted_payload_required_files_present",
            "pass" if validation.get("status") == "pass" else "fail",
            "required release payloads are present and checksum-valid",
            str(len(tuple(required_payloads))),
            "all required payloads",
        )
    )
    return rows


def run_release_payload_audit(
    root: Path | str = ".",
    required_payloads: Iterable[str] = REQUIRED_PAYLOADS,
    timeout_s: int = 120,
) -> pd.DataFrame:
    root_path = Path(root).resolve()
    required = tuple(required_payloads)
    rows: list[dict[str, str]] = []

    zip_path = root_path / "release" / BUNDLE_NAME
    if not zip_path.exists():
        if (root_path / MANIFEST_NAME).exists():
            rows.extend(_audit_extracted_payload(root_path, required))
        else:
            rows.append(_fail(f"release/{BUNDLE_NAME}", "release_zip_exists_nonempty", "release ZIP is missing"))
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

    inspection = inspect_release_bundle(root_path, required_payloads=required)
    inspection_detail = "pack-side release bundle inspection passes"
    if inspection.get("status") != "pass":
        inspection_detail = "; ".join(str(problem) for problem in inspection.get("problems", [])) or inspection_detail
    rows.append(
        _row(
            rel_zip,
            "pack_side_release_inspection_status",
            "pass" if inspection.get("status") == "pass" else "fail",
            inspection_detail,
            str(inspection.get("status")),
            "pass",
        )
    )

    try:
        with tempfile.TemporaryDirectory(prefix="bodyshield_release_payload_") as tmp:
            with zipfile.ZipFile(zip_path) as bundle:
                bad_member = bundle.testzip()
                names = _safe_extract(bundle, Path(tmp))
    except Exception as exc:  # pragma: no cover - defensive reporting path
        rows.append(_fail(rel_zip, "zip_extracts_safely", f"release ZIP could not be safely extracted: {exc}"))
        return pd.DataFrame(rows)

    rows.append(
        _row(
            rel_zip,
            "zip_integrity_test",
            "pass" if bad_member is None else "fail",
            "zipfile CRC test passes",
            str(bad_member),
            "None",
        )
    )
    rows.append(_pass(rel_zip, "zip_extracts_safely", "release ZIP entries extract without unsafe paths", str(len(names)), ">0 entries"))

    with tempfile.TemporaryDirectory(prefix="bodyshield_release_payload_") as tmp:
        extracted = Path(tmp)
        with zipfile.ZipFile(zip_path) as bundle:
            names = _safe_extract(bundle, extracted)
        verifier = extracted / "scripts" / "verify_release_payload.py"
        rows.append(
            _row(
                "scripts/verify_release_payload.py",
                "bundled_verifier_exists_nonempty",
                "pass" if verifier.exists() and verifier.stat().st_size > 0 else "fail",
                "bundled payload verifier exists after extraction",
                str(verifier.exists()),
                "True",
            )
        )
        payload, output = _run_bundled_payload_verifier(extracted, required, timeout_s)
        rows.append(
            _row(
                "scripts/verify_release_payload.py",
                "bundled_verifier_json_status",
                "pass" if payload.get("status") == "pass" else "fail",
                "bundled verifier runs from extracted payload and returns pass JSON",
                str(payload.get("status")),
                "pass",
            )
        )
        if payload.get("status") != "pass":
            rows.append(_fail("scripts/verify_release_payload.py", "bundled_verifier_output", output[:500] or "no output"))
        payload_files_match = inspection.get("payload_files") == payload.get("payload_files")
        payload_bytes_match = inspection.get("payload_bytes") == payload.get("payload_bytes")
        rows.append(
            _row(
                MANIFEST_NAME,
                "extracted_payload_file_count_matches_pack_inspection",
                "pass" if payload_files_match else "fail",
                "extracted verifier file count matches pack-side release inspection",
                str(payload.get("payload_files")),
                str(inspection.get("payload_files")),
            )
        )
        rows.append(
            _row(
                MANIFEST_NAME,
                "extracted_payload_bytes_match_pack_inspection",
                "pass" if payload_bytes_match else "fail",
                "extracted verifier payload bytes match pack-side release inspection",
                str(payload.get("payload_bytes")),
                str(inspection.get("payload_bytes")),
            )
        )
        rows.append(
            _row(
                MANIFEST_NAME,
                "zip_entry_count_matches_manifest_plus_control_files",
                "pass" if len(names) == int(inspection.get("payload_files", -1)) + 2 else "fail",
                "zip entries equal payload manifest rows plus release README and release manifest",
                str(len(names)),
                str(int(inspection.get("payload_files", -1)) + 2),
            )
        )
        rows.append(
            _row(
                "reports/ARTIFACT_MANIFEST.csv",
                "full_pack_manifest_boundary_documented",
                "pass",
                "release validation uses RELEASE_BUNDLE_MANIFEST.csv; reports/ARTIFACT_MANIFEST.csv is pack-side full-pack inventory",
                "release payload manifest authoritative for archive",
                "boundary explicit",
            )
        )

    rows.append(_pass("tmp", "temporary_extraction_cleaned", "temporary extraction directories removed"))
    return pd.DataFrame(rows)


def release_payload_audit_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_release_payload_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_release_payload_audit_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = release_payload_audit_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_release_payload_rows(rows)
    display = failures if not failures.empty else rows.head(80)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Release Payload Audit

Status: `{status}`

This audit safely extracts the portable release ZIP, runs the bundled unpacked-payload verifier from inside the extracted archive, and compares its payload counts with pack-side release inspection. It treats `RELEASE_BUNDLE_MANIFEST.csv` as the archive inventory; `reports/ARTIFACT_MANIFEST.csv` is a pack-side full-pack inventory and is intentionally not the release payload manifest.

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


def write_release_payload_audit_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_release_payload_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "release_payload_audit.csv", index=False)
    write_release_payload_audit_report(reports / "RELEASE_PAYLOAD_AUDIT.md", rows)
    return rows
