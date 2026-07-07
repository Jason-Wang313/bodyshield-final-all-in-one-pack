"""Verify reproducibility reports and release bundle entry points."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    required = [
        "reports/REPRODUCIBILITY_MANIFEST.md",
        "reports/final_artifact_manifest.json",
        "release/bodyshield_non_hardware_release.zip",
        "scripts/verify_non_hardware_pack.py",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    status = "pass" if not missing else "fail"
    print(f"REPRODUCIBILITY_VERIFY_STATUS={status}")
    if missing:
        print(f"MISSING={missing}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
