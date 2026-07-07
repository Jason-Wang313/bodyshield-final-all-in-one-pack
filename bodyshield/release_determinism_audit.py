"""Determinism audit for the portable release ZIP bytes."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pandas as pd

from bodyshield.release_bundle import (
    BUNDLE_NAME,
    CHECKSUMS_NAME,
    FIXED_ZIP_TIMESTAMP,
    MANIFEST_NAME,
    README_NAME,
    _read_manifest,
    _release_readme,
    _write_zip_entry,
    bytes_sha256,
    file_sha256,
)


EXPECTED_CONTROL_ENTRIES = (README_NAME, MANIFEST_NAME)


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


def _manifest_bytes(rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["path", "bytes", "sha256"])
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _release_readme_bytes(rows: list[dict[str, str]]) -> bytes:
    payload_bytes = sum(int(row["bytes"]) for row in rows)
    return _release_readme({"payload_files": len(rows), "payload_bytes": payload_bytes}).encode("utf-8")


def reconstruct_release_zip_bytes(root: Path | str = ".") -> bytes:
    root_path = Path(root).resolve()
    rows = _read_manifest(root_path / "release" / MANIFEST_NAME)
    manifest_bytes = _manifest_bytes(rows)
    readme_bytes = _release_readme_bytes(rows)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        _write_zip_entry(bundle, README_NAME, readme_bytes)
        _write_zip_entry(bundle, MANIFEST_NAME, manifest_bytes)
        for row in rows:
            _write_zip_entry(bundle, row["path"], (root_path / row["path"]).read_bytes())
    return output.getvalue()


def _safe_manifest_paths(paths: list[str]) -> bool:
    for rel_path in paths:
        if not rel_path or "\\" in rel_path or rel_path.startswith("/") or rel_path.startswith("../") or "/../" in rel_path:
            return False
    return True


def run_release_determinism_audit(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    release_dir = root_path / "release"
    zip_path = release_dir / BUNDLE_NAME
    manifest_path = release_dir / MANIFEST_NAME
    checksums_path = release_dir / CHECKSUMS_NAME
    readme_path = release_dir / README_NAME
    rel_zip = f"release/{BUNDLE_NAME}"
    rows: list[dict[str, str]] = []

    control_files = [zip_path, manifest_path, checksums_path, readme_path]
    missing = [path.relative_to(root_path).as_posix() for path in control_files if not path.exists() or path.stat().st_size <= 0]
    rows.append(
        _row(
            "release",
            "release_control_files_exist",
            "pass" if not missing else "fail",
            f"missing_or_empty={missing}",
            str(len(control_files) - len(missing)),
            str(len(control_files)),
        )
    )
    if missing:
        return pd.DataFrame(rows)

    try:
        manifest_rows = _read_manifest(manifest_path)
    except Exception as exc:  # pragma: no cover - defensive reporting path
        rows.append(_fail(f"release/{MANIFEST_NAME}", "release_manifest_parse", f"could not parse release manifest: {exc}"))
        return pd.DataFrame(rows)

    manifest_paths = [row.get("path", "") for row in manifest_rows]
    manifest_set = set(manifest_paths)
    rows.append(
        _row(
            f"release/{MANIFEST_NAME}",
            "release_manifest_parse_nonempty",
            "pass" if manifest_rows else "fail",
            "release payload manifest parses and has rows",
            str(len(manifest_rows)),
            ">0",
        )
    )
    rows.append(
        _row(
            f"release/{MANIFEST_NAME}",
            "manifest_paths_unique_safe",
            "pass" if len(manifest_set) == len(manifest_paths) and _safe_manifest_paths(manifest_paths) else "fail",
            "manifest paths are unique and relative-safe",
            f"unique={len(manifest_set)}; rows={len(manifest_paths)}",
            "unique and safe",
        )
    )
    excluded_pack_side = {
        "reports/ARTIFACT_MANIFEST.csv",
        "reports/ARTIFACT_MANIFEST.md",
        "reports/PORTABLE_HYGIENE_AUDIT.md",
        "reports/RELEASE_DETERMINISM_AUDIT.md",
        "reports/RELEASE_PAYLOAD_AUDIT.md",
        "reports/RELEASE_RUNTIME_AUDIT.md",
        "results/portable_hygiene_audit.csv",
        "results/release_determinism_audit.csv",
        "results/release_payload_audit.csv",
        "results/release_runtime_audit.csv",
    }
    excluded_present = sorted(path for path in manifest_paths if path in excluded_pack_side)
    rows.append(
        _row(
            f"release/{MANIFEST_NAME}",
            "pack_side_dynamic_outputs_excluded",
            "pass" if not excluded_present else "fail",
            f"pack-side dynamic outputs in payload={excluded_present}",
            str(len(excluded_present)),
            "0",
        )
    )

    missing_payload = []
    hash_mismatches = []
    size_mismatches = []
    for row in manifest_rows:
        rel_path = row["path"]
        path = root_path / rel_path
        if not path.exists() or not path.is_file():
            missing_payload.append(rel_path)
            continue
        if str(path.stat().st_size) != row.get("bytes", ""):
            size_mismatches.append(rel_path)
        if file_sha256(path) != row.get("sha256", ""):
            hash_mismatches.append(rel_path)
    rows.append(
        _row(
            f"release/{MANIFEST_NAME}",
            "current_payload_files_exist",
            "pass" if not missing_payload else "fail",
            f"missing_payload={missing_payload[:12]}",
            str(len(manifest_rows) - len(missing_payload)),
            str(len(manifest_rows)),
        )
    )
    rows.append(
        _row(
            f"release/{MANIFEST_NAME}",
            "current_payload_hashes_match_manifest",
            "pass" if not hash_mismatches and not size_mismatches else "fail",
            f"hash_mismatches={hash_mismatches[:12]}; size_mismatches={size_mismatches[:12]}",
            f"hash={len(hash_mismatches)}; size={len(size_mismatches)}",
            "0",
        )
    )

    computed_manifest_bytes = _manifest_bytes(manifest_rows)
    rows.append(
        _row(
            f"release/{MANIFEST_NAME}",
            "generated_manifest_bytes_match_file",
            "pass" if computed_manifest_bytes == manifest_path.read_bytes() else "fail",
            "deterministic manifest writer reproduces release manifest bytes",
            bytes_sha256(computed_manifest_bytes),
            file_sha256(manifest_path),
        )
    )
    computed_readme_bytes = _release_readme_bytes(manifest_rows)
    rows.append(
        _row(
            f"release/{README_NAME}",
            "generated_readme_bytes_match_file",
            "pass" if computed_readme_bytes == readme_path.read_bytes() else "fail",
            "deterministic release README writer reproduces release README bytes",
            bytes_sha256(computed_readme_bytes),
            file_sha256(readme_path),
        )
    )

    expected_order = list(EXPECTED_CONTROL_ENTRIES) + manifest_paths
    try:
        with zipfile.ZipFile(zip_path) as bundle:
            infos = bundle.infolist()
            zip_names = [info.filename for info in infos]
            fixed_timestamps = all(info.date_time == FIXED_ZIP_TIMESTAMP for info in infos)
            fixed_external_attr = all(info.external_attr == (0o644 << 16) for info in infos)
            no_dirs = all(not info.is_dir() for info in infos)
            readme_in_zip = bundle.read(README_NAME)
            manifest_in_zip = bundle.read(MANIFEST_NAME)
    except Exception as exc:  # pragma: no cover - defensive reporting path
        rows.append(_fail(rel_zip, "zip_metadata_readable", f"could not inspect zip metadata: {exc}"))
        return pd.DataFrame(rows)

    rows.append(_pass(rel_zip, "zip_metadata_readable", "release ZIP metadata is readable", str(len(zip_names))))
    rows.append(
        _row(
            rel_zip,
            "zip_entry_order_matches_manifest",
            "pass" if zip_names == expected_order else "fail",
            "ZIP entry order is deterministic README, manifest, then manifest rows",
            str(len(zip_names)),
            str(len(expected_order)),
        )
    )
    rows.append(
        _row(rel_zip, "zip_fixed_timestamps", "pass" if fixed_timestamps else "fail", "ZIP entries use fixed timestamp", str(fixed_timestamps), str(FIXED_ZIP_TIMESTAMP))
    )
    rows.append(
        _row(rel_zip, "zip_fixed_external_attr", "pass" if fixed_external_attr else "fail", "ZIP entries use fixed file permissions", str(fixed_external_attr), str(0o644 << 16))
    )
    rows.append(_row(rel_zip, "zip_no_directory_entries", "pass" if no_dirs else "fail", "ZIP contains only file entries", str(no_dirs), "True"))
    rows.append(
        _row(
            rel_zip,
            "zip_control_entries_match_files",
            "pass" if readme_in_zip == readme_path.read_bytes() and manifest_in_zip == manifest_path.read_bytes() else "fail",
            "control entries inside ZIP match release control files",
            f"readme={bytes_sha256(readme_in_zip)}; manifest={bytes_sha256(manifest_in_zip)}",
            "control file hashes",
        )
    )

    try:
        reconstructed = reconstruct_release_zip_bytes(root_path)
    except Exception as exc:
        rows.append(_fail(rel_zip, "reconstructed_zip_bytes_match", f"could not reconstruct release ZIP bytes: {exc}"))
        return pd.DataFrame(rows)
    actual = zip_path.read_bytes()
    rows.append(
        _row(
            rel_zip,
            "reconstructed_zip_sha256_matches",
            "pass" if bytes_sha256(reconstructed) == file_sha256(zip_path) else "fail",
            "reconstructed ZIP SHA-256 matches release ZIP",
            bytes_sha256(reconstructed),
            file_sha256(zip_path),
        )
    )
    rows.append(
        _row(
            rel_zip,
            "reconstructed_zip_bytes_match",
            "pass" if reconstructed == actual else "fail",
            "reconstructed ZIP bytes exactly match release ZIP bytes",
            str(len(reconstructed)),
            str(len(actual)),
        )
    )
    checksum_text = checksums_path.read_text(encoding="utf-8", errors="ignore")
    expected_lines = (
        f"{file_sha256(zip_path)}  release/{BUNDLE_NAME}",
        f"{file_sha256(manifest_path)}  release/{MANIFEST_NAME}",
    )
    rows.append(
        _row(
            f"release/{CHECKSUMS_NAME}",
            "checksums_file_matches_release_files",
            "pass" if all(line in checksum_text for line in expected_lines) else "fail",
            "checksums file contains current release ZIP and manifest hashes",
            "|".join(expected_lines),
            "both checksum lines",
        )
    )
    return pd.DataFrame(rows)


def release_determinism_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_release_determinism_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_release_determinism_audit_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = release_determinism_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_release_determinism_rows(rows)
    display = failures if not failures.empty else rows.head(80)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Release Determinism Audit

Status: `{status}`

This audit verifies that the portable release ZIP is byte-reproducible from the current release payload manifest, current local payload files, fixed ZIP metadata, deterministic entry order, and deterministic release README/manifest writers. Pack-side dynamic reports are intentionally excluded from the archive to avoid self-referential checksum churn.

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


def write_release_determinism_audit_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_release_determinism_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "release_determinism_audit.csv", index=False)
    write_release_determinism_audit_report(reports / "RELEASE_DETERMINISM_AUDIT.md", rows)
    return rows
