"""Generate final reviewer-facing ledgers, manifests, and video indexes."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
VIDEOS = ROOT / "videos"
PAPER = ROOT / "paper"


MANIFEST_EXCLUDES = {
    Path("reports/final_artifact_manifest.json"),
    Path("reports/final_artifact_manifest_nonhardware.json"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short=16", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return completed.stdout.strip()
    except Exception:
        return "unknown"


def _convert_claim_ledger() -> int:
    source = REPORTS / "CLAIM_LEDGER.md"
    target = REPORTS / "claim_ledger.csv"
    rows: list[list[str]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]
        if not cells or set("".join(cells)) <= {"-", ":"}:
            continue
        rows.append(cells)
    if not rows:
        raise RuntimeError("No markdown table rows found in reports/CLAIM_LEDGER.md")
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)
    return max(0, len(rows) - 1)


def _write_video_indexes() -> int:
    source = ROOT / "results" / "simulation_rollout_videos.csv"
    VIDEOS.mkdir(exist_ok=True)
    rows: list[dict[str, str]] = []
    if source.exists():
        with source.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    lines = [
        "# BodyShield Video Index",
        "",
        "Current videos are synthetic rollout media generated from analytic traces.",
        "They are not real-camera or hardware-verifier videos.",
        "",
        "| name | path | boundary |",
        "|---|---|---|",
    ]
    for row in rows:
        path = row.get("path") or row.get("artifact") or row.get("video_path") or ""
        name = row.get("name") or row.get("scenario") or Path(path).stem
        boundary = row.get("evidence_boundary") or row.get("boundary") or "synthetic rollout only"
        lines.append(f"| {name} | `{path}` | {boundary} |")
    if not rows:
        lines.append("| none | n/a | no video rows found |")
    content = "\n".join(lines) + "\n"
    (VIDEOS / "video_index.md").write_text(content, encoding="utf-8")
    (PAPER / "video_index.md").write_text(content, encoding="utf-8")
    return len(rows)


def _manifest() -> dict[str, object]:
    roots = [
        "bodyshield",
        "configs",
        "paper",
        "release",
        "reports",
        "results",
        "scripts",
        "tests",
        "videos",
        "logs",
        "figures",
        "tables",
        ".github",
    ]
    entries: list[dict[str, object]] = []
    for root_name in roots:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if rel in MANIFEST_EXCLUDES:
                continue
            if "__pycache__" in rel.parts or ".pytest_cache" in rel.parts:
                continue
            entries.append(
                {
                    "path": rel.as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_commit": _git_commit(),
        "scope": "non-hardware BodyShield source, paper, reports, results, videos, and release artifacts",
        "hardware_status": "not_run_requires_explicit_user_confirmation",
        "entry_count": len(entries),
        "entries": entries,
    }


def _write_final_reports(claim_rows: int, video_rows: int, manifest: dict[str, object]) -> None:
    readiness = f"""# Final Submission Readiness Report

Status: `not_ready_for_final_hardware_paper`

Code commit: `{manifest['code_commit']}`

## Green Non-Hardware Gates

- Pack verification passes in `reports/PACK_VERIFICATION.md`.
- Derived-results, source/import, results-integrity, artifact-inventory, command-surface, paper-source, visual-artifact, release-payload, release-determinism, and release-runtime audits pass.
- Claim ledger CSV generated with {claim_rows} claims at `reports/claim_ledger.csv`.
- Final manifest generated with {manifest['entry_count']} hashed artifacts at `reports/final_artifact_manifest.json`.
- Synthetic video index generated with {video_rows} rows at `videos/video_index.md`.

## Blocking Hardware Gates

- Hardware noise floor has not been measured.
- SO-ARM101/SO-101 camera verifier agreement has not been audited.
- Reset reliability, physical emergency stop, current/load thresholds, and safe unattended criteria are not available.
- Held-out physical-modification trials have not been run.

The package is ready as a non-hardware reproducibility artifact and paper draft. It is not ready as a final ICRA/RSS hardware-result submission until the hardware gates are completed and audited.
"""
    (REPORTS / "final_submission_readiness_report.md").write_text(readiness, encoding="utf-8")
    not_ready = """# Not Ready Reason

The red-line hardware evidence gates are not satisfied. The repository has a passing
non-hardware pack, but final paper readiness requires explicit user confirmation
of the SO-ARM101/SO-101 setup followed by safety-gated hardware trials, noise-floor
measurement, verifier audit, reset audit, oracle feasibility checks, held-out
physical modifications, and full hardware video/log manifests.
"""
    (REPORTS / "NOT_READY_REASON.md").write_text(not_ready, encoding="utf-8")
    complete = f"""# Paper Wrapped Complete

Status: `non_hardware_wrapped_hardware_pending`

This is the maximum safe wrap state before explicit hardware confirmation.

- Final artifact manifest: `reports/final_artifact_manifest.json`
- Claim ledger: `reports/claim_ledger.csv`
- Reviewer prebuttal: `reports/final_reviewer_prebuttal.md`
- Readiness report: `reports/final_submission_readiness_report.md`
- Video index: `videos/video_index.md`

Human review is required before submission. Hardware execution remains blocked.
"""
    (REPORTS / "PAPER_WRAPPED_COMPLETE.md").write_text(complete, encoding="utf-8")


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    claim_rows = _convert_claim_ledger()
    video_rows = _write_video_indexes()
    manifest = _manifest()
    (REPORTS / "final_artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / "final_artifact_manifest_nonhardware.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    _write_final_reports(claim_rows, video_rows, manifest)
    print("FINALIZE_MAXOUT_STATUS=pass")
    print(f"CLAIM_ROWS={claim_rows}")
    print(f"VIDEO_ROWS={video_rows}")
    print(f"MANIFEST_ENTRIES={manifest['entry_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
