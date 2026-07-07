"""Generated-results integrity audit for the local non-hardware pack."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SELF_AUDIT_CSV = "results/results_integrity_audit.csv"
PACK_SIDE_DYNAMIC_CSVS = {
    "results/artifact_inventory_audit.csv",
    "results/portable_hygiene_audit.csv",
    "results/release_determinism_audit.csv",
    "results/release_payload_audit.csv",
    "results/release_runtime_audit.csv",
}


@dataclass(frozen=True)
class NumericRange:
    column: str
    low: float | None = None
    high: float | None = None


@dataclass(frozen=True)
class RequiredValues:
    column: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class AllowedValues:
    column: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class TableSpec:
    path: str
    required_columns: tuple[str, ...]
    exact_rows: int | None = None
    min_rows: int | None = None
    unique_columns: tuple[str, ...] = ()
    required_non_null: tuple[str, ...] = ()
    numeric_ranges: tuple[NumericRange, ...] = ()
    required_values: tuple[RequiredValues, ...] = ()
    allowed_values: tuple[AllowedValues, ...] = ()


TABLE_SPECS: tuple[TableSpec, ...] = (
    TableSpec(
        path="results/trials.csv",
        exact_rows=1_152_000,
        required_columns=(
            "trial_id",
            "phase",
            "task_id",
            "robot_id",
            "method_id",
            "perturbation_family",
            "level",
            "bucket",
            "perturbation_cost",
            "success",
            "failure_category",
            "execution_time_s",
            "path_length_m",
            "workspace_violation",
            "verifier_confidence",
        ),
        unique_columns=("trial_id", "task_id", "robot_id", "method_id", "bucket", "perturbation_family", "level"),
        required_non_null=("trial_id", "phase", "task_id", "robot_id", "method_id", "bucket"),
        numeric_ranges=(
            NumericRange("perturbation_cost", 0.0, None),
            NumericRange("success", 0.0, 1.0),
            NumericRange("execution_time_s", 0.0, None),
            NumericRange("path_length_m", 0.0, None),
            NumericRange("workspace_violation", 0.0, 1.0),
            NumericRange("verifier_confidence", 0.0, 1.0),
        ),
        required_values=(
            RequiredValues("phase", ("simulation",)),
            RequiredValues("bucket", ("nominal", "seen", "heldout")),
            RequiredValues(
                "method_id",
                (
                    "nominal",
                    "random_tuning",
                    "domain_randomization",
                    "grid_worstcase",
                    "robust_control",
                    "sysid_retune",
                    "oracle",
                    "human_effect_prior",
                    "epec",
                    "bodyshield",
                ),
            ),
        ),
    ),
    TableSpec(
        path="results/breaking_search.csv",
        exact_rows=288,
        required_columns=(
            "method_id",
            "task_id",
            "robot_id",
            "search_mode",
            "breaking_cost",
            "success_rate",
            "trials",
            "perturbation",
            "active_axes",
            "notes",
        ),
        unique_columns=("method_id", "task_id", "robot_id", "search_mode"),
        numeric_ranges=(
            NumericRange("breaking_cost", 0.0, None),
            NumericRange("success_rate", 0.0, 1.0),
            NumericRange("trials", 1.0, 200.0),
        ),
        required_values=(RequiredValues("search_mode", ("random", "one_axis", "grid", "bodybreak")),),
        allowed_values=(
            AllowedValues("notes", ("found_break", "no_break_found_returned_lowest_success")),
        ),
    ),
    TableSpec(
        path="results/bodybreak_minimality_audit.csv",
        min_rows=12,
        required_columns=(
            "method_id",
            "task_id",
            "robot_id",
            "bodybreak_cost",
            "dense_candidate_count",
            "confirm_trials",
            "audit_status",
        ),
        numeric_ranges=(
            NumericRange("bodybreak_cost", 0.0, None),
            NumericRange("dense_candidate_count", 1.0, None),
            NumericRange("confirm_trials", 1.0, None),
        ),
    ),
    TableSpec(
        path="results/summary_by_method_bucket.csv",
        exact_rows=30,
        required_columns=("method_id", "bucket", "n", "successes", "success_rate", "ci_low", "ci_high"),
        unique_columns=("method_id", "bucket"),
        numeric_ranges=(
            NumericRange("n", 1.0, None),
            NumericRange("successes", 0.0, None),
            NumericRange("success_rate", 0.0, 1.0),
            NumericRange("ci_low", 0.0, 1.0),
            NumericRange("ci_high", 0.0, 1.0),
        ),
        required_values=(RequiredValues("bucket", ("nominal", "seen", "heldout")),),
    ),
    TableSpec(
        path="results/high_fidelity_benchmark.csv",
        min_rows=500,
        required_columns=("engine", "task_id", "method_id", "perturbation_family", "success_rate", "notes"),
        numeric_ranges=(NumericRange("success_rate", 0.0, 1.0),),
        required_values=(RequiredValues("engine", ("mujoco", "mujoco_planar", "maniskill")),),
    ),
    TableSpec(
        path="results/learned_outcome_model_eval.csv",
        exact_rows=6,
        required_columns=("split", "n_conditions", "mae", "brier", "log_loss", "auc_at_50"),
        numeric_ranges=(NumericRange("mae", 0.0, None), NumericRange("brier", 0.0, None)),
        required_values=(RequiredValues("split", ("train_seen_or_nominal", "heldout")),),
    ),
    TableSpec(
        path="results/trajectory_wam_eval.csv",
        exact_rows=6,
        required_columns=("split", "n_transitions", "n_rollouts", "transition_state_rmse", "final_xy_mae"),
        numeric_ranges=(NumericRange("n_transitions", 1.0, None), NumericRange("final_xy_mae", 0.0, None)),
        required_values=(RequiredValues("split", ("train_seen_or_nominal", "heldout")),),
    ),
    TableSpec(
        path="results/visual_wam_eval.csv",
        exact_rows=9,
        required_columns=("slice", "n_transitions", "n_rollouts", "transition_frame_mse", "transition_psnr_db"),
        numeric_ranges=(NumericRange("n_transitions", 1.0, None), NumericRange("transition_frame_mse", 0.0, None)),
    ),
    TableSpec(
        path="results/neural_wam_eval.csv",
        exact_rows=9,
        required_columns=("slice", "n_transitions", "n_rollouts", "transition_latent_mse", "final_latent_mse"),
        numeric_ranges=(NumericRange("n_transitions", 1.0, None), NumericRange("transition_latent_mse", 0.0, None)),
    ),
    TableSpec(
        path="results/corrective_adaptation_eval.csv",
        exact_rows=12,
        required_columns=("slice", "n_rollouts", "base_final_error", "adapted_final_error", "delta_final_error"),
        numeric_ranges=(NumericRange("n_rollouts", 1.0, None), NumericRange("base_final_error", 0.0, None)),
    ),
    TableSpec(
        path="results/mujoco_residual_policy_eval.csv",
        exact_rows=9,
        required_columns=("slice", "n_rollouts", "base_success_rate", "adapted_success_rate", "delta_final_error"),
        numeric_ranges=(
            NumericRange("n_rollouts", 1.0, None),
            NumericRange("base_success_rate", 0.0, 1.0),
            NumericRange("adapted_success_rate", 0.0, 1.0),
        ),
    ),
    TableSpec(
        path="results/mujoco_residual_policy_gate_ablation.csv",
        exact_rows=16,
        required_columns=("variant", "slice", "n_rollouts", "base_success_rate", "adapted_success_rate"),
        required_values=(RequiredValues("variant", ("residual_off", "always_on", "non_nominal_only", "gated_default")),),
        numeric_ranges=(NumericRange("base_success_rate", 0.0, 1.0), NumericRange("adapted_success_rate", 0.0, 1.0)),
    ),
    TableSpec(
        path="results/external_policy_benchmark_readiness.csv",
        exact_rows=2,
        required_columns=("policy_id", "source", "status", "checkpoint_present", "interface_checks_passed", "evidence_boundary"),
        required_values=(RequiredValues("status", ("fixture_smoke_passed", "missing_checkpoint")),),
    ),
    TableSpec(
        path="results/real_video_wam_readiness.csv",
        exact_rows=2,
        required_columns=("dataset_id", "source", "status", "dataset_present", "manifest_present", "evidence_boundary"),
        required_values=(RequiredValues("status", ("fixture_training_smoke_passed", "missing_dataset")),),
    ),
    TableSpec(
        path="results/corrective_trace_readiness.csv",
        exact_rows=2,
        required_columns=("dataset_id", "source", "status", "dataset_present", "manifest_present", "evidence_boundary"),
        required_values=(RequiredValues("status", ("fixture_fit_smoke_passed", "missing_dataset")),),
    ),
    TableSpec(
        path="results/simulation_rollout_videos.csv",
        exact_rows=3,
        required_columns=("artifact_id", "path", "frames", "frame_size_px", "success_probability", "evidence_boundary"),
        unique_columns=("artifact_id",),
        required_values=(RequiredValues("artifact_id", ("nominal_reference", "bodybreak_failure", "bodyshield_repair")),),
        numeric_ranges=(NumericRange("frames", 2.0, None), NumericRange("success_probability", 0.0, 1.0)),
    ),
    TableSpec(
        path="results/environment_dependency_audit.csv",
        min_rows=14,
        required_columns=("kind", "name", "required", "installed", "declared_in_pyproject", "status"),
        required_values=(RequiredValues("status", ("pass",)),),
    ),
    TableSpec(
        path="results/config_schema_audit.csv",
        min_rows=30,
        required_columns=("artifact", "check", "status", "detail", "observed", "expected"),
        required_values=(RequiredValues("status", ("pass",)),),
    ),
    TableSpec(
        path="results/source_import_audit.csv",
        min_rows=100,
        required_columns=("artifact", "check", "status", "detail", "observed", "expected"),
        required_values=(RequiredValues("status", ("pass",)),),
    ),
    TableSpec(
        path="results/derived_results_audit.csv",
        min_rows=10,
        required_columns=("artifact", "check", "status", "detail", "observed", "expected"),
        required_values=(RequiredValues("status", ("pass",)),),
    ),
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


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def source_tree_hash(root: Path | str = ".") -> str:
    root_path = Path(root).resolve()
    digest = hashlib.sha256()
    include_roots = [
        root_path / "bodyshield",
        root_path / "scripts",
        root_path / "tests",
        root_path / "configs",
        root_path / "pyproject.toml",
    ]
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
        digest.update(str(path.relative_to(root_path)).replace("\\", "/").encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def _load_csv(path: Path, cache: dict[str, pd.DataFrame], root: Path) -> pd.DataFrame:
    rel = _rel(path, root)
    if rel not in cache:
        cache[rel] = pd.read_csv(path)
    return cache[rel]


def _csv_generic_rows(root: Path, cache: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((root / "results").glob("*.csv")):
        rel = _rel(path, root)
        if rel == SELF_AUDIT_CSV or rel in PACK_SIDE_DYNAMIC_CSVS:
            continue
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(rel, "csv_exists_nonempty", "CSV missing or empty"))
            continue
        rows.append(_pass(rel, "csv_exists_nonempty", "CSV exists and is nonempty", str(path.stat().st_size), ">0 bytes"))
        try:
            df = _load_csv(path, cache, root)
        except Exception as exc:  # pragma: no cover - defensive reporting path
            rows.append(_fail(rel, "csv_parse", f"could not parse CSV: {exc}"))
            continue
        rows.append(_pass(rel, "csv_parse", "CSV parsed", f"{len(df)} rows; {len(df.columns)} columns"))
        if len(df) == 0:
            rows.append(_fail(rel, "csv_nonempty_rows", "CSV has no data rows", "0", ">0"))
        else:
            rows.append(_pass(rel, "csv_nonempty_rows", "CSV has data rows", str(len(df)), ">0"))
        duplicate_columns = sorted({column for column in df.columns if list(df.columns).count(column) > 1})
        if duplicate_columns:
            rows.append(_fail(rel, "csv_unique_columns", f"duplicate columns: {duplicate_columns}"))
        else:
            rows.append(_pass(rel, "csv_unique_columns", "column names are unique"))
    return rows


def _check_table_spec(root: Path, cache: dict[str, pd.DataFrame], spec: TableSpec) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    path = root / spec.path
    if not path.exists():
        return [_fail(spec.path, "spec_file_exists", "required table is missing")]
    try:
        df = _load_csv(path, cache, root)
    except Exception as exc:
        return [_fail(spec.path, "spec_csv_parse", f"could not parse required table: {exc}")]

    missing_columns = [column for column in spec.required_columns if column not in df.columns]
    if missing_columns:
        rows.append(_fail(spec.path, "required_columns", f"missing columns: {missing_columns}"))
    else:
        rows.append(_pass(spec.path, "required_columns", "required columns present", str(len(spec.required_columns))))

    if spec.exact_rows is not None:
        status = "pass" if len(df) == spec.exact_rows else "fail"
        rows.append(
            _row(spec.path, "exact_row_count", status, "row count matches expected", str(len(df)), str(spec.exact_rows))
        )
    if spec.min_rows is not None:
        status = "pass" if len(df) >= spec.min_rows else "fail"
        rows.append(
            _row(spec.path, "minimum_row_count", status, "row count meets minimum", str(len(df)), f">={spec.min_rows}")
        )

    for column in spec.required_non_null:
        if column not in df.columns:
            rows.append(_fail(spec.path, f"non_null:{column}", "column missing"))
            continue
        missing = int(df[column].isna().sum())
        status = "pass" if missing == 0 else "fail"
        rows.append(_row(spec.path, f"non_null:{column}", status, "required column has no nulls", str(missing), "0"))

    if spec.unique_columns:
        missing = [column for column in spec.unique_columns if column not in df.columns]
        if missing:
            rows.append(_fail(spec.path, "unique_key", f"unique-key columns missing: {missing}"))
        else:
            duplicates = int(df.duplicated(list(spec.unique_columns)).sum())
            status = "pass" if duplicates == 0 else "fail"
            rows.append(
                _row(
                    spec.path,
                    "unique_key",
                    status,
                    f"unique key {list(spec.unique_columns)} has no duplicates",
                    str(duplicates),
                    "0",
                )
            )

    for value_spec in spec.required_values:
        if value_spec.column not in df.columns:
            rows.append(_fail(spec.path, f"required_values:{value_spec.column}", "column missing"))
            continue
        present = {str(value) for value in df[value_spec.column].dropna().unique()}
        expected = set(value_spec.values)
        missing = sorted(expected - present)
        status = "pass" if not missing else "fail"
        rows.append(
            _row(
                spec.path,
                f"required_values:{value_spec.column}",
                status,
                f"missing required values: {missing}" if missing else "required values present",
                ",".join(sorted(present)),
                ",".join(value_spec.values),
            )
        )

    for value_spec in spec.allowed_values:
        if value_spec.column not in df.columns:
            rows.append(_fail(spec.path, f"allowed_values:{value_spec.column}", "column missing"))
            continue
        present = {str(value) for value in df[value_spec.column].dropna().unique()}
        allowed = set(value_spec.values)
        unexpected = sorted(present - allowed)
        status = "pass" if not unexpected else "fail"
        rows.append(
            _row(
                spec.path,
                f"allowed_values:{value_spec.column}",
                status,
                f"unexpected values: {unexpected}" if unexpected else "only allowed values present",
                ",".join(sorted(present)),
                ",".join(value_spec.values),
            )
        )

    for range_spec in spec.numeric_ranges:
        if range_spec.column not in df.columns:
            rows.append(_fail(spec.path, f"numeric_range:{range_spec.column}", "column missing"))
            continue
        values = pd.to_numeric(df[range_spec.column], errors="coerce").dropna()
        if values.empty:
            rows.append(_fail(spec.path, f"numeric_range:{range_spec.column}", "no numeric values"))
            continue
        low_ok = True if range_spec.low is None else bool((values >= range_spec.low).all())
        high_ok = True if range_spec.high is None else bool((values <= range_spec.high).all())
        observed = f"min={values.min():.6g}; max={values.max():.6g}"
        expected = f"[{range_spec.low if range_spec.low is not None else '-inf'}, {range_spec.high if range_spec.high is not None else 'inf'}]"
        rows.append(
            _row(
                spec.path,
                f"numeric_range:{range_spec.column}",
                "pass" if low_ok and high_ok else "fail",
                "numeric values are within range",
                observed,
                expected,
            )
        )
    return rows


def _json_and_parquet_rows(root: Path, cache: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_code_hash = source_tree_hash(root)

    sample_path = root / "results" / "trials_sample.jsonl"
    if not sample_path.exists() or sample_path.stat().st_size <= 0:
        rows.append(_fail("results/trials_sample.jsonl", "jsonl_exists_nonempty", "JSONL sample missing or empty"))
    else:
        trial_ids: set[str] = set()
        metadata_hashes: set[str] = set()
        count = 0
        bad_line = ""
        required_sample_keys = {
            "trial_id",
            "phase",
            "task_id",
            "robot_id",
            "method_id",
            "perturbation",
            "result",
            "safety",
            "verifier",
            "metadata",
        }
        with sample_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                count += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    bad_line = f"line {line_number}: {exc}"
                    break
                trial_id = str(record.get("trial_id", ""))
                if trial_id:
                    trial_ids.add(trial_id)
                metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
                code_hash = metadata.get("code_commit_hash")
                if code_hash:
                    metadata_hashes.add(str(code_hash))
                if not required_sample_keys <= set(record):
                    bad_line = f"line {line_number}: missing top-level sample keys"
                    break
        if bad_line:
            rows.append(_fail("results/trials_sample.jsonl", "jsonl_parse_and_shape", bad_line))
        else:
            rows.append(_pass("results/trials_sample.jsonl", "jsonl_parse_and_shape", "JSONL sample parsed with nested keys", str(count)))
            rows.append(_row("results/trials_sample.jsonl", "jsonl_exact_rows", "pass" if count == 2000 else "fail", "sample row count", str(count), "2000"))
            rows.append(
                _row(
                    "results/trials_sample.jsonl",
                    "jsonl_unique_trial_ids",
                    "pass" if len(trial_ids) == count else "fail",
                    "sample trial IDs are unique",
                    str(len(trial_ids)),
                    str(count),
                )
            )
            rows.append(
                _row(
                    "results/trials_sample.jsonl",
                    "jsonl_metadata_code_hash",
                    "pass" if metadata_hashes == {current_code_hash} else "fail",
                    "sample metadata code hash matches current source tree",
                    ",".join(sorted(metadata_hashes)),
                    current_code_hash,
                )
            )

    summary_path = root / "results" / "schema_validation_summary.json"
    if not summary_path.exists():
        rows.append(_fail("results/schema_validation_summary.json", "schema_summary_exists", "schema summary missing"))
    else:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            ok = (
                summary.get("lightweight_validated_records") == 1_152_000
                and summary.get("jsonschema_validated_sample_records") == 200
                and summary.get("parquet_status") == "written"
            )
            rows.append(
                _row(
                    "results/schema_validation_summary.json",
                    "schema_summary_values",
                    "pass" if ok else "fail",
                    "schema validation summary has expected counts/status",
                    json.dumps(summary, sort_keys=True),
                    "1,152,000 lightweight; 200 jsonschema; parquet written",
                )
            )
        except json.JSONDecodeError as exc:
            rows.append(_fail("results/schema_validation_summary.json", "schema_summary_parse", f"invalid JSON: {exc}"))

    parquet_path = root / "results" / "trials.parquet"
    if not parquet_path.exists() or parquet_path.stat().st_size <= 0:
        rows.append(_fail("results/trials.parquet", "parquet_exists_nonempty", "Parquet file missing or empty"))
    else:
        try:
            import pyarrow.parquet as pq

            parquet_file = pq.ParquetFile(parquet_path)
            parquet_rows = int(parquet_file.metadata.num_rows)
            trial_df = _load_csv(root / "results" / "trials.csv", cache, root)
            csv_rows = len(trial_df)
            rows.append(
                _row(
                    "results/trials.parquet",
                    "parquet_rows_match_trials_csv",
                    "pass" if parquet_rows == csv_rows == 1_152_000 else "fail",
                    "Parquet metadata row count matches trials.csv",
                    f"parquet={parquet_rows}; csv={csv_rows}",
                    "1152000",
                )
            )
        except Exception as exc:
            rows.append(_fail("results/trials.parquet", "parquet_metadata_read", f"could not inspect Parquet metadata: {exc}"))

    return rows


def run_results_integrity_audit(
    root: Path | str = ".",
    specs: tuple[TableSpec, ...] = TABLE_SPECS,
    include_pack_side_checks: bool = True,
) -> pd.DataFrame:
    root_path = Path(root).resolve()
    cache: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, str]] = []
    rows.extend(_csv_generic_rows(root_path, cache))
    for spec in specs:
        rows.extend(_check_table_spec(root_path, cache, spec))
    if include_pack_side_checks:
        rows.extend(_json_and_parquet_rows(root_path, cache))
    return pd.DataFrame(rows)


def results_integrity_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "failed": 0, "passed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "failed": int((statuses != "pass").sum()),
        "passed": int((statuses == "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_integrity_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_results_integrity_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = results_integrity_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_integrity_rows(rows)
    display = failures if not failures.empty else rows.head(80)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Results Integrity Audit

Status: `{status}`

This audit checks generated result tables for parseability, nonempty rows, duplicate-column corruption, expected row counts, required columns, key uniqueness, required categorical values, numeric ranges, JSONL sample shape, schema-summary counts, and Parquet row-count agreement.

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


def write_results_integrity_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_results_integrity_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "results_integrity_audit.csv", index=False)
    write_results_integrity_report(reports / "RESULTS_INTEGRITY_AUDIT.md", rows)
    return rows
