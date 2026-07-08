# BodyShield Claim Boundary

This non-hardware execution supports a software and analytic-simulation claim only.

Supported now:
- BodyBreak estimates minimal breaking perturbations in a CPU analytic simulator and includes a dense post-hoc minimality challenge for representative found breaks.
- BodyShield repair uses discovered failure axes to improve worst-case simulated success.
- Baseline comparisons, confidence intervals, plots, synthetic rollout GIFs, logs, and a paper draft with generated result tables are reproducible from this folder.

Not supported yet:
- No real SO-ARM101/SO-101 hardware result has been run.
- One public SB3/RL-Zoo HalfCheetah checkpoint benchmark has been run, but no broad external/full-scale robot-policy MuJoCo/ManiSkill benchmark suite has been run; bounded simulator probes, a local MuJoCo gated residual-policy audit, and an external-checkpoint readiness harness are logged.
- No real-camera or foundation-scale WAM training has been run; generated visual WAM audits and a real-video frame-manifest readiness harness are logged.
- No real/external corrective-trace adaptation has been run; synthetic corrective adaptation and a corrective-trace manifest readiness harness are logged.
- Camera verifier, reset reliability, noise floor, and safety-stop statistics are placeholders until hardware gates pass.

Agenda fit:
This remains a strong Jason-agenda project because the central mechanism is failure diagnosis, action-representation repair, and transfer under embodiment-control shift rather than hardware design.
