# No-Hardware and Theory Paper Decision Memo

The user asked two separate questions:

1. Would Guanya be okay with no-hardware/theory-style work?
2. Would ICRA be okay with no-hardware/theory-style work?

## Short answer

Guanya: **yes in principle**, if it is algorithmically/foundational and still tied to real robot learning/control.
ICRA: **yes in principle**, but strong accept is harder unless the theory/simulation result is unusually crisp, broad, and robotics-specific.

For the BodyShield project, the highest-odds ICRA paper remains:
**simulation + real SO-ARM101/SO-101 validation + repair method.**

The no-hardware tracks should be treated as:
- backup paper;
- companion theory paper;
- supporting section;
- or L4DC / CoRL / RSS / ICRA theory-style submission depending on final shape.

## Why Guanya can fit theory

Guanya's public research descriptions emphasize the intersection of machine learning and control theory, spanning theory/foundations, practical algorithms, and real-world robotics/autonomy. That means theory/foundation work can fit if it is not divorced from execution.

A theory paper that fits Guanya should be about:
- robust control / learning under body-control uncertainty;
- sample efficiency of adversarial perturbation repair;
- stability/safety under learned repair;
- model-based control with embodiment uncertainty;
- reachability or CBF-style guarantees for repaired policies;
- principled active testing/falsification of learned controllers.

A theory paper that does **not** fit well:
- generic ML robustness with robotics wording;
- video-only representation theory with no control/execution link;
- pure benchmark paper without method or guarantee.

## Why ICRA can accept no-hardware papers

ICRA/RAS guidance says a paper should not be rejected **without review** merely because it lacks real-world experiments.
This does not mean reviewers must accept weak validation. It means no hardware is not an automatic desk-rejection reason.

No-hardware ICRA papers work best when they have:
- a theorem;
- a rigorous algorithmic contribution;
- a strong robotics simulator benchmark;
- broad comparisons;
- provable stability/safety/optimality/sample-efficiency property;
- or a new robotic planning/control formulation.

## Ranked no-hardware paper types

### Track A — Theory of embodiment-adversarial repair

Title:
**Sample-Efficient Embodiment-Adversarial Repair for Robust Robot Policies**

Claim:
Falsification-guided repair is more sample-efficient than random/domain-randomized repair under structured embodiment uncertainty.

Guanya fit: 5/5
ICRA fit: 3.5-4/5
Why:
Strong if it has theorem + simulation. Very aligned with learning/control foundations.

Needed:
- formal perturbation space;
- assumptions on Lipschitz/smooth success boundary;
- active search regret/sample complexity;
- min-max repair objective;
- comparison to random sampling/domain randomization;
- simulation validation.

Risk:
If theorem is weak or too abstract, ICRA reviewers may call it ML/control theory without robotics punch.

### Track B — Reachability / CBF-safe BodyShield

Title:
**Falsification-Guided Safe Policy Repair under Embodiment Uncertainty**

Claim:
Use adversarial body perturbation discovery to update a safety/feasibility set, then enforce repaired policies through CBF/reachability constraints.

Guanya fit: 5/5
ICRA fit: 4/5
Why:
Control-theoretic, safety, robotics-specific. Very Guanya-coded.

Needed:
- formal safe set;
- robust invariant / reach-avoid condition;
- simulation on robot dynamics;
- comparison to robust MPC / CBF baselines.

Risk:
Harder math; may drift from Pathak.

### Track C — Simulation-only BodyShield with broad robot/task suite

Title:
**Embodiment Falsification and Repair across Simulated Robot Bodies**

Claim:
Policies with similar nominal success have different body-control robustness profiles; BodyShield improves held-out perturbation robustness.

Guanya fit: 4/5
ICRA fit: 3/5
Why:
Good but weaker than real-robot version because physical contact and hardware assumptions are central.

Needed:
- many robots;
- many tasks;
- strong baselines;
- no overclaiming real-world deployment.

Risk:
ICRA reviewers ask: why no real robot?

### Track D — Action-representation fragility theory

Title:
**Which Robot Action Spaces Survive Body Changes?**

Claim:
Object-relative effect actions and controller-wrapped waypoints have larger embodiment robustness radius than raw joint/end-effector actions under structured perturbations.

Guanya fit: 4/5
Pathak fit: 4/5
ICRA fit: 3.5/5

Needed:
- formal analysis of action representation under perturbation;
- simulation + maybe small real validation if possible;
- strong link to human/effect policies.

Risk:
Can become a study paper, not a method paper.

### Track E — Offline cross-embodiment dataset analysis

Title:
**Hidden Embodiment Confounding in Cross-Robot Datasets**

Claim:
Data from mixed robot bodies entangles task effects with body-specific action realizations; body-conditioned decoders or effect-conditioned representations reduce conflict.

Guanya fit: 3/5
Pathak fit: 5/5
ICRA fit: 2.5-3/5

Needed:
- strong dataset;
- careful empirical analysis;
- real/sim follow-up.

Risk:
Better for ML/CoRL workshop than ICRA main unless paired with execution evidence.

## Recommendation

Primary:
**BodyShield robot paper**.

Secondary/no-hardware companion:
**Track A or Track B**.

If the goal is Guanya specifically:
- Track B is the most Guanya-coded no-hardware theory paper.
- Track A is the cleanest algorithmic foundation.
- Track C is easiest but less strong.

If the goal is ICRA strong accept:
- robot BodyShield remains the best.
- no-hardware Track B can work if the math is serious and the simulation is broad.
- no-hardware Track C is unlikely to be strong accept unless the results are extremely clean.
