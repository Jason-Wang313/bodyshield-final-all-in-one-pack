"""Environment and dependency audit for the non-hardware pack."""

from __future__ import annotations

import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PYPROJECT_DEP_RE = re.compile(r'"([^"]+)"')


@dataclass(frozen=True)
class PythonPackageSpec:
    package: str
    import_name: str
    tier: str
    required: bool
    reason: str
    pyproject_name: str | None = None


@dataclass(frozen=True)
class SystemToolSpec:
    tool: str
    tier: str
    required: bool
    reason: str
    version_args: tuple[str, ...] = ("--version",)


PYTHON_PACKAGES: tuple[PythonPackageSpec, ...] = (
    PythonPackageSpec("numpy", "numpy", "core", True, "analytic simulation, models, and statistics"),
    PythonPackageSpec("pandas", "pandas", "core", True, "tables, reports, CSV/Parquet IO"),
    PythonPackageSpec("matplotlib", "matplotlib", "core", True, "generated figures"),
    PythonPackageSpec("pillow", "PIL", "core", True, "GIF/video and image validation", "pillow"),
    PythonPackageSpec("pypdf", "pypdf", "core", True, "PDF structure verification"),
    PythonPackageSpec("pyyaml", "yaml", "core", True, "YAML config compatibility", "pyyaml"),
    PythonPackageSpec("pyarrow", "pyarrow", "output_format", True, "pandas Parquet output"),
    PythonPackageSpec("tabulate", "tabulate", "output_format", True, "pandas markdown table output"),
    PythonPackageSpec("pytest", "pytest", "test", True, "documented test command"),
    PythonPackageSpec("mujoco", "mujoco", "bounded_simulator", True, "bounded MuJoCo probe tier"),
    PythonPackageSpec("mani-skill", "mani_skill", "bounded_simulator", True, "bounded ManiSkill probe tier", "mani-skill"),
    PythonPackageSpec("gymnasium", "gymnasium", "bounded_simulator", True, "ManiSkill environment wrapper"),
)

SYSTEM_TOOLS: tuple[SystemToolSpec, ...] = (
    SystemToolSpec("pdflatex", "paper_build", True, "clean PDF build from paper/main.tex"),
    SystemToolSpec("bibtex", "paper_build", True, "clean bibliography build from paper/references.bib"),
    SystemToolSpec("pdftoppm", "pdf_visual_validation", False, "optional rendered-page inspection", ("-v",)),
    SystemToolSpec("pdfinfo", "pdf_metadata_validation", False, "optional PDF metadata inspection", ("-v",)),
)


def _declared_dependencies(pyproject_text: str) -> set[str]:
    dependencies: set[str] = set()
    in_dependencies = False
    for raw_line in pyproject_text.splitlines():
        line = raw_line.strip()
        if line == "dependencies = [":
            in_dependencies = True
            continue
        if in_dependencies and line.startswith("]"):
            break
        if in_dependencies:
            match = PYPROJECT_DEP_RE.search(line)
            if match:
                dependencies.add(_normalise_package_name(match.group(1)))
    return dependencies


def _normalise_package_name(name: str) -> str:
    return name.lower().replace("_", "-")


def _package_version(package: str) -> str:
    try:
        import importlib.metadata as metadata

        return metadata.version(package)
    except Exception:
        return ""


