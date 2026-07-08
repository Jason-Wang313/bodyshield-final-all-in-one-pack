# Repository Gap Audit

Generated: `2026-07-08T01:02:34.320741+00:00`

## Files Present

- `README.md`
- `pyproject.toml`
- `environment.yml`
- `Makefile`
- `LICENSE`
- `CITATION.cff`
- `.github/workflows/smoke.yml`
- `paper/main.tex`
- `paper/supplement.tex`
- `reports/claim_ledger.csv`
- `reports/final_artifact_manifest.json`

## Files Missing

- none among required non-hardware/publication-hardening files

## Code Not Yet Implemented

- Real hardware bounded API implementation beyond refusal stubs.
- Camera verifier backed by real frames and human labels.
- Hardware reset checker, noise-floor calibration, current/load telemetry, and emergency-stop monitor integration.

## Experiments Not Yet Run

- Real SO-ARM101/SO-101 hardware trials.
- Hardware noise-floor and verifier-audit trials.
- Held-out physical-modification trials.
- External trained-policy checkpoint rollout benchmark.
- Real-video WAM and real corrective-trace adaptation.

## Hardware Readiness Status

`blocked`: no explicit user confirmation of assembled robot, camera, clear workspace, physical emergency stop, safe API installation, or safety gate.

## Publication-Readiness Risks

- Final ICRA hardware claims remain unsupported until hardware gates pass.
- Current evidence is analytic/bounded-probe non-hardware evidence.
- Cross-embodiment/foundation-policy generality must not be claimed.

## Exact Next Steps

1. Keep the current non-hardware claim boundary.
2. Obtain explicit hardware readiness confirmation.
3. Run H0 safety checks through `bodyshield.robot.*` only.
4. Run supervised H1/H2 batches and generate noise-floor, verifier, reset, oracle-feasibility, and physical-modification reports.
