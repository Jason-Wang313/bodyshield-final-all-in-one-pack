"""Real-video WAM dataset readiness checks.

The existing visual WAM audits use generated frames. This module validates the
separate data-ingestion path needed for future real camera sequences without
claiming that any real-video or foundation-scale model has been trained.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw


EVIDENCE_BOUNDARY = "Readiness/interface validation only; not real-video or foundation-scale WAM evidence."
FIXTURE_BOUNDARY = "Synthetic fixture frame-manifest smoke only; not real camera video or foundation WAM training."
MISSING_DATASET_BOUNDARY = "No real-video WAM evidence was generated because the dataset path or manifest is missing."
REAL_DATASET_SMOKE_BOUNDARY = (
    "Real-frame manifest ingestion smoke only; not foundation-scale training or physical transfer evidence."
)
REQUIRED_DATASET_FIELDS = {"dataset_id", "source", "dataset_root", "manifest_path", "action_dim"}
REQUIRED_MANIFEST_COLUMNS = {"frame_path", "next_frame_path"}
ALLOWED_SOURCES = {"fixture_sequence", "real_video_dataset"}


@dataclass(frozen=True)
class DatasetSpecContext:
    spec_path: Path
    root: Path
    path_base: str


def default_spec() -> dict[str, Any]:
    return {
        "benchmark_name": "bodyshield_real_video_wam_readiness",
        "schema_version": 1,
        "path_base": "repo_root",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "datasets": [
            {
                "dataset_id": "fixture_manifest_sequence",
                "source": "fixture_sequence",
                "dataset_root": "",
                "manifest_path": "",
                "action_dim": 2,
                "frame_size": 16,
                "frames": 8,
                "notes": "Deterministic generated frame-manifest smoke used to prove the ingestion and fit path executes.",
            },
            {
                "dataset_id": "replace_with_real_camera_sequence",
                "source": "real_video_dataset",
                "dataset_root": "external_real_video/replace_with_camera_sequence",
                "manifest_path": "manifest.csv",
                "action_dim": 2,
                "notes": "Template row: replace with extracted real camera frames and action labels before claiming real-video WAM evidence.",
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
        raise FileNotFoundError(f"real-video WAM readiness spec not found: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    datasets = spec.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("real-video WAM readiness spec must contain a nonempty 'datasets' list")
    for index, dataset in enumerate(datasets):
        _validate_dataset_spec(dataset, index)
    return spec


def _validate_dataset_spec(dataset: dict[str, Any], index: int) -> None:
    missing = sorted(REQUIRED_DATASET_FIELDS - set(dataset))
    if missing:
        raise ValueError(f"dataset spec {index} is missing required fields: {missing}")
    source = str(dataset["source"])
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"dataset spec {index} has unsupported source: {source}")
    action_dim = int(dataset["action_dim"])
    if action_dim <= 0:
        raise ValueError(f"dataset spec {index} action_dim must be positive")


def _resolve_path(raw_path: str | None, context: DatasetSpecContext, dataset_root: Path | None = None) -> Path | None:
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


def _centroid(path_or_image: Path | Image.Image) -> np.ndarray:
    image = path_or_image if isinstance(path_or_image, Image.Image) else Image.open(path_or_image)
    gray = np.asarray(image.convert("L"), dtype=float) / 255.0
    total = float(gray.sum())
    height, width = gray.shape
    if total <= 1e-12:
        return np.array([0.5, 0.5], dtype=float)
    ys, xs = np.indices(gray.shape)
    return np.array([float((xs * gray).sum() / total) / max(1, width - 1), float((ys * gray).sum() / total) / max(1, height - 1)])


def _fixture_transitions(frames: int, frame_size: int) -> list[dict[str, Any]]:
    count = max(4, int(frames))
    size = max(8, int(frame_size))
    positions = []
    for index in range(count):
        x = 0.20 + 0.55 * index / max(1, count - 1)
        y = 0.68 - 0.34 * index / max(1, count - 1)
        positions.append(np.array([x, y], dtype=float))
    transitions: list[dict[str, Any]] = []
    for index in range(count - 1):
        current = Image.new("L", (size, size), 0)
        nxt = Image.new("L", (size, size), 0)
        for image, position in [(current, positions[index]), (nxt, positions[index + 1])]:
            draw = ImageDraw.Draw(image)
            px = int(round(position[0] * (size - 1)))
            py = int(round(position[1] * (size - 1)))
            draw.ellipse((px - 1, py - 1, px + 1, py + 1), fill=255)
        transitions.append(
            {
                "frame": current,
                "next_frame": nxt,
                "action": positions[index + 1] - positions[index],
            }
        )
    return transitions


def _load_manifest_transitions(dataset_root: Path, manifest_path: Path, action_dim: int) -> tuple[list[dict[str, Any]], str]:
    rows = list(csv.DictReader(manifest_path.open(newline="", encoding="utf-8")))
    if not rows:
        raise ValueError("manifest has no transition rows")
    missing_columns = sorted(REQUIRED_MANIFEST_COLUMNS - set(rows[0]))
    if missing_columns:
        raise ValueError(f"manifest missing required columns: {missing_columns}")
    transitions: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        frame_path = _manifest_frame_path(dataset_root, row["frame_path"])
        next_frame_path = _manifest_frame_path(dataset_root, row["next_frame_path"])
        if not frame_path.exists() or not next_frame_path.exists():
            raise FileNotFoundError(f"transition {index} frame path missing")
        action = _row_action(row, action_dim)
        transitions.append({"frame": frame_path, "next_frame": next_frame_path, "action": action})
    return transitions, f"manifest_rows={len(rows)}"


def _manifest_frame_path(dataset_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else dataset_root / path


def _row_action(row: dict[str, str], action_dim: int) -> np.ndarray:
    values: list[float] = []
    for index in range(action_dim):
        for key in (f"action_{index}", f"action_{index + 1}", f"action_{'xyzw'[index]}" if index < 4 else ""):
            if key and key in row and row[key] != "":
                values.append(float(row[key]))
                break
        else:
            values.append(0.0)
    return np.asarray(values, dtype=float)


def _fit_centroid_predictor(transitions: list[dict[str, Any]], action_dim: int) -> dict[str, float]:
    features: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    baseline_targets: list[np.ndarray] = []
    for item in transitions:
        current = _centroid(item["frame"])
        nxt = _centroid(item["next_frame"])
        action = np.asarray(item["action"], dtype=float).reshape(-1)
        if action.size < action_dim:
            action = np.pad(action, (0, action_dim - action.size))
        action = action[:action_dim]
        features.append(np.concatenate([current, action, [1.0]]))
        targets.append(nxt)
        baseline_targets.append(current)
    x = np.vstack(features)
    y = np.vstack(targets)
    baseline = np.vstack(baseline_targets)
    ridge = 1e-6 * np.eye(x.shape[1])
    weights = np.linalg.solve(x.T @ x + ridge, x.T @ y)
    predicted = x @ weights
    return {
        "transitions": float(len(transitions)),
        "baseline_next_centroid_mse": float(np.mean((baseline - y) ** 2)),
        "fitted_next_centroid_mse": float(np.mean((predicted - y) ** 2)),
        "mean_action_norm": float(np.mean([np.linalg.norm(np.asarray(item["action"], dtype=float)) for item in transitions])),
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
        "training_smoke_passed": False,
        "action_dim": int(dataset["action_dim"]),
        "frames_checked": 0,
        "transitions": 0,
        "baseline_next_centroid_mse": float("nan"),
        "fitted_next_centroid_mse": float("nan"),
        "mean_action_norm": float("nan"),
        "evidence_boundary": boundary,
        "notes": dataset.get("notes", ""),
    }


def run_real_video_wam_readiness(
    spec_path: Path | str,
    *,
    root: Path | str | None = None,
) -> pd.DataFrame:
    spec_path = Path(spec_path)
    spec = load_readiness_spec(spec_path)
    root_path = Path(root).resolve() if root is not None else spec_path.resolve().parents[1]
    context = DatasetSpecContext(
        spec_path=spec_path.resolve(),
        root=root_path,
        path_base=str(spec.get("path_base", "repo_root")),
    )
    benchmark_name = str(spec.get("benchmark_name", "real_video_wam_readiness"))
    rows: list[dict[str, Any]] = []
    for dataset in spec["datasets"]:
        source = str(dataset["source"])
        dataset_root = _resolve_path(dataset.get("dataset_root"), context)
        manifest_path = _resolve_path(dataset.get("manifest_path"), context, dataset_root)
        boundary = FIXTURE_BOUNDARY if source == "fixture_sequence" else MISSING_DATASET_BOUNDARY
        row = _row_base(dataset, benchmark_name, dataset_root, manifest_path, boundary, root_path)
        action_dim = int(dataset["action_dim"])
        if source == "fixture_sequence":
            transitions = _fixture_transitions(int(dataset.get("frames", 8)), int(dataset.get("frame_size", 16)))
            metrics = _fit_centroid_predictor(transitions, action_dim)
            row.update(
                {
                    "status": "fixture_training_smoke_passed",
                    "training_smoke_passed": True,
                    "dataset_present": False,
                    "manifest_present": False,
                    "frames_checked": len(transitions) + 1,
                    "transitions": int(metrics["transitions"]),
                    "baseline_next_centroid_mse": metrics["baseline_next_centroid_mse"],
                    "fitted_next_centroid_mse": metrics["fitted_next_centroid_mse"],
                    "mean_action_norm": metrics["mean_action_norm"],
                }
            )
            rows.append(row)
            continue

        if dataset_root is None or manifest_path is None or not dataset_root.exists() or not manifest_path.exists():
            row.update(
                {
                    "status": "missing_dataset",
                    "notes": f"{row['notes']} Dataset root or manifest not found; real-video WAM training was not run.".strip(),
                }
            )
            rows.append(row)
            continue

        try:
            transitions, manifest_notes = _load_manifest_transitions(dataset_root, manifest_path, action_dim)
            metrics = _fit_centroid_predictor(transitions, action_dim)
        except Exception as exc:
            row.update(
                {
                    "status": "dataset_smoke_failed",
                    "evidence_boundary": REAL_DATASET_SMOKE_BOUNDARY,
                    "notes": f"{row['notes']} Dataset smoke failed: {type(exc).__name__}: {exc}".strip(),
                }
            )
            rows.append(row)
            continue
        row.update(
            {
                "status": "real_frame_manifest_smoke_passed",
                "evidence_boundary": REAL_DATASET_SMOKE_BOUNDARY,
                "training_smoke_passed": True,
                "frames_checked": len(transitions) + 1,
                "transitions": int(metrics["transitions"]),
                "baseline_next_centroid_mse": metrics["baseline_next_centroid_mse"],
                "fitted_next_centroid_mse": metrics["fitted_next_centroid_mse"],
                "mean_action_norm": metrics["mean_action_norm"],
                "notes": f"{row['notes']} {manifest_notes}".strip(),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def readiness_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {
            "rows": 0,
            "fixture_smokes": 0,
            "real_dataset_specs": 0,
            "real_dataset_smokes": 0,
            "missing_datasets": 0,
            "failed_rows": 0,
        }
    statuses = rows["status"].astype(str)
    return {
        "rows": int(len(rows)),
        "fixture_smokes": int((statuses == "fixture_training_smoke_passed").sum()),
        "real_dataset_specs": int((rows["source"].astype(str) == "real_video_dataset").sum()),
        "real_dataset_smokes": int((statuses == "real_frame_manifest_smoke_passed").sum()),
        "missing_datasets": int((statuses == "missing_dataset").sum()),
        "failed_rows": int((statuses == "dataset_smoke_failed").sum()),
    }


def write_real_video_wam_readiness_report(path: Path | str, rows: pd.DataFrame) -> None:
    summary = readiness_summary(rows)
    table = rows.to_markdown(index=False) if not rows.empty else "_No rows generated._"
    Path(path).write_text(
        f"""# Real-Video WAM Readiness

