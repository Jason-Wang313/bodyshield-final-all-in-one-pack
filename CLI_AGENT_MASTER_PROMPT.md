# CLI Agent Master Prompt

You are executing the BodyShield research plan.

Your task is to build the full non-hardware stack first, then stop and notify the user before any hardware experiments.

## Paper target

**BodyShield: Falsifying and Repairing Hidden Embodiment Assumptions in Robot Policies**

Primary claim:
A policy's nominal success is insufficient. We must identify the smallest body/control perturbations that break it, then use those discovered failures to repair the policy/action representation for stronger robustness to seen and held-out embodiment-control changes.

## Absolute rules

1. Do not invent results.
2. Do not invent citations.
3. Do not hide failed experiments.
4. Do not cherry-pick videos.
5. Do not call hardware unless the user explicitly confirms the robot is assembled, calibrated, clear of obstacles, powered correctly, and a physical emergency stop is available.
6. Do not send raw motor commands. Hardware control must go through the bounded safe API.
7. Do not continue into hardware after finishing non-hardware jobs. Stop and notify the user exactly as specified below.

## Non-hardware completion requirement

When all non-hardware tasks are complete, create:

`reports/NON_HARDWARE_COMPLETE.md`

Then print exactly:

```
NON-HARDWARE COMPLETE: BodyShield software, simulation, baselines, perturbation search, repair algorithms, analysis scripts, paper skeleton, verified citation table, and reviewer-defense reports are finished. Hardware phase is next. Do not proceed until the user confirms the SO-ARM101/SO-101 robot setup, safety gate, camera verifier, and emergency stop are ready.
```

## Required non-hardware deliverables

- Python package skeleton for BodyBreak/BodyShield.
- Simulation runner.
- Perturbation library.
- Baselines:
  - nominal policy
  - domain randomization / random perturbation tuning
  - worst-case grid tuning
  - robust/conservative control baseline
  - sysID+retune baseline where applicable
  - Pathak-style human/effect-prior baseline
  - oracle feasibility policy
  - BodyShield
- Adaptive adversarial perturbation search.
- Repair algorithm.
- Data schema and logging.
- Statistical analysis scripts.
- Plotting scripts.
- Simulation experiments with confidence intervals.
- Paper skeleton with placeholders only for real robot results.
- Reviewer attack closure report.
- Citation verification table.

## Hardware phase

Hardware phase may begin only after:
- user confirms robot is physically ready;
- `python -m bodyshield.robot.healthcheck` passes;
- `python -m bodyshield.robot.safety_gate --check-all` passes;
- camera verifier has at least 95% agreement with human labels on a calibration set;
- emergency stop has been tested;
- workspace is clear;
- physical reset fixtures are installed or manual reset protocol is approved.

The CLI agent may then launch autonomous batches only through:

`python -m bodyshield.robot.run_batch --config <config.yaml> --autonomous --require-safety-green`

The agent must pause after each batch and generate:
- success/failure summary;
- safety events;
- verifier disagreement cases;
- suggested next batch;
- hardware health report.
