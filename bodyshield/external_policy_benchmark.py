"""External trained-policy benchmark readiness checks.

This module validates the local interface needed to plug in future MuJoCo or
ManiSkill trained-policy checkpoints. It intentionally records missing
checkpoints as first-class rows instead of silently skipping them.
"""

from __future__ import annotations

import importlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EVIDENCE_BOUNDARY = (
    "Readiness/interface validation only; not an external full-scale trained-policy benchmark."
)
MISSING_CHECKPOINT_BOUNDARY = (
    "No external trained-policy evidence was generated because the checkpoint path is missing."
)
FIXTURE_BOUNDARY = "Deterministic fixture smoke only; not external checkpoint evidence."
EXTERNAL_SMOKE_BOUNDARY = (
    "External checkpoint interface smoke only; not a MuJoCo/ManiSkill task-rollout benchmark."
)
REQUIRED_POLICY_FIELDS = {"policy_id", "source", "engine", "task_id", "expected_action_dim"}
ALLOWED_SOURCES = {"fixture", "external_checkpoint"}


@dataclass(frozen=True)
class PolicySpecContext:
    spec_path: Path
    root: Path
    path_base: str


class InterfaceSmokeError(ValueError):
    """Raised when a policy adapter fails the deterministic interface smoke."""


def default_spec() -> dict[str, Any]:
    return {
        "benchmark_name": "bodyshield_external_policy_benchmark_readiness",
        "schema_version": 1,
        "path_base": "repo_root",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "policies": [
            {
                "policy_id": "fixture_proportional_planar",
                "source": "fixture",
                "engine": "interface_smoke",
                "task_id": "planar_reach_fixture",
                "adapter": "fixture:proportional",
                "expected_action_dim": 2,
                "observation_dim": 6,
                "notes": "Deterministic local smoke policy used to prove the harness path executes.",
            },
            {
                "policy_id": "replace_with_external_maniskill_checkpoint",
                "source": "external_checkpoint",
                "engine": "maniskill",
                "task_id": "PushCube-v1",
                "checkpoint_path": "external_checkpoints/replace_with_trained_policy.ckpt",
                "adapter": "your_policy_module:load_policy",
                "expected_action_dim": 7,
                "observation_dim": 16,
                "notes": "Template row: replace with a real checkpoint and adapter before claiming external policy evidence.",
            },
        ],
    }


