"""Portable-release hygiene checks for local path leakage and dynamic artifacts."""

from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path

import pandas as pd

from bodyshield.release_bundle import BUNDLE_NAME, MANIFEST_NAME


TEXT_SUFFIXES: tuple[str, ...] = (
    ".bib",
    ".csv",
    ".json",
    ".md",
    ".py",
    ".schema",
    ".tex",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
)
TEXT_ROOTS: tuple[str, ...] = ("bodyshield", "configs", "paper", "reports", "results", "scripts", "tests", "release")
ROOT_TEXT_FILES: tuple[str, ...] = (
    "README_EXECUTION.md",
    "README_FIRST.md",
    "pyproject.toml",
    "data_schema.json",
    "trial_schema.schema.json",
)
SKIP_PARTS: tuple[str, ...] = ("__pycache__", ".pytest_cache", "tmp", "build")
PACK_SIDE_DYNAMIC_OUTPUTS: tuple[str, ...] = (
    "reports/ARTIFACT_MANIFEST.csv",
    "reports/ARTIFACT_MANIFEST.md",
    "reports/PACK_VERIFICATION.json",
    "reports/PACK_VERIFICATION.md",
    "reports/PORTABLE_HYGIENE_AUDIT.md",
    "reports/RELEASE_DETERMINISM_AUDIT.md",
    "reports/RELEASE_PAYLOAD_AUDIT.md",
    "reports/RELEASE_RUNTIME_AUDIT.md",
    "results/portable_hygiene_audit.csv",
    "results/release_determinism_audit.csv",
    "results/release_payload_audit.csv",
    "results/release_runtime_audit.csv",
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


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _text_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for rel in ROOT_TEXT_FILES:
        path = root / rel
        if path.exists() and path.is_file():
            paths.append(path)
    for rel_root in TEXT_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(root).parts
            if path.relative_to(root).as_posix() in PACK_SIDE_DYNAMIC_OUTPUTS:
                continue
            if any(part in SKIP_PARTS for part in rel_parts):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES or path.name in {MANIFEST_NAME, "RELEASE_README.md"}:
                paths.append(path)
    return sorted(set(paths))


def _local_path_needles(root: Path) -> tuple[str, ...]:
    needles: list[str] = []
    for path in (root, Path.home()):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        for raw in (str(resolved), resolved.as_posix()):
            if raw and len(raw) > 4:
                needles.append(raw)
    return tuple(sorted(set(needles), key=len, reverse=True))


def _absolute_path_hits(text: str, root: Path) -> list[str]:
    hits = [needle for needle in _local_path_needles(root) if needle in text]
    regexes = (
        re.compile(r"[A-Za-z]:[\\/]+Users[\\/][A-Za-z0-9_.-]+"),
        re.compile(r"/home/[A-Za-z0-9_.-]+"),
        re.compile(r"/Users/[A-Za-z0-9_.-]+"),
    )
    for pattern in regexes:
        hits.extend(match.group(0) for match in pattern.finditer(text))
    return sorted(set(hits))


def _temp_markers() -> tuple[str, ...]:
    underscore = "_"
    return (
        "release" + underscore + "extract" + underscore,
        "bodyshield" + underscore + "release" + underscore + "payload" + underscore,
        "bodyshield" + underscore + "release" + underscore + "runtime" + underscore,
    )


def _temp_marker_hits(text: str) -> list[str]:
    hits: list[str] = []
    for marker in _temp_markers():
        pattern = re.compile(re.escape(marker) + r"[A-Za-z0-9_.-]{4,}")
        hits.extend(match.group(0) for match in pattern.finditer(text))
    return sorted(set(hits))


def _text_scan_rows(root: Path) -> list[dict[str, str]]:
    files = _text_files(root)
    path_hits: list[str] = []
    temp_hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = _safe_rel(path, root)
        for hit in _absolute_path_hits(text, root):
            path_hits.append(f"{rel}:{hit}")
        for marker in _temp_marker_hits(text):
            temp_hits.append(f"{rel}:{marker}")
    return [
        _row(
            "pack_text_files",
            "text_files_scanned",
            "pass" if files else "fail",
            "portable hygiene text scan found files",
            str(len(files)),
            ">0",
        ),
        _row(
            "pack_text_files",
            "local_absolute_paths_absent",
            "pass" if not path_hits else "fail",
            f"local absolute path hits={path_hits[:12]}",
            str(len(path_hits)),
            "0",
        ),
        _row(
            "pack_text_files",
            "temporary_extract_paths_absent",
            "pass" if not temp_hits else "fail",
            f"temporary extraction marker hits={temp_hits[:12]}",
            str(len(temp_hits)),
            "0",
        ),
    ]


def _specific_redaction_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rel in (
        "reports/PAPER_BUILD_LOG.txt",
        "reports/ENVIRONMENT_DEPENDENCY_AUDIT.md",
        "results/environment_dependency_audit.csv",
        "results/environment_snapshot.json",
    ):
        path = root / rel
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(rel, "redacted_artifact_exists_nonempty", "expected redacted artifact is missing or empty"))
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits = _absolute_path_hits(text, root)
        rows.append(
            _row(
                rel,
                "local_paths_redacted",
                "pass" if not hits else "fail",
                f"local absolute path hits={hits[:12]}",
                str(len(hits)),
                "0",
            )
        )
    return rows


