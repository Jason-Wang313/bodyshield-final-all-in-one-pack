"""Portable release-bundle creation and verification for the local pack."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


BUNDLE_NAME = "bodyshield_non_hardware_release.zip"
MANIFEST_NAME = "RELEASE_BUNDLE_MANIFEST.csv"
CHECKSUMS_NAME = "RELEASE_BUNDLE_CHECKSUMS.txt"
README_NAME = "RELEASE_README.md"
REPORT_NAME = "RELEASE_BUNDLE.md"
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

PAYLOAD_ROOTS = {"bodyshield", "configs", "paper", "reports", "results", "scripts", "tests"}
ROOT_PAYLOAD_NAMES = {
    "BODYSHIELD_FINAL_PLAN.md",
    "CLI_AGENT_MASTER_PROMPT.md",
    "data_schema.json",
    "EXPERIMENT_MATRIX_MAXOUT.csv",
    "HARDWARE_AUTONOMOUS_CLI_RUNBOOK.md",
    "MUJOCO_LOG.TXT",
    "NO_HARDWARE_AND_THEORY_DECISION_MEMO.md",
    "NON_HARDWARE_COMPLETION_PROTOCOL.md",
    "pyproject.toml",
    "README_EXECUTION.md",
    "README_FIRST.md",
    "REVIEWER_ATTACK_CLOSURE_MATRIX.md",
    "SAFE_ROBOT_API_SPEC.md",
    "SOURCE_NOTES_FOR_VERIFICATION.md",
    "tasks.yaml",
    "trial_schema.schema.json",
}
SKIP_PARTS = {"__pycache__", ".pytest_cache", "tmp", "release", "build"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".aux", ".bbl", ".blg", ".fls", ".fdb_latexmk", ".synctex.gz"}
SKIP_REPORTS = {
    "ARTIFACT_MANIFEST.csv",
    "ARTIFACT_MANIFEST.md",
    "PACK_VERIFICATION.json",
    "PACK_VERIFICATION.md",
    "PORTABLE_HYGIENE_AUDIT.md",
    "ARTIFACT_INVENTORY_AUDIT.md",
    "RELEASE_DETERMINISM_AUDIT.md",
    "RELEASE_PAYLOAD_AUDIT.md",
    "RELEASE_RUNTIME_AUDIT.md",
    REPORT_NAME,
}
SKIP_RESULTS = {
    "portable_hygiene_audit.csv",
    "artifact_inventory_audit.csv",
    "release_determinism_audit.csv",
    "release_payload_audit.csv",
    "release_runtime_audit.csv",
}
REQUIRED_PAYLOADS = (
    "README_EXECUTION.md",
    "pyproject.toml",
    "bodyshield/pack_verification.py",
    "bodyshield/paper_source_audit.py",
    "bodyshield/portable_hygiene_audit.py",
    "bodyshield/release_bundle.py",
    "bodyshield/release_determinism_audit.py",
    "bodyshield/release_payload_audit.py",
    "bodyshield/release_runtime_audit.py",
    "bodyshield/claim_boundary_audit.py",
    "bodyshield/command_surface_audit.py",
    "bodyshield/config_schema_audit.py",
    "bodyshield/artifact_inventory_audit.py",
    "bodyshield/derived_results_audit.py",
    "bodyshield/evidence_consistency.py",
    "bodyshield/environment_audit.py",
    "bodyshield/results_integrity.py",
    "bodyshield/source_import_audit.py",
    "bodyshield/visual_artifact_audit.py",
    "scripts/run_claim_boundary_audit.py",
    "scripts/run_artifact_inventory_audit.py",
    "scripts/run_command_surface_audit.py",
    "scripts/run_config_schema_audit.py",
    "scripts/run_derived_results_audit.py",
    "scripts/run_environment_dependency_audit.py",
    "scripts/run_evidence_consistency_audit.py",
    "scripts/run_paper_source_audit.py",
    "scripts/run_portable_hygiene_audit.py",
    "scripts/run_release_determinism_audit.py",
    "scripts/run_release_payload_audit.py",
    "scripts/run_release_runtime_audit.py",
    "scripts/run_results_integrity_audit.py",
    "scripts/run_source_import_audit.py",
    "scripts/run_visual_artifact_audit.py",
    "scripts/run_non_hardware.py",
    "scripts/verify_release_payload.py",
    "scripts/verify_non_hardware_pack.py",
    "configs/external_policy_benchmark.example.json",
    "configs/real_video_wam_readiness.example.json",
    "configs/corrective_trace_readiness.example.json",
    "results/trials.csv",
    "results/trials.parquet",
    "results/high_fidelity_benchmark.csv",
    "results/external_policy_benchmark_readiness.csv",
    "results/real_video_wam_readiness.csv",
    "results/corrective_trace_readiness.csv",
    "results/claim_boundary_audit.csv",
    "results/command_surface_audit.csv",
    "results/config_schema_audit.csv",
    "results/derived_results_audit.csv",
    "results/evidence_consistency_audit.csv",
    "results/environment_dependency_audit.csv",
    "results/environment_snapshot.json",
    "results/results_integrity_audit.csv",
    "results/source_import_audit.csv",
    "results/paper_source_audit.csv",
    "results/visual_artifact_audit.csv",
    "reports/CLAIM_LEDGER.md",
    "reports/CLAIM_BOUNDARY_AUDIT.md",
    "reports/COMMAND_SURFACE_AUDIT.md",
    "reports/CONFIG_SCHEMA_AUDIT.md",
    "reports/DERIVED_RESULTS_AUDIT.md",
    "reports/EVIDENCE_CONSISTENCY_AUDIT.md",
    "reports/ENVIRONMENT_DEPENDENCY_AUDIT.md",
    "reports/RESULTS_INTEGRITY_AUDIT.md",
    "reports/SOURCE_IMPORT_AUDIT.md",
    "reports/PAPER_SOURCE_AUDIT.md",
    "reports/VISUAL_ARTIFACT_AUDIT.md",
    "reports/REPRODUCIBILITY_MANIFEST.md",
    "paper/main.tex",
    "paper/references.bib",
    "paper/bodyshield_non_hardware_draft.pdf",
)


@dataclass(frozen=True)
class ReleaseBundleResult:
    zip_path: str
    manifest_path: str
    checksums_path: str
    readme_path: str
    report_path: str
    payload_files: int
    payload_bytes: int
    zip_bytes: int
    zip_sha256: str
    manifest_sha256: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_payload_file(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    rel = path.relative_to(root)
    parts = set(rel.parts)
    if parts & SKIP_PARTS:
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    if len(rel.parts) == 1:
        return rel.name in ROOT_PAYLOAD_NAMES
    if rel.parts[0] not in PAYLOAD_ROOTS:
        return False
    if rel.parts[0] == "reports" and rel.name in SKIP_REPORTS:
        return False
    if rel.parts[0] == "results" and rel.name in SKIP_RESULTS:
        return False
    return True


def iter_payload_files(root: Path | str) -> list[Path]:
    root = Path(root).resolve()
    return sorted(path for path in root.rglob("*") if _is_payload_file(path, root))


def _manifest_rows(root: Path, files: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in files:
        rows.append(
            {
                "path": _rel(path, root),
                "bytes": str(path.stat().st_size),
                "sha256": file_sha256(path),
            }
        )
    return rows


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)


def _read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _release_readme(result_stub: dict[str, Any]) -> str:
    return f"""# BodyShield Non-Hardware Release Bundle

