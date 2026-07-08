# BodyShield Non-Hardware Execution

Current code version: `657ed1811cb15297`

Run:
```powershell
python -m pytest -q
python scripts\run_external_policy_benchmark.py
python scripts\run_public_checkpoint_benchmark.py
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

Primary outputs:
- `reports/NON_HARDWARE_COMPLETE.md`
- `reports/NON_HARDWARE_AUDIT.md`
- `reports/NON_HARDWARE_REQUIREMENTS_TRACE.md`
- `reports/BUDGET_AND_FAIRNESS_AUDIT.md`
- `reports/BODYBREAK_MINIMALITY_AUDIT.md`
- `reports/CLAIM_LEDGER.md`
- `reports/REPRODUCIBILITY_MANIFEST.md`
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
- `reports/PACK_VERIFICATION.md`
- `reports/METHOD_DELTA_TABLE.md`
- `reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md`
- `reports/VISUAL_WAM_INTERPRETATION.md`
- `reports/SIMULATION_ROLLOUT_VIDEOS.md`
- `reports/NEURAL_WAM_INTERPRETATION.md`
- `reports/REAL_VIDEO_WAM_READINESS.md`
- `reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md`
- `reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md`
- `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md`
- `reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md`
- `reports/MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md`
- `reports/EXTERNAL_BASELINE_FAIRNESS.md`
- `reports/TRAJECTORY_WAM_INTERPRETATION.md`
- `reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md`
- `reports/CORRECTIVE_TRACE_READINESS.md`
- `reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md`
- `reports/MUJOCO_PLANAR_PROBE_TABLE.md`
- `results/trials.csv`
- `results/bodybreak_minimality_audit.csv`
- `results/visual_wam_rollouts.csv`
- `results/simulation_rollout_videos.csv`
- `results/neural_wam_rollouts.csv`
- `results/real_video_wam_readiness.csv`
- `results/mujoco_residual_policy_rollouts.csv`
- `results/mujoco_residual_policy_gate_ablation.csv`
- `results/external_policy_benchmark_readiness.csv`
- `results/public_pretrained_checkpoint_benchmark.csv`
- `results/public_pretrained_checkpoint_rollouts.csv`
- `results/public_pretrained_checkpoint_tuning.csv`
- `results/public_pretrained_checkpoint_delta.csv`
- `results/trajectory_wam_rollouts.csv`
- `results/corrective_adaptation_rollouts.csv`
- `results/corrective_trace_readiness.csv`
- `results/artifact_inventory_audit.csv`
- `results/claim_boundary_audit.csv`
- `results/command_surface_audit.csv`
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
- `results/high_fidelity_benchmark.csv`
- `results/videos/bodyshield_synthetic_*.gif`
- `release/bodyshield_non_hardware_release.zip`
- `release/RELEASE_BUNDLE_MANIFEST.csv`
- `release/RELEASE_BUNDLE_CHECKSUMS.txt`

After unpacking `release/bodyshield_non_hardware_release.zip`, validate the extracted payload with:
```powershell
python scripts\verify_release_payload.py
```

Boundary:
This pack stops before hardware. The robot healthcheck, safety gate, camera verifier, and emergency stop must be confirmed before any hardware batch command is meaningful.
