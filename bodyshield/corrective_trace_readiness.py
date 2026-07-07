"""Corrective-trace dataset readiness checks for future real/high-fidelity data."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EVIDENCE_BOUNDARY = (
    "Readiness/interface validation only; not real corrective-trace adaptation or hardware evidence."
)
FIXTURE_BOUNDARY = "Synthetic fixture corrective traces only; not real robot or external high-fidelity corrective data."
MISSING_DATASET_BOUNDARY = (
    "No real corrective-trace evidence was generated because the trace dataset path or manifest is missing."
)
DATASET_SMOKE_BOUNDARY = (
    "Corrective-trace manifest ingestion smoke only; not online adaptation, policy finetuning, or physical transfer evidence."
)
ALLOWED_SOURCES = {"fixture_corrective_traces", "real_or_external_corrective_traces"}
REQUIRED_DATASET_FIELDS = {"dataset_id", "source", "dataset_root", "manifest_path", "action_dim"}
REQUIRED_MANIFEST_COLUMNS = {
    "state_x",
    "state_y",
    "target_x",
    "target_y",
    "base_action_x",
    "base_action_y",
    "corrected_action_x",
    "corrected_action_y",
}


@dataclass(frozen=True)
class TraceSpecContext:
    spec_path: Path
    root: Path
    path_base: str


def default_spec() -> dict[str, Any]:
    return {
        "benchmark_name": "bodyshield_corrective_trace_readiness",
        "schema_version": 1,
        "path_base": "repo_root",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "datasets": [
            {
                "dataset_id": "fixture_corrective_trace_manifest",
                "source": "fixture_corrective_traces",
                "dataset_root": "",
                "manifest_path": "",
                "action_dim": 2,
                "rows": 12,
                "notes": "Deterministic generated corrective traces used to prove the ingestion and residual-fit path executes.",
            },
            {
                "dataset_id": "replace_with_real_corrective_traces",
                "source": "real_or_external_corrective_traces",
                "dataset_root": "external_corrective_traces/replace_with_trace_dataset",
                "manifest_path": "manifest.csv",
                "action_dim": 2,
                "notes": "Template row: replace with real robot or external high-fidelity corrective traces before claiming corrective-trace adaptation evidence.",
            },
        ],
    }


def write_default_spec(path: Path | str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(default_spec(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def load_readiness_spec(path: Path | str) -> dict[str, Any]:
    spec_path = Path(path)
    if not spec_path.exists():
        raise FileNotFoundError(f"corrective trace readiness spec not found: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    datasets = spec.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("corrective trace readiness spec must contain a nonempty 'datasets' list")
    for index, dataset in enumerate(datasets):
        _validate_dataset_spec(dataset, index)
    return spec


def _validate_dataset_spec(dataset: dict[str, Any], index: int) -> None:
    missing = sorted(REQUIRED_DATASET_FIELDS - set(dataset))
    if missing:
        raise ValueError(f"corrective trace dataset spec {index} missing fields: {missing}")
    source = str(dataset["source"])
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"corrective trace dataset spec {index} has unsupported source: {source}")
    action_dim = int(dataset["action_dim"])
    if action_dim <= 0:
        raise ValueError(f"corrective trace dataset spec {index} action_dim must be positive")


def _resolve_path(raw_path: str | None, context: TraceSpecContext, dataset_root: Path | None = None) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if dataset_root is not None:
        candidate = dataset_root / path
        if candidate.exists() or not (context.root / path).exists():
            return candidate
    if context.path_base == "spec_dir":
        return context.spec_path.parent / path
    return context.root / path


def _display_path(path: Path | None, root: Path) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _fixture_rows(count: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total = max(6, int(count))
    for index in range(total):
        phase = index / max(1, total - 1)
        state = np.array([0.08 + 0.18 * phase, -0.05 + 0.10 * np.sin(phase * np.pi)], dtype=float)
        target = np.array([0.32, 0.12], dtype=float)
        error = target - state
        base_action = 0.45 * error
        corrective_residual = np.array([0.025 + 0.005 * phase, -0.018 + 0.004 * phase], dtype=float)
        corrected = base_action + corrective_residual
        rows.append(
            {
                "trace_id": f"fixture_{index:03d}",
                "source": "fixture",
                "perturbation_label": "fixture_latency_and_payload",
                "state_x": state[0],
                "state_y": state[1],
                "target_x": target[0],
                "target_y": target[1],
                "base_action_x": base_action[0],
                "base_action_y": base_action[1],
                "corrected_action_x": corrected[0],
                "corrected_action_y": corrected[1],
            }
        )
    return pd.DataFrame(rows)


def _load_manifest(path: Path) -> pd.DataFrame:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    if not rows:
        raise ValueError("corrective trace manifest has no rows")
    missing = sorted(REQUIRED_MANIFEST_COLUMNS - set(rows[0]))
    if missing:
        raise ValueError(f"corrective trace manifest missing columns: {missing}")
    return pd.DataFrame(rows)


def _as_float_matrix(df: pd.DataFrame, columns: list[str]) -> np.ndarray:
    return df[columns].astype(float).to_numpy()


def _fit_residual_smoke(df: pd.DataFrame) -> dict[str, float]:
    state = _as_float_matrix(df, ["state_x", "state_y"])
    target = _as_float_matrix(df, ["target_x", "target_y"])
    base = _as_float_matrix(df, ["base_action_x", "base_action_y"])
    corrected = _as_float_matrix(df, ["corrected_action_x", "corrected_action_y"])
    residual = corrected - base
    features = np.column_stack([target - state, base, np.ones(len(df))])
    ridge = 1e-6 * np.eye(features.shape[1])
    weights = np.linalg.solve(features.T @ features + ridge, features.T @ residual)
    predicted_residual = features @ weights
    predicted_corrected = base + predicted_residual
    base_mse = float(np.mean((base - corrected) ** 2))
    fitted_mse = float(np.mean((predicted_corrected - corrected) ** 2))
    return {
        "trace_rows": float(len(df)),
        "base_action_mse_to_corrected": base_mse,
        "fitted_action_mse_to_corrected": fitted_mse,
        "mean_residual_norm": float(np.mean(np.linalg.norm(residual, axis=1))),
    }


def _row_base(
    dataset: dict[str, Any],
    benchmark_name: str,
    dataset_root: Path | None,
    manifest_path: Path | None,
    boundary: str,
    root: Path,
) -> dict[str, Any]:
    return {
        "benchmark_name": benchmark_name,
        "dataset_id": dataset["dataset_id"],
        "source": dataset["source"],
        "dataset_root": _display_path(dataset_root, root),
        "manifest_path": _display_path(manifest_path, root),
        "status": "not_started",
        "dataset_present": bool(dataset_root is not None and dataset_root.exists()),
        "manifest_present": bool(manifest_path is not None and manifest_path.exists()),
        "fit_smoke_passed": False,
        "action_dim": int(dataset["action_dim"]),
        "trace_rows": 0,
        "base_action_mse_to_corrected": float("nan"),
        "fitted_action_mse_to_corrected": float("nan"),
        "mean_residual_norm": float("nan"),
        "evidence_boundary": boundary,
        "notes": dataset.get("notes", ""),
    }


def run_corrective_trace_readiness(
    spec_path: Path | str,
    *,
    root: Path | str | None = None,
) -> pd.DataFrame:
    spec_path = Path(spec_path)
    spec = load_readiness_spec(spec_path)
    root_path = Path(root).resolve() if root is not None else spec_path.resolve().parents[1]
    context = TraceSpecContext(
        spec_path=spec_path.resolve(),
        root=root_path,
        path_base=str(spec.get("path_base", "repo_root")),
    )
    benchmark_name = str(spec.get("benchmark_name", "corrective_trace_readiness"))
    rows: list[dict[str, Any]] = []
    for dataset in spec["datasets"]:
        source = str(dataset["source"])
        dataset_root = _resolve_path(dataset.get("dataset_root"), context)
        manifest_path = _resolve_path(dataset.get("manifest_path"), context, dataset_root)
        boundary = FIXTURE_BOUNDARY if source == "fixture_corrective_traces" else MISSING_DATASET_BOUNDARY
        row = _row_base(dataset, benchmark_name, dataset_root, manifest_path, boundary, root_path)
        if source == "fixture_corrective_traces":
            trace_df = _fixture_rows(int(dataset.get("rows", 12)))
            metrics = _fit_residual_smoke(trace_df)
            row.update(
                {
                    "status": "fixture_fit_smoke_passed",
                    "fit_smoke_passed": True,
                    "trace_rows": int(metrics["trace_rows"]),
                    "base_action_mse_to_corrected": metrics["base_action_mse_to_corrected"],
                    "fitted_action_mse_to_corrected": metrics["fitted_action_mse_to_corrected"],
                    "mean_residual_norm": metrics["mean_residual_norm"],
                }
            )
            rows.append(row)
            continue

        if dataset_root is None or manifest_path is None or not dataset_root.exists() or not manifest_path.exists():
            row.update(
                {
                    "status": "missing_dataset",
                    "notes": f"{row['notes']} Dataset root or manifest not found; real corrective-trace adaptation was not run.".strip(),
                }
            )
            rows.append(row)
            continue

        try:
            trace_df = _load_manifest(manifest_path)
            metrics = _fit_residual_smoke(trace_df)
        except Exception as exc:
            row.update(
                {
                    "status": "dataset_smoke_failed",
                    "evidence_boundary": DATASET_SMOKE_BOUNDARY,
                    "notes": f"{row['notes']} Dataset smoke failed: {type(exc).__name__}: {exc}".strip(),
                }
            )
            rows.append(row)
            continue
        row.update(
            {
                "status": "corrective_trace_manifest_smoke_passed",
                "evidence_boundary": DATASET_SMOKE_BOUNDARY,
                "fit_smoke_passed": True,
                "trace_rows": int(metrics["trace_rows"]),
                "base_action_mse_to_corrected": metrics["base_action_mse_to_corrected"],
                "fitted_action_mse_to_corrected": metrics["fitted_action_mse_to_corrected"],
                "mean_residual_norm": metrics["mean_residual_norm"],
                "notes": f"{row['notes']} manifest_rows={len(trace_df)}".strip(),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def readiness_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {
            "rows": 0,
            "fixture_smokes": 0,
            "trace_dataset_specs": 0,
            "trace_dataset_smokes": 0,
            "missing_datasets": 0,
            "failed_rows": 0,
        }
    statuses = rows["status"].astype(str)
    return {
        "rows": int(len(rows)),
        "fixture_smokes": int((statuses == "fixture_fit_smoke_passed").sum()),
        "trace_dataset_specs": int((rows["source"].astype(str) == "real_or_external_corrective_traces").sum()),
        "trace_dataset_smokes": int((statuses == "corrective_trace_manifest_smoke_passed").sum()),
        "missing_datasets": int((statuses == "missing_dataset").sum()),
        "failed_rows": int((statuses == "dataset_smoke_failed").sum()),
    }


def write_corrective_trace_readiness_report(path: Path | str, rows: pd.DataFrame) -> None:
    summary = readiness_summary(rows)
    table = rows.to_markdown(index=False) if not rows.empty else "_No rows generated._"
    Path(path).write_text(
        f"""# Corrective Trace Readiness