def write_default_spec(path: Path | str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(default_spec(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def load_benchmark_spec(path: Path | str) -> dict[str, Any]:
    spec_path = Path(path)
    if not spec_path.exists():
        raise FileNotFoundError(f"external policy benchmark spec not found: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    policies = spec.get("policies")
    if not isinstance(policies, list) or not policies:
        raise ValueError("external policy benchmark spec must contain a nonempty 'policies' list")
    for index, policy in enumerate(policies):
        _validate_policy_spec(policy, index)
    return spec


def _validate_policy_spec(policy: dict[str, Any], index: int) -> None:
    missing = sorted(REQUIRED_POLICY_FIELDS - set(policy))
    if missing:
        raise ValueError(f"policy spec {index} is missing required fields: {missing}")
    source = str(policy["source"])
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"policy spec {index} has unsupported source: {source}")
    expected_action_dim = int(policy["expected_action_dim"])
    observation_dim = int(policy.get("observation_dim", 6))
    if expected_action_dim <= 0:
        raise ValueError(f"policy spec {index} expected_action_dim must be positive")
    if observation_dim < 4:
        raise ValueError(f"policy spec {index} observation_dim must be at least 4")
    if source == "external_checkpoint":
        for field in ("checkpoint_path", "adapter"):
            if not policy.get(field):
                raise ValueError(f"policy spec {index} external_checkpoint row missing {field}")


def _resolve_path(raw_path: str | None, context: PolicySpecContext) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if context.path_base == "spec_dir":
        return context.spec_path.parent / path
    return context.root / path


def _maybe_add_python_path(raw_path: str | None, context: PolicySpecContext) -> None:
    path = _resolve_path(raw_path, context)
    if path is not None and path.exists():
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _fixture_policy(observation: np.ndarray, step: int, spec: dict[str, Any]) -> np.ndarray:
    del step, spec
    state = observation[:2]
    target = observation[2:4]
    return np.clip(0.55 * (target - state), -0.06, 0.06)


def _load_external_policy(adapter: str, checkpoint_path: Path, spec: dict[str, Any]) -> Any:
    if ":" not in adapter:
        raise InterfaceSmokeError("adapter must use 'module:function' syntax")
    module_name, function_name = adapter.split(":", 1)
    module = importlib.import_module(module_name)
    factory = getattr(module, function_name)
    try:
        return factory(checkpoint_path=str(checkpoint_path), spec=dict(spec))
    except TypeError:
        return factory(str(checkpoint_path))


def _call_policy(policy: Any, observation: np.ndarray, step: int, spec: dict[str, Any]) -> Any:
    if hasattr(policy, "predict"):
        return policy.predict(observation)
    if hasattr(policy, "act"):
        return policy.act(observation)
    if callable(policy):
        callable_policy = policy
        try:
            return callable_policy(observation, step=step, spec=spec)
        except TypeError:
            try:
                return callable_policy(observation, step)
            except TypeError:
                return callable_policy(observation)
    raise InterfaceSmokeError("adapter did not return a callable, predict(), or act() policy")


def _display_path(path: Path | None, root: Path) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _row_base(
    policy: dict[str, Any],
    checkpoint_path: Path | None,
    benchmark_name: str,
    boundary: str,
    root: Path,
) -> dict[str, Any]:
    return {
        "benchmark_name": benchmark_name,
        "policy_id": policy["policy_id"],
        "source": policy["source"],
        "engine": policy["engine"],
        "task_id": policy["task_id"],
        "benchmark_mode": "deterministic_interface_smoke",
        "checkpoint_path": _display_path(checkpoint_path, root),
        "checkpoint_present": bool(checkpoint_path is not None and checkpoint_path.exists()),
        "adapter": policy.get("adapter", ""),
        "status": "not_started",
        "interface_checks_passed": False,
        "steps_requested": 0,
        "steps_executed": 0,
        "observation_dim": int(policy.get("observation_dim", 6)),
        "expected_action_dim": int(policy["expected_action_dim"]),
        "final_error": float("nan"),
        "improvement": float("nan"),
        "mean_action_norm": float("nan"),
        "evidence_boundary": boundary,
        "notes": policy.get("notes", ""),
    }


def _coerce_action(raw_action: Any, expected_dim: int) -> np.ndarray:
    action = np.asarray(raw_action, dtype=float).reshape(-1)
    if action.size != expected_dim:
        raise InterfaceSmokeError(f"action_dim={action.size}; expected={expected_dim}")
    if not np.isfinite(action).all():
        raise InterfaceSmokeError("action contains non-finite values")
    return action


def _run_interface_smoke(
    policy: Any,
    spec_row: dict[str, Any],
    row: dict[str, Any],
    *,
    steps: int,
    success_status: str,
) -> dict[str, Any]:
    observation_dim = int(spec_row.get("observation_dim", 6))
    expected_dim = int(spec_row["expected_action_dim"])
    state = np.zeros(2, dtype=float)
    target = np.array([0.24, -0.16], dtype=float)
    initial_error = float(np.linalg.norm(target - state))
    action_norms: list[float] = []
    executed = 0
    try:
        for step in range(steps):
            observation = np.zeros(observation_dim, dtype=float)
            observation[:2] = state
            observation[2:4] = target
            if observation_dim > 4:
                observation[4] = step / max(1, steps - 1)
            if observation_dim > 5:
                observation[5] = 1.0
            raw_action = _call_policy(policy, observation, step, spec_row)
            action = _coerce_action(raw_action, expected_dim)
            action_norms.append(float(np.linalg.norm(action)))
            motion = np.zeros(2, dtype=float)
            motion[: min(2, action.size)] = action[: min(2, action.size)]
            state += np.clip(motion, -0.05, 0.05)
            executed += 1
    except Exception as exc:
        row.update(
            {
                "status": "interface_smoke_failed",
                "interface_checks_passed": False,
                "steps_requested": steps,
                "steps_executed": executed,
                "notes": f"{row['notes']} Interface smoke failed: {type(exc).__name__}: {exc}".strip(),
            }
        )
        return row

    final_error = float(np.linalg.norm(target - state))
    row.update(
        {
            "status": success_status,
            "interface_checks_passed": True,
            "steps_requested": steps,
            "steps_executed": executed,
            "final_error": final_error,
            "improvement": initial_error - final_error,
            "mean_action_norm": float(np.mean(action_norms)) if action_norms else float("nan"),
        }
    )
    return row


def run_external_policy_benchmark(
    spec_path: Path | str,
    *,
    root: Path | str | None = None,
    steps: int = 6,
) -> pd.DataFrame:
    """Run the readiness/interface tier and return one row per policy spec."""

    spec_path = Path(spec_path)
    spec = load_benchmark_spec(spec_path)
    root_path = Path(root).resolve() if root is not None else spec_path.resolve().parents[1]
    context = PolicySpecContext(
        spec_path=spec_path.resolve(),
        root=root_path,
        path_base=str(spec.get("path_base", "repo_root")),
    )
    benchmark_name = str(spec.get("benchmark_name", "external_policy_benchmark_readiness"))
    rows: list[dict[str, Any]] = []
    for policy in spec["policies"]:
        checkpoint_path = _resolve_path(policy.get("checkpoint_path"), context)
        source = str(policy["source"])
        if source == "fixture":
            row = _row_base(policy, checkpoint_path, benchmark_name, FIXTURE_BOUNDARY, root_path)
            rows.append(
                _run_interface_smoke(
                    _fixture_policy,
                    policy,
                    row,
                    steps=steps,
                    success_status="fixture_smoke_passed",
                )
            )
            continue

        row = _row_base(policy, checkpoint_path, benchmark_name, MISSING_CHECKPOINT_BOUNDARY, root_path)
        if checkpoint_path is None or not checkpoint_path.exists():
            row.update(
                {
                    "status": "missing_checkpoint",
                    "steps_requested": steps,
                    "notes": f"{row['notes']} Checkpoint path not found; external trained-policy benchmark was not run.".strip(),
                }
            )
            rows.append(row)
            continue

        _maybe_add_python_path(policy.get("python_path"), context)
        try:
            external_policy = _load_external_policy(str(policy["adapter"]), checkpoint_path, policy)
        except Exception as exc:
            row.update(
                {
                    "status": "adapter_load_failed",
                    "steps_requested": steps,
                    "notes": f"{row['notes']} Adapter load failed: {type(exc).__name__}: {exc}".strip(),
                }
            )
            rows.append(row)
            continue
        row["evidence_boundary"] = EXTERNAL_SMOKE_BOUNDARY
        rows.append(
            _run_interface_smoke(
                external_policy,
                policy,
                row,
                steps=steps,
                success_status="executed_external_checkpoint_interface_smoke",
            )
        )
    return pd.DataFrame(rows)


def readiness_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {
            "rows": 0,
            "fixtures_passed": 0,
            "external_specs": 0,
            "external_interface_smokes": 0,
            "missing_checkpoints": 0,
            "failed_rows": 0,
        }
    statuses = rows["status"].astype(str)
    return {
        "rows": int(len(rows)),
        "fixtures_passed": int((statuses == "fixture_smoke_passed").sum()),
        "external_specs": int((rows["source"].astype(str) == "external_checkpoint").sum()),
        "external_interface_smokes": int((statuses == "executed_external_checkpoint_interface_smoke").sum()),
        "missing_checkpoints": int((statuses == "missing_checkpoint").sum()),
        "failed_rows": int(statuses.isin(["interface_smoke_failed", "adapter_load_failed"]).sum()),
    }


def write_external_policy_benchmark_report(path: Path | str, rows: pd.DataFrame) -> None:
    summary = readiness_summary(rows)
    table = rows.to_markdown(index=False) if not rows.empty else "_No rows generated._"
    Path(path).write_text(
        f"""# External Policy Benchmark Readiness

This report validates the local spec, checkpoint-detection, adapter-loading, and deterministic interface-smoke path for future external trained-policy checkpoints.

It is not external/full-scale MuJoCo or ManiSkill trained-policy evidence. A real benchmark row must have an existing checkpoint, an explicit adapter, and later task-rollout execution beyond this interface smoke.

## Summary
- Rows: {summary['rows']}
- Fixture smoke rows passed: {summary['fixtures_passed']}
- External checkpoint specs: {summary['external_specs']}
- External checkpoint interface smokes executed: {summary['external_interface_smokes']}
- Missing external checkpoints: {summary['missing_checkpoints']}
- Failed rows: {summary['failed_rows']}

## Rows
{table}

## Safe claim
The pack now has a runnable harness for external checkpoint readiness. With the included example spec, no external trained-policy checkpoint is present, so no external/full-scale trained-policy benchmark claim is supported.
""",
        encoding="utf-8",
    )


def write_external_policy_benchmark_artifacts(
    spec_path: Path | str,
    results_dir: Path | str,
    reports_dir: Path | str,
    *,
    root: Path | str | None = None,
    steps: int = 6,
) -> pd.DataFrame:
    rows = run_external_policy_benchmark(spec_path, root=root, steps=steps)
    results = Path(results_dir)
    reports = Path(reports_dir)
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "external_policy_benchmark_readiness.csv", index=False)
    write_external_policy_benchmark_report(reports / "EXTERNAL_POLICY_BENCHMARK_READINESS.md", rows)
    return rows
