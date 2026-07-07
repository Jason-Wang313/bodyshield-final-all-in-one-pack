"""Audit documented command entry points for the local non-hardware pack."""

from __future__ import annotations

import py_compile
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


COMMAND_PATTERN = re.compile(r"^\s*python(?:\.exe)?\s+(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

COMMAND_DOCUMENTS: tuple[str, ...] = (
    "README_EXECUTION.md",
    "reports/REPRODUCIBILITY_MANIFEST.md",
    "release/RELEASE_README.md",
)

PRIMARY_EXPECTED_COMMANDS: tuple[str, ...] = (
    "python -m pytest -q",
    "python scripts/run_external_policy_benchmark.py",
    "python scripts/run_real_video_wam_readiness.py",
    "python scripts/run_corrective_trace_readiness.py",
    "python scripts/run_artifact_inventory_audit.py",
    "python scripts/run_claim_boundary_audit.py",
    "python scripts/run_command_surface_audit.py",
    "python scripts/run_config_schema_audit.py",
    "python scripts/run_derived_results_audit.py",
    "python scripts/run_environment_dependency_audit.py",
    "python scripts/run_results_integrity_audit.py",
    "python scripts/run_source_import_audit.py",
    "python scripts/run_paper_source_audit.py",
    "python scripts/run_portable_hygiene_audit.py",
    "python scripts/run_visual_artifact_audit.py",
    "python scripts/run_release_payload_audit.py",
    "python scripts/run_release_determinism_audit.py",
    "python scripts/run_release_runtime_audit.py",
    "python scripts/run_evidence_consistency_audit.py",
    "python scripts/build_release_bundle.py",
    "python scripts/run_non_hardware.py",
    "python scripts/verify_non_hardware_pack.py --write-reports",
)

RELEASE_EXPECTED_COMMANDS: tuple[str, ...] = (
    "python scripts/verify_release_payload.py",
)

HELP_CALLABLE_SCRIPTS: tuple[str, ...] = (
    "scripts/build_release_bundle.py",
    "scripts/run_artifact_inventory_audit.py",
    "scripts/run_claim_boundary_audit.py",
    "scripts/run_command_surface_audit.py",
    "scripts/run_config_schema_audit.py",
    "scripts/run_derived_results_audit.py",
    "scripts/run_corrective_trace_readiness.py",
    "scripts/run_environment_dependency_audit.py",
    "scripts/run_evidence_consistency_audit.py",
    "scripts/run_external_policy_benchmark.py",
    "scripts/run_paper_source_audit.py",
    "scripts/run_portable_hygiene_audit.py",
    "scripts/run_real_video_wam_readiness.py",
    "scripts/run_release_determinism_audit.py",
    "scripts/run_release_payload_audit.py",
    "scripts/run_release_runtime_audit.py",
    "scripts/run_results_integrity_audit.py",
    "scripts/run_source_import_audit.py",
    "scripts/run_visual_artifact_audit.py",
    "scripts/verify_non_hardware_pack.py",
    "scripts/verify_release_payload.py",
)


@dataclass(frozen=True)
class ParsedCommand:
    document: str
    command: str
    normalized: str
    kind: str
    target: str


def normalize_command(command: str) -> str:
    return " ".join(command.replace("\\", "/").split())


def _row(
    document: str,
    command: str,
    check: str,
    status: str,
    detail: str,
    target: str = "",
    observed: str = "",
    expected: str = "",
) -> dict[str, str]:
    return {
        "document": document,
        "command": command,
        "target": target,
        "check": check,
        "status": status,
        "detail": detail,
        "observed": observed,
        "expected": expected,
    }


def _pass(
    document: str,
    command: str,
    check: str,
    detail: str,
    target: str = "",
    observed: str = "",
    expected: str = "",
) -> dict[str, str]:
    return _row(document, command, check, "pass", detail, target, observed, expected)


def _fail(
    document: str,
    command: str,
    check: str,
    detail: str,
    target: str = "",
    observed: str = "",
    expected: str = "",
) -> dict[str, str]:
    return _row(document, command, check, "fail", detail, target, observed, expected)


def parse_python_commands(text: str, document: str) -> list[ParsedCommand]:
    commands: list[ParsedCommand] = []
    for match in COMMAND_PATTERN.finditer(text):
        raw_command = f"python {match.group(1).strip()}"
        normalized = normalize_command(raw_command)
        parts = normalized.split()
        kind = "unknown"
        target = ""
        if len(parts) >= 3 and parts[1] == "-m":
            kind = "module"
            target = parts[2]
        elif len(parts) >= 2 and parts[1].startswith("scripts/"):
            kind = "script"
            target = parts[1]
        commands.append(ParsedCommand(document, raw_command, normalized, kind, target))
    return commands


def _read_document_commands(root: Path, documents: tuple[str, ...]) -> tuple[list[ParsedCommand], list[dict[str, str]]]:
    commands: list[ParsedCommand] = []
    rows: list[dict[str, str]] = []
    for rel_path in documents:
        path = root / rel_path
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(rel_path, "", "document_exists_nonempty", "command document is missing or empty"))
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        document_commands = parse_python_commands(text, rel_path)
        commands.extend(document_commands)
        rows.append(
            _row(
                rel_path,
                "",
                "document_has_python_commands",
                "pass" if document_commands else "fail",
                "document contains python command lines",
                observed=str(len(document_commands)),
                expected=">0",
            )
        )
    return commands, rows