def _release_manifest_rows(root: Path) -> list[dict[str, str]]:
    manifest = root / "release" / MANIFEST_NAME
    rel = f"release/{MANIFEST_NAME}"
    if not manifest.exists() or manifest.stat().st_size <= 0:
        return [_fail(rel, "release_manifest_exists_nonempty", "release manifest missing or empty")]
    rows = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))
    paths = [row.get("path", "") for row in rows]
    unsafe = sorted(path for path in paths if not path or "\\" in path or path.startswith("/") or path.startswith("../") or "/../" in path)
    dynamic_present = sorted(path for path in paths if path in PACK_SIDE_DYNAMIC_OUTPUTS)
    return [
        _row(
            rel,
            "release_manifest_paths_relative_safe",
            "pass" if rows and not unsafe else "fail",
            f"unsafe manifest paths={unsafe[:12]}",
            str(len(rows)),
            ">0 rows; no unsafe paths",
        ),
        _row(
            rel,
            "pack_side_dynamic_outputs_excluded",
            "pass" if not dynamic_present else "fail",
            f"pack-side dynamic outputs present={dynamic_present}",
            str(len(dynamic_present)),
            "0",
        ),
    ]


def _release_zip_rows(root: Path) -> list[dict[str, str]]:
    zip_path = root / "release" / BUNDLE_NAME
    rel = f"release/{BUNDLE_NAME}"
    if not zip_path.exists() or zip_path.stat().st_size <= 0:
        return [_fail(rel, "release_zip_exists_nonempty", "release ZIP missing or empty")]
    rows: list[dict[str, str]] = [
        _pass(rel, "release_zip_exists_nonempty", "release ZIP exists and is nonempty", str(zip_path.stat().st_size), ">0 bytes")
    ]
    path_hits: list[str] = []
    temp_hits: list[str] = []
    unsafe_entries: list[str] = []
    dynamic_entries: list[str] = []
    text_entries = 0
    try:
        with zipfile.ZipFile(zip_path) as bundle:
            for info in bundle.infolist():
                name = info.filename
                if not name or "\\" in name or name.startswith("/") or name.startswith("../") or "/../" in name:
                    unsafe_entries.append(name)
                if any(part in name.split("/") for part in SKIP_PARTS):
                    unsafe_entries.append(name)
                if name in PACK_SIDE_DYNAMIC_OUTPUTS:
                    dynamic_entries.append(name)
                suffix = Path(name).suffix.lower()
                if suffix not in TEXT_SUFFIXES and Path(name).name not in {MANIFEST_NAME, "RELEASE_README.md"}:
                    continue
                text_entries += 1
                text = bundle.read(name).decode("utf-8", errors="ignore")
                for hit in _absolute_path_hits(text, root):
                    path_hits.append(f"{name}:{hit}")
                for marker in _temp_marker_hits(text):
                    temp_hits.append(f"{name}:{marker}")
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return rows + [_fail(rel, "release_zip_readable", f"could not inspect release ZIP: {exc}")]

    rows.append(_pass(rel, "release_zip_readable", "release ZIP opens for hygiene inspection"))
    rows.append(
        _row(
            rel,
            "release_zip_entries_relative_safe",
            "pass" if not unsafe_entries else "fail",
            f"unsafe ZIP entries={unsafe_entries[:12]}",
            str(len(unsafe_entries)),
            "0",
        )
    )
    rows.append(
        _row(
            rel,
            "release_zip_text_hygiene",
            "pass" if text_entries > 0 and not path_hits and not temp_hits else "fail",
            f"text_entries={text_entries}; local_path_hits={path_hits[:12]}; temp_hits={temp_hits[:12]}",
            f"path_hits={len(path_hits)}; temp_hits={len(temp_hits)}",
            "0",
        )
    )
    rows.append(
        _row(
            rel,
            "release_zip_excludes_pack_side_dynamic_outputs",
            "pass" if not dynamic_entries else "fail",
            f"dynamic output entries present={dynamic_entries}",
            str(len(dynamic_entries)),
            "0",
        )
    )
    return rows


def run_portable_hygiene_audit(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    rows.extend(_text_scan_rows(root_path))
    rows.extend(_specific_redaction_rows(root_path))
    rows.extend(_release_manifest_rows(root_path))
    rows.extend(_release_zip_rows(root_path))
    return pd.DataFrame(rows)


def portable_hygiene_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_portable_hygiene_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_portable_hygiene_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = portable_hygiene_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_portable_hygiene_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Portable Hygiene Audit

Status: `{status}`

This pack-side audit scans text artifacts and the final release ZIP for local absolute path leakage, temporary extraction traces, unsafe archive paths, and accidental inclusion of self-referential dynamic verifier outputs.

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


def write_portable_hygiene_audit_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_portable_hygiene_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "portable_hygiene_audit.csv", index=False)
    write_portable_hygiene_report(reports / "PORTABLE_HYGIENE_AUDIT.md", rows)
    return rows
