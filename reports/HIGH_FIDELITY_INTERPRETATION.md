# High-Fidelity Interpretation

This evidence tier is bounded simulator evidence, not a full robot-policy result.

## MuJoCo
- Scope: 8 task-shaped 1-DOF probes, 7 perturbation families, 7 policy families, 4 seeds per condition.
- BodyShield mean success: 0.500
- Domain-randomization mean success: 0.482
- Oracle mean success: 0.625
- Interpretation: the probes check whether perturbation/control logic produces stable MuJoCo dynamics and nontrivial robustness structure. They do not model full robot kinematics, perception, contact geometry, or reset.

## MuJoCo Planar Effector
- Scope: 4 two-axis closed-loop planar end-effector tasks, 7 perturbation families, 7 policy families, 4 seeds per condition.
- BodyShield mean success: 0.241
- Domain-randomization mean success: 0.170
- Interpretation: this is a stronger local dynamics probe than the 1-DOF suite because it exercises two-axis delayed/noisy control. It remains a bounded benchmark, not a full robot-policy result.

## ManiSkill
- Scope: 6/6 selected tabletop tasks executed with CPU `pd_joint_delta_pos` random actions.
- Interpretation: this verifies local ManiSkill task availability and control-mode compatibility. It is not a trained policy baseline.

## Learned MuJoCo Gated Residual Policy
- Scope: supervised residual controller trained on nominal/seen MuJoCo planar corrective labels and evaluated with conservative gating on held-out planar perturbations.
- Gate: residuals are disabled for nominal perturbations and suppressed when instantaneous error is within 2.0x the task tolerance.
- Held-out base final error: 0.1838
- Held-out adapted final error: 0.1676
- Held-out final-error reduction: 0.0162
- Gate ablation: selected gated reduction 0.0162 versus residual-off reduction 0.0000; always-on nominal success delta -0.333; gated nominal success delta +0.000.
- Interpretation: this is a local trained high-fidelity gated residual-policy audit, not an external robot-policy checkpoint or real robot result.

## Safe claim
The local stack now has executable analytic, learned scalar outcome-model, synthetic visual-model, NumPy neural visual-latent WAM, real-video WAM readiness, synthetic trajectory-model, synthetic corrective-adaptation, MuJoCo 1-DOF, MuJoCo planar-effector, learned MuJoCo gated residual-policy, ManiSkill, and external-checkpoint readiness tiers. Only the analytic tier is currently used for the main BodyShield-vs-baseline claim; high-fidelity rows remain local simulator evidence until external trained checkpoints or hardware logs are integrated.
