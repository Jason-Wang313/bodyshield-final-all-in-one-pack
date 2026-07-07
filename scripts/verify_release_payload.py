"""Verify an unpacked BodyShield non-hardware release payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.release_bundle import validate_release_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Extracted release root.")
    parser.add_argument(
        "--required-payload",
        action="append",
        default=None,
        help="Required payload path. May be repeated; defaults to the full BodyShield required payload set.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of compact text.")
    args = parser.parse_args(argv)

    payload = validate_release_payload(args.root, required_payloads=args.required_payload or None)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"RELEASE_PAYLOAD_STATUS={payload['status']}")
        print(f"PAYLOAD_FILES={payload.get('payload_files', 0)}")
        print(f"PAYLOAD_BYTES={payload.get('payload_bytes', 0)}")
        if payload.get("problems"):
            for problem in payload["problems"]:
                print(f"FAIL: {problem}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
