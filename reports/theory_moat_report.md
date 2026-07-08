# Theory Moat Report

Status: `bounded_proof_sketches_only`

These statements support the experiments. They are not claims of general robust
control, certified global optimality, or physical transfer.

## Proposition 1: Nominal Success Does Not Imply Embodiment Robustness

Consider a one-dimensional push task with target interval `[1, 1.1]`. Policy A
always commands displacement `1.05`. Policy B commands displacement
`1.05 + k z`, where `z` is an unmodeled calibration offset and `k > 0`. At
nominal `z = 0`, both policies succeed. Under small nonzero calibration offset,
Policy B can leave the target interval before Policy A does. Equal nominal
success therefore does not imply equal minimal breaking perturbation.

Experimental anchor: `results/nominal_vs_robustness_radius.csv`.

## Proposition 2: Adaptive Falsification Can Be More Sample-Efficient

Assume a perturbation family has a monotone or locally smooth success boundary
and an evaluator with bounded Bernoulli noise. A one-axis or active-axis search
can bracket a threshold crossing with logarithmic samples in the axis
resolution, while uniform random search spends samples throughout the full
volume. The benefit disappears when the failure set is disconnected, highly
nonmonotone, or larger than the random sampler's support.

Experimental anchor: `results/breaking_search.csv` and
`reports/SEARCH_COMPARISON_TABLE.md`. The current evidence is empirical under a
fixed evaluator budget, not a theorem for arbitrary perturbation spaces.

## Proposition 3: Finite-Set Repair Improves Empirical Worst-Case Success When a Better Candidate Exists

Let `Z_d` be the finite discovered perturbation set and let the repair routine
select the candidate policy with maximum empirical score over `Z_d` plus a
nominal-retention penalty. If the candidate set contains a policy with strictly
higher penalized worst-case score than the previous policy and the evaluator is
the same for all candidates, the selected candidate has empirical score at least
as high as the previous policy on that finite objective. This statement is
finite-sample and objective-relative.

Experimental anchor: `results/repair_history.csv`,
`results/summary_by_method_bucket.csv`, and
`results/method_deltas_vs_bodyshield.csv`.

## Proposition 4: Feasibility Caveat

A perturbation only supports a brittleness claim if the task remains feasible
under the same perturbation. If every policy, including an oracle or retuned
expert, fails under `z`, then `z` may have made the task impossible rather than
revealing a hidden policy assumption. BodyShield therefore reports oracle
feasibility for main analytic breaking perturbations and treats hardware oracle
feasibility as pending.

Experimental anchor: `results/oracle_feasibility.csv`.

## Paper Wording Rule

Use "estimated lowest-cost breaking perturbation under budget" unless a global
optimizer and proof are added. Use "analytic-simulation evidence" unless the
specific claim is backed by hardware, the public checkpoint benchmark, or a broader trained-policy suite.
