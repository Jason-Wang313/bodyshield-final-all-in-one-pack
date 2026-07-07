"""Source-tree compile/import audit for the local non-hardware pack."""

from __future__ import annotations

import ast
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd


SOURCE_ROOTS: tuple[str, ...] = ("bodyshield", "scripts", "tests")
SKIP_PARTS: tuple[str, ...] = ("__pycache__", ".pytest_cache", "tmp", "release", "build")
HARDWARE_STUBS: tuple[str, ...] = (
    "bodyshield/safe_robot_runner.py",
    "bodyshield/robot/healthcheck.py",
    "bodyshield/robot/safety_gate.py",
    "bodyshield/robot/run_batch.py",
)
RAW_HARDWARE_TOKENS: tuple[str, ...] = (
    "serial.Serial(",
    "socket.socket(",
    "requests.post(",
    "requests.put(",
    "urllib.request.urlopen(",
    "movej(",
    "movel(",
    "set_servo_angle(",
    "write_register(",
    "write_goal_position(",
)


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


def _has_skipped_part(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def iter_python_files(root: Path | str, source_roots: Iterable[str] = SOURCE_ROOTS) -> list[Path]:
    root_path = Path(root).resolve()
    files: list[Path] = []
    for rel_root in source_roots:
        base = root_path / rel_root
        if not base.exists():
            continue
        paths = [base] if base.is_file() else base.rglob("*.py")
        files.extend(path for path in paths if path.is_file() and not _has_skipped_part(path))
    return sorted(set(files))


def module_name_from_path(path: Path, root: Path | str) -> str | None:
    root_path = Path(root).resolve()
    package_root = root_path / "bodyshield"
    try:
        rel = path.resolve().relative_to(package_root)
    except ValueError:
        return None
    if path.suffix != ".py":
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(("bodyshield", *parts))


def _compile_rows(root: Path, python_files: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in python_files:
        rel_path = _rel(path, root)
        try:
            py_compile.compile(str(path), doraise=True)
            rows.append(_pass(rel_path, "python_file_py_compile", "Python source compiles"))
        except py_compile.PyCompileError as exc:
            rows.append(_fail(rel_path, "python_file_py_compile", f"compile failed: {exc}"))
    return rows


def _script_guard_rows(root: Path, python_files: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    scripts_root = root / "scripts"
    for path in python_files:
        try:
            path.resolve().relative_to(scripts_root)
        except ValueError:
            continue
        rel_path = _rel(path, root)
        text = path.read_text(encoding="utf-8", errors="ignore")
        has_guard = 'if __name__ == "__main__"' in text
        rows.append(
            _row(
                rel_path,
                "script_has_main_guard",
                "pass" if has_guard else "fail",
                "script has a guarded CLI entry point",
            )
        )
    return rows


def _import_subprocess_rows(root: Path, modules: list[str], timeout_s: int) -> list[dict[str, str]]:
    if not modules:
        return [_fail("bodyshield", "bodyshield_module_imports_in_subprocess", "no bodyshield modules discovered")]

    code = r"""
import contextlib
import importlib
import io
import json
import sys
import traceback

modules = json.loads(sys.argv[1])
rows = []
for module in modules:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            importlib.import_module(module)
        rows.append(
            {
                "module": module,
                "status": "pass",
                "detail": "module imported",
                "observed": "",
            }
        )
    except BaseException as exc:
        captured = (stdout_capture.getvalue() + "\n" + stderr_capture.getvalue()).strip()
        detail = f"{type(exc).__name__}: {exc}"
        if captured:
            detail = detail + "; captured_output=" + captured[:500]
        rows.append(
            {
                "module": module,
                "status": "fail",
                "detail": detail,
                "observed": traceback.format_exc(limit=4)[-1000:],
            }
        )
print(json.dumps(rows))
sys.exit(0 if all(row["status"] == "pass" for row in rows) else 1)
""".strip()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        completed = subprocess.run(
            [sys.executable, "-c", code, json.dumps(modules)],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [
            _fail(
                "bodyshield",
                "bodyshield_module_imports_in_subprocess",
                "import subprocess timed out",
                observed=f">{timeout_s}s",
                expected=f"<={timeout_s}s",
            )
        ]

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = (completed.stdout + "\n" + completed.stderr).strip()[:1000]
        return [
            _fail(
                "bodyshield",
                "bodyshield_module_imports_in_subprocess",
                "import subprocess did not return valid JSON",
                observed=f"returncode={completed.returncode}; output={detail}",
                expected="valid JSON rows",
            )
        ]

    rows: list[dict[str, str]] = []
    for item in payload:
        module = str(item.get("module", ""))
        status = "pass" if item.get("status") == "pass" else "fail"
        rows.append(
            _row(
                module,
                "bodyshield_module_imports_in_subprocess",
                status,
                str(item.get("detail", "")),
                str(item.get("observed", "")),
                "import succeeds",
            )
        )
    return rows


def _raises_safety_violation(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Raise) or child.exc is None:
            continue
        exc = child.exc
        if isinstance(exc, ast.Call):
            exc = exc.func
        if isinstance(exc, ast.Name) and exc.id == "SafetyViolation":
            return True
        if isinstance(exc, ast.Attribute) and exc.attr == "SafetyViolation":
            return True
    return False


def _safe_robot_runner_rows(path: Path, root: Path) -> list[dict[str, str]]:
    rel_path = _rel(path, root)
    rows: list[dict[str, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
    except SyntaxError as exc:
        return [_fail(rel_path, "safe_robot_api_methods_raise_safety_violation", f"could not parse AST: {exc}")]

    missing: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "SafeRobot":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name != "__init__" and not _raises_safety_violation(child):
                    missing.append(f"SafeRobot.{child.name}")
        if isinstance(node, ast.FunctionDef) and node.name == "run_batch" and not _raises_safety_violation(node):
            missing.append("run_batch")
    rows.append(
        _row(
            rel_path,
            "safe_robot_api_methods_raise_safety_violation",
            "pass" if not missing else "fail",
            f"missing safety raises: {missing}" if missing else "safe robot API entry points refuse with SafetyViolation",
            observed=",".join(missing),
            expected="no missing SafetyViolation raises",
        )
    )
    return rows


def _hardware_stub_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rel_path in HARDWARE_STUBS:
        path = root / rel_path
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(rel_path, "hardware_stub_exists_nonempty", "hardware stub is missing or empty"))
            continue
        rows.append(_pass(rel_path, "hardware_stub_exists_nonempty", "hardware stub exists and is nonempty"))
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        boundary_ok = "safety" in lower and any(
            term in lower for term in ("confirmation", "refusing", "refuses", "not enabled", "not confirmed")
        )
        rows.append(
            _row(
                rel_path,
                "hardware_stub_refusal_boundary_present",
                "pass" if boundary_ok else "fail",
                "hardware stub contains explicit safety/refusal boundary wording",
                expected="safety plus refusal/confirmation wording",
            )
        )
        forbidden_hits = [token for token in RAW_HARDWARE_TOKENS if token in text]
        rows.append(
            _row(
                rel_path,
                "hardware_stub_forbidden_raw_io_absent",
                "pass" if not forbidden_hits else "fail",
                f"raw hardware/network I/O tokens found: {forbidden_hits}" if forbidden_hits else "no raw hardware/network I/O tokens found",
                observed=",".join(forbidden_hits),
                expected="no forbidden tokens",
            )
        )
        if "def main(" in text:
            has_guard = 'if __name__ == "__main__"' in text
            rows.append(
                _row(
                    rel_path,
                    "hardware_stub_cli_guard_present",
                    "pass" if has_guard else "fail",
                    "hardware stub CLI entry point is guarded",
                )
            )
        else:
            rows.append(_pass(rel_path, "hardware_stub_cli_guard_present", "hardware stub is not a CLI module"))
        if rel_path == "bodyshield/safe_robot_runner.py":
            rows.extend(_safe_robot_runner_rows(path, root))
    return rows


def _discovery_rows(root: Path, python_files: list[Path], modules: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rel_root in SOURCE_ROOTS:
        path = root / rel_root
        exists = path.exists() and path.is_dir()
        rows.append(
            _row(
                rel_root,
                "source_root_exists",
                "pass" if exists else "fail",
                "source root exists",
                observed=str(exists),
                expected="True",
            )
        )
        count = sum(1 for file_path in python_files if file_path.resolve().is_relative_to(path.resolve())) if exists else 0
        rows.append(
            _row(
                rel_root,
                "source_python_files_discovered",
                "pass" if count > 0 else "fail",
                "Python source files discovered under root",
                observed=str(count),
                expected=">0",
            )
        )
    rows.append(
        _row(
            "bodyshield",
            "bodyshield_modules_discovered",
            "pass" if modules else "fail",
            "importable bodyshield modules discovered",
            observed=str(len(modules)),
            expected=">0",
        )
    )
    return rows


def run_source_import_audit(root: Path | str = ".", timeout_s: int = 60) -> pd.DataFrame:
    root_path = Path(root).resolve()
    python_files = iter_python_files(root_path)
    modules = sorted({module for path in python_files if (module := module_name_from_path(path, root_path))})
    rows: list[dict[str, str]] = []
    rows.extend(_discovery_rows(root_path, python_files, modules))
    rows.extend(_compile_rows(root_path, python_files))
    rows.extend(_script_guard_rows(root_path, python_files))
    rows.extend(_import_subprocess_rows(root_path, modules, timeout_s))
    rows.extend(_hardware_stub_rows(root_path))
    return pd.DataFrame(rows)


def source_import_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_source_import_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_source_import_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = source_import_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_source_import_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Source Import Audit

Status: `{status}`

This audit checks that every shipped Python source file under `bodyshield/`, `scripts/`, and `tests/` compiles; every script has a guarded CLI entry point; every `bodyshield.*` module imports in a fresh subprocess; and hardware-facing stubs remain refusal-only without raw hardware or network I/O tokens.

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


def write_source_import_audit_reports(root: Path | str = ".", timeout_s: int = 60) -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_source_import_audit(root_path, timeout_s=timeout_s)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "source_import_audit.csv", index=False)
    write_source_import_report(reports / "SOURCE_IMPORT_AUDIT.md", rows)
    return rows
