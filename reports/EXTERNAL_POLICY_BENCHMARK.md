# External Policy Benchmark

Generated: `2026-07-08T02:29:54+00:00`

Status: `partial_analytic_surrogate`; external trained-policy evidence remains blocked.

The v3 pass found no public or user-provided trained policy checkpoint inside this repository. It therefore exports a local residual-policy surrogate summary from existing generated MuJoCo-style rollouts and labels it as surrogate evidence only.

| benchmark | status | n rollouts | delta success | limitation |
|---|---|---:|---:|---|
| mujoco_residual_policy_surrogate | complete_only_local_surrogate | 252 | 0.067 | Does not close the external trained-policy checkpoint evidence tier. |
| mujoco_residual_policy_surrogate | complete_only_local_surrogate | 72 | 0.000 | Does not close the external trained-policy checkpoint evidence tier. |
| mujoco_residual_policy_surrogate | complete_only_local_surrogate | 180 | 0.094 | Does not close the external trained-policy checkpoint evidence tier. |
| external_trained_policy_checkpoint | blocked_external_data_checkpoints | 0 |  | Requires public or provided trained policy checkpoints plus compute-matched rollout protocol. |

Artifacts:

- `results/external_policy_benchmark.csv`
- `figures/external_policy_bodyshield_delta.pdf`
- `results/mujoco_residual_policy_eval.csv`

Allowed wording: BodyShield is evaluated on local analytic and bounded high-fidelity surrogates. Do not claim external trained-policy validation.