This archive is a portable local export of the BodyShield non-hardware pack.

Evidence boundary:
- Contains software, configs, generated non-hardware results, reports, synthetic media, and the paper draft.
- Does not contain hardware logs, real camera-verifier videos, external trained-policy checkpoints, real-video WAM data, or real corrective-trace datasets.
- Does not replace an external archival upload or public repository release.

Suggested verification after unpacking:
```powershell
python scripts\\verify_release_payload.py
python -m pytest -q
```

Payload summary:
- Payload files: {result_stub["payload_files"]}
- Payload bytes: {result_stub["payload_bytes"]}
- Manifest: `{MANIFEST_NAME}`
"""


def _write_zip_entry(bundle: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(arcname, FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    bundle.writestr(info, data)


def write_release_bundle(root: Path | str = ".") -> ReleaseBundleResult:
    root = Path(root).resolve()
    release_dir = root / "release"
    reports_dir = root / "reports"
    release_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    zip_path = release_dir / BUNDLE_NAME
    manifest_path = release_dir / MANIFEST_NAME
    checksums_path = release_dir / CHECKSUMS_NAME
    readme_path = release_dir / README_NAME
    report_path = reports_dir / REPORT_NAME

    files = iter_payload_files(root)
    rows = _manifest_rows(root, files)
    payload_bytes = sum(int(row["bytes"]) for row in rows)
    result_stub = {"payload_files": len(rows), "payload_bytes": payload_bytes}
    readme_text = _release_readme(result_stub)

    _write_manifest(manifest_path, rows)
    readme_path.write_text(readme_text, encoding="utf-8", newline="\n")
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = bytes_sha256(manifest_bytes)

    with zipfile.ZipFile(zip_path, "w") as bundle:
        _write_zip_entry(bundle, README_NAME, readme_text.encode("utf-8"))
        _write_zip_entry(bundle, MANIFEST_NAME, manifest_bytes)
        for path, row in zip(files, rows):
            _write_zip_entry(bundle, row["path"], path.read_bytes())

    zip_sha = file_sha256(zip_path)
    checksums_path.write_text(
        f"{zip_sha}  release/{BUNDLE_NAME}\n{manifest_sha}  release/{MANIFEST_NAME}\n",
        encoding="utf-8",
    )
    result = ReleaseBundleResult(
        zip_path=f"release/{BUNDLE_NAME}",
        manifest_path=f"release/{MANIFEST_NAME}",
        checksums_path=f"release/{CHECKSUMS_NAME}",
        readme_path=f"release/{README_NAME}",
        report_path=f"reports/{REPORT_NAME}",
        payload_files=len(rows),
        payload_bytes=payload_bytes,
        zip_bytes=zip_path.stat().st_size,
        zip_sha256=zip_sha,
        manifest_sha256=manifest_sha,
    )
    write_release_bundle_report(root, result)
    return result


def write_release_bundle_report(root: Path | str, result: ReleaseBundleResult) -> None:
    root = Path(root).resolve()
    report_path = root / result.report_path
    report_path.write_text(
        f"""# Release Bundle