def _command_rows(root: Path, commands: list[ParsedCommand], help_scripts: tuple[str, ...], timeout_s: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    help_script_set = set(help_scripts)
    for command in commands:
        if command.kind == "unknown":
            rows.append(_fail(command.document, command.normalized, "command_target_recognized", "command target is not a script or module"))
            continue
        rows.append(_pass(command.document, command.normalized, "command_target_recognized", "command target recognized", command.target))

        if command.kind == "module":
            if command.target == "pytest":
                tests_dir = root / "tests"
                rows.append(
                    _row(
                        command.document,
                        command.normalized,
                        "pytest_tests_dir_exists",
                        "pass" if tests_dir.exists() and any(tests_dir.glob("test_*.py")) else "fail",
                        "pytest command has local tests",
                        command.target,
                    )
                )
            else:
                rows.append(_pass(command.document, command.normalized, "module_command_deferred", "non-pytest module command is not executed by this audit", command.target))
            continue

        script_path = root / command.target
        if not script_path.exists() or script_path.stat().st_size <= 0:
            rows.append(_fail(command.document, command.normalized, "script_exists_nonempty", "script target missing or empty", command.target))
            continue
        rows.append(_pass(command.document, command.normalized, "script_exists_nonempty", "script target exists and is nonempty", command.target, str(script_path.stat().st_size), ">0 bytes"))

        try:
            py_compile.compile(str(script_path), doraise=True)
            rows.append(_pass(command.document, command.normalized, "script_py_compile", "script compiles", command.target))
        except py_compile.PyCompileError as exc:
            rows.append(_fail(command.document, command.normalized, "script_py_compile", f"script compile failed: {exc}", command.target))

        text = script_path.read_text(encoding="utf-8", errors="ignore")
        has_guard = 'if __name__ == "__main__"' in text
        rows.append(
            _row(
                command.document,
                command.normalized,
                "script_has_main_guard",
                "pass" if has_guard else "fail",
                "script has a guarded CLI entry point",
                command.target,
            )
        )

        if command.target in help_script_set:
            try:
                completed = subprocess.run(
                    [sys.executable, str(script_path), "--help"],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    timeout=timeout_s,
                    check=False,
                )
                output = (completed.stdout + "\n" + completed.stderr).strip()
                status = "pass" if completed.returncode == 0 and ("usage:" in output.lower() or "--help" in output.lower()) else "fail"
                rows.append(
                    _row(
                        command.document,
                        command.normalized,
                        "script_help_callable",
                        status,
                        "script --help exits successfully",
                        command.target,
                        f"returncode={completed.returncode}",
                        "returncode=0",
                    )
                )
            except subprocess.TimeoutExpired:
                rows.append(_fail(command.document, command.normalized, "script_help_callable", "script --help timed out", command.target, f">{timeout_s}s"))
        else:
            rows.append(_pass(command.document, command.normalized, "script_help_not_required", "script is intentionally not help-probed by this audit", command.target))
    return rows


def _expected_command_rows(commands: list[ParsedCommand], expected_primary: tuple[str, ...], expected_release: tuple[str, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    by_document: dict[str, set[str]] = {}
    for command in commands:
        by_document.setdefault(command.document, set()).add(command.normalized)

    expected_primary_set = {normalize_command(command) for command in expected_primary}
    expected_release_set = {normalize_command(command) for command in expected_release}
    for document in ("README_EXECUTION.md", "reports/REPRODUCIBILITY_MANIFEST.md"):
        present = by_document.get(document, set())
        missing = sorted(expected_primary_set - present)
        extra = sorted(present - expected_primary_set)
        rows.append(
            _row(
                document,
                "",
                "primary_command_set_matches",
                "pass" if not missing else "fail",
                f"primary command set missing={missing}; extra_documented_commands={extra}",
                observed=str(len(present)),
                expected=str(len(expected_primary_set)),
            )
        )
    release_present = by_document.get("release/RELEASE_README.md", set())
    if release_present:
        missing_release = sorted(expected_release_set - release_present)
        rows.append(
            _row(
                "release/RELEASE_README.md",
                "",
                "release_command_set_contains_required",
                "pass" if not missing_release else "fail",
                f"release command set missing={missing_release}",
                observed=str(len(release_present)),
                expected=str(len(expected_release_set)),
            )
        )
    return rows


def run_command_surface_audit(
    root: Path | str = ".",
    documents: tuple[str, ...] = COMMAND_DOCUMENTS,
    expected_primary_commands: tuple[str, ...] = PRIMARY_EXPECTED_COMMANDS,
    expected_release_commands: tuple[str, ...] = RELEASE_EXPECTED_COMMANDS,
    help_scripts: tuple[str, ...] = HELP_CALLABLE_SCRIPTS,
    timeout_s: int = 20,
) -> pd.DataFrame:
    root_path = Path(root).resolve()
    commands, rows = _read_document_commands(root_path, documents)
    rows.extend(_command_rows(root_path, commands, help_scripts, timeout_s))
    rows.extend(_expected_command_rows(commands, expected_primary_commands, expected_release_commands))
    return pd.DataFrame(rows)


def command_surface_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "commands": 0, "documents": 0}
    statuses = rows["status"].astype(str)
    command_rows = rows[rows["command"].astype(str) != ""]
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "commands": int(command_rows["command"].nunique()),
        "documents": int(rows["document"].nunique()),
    }


def failed_command_surface_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_command_surface_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = command_surface_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_command_surface_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Command Surface Audit

Status: `{status}`

This audit checks that documented local commands remain synchronized across the README, reproducibility manifest, and release README; that referenced script targets exist, compile, expose guarded entry points, and that safe CLI scripts respond to `--help`.

| metric | value |
|---|---:|
| checks | {summary['checks']} |
| passed | {summary['passed']} |
| failed | {summary['failed']} |
| commands audited | {summary['commands']} |
| documents audited | {summary['documents']} |

## Display Rows

{body}
""",
        encoding="utf-8",
    )


def write_command_surface_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_command_surface_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "command_surface_audit.csv", index=False)
    write_command_surface_report(reports / "COMMAND_SURFACE_AUDIT.md", rows)
    return rows
