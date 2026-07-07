"""Verify generated BodyShield non-hardware pack artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.pack_verification import verification_payload, write_verification_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root to verify.")
    parser.add_argument("--write-reports", action="store_true", help="Write reports/PACK_VERIFICATION.{json,md}.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a compact text summary.")
    args = parser.parse_args(argv)

    payload = write_verification_reports(args.root) if args.write_reports else verification_payload(args.root)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"PACK_VERIFICATION_STATUS={payload['status']}")
        print(f"CODE_VERSION={payload['code_version']}")
        for check in payload["checks"]:
            print(f"{check['status'].upper()}: {check['name']} - {check['detail']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
