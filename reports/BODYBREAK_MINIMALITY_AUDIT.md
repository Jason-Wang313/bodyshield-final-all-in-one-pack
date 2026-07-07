# BodyBreak Dense Minimality Audit

This audit challenges representative BodyBreak found-break cases with a larger deterministic analytic search pool. It is a post-hoc stress test of estimated minimality, not a mathematical global proof.

## Audit protocol
- Cases: 12 lowest-cost BodyBreak found-break cases, capped per search policy family.
- Candidate pool per case: compact search grid, the BodyBreak perturbation, interpolated lower-cost variants of the BodyBreak perturbation and its active axes, plus deterministic random candidates.
- Mean candidates per case: 448.9
- Evaluator: same deterministic analytic success probability used by the original search, followed by independent 320-trial confirmation before a dense candidate counts as a break.
- Threshold: success rate <= 0.50.

## Result
- Lower-cost independently confirmed dense breaks found: 1/12
- BodyBreak found breaks above threshold under independent confirmation: 6/12
- Mean positive confirmed BodyBreak cost regret: 0.0305
- Max positive confirmed BodyBreak cost regret: 0.0305
- Table: `reports/BODYBREAK_MINIMALITY_AUDIT_TABLE.md`
- Raw CSV: `results/bodybreak_minimality_audit.csv`

## Safe claim
BodyBreak remains an estimated lowest-cost search procedure under a fixed evaluator budget. The dense audit makes the minimality boundary auditable by reporting whether a stronger local candidate pool finds lower-cost analytic breaks for representative cases.
