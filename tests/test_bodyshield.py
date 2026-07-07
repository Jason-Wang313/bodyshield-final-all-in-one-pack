import json
import hashlib
import shutil
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw
from pypdf import PdfWriter

from bodyshield.bodybreak_search import find_minimal_breaking_perturbation
from bodyshield.bodyshield_repair import repair_policy
from bodyshield.artifact_inventory_audit import (
    expected_artifact_manifest_paths,
    failed_artifact_inventory_rows,
    run_artifact_inventory_audit,
)
from bodyshield.claim_boundary_audit import DocumentRequirement, failed_claim_boundary_rows, run_claim_boundary_audit
from bodyshield.command_surface_audit import failed_command_surface_rows, parse_python_commands, run_command_surface_audit
from bodyshield.config_schema_audit import failed_config_schema_rows, run_config_schema_audit
from bodyshield.corrective_adaptation import fit_corrective_trace_adapter
from bodyshield.corrective_trace_readiness import run_corrective_trace_readiness
from bodyshield.derived_results_audit import (
    failed_derived_results_rows,
    recompute_failure_taxonomy_counts,
    recompute_method_deltas,
    recompute_robustness_profiles,
    recompute_secondary_metrics,
    recompute_summary_by_method_bucket,
    run_derived_results_audit,
)
from bodyshield.evidence_consistency import extract_local_references, failed_references, run_evidence_consistency_audit
from bodyshield.environment_audit import failed_environment_rows, run_environment_dependency_audit, write_environment_dependency_reports
from bodyshield.external_policy_benchmark import run_external_policy_benchmark
from bodyshield.high_fidelity import run_maniskill_pushcube_probe, run_mujoco_planar_arm_suite, run_mujoco_push_probe
from bodyshield.high_fidelity_learning import fit_mujoco_planar_residual_policy
from bodyshield.learned_outcome_model import fit_learned_outcome_model
from bodyshield.neural_wam import fit_neural_latent_wam, visual_latent_from_frame
from bodyshield.paper_source_audit import failed_paper_source_rows, run_paper_source_audit
from bodyshield.perturbations import AXES, Perturbation, axis_level_perturbations
from bodyshield.policies import default_policies
from bodyshield.portable_hygiene_audit import failed_portable_hygiene_rows, run_portable_hygiene_audit
from bodyshield.real_video_wam_readiness import run_real_video_wam_readiness
from bodyshield.release_bundle import iter_payload_files, validate_release_payload, inspect_release_bundle, write_release_bundle
from bodyshield.release_determinism_audit import (
    failed_release_determinism_rows,
    reconstruct_release_zip_bytes,
    run_release_determinism_audit,
)
from bodyshield.release_payload_audit import failed_release_payload_rows, run_release_payload_audit
from bodyshield.release_runtime_audit import failed_release_runtime_rows, run_release_runtime_audit
from bodyshield.results_integrity import (
    NumericRange,
    RequiredValues,
    TableSpec,
    failed_integrity_rows,
    run_results_integrity_audit,
)
from bodyshield.schema import validate_trial, validate_trial_jsonschema
from bodyshield.source_import_audit import failed_source_import_rows, run_source_import_audit
from bodyshield.sim_envs import check_sim_envs
from bodyshield.sim import ROBOTS, TASKS, evaluate_rate, stable_seed, trial_records
from bodyshield.sim_videos import export_synthetic_rollout_videos
from bodyshield.tasks import TASK_CARDS
from bodyshield.trajectory_wam import fit_trajectory_wam_proxy, generate_synthetic_trajectory
from bodyshield.visual_artifact_audit import failed_visual_artifact_rows, run_visual_artifact_audit
from bodyshield.visual_wam import fit_visual_wam_proxy, render_synthetic_visual_frame
from scripts.run_non_hardware import audit_bodybreak_minimality, parse_perturbation_label


def test_perturbation_cost_nominal_zero():
    assert Perturbation().cost() == 0.0
    assert Perturbation({"latency_ms": 120}).cost() > 0.0
    assert Perturbation({"acceleration_cap_scale": 0.5}).cost() > 0.0
    assert Perturbation({"controller_rate_scale": 0.5}).cost() > 0.0
    assert Perturbation({"physical_gripper_restriction_mm": 10}).cost() > 0.0
    assert Perturbation({"obstacle_clearance_cm": 5}).cost() > 0.0


def test_all_planned_axes_have_axis_levels():
    covered = {family for family, _, _ in axis_level_perturbations()}
    for axis in AXES:
        if axis == "joint_lock":
            continue
        assert axis in covered or axis == "nominal"


def test_required_baselines_exist():
    policies = default_policies()
    for method_id in [
        "nominal",
        "random_tuning",
        "domain_randomization",
        "grid_worstcase",
        "robust_control",
        "sysid_retune",
        "oracle",
        "human_effect_prior",
        "epec",
    ]:
        assert method_id in policies


def test_bodybreak_finds_breaking_case():
    policies = default_policies()
    task = next(t for t in TASKS if t.task_id == "pick_place_bin")
    robot = next(r for r in ROBOTS if r.robot_id == "so101_urdf")

    def evaluator(z):
        return evaluate_rate(policies["nominal"], task, robot, z, n_trials=40, seed=stable_seed("test-search", z.label()))

    result = find_minimal_breaking_perturbation(None, None, evaluator, threshold=0.65, budget=50, mode="bodybreak", seed=3)
    assert result.cost > 0.0
    assert result.trials <= 50
    assert result.success_rate <= 0.80


def test_bodybreak_dense_minimality_audit_runs_for_tiny_case():
    parsed = parse_perturbation_label("latency_ms=40;calibration_offset_mm=5.0")
    assert parsed.canonical()["latency_ms"] == 40.0
    assert parsed.canonical()["calibration_offset_mm"] == 5.0

    policies = default_policies()
    task = next(t for t in TASKS if t.task_id == "pick_place_bin")
    robot = next(r for r in ROBOTS if r.robot_id == "so101_urdf")
    method_id = "nominal"

    def evaluator(z):
        return evaluate_rate(
            policies[method_id],
            task,
            robot,
            z,
            n_trials=40,
            seed=stable_seed("search", method_id, task.task_id, robot.robot_id, z.label()),
        )

    result = find_minimal_breaking_perturbation(None, None, evaluator, threshold=0.65, budget=50, mode="bodybreak", seed=3)
    assert result.notes == "found_break"
    search = pd.DataFrame(
        [
            {
                "method_id": method_id,
                "task_id": task.task_id,
                "robot_id": robot.robot_id,
                "search_mode": "bodybreak",
                "breaking_cost": result.cost,
                "success_rate": result.success_rate,
                "trials": result.trials,
                "perturbation": result.perturbation.label(),
                "active_axes": ",".join(result.perturbation.active_axes()),
                "notes": result.notes,
            }
        ]
    )
    audit = audit_bodybreak_minimality(search, policies, threshold=0.65, cases_per_method=1, random_budget=8, scale_steps=4)
    assert not audit.empty
    row = audit.iloc[0]
    assert row["bodybreak_perturbation"] == result.perturbation.label()
    assert row["dense_candidate_count"] > 0
    assert row["confirm_trials"] > 0
    assert row["audit_status"] in {
        "confirmed_lower_cost_break_found",
        "bodybreak_matches_confirmed_dense_pool",
        "no_lower_confirmed_break_bodybreak_not_confirmed",
        "no_confirmed_dense_break_found",
    }


def test_repair_improves_discovered_case():
    policies = default_policies()
    task = next(t for t in TASKS if t.task_id == "constrained_place")
    robot = next(r for r in ROBOTS if r.robot_id == "so101_urdf")
    z = Perturbation({"calibration_offset_mm": 20, "action_noise_std": 0.02})

    def evaluator(policy, perturbation):
        return evaluate_rate(policy, task, robot, perturbation, n_trials=60, seed=stable_seed("test-repair", policy.method_id, perturbation.label()))

    before = evaluator(policies["nominal"], z)
    repaired = repair_policy(policies["nominal"], [{"perturbation": z, "success_rate": before}], evaluator=evaluator, budget=30, seed=5).policy
    after = evaluator(repaired, z)
    assert after >= before


