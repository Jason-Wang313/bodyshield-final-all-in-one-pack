# Full Reviewer Prebuttal

Generated: `2026-07-08T02:29:58+00:00`

| # | reviewer attack | response |
|---:|---|---|
| 1 | This is just domain randomization. | No. The package reports budget-matched domain randomization and dynamics-randomization-style baselines. The allowed claim is narrower: diagnosis-driven repair can improve the tested analytic perturbation families under the same local budget. |
| 2 | Domain randomization is stronger and more established. | Agreed; it is the dangerous baseline. BodyShield must beat it under equal or lower budget before any stronger wording. |
| 3 | This is only a benchmark. | The package includes before/after repair artifacts, not only stress tests, but hardware repair evidence is still blocked. |
| 4 | The perturbations are artificial. | Some are analytic/control perturbations. Physical-style proxies exist, while real physical modifications remain blocked by hardware. |
| 5 | The method overfits to discovered failures. | Held-out perturbation families and robustness profiles are included, but external checkpoint and physical held-out tests remain future evidence. |
| 6 | BodyBreak minimality is not proven. | Correct. The claim is finite-budget estimated minimality over evaluated candidates only. |
| 7 | Oracle feasibility is synthetic. | Correct. It is an analytic upper-bound audit, not physical oracle feasibility. |
| 8 | Baselines may be under-tuned. | The v2/v3 audits require budget accounting and fair tuning; external trained-controller compute matching remains unresolved. |
| 9 | High-fidelity probes are too small. | Correct. They are bounded probes, not full benchmark closure. |
| 10 | No real videos exist. | Correct. Current media are generated/synthetic; videos/hardware is a blocked placeholder. |
| 11 | No real corrective traces exist. | Correct. Readiness checks exist, dataset evidence does not. |
| 12 | No real-video WAM data exist. | Correct. The repository only defines readiness/schema. |
| 13 | The safe API is not a safety proof. | Correct. It is a software gate and does not replace physical safety validation. |
| 14 | The paper is too short for final submission. | Correct. v3 creates a fuller draft, but the readiness audit still marks the paper not ready. |
| 15 | The release is not externally archived. | Correct. It is a local deterministic archive, not independent preservation. |
| 16 | The method may fail under perception/contact shifts. | Yes. Those are listed as limitations and require external/hardware evidence. |
| 17 | Embodiment-aware steering methods already solve this. | They adapt/steer execution. BodyShield is framed as falsify hidden assumptions, repair, and validate held-out shifts. |
| 18 | Robust MPC/CBF/sysID could solve it. | Those are strong alternative families. BodyShield should be compared fairly, not declared superior globally. |
| 19 | EPEC/human-effect policies distract from the core. | They are stress-test alternatives only; BodyShield remains the main method. |
| 20 | The repo overclaims readiness. | The v3 readiness audit explicitly says the paper is not ready and names blockers. |

Primary artifacts: `reports/POST_NON_HARDWARE_REPO_AUDIT.md`, `reports/METHOD_THEORY_STRENGTHENING.md`, `reports/BUDGET_AND_FAIRNESS_AUDIT.md`, `reports/EXTERNAL_POLICY_BENCHMARK.md`, `reports/HIGH_FIDELITY_POLICY_RESULTS.md`, and `reports/SUBMISSION_READY_AUDIT.md`.
