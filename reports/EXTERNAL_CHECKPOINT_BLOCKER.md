# External Checkpoint Blocker

Status: `blocked_external_data_checkpoints`

Missing items:

- A trained policy checkpoint from a public or user-provided benchmark.
- Exact environment version, observation/action wrappers, normalization, seed list, and evaluation horizon.
- Compute-matched baseline tuning budget for the same controller family.
- Reproducible rollout script that can regenerate the benchmark table without fixture shortcuts.

The repository contains local analytic and bounded MuJoCo/ManiSkill probes, but those are not a substitute for an external trained-policy checkpoint benchmark.
