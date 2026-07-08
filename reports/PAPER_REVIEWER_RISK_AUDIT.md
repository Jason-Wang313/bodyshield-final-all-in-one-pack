# Paper Reviewer Risk Audit

| Severity | Location | Likely complaint | Fix already applied | Remaining evidence slot |
|---|---|---|---|---|
| High | Simulation Results | Evidence is mostly analytic and may not transfer to real contact dynamics. | Claim boundary, ledger, learned scalar/visual/neural-latent/trajectory/corrective audits, learned MuJoCo gated residual-policy audit with gate ablation, bounded high-fidelity benchmark tables, one public SB3/RL-Zoo HalfCheetah checkpoint rollout, and readiness reporting separate evidence tiers. | Real-video WAM, broad manipulation/foundation-policy checkpoint suite, or hardware. |
| High | BodyBreak | Minimal perturbation sounds globally optimal. | Paper uses "estimated" and reports budgets, fallback rows, threshold sensitivity, and a dense post-hoc minimality challenge. | Formal global proof or stronger high-fidelity optimizer if making stronger claims. |
| High | BodyShield | Repair could win by being conservative. | Secondary metrics include execution time, path length, retries, and nominal retention. | Physical execution-time/path-length measurements. |
| Medium | MuJoCo residual policy | The residual gate could look arbitrary. | Gate ablation compares residual-off, always-on, non-nominal-only, and selected gated variants for held-out gain and nominal preservation. | Additional public checkpoints or hardware traces. |
| Medium | External policy benchmarks | A reader may expect broad imported trained-policy checkpoints. | `reports/PUBLIC_PRETRAINED_CHECKPOINT_COMPLETE.md` records one public HalfCheetah checkpoint; `reports/EXTERNAL_BASELINE_FAIRNESS.md` records the action-gain fairness risk; `reports/EXTERNAL_POLICY_BENCHMARK_READINESS.md` remains a harness for future manipulation checkpoints. | Broad manipulation/foundation-policy checkpoints plus full task-rollout adapters. |
| Medium | Media artifacts | Synthetic GIFs might be mistaken for real videos. | `reports/SIMULATION_ROLLOUT_VIDEOS.md` and the claim ledger label them as generated rollout media only. | Real camera/verifier videos from hardware. |
| Medium | Real-video WAM | A reader may expect camera sequences or foundation-video training. | `reports/REAL_VIDEO_WAM_READINESS.md` records fixture smoke and missing-dataset rows explicitly. | Real camera frame manifests plus substantive real-video/foundation WAM training. |
| Medium | Corrective traces | A reader may expect real failed-attempt corrections or online adaptation. | `reports/CORRECTIVE_TRACE_READINESS.md` records fixture smoke and missing-dataset rows explicitly. | Real robot or external high-fidelity corrective trace datasets plus substantive adaptation. |
| Medium | Baselines | Domain randomization, action-scaling, and sysID baselines may be too stylized or under-matched. | Separate random tuning, domain randomization, grid, robust control, sysID, oracle, EPEC, and human/effect policies are implemented; the public checkpoint has an explicit fairness caveat. | Compute-matched external controller baselines in the same checkpoint environment and hardware. |
| Medium | Feasibility | Perturbations may make tasks impossible. | Oracle feasibility passes for all analytic BodyBreak failures. | Hardware oracle feasibility. |

## Safer Wording

| Risky wording | Safer wording |
|---|---|
| BodyBreak finds the minimal perturbation. | BodyBreak estimates the lowest-cost breaking perturbation found under a fixed evaluator budget. |
| BodyShield transfers to held-out physical modifications. | BodyShield improves held-out analytic perturbation families; physical transfer remains untested until hardware. |
| The method is simulator independent. | The software stack separates analytic, learned scalar/visual/neural-latent/trajectory/corrective proxy, learned MuJoCo gated residual-policy, bounded MuJoCo, bounded ManiSkill, and future hardware evidence tiers. |
