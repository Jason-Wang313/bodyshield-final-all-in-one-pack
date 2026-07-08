# BodyShield

BodyShield is a falsification-to-repair package for hidden embodiment-control
assumptions in robot policies. The current public artifact is the non-hardware
execution pack for:

**BodyShield: Falsifying and Repairing Hidden Embodiment Assumptions in Robot Policies**

The repository contains analytic-simulation experiments, bounded simulator
probes, repair/search code, generated figures and tables, a paper draft, audit
reports, and a compressed release bundle. It does not contain completed real
SO-ARM101/SO-101 hardware trials.

## Quick Commands

```bash
make smoke
make test
make sim-minimal
make sim-full
make verify
make reproduce-minimal
make reproduce-main-figures
make paper
make package-artifacts
```

On Windows systems without GNU Make, run the underlying commands directly:

```powershell
python scripts/smoke_check.py
python -m pytest -q
python scripts/finalize_v2_artifacts.py
python -m bodyshield.analysis.verify_package --json
python scripts/finalize_maxout_artifacts.py
python scripts/run_derived_results_audit.py --json
python scripts/run_results_integrity_audit.py --json
python scripts/run_visual_artifact_audit.py --json
python scripts/build_bodyshield_icra_paper.py
python scripts/run_paper_source_audit.py --json
python scripts/build_release_bundle.py --json
python scripts/verify_non_hardware_pack.py --write-reports --json
```

## Main Artifacts

- Paper draft: `paper/bodyshield_non_hardware_draft.pdf`
- ICRA-style source draft: `paper/bodyshield_icra.tex`
- Reproducibility package: `release/bodyshield_non_hardware_release.zip`
- Pack verifier: `reports/PACK_VERIFICATION.md`
- Claim ledger: `reports/claim_ledger.csv`
- Citation verification: `reports/citation_verification.md`
- V2 package verifier: `python -m bodyshield.analysis.verify_package --json`
- Final manifest: `reports/final_artifact_manifest.json`
- Reviewer prebuttal: `reports/final_reviewer_prebuttal.md`
- Submission readiness: `reports/final_submission_readiness_report.md`

## Evidence Boundary

Supported now:

- BodyBreak estimates low-cost breaking perturbations in the analytic simulator.
- BodyShield repairs against discovered failures and improves simulated seen and
  held-out perturbation robustness while tracking nominal retention.
- Oracle feasibility, secondary metrics, threshold sensitivity, command-surface,
  source/import, paper-source, visual-artifact, release, and manifest audits are
  generated locally.
- One public SB3/RL-Zoo HalfCheetah checkpoint benchmark is complete with a
  scoped actuator-loss repair and an explicit baseline-fairness caveat.

Not supported yet:

- No real SO-ARM101/SO-101 hardware trials have been run.
- No hardware noise floor, verifier agreement, reset reliability, or emergency
  stop statistics are available.
- Broad manipulation/foundation-policy checkpoint suites, real-camera WAM
  training, and real corrective-trace adaptation remain readiness harnesses
  rather than evidence.

Hardware execution must not begin until the user explicitly confirms the robot,
camera, workspace, physical emergency stop, power, reset protocol, and bounded
safe API are ready.