This report validates the local corrective-trace manifest, residual-label, and tiny residual-fit path needed before future real robot or external high-fidelity corrective-trace experiments.

It is not real corrective-trace adaptation, online learning, policy finetuning, or hardware evidence. With the included example spec, no real/external corrective trace dataset is present.

## Summary
- Rows: {summary['rows']}
- Fixture fit-smoke rows passed: {summary['fixture_smokes']}
- Real/external corrective trace dataset specs: {summary['trace_dataset_specs']}
- Corrective trace manifest smokes executed: {summary['trace_dataset_smokes']}
- Missing corrective trace datasets: {summary['missing_datasets']}
- Failed rows: {summary['failed_rows']}

## Rows
{table}

## Safe claim
The pack now has a runnable readiness harness for corrective-trace data ingestion and residual-fit validation. The included example real/external corrective trace dataset is missing, so no real corrective-trace adaptation claim is supported.
""",
        encoding="utf-8",
    )


def write_corrective_trace_readiness_artifacts(
    spec_path: Path | str,
    results_dir: Path | str,
    reports_dir: Path | str,
    *,
    root: Path | str | None = None,
) -> pd.DataFrame:
    rows = run_corrective_trace_readiness(spec_path, root=root)
    results = Path(results_dir)
    reports = Path(reports_dir)
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "corrective_trace_readiness.csv", index=False)
    write_corrective_trace_readiness_report(reports / "CORRECTIVE_TRACE_READINESS.md", rows)
    return rows
