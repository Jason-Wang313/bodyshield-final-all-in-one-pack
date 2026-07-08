# Self-Trained Public Environment Complete

Status: `complete_self_trained_public_env_only`

Generated: `2026-07-08T09:01:20+00:00`

The repository now contains a real CPU-only trained checkpoint for a public Gymnasium environment: `CartPole-v1`. The policy is a linear CartPole controller trained by cross-entropy search, saved at `results/checkpoints/self_trained_cartpole_linear_policy.json`, and evaluated under nominal, seen BodyBreak-style perturbations, and held-out perturbations.

| field | value |
|---|---|
| benchmark csv | `results/self_trained_public_env_benchmark.csv` |
| training curve | `results/self_trained_public_env_training_curve.csv` |
| bodybreak csv | `results/self_trained_public_env_bodybreak.csv` |
| budget csv | `results/self_trained_public_env_budget.csv` |
| returns figure | `figures/self_trained_public_env_returns.pdf` |
| training figure | `figures/self_trained_public_env_training_curve.pdf` |
| repaired checkpoint | `results/checkpoints/self_trained_cartpole_linear_policy.json` |
| heldout nominal mean return | 240.300 |
| heldout BodyShield-repaired mean return | 293.900 |
| heldout domain-randomization mean return | 298.900 |
| BodyShield minus nominal heldout delta | 53.600 |
| BodyShield minus domain-randomization heldout delta | -5.000 |

Boundary: This closes only a small self-trained public Gymnasium environment evidence slot. It does not close the user-provided or public pretrained checkpoint slot.

Allowed wording: a self-trained public-environment policy benchmark was completed. Do not call this a MuJoCo/ManiSkill pretrained-policy benchmark, hardware transfer evidence, or proof that BodyShield beats domain randomization.
