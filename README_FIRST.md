# BodyShield Execution Note

The current repository state is non-hardware complete under analytic/synthetic scope. For the v3 post-nonhardware audit, start with:

```bash
python scripts/finalize_v3_artifacts.py
python -m bodyshield.analysis.verify_package --json
```

Hardware remains blocked until the user confirms the SO-ARM101/SO-101 setup, safety gate, camera verifier, reset protocol, and emergency stop are ready. See `reports/SUBMISSION_READY_AUDIT.md` before using any paper wording.
