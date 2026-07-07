"""End-to-end verification helpers for the non-hardware BodyShield pack."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image
from pypdf import PdfReader

from bodyshield.release_bundle import inspect_release_bundle


REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "results/trials.csv",
    "results/trials.parquet",
    "results/trials_sample.jsonl",
    "results/breaking_search.csv",
    "results/bodybreak_minimality_audit.csv",
    "results/summary_by_method_bucket.csv",
    "results/high_fidelity_benchmark.csv",
    "results/external_policy_benchmark_readiness.csv",
    "results/real_video_wam_readiness.csv",
    "results/corrective_trace_readiness.csv",
    "results/artifact_inventory_audit.csv",
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
    "results/portable_hygiene_audit.csv",
    "results/release_determinism_audit.csv",
    "results/release_payload_audit.csv",
    "results/release_runtime_audit.csv",
    "results/visual_artifact_audit.csv",
    "results/mujoco_residual_policy_gate_ablation.csv",
    "results/simulation_rollout_videos.csv",
    "results/videos/bodyshield_synthetic_nominal_reference.gif",
    "results/videos/bodyshield_synthetic_bodybreak_failure.gif",
    "results/videos/bodyshield_synthetic_bodyshield_repair.gif",
    "reports/NON_HARDWARE_AUDIT.md",
    "reports/NON_HARDWARE_REQUIREMENTS_TRACE.md",
    "reports/CLAIM_LEDGER.md",
    "reports/claim_ledger.csv",
    "reports/NOT_READY_REASON.md",
    "reports/PAPER_WRAPPED_COMPLETE.md",
    "reports/baseline_fairness_protocol.md",
    "reports/final_artifact_manifest.json",
    "reports/final_artifact_manifest_nonhardware.json",
    "reports/final_reviewer_prebuttal.md",
    "reports/final_submission_readiness_report.md",
    "reports/related_work_audit.md",
    "reports/theory_moat_report.md",
    "reports/REPRODUCIBILITY_MANIFEST.md",
    "reports/SIMULATION_ROLLOUT_VIDEOS.md",
    "reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md",
    "reports/REAL_VIDEO_WAM_READINESS.md",
    "reports/CORRECTIVE_TRACE_READINESS.md",
    "reports/ARTIFACT_INVENTORY_AUDIT.md",
    "reports/CLAIM_BOUNDARY_AUDIT.md",
    "reports/COMMAND_SURFACE_AUDIT.md",
    "reports/CONFIG_SCHEMA_AUDIT.md",
    "reports/DERIVED_RESULTS_AUDIT.md",
    "reports/EVIDENCE_CONSISTENCY_AUDIT.md",
    "reports/ENVIRONMENT_DEPENDENCY_AUDIT.md",
    "reports/RESULTS_INTEGRITY_AUDIT.md",
    "reports/SOURCE_IMPORT_AUDIT.md",
    "reports/PAPER_SOURCE_AUDIT.md",
    "reports/PORTABLE_HYGIENE_AUDIT.md",
    "reports/RELEASE_DETERMINISM_AUDIT.md",
    "reports/RELEASE_PAYLOAD_AUDIT.md",
    "reports/RELEASE_RUNTIME_AUDIT.md",
    "reports/VISUAL_ARTIFACT_AUDIT.md",
    "reports/PAPER_BUILD_STATUS.json",
    "reports/PAPER_BUILD_LOG.txt",
    "reports/ARTIFACT_MANIFEST.csv",
    "reports/RELEASE_BUNDLE.md",
    "paper/bodyshield_icra.tex",
    "paper/related_work_table.tex",
    "paper/supplementary.tex",
    "paper/appendix_reviewer_prebuttal.tex",
    "paper/video_index.md",
    "paper/bodyshield_non_hardware_draft.pdf",
    "videos/video_index.md",
    "release/bodyshield_non_hardware_release.zip",
    "release/RELEASE_BUNDLE_MANIFEST.csv",
    "release/RELEASE_BUNDLE_CHECKSUMS.txt",
    "release/RELEASE_README.md",
)

EXPECTED_GIFS: tuple[str, ...] = (
    "results/videos/bodyshield_synthetic_nominal_reference.gif",
    "results/videos/bodyshield_synthetic_bodybreak_failure.gif",
    "results/videos/bodyshield_synthetic_bodyshield_repair.gif",
)

STALE_PHRASES: tuple[str, ...] = (
    "simulation videos were not generated",
    "does not yet train a neural",
    "no neural WAM",
    "neural visual WAM training",
    "visual or neural WAM",
    "learned MuJoCo residual-policy",
    "local MuJoCo residual-policy",
    "MuJoCo residual policy is a local",
    "# MuJoCo Residual Policy Interpretation",
    "not full trained-policy quality",
    "no full robot-policy",
)

TEXT_SKIP_PARTS = {"__pycache__", ".pytest_cache", "tmp"}
TEXT_SKIP_SUFFIXES = {".pdf", ".png", ".gif", ".parquet", ".pyc", ".pyo", ".zip"}


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    status: str
    detail: str


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    include_roots = [root / "bodyshield", root / "scripts", root / "tests", root / "configs", root / "pyproject.toml"]
    files: list[Path] = []
    for item in include_roots:
        if item.is_file():
            files.append(item)
        elif item.exists():
            files.extend(
                path
                for path in item.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and ".pytest_cache" not in path.parts
                and path.suffix not in {".pyc", ".pyo"}
            )
    for path in sorted(files):
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ok(name: str, detail: str) -> VerificationCheck:
    return VerificationCheck(name, "pass", detail)


def _fail(name: str, detail: str) -> VerificationCheck:
    return VerificationCheck(name, "fail", detail)


def _text_files(root: Path) -> Iterable[Path]:
    for base in [root / "paper", root / "reports", root / "scripts", root / "bodyshield", root / "tests", root / "README_EXECUTION.md"]:
        if not base.exists():
            continue
        paths = [base] if base.is_file() else base.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            if any(part in TEXT_SKIP_PARTS for part in path.parts):
                continue
            if path.name == "pack_verification.py":
                continue
            if path.suffix.lower() in TEXT_SKIP_SUFFIXES:
                continue
            yield path


def check_required_artifacts(root: Path) -> VerificationCheck:
    missing: list[str] = []
    empty: list[str] = []
    for rel_path in REQUIRED_ARTIFACTS:
        path = root / rel_path
        if not path.exists():
            missing.append(rel_path)
        elif path.stat().st_size <= 0:
            empty.append(rel_path)
    if missing or empty:
        return _fail("required_artifacts", f"missing={missing}; empty={empty}")
    return _ok("required_artifacts", f"{len(REQUIRED_ARTIFACTS)} required artifacts exist and are nonempty")


def check_manifest(root: Path) -> VerificationCheck:
    manifest = root / "reports" / "ARTIFACT_MANIFEST.csv"
    if not manifest.exists():
        return _fail("artifact_manifest", "reports/ARTIFACT_MANIFEST.csv is missing")
    rows = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))
    code_version = tree_hash(root)
    bad: list[str] = []
    seen_paths = set()
    for row in rows:
        rel_path = row["path"]
        seen_paths.add(rel_path)
        path = root / rel_path
        if not path.exists():
            bad.append(f"{rel_path}:missing")
            continue
        if file_sha256(path) != row["sha256"]:
            bad.append(f"{rel_path}:sha256")
        if row["code_version"] != code_version:
            bad.append(f"{rel_path}:code_version")
    manifest_excluded = {
        "reports/ARTIFACT_MANIFEST.csv",
        "reports/ARTIFACT_MANIFEST.md",
        "reports/ARTIFACT_INVENTORY_AUDIT.md",
        "reports/PORTABLE_HYGIENE_AUDIT.md",
        "reports/RELEASE_DETERMINISM_AUDIT.md",
        "reports/RELEASE_PAYLOAD_AUDIT.md",
        "reports/RELEASE_RUNTIME_AUDIT.md",
        "reports/final_artifact_manifest.json",
        "reports/final_artifact_manifest_nonhardware.json",
        "results/artifact_inventory_audit.csv",
        "results/portable_hygiene_audit.csv",
        "results/release_determinism_audit.csv",
        "results/release_payload_audit.csv",
        "results/release_runtime_audit.csv",
    }
    required_in_manifest = [
        path for path in REQUIRED_ARTIFACTS if not path.startswith("reports/PACK_VERIFICATION") and path not in manifest_excluded
    ]
    missing_required = [path for path in required_in_manifest if path not in seen_paths]
    if bad or missing_required:
        return _fail("artifact_manifest", f"rows={len(rows)}; bad={bad[:12]}; missing_required={missing_required}")
    return _ok("artifact_manifest", f"rows={len(rows)}; code_version={code_version}; hashes and required rows match")


def check_pdf(root: Path) -> VerificationCheck:
    pdf_path = root / "paper" / "bodyshield_non_hardware_draft.pdf"
    try:
        reader = PdfReader(str(pdf_path))
        trailer_root: dict[str, Any] = reader.trailer.get("/Root", {})
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return _fail("paper_pdf", f"could not read PDF: {exc}")
    bad_tokens = [token for token in ("??", "[?]", "undefined", "Citation") if token in text]
    unsafe = {
        "encrypted": reader.is_encrypted,
        "open_action": bool(trailer_root.get("/OpenAction")),
        "acroform": bool(trailer_root.get("/AcroForm")),
        "names": bool(trailer_root.get("/Names")),
    }
    unsafe_hits = [name for name, hit in unsafe.items() if hit]
    if len(reader.pages) != 3 or bad_tokens or unsafe_hits:
        return _fail("paper_pdf", f"pages={len(reader.pages)}; bad_tokens={bad_tokens}; unsafe={unsafe_hits}")
    required_boundary_terms = ("rollout", "generated frames", "real camera videos")
    if any(term not in text for term in required_boundary_terms):
        return _fail("paper_pdf", "missing synthetic-media boundary sentence in extracted text")
    return _ok("paper_pdf", "3 pages; safe structure; citations resolved; synthetic-media boundary present")


def check_paper_build_log(root: Path) -> VerificationCheck:
    logs = [root / "paper" / "build" / "main.log", root / "reports" / "PAPER_BUILD_LOG.txt"]
    patterns = ("LaTeX Warning", "undefined", "Citation", "Reference", "Overfull")
    hits: list[str] = []
    for path in logs:
        if not path.exists():
            hits.append(f"{path.relative_to(root).as_posix()}:missing")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern in text:
                hits.append(f"{path.relative_to(root).as_posix()}:{pattern}")
    if hits:
        return _fail("paper_build_log", "; ".join(hits))
    return _ok("paper_build_log", "final TeX logs contain no unresolved citation/reference warnings")


def check_gifs(root: Path) -> VerificationCheck:
    bad: list[str] = []
    frame_counts: list[str] = []
    for rel_path in EXPECTED_GIFS:
        path = root / rel_path
        if not path.exists():
            bad.append(f"{rel_path}:missing")
            continue
        try:
            image = Image.open(path)
            frame_counts.append(f"{Path(rel_path).name}={image.n_frames}")
            if image.n_frames < 2 or image.size[0] <= 0 or image.size[1] <= 0:
                bad.append(f"{rel_path}:invalid_frames_or_size")
        except Exception as exc:  # pragma: no cover - defensive reporting path
            bad.append(f"{rel_path}:{exc}")
    if bad:
        return _fail("synthetic_gifs", "; ".join(bad))
    return _ok("synthetic_gifs", "; ".join(frame_counts))


def check_video_manifest(root: Path) -> VerificationCheck:
    path = root / "results" / "simulation_rollout_videos.csv"
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"))) if path.exists() else []
    artifact_ids = {row.get("artifact_id", "") for row in rows}
    expected = {"nominal_reference", "bodybreak_failure", "bodyshield_repair"}
    boundary_ok = all("Synthetic generated rollout only" in row.get("evidence_boundary", "") for row in rows)
    if artifact_ids != expected or not boundary_ok:
        return _fail("simulation_rollout_videos", f"artifact_ids={sorted(artifact_ids)}; boundary_ok={boundary_ok}")
    return _ok("simulation_rollout_videos", "3 synthetic rollout rows with explicit evidence boundary")


def check_external_policy_readiness(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "external_policy_benchmark_readiness.csv"
    report_path = root / "reports" / "EXTERNAL_POLICY_BENCHMARK_READINESS.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    statuses = [row.get("status", "") for row in rows]
    boundaries = [row.get("evidence_boundary", "") for row in rows]
    fixture_ok = "fixture_smoke_passed" in statuses
    missing_ok = "missing_checkpoint" in statuses
    boundary_ok = all(
        "not external" in boundary.lower() or "no external trained-policy evidence" in boundary.lower()
        or "not a mujoco/maniskill task-rollout benchmark" in boundary.lower()
        for boundary in boundaries
    )
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_boundary_ok = (
        "not external/full-scale MuJoCo or ManiSkill trained-policy evidence" in report_text
        and "no external trained-policy checkpoint is present" in report_text
    )
    if not rows or not fixture_ok or not missing_ok or not boundary_ok or not report_boundary_ok:
        return _fail(
            "external_policy_readiness",
            f"rows={len(rows)}; statuses={statuses}; boundary_ok={boundary_ok}; report_boundary_ok={report_boundary_ok}",
        )
    return _ok(
        "external_policy_readiness",
        f"rows={len(rows)}; fixture_smoke_passed={statuses.count('fixture_smoke_passed')}; missing_checkpoint={statuses.count('missing_checkpoint')}",
    )


def check_real_video_wam_readiness(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "real_video_wam_readiness.csv"
    report_path = root / "reports" / "REAL_VIDEO_WAM_READINESS.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    statuses = [row.get("status", "") for row in rows]
    boundaries = [row.get("evidence_boundary", "") for row in rows]
    fixture_ok = "fixture_training_smoke_passed" in statuses
    missing_ok = "missing_dataset" in statuses
    boundary_ok = all(
        "not real camera video" in boundary.lower()
        or "no real-video wam evidence" in boundary.lower()
        or "not foundation-scale training" in boundary.lower()
        for boundary in boundaries
    )
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_boundary_ok = (
        "not real-video WAM evidence" in report_text
        and "no real camera dataset is present" in report_text
        and "no real-video or foundation-scale WAM claim is supported" in report_text
    )
    if not rows or not fixture_ok or not missing_ok or not boundary_ok or not report_boundary_ok:
        return _fail(
            "real_video_wam_readiness",
            f"rows={len(rows)}; statuses={statuses}; boundary_ok={boundary_ok}; report_boundary_ok={report_boundary_ok}",
        )
    return _ok(
        "real_video_wam_readiness",
        f"rows={len(rows)}; fixture_training_smoke_passed={statuses.count('fixture_training_smoke_passed')}; missing_dataset={statuses.count('missing_dataset')}",
    )


def check_corrective_trace_readiness(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "corrective_trace_readiness.csv"
    report_path = root / "reports" / "CORRECTIVE_TRACE_READINESS.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    statuses = [row.get("status", "") for row in rows]
    boundaries = [row.get("evidence_boundary", "") for row in rows]
    fixture_ok = "fixture_fit_smoke_passed" in statuses
    missing_ok = "missing_dataset" in statuses
    boundary_ok = all(
        "not real robot" in boundary.lower()
        or "no real corrective-trace evidence" in boundary.lower()
        or "not online adaptation" in boundary.lower()
        for boundary in boundaries
    )
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_boundary_ok = (
        "not real corrective-trace adaptation" in report_text
        and "no real/external corrective trace dataset is present" in report_text
        and "no real corrective-trace adaptation claim is supported" in report_text
    )
    if not rows or not fixture_ok or not missing_ok or not boundary_ok or not report_boundary_ok:
        return _fail(
            "corrective_trace_readiness",
            f"rows={len(rows)}; statuses={statuses}; boundary_ok={boundary_ok}; report_boundary_ok={report_boundary_ok}",
        )
    return _ok(
        "corrective_trace_readiness",
        f"rows={len(rows)}; fixture_fit_smoke_passed={statuses.count('fixture_fit_smoke_passed')}; missing_dataset={statuses.count('missing_dataset')}",
    )


def check_stale_phrases(root: Path) -> VerificationCheck:
    hits: list[str] = []
    for path in _text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for phrase in STALE_PHRASES:
            if phrase in text:
                hits.append(f"{path.relative_to(root).as_posix()}:{phrase}")
    if hits:
        return _fail("stale_phrases", "; ".join(hits[:20]))
    return _ok("stale_phrases", f"no stale downgrade phrases in {sum(1 for _ in _text_files(root))} text files")


def check_release_bundle(root: Path) -> VerificationCheck:
    inspection = inspect_release_bundle(root)
    if inspection.get("status") != "pass":
        return _fail("release_bundle", "; ".join(str(problem) for problem in inspection.get("problems", [])))
    return _ok(
        "release_bundle",
        (
            f"payload_files={inspection['payload_files']}; zip_bytes={inspection['zip_bytes']}; "
            f"zip_sha256={inspection['zip_sha256']}"
        ),
    )


def check_evidence_consistency(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "evidence_consistency_audit.csv"
    report_path = root / "reports" / "EVIDENCE_CONSISTENCY_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "ok"]
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "missing references | 0" in report_text
    if not rows or bad or not report_ok:
        return _fail(
            "evidence_consistency",
            f"rows={len(rows)}; bad={bad[:12]}; report_ok={report_ok}",
        )
    documents = sorted({row.get("document", "") for row in rows})
    return _ok("evidence_consistency", f"rows={len(rows)}; documents={len(documents)}; all referenced local evidence exists")


def check_environment_dependency_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "environment_dependency_audit.csv"
    snapshot_path = root / "results" / "environment_snapshot.json"
    report_path = root / "reports" / "ENVIRONMENT_DEPENDENCY_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    required_bad = [
        row
        for row in rows
        if str(row.get("required", "")).lower() in {"true", "1"} and row.get("status") != "pass"
    ]
    snapshot_ok = False
    if snapshot_path.exists():
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot_ok = bool(snapshot.get("python_version") and snapshot.get("platform") and snapshot.get("pyproject_dependencies"))
        except json.JSONDecodeError:
            snapshot_ok = False
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "required failures | 0" in report_text
    if not rows or required_bad or not snapshot_ok or not report_ok:
        return _fail(
            "environment_dependency_audit",
            f"rows={len(rows)}; required_bad={required_bad[:12]}; snapshot_ok={snapshot_ok}; report_ok={report_ok}",
        )
    return _ok("environment_dependency_audit", f"rows={len(rows)}; required dependencies/tools present and declared")


def check_results_integrity_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "results_integrity_audit.csv"
    report_path = root / "reports" / "RESULTS_INTEGRITY_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "csv_parse",
        "csv_nonempty_rows",
        "required_columns",
        "exact_row_count",
        "jsonl_metadata_code_hash",
        "parquet_rows_match_trials_csv",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "results_integrity_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("results_integrity_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; generated tables pass integrity checks")


def check_source_import_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "source_import_audit.csv"
    report_path = root / "reports" / "SOURCE_IMPORT_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "source_root_exists",
        "source_python_files_discovered",
        "python_file_py_compile",
        "script_has_main_guard",
        "bodyshield_module_imports_in_subprocess",
        "hardware_stub_refusal_boundary_present",
        "hardware_stub_forbidden_raw_io_absent",
        "safe_robot_api_methods_raise_safety_violation",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "source_import_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("source_import_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; source compile/import and hardware-stub safety pass")


def check_derived_results_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "derived_results_audit.csv"
    report_path = root / "reports" / "DERIVED_RESULTS_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    artifacts = {row.get("artifact", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "primary_trials_exists_nonempty",
        "derived_table_required_columns_present",
        "derived_table_key_set_matches",
        "derived_table_numeric_values_match",
    }
    required_artifacts = {
        "results/summary_by_method_bucket.csv",
        "results/robustness_profiles.csv",
        "results/secondary_metrics_by_method.csv",
        "results/failure_taxonomy_counts.csv",
        "results/method_deltas_vs_bodyshield.csv",
    }
    missing_checks = sorted(required_checks - checks)
    missing_artifacts = sorted(required_artifacts - artifacts)
    if not rows or bad or missing_checks or missing_artifacts or not report_ok:
        return _fail(
            "derived_results_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; missing_artifacts={missing_artifacts}; report_ok={report_ok}",
        )
    return _ok("derived_results_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; derived tables recompute from primary trials")


def check_artifact_inventory_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "artifact_inventory_audit.csv"
    report_path = root / "reports" / "ARTIFACT_INVENTORY_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "artifact_manifest_exact_current_generated_set",
        "artifact_manifest_hashes_match_current_files",
        "release_manifest_exact_current_payload_set",
        "release_manifest_hashes_match_current_files",
        "documented_output_exists_nonempty",
        "documented_output_in_artifact_manifest_when_eligible",
        "documented_output_in_release_manifest_when_eligible",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "artifact_inventory_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("artifact_inventory_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; documented outputs and manifests are synchronized")


def check_paper_source_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "paper_source_audit.csv"
    report_path = root / "reports" / "PAPER_SOURCE_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "tex_citations_resolve",
        "tex_bibliography_files_resolve",
        "tex_refs_resolve",
        "tex_local_paths_resolve",
        "tex_boundary_terms_present",
        "paper_build_status_written",
        "paper_build_log_clean",
        "pdf_readable_pages",
        "pdf_boundary_terms_present",
        "pdf_matches_build_output",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "paper_source_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("paper_source_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; paper source/build/PDF links pass integrity checks")


def check_portable_hygiene_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "portable_hygiene_audit.csv"
    report_path = root / "reports" / "PORTABLE_HYGIENE_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "local_absolute_paths_absent",
        "temporary_extract_paths_absent",
        "release_manifest_paths_relative_safe",
        "pack_side_dynamic_outputs_excluded",
        "release_zip_entries_relative_safe",
        "release_zip_text_hygiene",
        "release_zip_excludes_pack_side_dynamic_outputs",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "portable_hygiene_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("portable_hygiene_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; text and release ZIP hygiene pass")


def check_config_schema_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "config_schema_audit.csv"
    report_path = root / "reports" / "CONFIG_SCHEMA_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "pyproject_required_dependencies_declared",
        "data_schema_required_perturbation_keys",
        "trial_json_schema_matches_code_constant",
        "phase_ids_match_expected",
        "hardware_safety_phase_requires_confirmation",
        "simulation_methods_match_policies",
        "simulation_perturbation_axes_cover_code",
        "hardware_config_safety_gated",
        "readiness_spec_loader_accepts",
        "readiness_spec_boundary_present",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "config_schema_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("config_schema_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; config and schema contracts pass")


def check_claim_boundary_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "claim_boundary_audit.csv"
    report_path = root / "reports" / "CLAIM_BOUNDARY_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "required_boundary_phrase",
        "required_pdf_boundary_phrase",
        "required_statuses",
        "forbidden_overclaim_phrases",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "claim_boundary_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("claim_boundary_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; claim boundaries preserved")


def check_command_surface_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "command_surface_audit.csv"
    report_path = root / "reports" / "COMMAND_SURFACE_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "document_has_python_commands",
        "script_exists_nonempty",
        "script_py_compile",
        "script_has_main_guard",
        "script_help_callable",
        "primary_command_set_matches",
        "release_command_set_contains_required",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "command_surface_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    commands = sorted({row.get("command", "") for row in rows if row.get("command", "")})
    return _ok("command_surface_audit", f"checks={len(rows)}; commands={len(commands)}; documented commands callable and synchronized")


def check_visual_artifact_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "visual_artifact_audit.csv"
    report_path = root / "reports" / "VISUAL_ARTIFACT_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "figure_stems_match_expected",
        "pdf_png_pair_exists",
        "pdf_readable",
        "png_nonblank_variance",
        "caption_figure_paths_match_expected",
        "gif_frame_count_matches_manifest",
        "gif_has_motion",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "visual_artifact_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("visual_artifact_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; figures and GIF media pass integrity checks")


def check_release_payload_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "release_payload_audit.csv"
    report_path = root / "reports" / "RELEASE_PAYLOAD_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "release_zip_exists_nonempty",
        "zip_extracts_safely",
        "bundled_verifier_exists_nonempty",
        "bundled_verifier_json_status",
        "extracted_payload_file_count_matches_pack_inspection",
        "extracted_payload_bytes_match_pack_inspection",
        "full_pack_manifest_boundary_documented",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "release_payload_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("release_payload_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; extracted payload verifier passes")


def check_release_determinism_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "release_determinism_audit.csv"
    report_path = root / "reports" / "RELEASE_DETERMINISM_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "release_control_files_exist",
        "pack_side_dynamic_outputs_excluded",
        "current_payload_hashes_match_manifest",
        "zip_entry_order_matches_manifest",
        "zip_fixed_timestamps",
        "zip_fixed_external_attr",
        "reconstructed_zip_sha256_matches",
        "reconstructed_zip_bytes_match",
        "checksums_file_matches_release_files",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "release_determinism_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("release_determinism_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; release ZIP bytes are reproducible")


def check_release_runtime_audit(root: Path) -> VerificationCheck:
    csv_path = root / "results" / "release_runtime_audit.csv"
    report_path = root / "reports" / "RELEASE_RUNTIME_AUDIT.md"
    rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8"))) if csv_path.exists() else []
    bad = [row for row in rows if row.get("status") != "pass"]
    checks = {row.get("check", "") for row in rows}
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.exists() else ""
    report_ok = "Status: `pass`" in report_text and "failed | 0" in report_text
    required_checks = {
        "release_zip_exists_nonempty",
        "zip_extracts_safely",
        "extracted_tests_present",
        "extracted_pytest_returncode",
        "extracted_pytest_passed_count",
        "temporary_runtime_extraction_cleaned",
    }
    missing_checks = sorted(required_checks - checks)
    if not rows or bad or missing_checks or not report_ok:
        return _fail(
            "release_runtime_audit",
            f"rows={len(rows)}; bad={bad[:12]}; missing_checks={missing_checks}; report_ok={report_ok}",
        )
    passed_counts = [int(row.get("observed", "0")) for row in rows if row.get("check") == "extracted_pytest_passed_count" and str(row.get("observed", "")).isdigit()]
    artifacts = sorted({row.get("artifact", "") for row in rows})
    return _ok("release_runtime_audit", f"checks={len(rows)}; artifacts={len(artifacts)}; extracted pytest passed={passed_counts[0] if passed_counts else 'unknown'}")


def run_pack_verification(root: Path | str = ".") -> list[VerificationCheck]:
    root = Path(root).resolve()
    return [
        check_required_artifacts(root),
        check_manifest(root),
        check_pdf(root),
        check_paper_build_log(root),
        check_gifs(root),
        check_video_manifest(root),
        check_external_policy_readiness(root),
        check_real_video_wam_readiness(root),
        check_corrective_trace_readiness(root),
        check_release_bundle(root),
        check_evidence_consistency(root),
        check_environment_dependency_audit(root),
        check_config_schema_audit(root),
        check_derived_results_audit(root),
        check_results_integrity_audit(root),
        check_source_import_audit(root),
        check_artifact_inventory_audit(root),
        check_paper_source_audit(root),
        check_portable_hygiene_audit(root),
        check_claim_boundary_audit(root),
        check_command_surface_audit(root),
        check_visual_artifact_audit(root),
        check_release_payload_audit(root),
        check_release_determinism_audit(root),
        check_release_runtime_audit(root),
        check_stale_phrases(root),
    ]


def verification_payload(root: Path | str = ".") -> dict[str, Any]:
    root = Path(root).resolve()
    checks = run_pack_verification(root)
    return {
        "status": "pass" if all(check.status == "pass" for check in checks) else "fail",
        "code_version": tree_hash(root),
        "checks": [asdict(check) for check in checks],
        "manifest_note": "PACK_VERIFICATION, ARTIFACT_INVENTORY_AUDIT, PORTABLE_HYGIENE_AUDIT, RELEASE_PAYLOAD_AUDIT, RELEASE_DETERMINISM_AUDIT, and RELEASE_RUNTIME_AUDIT reports are excluded from ARTIFACT_MANIFEST to avoid self-referential hash churn.",
    }


def write_verification_reports(root: Path | str = ".") -> dict[str, Any]:
    root = Path(root).resolve()
    payload = verification_payload(root)
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "PACK_VERIFICATION.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    rows = "\n".join(
        f"| {check['name']} | {check['status']} | {check['detail']} |" for check in payload["checks"]
    )
    (reports / "PACK_VERIFICATION.md").write_text(
        f"""# Pack Verification

Status: `{payload['status']}`

Code version: `{payload['code_version']}`

{payload['manifest_note']}

| check | status | detail |
|---|---|---|
{rows}
""",
        encoding="utf-8",
    )
    return payload
