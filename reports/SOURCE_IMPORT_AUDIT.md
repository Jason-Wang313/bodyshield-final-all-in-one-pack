# Source Import Audit

Status: `pass`

This audit checks that every shipped Python source file under `bodyshield/`, `scripts/`, and `tests/` compiles; every script has a guarded CLI entry point; every `bodyshield.*` module imports in a fresh subprocess; and hardware-facing stubs remain refusal-only without raw hardware or network I/O tokens.

| metric | value |
|---|---:|
| checks | 295 |
| passed | 295 |
| failed | 0 |
| artifacts audited | 241 |

## Display Rows

| artifact                                    | check                          | status   | detail                                    |   observed | expected   |
|:--------------------------------------------|:-------------------------------|:---------|:------------------------------------------|-----------:|:-----------|
| bodyshield                                  | source_root_exists             | pass     | source root exists                        |       True | True       |
| bodyshield                                  | source_python_files_discovered | pass     | Python source files discovered under root |         98 | >0         |
| scripts                                     | source_root_exists             | pass     | source root exists                        |       True | True       |
| scripts                                     | source_python_files_discovered | pass     | Python source files discovered under root |         32 | >0         |
| tests                                       | source_root_exists             | pass     | source root exists                        |       True | True       |
| tests                                       | source_python_files_discovered | pass     | Python source files discovered under root |         14 | >0         |
| bodyshield                                  | bodyshield_modules_discovered  | pass     | importable bodyshield modules discovered  |         95 | >0         |
| bodyshield/__init__.py                      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/_legacy.py                       | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/__init__.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/audit_videos.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/claim_ledger.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/make_figures.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/make_tables.py          | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/plots.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/stats.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/summarize_batch.py      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/tables.py               | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/verify_package.py       | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/analysis/videos.py               | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/artifact_inventory_audit.py      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/bodybreak.py                     | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/bodybreak_search.py              | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/bodyshield.py                    | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/bodyshield_repair.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/claim_boundary_audit.py          | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/command_surface_audit.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/config_schema_audit.py           | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/core/__init__.py                 | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/core/bodybreak.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/core/bodyshield.py               | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/core/metrics.py                  | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/core/oracle.py                   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/core/perturbations.py            | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/core/repair.py                   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/corrective_adaptation.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/corrective_trace_readiness.py    | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/derived_results_audit.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/environment_audit.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/evidence_consistency.py          | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/external_policy_benchmark.py     | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/falsification/__init__.py        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/high_fidelity.py                 | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/high_fidelity_learning.py        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/learned_outcome_model.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/logging_utils.py                 | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/metrics.py                       | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/neural_wam.py                    | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/pack_verification.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/paper/__init__.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/paper/build.py                   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/paper_source_audit.py            | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/perturbations.py                 | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/plotting.py                      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/__init__.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/bodyshield_policy.py    | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/domain_randomization.py | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/epec.py                 | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/grid_worstcase.py       | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/human_effect_prior.py   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/nominal.py              | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/robust_control.py       | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies/sysid_retune.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/policies.py                      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/portable_hygiene_audit.py        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/real_video_wam_readiness.py      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/release_bundle.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/release_determinism_audit.py     | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/release_payload_audit.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/release_runtime_audit.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/repair/__init__.py               | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/repair.py                        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/results_integrity.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/__init__.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/audit_labels.py            | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/calibrate_noise_floor.py   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/emergency_stop_monitor.py  | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/healthcheck.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/reset_check.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/run_batch.py               | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/safe_api.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/safety_gate.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/robot/verifier.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/safe_robot_runner.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/schema.py                        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim/__init__.py                  | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim/envs.py                      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim/robots.py                    | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim/runners.py                   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim/tasks.py                     | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim/validators.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim.py                           | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim_envs.py                      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/sim_videos.py                    | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/simulation/__init__.py           | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/simulation/envs.py               | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/simulation/robots.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/simulation/tasks.py              | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/simulation/wrappers.py           | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/source_import_audit.py           | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/stats.py                         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/tasks.py                         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/trajectory_wam.py                | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/visual_artifact_audit.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| bodyshield/visual_wam.py                    | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/build_bodyshield_icra_paper.py      | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/build_paper_targets.py              | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/build_release_bundle.py             | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/finalize_maxout_artifacts.py        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/finalize_nonrejectable_artifacts.py | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/finalize_v2_artifacts.py            | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/finalize_v3_artifacts.py            | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_artifact_inventory_audit.py     | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_claim_boundary_audit.py         | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_command_surface_audit.py        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_config_schema_audit.py          | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_corrective_trace_readiness.py   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_derived_results_audit.py        | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_environment_dependency_audit.py | python_file_py_compile         | pass     | Python source compiles                    |            |            |
| scripts/run_evidence_consistency_audit.py   | python_file_py_compile         | pass     | Python source compiles                    |            |            |
