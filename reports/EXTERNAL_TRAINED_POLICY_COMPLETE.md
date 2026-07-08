# External Trained Policy Tier

Status: `partial_complete_self_trained_public_env`; `external_checkpoint_still_blocked`

Completed:

- A real self-trained public Gymnasium `CartPole-v1` policy checkpoint exists at `results/checkpoints/self_trained_cartpole_linear_policy.json`.
- The benchmark is reproducible with `python scripts\run_self_trained_public_env_benchmark.py`.
- Results are written to `results/self_trained_public_env_benchmark.csv`.

Still blocked:

- No user-provided or public pretrained external checkpoint is present.
- No full-scale MuJoCo/ManiSkill trained-policy rollout benchmark is completed.

Reviewer-safe interpretation: the repo now has one small public-env trained-policy benchmark, but the stronger external checkpoint claim remains blocked.