def _tool_version(tool_path: str, args: tuple[str, ...]) -> str:
    try:
        completed = subprocess.run(
            [tool_path, *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return ""
    text = (completed.stdout or completed.stderr or "").strip().splitlines()
    return text[0].strip() if text else ""


def _redact_local_paths(value: str, root: Path) -> str:
    text = str(value)
    replacements: list[tuple[str, str]] = []
    for path, token in ((root, "<PACK_ROOT>"), (Path.home(), "<USER_HOME>")):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        replacements.append((str(resolved), token))
        replacements.append((resolved.as_posix(), token))
    for raw, token in sorted(set(replacements), key=lambda item: len(item[0]), reverse=True):
        if raw:
            text = text.replace(raw, token)
    text = re.sub(r"[A-Za-z]:[\\/]+Users[\\/][A-Za-z0-9_.-]+", "<USER_HOME>", text)
    text = re.sub(r"/home/[A-Za-z0-9_.-]+", "<USER_HOME>", text)
    text = re.sub(r"/Users/[A-Za-z0-9_.-]+", "<USER_HOME>", text)
    return text


def run_environment_dependency_audit(root: Path | str = ".") -> tuple[pd.DataFrame, dict[str, Any]]:
    root = Path(root).resolve()
    pyproject_path = root / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8", errors="ignore") if pyproject_path.exists() else ""
    declared = _declared_dependencies(pyproject_text)
    rows: list[dict[str, Any]] = []

    for spec in PYTHON_PACKAGES:
        declared_name = _normalise_package_name(spec.pyproject_name or spec.package)
        import_present = importlib.util.find_spec(spec.import_name) is not None
        version = _package_version(spec.package)
        declared_ok = declared_name in declared
        status = "pass" if import_present and version and declared_ok else "fail"
        rows.append(
            {
                "kind": "python_package",
                "name": spec.package,
                "import_name": spec.import_name,
                "tier": spec.tier,
                "required": spec.required,
                "installed": bool(import_present and version),
                "version": version,
                "declared_in_pyproject": bool(declared_ok),
                "path": "",
                "status": status if spec.required else ("pass" if import_present else "optional_missing"),
                "reason": spec.reason,
            }
        )

    for spec in SYSTEM_TOOLS:
        tool_path = shutil.which(spec.tool) or ""
        version = _tool_version(tool_path, spec.version_args) if tool_path else ""
        status = "pass" if tool_path else ("fail" if spec.required else "optional_missing")
        rows.append(
            {
                "kind": "system_tool",
                "name": spec.tool,
                "import_name": "",
                "tier": spec.tier,
                "required": spec.required,
                "installed": bool(tool_path),
                "version": version,
                "declared_in_pyproject": "",
                "path": _redact_local_paths(tool_path, root),
                "status": status,
                "reason": spec.reason,
            }
        )

    snapshot = {
        "python_executable": _redact_local_paths(sys.executable, root),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "implementation": platform.python_implementation(),
        "required_python": ">=3.10",
        "pyproject_dependencies": sorted(declared),
    }
    return pd.DataFrame(rows), snapshot


def environment_audit_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"rows": 0, "required": 0, "required_failures": 0, "optional_missing": 0}
    required = rows["required"].astype(str).str.lower().isin({"true", "1"})
    statuses = rows["status"].astype(str)
    return {
        "rows": int(len(rows)),
        "required": int(required.sum()),
        "required_failures": int((required & (statuses != "pass")).sum()),
        "optional_missing": int((statuses == "optional_missing").sum()),
    }


def _markdown_table(rows: pd.DataFrame) -> str:
    display = rows.copy()
    return display.to_markdown(index=False)


def write_environment_dependency_reports(root: Path | str = ".") -> pd.DataFrame:
    root = Path(root).resolve()
    results = root / "results"
    reports = root / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows, snapshot = run_environment_dependency_audit(root)
    rows.to_csv(results / "environment_dependency_audit.csv", index=False)
    (results / "environment_snapshot.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    summary = environment_audit_summary(rows)
    status = "pass" if summary["required_failures"] == 0 and summary["rows"] > 0 else "fail"
    (reports / "ENVIRONMENT_DEPENDENCY_AUDIT.md").write_text(
        f"""# Environment Dependency Audit

Status: `{status}`

This audit records the local Python/platform snapshot, required Python packages, output-format packages, bounded-simulator packages, test package, and PDF/system tools needed by the current non-hardware pack.

| metric | value |
|---|---:|
| rows checked | {summary['rows']} |
| required entries | {summary['required']} |
| required failures | {summary['required_failures']} |
| optional missing | {summary['optional_missing']} |

## Environment Snapshot

| field | value |
|---|---|
| python executable | `{snapshot['python_executable']}` |
| python version | `{snapshot['python_version']}` |
| platform | `{snapshot['platform']}` |
| machine | `{snapshot['machine']}` |
| implementation | `{snapshot['implementation']}` |
| required python | `{snapshot['required_python']}` |

## Dependency Rows

{_markdown_table(rows)}
""",
        encoding="utf-8",
    )
    return rows


def failed_environment_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    required = rows["required"].astype(str).str.lower().isin({"true", "1"})
    return rows[required & (rows["status"].astype(str) != "pass")].copy()
