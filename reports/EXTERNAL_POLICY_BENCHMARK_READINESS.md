# External Policy Benchmark Readiness

This report validates the local spec, checkpoint-detection, adapter-loading, and deterministic interface-smoke path for future external trained-policy checkpoints.

It is not external/full-scale MuJoCo or ManiSkill trained-policy evidence. A real benchmark row must have an existing checkpoint, an explicit adapter, and later task-rollout execution beyond this interface smoke.

## Summary
- Rows: 2
- Fixture smoke rows passed: 1
- External checkpoint specs: 1
- External checkpoint interface smokes executed: 0
- Missing external checkpoints: 1
- Failed rows: 0

## Rows
| benchmark_name                                 | policy_id                                  | source              | engine          | task_id              | benchmark_mode                | checkpoint_path                                       | checkpoint_present   | adapter                        | status               | interface_checks_passed   |   steps_requested |   steps_executed |   observation_dim |   expected_action_dim |   final_error |   improvement |   mean_action_norm | evidence_boundary                                                                         | notes                                                                                                                                                                        |
|:-----------------------------------------------|:-------------------------------------------|:--------------------|:----------------|:---------------------|:------------------------------|:------------------------------------------------------|:---------------------|:-------------------------------|:---------------------|:--------------------------|------------------:|-----------------:|------------------:|----------------------:|--------------:|--------------:|-------------------:|:------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| bodyshield_external_policy_benchmark_readiness | fixture_proportional_planar                | fixture             | interface_smoke | planar_reach_fixture | deterministic_interface_smoke |                                                       | False                | fixture:proportional           | fixture_smoke_passed | True                      |                 6 |                6 |                 6 |                     2 |    0.00856236 |      0.279882 |          0.0539304 | Deterministic fixture smoke only; not external checkpoint evidence.                       | Deterministic local smoke policy used to prove the harness path executes.                                                                                                    |
| bodyshield_external_policy_benchmark_readiness | replace_with_external_maniskill_checkpoint | external_checkpoint | maniskill       | PushCube-v1          | deterministic_interface_smoke | external_checkpoints/replace_with_trained_policy.ckpt | False                | your_policy_module:load_policy | missing_checkpoint   | False                     |                 6 |                0 |                16 |                     7 |  nan          |    nan        |        nan         | No external trained-policy evidence was generated because the checkpoint path is missing. | Template row: replace with a real checkpoint and adapter before claiming external policy evidence. Checkpoint path not found; external trained-policy benchmark was not run. |

## Safe claim
The pack now has a runnable harness for external checkpoint readiness. With the included example spec, no external trained-policy checkpoint is present, so no external/full-scale trained-policy benchmark claim is supported.
