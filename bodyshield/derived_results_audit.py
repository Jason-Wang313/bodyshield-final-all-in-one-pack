"""Recompute derived result tables from primary trial outputs."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from bodyshield.sim import stable_seed
from bodyshield.stats import bootstrap_mean_ci, profile_auc, wilson_interval


TRIAL_COLUMNS: tuple[str, ...] = (
    "method_id",
    "bucket",
    "success",
    "execution_time_s",
    "path_length_m",
    "retries",
    "workspace_violation",
    "max_tracking_error",
    "max_current_or_load",
    "verifier_confidence",
    "failure_category",
    "perturbation_family",
    "perturbation_cost",
)
FLOAT_TOLERANCE = 1e-10


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


def _key_set(df: pd.DataFrame, keys: tuple[str, ...]) -> set[tuple[str, ...]]:
    if df.empty:
        return set()
    return {tuple(str(row[key]) for key in keys) for _, row in df[list(keys)].iterrows()}


def _max_abs_diff(left: pd.Series, right: pd.Series) -> float:
    left_values = pd.to_numeric(left, errors="coerce").to_numpy(dtype=float)
    right_values = pd.to_numeric(right, errors="coerce").to_numpy(dtype=float)
    both_nan = np.isnan(left_values) & np.isnan(right_values)
    diffs = np.abs(left_values - right_values)
    diffs[both_nan] = 0.0
    if len(diffs) == 0:
        return 0.0
    return float(np.nanmax(diffs))


def _compare_table(
    artifact: str,
    expected: pd.DataFrame,
    observed: pd.DataFrame,
    key_columns: tuple[str, ...],
    numeric_columns: tuple[str, ...],
    string_columns: tuple[str, ...] = (),
    tolerance: float = FLOAT_TOLERANCE,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    missing_columns = sorted(set(key_columns + numeric_columns + string_columns) - set(observed.columns))
    rows.append(
        _row(
            artifact,
            "derived_table_required_columns_present",
            "pass" if not missing_columns else "fail",
            f"missing columns={missing_columns}",
            observed=str(len(observed.columns)),
            expected=str(len(set(key_columns + numeric_columns + string_columns))),
        )
    )
    if missing_columns:
        return rows

    expected_keys = _key_set(expected, key_columns)
    observed_keys = _key_set(observed, key_columns)
    missing_keys = sorted(expected_keys - observed_keys)
    extra_keys = sorted(observed_keys - expected_keys)
    rows.append(
        _row(
            artifact,
            "derived_table_key_set_matches",
            "pass" if not missing_keys and not extra_keys else "fail",
            f"missing_keys={missing_keys[:12]}; extra_keys={extra_keys[:12]}",
            observed=str(len(observed_keys)),
            expected=str(len(expected_keys)),
        )
    )
    if missing_keys or extra_keys:
        return rows

    expected_sorted = expected.sort_values(list(key_columns)).reset_index(drop=True)
    observed_sorted = observed.sort_values(list(key_columns)).reset_index(drop=True)
    merged = expected_sorted.merge(observed_sorted, on=list(key_columns), how="inner", suffixes=("_expected", "_observed"))

    bad_numeric: list[str] = []
    max_diffs: list[str] = []
    for column in numeric_columns:
        diff = _max_abs_diff(merged[f"{column}_expected"], merged[f"{column}_observed"])
        max_diffs.append(f"{column}={diff:.3g}")
        if math.isnan(diff) or diff > tolerance:
            bad_numeric.append(f"{column}:{diff:.6g}")
    rows.append(
        _row(
            artifact,
            "derived_table_numeric_values_match",
            "pass" if not bad_numeric else "fail",
            f"bad numeric columns={bad_numeric[:12]}",
            observed="; ".join(max_diffs),
            expected=f"max_abs_diff<={tolerance:g}",
        )
    )

    bad_strings: list[str] = []
    for column in string_columns:
        left = merged[f"{column}_expected"].astype(str).fillna("")
        right = merged[f"{column}_observed"].astype(str).fillna("")
        mismatches = int((left != right).sum())
        if mismatches:
            bad_strings.append(f"{column}:{mismatches}")
    if string_columns:
        rows.append(
            _row(
                artifact,
                "derived_table_string_values_match",
                "pass" if not bad_strings else "fail",
                f"bad string columns={bad_strings[:12]}",
                observed=str(sum(int(item.split(':')[1]) for item in bad_strings) if bad_strings else 0),
                expected="0",
            )
        )
    return rows


def success_delta_interval(successes_a: int, n_a: int, successes_b: int, n_b: int, z: float = 1.96) -> tuple[float, float, float]:
    if n_a == 0 or n_b == 0:
        return (float("nan"), float("nan"), float("nan"))
    p_a = successes_a / n_a
    p_b = successes_b / n_b
    delta = p_a - p_b
    se = math.sqrt((p_a * (1.0 - p_a) / n_a) + (p_b * (1.0 - p_b) / n_b))
    return (delta, delta - z * se, delta + z * se)


def load_trials(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    return pd.read_csv(root_path / "results" / "trials.csv", usecols=list(TRIAL_COLUMNS), keep_default_na=False)


def recompute_summary_by_method_bucket(trials: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for keys, group in trials.groupby(["method_id", "bucket"], sort=True):
        method_id, bucket = keys
        successes = int(group["success"].sum())
        n = int(len(group))
        lo, hi = wilson_interval(successes, n)
        rows.append(
            {
                "method_id": method_id,
                "bucket": bucket,
                "n": n,
                "successes": successes,
                "success_rate": successes / n,
                "ci_low": lo,
                "ci_high": hi,
                "mean_execution_time_s": group["execution_time_s"].mean(),
                "mean_path_length_m": group["path_length_m"].mean(),
                "mean_retries": group["retries"].mean(),
                "workspace_violation_rate": group["workspace_violation"].mean(),
            }
        )
    return pd.DataFrame(rows)


def recompute_robustness_profiles(trials: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for keys, group in trials.groupby(["method_id", "perturbation_family"], sort=True):
        method_id, family = keys
        by_cost = group.groupby("perturbation_cost")["success"].mean().reset_index()
        auc = profile_auc(by_cost["perturbation_cost"], by_cost["success"])
        lo, hi = bootstrap_mean_ci(by_cost["success"], seed=stable_seed("auc", method_id, family))
        rows.append(
            {
                "method_id": method_id,
                "perturbation_family": family,
                "profile_auc": auc,
                "bootstrap_low": lo,
                "bootstrap_high": hi,
            }
        )
    return pd.DataFrame(rows)


def recompute_secondary_metrics(trials: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for method_id, group in trials.groupby("method_id", sort=True):
        rows.append(
            {
                "method_id": method_id,
                "mean_execution_time_s": group["execution_time_s"].mean(),
                "mean_path_length_m": group["path_length_m"].mean(),
                "mean_retries": group["retries"].mean(),
                "mean_tracking_error": group["max_tracking_error"].mean(),
                "mean_current_or_load": group["max_current_or_load"].mean(),
                "workspace_violation_rate": group["workspace_violation"].mean(),
                "verifier_confidence": group["verifier_confidence"].mean(),
            }
        )
    return pd.DataFrame(rows)


def recompute_failure_taxonomy_counts(trials: pd.DataFrame) -> pd.DataFrame:
    return (
        trials[trials["success"] == 0]
        .groupby(["method_id", "failure_category"], as_index=False, sort=True)
        .size()
        .rename(columns={"size": "failures"})
    )


def recompute_method_deltas(summary: pd.DataFrame) -> pd.DataFrame:
    bodyshield = summary[summary["method_id"] == "bodyshield"].set_index("bucket")
    rows: list[dict[str, float | int | str]] = []
    for _, row in summary[summary["method_id"] != "bodyshield"].sort_values(["method_id", "bucket"]).iterrows():
        bucket = row["bucket"]
        if bucket not in bodyshield.index:
            continue
        bs = bodyshield.loc[bucket]
        delta, low, high = success_delta_interval(
            int(bs["successes"]),
            int(bs["n"]),
            int(row["successes"]),
            int(row["n"]),
        )
        rows.append(
            {
                "baseline_method": row["method_id"],
                "bucket": bucket,
                "bodyshield_success_rate": float(bs["success_rate"]),
                "baseline_success_rate": float(row["success_rate"]),
                "delta_success_rate": delta,
                "delta_ci_low": low,
                "delta_ci_high": high,
                "bodyshield_n": int(bs["n"]),
                "baseline_n": int(row["n"]),
                "bodyshield_execution_time_s": float(bs["mean_execution_time_s"]),
                "baseline_execution_time_s": float(row["mean_execution_time_s"]),
                "delta_execution_time_s": float(bs["mean_execution_time_s"] - row["mean_execution_time_s"]),
                "bodyshield_path_length_m": float(bs["mean_path_length_m"]),
                "baseline_path_length_m": float(row["mean_path_length_m"]),
                "delta_path_length_m": float(bs["mean_path_length_m"] - row["mean_path_length_m"]),
            }
        )
    return pd.DataFrame(rows)


def _read_output(root: Path, rel_path: str) -> pd.DataFrame:
    return pd.read_csv(root / rel_path, keep_default_na=False)


def run_derived_results_audit(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    trials_path = root_path / "results" / "trials.csv"
    if not trials_path.exists() or trials_path.stat().st_size <= 0:
        return pd.DataFrame([_fail("results/trials.csv", "primary_trials_exists_nonempty", "primary trials CSV is missing or empty")])

    trials = load_trials(root_path)
    rows.append(_pass("results/trials.csv", "primary_trials_exists_nonempty", "primary trials CSV exists and was loaded", observed=str(len(trials)), expected=">0 rows"))

    expected_summary = recompute_summary_by_method_bucket(trials)
    observed_summary = _read_output(root_path, "results/summary_by_method_bucket.csv")
    rows.extend(
        _compare_table(
            "results/summary_by_method_bucket.csv",
            expected_summary,
            observed_summary,
            ("method_id", "bucket"),
            (
                "n",
                "successes",
                "success_rate",
                "ci_low",
                "ci_high",
                "mean_execution_time_s",
                "mean_path_length_m",
                "mean_retries",
                "workspace_violation_rate",
            ),
        )
    )

    expected_profiles = recompute_robustness_profiles(trials)
    observed_profiles = _read_output(root_path, "results/robustness_profiles.csv")
    rows.extend(
        _compare_table(
            "results/robustness_profiles.csv",
            expected_profiles,
            observed_profiles,
            ("method_id", "perturbation_family"),
            ("profile_auc", "bootstrap_low", "bootstrap_high"),
        )
    )

    expected_secondary = recompute_secondary_metrics(trials)
    observed_secondary = _read_output(root_path, "results/secondary_metrics_by_method.csv")
    rows.extend(
        _compare_table(
            "results/secondary_metrics_by_method.csv",
            expected_secondary,
            observed_secondary,
            ("method_id",),
            (
                "mean_execution_time_s",
                "mean_path_length_m",
                "mean_retries",
                "mean_tracking_error",
                "mean_current_or_load",
                "workspace_violation_rate",
                "verifier_confidence",
            ),
        )
    )

    expected_failures = recompute_failure_taxonomy_counts(trials)
    observed_failures = _read_output(root_path, "results/failure_taxonomy_counts.csv")
    rows.extend(
        _compare_table(
            "results/failure_taxonomy_counts.csv",
            expected_failures,
            observed_failures,
            ("method_id", "failure_category"),
            ("failures",),
        )
    )

    expected_deltas = recompute_method_deltas(expected_summary)
    observed_deltas = _read_output(root_path, "results/method_deltas_vs_bodyshield.csv")
    rows.extend(
        _compare_table(
            "results/method_deltas_vs_bodyshield.csv",
            expected_deltas,
            observed_deltas,
            ("baseline_method", "bucket"),
            (
                "bodyshield_success_rate",
                "baseline_success_rate",
                "delta_success_rate",
                "delta_ci_low",
                "delta_ci_high",
                "bodyshield_n",
                "baseline_n",
                "bodyshield_execution_time_s",
                "baseline_execution_time_s",
                "delta_execution_time_s",
                "bodyshield_path_length_m",
                "baseline_path_length_m",
                "delta_path_length_m",
            ),
        )
    )
    return pd.DataFrame(rows)


def derived_results_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_derived_results_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_derived_results_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = derived_results_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_derived_results_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Derived Results Audit

Status: `{status}`

This audit recomputes generated summary tables from `results/trials.csv` and checks that the shipped summaries, robustness profiles, secondary metrics, failure taxonomy, and BodyShield-vs-baseline deltas match the primary trial table.

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


def write_derived_results_audit_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_derived_results_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "derived_results_audit.csv", index=False)
    write_derived_results_report(reports / "DERIVED_RESULTS_AUDIT.md", rows)
    return rows