def test_trial_schema():
    policies = default_policies()
    record = trial_records(policies["nominal"], TASKS[0], ROBOTS[0], Perturbation(), n_trials=1, seed=11)[0]
    validate_trial(record)
    validate_trial_jsonschema(record)
    assert "path_length_m" in record["result"]
    assert "controller_rate_scale" in record["perturbation"]


def test_task_cards_cover_tasks():
    card_ids = {card.task_id for card in TASK_CARDS}
    task_ids = {task.task_id for task in TASKS}
    assert card_ids == task_ids


def test_sim_env_availability_shape():
    rows = check_sim_envs()
    assert {row["engine"] for row in rows} >= {"mujoco", "maniskill", "gymnasium"}
    assert all("installed" in row for row in rows)


def test_mujoco_probe_runs_for_one_seed():
    policies = default_policies()
    rows = run_mujoco_push_probe(policies, seeds=1)
    assert rows
    assert {row["engine"] for row in rows} == {"mujoco"}
    assert all(0.0 <= row["success_rate"] <= 1.0 for row in rows)


def test_mujoco_planar_probe_runs_for_one_seed():
    policies = default_policies()
    rows = run_mujoco_planar_arm_suite(policies, seeds=1)
    assert rows
    assert {row["engine"] for row in rows} == {"mujoco_planar"}
    assert all(0.0 <= row["success_rate"] <= 1.0 for row in rows)
    assert all("mean_final_error" in row for row in rows)


def test_mujoco_residual_policy_runs_for_tiny_grid():
    policies = default_policies()
    policies["bodyshield"] = policies["domain_randomization"].with_id("bodyshield")
    result = fit_mujoco_planar_residual_policy(
        policies,
        source_method_ids=("nominal", "bodyshield"),
        train_seeds=1,
        eval_seeds=1,
        sample_stride=32,
        trace_sample_limit=2,
    )
    assert not result.metrics.empty
    assert not result.rollouts.empty
    assert not result.residual_weights.empty
    assert result.trace_sample
    assert "bucket=heldout" in set(result.metrics["slice"])
    assert set(result.rollouts["split"]) == {"train_seen_or_nominal", "heldout"}
    assert result.rollouts["base_path_length"].mean() > 0.0
    assert result.rollouts["adapted_path_length"].mean() > 0.0
    assert not result.gate_ablation.empty
    assert {"residual_off", "always_on", "non_nominal_only", "gated_default"} <= set(result.gate_ablation["variant"])
    nominal = result.metrics[result.metrics["slice"] == "bucket=nominal"].iloc[0]
    assert nominal["adapted_success_rate"] >= nominal["base_success_rate"]
    heldout = result.metrics[result.metrics["slice"] == "bucket=heldout"].iloc[0]
    assert heldout["delta_final_error"] >= 0.0
    ablation_heldout = result.gate_ablation[result.gate_ablation["slice"] == "bucket=heldout"].set_index("variant")
    ablation_nominal = result.gate_ablation[result.gate_ablation["slice"] == "bucket=nominal"].set_index("variant")
    assert ablation_heldout.loc["gated_default", "delta_final_error"] >= ablation_heldout.loc["residual_off", "delta_final_error"]
    assert ablation_nominal.loc["gated_default", "delta_success_rate"] >= -1e-12


def test_maniskill_pushcube_probe_runs():
    rows = run_maniskill_pushcube_probe(steps=1)
    assert rows
    assert rows[0]["engine"] == "maniskill"
    assert rows[0]["task_id"] == "PushCube-v1"
    assert rows[0]["status"] in {"executed", "failed"}


def test_learned_outcome_model_runs_on_small_grid():
    policies = default_policies()
    conditions = [
        {"bucket": "nominal", "family": "nominal", "perturbation": Perturbation()},
        {"bucket": "seen", "family": "latency_ms", "perturbation": Perturbation({"latency_ms": 80})},
        {"bucket": "heldout", "family": "payload_g", "perturbation": Perturbation({"payload_g": 250})},
    ]
    result = fit_learned_outcome_model({"nominal": policies["nominal"], "bodyshield": policies["domain_randomization"].with_id("bodyshield")}, conditions, n_trials=8)
    assert not result.metrics.empty
    assert not result.axis_weights.empty
    assert not result.predictions.empty
    assert set(result.predictions["split"]) == {"train_seen_or_nominal", "heldout"}


def test_trajectory_wam_proxy_runs_on_small_grid():
    policies = default_policies()
    conditions = [
        {"bucket": "nominal", "family": "nominal", "level": "none", "perturbation": Perturbation()},
        {"bucket": "seen", "family": "latency_ms", "level": "medium", "perturbation": Perturbation({"latency_ms": 80})},
        {"bucket": "heldout", "family": "payload_g", "level": "heldout_medium", "perturbation": Perturbation({"payload_g": 250})},
    ]
    small_policies = {"nominal": policies["nominal"], "bodyshield": policies["domain_randomization"].with_id("bodyshield")}
    trace = generate_synthetic_trajectory(small_policies["nominal"], TASKS[0], ROBOTS[0], Perturbation(), steps=5)
    assert trace["states"].shape == (6, 4)
    assert trace["actions"].shape == (5, 2)
    result = fit_trajectory_wam_proxy(small_policies, conditions, steps=5, trace_sample_limit=4)
    assert not result.metrics.empty
    assert not result.axis_weights.empty
    assert not result.rollouts.empty
    assert result.trace_sample
    assert set(result.rollouts["split"]) == {"train_seen_or_nominal", "heldout"}


def test_corrective_trace_adapter_runs_on_small_grid():
    policies = default_policies()
    policies["bodyshield"] = policies["domain_randomization"].with_id("bodyshield")
    conditions = [
        {"bucket": "nominal", "family": "nominal", "level": "none", "perturbation": Perturbation()},
        {"bucket": "seen", "family": "latency_ms", "level": "medium", "perturbation": Perturbation({"latency_ms": 80})},
        {"bucket": "heldout", "family": "payload_g", "level": "heldout_medium", "perturbation": Perturbation({"payload_g": 250})},
    ]
    result = fit_corrective_trace_adapter(
        policies,
        conditions,
        source_method_ids=("nominal", "bodyshield"),
        steps=5,
        trace_sample_limit=4,
    )
    assert not result.metrics.empty
    assert not result.rollouts.empty
    assert not result.residual_weights.empty
    assert result.trace_sample
    assert set(result.rollouts["split"]) == {"train_seen_or_nominal", "heldout"}


def test_visual_wam_proxy_runs_on_small_grid():
    policies = default_policies()
    policies["bodyshield"] = policies["domain_randomization"].with_id("bodyshield")
    conditions = [
        {"bucket": "nominal", "family": "nominal", "level": "none", "perturbation": Perturbation()},
        {"bucket": "seen", "family": "latency_ms", "level": "medium", "perturbation": Perturbation({"latency_ms": 80})},
        {"bucket": "heldout", "family": "camera_shift_px", "level": "heldout_medium", "perturbation": Perturbation({"camera_shift_px": 40})},
    ]
    trace = generate_synthetic_trajectory(policies["nominal"], TASKS[0], ROBOTS[0], Perturbation(), steps=4)
    frame = render_synthetic_visual_frame(trace["states"][0], trace["target"], TASKS[0], Perturbation(), frame_size=8)
    assert frame.shape == (2, 8, 8)
    assert 0.0 <= frame.min() <= frame.max() <= 1.0
    result = fit_visual_wam_proxy(
        policies,
        conditions,
        source_method_ids=("nominal", "bodyshield"),
        steps=4,
        frame_size=8,
        trace_sample_limit=4,
    )
    assert not result.metrics.empty
    assert not result.rollouts.empty
    assert not result.feature_weights.empty
    assert result.trace_sample
    assert set(result.rollouts["split"]) == {"train_seen_or_nominal", "heldout"}


