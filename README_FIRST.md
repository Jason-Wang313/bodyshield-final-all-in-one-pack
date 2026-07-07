# BodyShield Final All-in-One Execution Pack

Date: 2026-07-05

This pack is the final BodyShield plan: **BodyShield main, EPEC/human-effect policies as a stress-test**, not a separate paper.

Primary paper title:
**BodyShield: Falsifying and Repairing Hidden Embodiment Assumptions in Robot Policies**

Core thesis:
Robot policies can succeed on nominal hardware while secretly relying on brittle body/control assumptions.
BodyShield actively finds the smallest body/control perturbations that break a policy, then repairs the policy/action representation to survive seen and held-out embodiment-control changes.

Execution philosophy:
- Main ICRA target: real robot + simulation + repair method.
- The no-hardware/theory tracks are included as backups or companion directions, not replacements for the highest-odds ICRA submission.
- The CLI agent must complete all non-hardware work first, produce `reports/NON_HARDWARE_COMPLETE.md`, and print the exact completion message specified in `NON_HARDWARE_COMPLETION_PROTOCOL.md`.
- Hardware automation is allowed only through the bounded API and safety gate described in `HARDWARE_AUTONOMOUS_CLI_RUNBOOK.md` and `SAFE_ROBOT_API_SPEC.md`.
- The LLM/CLI agent must never issue raw motor commands directly.

Files:
1. `CLI_AGENT_MASTER_PROMPT.md` — give this to the CLI agent.
2. `BODYSHIELD_FINAL_PLAN.md` — full research, experiment, and paper plan.
3. `HARDWARE_AUTONOMOUS_CLI_RUNBOOK.md` — how the CLI agent should run hardware experiments automatically after safety gates.
4. `SAFE_ROBOT_API_SPEC.md` — bounded primitives, safety monitor, stop conditions.
5. `NON_HARDWARE_COMPLETION_PROTOCOL.md` — exact completion notification.
6. `NO_HARDWARE_AND_THEORY_DECISION_MEMO.md` — Guanya-fit vs ICRA-fit ranking for no-hardware paper types.
7. `REVIEWER_ATTACK_CLOSURE_MATRIX.md` — all known reviewer attacks and required closure artifacts.
8. `EXPERIMENT_MATRIX_MAXOUT.csv` — maxed-out simulation + real-robot experiment matrix.
9. `tasks.yaml` — machine-readable task graph for the CLI agent.
10. `data_schema.json` — unified schema for trial logs.
11. `configs/` — example hardware/simulation configs.
12. `skeleton/` — non-hardware code skeletons the CLI agent should flesh out.
13. `SOURCE_NOTES_FOR_VERIFICATION.md` — sources the agent must verify again before final writing.

No plan can guarantee acceptance. This pack is designed to remove obvious reviewer attack surfaces and aim for strong-accept evidence.
