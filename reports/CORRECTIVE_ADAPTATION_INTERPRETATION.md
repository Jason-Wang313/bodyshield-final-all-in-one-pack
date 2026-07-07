# Corrective Adaptation Interpretation

This is a synthetic corrective-trace adaptation audit, not real-robot online learning, neural policy finetuning, or video-conditioned adaptation.

## Scope
- Source policies: nominal, domain randomization, and BodyShield when available.
- Teacher: analytic oracle-style corrective action target.
- Training split: nominal and seen perturbation buckets.
- Held-out split: held-out analytic physical-style perturbation families.
- Trace sample: `results/corrective_adaptation_trace_sample.jsonl`.

## Held-out performance
- Rollouts: 2736
- Base final error: 0.0485
- Adapted final error: 0.0418
- Final-error reduction: 0.0067
- Base success rate: 0.892
- Adapted success rate: 0.896
- Progress gain: 0.0063

## Safe claim
The package now tests a closed local loop: BodyBreak-style perturbations expose synthetic failures, corrective traces produce a residual action adapter, and held-out rollouts measure whether the adapter reduces drift. This is useful evidence for the adaptation mechanism in the analytic trace world; it does not establish physical adaptation, neural policy learning, or visual WAM transfer.
