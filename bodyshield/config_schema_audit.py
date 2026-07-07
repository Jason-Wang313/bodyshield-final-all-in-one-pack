"""Config and schema integrity audit for the non-hardware pack."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from bodyshield.corrective_trace_readiness import load_readiness_spec as load_corrective_trace_spec
from bodyshield.environment_audit import PYTHON_PACKAGES
from bodyshield.external_policy_benchmark import load_benchmark_spec as load_external_policy_spec
from bodyshield.perturbations import AXES
from bodyshield.policies import default_policies
from bodyshield.real_video_wam_readiness import load_readiness_spec as load_real_video_spec
from bodyshield.schema import METHOD_IDS, REQUIRED_PERTURBATION, REQUIRED_TOP_LEVEL, TRIAL_JSON_SCHEMA
from bodyshield.sim import ROBOTS
from bodyshield.tasks import TASK_CARDS


REQUIRED_CONFIGS: tuple[str, ...] = (
    "pyproject.toml",
    "data_schema.json",
    "trial_schema.schema.json",
    "tasks.yaml",
    "configs/simulation_bodyshield_maxout.yaml",
    "configs/hardware_push_block_phase2.yaml",
    "configs/external_policy_benchmark.example.json",
    "configs/real_video_wam_readiness.example.json",
    "configs/corrective_trace_readiness.example.json",
)
EXPECTED_PHASE_IDS: tuple[str, ...] = (
    "phase_0_literature_and_claim_lock",
    "phase_1_software_stack",
    "phase_2_simulation",
    "phase_3_non_hardware_completion",
    "phase_4_hardware_safety_setup",
    "phase_5_hardware_bodybreak",
    "phase_6_hardware_bodyshield",
    "phase_7_submission_pack",
)
HARDWARE_PHASE_IDS = {"phase_4_hardware_safety_setup", "phase_5_hardware_bodybreak", "phase_6_hardware_bodyshield"}
REQUIRED_HARDWARE_SAFETY_TASKS = {"healthcheck", "safety_gate", "emergency_stop_test"}


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


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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
            match = re.search(r'"([^"]+)"', line)
            if match:
                dependencies.add(match.group(1).lower().replace("_", "-"))
    return dependencies


def _pyproject_rows(root: Path) -> list[dict[str, str]]:
    rel = "pyproject.toml"
    path = root / rel
    if not path.exists() or path.stat().st_size <= 0:
        return [_fail(rel, "pyproject_exists_nonempty", "pyproject.toml missing or empty")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    rows = [_pass(rel, "pyproject_exists_nonempty", "pyproject.toml exists and is nonempty", str(path.stat().st_size), ">0 bytes")]
    name_ok = re.search(r'(?m)^name\s*=\s*"bodyshield"\s*$', text) is not None
    rows.append(_row(rel, "pyproject_name_bodyshield", "pass" if name_ok else "fail", "project name is bodyshield", str(name_ok), "True"))
    python_ok = 'requires-python = ">=3.10"' in text
    rows.append(_row(rel, "pyproject_python_requires_declared", "pass" if python_ok else "fail", "requires-python lower bound is declared", str(python_ok), ">=3.10"))
    declared = _declared_dependencies(text)
    required = {str(spec.pyproject_name or spec.package).lower().replace("_", "-") for spec in PYTHON_PACKAGES if spec.required}
    missing = sorted(required - declared)
    rows.append(
        _row(
            rel,
            "pyproject_required_dependencies_declared",
            "pass" if not missing else "fail",
            f"required dependencies missing={missing}",
            str(len(required) - len(missing)),
            str(len(required)),
        )
    )
    pytest_ok = 'pythonpath = ["."]' in text and 'testpaths = ["tests"]' in text
    rows.append(_row(rel, "pyproject_pytest_paths_declared", "pass" if pytest_ok else "fail", "pytest pythonpath and testpaths are declared", str(pytest_ok), "True"))
    return rows


def _schema_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    data_rel = "data_schema.json"
    schema_rel = "trial_schema.schema.json"
    try:
        data_schema = _load_json(root / data_rel)
        rows.append(_pass(data_rel, "json_parse", "data schema JSON parses"))
    except Exception as exc:
        return [_fail(data_rel, "json_parse", f"data schema JSON parse failed: {exc}")]
    try:
        trial_schema = _load_json(root / schema_rel)
        rows.append(_pass(schema_rel, "json_parse", "trial JSON schema parses"))
    except Exception as exc:
        rows.append(_fail(schema_rel, "json_parse", f"trial JSON schema parse failed: {exc}"))
        return rows

    top_missing = sorted(REQUIRED_TOP_LEVEL - set(data_schema))
    perturbation = data_schema.get("perturbation", {})
    perturbation_missing = sorted(REQUIRED_PERTURBATION - set(perturbation if isinstance(perturbation, dict) else {}))
    rows.append(
        _row(
            data_rel,
            "data_schema_required_top_level_keys",
            "pass" if not top_missing else "fail",
            f"missing top-level keys={top_missing}",
            str(len(REQUIRED_TOP_LEVEL) - len(top_missing)),
            str(len(REQUIRED_TOP_LEVEL)),
        )
    )
    rows.append(
        _row(
            data_rel,
            "data_schema_required_perturbation_keys",
            "pass" if not perturbation_missing else "fail",
            f"missing perturbation keys={perturbation_missing}",
            str(len(REQUIRED_PERTURBATION) - len(perturbation_missing)),
            str(len(REQUIRED_PERTURBATION)),
        )
    )
    method_text = str(data_schema.get("method_id", ""))
    missing_methods = sorted(method for method in METHOD_IDS if method not in method_text)
    rows.append(
        _row(
            data_rel,
            "data_schema_method_ids_documented",
            "pass" if not missing_methods else "fail",
            f"missing method ids={missing_methods}",
            str(len(METHOD_IDS) - len(missing_methods)),
            str(len(METHOD_IDS)),
        )
    )

    required = set(trial_schema.get("required", []))
    schema_top_missing = sorted(REQUIRED_TOP_LEVEL - required)
    schema_perturbation = trial_schema.get("properties", {}).get("perturbation", {})
    schema_perturbation_required = set(schema_perturbation.get("required", []))
    schema_perturbation_missing = sorted(REQUIRED_PERTURBATION - schema_perturbation_required)
    schema_methods = set(trial_schema.get("properties", {}).get("method_id", {}).get("enum", []))
    schema_method_missing = sorted(METHOD_IDS - schema_methods)
    schema_exact = trial_schema == TRIAL_JSON_SCHEMA
    rows.append(
        _row(
            schema_rel,
            "trial_json_schema_required_top_level_keys",
            "pass" if not schema_top_missing else "fail",
            f"missing top-level required keys={schema_top_missing}",
            str(len(REQUIRED_TOP_LEVEL) - len(schema_top_missing)),
            str(len(REQUIRED_TOP_LEVEL)),
        )
    )
    rows.append(
        _row(
            schema_rel,
            "trial_json_schema_required_perturbation_keys",
            "pass" if not schema_perturbation_missing else "fail",
            f"missing perturbation required keys={schema_perturbation_missing}",
            str(len(REQUIRED_PERTURBATION) - len(schema_perturbation_missing)),
            str(len(REQUIRED_PERTURBATION)),
        )
    )
    rows.append(
        _row(
            schema_rel,
            "trial_json_schema_method_ids_match_code",
            "pass" if not schema_method_missing and schema_methods == METHOD_IDS else "fail",
            f"missing method ids={schema_method_missing}; extra={sorted(schema_methods - METHOD_IDS)}",
            str(len(schema_methods)),
            str(len(METHOD_IDS)),
        )
    )
    rows.append(_row(schema_rel, "trial_json_schema_matches_code_constant", "pass" if schema_exact else "fail", "serialized schema matches bodyshield.schema.TRIAL_JSON_SCHEMA", str(schema_exact), "True"))
    return rows


def _tasks_yaml_rows(root: Path) -> list[dict[str, str]]:
    rel = "tasks.yaml"
    try:
        payload = _load_yaml(root / rel)
    except Exception as exc:
        return [_fail(rel, "yaml_parse", f"tasks.yaml parse failed: {exc}")]
    phases = payload.get("phases", []) if isinstance(payload, dict) else []
    phase_ids = [phase.get("id") for phase in phases if isinstance(phase, dict)]
    rows = [_pass(rel, "yaml_parse", "tasks.yaml parses")]
    rows.append(
        _row(
            rel,
            "phase_ids_match_expected",
            "pass" if tuple(phase_ids) == EXPECTED_PHASE_IDS else "fail",
            f"phase ids={phase_ids}",
            ",".join(phase_ids),
            ",".join(EXPECTED_PHASE_IDS),
        )
    )
    hardware_flags_ok = True
    safety_tasks_ok = False
    for phase in phases:
        if not isinstance(phase, dict):
            hardware_flags_ok = False
            continue
        phase_id = phase.get("id")
        should_be_hardware = phase_id in HARDWARE_PHASE_IDS
        hardware_flags_ok = hardware_flags_ok and bool(phase.get("hardware")) == should_be_hardware
        if phase_id == "phase_4_hardware_safety_setup":
            safety_tasks = set(phase.get("tasks", []))
            safety_tasks_ok = bool(phase.get("requires_user_confirmation")) and REQUIRED_HARDWARE_SAFETY_TASKS <= safety_tasks
    rows.append(_row(rel, "hardware_phase_flags_match_scope", "pass" if hardware_flags_ok else "fail", "hardware flags are true only for hardware phases", str(hardware_flags_ok), "True"))
    rows.append(_row(rel, "hardware_safety_phase_requires_confirmation", "pass" if safety_tasks_ok else "fail", "hardware safety setup requires user confirmation and safety tasks", str(safety_tasks_ok), "True"))
    return rows


def _simulation_config_rows(root: Path) -> list[dict[str, str]]:
    rel = "configs/simulation_bodyshield_maxout.yaml"
    try:
        payload = _load_yaml(root / rel)
    except Exception as exc:
        return [_fail(rel, "yaml_parse", f"simulation config parse failed: {exc}")]
    rows = [_pass(rel, "yaml_parse", "simulation maxout config parses")]
    task_ids = set(payload.get("tasks", []) if isinstance(payload, dict) else [])
    expected_tasks = {card.task_id for card in TASK_CARDS}
    method_ids = set(payload.get("methods", []) if isinstance(payload, dict) else [])
    expected_methods = set(default_policies()) | {"bodyshield"}
    robots = set(payload.get("simulation", {}).get("robots", []) if isinstance(payload, dict) else [])
    expected_robots = {robot.robot_id for robot in ROBOTS}
    perturbation_axes = set((payload.get("perturbations", {}).get("software", {}) if isinstance(payload, dict) else {}).keys())
    required_axes = set(AXES) - {"joint_lock"}
    rows.append(_row(rel, "simulation_tasks_match_task_cards", "pass" if task_ids == expected_tasks else "fail", f"missing={sorted(expected_tasks - task_ids)}; extra={sorted(task_ids - expected_tasks)}", str(len(task_ids)), str(len(expected_tasks))))
    rows.append(_row(rel, "simulation_methods_match_policies", "pass" if method_ids == expected_methods else "fail", f"missing={sorted(expected_methods - method_ids)}; extra={sorted(method_ids - expected_methods)}", str(len(method_ids)), str(len(expected_methods))))
    rows.append(_row(rel, "simulation_robots_match_code", "pass" if robots == expected_robots else "fail", f"missing={sorted(expected_robots - robots)}; extra={sorted(robots - expected_robots)}", str(len(robots)), str(len(expected_robots))))
    rows.append(_row(rel, "simulation_perturbation_axes_cover_code", "pass" if required_axes <= perturbation_axes else "fail", f"missing={sorted(required_axes - perturbation_axes)}", str(len(perturbation_axes)), f">={len(required_axes)}"))
    return rows


def _hardware_config_rows(root: Path) -> list[dict[str, str]]:
    rel = "configs/hardware_push_block_phase2.yaml"
    try:
        payload = _load_yaml(root / rel)
    except Exception as exc:
        return [_fail(rel, "yaml_parse", f"hardware config parse failed: {exc}")]
    rows = [_pass(rel, "yaml_parse", "hardware placeholder config parses")]
    safety = payload.get("safety", {}) if isinstance(payload, dict) else {}
    method = payload.get("method", {}) if isinstance(payload, dict) else {}
    logging = payload.get("logging", {}) if isinstance(payload, dict) else {}
    safety_ok = (
        safety.get("require_safety_green") is True
        and safety.get("pause_on_safety_event") is True
        and safety.get("pause_on_verifier_uncertainty") is True
        and float(safety.get("speed_scale_max", 1.0)) <= 0.30
        and int(safety.get("max_trials_per_batch", 999)) <= 50
    )
    rows.append(_row(rel, "hardware_config_safety_gated", "pass" if safety_ok else "fail", "hardware config enforces safety gate, pause flags, speed cap, and batch cap", str(safety_ok), "True"))
    rows.append(_row(rel, "hardware_config_policy_bodyshield", "pass" if method.get("policy") == "bodyshield" else "fail", "hardware placeholder policy remains BodyShield", str(method.get("policy")), "bodyshield"))
    rows.append(_row(rel, "hardware_config_logs_config_hash", "pass" if logging.get("save_config_hash") is True else "fail", "hardware placeholder saves config hash", str(logging.get("save_config_hash")), "True"))
    return rows


def _readiness_spec_rows(root: Path) -> list[dict[str, str]]:
    specs = (
        ("configs/external_policy_benchmark.example.json", load_external_policy_spec, "policies", {"fixture", "external_checkpoint"}),
        ("configs/real_video_wam_readiness.example.json", load_real_video_spec, "datasets", {"fixture_sequence", "real_video_dataset"}),
        ("configs/corrective_trace_readiness.example.json", load_corrective_trace_spec, "datasets", {"fixture_corrective_traces", "real_or_external_corrective_traces"}),
    )
    rows: list[dict[str, str]] = []
    for rel, loader, list_key, expected_sources in specs:
        path = root / rel
        try:
            payload = loader(path)
            rows.append(_pass(rel, "readiness_spec_loader_accepts", "module readiness loader accepts example spec"))
        except Exception as exc:
            rows.append(_fail(rel, "readiness_spec_loader_accepts", f"module readiness loader rejected example spec: {exc}"))
            continue
        schema_ok = payload.get("schema_version") == 1 and payload.get("path_base") in {"repo_root", "spec_dir"}
        entries = payload.get(list_key, [])
        sources = {str(entry.get("source")) for entry in entries if isinstance(entry, dict)}
        boundary = str(payload.get("evidence_boundary", "")).lower()
        boundary_ok = "readiness/interface validation only" in boundary and "not " in boundary
        rows.append(_row(rel, "readiness_spec_schema_version_and_path_base", "pass" if schema_ok else "fail", "schema_version=1 and path_base is supported", f"schema={payload.get('schema_version')}; path_base={payload.get('path_base')}", "schema=1; path_base in repo_root/spec_dir"))
        rows.append(_row(rel, "readiness_spec_sources_cover_fixture_and_placeholder", "pass" if sources == expected_sources else "fail", f"sources={sorted(sources)}", ",".join(sorted(sources)), ",".join(sorted(expected_sources))))
        rows.append(_row(rel, "readiness_spec_boundary_present", "pass" if boundary_ok else "fail", "readiness evidence boundary is explicit", payload.get("evidence_boundary", ""), "readiness/interface validation only; not ..."))
    return rows


def _required_config_rows(root: Path) -> list[dict[str, str]]:
    missing = [rel for rel in REQUIRED_CONFIGS if not (root / rel).exists() or (root / rel).stat().st_size <= 0]
    return [
        _row(
            "config_schema_inputs",
            "required_config_files_exist",
            "pass" if not missing else "fail",
            f"missing_or_empty={missing}",
            str(len(REQUIRED_CONFIGS) - len(missing)),
            str(len(REQUIRED_CONFIGS)),
        )
    ]


def run_config_schema_audit(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    rows.extend(_required_config_rows(root_path))
    rows.extend(_pyproject_rows(root_path))
    rows.extend(_schema_rows(root_path))
    rows.extend(_tasks_yaml_rows(root_path))
    rows.extend(_simulation_config_rows(root_path))
    rows.extend(_hardware_config_rows(root_path))
    rows.extend(_readiness_spec_rows(root_path))
    return pd.DataFrame(rows)


def config_schema_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_config_schema_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_config_schema_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = config_schema_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_config_schema_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Config Schema Audit

Status: `{status}`

This audit checks the pack control plane: `pyproject.toml`, trial schemas, planning/task YAML, simulation and hardware-placeholder configs, and readiness JSON specs. It verifies parseability, code/config ID synchronization, safety-gated hardware placeholders, and explicit readiness evidence boundaries.

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


def write_config_schema_audit_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_config_schema_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "config_schema_audit.csv", index=False)
    write_config_schema_report(reports / "CONFIG_SCHEMA_AUDIT.md", rows)
    return rows
