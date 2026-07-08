# Reproducibility Manifest

Code version: `b2492a6fe5c81e0f`

Python: `3.10.11`

Primary commands:
```powershell
python -m pytest -q
python scripts\run_external_policy_benchmark.py
python scripts\run_real_video_wam_readiness.py
python scripts\run_corrective_trace_readiness.py
python scripts\run_artifact_inventory_audit.py
python scripts\run_claim_boundary_audit.py
python scripts\run_command_surface_audit.py
python scripts\run_config_schema_audit.py
python scripts\run_derived_results_audit.py
python scripts\run_environment_dependency_audit.py
python scripts\run_results_integrity_audit.py
python scripts\run_source_import_audit.py
python scripts\run_paper_source_audit.py
python scripts\run_portable_hygiene_audit.py
python scripts\run_visual_artifact_audit.py
python scripts\run_evidence_consistency_audit.py
python scripts\build_release_bundle.py
python scripts\run_release_payload_audit.py
python scripts\run_release_determinism_audit.py
python scripts\run_release_runtime_audit.py
python scripts\run_non_hardware.py
python scripts\verify_non_hardware_pack.py --write-reports
```

Inputs:
- `configs/simulation_bodyshield_maxout.yaml`
- `configs/external_policy_benchmark.example.json`
- `configs/real_video_wam_readiness.example.json`
- `configs/corrective_trace_readiness.example.json`
- `tasks.yaml`
- `data_schema.json`

Generated tables:
- `results/trials.csv`
- `results/trials.parquet`
- `results/trials_sample.jsonl`
- `results/schema_validation_summary.json`
- `results/breaking_search.csv`
- `results/bodybreak_minimality_audit.csv`
- `results/summary_by_method_bucket.csv`
- `results/robustness_profiles.csv`
- `results/threshold_sensitivity.csv`
- `results/oracle_feasibility.csv`
- `results/method_deltas_vs_bodyshield.csv`
- `results/learned_outcome_model_eval.csv`
- `results/learned_outcome_axis_weights.csv`
- `results/learned_outcome_predictions.csv`
- `results/visual_wam_eval.csv`
- `results/visual_wam_feature_weights.csv`
- `results/visual_wam_rollouts.csv`
- `results/visual_wam_trace_sample.jsonl`
- `results/neural_wam_eval.csv`
- `results/neural_wam_rollouts.csv`
- `results/neural_wam_training_curve.csv`
- `results/neural_wam_trace_sample.jsonl`
- `results/real_video_wam_readiness.csv`
- `results/mujoco_residual_policy_eval.csv`
- `results/mujoco_residual_policy_rollouts.csv`
- `results/mujoco_residual_policy_weights.csv`
- `results/mujoco_residual_policy_gate_ablation.csv`
- `results/mujoco_residual_policy_trace_sample.jsonl`
- `results/trajectory_wam_eval.csv`
- `results/trajectory_wam_axis_weights.csv`
- `results/trajectory_wam_rollouts.csv`
- `results/trajectory_wam_trace_sample.jsonl`
- `results/corrective_adaptation_eval.csv`
- `results/corrective_adaptation_residual_weights.csv`
- `results/corrective_adaptation_rollouts.csv`
- `results/corrective_adaptation_trace_sample.jsonl`
- `results/corrective_trace_readiness.csv`
- `results/artifact_inventory_audit.csv`
- `results/claim_boundary_audit.csv`
- `results/command_surface_audit.csv`
- `results/evidence_consistency_audit.csv`
- `results/environment_dependency_audit.csv`
- `results/environment_snapshot.json`
- `results/config_schema_audit.csv`
- `results/derived_results_audit.csv`
- `results/source_import_audit.csv`
- `results/results_integrity_audit.csv`
- `results/paper_source_audit.csv`
- `results/portable_hygiene_audit.csv`
- `results/visual_artifact_audit.csv`
- `results/release_payload_audit.csv`
- `results/release_determinism_audit.csv`
- `results/release_runtime_audit.csv`
- `results/simulation_rollout_videos.csv`
- `results/secondary_metrics_by_method.csv`
- `results/failure_taxonomy_counts.csv`
- `results/nominal_vs_robustness_radius.csv`
- `results/high_fidelity_benchmark.csv`
- `results/external_policy_benchmark_readiness.csv`
- `trial_schema.schema.json`

