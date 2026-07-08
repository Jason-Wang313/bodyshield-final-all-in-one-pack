"""Audit documented outputs against artifact and release inventories."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pandas as pd

from bodyshield.evidence_consistency import extract_local_references
from bodyshield.release_bundle import iter_payload_files


DOCUMENTED_OUTPUT_DOCS: tuple[str, ...] = (
    "README_EXECUTION.md",
    "reports/REPRODUCIBILITY_MANIFEST.md",
    "reports/NON_HARDWARE_COMPLETE.md",
)
ARTIFACT_ROOTS: tuple[str, ...] = ("results", "reports", "paper", "release", "videos", "logs", "figures", "tables")
ARTIFACT_ROOT_FILES: tuple[str, ...] = (
    "trial_schema.schema.json",
    "data_schema.json",
    "README_EXECUTION.md",
    "README.md",
    "REPRODUCE.md",
    "Makefile",
    "requirements.txt",
    "environment.yml",
    "LICENSE",
    "CITATION.cff",
)
ARTIFACT_MANIFEST_EXCLUDED_NAMES: tuple[str, ...] = (
    "ARTIFACT_MANIFEST.csv",
    "ARTIFACT_MANIFEST.md",
    "ARTIFACT_INVENTORY_AUDIT.md",
    "PACK_VERIFICATION.json",
    "PACK_VERIFICATION.md",
    "PORTABLE_HYGIENE_AUDIT.md",
    "RELEASE_DETERMINISM_AUDIT.md",
    "RELEASE_PAYLOAD_AUDIT.md",
    "RELEASE_RUNTIME_AUDIT.md",
    "final_artifact_manifest.json",
    "final_artifact_manifest_nonhardware.json",
    "artifact_inventory_audit.csv",
    "portable_hygiene_audit.csv",
    "release_determinism_audit.csv",
    "release_payload_audit.csv",
    "release_runtime_audit.csv",
)
SELF_OUTPUTS: tuple[str, ...] = (
    "results/artifact_inventory_audit.csv",
    "reports/ARTIFACT_INVENTORY_AUDIT.md",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row(
    artifact: str,
    check: str,
    status: str,
    detail: str,
    observed: str = "",
    expected: str = "",
) -> dict[str, str]:
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


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_artifact_manifest_paths(root: Path | str = ".") -> set[str]:
    root_path = Path(root).resolve()
    excluded = set(ARTIFACT_MANIFEST_EXCLUDED_NAMES)
    paths: set[str] = set()
    for rel_root in ARTIFACT_ROOTS:
        base = root_path / rel_root
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            if path.name in excluded:
                continue
            paths.add(_rel(path, root_path))
    for rel_path in ARTIFACT_ROOT_FILES:
        path = root_path / rel_path
        if path.exists() and path.is_file():
            paths.add(rel_path)
    return paths


def _manifest_exact_set_rows(root: Path, manifest_rows: list[dict[str, str]], expected_paths: set[str]) -> list[dict[str, str]]:
    manifest_paths = {row.get("path", "") for row in manifest_rows}
    missing = sorted(expected_paths - manifest_paths)
    extra = sorted(manifest_paths - expected_paths)
    rows = [
        _row(
            "reports/ARTIFACT_MANIFEST.csv",
            "artifact_manifest_exact_current_generated_set",
            "pass" if not missing and not extra else "fail",
            f"missing={missing[:12]}; extra={extra[:12]}",
            observed=str(len(manifest_paths)),
            expected=str(len(expected_paths)),
        )
    ]
    bad_hashes: list[str] = []
    bad_bytes: list[str] = []
    for row in manifest_rows:
        rel_path = row.get("path", "")
        path = root / rel_path
        if rel_path not in expected_paths:
            continue
        if not path.exists() or not path.is_file():
            bad_bytes.append(f"{rel_path}:missing")
            continue
        if str(path.stat().st_size) != str(row.get("bytes", "")):
            bad_bytes.append(rel_path)
        if file_sha256(path) != row.get("sha256", ""):
            bad_hashes.append(rel_path)
    rows.append(
        _row(
            "reports/ARTIFACT_MANIFEST.csv",
            "artifact_manifest_hashes_match_current_files",
            "pass" if not bad_hashes and not bad_bytes else "fail",
            f"bad_bytes={bad_bytes[:12]}; bad_hashes={bad_hashes[:12]}",
            observed=str(len(bad_bytes) + len(bad_hashes)),
            expected="0",
        )
    )
    return rows


def _release_exact_set_rows(root: Path, release_rows: list[dict[str, str]], expected_payloads: set[str]) -> list[dict[str, str]]:
    manifest_paths = {row.get("path", "") for row in release_rows}
    missing = sorted(expected_payloads - manifest_paths)
    extra = sorted(manifest_paths - expected_payloads)
    rows = [
        _row(
            "release/RELEASE_BUNDLE_MANIFEST.csv",
            "release_manifest_exact_current_payload_set",
            "pass" if not missing and not extra else "fail",
            f"missing={missing[:12]}; extra={extra[:12]}",
            observed=str(len(manifest_paths)),
            expected=str(len(expected_payloads)),
        )
    ]
    bad_hashes: list[str] = []
    bad_bytes: list[str] = []
    for row in release_rows:
        rel_path = row.get("path", "")
        path = root / rel_path
        if rel_path not in expected_payloads:
            continue
        if not path.exists() or not path.is_file():
            bad_bytes.append(f"{rel_path}:missing")
            continue
        if str(path.stat().st_size) != str(row.get("bytes", "")):
            bad_bytes.append(rel_path)
        if file_sha256(path) != row.get("sha256", ""):
            bad_hashes.append(rel_path)
    rows.append(
        _row(
            "release/RELEASE_BUNDLE_MANIFEST.csv",
            "release_manifest_hashes_match_current_files",
            "pass" if not bad_hashes and not bad_bytes else "fail",
            f"bad_bytes={bad_bytes[:12]}; bad_hashes={bad_hashes[:12]}",
            observed=str(len(bad_bytes) + len(bad_hashes)),
            expected="0",
        )
    )
    return rows


def _reference_matches(root: Path, reference: str) -> list[str]:
    if "*" in reference:
        return sorted(_rel(path, root) for path in root.glob(reference) if path.is_file())
    path = root / reference
    return [reference] if path.exists() and path.is_file() else []


def _documented_output_rows(
    root: Path,
    artifact_paths: set[str],
    release_paths: set[str],
    expected_artifacts: set[str],
    expected_payloads: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for doc in DOCUMENTED_OUTPUT_DOCS:
        path = root / doc
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(doc, "documented_output_doc_exists", "documented output source is missing or empty"))
            continue
        references = extract_local_references(path.read_text(encoding="utf-8", errors="ignore"))
        output_refs = [
            ref
            for ref in references
            if ref.startswith(("results/", "reports/", "paper/", "release/"))
            or ref in {"trial_schema.schema.json", "data_schema.json", "README_EXECUTION.md"}
        ]
        rows.append(
            _row(
                doc,
                "documented_output_references_discovered",
                "pass" if output_refs else "fail",
                "documented output references discovered",
                observed=str(len(output_refs)),
                expected=">0",
            )
        )
        for reference in output_refs:
            key = (doc, reference)
            if key in seen:
                continue
            seen.add(key)
            matches = _reference_matches(root, reference)
            if not matches and reference in SELF_OUTPUTS:
                rows.append(
                    _pass(
                        reference,
                        "documented_output_exists_nonempty",
                        f"{doc} reference is produced by this audit after row generation",
                        observed="self_output",
                        expected="self_output",
                    )
                )
                continue
            nonempty_matches = [match for match in matches if (root / match).stat().st_size > 0]
            rows.append(
                _row(
                    reference,
                    "documented_output_exists_nonempty",
                    "pass" if matches and len(matches) == len(nonempty_matches) else "fail",
                    f"{doc} reference exists and is nonempty",
                    observed=str(len(nonempty_matches)),
                    expected=str(len(matches) if matches else ">0"),
                )
            )
            if not matches:
                continue
            artifact_eligible = sorted(match for match in matches if match in expected_artifacts)
            artifact_missing = sorted(match for match in artifact_eligible if match not in artifact_paths)
            rows.append(
                _row(
                    reference,
                    "documented_output_in_artifact_manifest_when_eligible",
                    "pass" if not artifact_missing else "fail",
                    f"{doc} reference artifact_manifest_missing={artifact_missing[:12]}",
                    observed=str(len(artifact_eligible) - len(artifact_missing)),
                    expected=str(len(artifact_eligible)),
                )
            )
            release_eligible = sorted(match for match in matches if match in expected_payloads)
            release_missing = sorted(match for match in release_eligible if match not in release_paths)
            rows.append(
                _row(
                    reference,
                    "documented_output_in_release_manifest_when_eligible",
                    "pass" if not release_missing else "fail",
                    f"{doc} reference release_manifest_missing={release_missing[:12]}",
                    observed=str(len(release_eligible) - len(release_missing)),
                    expected=str(len(release_eligible)),
                )
            )
    return rows


def run_artifact_inventory_audit(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    artifact_manifest_path = root_path / "reports" / "ARTIFACT_MANIFEST.csv"
    release_manifest_path = root_path / "release" / "RELEASE_BUNDLE_MANIFEST.csv"

    if not artifact_manifest_path.exists() or artifact_manifest_path.stat().st_size <= 0:
        return pd.DataFrame([_fail("reports/ARTIFACT_MANIFEST.csv", "artifact_manifest_exists_nonempty", "artifact manifest is missing or empty")])
    if not release_manifest_path.exists() or release_manifest_path.stat().st_size <= 0:
        return pd.DataFrame([_fail("release/RELEASE_BUNDLE_MANIFEST.csv", "release_manifest_exists_nonempty", "release manifest is missing or empty")])

    artifact_rows = _read_manifest(artifact_manifest_path)
    release_rows = _read_manifest(release_manifest_path)
    artifact_paths = {row.get("path", "") for row in artifact_rows}
    release_paths = {row.get("path", "") for row in release_rows}
    expected_artifacts = expected_artifact_manifest_paths(root_path)
    expected_payloads = {_rel(path, root_path) for path in iter_payload_files(root_path)}

    rows.append(_pass("reports/ARTIFACT_MANIFEST.csv", "artifact_manifest_exists_nonempty", "artifact manifest exists and is nonempty", str(len(artifact_rows)), ">0 rows"))
    rows.append(_pass("release/RELEASE_BUNDLE_MANIFEST.csv", "release_manifest_exists_nonempty", "release manifest exists and is nonempty", str(len(release_rows)), ">0 rows"))
    rows.extend(_manifest_exact_set_rows(root_path, artifact_rows, expected_artifacts))
    rows.extend(_release_exact_set_rows(root_path, release_rows, expected_payloads))
    rows.extend(_documented_output_rows(root_path, artifact_paths, release_paths, expected_artifacts, expected_payloads))
    return pd.DataFrame(rows)


def artifact_inventory_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_artifact_inventory_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_artifact_inventory_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = artifact_inventory_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_artifact_inventory_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Artifact Inventory Audit

Status: `{status}`

This audit checks that the final artifact manifest exactly matches current generated artifacts, that the release manifest exactly matches current release-eligible payload files, and that documented output references in the README, reproducibility manifest, and completion report exist and are present in the artifact/release manifests whenever eligible.

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


def write_artifact_inventory_audit_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_artifact_inventory_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "artifact_inventory_audit.csv", index=False)
    write_artifact_inventory_report(reports / "ARTIFACT_INVENTORY_AUDIT.md", rows)
    return rows
