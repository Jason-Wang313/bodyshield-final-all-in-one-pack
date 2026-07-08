# BodyShield Non-Hardware Release Bundle

This archive is a portable local export of the BodyShield non-hardware pack.

Evidence boundary:
- Contains software, configs, generated non-hardware results, reports, synthetic media, and the paper draft.
- Does not contain hardware logs, real camera-verifier videos, external trained-policy checkpoints, real-video WAM data, or real corrective-trace datasets.
- Does not replace an external archival upload or public repository release.

Suggested verification after unpacking:
```powershell
python scripts\verify_release_payload.py
python -m pytest -q
```

Payload summary:
- Payload files: 498
- Payload bytes: 374340132
- Manifest: `RELEASE_BUNDLE_MANIFEST.csv`
