# Final Reviewer Prebuttal

Status: `non_hardware_prebuttal_hardware_pending`

## 1. Why This Is Not Domain Randomization

Domain randomization trains over sampled variation. BodyShield first searches
for perturbations that break the current policy under a costed body/control
space, records the failure axis, then repairs against the discovered
counterexamples. Domain randomization remains a baseline, not the target being
renamed.

## 2. Why This Is Not Just Counterexample-Guided Repair

The counterexamples are not only unsafe states or adversarial trajectories. They
are embodiment-control changes such as latency, calibration offset, gripper
restriction, actuation caps, payload, tool extension, friction, sensing shift,
and compounds. The unit of evidence is a policy failing under a small body/control
change while an oracle/tuned policy still solves the task.

## 3. Why Cheap Hardware Is Scientifically Appropriate

The intended SO-ARM101/SO-101 phase tests whether hidden embodiment-control
assumptions appear in accessible robot manipulation. The scientific target is
the falsification-to-repair mechanism, not high-end robot performance. Hardware
claims remain blocked until safety-gated trials exist.

## 4. Why Perturbations Do Not Merely Make Tasks Impossible

The analytic pack includes oracle feasibility rows for main BodyBreak failures.
If the oracle cannot solve a perturbation, that perturbation must be excluded
from brittleness claims or described as task infeasibility. Hardware oracle
feasibility is still pending.

## 5. Why Artificial Perturbations Might Transfer to Physical Modifications

Software/control perturbations model mechanisms that often arise physically:
latency, calibration, actuation limits, gripper restrictions, payload, sensing
shift, and contact changes. The current pack does not claim physical transfer;
it defines the test that hardware must run.

## 6. Why BodyShield Is Not Just Conservative

The reports include nominal retention, execution time, path length, retries,
failure categories, threshold sensitivity, and secondary metrics. A repair that
only slows down or avoids the task should be visible in those metrics.

## 7. Why Baselines Are Fair

The analytic baselines use matched task, robot, perturbation, and evaluation
grids. The remaining limitation is that these are parameterized local baselines,
not full external neural controllers with matched training compute.

## 8. Why EPEC/Human-Effect Priors Are Included

They are stress-test policy families. They check whether effect-preserving or
human-prior action choices still hide brittle embodiment assumptions. They are
not the paper's main novelty.

## 9. What Limitations Remain

No real hardware trials, hardware noise floor, camera-verifier audit, reset
reliability, external trained-policy rollout benchmark, real-video WAM training,
or real corrective-trace adaptation is completed in the current public pack.

## 10. What Claims Are Intentionally Not Made

The paper should not claim global minimality, cross-embodiment foundation-model
generality, hardware success, real-video learning, certified safety, or
non-rejectability.
