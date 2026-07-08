# External Checkpoint Blocker

Status: `blocked_external_checkpoint_missing`

The self-trained public-env benchmark is complete, but no user-provided or public pretrained external checkpoint is present. The controlling status file is `reports/EXTERNAL_CHECKPOINT_STILL_BLOCKED.md`.

Still missing:

- Trained external checkpoint file or URL with redistribution/license status.
- Exact environment version, wrappers, observation/action normalization, and checkpoint loader.
- Seed list, horizon, success metric, and evaluation protocol.
- Compute-matched tuning budget for BodyShield, domain randomization, robust-control/sysID alternatives, and the original policy.
- Reproducible rollout script for the external checkpoint in its intended environment.

Allowed wording: self-trained public-env benchmark complete; external checkpoint integration remains blocked.
