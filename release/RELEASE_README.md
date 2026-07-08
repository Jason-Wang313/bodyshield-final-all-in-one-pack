# BodyShield Non-Hardware Release Bundle

This archive is a portable local export of the BodyShield non-hardware pack.

Evidence boundary:
- Contains software, configs, generated non-hardware results, reports, synthetic media, and the paper draft.
- Contains one public pretrained MuJoCo checkpoint benchmark and its copied SB3/RL-Zoo checkpoint artifacts.
- Does not contain hardware logs, real camera-verifier videos, broad manipulation/foundation-policy checkpoint suites, real-video WAM data, or real corrective-trace datasets.
- Does not replace an external archival upload or public repository release.

Suggested verification after unpacking:
```powershell
python scripts\verify_release_payload.py
python -m pytest -q
```

Payload summary:
- Payload files: 501
- Payload bytes: 374863886
- Manifest: `RELEASE_BUNDLE_MANIFEST.csv`
