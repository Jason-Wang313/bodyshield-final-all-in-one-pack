# External Policy Integration Plan

Status: `closed_for_public_pretrained_checkpoint`

The public external-policy gate is closed for one redistributable public checkpoint:

- Source: `sb3/ppo-HalfCheetah-v3`
- Model card: https://huggingface.co/sb3/ppo-HalfCheetah-v3
- RL-Zoo source: https://github.com/DLR-RM/rl-baselines3-zoo
- Local artifacts: `results/checkpoints/public_sb3_ppo_halfcheetah_v3/`
- Reproducible runner: `python scripts\run_public_checkpoint_benchmark.py`

Optional future extensions:

1. Add a ManiSkill manipulation checkpoint with wrappers, normalization, seeds, horizon, and rollout script.
2. Add a second locomotion family only if the paper claims broader trained-policy coverage.
3. Add a user-provided/private checkpoint only as an additional evidence tier, not as a blocker for the current public checkpoint gate.

Reviewer-safe boundary: Public pretrained SB3/RL-Zoo MuJoCo checkpoint evidence only; evaluated locally in Gymnasium HalfCheetah-v5 using the checkpoint's VecNormalize statistics. This does not claim hardware transfer, manipulation transfer, or superiority over all robust-control/sysID baselines.
