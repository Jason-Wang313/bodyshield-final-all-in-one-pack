# Post-Nonhardware Repository Audit

Generated: `2026-07-08T02:29:56+00:00`

This audit classifies every remaining evidence tier after the v2 non-hardware package and v3 post-nonhardware pass.

| evidence tier | classification | evidence | residual blocker/risk | allowed wording |
|---|---|---|---|---|
| Python package/tests/CI | complete | `bodyshield/, tests/, Makefile, pyproject.toml` | 67 local tests passed before v3 edits | claim software package only |
| Analytic simulation trials | complete | `results/trials.parquet, logs/sim/results.jsonl` | CPU analytic/synthetic scope | claim analytic-simulation evidence |
| BodyBreak search | complete | `results/breaking_search.csv, reports/BODYBREAK_MINIMALITY_AUDIT.md` | estimated minimal break only | do not claim global minimality |
| BodyShield repair | complete | `results/repair_history.csv, reports/gate_2_before_after_repair.md` | analytic repair policies | claim before/after analytic repair |
| Budget and fairness | complete | `reports/BUDGET_AND_FAIRNESS_AUDIT.md` | baseline tuning remains analytic | claim budget-matched local comparison |
| Claim/citation/repro audits | complete | `reports/CLAIM_LEDGER.md, reports/citation_verification.md, REPRODUCE.md` | local verification | claim audited local package |
| High-fidelity probes | complete only analytic surrogate | `results/high_fidelity_policy_results.csv` | bounded probes, not full external trained policies | claim bounded simulator probes |
| External trained policy benchmark | blocked by external data/checkpoints | `reports/EXTERNAL_CHECKPOINT_BLOCKER.md` | no checkpoint in repo | do not claim external checkpoint validation |
| Real-video WAM | readiness only | `reports/REAL_VIDEO_WAM_RESULTS.md` | dataset missing | schema/readiness only |
| Corrective-trace adaptation | readiness only | `reports/CORRECTIVE_TRACE_RESULTS.md` | dataset missing | synthetic proxy only |
| Oracle feasibility | complete only analytic surrogate | `reports/oracle_feasibility.md` | not physical oracle feasibility | claim analytic upper-bound gap |
| Hardware noise/verifier/reset | blocked by hardware | `reports/HARDWARE_BLOCKER.md` | robot/camera/estop not confirmed | do not claim hardware evidence |
| Held-out physical modifications | blocked by hardware | `reports/HARDWARE_HELDOUT_PHYSICAL_MODS.md` | physical mods not run | do not claim real physical modifications |
| Videos | complete only synthetic | `videos/index.md, videos/hardware/index.md` | generated frames only; no real hardware videos | claim synthetic rollout media |
| Paper | draft only | `paper/main.tex, paper/bodyshield_full_paper.pdf` | needs human review and missing evidence tiers | analytic/simulation study wording only |
| Release | complete local archive | `release/bodyshield_non_hardware_release.zip` | not independent external archive | claim local deterministic bundle |

Bottom line: the repository is strong as a non-hardware analytic/synthetic artifact pack. It is not evidence-complete for a final robotics submission.

PAPER NOT READY: hardware validation/noise floor/verifier/reset/physical modifications/videos are not run; external trained-policy checkpoints and full-scale rollouts are missing; real-video WAM and corrective-trace datasets are missing; oracle feasibility is analytic only; BodyBreak minimality is estimated rather than globally proven; release is local rather than independently archived; human paper review remains open.