This report validates the local frame-manifest, action-label, centroid-feature, and tiny predictor-fit path needed before future real-camera WAM experiments.

It is not real-video WAM evidence, foundation-model training, or physical transfer evidence. With the included example spec, no real camera dataset is present.

## Summary
- Rows: {summary['rows']}
- Fixture training-smoke rows passed: {summary['fixture_smokes']}
- Real-video dataset specs: {summary['real_dataset_specs']}
- Real-frame manifest smokes executed: {summary['real_dataset_smokes']}
- Missing real-video datasets: {summary['missing_datasets']}
- Failed rows: {summary['failed_rows']}

## Rows
{table}

## Safe claim
The pack now has a runnable readiness harness for real-video WAM data ingestion and tiny fit validation. The included example real-video dataset is missing, so no real-video or foundation-scale WAM claim is supported.
""",
        encoding="utf-8",
    )


def write_real_video_wam_readiness_artifacts(
    spec_path: Path | str,
    results_dir: Path | str,
    reports_dir: Path | str,
    *,
    root: Path | str | None = None,
) -> pd.DataFrame:
    rows = run_real_video_wam_readiness(spec_path, root=root)
    results = Path(results_dir)
    reports = Path(reports_dir)
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "real_video_wam_readiness.csv", index=False)
    write_real_video_wam_readiness_report(reports / "REAL_VIDEO_WAM_READINESS.md", rows)
    return rows