def test_synthetic_rollout_video_export_runs(tmp_path):
    policies = default_policies()
    policies["bodyshield"] = policies["domain_randomization"].with_id("bodyshield")
    task = next(t for t in TASKS if t.task_id == "constrained_place")
    robot = next(r for r in ROBOTS if r.robot_id == "so101_urdf")
    z = Perturbation({"calibration_offset_mm": 20, "action_noise_std": 0.02})
    manifest = export_synthetic_rollout_videos(
        policies,
        [{"task_id": task.task_id, "robot_id": robot.robot_id, "perturbation": z, "cost": z.cost()}],
        tmp_path,
        steps=4,
        frame_size=12,
    )
    assert set(manifest["artifact_id"]) == {"nominal_reference", "bodybreak_failure", "bodyshield_repair"}
    assert all("Synthetic generated rollout only" in value for value in manifest["evidence_boundary"])
    for path in manifest["path"]:
        image = Image.open(path)
        assert getattr(image, "n_frames", 1) == 5
        assert image.size[0] > 0 and image.size[1] > 0


def test_release_bundle_round_trip_excludes_cache_and_verifies_payload(tmp_path):
    for directory in ["bodyshield", "scripts", "configs", "results", "reports", "paper", "tmp"]:
        (tmp_path / directory).mkdir()
    (tmp_path / "bodyshield" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "bodyshield" / "__pycache__").mkdir()
    (tmp_path / "bodyshield" / "__pycache__" / "module.pyc").write_bytes(b"cache")
    (tmp_path / "scripts" / "run_non_hardware.py").write_text("print('run')\n", encoding="utf-8")
    (tmp_path / "scripts" / "verify_release_payload.py").write_text("print('verify payload')\n", encoding="utf-8")
    (tmp_path / "configs" / "spec.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "results" / "trials.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "reports" / "ARTIFACT_MANIFEST.csv").write_text("path,bytes,sha256\n", encoding="utf-8")
    (tmp_path / "paper" / "main.tex").write_text("\\section{x}\n", encoding="utf-8")
    (tmp_path / "tmp" / "scratch.txt").write_text("do not ship\n", encoding="utf-8")
    (tmp_path / "README_EXECUTION.md").write_text("# Run\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")

    result = write_release_bundle(tmp_path)
    required_payloads = [
        "README_EXECUTION.md",
        "bodyshield/module.py",
        "scripts/verify_release_payload.py",
        "results/trials.csv",
    ]
    inspection = inspect_release_bundle(
        tmp_path,
        required_payloads=required_payloads,
    )

    assert inspection["status"] == "pass"
    assert result.payload_files >= 6
    extracted = tmp_path / "extracted_release"
    with zipfile.ZipFile(tmp_path / result.zip_path) as bundle:
        bundle.extractall(extracted)
        names = set(bundle.namelist())
    payload = validate_release_payload(extracted, required_payloads=required_payloads)
    assert payload["status"] == "pass"
    assert "bodyshield/module.py" in names
    assert "RELEASE_BUNDLE_MANIFEST.csv" in names
    assert "scripts/verify_release_payload.py" in names
    assert "reports/ARTIFACT_MANIFEST.csv" not in names
    assert "bodyshield/__pycache__/module.pyc" not in names
    assert "tmp/scratch.txt" not in names


