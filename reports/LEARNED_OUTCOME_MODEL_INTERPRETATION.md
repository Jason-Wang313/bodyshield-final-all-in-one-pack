# Learned Outcome Model Interpretation

This is a lightweight WAM-style proxy, not a visual world model and not a policy.

## Scope
- Inputs: task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: simulator success rate for a task/robot/policy/perturbation condition.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.

## Held-out performance
- Conditions: 9120
- MAE: 0.084
- Brier score: 0.013
- AUC at 0.50 success threshold: 0.923

## Safe claim
The model shows that the local artifact can learn a reusable outcome predictor over tasks, robots, policies, and body/control perturbations. It does not establish video-based world modeling, real-robot adaptation, or policy learning from physical attempts.
