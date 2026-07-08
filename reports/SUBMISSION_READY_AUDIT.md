# Submission Ready Audit

Generated: `2026-07-08T02:29:58+00:00`

| gate name | pass/fail | evidence | residual risk | allowed wording |
|---|---|---|---|---|
| software_package | pass | `bodyshield/, tests/, Makefile` | low | software package complete |
| analytic_simulation | pass | `results/trials.parquet, logs/sim/results.jsonl` | analytic only | analytic-simulation evidence |
| budget_fairness | pass | `reports/BUDGET_AND_FAIRNESS_AUDIT.md` | external controller matching open | budget-matched local baselines |
| claim_citation_repro | pass | `reports/CLAIM_LEDGER.md, reports/citation_verification.md, REPRODUCE.md` | local only | audited local package |
| high_fidelity_bounded | pass_with_scope_limit | `results/high_fidelity_policy_results.csv` | bounded probes only | bounded simulator probes |
| external_trained_policy | fail | `reports/EXTERNAL_CHECKPOINT_BLOCKER.md` | checkpoint missing | do not claim external policy validation |
| real_video_wam | fail | `reports/REAL_VIDEO_WAM_RESULTS.md` | dataset missing | readiness only |
| corrective_trace | fail | `reports/CORRECTIVE_TRACE_RESULTS.md` | dataset missing | synthetic proxy only |
| hardware_safety_noise_verifier_reset | fail | `reports/HARDWARE_BLOCKER.md` | hardware not confirmed or run | software readiness only |
| heldout_physical_modifications | fail | `reports/HARDWARE_HELDOUT_PHYSICAL_MODS.md` | physical mods not run | do not claim physical held-out validation |
| hardware_videos | fail | `videos/hardware/index.md` | real videos missing | do not claim real videos |
| paper_human_review | fail | `paper/main.tex, paper/bodyshield_full_paper.pdf` | human review open and evidence incomplete | draft analytic/simulation paper |
| external_archive | fail | `release/bodyshield_non_hardware_release.zip` | local archive only | local release bundle |

PAPER NOT READY: hardware validation/noise floor/verifier/reset/physical modifications/videos are not run; external trained-policy checkpoints and full-scale rollouts are missing; real-video WAM and corrective-trace datasets are missing; oracle feasibility is analytic only; BodyBreak minimality is estimated rather than globally proven; release is local rather than independently archived; human paper review remains open.