def _sha256_for_test(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv_manifest(path: Path, root: Path, rel_paths: list[str]) -> None:
    lines = ["path,bytes,sha256"]
    for rel_path in rel_paths:
        item = root / rel_path
        lines.append(f"{rel_path},{item.stat().st_size},{_sha256_for_test(item)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_inventory_fixture(root: Path) -> None:
    for directory in ["results", "reports", "paper", "release"]:
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / "results" / "demo.csv").write_text("id,value\nrow1,1\n", encoding="utf-8")
    (root / "reports" / "doc.md").write_text("# Doc\n", encoding="utf-8")
    (root / "paper" / "main.tex").write_text("\\section{Demo}\n", encoding="utf-8")
    readme = (
        "- `results/demo.csv`\n"
        "- `reports/doc.md`\n"
        "- `paper/main.tex`\n"
        "- `results/artifact_inventory_audit.csv`\n"
        "- `reports/ARTIFACT_INVENTORY_AUDIT.md`\n"
    )
    (root / "README_EXECUTION.md").write_text(readme, encoding="utf-8")
    (root / "data_schema.json").write_text("{}\n", encoding="utf-8")
    (root / "trial_schema.schema.json").write_text("{}\n", encoding="utf-8")
    (root / "reports" / "REPRODUCIBILITY_MANIFEST.md").write_text(readme, encoding="utf-8")
    (root / "reports" / "NON_HARDWARE_COMPLETE.md").write_text(readme, encoding="utf-8")

    release_paths = sorted(path.relative_to(root).as_posix() for path in iter_payload_files(root))
    _write_csv_manifest(root / "release" / "RELEASE_BUNDLE_MANIFEST.csv", root, release_paths)
    artifact_paths = sorted(expected_artifact_manifest_paths(root))
    _write_csv_manifest(root / "reports" / "ARTIFACT_MANIFEST.csv", root, artifact_paths)


def test_artifact_inventory_audit_passes_manifest_and_documented_output_sync(tmp_path):
    _write_inventory_fixture(tmp_path)

    rows = run_artifact_inventory_audit(tmp_path)

    assert failed_artifact_inventory_rows(rows).empty
    checks = set(rows["check"])
    assert "artifact_manifest_exact_current_generated_set" in checks
    assert "release_manifest_exact_current_payload_set" in checks
    assert "documented_output_in_release_manifest_when_eligible" in checks


def test_artifact_inventory_audit_reports_manifest_and_documentation_drift(tmp_path):
    _write_inventory_fixture(tmp_path)
    (tmp_path / "README_EXECUTION.md").write_text("- `results/missing.csv`\n- `results/demo.csv`\n", encoding="utf-8")
    (tmp_path / "reports" / "ARTIFACT_MANIFEST.csv").write_text("path,bytes,sha256\nreports/doc.md,1,bad\n", encoding="utf-8")
    (tmp_path / "release" / "RELEASE_BUNDLE_MANIFEST.csv").write_text("path,bytes,sha256\nREADME_EXECUTION.md,1,bad\n", encoding="utf-8")

    rows = run_artifact_inventory_audit(tmp_path)
    failures = failed_artifact_inventory_rows(rows)

    assert "artifact_manifest_exact_current_generated_set" in set(failures["check"])
    assert "artifact_manifest_hashes_match_current_files" in set(failures["check"])
    assert "release_manifest_exact_current_payload_set" in set(failures["check"])
    assert "release_manifest_hashes_match_current_files" in set(failures["check"])
    assert "documented_output_exists_nonempty" in set(failures["check"])


def test_release_payload_audit_extracts_and_runs_bundled_verifier(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    for directory in ["bodyshield", "scripts", "configs", "results", "reports", "paper"]:
        (tmp_path / directory).mkdir()
    shutil.copy2(project_root / "bodyshield" / "__init__.py", tmp_path / "bodyshield" / "__init__.py")
    shutil.copy2(project_root / "bodyshield" / "release_bundle.py", tmp_path / "bodyshield" / "release_bundle.py")
    shutil.copy2(project_root / "scripts" / "verify_release_payload.py", tmp_path / "scripts" / "verify_release_payload.py")
    (tmp_path / "README_EXECUTION.md").write_text("# Run\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")
    (tmp_path / "results" / "trials.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "reports" / "ARTIFACT_MANIFEST.csv").write_text("path,bytes,sha256\n", encoding="utf-8")
    (tmp_path / "paper" / "main.tex").write_text("\\section{x}\n", encoding="utf-8")

    result = write_release_bundle(tmp_path)
    required_payloads = [
        "README_EXECUTION.md",
        "bodyshield/release_bundle.py",
        "scripts/verify_release_payload.py",
        "results/trials.csv",
    ]

    rows = run_release_payload_audit(tmp_path, required_payloads=required_payloads, timeout_s=20)
    failures = failed_release_payload_rows(rows)

    assert failures.empty
    assert "bundled_verifier_json_status" in set(rows["check"])
    extracted = tmp_path / "extracted_release"
    with zipfile.ZipFile(tmp_path / result.zip_path) as bundle:
        bundle.extractall(extracted)
    extracted_rows = run_release_payload_audit(extracted, required_payloads=required_payloads, timeout_s=20)
    assert failed_release_payload_rows(extracted_rows).empty


def test_release_payload_audit_reports_missing_release_zip(tmp_path):
    rows = run_release_payload_audit(tmp_path, required_payloads=("README_EXECUTION.md",), timeout_s=5)
    failures = failed_release_payload_rows(rows)

    assert "release_zip_exists_nonempty" in set(failures["check"])


def test_release_determinism_audit_reconstructs_exact_zip_bytes(tmp_path):
    for directory in ["bodyshield", "scripts", "configs", "results", "reports", "paper"]:
        (tmp_path / directory).mkdir()
    (tmp_path / "bodyshield" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "scripts" / "verify_release_payload.py").write_text("print('verify payload')\n", encoding="utf-8")
    (tmp_path / "results" / "trials.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "results" / "release_payload_audit.csv").write_text("dynamic,excluded\n1,yes\n", encoding="utf-8")
    (tmp_path / "reports" / "ARTIFACT_MANIFEST.csv").write_text("path,bytes,sha256\n", encoding="utf-8")
    (tmp_path / "reports" / "RELEASE_PAYLOAD_AUDIT.md").write_text("# dynamic\n", encoding="utf-8")
    (tmp_path / "paper" / "main.tex").write_text("\\section{x}\n", encoding="utf-8")
    (tmp_path / "README_EXECUTION.md").write_text("# Run\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")

    result = write_release_bundle(tmp_path)
    rows = run_release_determinism_audit(tmp_path)
    failures = failed_release_determinism_rows(rows)

    assert failures.empty
    assert reconstruct_release_zip_bytes(tmp_path) == (tmp_path / result.zip_path).read_bytes()
    with zipfile.ZipFile(tmp_path / result.zip_path) as bundle:
        names = set(bundle.namelist())
    assert "reports/ARTIFACT_MANIFEST.csv" not in names
    assert "reports/RELEASE_PAYLOAD_AUDIT.md" not in names
    assert "results/release_payload_audit.csv" not in names


def test_release_determinism_audit_detects_payload_drift(tmp_path):
    for directory in ["bodyshield", "scripts", "results", "reports", "paper"]:
        (tmp_path / directory).mkdir()
    (tmp_path / "bodyshield" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "scripts" / "verify_release_payload.py").write_text("print('verify payload')\n", encoding="utf-8")
    (tmp_path / "results" / "trials.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "paper" / "main.tex").write_text("\\section{x}\n", encoding="utf-8")
    (tmp_path / "README_EXECUTION.md").write_text("# Run\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")

    write_release_bundle(tmp_path)
    (tmp_path / "bodyshield" / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    rows = run_release_determinism_audit(tmp_path)
    failures = failed_release_determinism_rows(rows)

    assert "current_payload_hashes_match_manifest" in set(failures["check"])
    assert "reconstructed_zip_sha256_matches" in set(failures["check"])


def test_release_runtime_audit_runs_pytest_inside_extracted_release(tmp_path):
    for directory in ["bodyshield", "scripts", "results", "reports", "paper", "tests"]:
        (tmp_path / directory).mkdir()
    (tmp_path / "bodyshield" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "bodyshield" / "demo.py").write_text("VALUE = 3\n", encoding="utf-8")
    (tmp_path / "scripts" / "verify_release_payload.py").write_text("print('verify payload')\n", encoding="utf-8")
    (tmp_path / "results" / "trials.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "paper" / "main.tex").write_text("\\section{x}\n", encoding="utf-8")
    (tmp_path / "tests" / "test_demo.py").write_text("from bodyshield.demo import VALUE\n\ndef test_value():\n    assert VALUE == 3\n", encoding="utf-8")
    (tmp_path / "README_EXECUTION.md").write_text("# Run\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")

    write_release_bundle(tmp_path)
    rows = run_release_runtime_audit(tmp_path, timeout_s=30)
    failures = failed_release_runtime_rows(rows)

    assert failures.empty
    assert "extracted_pytest_returncode" in set(rows["check"])
    assert rows.loc[rows["check"] == "extracted_pytest_passed_count", "observed"].iloc[0] == "1"


def test_release_runtime_audit_reports_failing_extracted_pytest(tmp_path):
    for directory in ["bodyshield", "scripts", "results", "paper", "tests"]:
        (tmp_path / directory).mkdir()
    (tmp_path / "bodyshield" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "scripts" / "verify_release_payload.py").write_text("print('verify payload')\n", encoding="utf-8")
    (tmp_path / "results" / "trials.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "paper" / "main.tex").write_text("\\section{x}\n", encoding="utf-8")
    (tmp_path / "tests" / "test_demo.py").write_text("def test_failure():\n    assert False\n", encoding="utf-8")
    (tmp_path / "README_EXECUTION.md").write_text("# Run\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")

    write_release_bundle(tmp_path)
    rows = run_release_runtime_audit(tmp_path, timeout_s=30)
    failures = failed_release_runtime_rows(rows)

    assert "extracted_pytest_returncode" in set(failures["check"])
    assert "extracted_pytest_passed_count" in set(failures["check"])


def test_evidence_consistency_audit_checks_referenced_artifacts(tmp_path):
    for directory in ["reports", "results", "release", "scripts"]:
        (tmp_path / directory).mkdir()
    (tmp_path / "results" / "existing.csv").write_text("a\n1\n", encoding="utf-8")
    (tmp_path / "reports" / "existing.md").write_text("# ok\n", encoding="utf-8")
    (tmp_path / "release" / "bundle.zip").write_text("zip-placeholder\n", encoding="utf-8")
    docs = {
        "README_EXECUTION.md": "`results/existing.csv`\n",
        "reports/CLAIM_LEDGER.md": "`results/existing.csv`, `reports/existing.md`\n",
        "reports/NON_HARDWARE_REQUIREMENTS_TRACE.md": "results/existing.csv, reports/existing.md\n",
        "reports/REPRODUCIBILITY_MANIFEST.md": "`release/bundle.zip`\n",
        "reports/NON_HARDWARE_COMPLETE.md": "`results/existing.csv`\n",
        "reports/SIMULATION_SUMMARY.md": "`reports/existing.md`\n",
        "reports/RELEASE_BUNDLE.md": "`release/bundle.zip`\n",
    }
    for rel_path, text in docs.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    rows = run_evidence_consistency_audit(tmp_path)

    assert not rows.empty
    assert failed_references(rows).empty
    references = extract_local_references("Run `python -m pytest -q`; see `results/existing.csv` and results/missing.csv")
    assert "results/existing.csv" in references
    assert "results/missing.csv" in references
    assert all(not ref.startswith("python ") for ref in references)


def test_evidence_consistency_audit_reports_missing_reference(tmp_path):
    (tmp_path / "reports").mkdir()
    (tmp_path / "README_EXECUTION.md").write_text("`results/missing.csv`\n", encoding="utf-8")
    for rel_path in [
        "reports/CLAIM_LEDGER.md",
        "reports/NON_HARDWARE_REQUIREMENTS_TRACE.md",
        "reports/REPRODUCIBILITY_MANIFEST.md",
        "reports/NON_HARDWARE_COMPLETE.md",
        "reports/SIMULATION_SUMMARY.md",
        "reports/RELEASE_BUNDLE.md",
    ]:
        (tmp_path / rel_path).write_text("No local refs here.\n", encoding="utf-8")

    rows = run_evidence_consistency_audit(tmp_path)
    failures = failed_references(rows)

    assert "results/missing.csv" in set(failures["reference"])


def test_environment_dependency_audit_checks_declared_installed_packages(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = [
  "numpy",
  "pandas",
  "matplotlib",
  "pillow",
  "pyarrow",
  "pypdf",
  "pyyaml",
  "tabulate",
  "pytest",
  "mujoco",
  "mani-skill",
  "gymnasium",
]
""".lstrip(),
        encoding="utf-8",
    )
    rows = write_environment_dependency_reports(tmp_path)
    failures = failed_environment_rows(rows)

    assert failures.empty
    assert (tmp_path / "results" / "environment_dependency_audit.csv").exists()
    assert (tmp_path / "results" / "environment_snapshot.json").exists()
    assert (tmp_path / "reports" / "ENVIRONMENT_DEPENDENCY_AUDIT.md").exists()
    assert {"python_package", "system_tool"} <= set(rows["kind"])
    combined_text = "\n".join(
        [
            (tmp_path / "results" / "environment_dependency_audit.csv").read_text(encoding="utf-8"),
            (tmp_path / "results" / "environment_snapshot.json").read_text(encoding="utf-8"),
            (tmp_path / "reports" / "ENVIRONMENT_DEPENDENCY_AUDIT.md").read_text(encoding="utf-8"),
        ]
    )
    assert str(Path.home()) not in combined_text
    assert Path.home().as_posix() not in combined_text


def test_environment_dependency_audit_fails_missing_required_declaration(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = [
  "numpy",
]
""".lstrip(),
        encoding="utf-8",
    )
    rows, _ = run_environment_dependency_audit(tmp_path)
    failures = failed_environment_rows(rows)

    assert "pandas" in set(failures["name"])
    assert "pyarrow" in set(failures["name"])


def _copy_config_schema_inputs(root: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    for rel in [
        "pyproject.toml",
        "data_schema.json",
        "trial_schema.schema.json",
        "tasks.yaml",
        "configs/simulation_bodyshield_maxout.yaml",
        "configs/hardware_push_block_phase2.yaml",
        "configs/external_policy_benchmark.example.json",
        "configs/real_video_wam_readiness.example.json",
        "configs/corrective_trace_readiness.example.json",
    ]:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_root / rel, target)


def test_config_schema_audit_passes_pack_control_files(tmp_path):
    _copy_config_schema_inputs(tmp_path)

    rows = run_config_schema_audit(tmp_path)

    assert failed_config_schema_rows(rows).empty
    assert {
        "trial_json_schema_matches_code_constant",
        "simulation_methods_match_policies",
        "hardware_config_safety_gated",
        "readiness_spec_boundary_present",
    } <= set(rows["check"])


def test_config_schema_audit_reports_dependency_and_hardware_safety_drift(tmp_path):
    _copy_config_schema_inputs(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(pyproject.read_text(encoding="utf-8").replace('  "pandas",\n', ""), encoding="utf-8")
    hardware = tmp_path / "configs" / "hardware_push_block_phase2.yaml"
    hardware.write_text(hardware.read_text(encoding="utf-8").replace("speed_scale_max: 0.30", "speed_scale_max: 0.90"), encoding="utf-8")

    rows = run_config_schema_audit(tmp_path)
    failures = failed_config_schema_rows(rows)

    assert "pyproject_required_dependencies_declared" in set(failures["check"])
    assert "hardware_config_safety_gated" in set(failures["check"])


def _write_demo_release_zip(root: Path, entries: dict[str, str]) -> None:
    release = root / "release"
    release.mkdir(parents=True, exist_ok=True)
    manifest_rows = ["path,bytes,sha256"]
    for name, text in entries.items():
        manifest_rows.append(f"{name},{len(text.encode('utf-8'))},placeholder")
    (release / "RELEASE_BUNDLE_MANIFEST.csv").write_text("\n".join(manifest_rows) + "\n", encoding="utf-8")
    (release / "RELEASE_README.md").write_text("Portable local export.\n", encoding="utf-8")
    (release / "RELEASE_BUNDLE_CHECKSUMS.txt").write_text("placeholder\n", encoding="utf-8")
    with zipfile.ZipFile(release / "bodyshield_non_hardware_release.zip", "w") as bundle:
        bundle.writestr("RELEASE_README.md", "Portable local export.\n")
        bundle.writestr("RELEASE_BUNDLE_MANIFEST.csv", "\n".join(manifest_rows) + "\n")
        for name, text in entries.items():
            bundle.writestr(name, text)


def _write_demo_hygiene_pack(root: Path, *, leak: bool = False) -> None:
    reports = root / "reports"
    results = root / "results"
    reports.mkdir()
    results.mkdir()
    home_text = str(Path.home()) if leak else "<USER_HOME>"
    (root / "README_EXECUTION.md").write_text("Run locally.\n", encoding="utf-8")
    (reports / "PAPER_BUILD_LOG.txt").write_text(f"tool path {home_text}\n", encoding="utf-8")
    (reports / "ENVIRONMENT_DEPENDENCY_AUDIT.md").write_text("Status: `pass`\n<USER_HOME>\n", encoding="utf-8")
    (results / "environment_dependency_audit.csv").write_text(
        "kind,name,required,installed,declared_in_pyproject,path,status\nsystem_tool,pdflatex,True,True,,<USER_HOME>/pdflatex,pass\n",
        encoding="utf-8",
    )
    (results / "environment_snapshot.json").write_text(json.dumps({"python_executable": "<USER_HOME>/python"}), encoding="utf-8")
    entries = {"README_EXECUTION.md": "Run locally.\n"}
    if leak:
        entries["reports/PORTABLE_HYGIENE_AUDIT.md"] = "dynamic output should not ship\n"
        entries["reports/leak.md"] = f"leaked path {Path.home()}\n"
    _write_demo_release_zip(root, entries)


def test_portable_hygiene_audit_passes_redacted_pack(tmp_path):
    _write_demo_hygiene_pack(tmp_path)

    rows = run_portable_hygiene_audit(tmp_path)

    assert failed_portable_hygiene_rows(rows).empty
    assert {
        "local_absolute_paths_absent",
        "release_zip_text_hygiene",
        "release_zip_excludes_pack_side_dynamic_outputs",
    } <= set(rows["check"])


def test_portable_hygiene_audit_reports_local_path_and_dynamic_release_entry(tmp_path):
    _write_demo_hygiene_pack(tmp_path, leak=True)

    rows = run_portable_hygiene_audit(tmp_path)
    failures = failed_portable_hygiene_rows(rows)

    assert "local_absolute_paths_absent" in set(failures["check"])
    assert "release_zip_text_hygiene" in set(failures["check"])
    assert "release_zip_excludes_pack_side_dynamic_outputs" in set(failures["check"])


def test_results_integrity_audit_passes_custom_table(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "demo.csv").write_text("id,value,bucket\nrow1,0.2,a\nrow2,0.8,b\n", encoding="utf-8")
    spec = TableSpec(
        path="results/demo.csv",
        exact_rows=2,
        required_columns=("id", "value", "bucket"),
        unique_columns=("id",),
        numeric_ranges=(NumericRange("value", 0.0, 1.0),),
        required_values=(RequiredValues("bucket", ("a", "b")),),
    )

    rows = run_results_integrity_audit(tmp_path, specs=(spec,), include_pack_side_checks=False)

    assert failed_integrity_rows(rows).empty


def test_results_integrity_audit_reports_duplicate_and_range_failures(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "demo.csv").write_text("id,value,bucket\nrow1,0.2,a\nrow1,1.8,a\n", encoding="utf-8")
    spec = TableSpec(
        path="results/demo.csv",
        exact_rows=2,
        required_columns=("id", "value", "bucket"),
        unique_columns=("id",),
        numeric_ranges=(NumericRange("value", 0.0, 1.0),),
        required_values=(RequiredValues("bucket", ("a", "b")),),
    )

    rows = run_results_integrity_audit(tmp_path, specs=(spec,), include_pack_side_checks=False)
    failures = failed_integrity_rows(rows)

    assert "unique_key" in set(failures["check"])
    assert "numeric_range:value" in set(failures["check"])
    assert "required_values:bucket" in set(failures["check"])


def _write_derived_results_fixture(root: Path) -> None:
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    rows = []
    for method_id, base_success in [("bodyshield", 1), ("nominal", 0)]:
        for bucket in ["nominal", "heldout"]:
            for index in range(6):
                success = int(base_success or index % 2 == 0)
                rows.append(
                    {
                        "method_id": method_id,
                        "bucket": bucket,
                        "success": success,
                        "execution_time_s": 1.0 + 0.1 * index + (0.2 if method_id == "bodyshield" else 0.0),
                        "path_length_m": 0.4 + 0.01 * index,
                        "retries": index % 3,
                        "workspace_violation": int(index == 5 and bucket == "heldout"),
                        "max_tracking_error": 0.001 * (index + 1),
                        "max_current_or_load": 0.02,
                        "verifier_confidence": 0.9,
                        "failure_category": "" if success else ("collision" if index % 2 else "tracking_error"),
                        "perturbation_family": "nominal" if bucket == "nominal" else "payload_g",
                        "perturbation_cost": 0.0 if bucket == "nominal" else float(index % 3 + 1),
                    }
                )
    trials = pd.DataFrame(rows)
    trials.to_csv(results / "trials.csv", index=False)
    summary = recompute_summary_by_method_bucket(trials)
    summary.to_csv(results / "summary_by_method_bucket.csv", index=False)
    recompute_robustness_profiles(trials).to_csv(results / "robustness_profiles.csv", index=False)
    recompute_secondary_metrics(trials).to_csv(results / "secondary_metrics_by_method.csv", index=False)
    recompute_failure_taxonomy_counts(trials).to_csv(results / "failure_taxonomy_counts.csv", index=False)
    recompute_method_deltas(summary).to_csv(results / "method_deltas_vs_bodyshield.csv", index=False)


def test_derived_results_audit_passes_recomputed_tiny_tables(tmp_path):
    _write_derived_results_fixture(tmp_path)

    rows = run_derived_results_audit(tmp_path)

    assert failed_derived_results_rows(rows).empty
    assert {
        "derived_table_key_set_matches",
        "derived_table_numeric_values_match",
        "primary_trials_exists_nonempty",
    } <= set(rows["check"])


def test_derived_results_audit_reports_summary_drift(tmp_path):
    _write_derived_results_fixture(tmp_path)
    summary_path = tmp_path / "results" / "summary_by_method_bucket.csv"
    summary = pd.read_csv(summary_path)
    summary.loc[0, "successes"] = int(summary.loc[0, "successes"]) - 1
    summary.to_csv(summary_path, index=False)

    rows = run_derived_results_audit(tmp_path)
    failures = failed_derived_results_rows(rows)

    assert "derived_table_numeric_values_match" in set(failures["check"])
    assert "results/summary_by_method_bucket.csv" in set(failures["artifact"])


def _write_source_import_fixture(root: Path) -> None:
    bodyshield = root / "bodyshield"
    robot = bodyshield / "robot"
    scripts = root / "scripts"
    tests_dir = root / "tests"
    for directory in (bodyshield, robot, scripts, tests_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (bodyshield / "__init__.py").write_text("", encoding="utf-8")
    (bodyshield / "demo.py").write_text("VALUE = 1\n", encoding="utf-8")
    (robot / "__init__.py").write_text("", encoding="utf-8")
    (robot / "healthcheck.py").write_text(
        """
def main():
    print("safety confirmation required")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
""".lstrip(),
        encoding="utf-8",
    )
    (robot / "safety_gate.py").write_text(
        """
def main():
    print("safety gate not enabled without confirmation")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
""".lstrip(),
        encoding="utf-8",
    )
    (robot / "run_batch.py").write_text(
        """
def main():
    print("refusing hardware batch until safety confirmation")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
""".lstrip(),
        encoding="utf-8",
    )
    (bodyshield / "safe_robot_runner.py").write_text(
        """
class SafetyViolation(RuntimeError):
    pass


class SafeRobot:
    def __init__(self, config):
        self.config = config

    def safety_check(self):
        raise SafetyViolation("safety confirmation not enabled")

    def reset_to_home(self):
        raise SafetyViolation("safety confirmation not enabled")

    def move_to_pose(self, pose, speed_scale=0.2):
        raise SafetyViolation("safety confirmation not enabled")

    def stop_now(self):
        raise SafetyViolation("safety confirmation not enabled")


def run_batch(config_path):
    raise SafetyViolation(f"refusing hardware batch for {config_path}: safety not confirmed")
""".lstrip(),
        encoding="utf-8",
    )
    (scripts / "demo.py").write_text(
        """
def main():
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
""".lstrip(),
        encoding="utf-8",
    )
    (tests_dir / "test_demo.py").write_text("def test_demo():\n    assert True\n", encoding="utf-8")


def test_source_import_audit_passes_compile_import_and_stub_checks(tmp_path):
    _write_source_import_fixture(tmp_path)

    rows = run_source_import_audit(tmp_path, timeout_s=10)

    assert failed_source_import_rows(rows).empty
    checks = set(rows["check"])
    assert "python_file_py_compile" in checks
    assert "bodyshield_module_imports_in_subprocess" in checks
    assert "hardware_stub_forbidden_raw_io_absent" in checks
    assert "safe_robot_api_methods_raise_safety_violation" in checks


def test_source_import_audit_reports_syntax_import_and_stub_drift(tmp_path):
    _write_source_import_fixture(tmp_path)
    (tmp_path / "bodyshield" / "bad_syntax.py").write_text("def broken(:\n", encoding="utf-8")
    (tmp_path / "bodyshield" / "bad_import.py").write_text("raise RuntimeError('import boom')\n", encoding="utf-8")
    (tmp_path / "scripts" / "no_guard.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "bodyshield" / "robot" / "run_batch.py").write_text(
        """
def main():
    serial.Serial("COM1")
    print("running hardware without boundary")
    return 0
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "bodyshield" / "safe_robot_runner.py").write_text(
        """
class SafetyViolation(RuntimeError):
    pass


class SafeRobot:
    def move_to_pose(self, pose, speed_scale=0.2):
        return None


def run_batch(config_path):
    return None
""".lstrip(),
        encoding="utf-8",
    )

    rows = run_source_import_audit(tmp_path, timeout_s=10)
    failures = failed_source_import_rows(rows)

    assert "python_file_py_compile" in set(failures["check"])
    assert "bodyshield_module_imports_in_subprocess" in set(failures["check"])
    assert "script_has_main_guard" in set(failures["check"])
    assert "hardware_stub_refusal_boundary_present" in set(failures["check"])
    assert "hardware_stub_forbidden_raw_io_absent" in set(failures["check"])
    assert "safe_robot_api_methods_raise_safety_violation" in set(failures["check"])


def test_claim_boundary_audit_passes_required_boundary_doc(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "doc.md").write_text(
        "This is an analytic-simulation claim only. No hardware validation complete claim is made.\n",
        encoding="utf-8",
    )
    rows = run_claim_boundary_audit(
        tmp_path,
        document_requirements=(DocumentRequirement("reports/doc.md", ("analytic-simulation claim only",)),),
        csv_requirements=(),
        pdf_requirements=(),
        forbidden_phrases=("external archival upload complete",),
    )

    assert failed_claim_boundary_rows(rows).empty


def test_claim_boundary_audit_reports_missing_boundary_and_overclaim(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "doc.md").write_text("Hardware validation complete.\n", encoding="utf-8")
    rows = run_claim_boundary_audit(
        tmp_path,
        document_requirements=(DocumentRequirement("reports/doc.md", ("analytic-simulation claim only",)),),
        csv_requirements=(),
        pdf_requirements=(),
        forbidden_phrases=("hardware validation complete",),
    )
    failures = failed_claim_boundary_rows(rows)

    assert "required_boundary_phrase" in set(failures["check"])
    assert "forbidden_overclaim_phrases" in set(failures["check"])


def test_command_surface_parser_normalizes_script_commands():
    commands = parse_python_commands(
        "```powershell\npython scripts\\run_demo.py --flag\npython -m pytest -q\n```\n",
        "README.md",
    )

    assert [command.normalized for command in commands] == ["python scripts/run_demo.py --flag", "python -m pytest -q"]
    assert commands[0].kind == "script"
    assert commands[0].target == "scripts/run_demo.py"
    assert commands[1].kind == "module"
    assert commands[1].target == "pytest"


def test_command_surface_audit_passes_matching_docs_and_help_script(tmp_path):
    scripts = tmp_path / "scripts"
    reports = tmp_path / "reports"
    release = tmp_path / "release"
    tests_dir = tmp_path / "tests"
    scripts.mkdir()
    reports.mkdir()
    release.mkdir()
    tests_dir.mkdir()
    (tests_dir / "test_demo.py").write_text("def test_demo():\n    assert True\n", encoding="utf-8")
    (scripts / "demo.py").write_text(
        """
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
""".lstrip(),
        encoding="utf-8",
    )
    primary = ("python -m pytest -q", "python scripts/demo.py")
    release_cmds = ("python scripts/demo.py",)
    command_block = "```powershell\npython -m pytest -q\npython scripts\\demo.py\n```\n"
    (tmp_path / "README_EXECUTION.md").write_text(command_block, encoding="utf-8")
    (reports / "REPRODUCIBILITY_MANIFEST.md").write_text(command_block, encoding="utf-8")
    (release / "RELEASE_README.md").write_text("```powershell\npython scripts\\demo.py\n```\n", encoding="utf-8")

    rows = run_command_surface_audit(
        tmp_path,
        expected_primary_commands=primary,
        expected_release_commands=release_cmds,
        help_scripts=("scripts/demo.py",),
        timeout_s=10,
    )

    assert failed_command_surface_rows(rows).empty


def test_command_surface_audit_reports_missing_script(tmp_path):
    reports = tmp_path / "reports"
    release = tmp_path / "release"
    tests_dir = tmp_path / "tests"
    reports.mkdir()
    release.mkdir()
    tests_dir.mkdir()
    (tests_dir / "test_demo.py").write_text("def test_demo():\n    assert True\n", encoding="utf-8")
    primary = ("python -m pytest -q", "python scripts/missing.py")
    command_block = "```powershell\npython -m pytest -q\npython scripts\\missing.py\n```\n"
    (tmp_path / "README_EXECUTION.md").write_text(command_block, encoding="utf-8")
    (reports / "REPRODUCIBILITY_MANIFEST.md").write_text(command_block, encoding="utf-8")
    (release / "RELEASE_README.md").write_text("```powershell\npython scripts\\missing.py\n```\n", encoding="utf-8")

    rows = run_command_surface_audit(
        tmp_path,
        expected_primary_commands=primary,
        expected_release_commands=("python scripts/missing.py",),
        help_scripts=("scripts/missing.py",),
        timeout_s=10,
    )
    failures = failed_command_surface_rows(rows)

    assert "script_exists_nonempty" in set(failures["check"])


def _write_blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)


def _write_demo_paper_pack(root: Path, *, missing_citation: bool = False, missing_figure: bool = False) -> None:
    paper = root / "paper"
    reports = root / "reports"
    figures = root / "results" / "figures"
    build = paper / "build"
    for directory in (paper, reports, figures, build):
        directory.mkdir(parents=True, exist_ok=True)

    cite_key = "missing_key" if missing_citation else "demo"
    tex = rf"""
\documentclass{{article}}
\usepackage{{graphicx}}
\begin{{document}}
Demo text with a local reference \path{{data_schema.json}}.
See Table~\ref{{tab:demo}} and cite~\cite{{{cite_key},extra}}.
\begin{{table}}
\caption{{Demo table}}
\label{{tab:demo}}
\begin{{tabular}}{{c}}x\end{{tabular}}
\end{{table}}
\includegraphics{{results/figures/demo.pdf}}
\bibliographystyle{{plain}}
\bibliography{{references}}
\end{{document}}
""".lstrip()
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    (paper / "references.bib").write_text(
        """@article{demo,
  title={Demo},
  author={A. Author},
  year={2026}
}

@article{extra,
  title={Extra},
  author={B. Author},
  year={2026}
}
""",
        encoding="utf-8",
    )
    (root / "data_schema.json").write_text("{}", encoding="utf-8")
    if not missing_figure:
        _write_blank_pdf(figures / "demo.pdf")
    _write_blank_pdf(paper / "bodyshield_non_hardware_draft.pdf")
    shutil.copy2(paper / "bodyshield_non_hardware_draft.pdf", build / "main.pdf")
    (reports / "PAPER_BUILD_STATUS.json").write_text(
        json.dumps({"status": "written", "output": "paper\\bodyshield_non_hardware_draft.pdf"}),
        encoding="utf-8",
    )
    (reports / "PAPER_BUILD_LOG.txt").write_text("Clean build log.\n", encoding="utf-8")


def test_paper_source_audit_passes_tiny_tex_bib_pdf_pack(tmp_path):
    _write_demo_paper_pack(tmp_path)

    rows = run_paper_source_audit(
        tmp_path,
        expected_bib_keys=("demo", "extra"),
        expected_page_count=1,
        required_pdf_terms=(),
        required_tex_terms=("Demo text",),
        required_local_refs=("data_schema.json",),
    )

    assert failed_paper_source_rows(rows).empty
    assert {"tex_citations_resolve", "tex_figure_paths_resolve", "pdf_matches_build_output"} <= set(rows["check"])


def test_paper_source_audit_reports_missing_citation_and_figure(tmp_path):
    _write_demo_paper_pack(tmp_path, missing_citation=True, missing_figure=True)

    rows = run_paper_source_audit(
        tmp_path,
        expected_bib_keys=("demo", "extra"),
        expected_page_count=1,
        required_pdf_terms=(),
        required_tex_terms=("Demo text",),
        required_local_refs=("data_schema.json",),
    )
    failures = failed_paper_source_rows(rows)

    assert "tex_citations_resolve" in set(failures["check"])
    assert "tex_figure_paths_resolve" in set(failures["check"])


def _write_demo_visual_artifacts(root):
    figures = root / "results" / "figures"
    videos = root / "results" / "videos"
    reports = root / "reports"
    figures.mkdir(parents=True)
    videos.mkdir(parents=True)
    reports.mkdir()

    image = Image.new("RGB", (320, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 280, 160), fill="steelblue")
    draw.line((40, 160, 280, 40), fill="black", width=4)
    image.save(figures / "demo.png")
    image.save(figures / "demo.pdf", "PDF")

    manifest_rows = ["artifact_id,path,frames,frame_size_px,evidence_boundary"]
    for index in range(3):
        frames = []
        for x in (10 + index, 30 + index):
            frame = Image.new("RGB", (60, 84), "white")
            frame_draw = ImageDraw.Draw(frame)
            frame_draw.ellipse((x, 20, x + 12, 32), fill="black")
            frames.append(frame)
        gif_name = f"bodyshield_synthetic_demo_{index}.gif"
        frames[0].save(videos / gif_name, save_all=True, append_images=frames[1:], duration=80, loop=0)
        manifest_rows.append(
            f"demo_{index},results/videos/{gif_name},2,10,Synthetic generated rollout only; not real video."
        )

    (root / "results" / "simulation_rollout_videos.csv").write_text("\n".join(manifest_rows) + "\n", encoding="utf-8")
    (reports / "FIGURE_CAPTIONS.md").write_text(
        "# Figure Captions\n\n"
        "## `results/figures/demo.pdf`\nDemo figure.\n\n"
        "## `results/videos/bodyshield_synthetic_*.gif`\nDemo GIFs.\n",
        encoding="utf-8",
    )


def test_visual_artifact_audit_passes_readable_figure_and_gif(tmp_path):
    _write_demo_visual_artifacts(tmp_path)

    rows = run_visual_artifact_audit(tmp_path, expected_stems=("demo",))

    assert failed_visual_artifact_rows(rows).empty


def test_visual_artifact_audit_reports_blank_png_and_missing_pdf(tmp_path):
    figures = tmp_path / "results" / "figures"
    reports = tmp_path / "reports"
    figures.mkdir(parents=True)
    reports.mkdir()
    Image.new("RGB", (320, 200), "white").save(figures / "demo.png")
    (reports / "FIGURE_CAPTIONS.md").write_text("## `results/figures/demo.pdf`\nDemo figure.\n", encoding="utf-8")
    (tmp_path / "results" / "simulation_rollout_videos.csv").write_text("", encoding="utf-8")

    rows = run_visual_artifact_audit(tmp_path, expected_stems=("demo",))
    failures = failed_visual_artifact_rows(rows)

    assert "pdf_exists_nonempty" in set(failures["check"])
    assert "png_nonblank_variance" in set(failures["check"])
    assert "gif_manifest_exists_nonempty" in set(failures["check"])


def test_external_policy_benchmark_readiness_handles_fixture_missing_and_adapter(tmp_path):
    adapter_module = tmp_path / "mock_external_policy.py"
    adapter_module.write_text(
        """
def load_policy(checkpoint_path, spec):
    def policy(observation, step=0, spec=None):
        return [0.04, -0.03]
    return policy
""".lstrip(),
        encoding="utf-8",
    )
    checkpoint = tmp_path / "policy.ckpt"
    checkpoint.write_text("mock checkpoint", encoding="utf-8")
    spec = {
        "benchmark_name": "test_external_policy_readiness",
        "path_base": "repo_root",
        "policies": [
            {
                "policy_id": "fixture",
                "source": "fixture",
                "engine": "interface_smoke",
                "task_id": "fixture_task",
                "adapter": "fixture:proportional",
                "expected_action_dim": 2,
                "observation_dim": 6,
            },
            {
                "policy_id": "missing_external",
                "source": "external_checkpoint",
                "engine": "maniskill",
                "task_id": "PushCube-v1",
                "checkpoint_path": "missing.ckpt",
                "adapter": "mock_external_policy:load_policy",
                "expected_action_dim": 2,
                "observation_dim": 6,
                "python_path": ".",
            },
            {
                "policy_id": "present_external",
                "source": "external_checkpoint",
                "engine": "mujoco",
                "task_id": "planar_reach",
                "checkpoint_path": "policy.ckpt",
                "adapter": "mock_external_policy:load_policy",
                "expected_action_dim": 2,
                "observation_dim": 6,
                "python_path": ".",
            },
        ],
    }
    spec_path = tmp_path / "external_policy_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    rows = run_external_policy_benchmark(spec_path, root=tmp_path, steps=3)
    statuses = dict(zip(rows["policy_id"], rows["status"]))
    assert statuses["fixture"] == "fixture_smoke_passed"
    assert statuses["missing_external"] == "missing_checkpoint"
    assert statuses["present_external"] == "executed_external_checkpoint_interface_smoke"
    present = rows[rows["policy_id"] == "present_external"].iloc[0]
    assert bool(present["interface_checks_passed"])
    assert present["steps_executed"] == 3
    assert "not a MuJoCo/ManiSkill task-rollout benchmark" in present["evidence_boundary"]


def test_real_video_wam_readiness_handles_fixture_missing_and_present_dataset(tmp_path):
    dataset_root = tmp_path / "real_frames"
    frames_dir = dataset_root / "frames"
    frames_dir.mkdir(parents=True)
    positions = [(4, 10), (6, 8), (8, 6), (10, 4)]
    for index, position in enumerate(positions):
        image = Image.new("L", (16, 16), 0)
        draw = ImageDraw.Draw(image)
        x, y = position
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=255)
        image.save(frames_dir / f"frame_{index:02d}.png")
    manifest_rows = ["frame_path,next_frame_path,action_x,action_y"]
    for index in range(len(positions) - 1):
        x0, y0 = positions[index]
        x1, y1 = positions[index + 1]
        manifest_rows.append(
            f"frames/frame_{index:02d}.png,frames/frame_{index + 1:02d}.png,{(x1 - x0) / 15.0},{(y1 - y0) / 15.0}"
        )
    (dataset_root / "manifest.csv").write_text("\n".join(manifest_rows) + "\n", encoding="utf-8")
    spec = {
        "benchmark_name": "test_real_video_wam_readiness",
        "path_base": "repo_root",
        "datasets": [
            {
                "dataset_id": "fixture_sequence",
                "source": "fixture_sequence",
                "dataset_root": "",
                "manifest_path": "",
                "action_dim": 2,
                "frames": 5,
                "frame_size": 12,
            },
            {
                "dataset_id": "missing_real_video",
                "source": "real_video_dataset",
                "dataset_root": "missing_real_video",
                "manifest_path": "manifest.csv",
                "action_dim": 2,
            },
            {
                "dataset_id": "present_real_video",
                "source": "real_video_dataset",
                "dataset_root": "real_frames",
                "manifest_path": "manifest.csv",
                "action_dim": 2,
            },
        ],
    }
    spec_path = tmp_path / "real_video_wam_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    rows = run_real_video_wam_readiness(spec_path, root=tmp_path)
    statuses = dict(zip(rows["dataset_id"], rows["status"]))
    assert statuses["fixture_sequence"] == "fixture_training_smoke_passed"
    assert statuses["missing_real_video"] == "missing_dataset"
    assert statuses["present_real_video"] == "real_frame_manifest_smoke_passed"
    present = rows[rows["dataset_id"] == "present_real_video"].iloc[0]
    assert bool(present["training_smoke_passed"])
    assert present["frames_checked"] == 4
    assert present["fitted_next_centroid_mse"] <= present["baseline_next_centroid_mse"]
    assert "not foundation-scale training" in present["evidence_boundary"]


def test_corrective_trace_readiness_handles_fixture_missing_and_present_dataset(tmp_path):
    dataset_root = tmp_path / "corrective_traces"
    dataset_root.mkdir()
    manifest = dataset_root / "manifest.csv"
    lines = [
        "trace_id,source,perturbation_label,state_x,state_y,target_x,target_y,base_action_x,base_action_y,corrected_action_x,corrected_action_y"
    ]
    for index in range(6):
        state_x = 0.05 + 0.02 * index
        state_y = -0.03 + 0.01 * index
        target_x = 0.25
        target_y = 0.12
        base_x = 0.4 * (target_x - state_x)
        base_y = 0.4 * (target_y - state_y)
        corrected_x = base_x + 0.02
        corrected_y = base_y - 0.01
        lines.append(
            f"trace_{index},mock,latency,{state_x},{state_y},{target_x},{target_y},{base_x},{base_y},{corrected_x},{corrected_y}"
        )
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spec = {
        "benchmark_name": "test_corrective_trace_readiness",
        "path_base": "repo_root",
        "datasets": [
            {
                "dataset_id": "fixture_traces",
                "source": "fixture_corrective_traces",
                "dataset_root": "",
                "manifest_path": "",
                "action_dim": 2,
                "rows": 6,
            },
            {
                "dataset_id": "missing_traces",
                "source": "real_or_external_corrective_traces",
                "dataset_root": "missing_traces",
                "manifest_path": "manifest.csv",
                "action_dim": 2,
            },
            {
                "dataset_id": "present_traces",
                "source": "real_or_external_corrective_traces",
                "dataset_root": "corrective_traces",
                "manifest_path": "manifest.csv",
                "action_dim": 2,
            },
        ],
    }
    spec_path = tmp_path / "corrective_trace_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    rows = run_corrective_trace_readiness(spec_path, root=tmp_path)
    statuses = dict(zip(rows["dataset_id"], rows["status"]))
    assert statuses["fixture_traces"] == "fixture_fit_smoke_passed"
    assert statuses["missing_traces"] == "missing_dataset"
    assert statuses["present_traces"] == "corrective_trace_manifest_smoke_passed"
    present = rows[rows["dataset_id"] == "present_traces"].iloc[0]
    assert bool(present["fit_smoke_passed"])
    assert present["trace_rows"] == 6
    assert present["fitted_action_mse_to_corrected"] <= present["base_action_mse_to_corrected"]
    assert "not online adaptation" in present["evidence_boundary"]


def test_neural_latent_wam_runs_on_small_grid():
    policies = default_policies()
    policies["bodyshield"] = policies["domain_randomization"].with_id("bodyshield")
    conditions = [
        {"bucket": "nominal", "family": "nominal", "level": "none", "perturbation": Perturbation()},
        {"bucket": "seen", "family": "latency_ms", "level": "medium", "perturbation": Perturbation({"latency_ms": 80})},
        {"bucket": "heldout", "family": "camera_shift_px", "level": "heldout_medium", "perturbation": Perturbation({"camera_shift_px": 40})},
    ]
    trace = generate_synthetic_trajectory(policies["nominal"], TASKS[0], ROBOTS[0], Perturbation(), steps=4)
    frame = render_synthetic_visual_frame(trace["states"][0], trace["target"], TASKS[0], Perturbation(), frame_size=8)
    latent = visual_latent_from_frame(frame)
    assert latent.shape == (11,)
    assert latent[-1] >= 0.0
    result = fit_neural_latent_wam(
        policies,
        conditions,
        source_method_ids=("nominal", "bodyshield"),
        steps=4,
        frame_size=8,
        hidden_units=8,
        epochs=4,
        max_train_samples=128,
        trace_sample_limit=4,
    )
    assert not result.metrics.empty
    assert not result.rollouts.empty
    assert not result.training_curve.empty
    assert result.trace_sample
    assert set(result.rollouts["split"]) == {"train_seen_or_nominal", "heldout"}
