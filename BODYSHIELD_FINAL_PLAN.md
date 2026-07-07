# BodyShield Final Plan

## 0. Final decision

The main paper is:

**BodyShield: Falsifying and Repairing Hidden Embodiment Assumptions in Robot Policies**

This is not a benchmark paper.
This is not a Mini-ENPIRE paper.
This is not an EPEC-only paper.
This is not a human-video-only paper.

It is a **falsification-to-repair method paper**.

EPEC / human-effect-prior policies are included as one stress-test family because they are highly relevant to Pathak-style video/affordance work, but the main novelty is BodyShield.

## 1. Paper thesis

Robot policies are normally evaluated on nominal hardware. But deployment changes the body-control interface:
- latency
- calibration
- action noise
- joint limits
- gripper range
- tool geometry
- payload
- speed/torque caps
- sensing geometry
- contact/friction

Two policies may have similar nominal success yet very different hidden embodiment assumptions.

BodyShield:
1. actively finds the smallest body/control perturbations that break a policy;
2. diagnoses the failure axis;
3. repairs the policy/action representation by optimizing worst-case success over discovered perturbations;
4. validates repair on seen perturbations, held-out perturbation families, and held-out physical modifications.

## 2. Final contributions

### Contribution 1 — Embodiment falsification

Define and estimate the **minimal breaking perturbation**: the smallest body/control perturbation that drops policy success below a threshold or causes a specified success-rate collapse.

Outputs:
- robustness profiles
- robustness radius
- failure axis attribution
- compound perturbation search

### Contribution 2 — Embodiment-adversarial repair

Use discovered failures to repair the policy.

BodyShield objective:

```
theta* = argmax_theta min_{z in Z_break(theta_old) U Z_train} Success(policy_theta, task, z)
```

CPU-feasible implementations:
- candidate action library + success predictor
- Bayesian optimization / CMA-ES over policy parameters
- failure-conditioned repair library
- conservative controller with learned failure-specific margins
- robust action selection over adversarial perturbation set

### Contribution 3 — Real robot validation

SO-ARM101/SO-101 used as a controlled low-cost embodiment-control stress-test platform:
- not claimed as high-performance robot;
- used because its constraints expose hidden body assumptions;
- quantified noise floor;
- automatic verifier;
- real failure/recovery videos;
- held-out physical modifications.

### Contribution 4 — Simulation breadth

Simulation covers more bodies/tasks/perturbations than hardware:
- multiple robot morphologies;
- broad perturbation families;
- compound perturbation search;
- baselines under equal trial budgets;
- support for theory/no-hardware companion track.

### Contribution 5 — EPEC/human-effect stress test

Include policies that preserve desired effects or imitate human/video affordances:
- direct human/effect-prior policy
- controller-guided action repair
- EPEC-style effect-preserving action alternatives
- BodyShield applied to each

This shows BodyShield is useful for Pathak-style scalable priors but keeps the paper grounded in Guanya-style execution.

## 3. Core novelty defense

### Not domain randomization

Domain randomization samples perturbations broadly.
BodyShield searches for the minimal perturbation that actually breaks the policy, then repairs the specific hidden assumption.

Required evidence:
- same trial budget comparison vs domain randomization;
- BodyShield must improve held-out perturbation robustness with fewer trials.

### Not benchmark only

BodyBreak diagnosis alone is not enough.
BodyShield must improve execution.

Required evidence:
- before/after repair success;
- seen and unseen perturbation improvement;
- nominal success preserved.

### Not cheap-arm demo

The cheap robot is a controlled stress-test instrument.

Required evidence:
- hardware noise floor;
- repeatability;
- calibration;
- held-out physical modifications;
- all logs/videos.

### Not impossible-task artifact

For every claimed failure:
- oracle feasibility policy or retuned policy must solve the task under the same perturbation.
This proves the perturbation breaks the policy, not the task.

## 4. Main experiments

### Experiment 1 — Hidden brittleness

Question:
Do policies with similar nominal success have different minimal breaking perturbations?

Methods:
- nominal policy
- robust/conservative policy
- human/effect-prior policy
- domain-randomized policy
- BodyShield-repaired policy

Outputs:
- robustness profiles;
- nominal success vs robustness radius scatter;
- examples of policies with same nominal success but different failure thresholds.

### Experiment 2 — BodyBreak search quality

Question:
Does adversarial search find smaller failures than random/grid/one-axis search?

Baselines:
- random perturbation search
- one-axis binary search
- grid search
- BodyBreak compound adversarial search

Outputs:
- minimal breaking perturbation cost;
- trials to find failure;
- compound failures missed by one-axis sweeps.

### Experiment 3 — BodyShield repair

