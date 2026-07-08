# External Trained Policy Tier

Status: `complete_public_pretrained_checkpoint`

Completed:

- Public pretrained SB3/RL-Zoo checkpoint integrated: `sb3/ppo-HalfCheetah-v3`.
- Full-horizon MuJoCo/Gymnasium rollouts completed for `HalfCheetah-v5`.
- Public checkpoint and VecNormalize statistics are copied into `results/checkpoints/public_sb3_ppo_halfcheetah_v3/`.
- Reproducible runner: `python scripts\run_public_checkpoint_benchmark.py`.

Remaining scope limits:

- This is one locomotion checkpoint, not a broad trained-policy suite.
- No ManiSkill manipulation checkpoint is included.
- Hardware, real-video WAM, and real corrective traces remain separate blockers.

Allowed wording: external public pretrained MuJoCo checkpoint benchmark complete.
