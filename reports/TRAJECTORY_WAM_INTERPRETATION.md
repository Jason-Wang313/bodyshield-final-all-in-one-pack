# Trajectory WAM Proxy Interpretation

This is a synthetic proprioceptive trajectory model, not video prediction, neural policy learning, or hardware adaptation.

## Scope
- Inputs: current 2-D state, action, target, task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: next synthetic state delta for action-conditioned traces generated from the analytic BodyShield setup.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/trajectory_wam_trace_sample.jsonl`.

## Held-out performance
- Transitions: 164160
- Rollouts: 9120
- Transition state RMSE: 0.0230
- Transition XY RMSE: 0.0164
- Final XY MAE: 0.0472
- Final progress MAE: 0.0391

## Safe claim
The package now includes an action-conditioned trajectory-level audit in addition to scalar, visual, and neural-latent prediction. It verifies that BodyShield perturbations can drive a learned next-state/rollout model over synthetic traces. It does not establish real-video WAM performance, real corrective-trace adaptation, or trained robot-policy transfer.
