# External Policy Integration Plan

Status: `ready_for_checkpoint_when_available`

1. Place a redistributable checkpoint under `external_checkpoints/` or record an immutable download URL.
2. Add a spec row to `configs/external_policy_benchmark.example.json` with checkpoint path, adapter module, expected observation/action dimensions, wrappers, seeds, horizon, and metric.
3. Implement the adapter as `module:function`, returning a callable policy or object with `predict()`/`act()`.
4. Run `python scripts\run_external_policy_benchmark.py --spec <spec>` for interface validation.
5. Run a task-rollout benchmark that logs raw episode returns/successes, BodyBreak perturbation search, BodyShield repair, domain-randomization baseline, budget accounting, and held-out perturbations.
6. Update `reports/SUBMISSION_READY_AUDIT.md` only after the real checkpoint rollout passes.

Until then, `reports/EXTERNAL_CHECKPOINT_STILL_BLOCKED.md` is the controlling status.
