# Figure Captions

## `results/figures/bodyshield_mechanism.pdf`
Conceptual pipeline: nominal policy evaluation, BodyBreak failure search, failure-axis attribution, and BodyShield repair. This is a schematic, not empirical evidence.

## `results/figures/breaking_search_comparison.pdf`
Search comparison across random, one-axis, grid, and BodyBreak modes. Panel 1 reports found-break-only estimated costs, Panel 2 reports break-found rate, and Panel 3 reports evaluator calls used under the fixed search budget.

## `results/figures/bodybreak_minimality_audit.pdf`
Dense BodyBreak minimality challenge. Compares representative BodyBreak found-break costs against a larger deterministic local candidate pool with independent sampled confirmation and reports cost regret. This is an audit of estimated minimality, not a mathematical proof of global optimality.

## `results/figures/repair_seen_heldout.pdf`
Success rate by method and perturbation bucket. Wilson confidence intervals are reported in `reports/SIMULATION_BUCKET_SUMMARY_TABLE.md`.

## `results/figures/nominal_vs_radius.pdf`
Nominal success versus estimated robustness radius on the SO101-style push-block analytic probe. This supports the limited claim that nominal success and robustness radius can decouple in the analytic simulator.

## `results/figures/high_fidelity_summary.pdf`
Bounded MuJoCo and ManiSkill simulator checks. The first MuJoCo panel averages success over task-shaped 1-DOF probes, the second MuJoCo panel reports 2-DOF planar-effector probes, and the ManiSkill panel reports random-action reward over installed CPU tabletop tasks. This figure verifies simulator execution and bounded dynamics behavior; the separate residual-policy figure covers local MuJoCo gated residual learning. Neither is external/full-scale trained-policy evidence.

## `results/figures/trajectory_wam_summary.pdf`
Synthetic trajectory WAM proxy audit. The first panel compares true and predicted final rollout error; the second reports autoregressive final-XY drift by perturbation bucket. This verifies a local action-conditioned trajectory-modeling path, not visual prediction or real corrective-trace adaptation.

## `results/figures/visual_wam_summary.pdf`
Synthetic visual WAM proxy audit. The first panel reports final rendered-object centroid drift by perturbation bucket; the second reports one-step rendered-frame PSNR by split. This verifies a generated-frame prediction path, not real camera video or neural foundation-WAM training.

## `results/figures/neural_wam_summary.pdf`
Neural visual-latent WAM proxy audit. The first panel shows NumPy MLP train/held-out latent prediction error over epochs; the second reports autoregressive final-centroid drift by perturbation bucket. This verifies a local nonlinear visual-latent dynamics path, not real-video foundation-model training or physical transfer.

## `results/figures/mujoco_residual_policy_summary.pdf`
Learned MuJoCo gated residual-policy audit. The first panel compares base and adapted planar final error by bucket; the second reports held-out final-error reduction by source policy. This verifies a local simulator residual-action learning path with nominal and near-success residual suppression, not an external robot-policy checkpoint, full ManiSkill benchmark, or hardware transfer.

## `results/figures/mujoco_residual_gate_ablation.pdf`
MuJoCo residual gate ablation. Compares residual-off, always-on, non-nominal-only, and selected gated residual variants; the left panel reports held-out final-error reduction, and the right panel reports nominal success delta. This justifies the conservative gate as local simulator evidence, not external-policy transfer.

## `results/figures/corrective_adaptation_summary.pdf`
Synthetic corrective-trace adaptation audit. The first panel compares base and adapted final error by bucket; the second reports held-out final-error reduction by source policy. This verifies a local residual-action adaptation path over generated traces, not real online learning or neural policy finetuning.

## `results/videos/bodyshield_synthetic_*.gif`
Synthetic rollout media for visual inspection of a nominal reference, the nominal policy under a BodyBreak perturbation, and BodyShield under the same perturbation. These GIFs use generated visual frames from the analytic trajectory proxy; they are not real camera video, verifier clips, or hardware evidence.
