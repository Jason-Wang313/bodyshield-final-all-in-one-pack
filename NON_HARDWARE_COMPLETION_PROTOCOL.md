# Non-Hardware Completion Protocol

The CLI agent must stop after completing all non-hardware jobs.

## File to create

`reports/NON_HARDWARE_COMPLETE.md`

This file must include:
- commit hash / code version
- list of completed software modules
- list of completed simulation experiments
- baselines completed
- tables and plots generated
- citation verification status
- remaining hardware-only tasks
- known risks before hardware execution

## Exact terminal message

After creating the report, print exactly:

```
NON-HARDWARE COMPLETE: BodyShield software, simulation, baselines, perturbation search, repair algorithms, analysis scripts, paper skeleton, verified citation table, and reviewer-defense reports are finished. Hardware phase is next. Do not proceed until the user confirms the SO-ARM101/SO-101 robot setup, safety gate, camera verifier, and emergency stop are ready.
```

Do not proceed to hardware until explicit user confirmation is received.
