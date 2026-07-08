# Reviewer Prebuttal

## This is just domain randomization.
BodyShield is framed as falsification-guided repair, not broad random sampling. The current analytic evidence reports BodyBreak search separately from domain randomization and random tuning, then evaluates repair on seen and held-out buckets.

## Minimal perturbation is overclaimed.
The paper draft and claim ledger use "estimated minimal" and report search budget, break-found rate, threshold sensitivity, and a dense post-hoc candidate-pool challenge for representative BodyBreak cases. Global optimality is not claimed.

## The simulator is too synthetic.
Correct for the current local execution. Reports explicitly label the main claim as analytic-simulation plus one scoped public-checkpoint result, add tabular outcome, synthetic visual, synthetic rollout GIF media, NumPy neural visual-latent, synthetic trajectory, synthetic corrective-adaptation, learned MuJoCo gated residual-policy audits with gate ablation against residual-off and always-on variants, one public SB3/RL-Zoo HalfCheetah checkpoint rollout, real-video WAM frame-manifest readiness, and corrective-trace dataset readiness. Real-video/foundation-scale WAM training, broad manipulation/foundation-policy checkpoint suites, real corrective traces, and real robot results remain missing evidence slots.

## The repair might be too conservative.
Nominal retention, execution time, path length, retries, and secondary safety proxies are logged and summarized. A method that wins only by slowing down should be visible in `results/secondary_metrics_by_method.csv`.

## Failures may be impossible tasks.
`results/oracle_feasibility.csv` checks oracle success at BodyBreak perturbations. Hardware oracle evidence is still required before physical claims.
