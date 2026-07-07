# Related Work Audit

Status: `non_hardware_verified_primary_sources`

This audit positions BodyShield against adjacent areas using primary source URLs
or project pages. It is a paper-writing guardrail, not a claim that BodyShield
already beats every external implementation.

| Area | Primary source anchor | What the source covers | BodyShield distinction |
|---|---|---|---|
| Domain randomization | Tobin et al., domain randomization, https://arxiv.org/abs/1703.06907 | Train on randomized simulated visual conditions so the real world appears as another variation. | BodyShield first falsifies the current policy to find low-cost breaking body/control perturbations, then repairs against those counterexamples. |
| Automatic/domain randomization for dexterous manipulation | OpenAI et al., ADR, https://arxiv.org/abs/1910.07113 | Expand a training distribution over randomized simulated environments for sim-to-real transfer. | BodyShield reports discovered perturbations and failure axes rather than only broad randomized training distributions. |
| Randomized simulation review | Muratore et al., https://arxiv.org/abs/2111.00956 | Survey of randomized simulation and sim-to-real reality-gap methods. | BodyShield uses randomization baselines but centers falsification, oracle feasibility, and claim-scoped repair. |
| Robust/adversarial RL | Pinto et al., RARL, https://arxiv.org/abs/1703.02702 | Minimax training with an adversary applying destabilizing disturbances. | BodyShield's adversary is an embodiment-control perturbation search with raw-unit costs and estimated minimal breaking changes. |
| Falsification-based RL | Falsification-Based Robust Adversarial RL, https://arxiv.org/abs/2007.00691 | Integrates temporal-logic falsification into adversarial RL. | BodyShield uses falsification to expose hidden embodiment assumptions and feed a repair set, not only to train against temporal-logic violations. |
| Counterexample-guided RL repair | Safety-critic repair, https://arxiv.org/abs/2405.15430 | Repair trained RL agents against safety counterexamples. | BodyShield's counterexamples are body/control changes such as latency, calibration, gripper limits, payload, contact, and sensing shifts. |
| CEGIS and counterexample-guided control | CEGIS CLF synthesis, https://arxiv.org/abs/2303.10024 | Iterative learner/verifier synthesis of Lyapunov functions and controllers under uncertainty. | BodyShield borrows the counterexample loop but reports empirical policy brittleness and repair in robot task perturbation space. |
| Perception/control synthesis | Counterexample-guided perception/control synthesis, https://arxiv.org/abs/1911.01523 | Uses falsifier traces to model perception errors and synthesize robust controllers. | BodyShield targets embodiment-control assumptions across morphology, actuation, sensing geometry, and contact rather than only perception-model error. |
| Robust MPC and CBF/safety filters | Neural CBF/MPC examples, https://arxiv.org/html/2502.15006v2 | Enforce safety constraints in predictive control and barrier-function settings. | BodyShield is diagnostic and repair-oriented; it does not claim formal safety invariance without hardware and controller certificates. |
| SysID plus retuning | Active exploration for system ID, https://arxiv.org/abs/2404.12308 | Collect targeted data to refine simulator parameters and transfer control. | BodyShield compares sysID-retune as a baseline but also asks which body/control changes break a nominally successful policy. |
| Cross-embodiment datasets and RT-X | Open X-Embodiment, https://arxiv.org/abs/2310.08864 and https://robotics-transformer-x.github.io/ | Large multi-robot dataset and models for cross-embodiment transfer. | BodyShield does not claim foundation-policy generality; it audits hidden embodiment brittleness and repair on a scoped perturbation suite. |
| Morphology-conditioned policies | Morphology-conditioned hypernetworks, https://arxiv.org/html/2402.06570v2 | Learn universal policies across robot morphologies. | BodyShield can test morphology-conditioned policies, but the current artifact does not train a universal cross-robot policy. |
| Manipulation benchmarks | ManiSkill and robosuite, https://arxiv.org/abs/2412.13211 and https://arxiv.org/abs/2009.12293 | Standardized manipulation environments and baselines. | Current BodyShield high-fidelity evidence is bounded probe coverage, not a full external benchmark leaderboard. |
| Real-world robot datasets | DROID, https://arxiv.org/abs/2403.12945 | Large in-the-wild robot manipulation dataset and policy-learning code. | BodyShield's real-video and corrective-trace paths are readiness harnesses until actual datasets or hardware logs are supplied. |

## Paper-Safe Distinction

Domain randomization trains broadly over sampled perturbations. BodyShield
actively searches for perturbations that break the current policy, diagnoses the
failure axis, repairs against discovered counterexamples, and then tests seen
and held-out perturbation buckets. This distinction should be stated as a
mechanism difference, not as a universal superiority claim.

Counterexample-guided repair typically targets safety violations in state or
environment space. BodyShield targets embodiment-control assumptions:
morphology, sensing, latency, calibration, gripper limits, actuation limits,
payload, tool geometry, and contact/friction changes. The unit of falsification
is the lowest-cost body/control change found under a budget that makes a policy
fail while an oracle/tuned policy can still solve the task.

## Remaining Citation Work

Before camera-ready submission, refresh publication metadata for every arXiv
entry, cite venue versions where available, and add full BibTeX entries for any
source promoted from this audit into the paper body.
