# Method Theory Strengthening

Status: `bounded_formalization`

## Perturbation Space

Let a task be tau, a robot/body interface be r, and a policy be pi_theta. BodyShield models an embodiment-control perturbation as z in Z, where Z is the product of bounded axes such as latency, action noise, joint-range scale, gripper authority, speed/acceleration caps, calibration offset, controller-rate change, camera shift, payload, tool extension, surface friction, and obstacle clearance.

Each z has a normalized cost c(z) in [0, 1]. The current package evaluates a finite candidate subset Z_B under a fixed evaluator budget B.

## Estimated Minimal Break

BodyBreak estimates

    z_hat = argmin_{z in Z_B} c(z) subject to S(pi_theta, tau, r, z) <= alpha

where S is a success-rate or success-probability evaluator and alpha is the break threshold. Because Z_B is finite and the evaluator is noisy or approximate, z_hat is an estimated minimal break under the candidate set and budget, not a global certificate over Z.

## Robustness Radius and Profile

The robustness radius rho(pi_theta, tau, r) is reported as the smallest evaluated cost with failure under the threshold. A robustness profile R(epsilon) reports the empirical success rate for all evaluated perturbations with c(z) <= epsilon. Profiles are more reviewer-resistant than a single radius because they show whether repair improves only one point or an interval of perturbation severity.

## Repair Objective

BodyShield repairs by minimizing a weighted loss over nominal cases, discovered break cases, near-boundary cases, and held-out validation cases:

    min_theta L_nominal(theta) + lambda_b L_break(theta; B_break) + lambda_h L_heldout(theta; B_holdout) + lambda_s C_secondary(theta)

The intended mechanism is not random broadening. It is diagnosis-driven allocation of repair capacity to axes that were shown to break the controller.

## Budget Accounting

All fair comparisons must count evaluator calls, rollout count, seeds, policy updates, search candidates, and baseline tuning attempts. Domain randomization and dynamics randomization are dangerous baselines because they are established sim-to-real methods; BodyShield should be claimed only when it wins under equal or lower budget in the stated scope.

## Why Not Global Optimization

Global optimization is not claimed because the perturbation space contains mixed continuous, discrete, and semantic physical modifications; hardware evaluation is expensive; and verifier labels can be noisy. The package therefore reports finite-budget falsification and repair, plus dense post-hoc audits where available.

## Sample-Efficiency Assumptions

BodyShield can be sample efficient only when hidden failure axes are low-dimensional enough to identify, repair capacity is sufficient, perturbation labels are reliable, and held-out perturbations share mechanism-level structure with discovered breaks. It can fail when failures are high-dimensional, discontinuous, outside the repair parameterization, or dominated by unmodeled perception/contact effects.

## Proposition (Finite Candidate Soundness)

For a fixed candidate set Z_B, deterministic evaluator S, threshold alpha, and exact costs c, if BodyBreak returns the evaluated candidate z_hat with minimal c among all candidates with S(pi_theta, tau, r, z) <= alpha, then no candidate in Z_B with lower cost was observed to break the policy. This proposition does not imply global minimality over Z, hardware transfer, or robustness to unevaluated perturbations.

## Limits

The current evidence is analytic/synthetic plus bounded simulator probes. Hardware validation, external trained-policy checkpoints, real-video WAM, real corrective traces, and independent archive replication are outside the completed evidence set.
