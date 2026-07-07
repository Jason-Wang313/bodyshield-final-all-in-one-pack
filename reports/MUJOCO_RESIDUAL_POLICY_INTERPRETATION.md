# MuJoCo Gated Residual Policy Interpretation

This is a learned high-fidelity simulator audit with conservative residual gating, not hardware and not an external robot-policy checkpoint.

## Scope
- Environment: local MuJoCo 2-DOF planar end-effector tasks.
- Training data: simulator corrective labels collected on nominal and seen perturbation buckets.
- Model: CPU ridge residual controller over state, target, base command, policy metadata, task id, and perturbation severities.
- Gate: nominal residual scale 0.00; non-nominal residual scale 1.00; no residual when instantaneous error is within 2.0x task tolerance.
- Evaluation: base analytic command versus adapted gated residual command on nominal, seen, and held-out planar perturbations.
- Trace sample: `results/mujoco_residual_policy_trace_sample.jsonl`.

## Held-out performance
- Rollouts: 72
- Base success rate: 0.000
- Adapted success rate: 0.000
- Base final error: 0.1838
- Adapted final error: 0.1676
- Final-error reduction: 0.0162
- Mean residual norm: 0.0092

## Gate ablation
- Table: `results/mujoco_residual_policy_gate_ablation.csv`.
- Residual-off held-out final-error reduction: 0.0000
- Selected gated held-out final-error reduction: 0.0162
- Always-on nominal success delta: -0.333
- Selected gated nominal success delta: +0.000

## Safe claim
The package now trains and evaluates a local gated residual policy inside MuJoCo dynamics, reducing the gap between analytic repair and high-fidelity learned-policy evidence while avoiding always-on nominal residuals. It still does not establish performance for external neural robot checkpoints, ManiSkill trained policies, real cameras, resets, contact-rich hardware, or physical transfer.