Question:
Does falsification-guided repair improve robustness?

Baselines:
- nominal
- random/domain-randomized tuning
- worst-case grid tuning
- robust/conservative controller
- sysID+retune
- BodyShield

Outputs:
- success on seen perturbations;
- success on held-out perturbation levels;
- success on held-out perturbation families;
- nominal performance retention;
- trial efficiency.

### Experiment 4 — Held-out physical modifications

Question:
Does repair transfer beyond artificial/software perturbations?

Train/repair on:
- latency
- joint limits
- action noise
- calibration offset

Test on:
- actual payload
- tool extension
- physical gripper restriction
- camera extrinsics shift
- different friction/contact surface
- workspace obstacle

This is crucial for reviewer defense.

### Experiment 5 — Oracle feasibility

Question:
Are failures due to task impossibility or policy brittleness?

For each claimed breaking perturbation:
- run oracle tuned policy or expert scripted controller;
- prove task remains solvable.

### Experiment 6 — Hardware noise floor

Question:
Can we separate cheap hardware noise from systematic embodiment failure?

Metrics:
- repeated identical action success;
- end-effector repeatability;
- commanded vs actual joint error;
- calibration drift;
- label accuracy;
- mechanical fault rate.

### Experiment 7 — EPEC/human-effect stress test

Question:
Are human/effect-prior policies especially brittle under hidden embodiment assumptions?

Compare:
- direct human/effect prior
- controller-guided action repair
- EPEC-style alternative action search
- EPEC + BodyShield

Output:
- BodyShield improves human/effect-prior robustness without making EPEC the headline.

## 5. Task suite

Hardware tasks:
1. push block to target
2. press button / switch
3. slide object along track
4. pick block into bin
5. pull ring / small drawer
6. constrained placement around obstacle
7. tool-extension push
8. rotate/align object using contacts

Each task must have:
- automatic verifier;
- standard reset;
- safety envelope;
- oracle feasibility policy;
- failure taxonomy.

## 6. Perturbation families

### Software/control perturbations
- latency
- action noise
- speed cap
- acceleration cap
- calibration offset
- joint range limit
- joint lock
- gripper opening limit
- sensing/camera shift
- controller update-rate reduction

### Physical perturbations
- payload
- tool extension
- gripper pad/friction change
- physical gripper restriction
- object friction surface
- workspace obstacle
- camera physical move
- surface incline if safe

### Compound perturbations
Search combinations:
- latency + action noise
- gripper limit + calibration shift
- wrist limit + payload
- speed cap + pull task
- camera shift + contact task

## 7. Baselines

Required:
1. nominal policy
2. random search / random perturbation tuning
3. domain randomization
4. worst-case grid tuning
5. robust/conservative controller
6. sysID+retune
7. oracle feasibility
8. Pathak-style human/effect-prior policy
9. EPEC-style effect-preserving alternative action policy
10. BodyShield

## 8. Metrics

Primary:
- nominal success
- success under seen perturbations
- success under held-out perturbation families
- success under held-out physical modifications
- minimal breaking perturbation
- robustness profile area under curve
- trials to find failure
- trials to repair
- nominal performance retention

Secondary:
- execution time
- path length
- number of retries
- safety stop count
- servo load/current if available
- tracking error
- verifier accuracy
- reset reliability
- human intervention count

## 9. Statistical standards

- Binomial confidence intervals for success rates.
- Bootstrap confidence intervals for robustness area.
- Report uncertainty for breaking-point estimates.
- Predefine thresholds:
  - 20% relative success drop
  - 30% relative success drop
  - 50% absolute success threshold
- Report threshold sensitivity.
- All trials included unless mechanical fault category triggered.
- Mechanical fault category must be separately reported.

## 10. Paper outline

1. Introduction
2. Related Work
3. Problem Formulation: Hidden Embodiment Assumptions
4. BodyBreak: Embodiment Falsification
5. BodyShield: Falsification-Guided Repair
6. Experimental Setup
7. Simulation Results
8. Real Robot Results
9. EPEC/Human-Effect Stress Test
10. Ablations and Failure Analysis
11. Limitations
12. Conclusion

## 11. Red-line checklist before submission

Do not submit unless:
- BodyShield beats domain randomization under equal or lower budget.
- BodyShield improves held-out perturbation families.
- BodyShield improves held-out physical modifications.
- Oracle feasibility is shown for every main failure claim.
- Hardware noise floor is quantified.
- All baselines are fair and budget-matched.
- Automatic verifier has audited accuracy.
- All logs, videos, configs, plots, and scripts are reproducible.
- The paper does not overclaim cross-embodiment foundation-model generality.
