# Visual WAM Proxy Interpretation

This is a synthetic rendered-frame WAM audit, not real camera video, neural foundation-model training, or physical visual adaptation.

## Scope
- Inputs: current two-channel rendered frame, action, task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: next rendered synthetic visual frame from the analytic trajectory generator.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/visual_wam_trace_sample.jsonl`.

## Held-out performance
- Transitions: 38304
- Rollouts: 2736
- Transition frame MSE: 0.000461
- Transition PSNR: 33.36 dB
- Final frame MSE: 0.001056
- Final centroid error: 0.0972

## Safe claim
The package now includes an action-conditioned visual prediction proxy over generated pixel observations. It tests the software path from BodyBreak perturbations to rendered observations to held-out visual rollout prediction. It does not establish real-video WAM learning, neural visual dynamics, or physical transfer.
