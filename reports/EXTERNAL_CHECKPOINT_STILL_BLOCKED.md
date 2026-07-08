# External Checkpoint Still Blocked

Status: `blocked_external_checkpoint_missing`

The self-trained public-env benchmark is complete, but it does not provide a public pretrained or user-provided external checkpoint. The following are still missing:

- Trained external checkpoint file or URL with redistribution/license status.
- Exact environment version, wrappers, observation/action normalization, and checkpoint loader.
- Seed list, horizon, success metric, and evaluation protocol.
- Compute-matched tuning budget for BodyShield, domain randomization, robust-control/sysID alternatives, and the original policy.
- Reproducible rollout script for the external checkpoint in its intended environment.

Allowed wording: external checkpoint integration remains blocked.
