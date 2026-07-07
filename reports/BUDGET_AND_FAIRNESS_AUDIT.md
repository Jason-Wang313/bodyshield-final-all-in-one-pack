# Budget And Fairness Audit

## Main Analytic Evaluation

- Every method is evaluated on the same task, robot, perturbation-family, and trial grid.
- Each condition uses 50 simulator trials.
- Bucket-level sample parity is reported in `reports/EVALUATION_BUDGET_TABLE.md`.
- This is an evaluation-budget match. It is not evidence that external neural-policy training compute is matched.

## BodyBreak Search

- `compare_search_modes` configures the same 200-evaluator-call cap for random, one-axis, grid, and BodyBreak modes.
- Some modes use fewer calls when their finite candidate set is exhausted or when BodyBreak stops after finding and refining a breaking perturbation.
- Search budget accounting is reported in `reports/SEARCH_BUDGET_TABLE.md` and `results/breaking_search.csv`.
- Dense post-hoc minimality challenge rows are reported in `results/bodybreak_minimality_audit.csv`; this uses a larger deterministic local candidate pool and does not claim global optimality.

## Repair And Feasibility

- BodyShield repair samples 160 candidate repairs in this CPU analytic implementation.
- Each repair candidate is scored on discovered breaking perturbations through the same evaluator path used by the analytic simulator.
- Threshold sensitivity contains 360 search rows with 150-call caps and the same deterministic analytic success-probability evaluator used by BodyBreak search.
- Oracle feasibility contains 60 BodyBreak failure rows, each evaluated with 60 simulator trials.

## Remaining Budget Limits

- Domain randomization, robust control, SysID+retune, EPEC, and human/effect-prior policies are analytic parameterized baselines, not externally trained controllers.
- Full trained-policy compute matching is non-hardware future work if this becomes a simulation-only submission.
- Hardware budgets, reset costs, verifier audits, and physical intervention counts remain hardware-only.
