# Reviewer Attack Closure Report

| Attack | Closure status after this execution |
|---|---|
| Just domain randomization | Equal-budget analytic comparison generated in `results/breaking_search.csv` and `results/summary_by_method_bucket.csv`. |
| Benchmark not method | Before/after repair implemented through `bodyshield.bodyshield_repair` and summarized in `reports/SIMULATION_SUMMARY.md`. |
| Cheap hardware artifact | Not closed yet; hardware noise floor remains hardware-only. |
| Perturbation makes task impossible | Oracle feasibility baseline is implemented in simulation; hardware oracle remains pending. |
| Artificial perturbations not real transfer | Held-out analytic families are generated; held-out physical modifications remain pending. |
| Metrics arbitrary | Wilson intervals, bootstrap profile summaries, and robustness radius are generated. |
| Adversarial search trivial | Random, one-axis, grid, and BodyBreak comparisons are generated; found-break-only accounting is reported separately from no-break fallback rows; dense minimality challenge rows audit representative BodyBreak found breaks. |
| Repair overfits | Held-out perturbation-family summary is generated; physical held-out tests remain pending. |
| Baselines weak | Nominal, random perturbation tuning, domain-randomization, grid, robust-control, sysID+retune, oracle, human/effect-prior, EPEC, and BodyShield methods are implemented. |
| Too conservative | Execution time, path length, retries, and nominal retention are logged and summarized. |
| No media artifact | Synthetic rollout GIFs are generated and listed in `reports/SIMULATION_ROLLOUT_VIDEOS.md`; real-video WAM readiness validates a future frame-manifest path; real camera/verifier videos remain hardware-only. |
| Manual labeling/reset bias | Not closed yet; verifier audit and reset protocol are hardware-only. |
| AI-generated citation risk | Verified citation table created in `reports/CITATION_VERIFICATION_TABLE.md`; unverified claims are excluded from the paper draft. |
| LLM raw hardware control unsafe | Hardware entry points refuse to run before safety confirmation and do not expose raw motor commands. |
