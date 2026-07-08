# Evidence Consistency Audit

Status: `pass`

This audit scans the main claim, trace, reproducibility, completion, simulation-summary, README, and release-bundle documents for local evidence references, then verifies that each referenced file or glob exists in the pack.

| metric | value |
|---|---:|
| audited documents | 7 |
| references checked | 714 |
| passing references | 714 |
| missing references | 0 |

## Checked References

| document            | reference                                             | status   | detail                      |   matches |
|:--------------------|:------------------------------------------------------|:---------|:----------------------------|----------:|
| README_EXECUTION.md | reports/NON_HARDWARE_COMPLETE.md                      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/NON_HARDWARE_AUDIT.md                         | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/NON_HARDWARE_REQUIREMENTS_TRACE.md            | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/BUDGET_AND_FAIRNESS_AUDIT.md                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/BODYBREAK_MINIMALITY_AUDIT.md                 | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/CLAIM_LEDGER.md                               | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/REPRODUCIBILITY_MANIFEST.md                   | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/RELEASE_BUNDLE.md                             | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/ARTIFACT_INVENTORY_AUDIT.md                   | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/CLAIM_BOUNDARY_AUDIT.md                       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/COMMAND_SURFACE_AUDIT.md                      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/EVIDENCE_CONSISTENCY_AUDIT.md                 | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/ENVIRONMENT_DEPENDENCY_AUDIT.md               | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/CONFIG_SCHEMA_AUDIT.md                        | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/DERIVED_RESULTS_AUDIT.md                      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/SOURCE_IMPORT_AUDIT.md                        | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/RESULTS_INTEGRITY_AUDIT.md                    | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/PAPER_SOURCE_AUDIT.md                         | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/PORTABLE_HYGIENE_AUDIT.md                     | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/VISUAL_ARTIFACT_AUDIT.md                      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/RELEASE_PAYLOAD_AUDIT.md                      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/RELEASE_DETERMINISM_AUDIT.md                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/RELEASE_RUNTIME_AUDIT.md                      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/PACK_VERIFICATION.md                          | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/METHOD_DELTA_TABLE.md                         | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/VISUAL_WAM_INTERPRETATION.md                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/SIMULATION_ROLLOUT_VIDEOS.md                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/NEURAL_WAM_INTERPRETATION.md                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/REAL_VIDEO_WAM_READINESS.md                   | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md        | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/MUJOCO_PUBLIC_CHECKPOINT_ROLLOUT_COMPLETE.md  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/EXTERNAL_BASELINE_FAIRNESS.md                 | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/TRAJECTORY_WAM_INTERPRETATION.md              | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/CORRECTIVE_TRACE_READINESS.md                 | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md         | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | reports/MUJOCO_PLANAR_PROBE_TABLE.md                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/trials.csv                                    | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/bodybreak_minimality_audit.csv                | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/visual_wam_rollouts.csv                       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/simulation_rollout_videos.csv                 | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/neural_wam_rollouts.csv                       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/real_video_wam_readiness.csv                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/mujoco_residual_policy_rollouts.csv           | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/mujoco_residual_policy_gate_ablation.csv      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/external_policy_benchmark_readiness.csv       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/public_pretrained_checkpoint_benchmark.csv    | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/public_pretrained_checkpoint_rollouts.csv     | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/public_pretrained_checkpoint_tuning.csv       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/public_pretrained_checkpoint_delta.csv        | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/trajectory_wam_rollouts.csv                   | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/corrective_adaptation_rollouts.csv            | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/corrective_trace_readiness.csv                | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/artifact_inventory_audit.csv                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/claim_boundary_audit.csv                      | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/command_surface_audit.csv                     | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/config_schema_audit.csv                       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/derived_results_audit.csv                     | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/source_import_audit.csv                       | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/results_integrity_audit.csv                   | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/paper_source_audit.csv                        | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/portable_hygiene_audit.csv                    | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/visual_artifact_audit.csv                     | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/release_payload_audit.csv                     | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/release_determinism_audit.csv                 | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/release_runtime_audit.csv                     | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/high_fidelity_benchmark.csv                   | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | results/videos/bodyshield_synthetic_*.gif             | ok       | glob matched 3 file(s)      |         3 |
| README_EXECUTION.md | release/bodyshield_non_hardware_release.zip           | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | release/RELEASE_BUNDLE_MANIFEST.csv                   | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | release/RELEASE_BUNDLE_CHECKSUMS.txt                  | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | scripts/run_external_policy_benchmark.py              | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | scripts/run_public_checkpoint_benchmark.py            | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | scripts/run_real_video_wam_readiness.py               | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | scripts/run_corrective_trace_readiness.py             | ok       | file exists and is nonempty |         1 |
| README_EXECUTION.md | scripts/run_artifact_inventory_audit.py               | ok       | file exists and is nonempty |         1 |
