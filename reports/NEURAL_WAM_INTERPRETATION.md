# Neural WAM Proxy Interpretation

This is a NumPy MLP visual-latent WAM audit over generated observations, not real camera video, a foundation video model, or physical visual adaptation.

## Scope
- Inputs: visual latents from the current rendered frame, action, task id, robot id, policy id, policy metadata, and embodiment-control perturbation severities.
- Target: next visual latent extracted from the generated rendered-frame trajectory.
- Model: one-hidden-layer NumPy MLP trained on CPU with deterministic seeds.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/neural_wam_trace_sample.jsonl`.

## Training
- Hidden units: 48
- Max train samples: 12000
- Final epoch: 64
- Final train latent MSE: 0.001719
- Final held-out latent MSE: 0.001162

## Held-out performance
- Transitions: 38304
- Rollouts: 2736
- Transition latent MSE: 0.002514
- Transition centroid error: 0.1033
- Final latent MSE: 0.008028
- Final centroid error: 0.1668

## Safe claim
The package now includes a trained nonlinear neural audit that predicts action-conditioned visual-state dynamics over synthetic rendered observations. This closes the local missing-neural-dynamics gap, but it still does not establish real-video WAM learning, large-scale foundation-model behavior, high-fidelity robot-policy transfer, or physical adaptation.
