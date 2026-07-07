# Baseline Fairness Protocol

Status: `non_hardware_protocol_active`

The non-hardware evaluation uses matched task, robot, perturbation-family, and
trial grids for analytic baselines. This is an evaluation-budget match, not a
claim that full external neural-policy training compute is matched.

## Shared Conditions

- Same task cards and robot archetypes.
- Same perturbation families and bucket definitions.
- Same success verifier and failure taxonomy.
- Same trial count per analytic condition where feasible.
- Same train/validation/test split definitions for seen and held-out buckets.
- Same evidence boundary language in the claim ledger.

## Baselines

- nominal policy
- random perturbation tuning
- domain randomization
- worst-case grid tuning
- robust/conservative controller
- sysID plus retune
- oracle feasibility policy
- human/effect-prior stress-test policy
- EPEC-style effect alternative policy
- BodyShield diagnosis only
- BodyShield repair variants
- BodyShield full

## Budget Records

- Evaluation budgets: `reports/EVALUATION_BUDGET_TABLE.md`
- Search budgets: `reports/SEARCH_BUDGET_TABLE.md`
- BodyBreak rows: `results/breaking_search.csv`
- Dense minimality challenge: `results/bodybreak_minimality_audit.csv`
- Repair history: `results/repair_history.csv`
- Secondary metrics: `results/secondary_metrics_by_method.csv`

## Hardware Extension

When hardware is enabled, each method must use the same batch protocol, reset
rules, verifier, human-audit sampling policy, physical perturbation levels, and
stop conditions. Mechanical faults must be reported separately from policy
failures.
