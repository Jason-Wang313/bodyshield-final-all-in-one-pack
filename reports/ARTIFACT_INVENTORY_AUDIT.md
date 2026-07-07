# Artifact Inventory Audit

Status: `pass`

This audit checks that the final artifact manifest exactly matches current generated artifacts, that the release manifest exactly matches current release-eligible payload files, and that documented output references in the README, reproducibility manifest, and completion report exist and are present in the artifact/release manifests whenever eligible.

| metric | value |
|---|---:|
| checks | 996 |
| passed | 996 |
| failed | 0 |
| artifacts audited | 150 |

## Display Rows

| artifact                                              | check                                                | status   | detail                                                     |   observed | expected   |
|:------------------------------------------------------|:-----------------------------------------------------|:---------|:-----------------------------------------------------------|-----------:|:-----------|
| reports/ARTIFACT_MANIFEST.csv                         | artifact_manifest_exists_nonempty                    | pass     | artifact manifest exists and is nonempty                   |        178 | >0 rows    |
| release/RELEASE_BUNDLE_MANIFEST.csv                   | release_manifest_exists_nonempty                     | pass     | release manifest exists and is nonempty                    |        252 | >0 rows    |
| reports/ARTIFACT_MANIFEST.csv                         | artifact_manifest_exact_current_generated_set        | pass     | missing=[]; extra=[]                                       |        178 | 178        |
| reports/ARTIFACT_MANIFEST.csv                         | artifact_manifest_hashes_match_current_files         | pass     | bad_bytes=[]; bad_hashes=[]                                |          0 | 0          |
| release/RELEASE_BUNDLE_MANIFEST.csv                   | release_manifest_exact_current_payload_set           | pass     | missing=[]; extra=[]                                       |        252 | 252        |
| release/RELEASE_BUNDLE_MANIFEST.csv                   | release_manifest_hashes_match_current_files          | pass     | bad_bytes=[]; bad_hashes=[]                                |          0 | 0          |
| README_EXECUTION.md                                   | documented_output_references_discovered              | pass     | documented output references discovered                    |         68 | >0         |
| reports/NON_HARDWARE_COMPLETE.md                      | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/NON_HARDWARE_COMPLETE.md                      | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/NON_HARDWARE_COMPLETE.md                      | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/NON_HARDWARE_AUDIT.md                         | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/NON_HARDWARE_AUDIT.md                         | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/NON_HARDWARE_AUDIT.md                         | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/NON_HARDWARE_REQUIREMENTS_TRACE.md            | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/NON_HARDWARE_REQUIREMENTS_TRACE.md            | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/NON_HARDWARE_REQUIREMENTS_TRACE.md            | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/BUDGET_AND_FAIRNESS_AUDIT.md                  | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/BUDGET_AND_FAIRNESS_AUDIT.md                  | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/BUDGET_AND_FAIRNESS_AUDIT.md                  | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/BODYBREAK_MINIMALITY_AUDIT.md                 | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/BODYBREAK_MINIMALITY_AUDIT.md                 | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/BODYBREAK_MINIMALITY_AUDIT.md                 | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/CLAIM_LEDGER.md                               | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/CLAIM_LEDGER.md                               | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/CLAIM_LEDGER.md                               | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/REPRODUCIBILITY_MANIFEST.md                   | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/REPRODUCIBILITY_MANIFEST.md                   | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/REPRODUCIBILITY_MANIFEST.md                   | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/RELEASE_BUNDLE.md                             | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/RELEASE_BUNDLE.md                             | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/RELEASE_BUNDLE.md                             | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          0 | 0          |
| reports/ARTIFACT_INVENTORY_AUDIT.md                   | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/ARTIFACT_INVENTORY_AUDIT.md                   | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          0 | 0          |
| reports/ARTIFACT_INVENTORY_AUDIT.md                   | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          0 | 0          |
| reports/CLAIM_BOUNDARY_AUDIT.md                       | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/CLAIM_BOUNDARY_AUDIT.md                       | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/CLAIM_BOUNDARY_AUDIT.md                       | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/COMMAND_SURFACE_AUDIT.md                      | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/COMMAND_SURFACE_AUDIT.md                      | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/COMMAND_SURFACE_AUDIT.md                      | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/EVIDENCE_CONSISTENCY_AUDIT.md                 | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/EVIDENCE_CONSISTENCY_AUDIT.md                 | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/EVIDENCE_CONSISTENCY_AUDIT.md                 | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/ENVIRONMENT_DEPENDENCY_AUDIT.md               | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/ENVIRONMENT_DEPENDENCY_AUDIT.md               | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/ENVIRONMENT_DEPENDENCY_AUDIT.md               | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/CONFIG_SCHEMA_AUDIT.md                        | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/CONFIG_SCHEMA_AUDIT.md                        | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/CONFIG_SCHEMA_AUDIT.md                        | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/DERIVED_RESULTS_AUDIT.md                      | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/DERIVED_RESULTS_AUDIT.md                      | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/DERIVED_RESULTS_AUDIT.md                      | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/SOURCE_IMPORT_AUDIT.md                        | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/SOURCE_IMPORT_AUDIT.md                        | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/SOURCE_IMPORT_AUDIT.md                        | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/RESULTS_INTEGRITY_AUDIT.md                    | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/RESULTS_INTEGRITY_AUDIT.md                    | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/RESULTS_INTEGRITY_AUDIT.md                    | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/PAPER_SOURCE_AUDIT.md                         | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/PAPER_SOURCE_AUDIT.md                         | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/PAPER_SOURCE_AUDIT.md                         | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/PORTABLE_HYGIENE_AUDIT.md                     | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/PORTABLE_HYGIENE_AUDIT.md                     | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          0 | 0          |
| reports/PORTABLE_HYGIENE_AUDIT.md                     | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          0 | 0          |
| reports/VISUAL_ARTIFACT_AUDIT.md                      | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/VISUAL_ARTIFACT_AUDIT.md                      | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/VISUAL_ARTIFACT_AUDIT.md                      | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/RELEASE_PAYLOAD_AUDIT.md                      | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/RELEASE_PAYLOAD_AUDIT.md                      | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          0 | 0          |
| reports/RELEASE_PAYLOAD_AUDIT.md                      | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          0 | 0          |
| reports/RELEASE_DETERMINISM_AUDIT.md                  | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/RELEASE_DETERMINISM_AUDIT.md                  | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          0 | 0          |
| reports/RELEASE_DETERMINISM_AUDIT.md                  | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          0 | 0          |
| reports/RELEASE_RUNTIME_AUDIT.md                      | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/RELEASE_RUNTIME_AUDIT.md                      | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          0 | 0          |
| reports/RELEASE_RUNTIME_AUDIT.md                      | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          0 | 0          |
| reports/PACK_VERIFICATION.md                          | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/PACK_VERIFICATION.md                          | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          0 | 0          |
| reports/PACK_VERIFICATION.md                          | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          0 | 0          |
| reports/METHOD_DELTA_TABLE.md                         | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/METHOD_DELTA_TABLE.md                         | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/METHOD_DELTA_TABLE.md                         | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md       | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md       | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/LEARNED_OUTCOME_MODEL_INTERPRETATION.md       | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/VISUAL_WAM_INTERPRETATION.md                  | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/VISUAL_WAM_INTERPRETATION.md                  | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/VISUAL_WAM_INTERPRETATION.md                  | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/SIMULATION_ROLLOUT_VIDEOS.md                  | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/SIMULATION_ROLLOUT_VIDEOS.md                  | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/SIMULATION_ROLLOUT_VIDEOS.md                  | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/NEURAL_WAM_INTERPRETATION.md                  | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/NEURAL_WAM_INTERPRETATION.md                  | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/NEURAL_WAM_INTERPRETATION.md                  | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/REAL_VIDEO_WAM_READINESS.md                   | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/REAL_VIDEO_WAM_READINESS.md                   | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/REAL_VIDEO_WAM_READINESS.md                   | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md      | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md      | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/MUJOCO_RESIDUAL_POLICY_INTERPRETATION.md      | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/MUJOCO_RESIDUAL_POLICY_GATE_ABLATION_TABLE.md | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md        | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md        | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md        | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/TRAJECTORY_WAM_INTERPRETATION.md              | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/TRAJECTORY_WAM_INTERPRETATION.md              | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/TRAJECTORY_WAM_INTERPRETATION.md              | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md       | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md       | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/CORRECTIVE_ADAPTATION_INTERPRETATION.md       | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/CORRECTIVE_TRACE_READINESS.md                 | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/CORRECTIVE_TRACE_READINESS.md                 | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/CORRECTIVE_TRACE_READINESS.md                 | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md         | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md         | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
| reports/MUJOCO_PLANAR_METHOD_SUMMARY_TABLE.md         | documented_output_in_release_manifest_when_eligible  | pass     | README_EXECUTION.md reference release_manifest_missing=[]  |          1 | 1          |
| reports/MUJOCO_PLANAR_PROBE_TABLE.md                  | documented_output_exists_nonempty                    | pass     | README_EXECUTION.md reference exists and is nonempty       |          1 | 1          |
| reports/MUJOCO_PLANAR_PROBE_TABLE.md                  | documented_output_in_artifact_manifest_when_eligible | pass     | README_EXECUTION.md reference artifact_manifest_missing=[] |          1 | 1          |