Generated reports:
- `reports/ARTIFACT_MANIFEST.csv`
- `reports/ARTIFACT_MANIFEST.md`
- `reports/RELEASE_BUNDLE.md`
- `reports/ARTIFACT_INVENTORY_AUDIT.md`
- `reports/CLAIM_BOUNDARY_AUDIT.md`
- `reports/COMMAND_SURFACE_AUDIT.md`
- `reports/EVIDENCE_CONSISTENCY_AUDIT.md`
- `reports/ENVIRONMENT_DEPENDENCY_AUDIT.md`
- `reports/CONFIG_SCHEMA_AUDIT.md`
- `reports/DERIVED_RESULTS_AUDIT.md`
- `reports/SOURCE_IMPORT_AUDIT.md`
- `reports/RESULTS_INTEGRITY_AUDIT.md`
- `reports/PAPER_SOURCE_AUDIT.md`
- `reports/PORTABLE_HYGIENE_AUDIT.md`
- `reports/VISUAL_ARTIFACT_AUDIT.md`
- `reports/RELEASE_PAYLOAD_AUDIT.md`
- `reports/RELEASE_DETERMINISM_AUDIT.md`
- `reports/RELEASE_RUNTIME_AUDIT.md`
- `reports/PACK_VERIFICATION.json`
- `reports/PACK_VERIFICATION.md`
- `reports/NON_HARDWARE_AUDIT.md`
- `reports/CLAIM_LEDGER.md`
- `reports/NON_HARDWARE_REQUIREMENTS_TRACE.md`
- `reports/BUDGET_AND_FAIRNESS_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT_TABLE.md`
- `reports/METHOD_DELTA_TABLE.md`
- `reports/AGENDA_FIT_MEMO.md`
- `reports/LEARNED_OUTCOME_MODEL_TABLE.md`
- `reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md`
- `reports/VISUAL_WAM_TABLE.md`
- `reports/VISUAL_WAM_FEATURE_WEIGHT_TABLE.md`
- `reports/VISUAL_WAM_INTERPRETATION.md`
- `reports/NEURAL_WAM_TABLE.md`
- `reports/NEURAL_WAM_TRAINING_CURVE.md`
- `reports/NEURAL_WAM_INTERPRETATION.md`
- `reports/REAL_VIDEO_WAM_READINESS.md`
- `reports/REAL_VIDEO_WAM_READINESS_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_WEIGHT_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md`
- `reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md`
- `reports/TRAJECTORY_WAM_TABLE.md`
- `reports/TRAJECTORY_WAM_AXIS_TABLE.md`
- `reports/TRAJECTORY_WAM_INTERPRETATION.md`
- `reports/CORRECTIVE_ADAPTATION_TABLE.md`
- `reports/CORRECTIVE_ADAPTATION_WEIGHT_TABLE.md`
- `reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md`
- `reports/CORRECTIVE_TRACE_READINESS.md`
- `reports/CORRECTIVE_TRACE_READINESS_TABLE.md`
- `reports/SIMULATION_ROLLOUT_VIDEOS.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS_TABLE.md`
- `reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md`
- `reports/MUJOCO_PLANAR_PROBE_TABLE.md`
- `reports/REVIEWER_ATTACK_CLOSURE.md`
- `reports/CITATION_VERIFICATION_TABLE.md`
- `reports/PREBUTTAL.md`
- `reports/PAPER_REVIEWER_RISK_AUDIT.md`
- `reports/FIGURE_CAPTIONS.md`
- `reports/HIGH_FIDELITY_INTERPRETATION.md`
- `paper/bodyshield_non_hardware_draft.pdf`

Generated media:
- `results/videos/bodyshield_synthetic_nominal_reference.gif`
- `results/videos/bodyshield_synthetic_bodybreak_failure.gif`
- `results/videos/bodyshield_synthetic_bodyshield_repair.gif`

Release bundle:
- `release/bodyshield_non_hardware_release.zip`
- `release/RELEASE_BUNDLE_MANIFEST.csv`
- `release/RELEASE_BUNDLE_CHECKSUMS.txt`
- `release/RELEASE_README.md`

After unpacking the release ZIP:
```powershell
python scripts\verify_release_payload.py
```

Determinism:
All analytic evaluations use stable SHA-256-derived seeds through `bodyshield.sim.stable_seed`.

Verification:
`reports/PACK_VERIFICATION.md`, `reports/RELEASE_PAYLOAD_AUDIT.md`, `reports/RELEASE_DETERMINISM_AUDIT.md`, and `reports/RELEASE_RUNTIME_AUDIT.md` are pack-side verifier outputs. They are intentionally excluded from `reports/ARTIFACT_MANIFEST.csv` and from the release payload to avoid self-referential manifest hash churn. `release/RELEASE_BUNDLE_MANIFEST.csv` is the authoritative archive inventory. The release bundle is local export evidence only; it is not an external archival upload.
