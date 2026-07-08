# Initial Repository Audit

Generated: `2026-07-08T01:05:15+00:00`

## First Command Results

- `git status --short`: `M Makefile
 M README.md
 M bodyshield/analysis/make_figures.py
 M bodyshield/analysis/make_tables.py
 M bodyshield/artifact_inventory_audit.py
 M bodyshield/paper_source_audit.py
 M bodyshield/release_bundle.py
 M bodyshield/robot/calibrate_noise_floor.py
 M bodyshield/robot/emergency_stop_monitor.py
 M bodyshield/robot/healthcheck.py
 M bodyshield/robot/run_batch.py
 M bodyshield/robot/safety_gate.py
 M bodyshield/robot/verifier.py
 M bodyshield/safe_robot_runner.py
 M paper/appendix_reviewer_prebuttal.tex
 M paper/bodyshield_icra.pdf
 M paper/main.tex
 M paper/references.bib
 M paper/supplement.pdf
 M reports/CITATION_VERIFICATION_TABLE.md
 M reports/CLAIM_LEDGER.md
 M reports/COMMAND_SURFACE_AUDIT.md
 M reports/PAPER_SOURCE_AUDIT.md
 M reports/SOURCE_IMPORT_AUDIT.md
 M reports/claim_ledger.csv
 M reports/final_artifact_manifest.json
 M reports/final_artifact_manifest_nonhardware.json
 M reports/final_reviewer_prebuttal.md
 M reports/final_submission_readiness_report.md
 M reports/final_video_index.md
 M reports/hardware_noise_floor.md
 M reports/prior_work_comparison_table.csv
 M reports/repo_gap_audit.md
 M reports/reviewer_prebuttal.md
 M reports/submission_readiness_gate.md
 M results/command_surface_audit.csv
 M results/paper_source_audit.csv
 M results/source_import_audit.csv
 M scripts/build_paper_targets.py
 M scripts/finalize_nonrejectable_artifacts.py
 M scripts/run_non_hardware.py
 M scripts/verify_citations.py
 M tables/oracle_feasibility.csv
 M videos/video_index.md
?? REPRODUCE.md
?? bodyshield/_legacy.py
?? bodyshield/analysis/claim_ledger.py
?? bodyshield/analysis/plots.py
?? bodyshield/analysis/stats.py
?? bodyshield/analysis/tables.py
?? bodyshield/analysis/verify_package.py
?? bodyshield/analysis/videos.py
?? bodyshield/core/
?? bodyshield/paper/build.py
?? bodyshield/policies/
?? bodyshield/robot/audit_labels.py
?? bodyshield/robot/reset_check.py
?? bodyshield/sim/
?? figures/bodybreak_search_efficiency.png
?? figures/bodyshield_before_after.png
?? figures/budget_matched_comparison.png
?? figures/epec_stress_test.png
?? figures/heldout_perturbation_success.png
?? figures/nominal_vs_radius_scatter.png
?? figures/robustness_profiles.png
?? figures/threshold_sensitivity.png
?? logs/sim/
?? paper/appendix_claim_ledger.tex
?? paper/bodyshield.pdf
?? reports/baseline_fairness.md
?? reports/citation_verification.md
?? reports/conservatism_analysis.md
?? reports/gate_1_domain_randomization.md
?? reports/gate_2_before_after_repair.md
?? reports/heldout_generalization.md
?? reports/heldout_physical_modifications.md
?? reports/initial_repo_audit.md
?? reports/oracle_feasibility.md
?? reports/prior_work_hardening.md
?? reports/verifier_audit.md
?? requirements.txt
?? scripts/finalize_v2_artifacts.py
?? tables/sim_budget_matched_results.csv
?? tables/sim_heldout_results.csv
?? tables/sim_main_results.csv
?? tests/test_bodybreak.py
?? tests/test_claim_ledger.py
?? tests/test_robot_safety_gate.py
?? tests/test_schema.py
?? tests/test_verifier_logic.py
?? videos/failure_recovery.md
?? videos/heldout_physical_mods.md
?? videos/index.md
?? videos/oracle_feasibility.md
?? videos/teaser_successes.md`
- Python: `Python 3.10.11`
- File count discovered by recursive local listing: `1794`

## What Exists

- Real Python package with analytic simulation, BodyBreak search, BodyShield repair, audits, release packaging, paper sources, tests, and CI.
- Non-hardware simulation logs and tables under `results/`, `logs/`, `tables/`, and `figures/`.
- Safety-gated hardware command modules under `bodyshield/robot/`; they refuse to run before physical readiness confirmation.

## Plan-Only Files

- `BODYSHIELD_FINAL_PLAN.md`
- `CLI_AGENT_MASTER_PROMPT.md`
- `HARDWARE_AUTONOMOUS_CLI_RUNBOOK.md`
- `NON_HARDWARE_COMPLETION_PROTOCOL.md`
- `NO_HARDWARE_AND_THEORY_DECISION_MEMO.md`
- `REVIEWER_ATTACK_CLOSURE_MATRIX.md`

## Executable Files

- `bodyshield/core/*`
- `bodyshield/policies/*`
- `bodyshield/sim/*`
- `bodyshield/analysis/verify_package.py`
- `bodyshield/robot/*`
- `scripts/run_non_hardware.py`
- `scripts/finalize_v2_artifacts.py`
- `scripts/verify_claims.py`
- `scripts/verify_citations.py`
- `scripts/verify_reproducibility.py`

## Missing Or Blocked Evidence

- real SO-ARM101/SO-101 noise-floor logs
- camera-verifier agreement labels
- reset reliability logs
- all-trials hardware videos
- held-out physical-modification hardware runs
- external trained-policy checkpoints

## Blockers

- Hardware phase is blocked until the user confirms assembled robot, camera, workspace, physical emergency stop, reset protocol, and bounded safe API readiness.
- Final submission readiness is blocked because hardware noise floor, verifier accuracy, reset reliability, real held-out physical modifications, and hardware videos are absent.

## Status

- Non-hardware complete: `yes`, after `python -m bodyshield.analysis.verify_package --json` passes.
- Hardware-ready: `no`, pending physical readiness and safety gate.
- Submission-ready: `no`, because hardware gates are not run.