Status: `created`

| field | value |
|---|---|
| zip | `{result.zip_path}` |
| zip bytes | {result.zip_bytes} |
| zip sha256 | `{result.zip_sha256}` |
| manifest | `{result.manifest_path}` |
| manifest sha256 | `{result.manifest_sha256}` |
| payload files | {result.payload_files} |
| payload bytes | {result.payload_bytes} |
| checksums | `{result.checksums_path}` |

Boundary: this is a portable local non-hardware archive. It does not prove an external archival upload, real trained-policy checkpoint benchmark, real-video WAM training, real corrective-trace adaptation, or hardware transfer.
""",
        encoding="utf-8",
    )


def inspect_release_bundle(root: Path | str = ".", required_payloads: Iterable[str] = REQUIRED_PAYLOADS) -> dict[str, Any]:
    root = Path(root).resolve()
    release_dir = root / "release"
    zip_path = release_dir / BUNDLE_NAME
    manifest_path = release_dir / MANIFEST_NAME
    checksums_path = release_dir / CHECKSUMS_NAME
    readme_path = release_dir / README_NAME
    report_path = root / "reports" / REPORT_NAME
    problems: list[str] = []

    for path in (zip_path, manifest_path, checksums_path, readme_path, report_path):
        if not path.exists() or path.stat().st_size <= 0:
            problems.append(f"{_rel(path, root)}:missing_or_empty")
    if problems:
        return {"status": "fail", "problems": problems}

    rows = _read_manifest(manifest_path)
    manifest_paths = [row.get("path", "") for row in rows]
    manifest_set = set(manifest_paths)
    if len(manifest_set) != len(manifest_paths):
        problems.append("manifest:duplicate_paths")
    for rel_path in manifest_paths:
        if not rel_path or "\\" in rel_path or rel_path.startswith("/") or rel_path.startswith("../") or "/../" in rel_path:
            problems.append(f"{rel_path}:unsafe_path")
        if any(part in rel_path.split("/") for part in SKIP_PARTS):
            problems.append(f"{rel_path}:skipped_part_present")

    missing_required = [path for path in required_payloads if path not in manifest_set]
    if missing_required:
        problems.append(f"missing_required_payloads={missing_required[:12]}")

    try:
        with zipfile.ZipFile(zip_path) as bundle:
            zip_names = set(bundle.namelist())
            expected_names = manifest_set | {README_NAME, MANIFEST_NAME}
            extra = sorted(zip_names - expected_names)
            missing = sorted(expected_names - zip_names)
            if extra or missing:
                problems.append(f"zip_names:extra={extra[:12]};missing={missing[:12]}")
            zipped_manifest = bundle.read(MANIFEST_NAME)
            if bytes_sha256(zipped_manifest) != bytes_sha256(manifest_path.read_bytes()):
                problems.append("zip_manifest:sha256")
            for row in rows:
                rel_path = row["path"]
                data = bundle.read(rel_path)
                if str(len(data)) != row["bytes"]:
                    problems.append(f"{rel_path}:bytes")
                if bytes_sha256(data) != row["sha256"]:
                    problems.append(f"{rel_path}:sha256")
    except Exception as exc:  # pragma: no cover - defensive reporting path
        problems.append(f"zip_read:{exc}")

    checksum_text = checksums_path.read_text(encoding="utf-8", errors="ignore")
    expected_zip_line = f"{file_sha256(zip_path)}  release/{BUNDLE_NAME}"
    expected_manifest_line = f"{file_sha256(manifest_path)}  release/{MANIFEST_NAME}"
    if expected_zip_line not in checksum_text or expected_manifest_line not in checksum_text:
        problems.append("checksums:mismatch")

    boundary_text = readme_path.read_text(encoding="utf-8", errors="ignore") + "\n" + report_path.read_text(
        encoding="utf-8", errors="ignore"
    )
    boundary_terms = (
        "portable local export",
        "Does not contain hardware logs",
        "does not prove an external archival upload",
        "python scripts\\verify_release_payload.py",
    )
    missing_terms = [term for term in boundary_terms if term not in boundary_text]
    if missing_terms:
        problems.append(f"boundary_terms={missing_terms}")

    return {
        "status": "pass" if not problems else "fail",
        "problems": problems,
        "payload_files": len(rows),
        "payload_bytes": sum(int(row["bytes"]) for row in rows),
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": file_sha256(zip_path),
        "manifest_sha256": file_sha256(manifest_path),
    }


def validate_release_payload(root: Path | str = ".", required_payloads: Iterable[str] | None = REQUIRED_PAYLOADS) -> dict[str, Any]:
    """Validate an unpacked release archive from inside its extracted root."""

    root = Path(root).resolve()
    manifest_path = root / MANIFEST_NAME
    readme_path = root / README_NAME
    problems: list[str] = []
    for path in (manifest_path, readme_path):
        if not path.exists() or path.stat().st_size <= 0:
            problems.append(f"{path.name}:missing_or_empty")
    if problems:
        return {"status": "fail", "problems": problems}

    rows = _read_manifest(manifest_path)
    manifest_paths = [row.get("path", "") for row in rows]
    manifest_set = set(manifest_paths)
    if len(manifest_set) != len(manifest_paths):
        problems.append("manifest:duplicate_paths")
    if required_payloads is None:
        required_payloads = REQUIRED_PAYLOADS
    missing_required = [path for path in required_payloads if path not in manifest_set]
    if missing_required:
        problems.append(f"missing_required_payloads={missing_required[:12]}")

    for row in rows:
        rel_path = row.get("path", "")
        if not rel_path or "\\" in rel_path or rel_path.startswith("/") or rel_path.startswith("../") or "/../" in rel_path:
            problems.append(f"{rel_path}:unsafe_path")
            continue
        if any(part in rel_path.split("/") for part in SKIP_PARTS):
            problems.append(f"{rel_path}:skipped_part_present")
        path = root / rel_path
        try:
            resolved = path.resolve()
        except OSError as exc:
            problems.append(f"{rel_path}:resolve:{exc}")
            continue
        if root not in resolved.parents and resolved != root:
            problems.append(f"{rel_path}:outside_root")
            continue
        if not path.exists() or not path.is_file():
            problems.append(f"{rel_path}:missing")
            continue
        if str(path.stat().st_size) != row.get("bytes", ""):
            problems.append(f"{rel_path}:bytes")
        if file_sha256(path) != row.get("sha256", ""):
            problems.append(f"{rel_path}:sha256")

    readme_text = readme_path.read_text(encoding="utf-8", errors="ignore")
    boundary_terms = (
        "portable local export",
        "Does not contain hardware logs",
        "Does not replace an external archival upload",
        "python scripts\\verify_release_payload.py",
    )
    missing_terms = [term for term in boundary_terms if term not in readme_text]
    if missing_terms:
        problems.append(f"readme_terms={missing_terms}")

    return {
        "status": "pass" if not problems else "fail",
        "problems": problems,
        "payload_files": len(rows),
        "payload_bytes": sum(int(row.get("bytes", 0)) for row in rows),
        "manifest_sha256": file_sha256(manifest_path),
    }


def release_bundle_payload_json(root: Path | str = ".") -> str:
    return json.dumps(inspect_release_bundle(root), indent=2, sort_keys=True)


def release_payload_validation_json(root: Path | str = ".") -> str:
    return json.dumps(validate_release_payload(root), indent=2, sort_keys=True)
