# Public Pretrained Checkpoint Complete

Status: `complete_public_pretrained_mujoco_checkpoint`

Generated: `2026-07-08T09:04:46+00:00`

The repository now contains and evaluates a real public pretrained checkpoint: SB3/RL-Zoo PPO for `HalfCheetah-v3`, evaluated locally in Gymnasium `HalfCheetah-v5` with its public `vec_normalize.pkl` statistics.

## Source


- Hugging Face model card: https://huggingface.co/sb3/ppo-HalfCheetah-v3
- RL Baselines3 Zoo repository: https://github.com/DLR-RM/rl-baselines3-zoo
- Source repo id: `sb3/ppo-HalfCheetah-v3`
- Snapshot: `6765c82ac33ac720927a722a0b42a1eb09a65700`
- Model SHA256: `8df0cd0c34b5ddf1e5210a5f45507e6d5da7c2f5bfde825e548009aa51d21a6f`
- VecNormalize SHA256: `b364c6b89c475a08290ac03d8e557c337cbdb592b33ef0e38b7e788cc071e759`


## Results

| field | value |
|---|---:|
| nominal mean return | 5883.719 |
| seen actuator-loss base return | 1747.849 |
| seen actuator-loss BodyShield return | 3123.995 |
| tuned action gain | 1.800 |
| held-out mean delta return | 677.408 |
| held-out actuator/compound mean delta return | 1354.815 |

Artifacts:

- `results/public_pretrained_checkpoint_benchmark.csv`
- `results/public_pretrained_checkpoint_rollouts.csv`
- `results/public_pretrained_checkpoint_tuning.csv`
- `results/public_pretrained_checkpoint_delta.csv`
- `figures/public_pretrained_checkpoint_returns.pdf`
- `results/checkpoints/public_sb3_ppo_halfcheetah_v3/ppo-HalfCheetah-v3.zip`
- `results/checkpoints/public_sb3_ppo_halfcheetah_v3/vec_normalize.pkl`

Boundary: Public pretrained SB3/RL-Zoo MuJoCo checkpoint evidence only; evaluated locally in Gymnasium HalfCheetah-v5 using the checkpoint's VecNormalize statistics. This does not claim hardware transfer, manipulation transfer, or superiority over all robust-control/sysID baselines.
