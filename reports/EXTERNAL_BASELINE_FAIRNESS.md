# External Baseline Fairness

Status: `scoped_fairness_report_for_public_checkpoint`

This report bounds the public SB3/RL-Zoo HalfCheetah checkpoint result. It exists because the public-checkpoint BodyShield repair uses a gated action-gain adapter, and a reviewer can reasonably ask whether the improvement is just hand-tuned action scaling.

## What Was Run

- Public checkpoint: `sb3/ppo-HalfCheetah-v3`
- Evaluation environment: Gymnasium `HalfCheetah-v5`
- Horizon: `1000`
- Evaluation seeds: `20,21,22,23,24`
- Tuning seeds: `10,11,12`
- Tuning artifact: `results/public_pretrained_checkpoint_tuning.csv`
- Rollout artifact: `results/public_pretrained_checkpoint_rollouts.csv`
- Summary artifact: `results/public_pretrained_checkpoint_benchmark.csv`
- Delta artifact: `results/public_pretrained_checkpoint_delta.csv`

The adapter tunes a scalar `action_gain` over the fixed candidate set logged in `results/public_pretrained_checkpoint_tuning.csv`. It is selected on the seen actuator-loss perturbation `actuator_0.65` and then applied only when the perturbation has reduced actuator authority (`action_scale < 1.0`).

## Fair Claim

The fair claim is:

> For one public SB3/RL-Zoo HalfCheetah checkpoint, a diagnosed actuator-authority repair improves the logged seen actuator-loss perturbation and produces positive mean delta on the logged held-out actuator/compound family.

This is a narrow external-policy sanity benchmark. It is not evidence that BodyShield is superior to all action-scaling, dynamics-randomization, robust-control, sysID, MPC, CBF, or foundation-policy adaptation methods.

## Baseline Risk

The strongest alternative explanation is that a compute-matched action-scaling baseline, tuned on the same seen actuator-loss seeds and evaluated on the same held-out seeds, may recover some or all of the reported gain. In this benchmark, BodyShield's repair is intentionally simple and interpretable: diagnose actuator authority loss, then compensate with a bounded scalar gain.

## What Would Be Stronger

A stronger trained-policy benchmark would add:

- A matched action-gain baseline reported as its own method row.
- A dynamics-randomization or domain-randomization policy trained for the same environment and budget.
- A robust-control/sysID baseline with its own logged tuning budget.
- A second public MuJoCo checkpoint family.
- A manipulation checkpoint, preferably ManiSkill or another robot-manipulation environment.
- Real hardware noise floor, verifier agreement, reset reliability, held-out physical modifications, and all-trials video.

## Wording Boundary

Allowed wording: one public pretrained MuJoCo checkpoint benchmark is complete with a scoped actuator-loss repair.

Disallowed wording: this result proves broad trained-policy robustness, manipulation transfer, hardware transfer, or dominance over compute-matched action scaling, domain randomization, robust control, sysID, MPC, CBF, or foundation-policy adaptation.
