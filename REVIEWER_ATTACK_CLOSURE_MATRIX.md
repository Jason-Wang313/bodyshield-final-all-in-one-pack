# Reviewer Attack Closure Matrix

| Attack | Why it hurts | Required closure artifact |
|---|---|---|
| Just domain randomization | Novelty collapse | Equal-budget comparison showing BodyShield finds/repairs failures with fewer trials |
| Benchmark not method | Reject as diagnostic only | Before/after BodyShield repair results |
| Cheap hardware artifact | Undermines physical evidence | Hardware noise floor report and repeatability controls |
| Perturbation makes task impossible | Invalid brittleness claim | Oracle feasibility policy succeeds under same perturbation |
| Artificial perturbations not real transfer | Scope problem | Held-out physical modification experiments |
| Metrics arbitrary | Trust problem | Robustness profiles + threshold sensitivity |
| Adversarial search trivial | Weak algorithm | Compound perturbation search with smaller discovered failures |
| Repair overfits | Weak generalization | Held-out perturbation families and physical modifications |
| Baselines weak | Easy reject | Domain randomization, robust control, sysID+retune, oracle, human/effect priors |
| Too conservative | Method wins by slowing down | Report execution time/path length/nominal retention |
| Manual labeling/reset bias | Reproducibility | Verifier audit, reset protocol, all logs |
| No relevance to modern robot learning | Motivation weak | EPEC/human-effect stress test and simulated multi-body breadth |
| Simulation disagrees with robot | Evidence conflict | Treat sim as breadth and robot as truth; analyze disagreement |
| No stats | Fragile evidence | Confidence intervals and bootstrap estimates |
| Too many moving parts | Clarity | Single narrative: falsify hidden body assumption → repair policy |
| AI-generated citation risk | Administrative kill | Verified citation table; no unverified references |
| SysID/robust control already solve this | Prior work attack | Include sysID/robust-control baseline |
| Action noise not embodiment | Semantics | Use embodiment-control perturbation terminology |
| Minimal is not truly minimal | Overclaim | Say estimated minimal; show search budgets/seeds |
| LLM raw hardware control unsafe | Safety/reproducibility | Bounded API, safety shield, stop rules |
