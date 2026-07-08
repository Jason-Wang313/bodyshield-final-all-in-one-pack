# Reviewer Prebuttal

## Is this just domain randomization?

No in the analytic package: see `reports/gate_1_domain_randomization.md` and `tables/sim_budget_matched_results.csv`. Hardware comparison remains pending.

## Is this just benchmark/stress testing?

No for non-hardware: before/after repair is reported in `reports/gate_2_before_after_repair.md`.

## Is the cheap arm too toy?

Hardware is not claimed. The cheap-arm stack is safety-gated in `bodyshield/robot/` and must be treated as a validation ladder.

## Are perturbations artificial?

Some are software/control shifts; physical-style proxies are logged in `reports/heldout_physical_modifications.md`, while real physical modifications are blocked.

## Are failures impossible tasks?

Analytic oracle feasibility is reported in `reports/oracle_feasibility.md`. Hardware oracle feasibility is pending.

## Is this robust control/sysID?

No; `reports/prior_work_hardening.md` frames BodyShield as a diagnostic repair layer, not a replacement.

## Is it too conservative?

`reports/conservatism_analysis.md` tracks execution time, path length, retries, and nominal retention.

## Are baselines fair?

`reports/baseline_fairness.md` and `reports/BUDGET_AND_FAIRNESS_AUDIT.md` document budgets.

## Does repair overfit?

`reports/heldout_generalization.md` reports held-out perturbation families.

## Is labeling biased?

`reports/verifier_audit.md` is blocked and prevents hardware claims.

## Is EPEC distracting?

EPEC is only a stress-test policy family, not the headline method.

## Why should ICRA care?

The mechanism is failure diagnosis and repair for learned robot policies under body/control shift.

## What does it not prove?

It does not prove hardware transfer, foundation-model generality, or cross-embodiment transfer.

## What would fail on bigger robots?

Unmodeled compliance, force limits, perception latency, calibration drift, reset reliability, and safety limits.

## Why valuable to labs with better hardware?

It gives a falsification-to-repair audit layer that can be run before expensive deployments.
