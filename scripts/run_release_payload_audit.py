"""Run the BodyShield release-payload extraction audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.release_payload_audit import (
    failed_release_payload_rows,
    release_payload_audit_summary,
    write_release_payload_audit_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Full pack root or extracted release root.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary instead of compact text.")
    args = parser.parse_args(argv)

    rows = write_release_payload_audit_reports(args.root)
    summary = release_payload_audit_summary(rows)
    failures = failed_release_payload_rows(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    payload = {
        "status": status,
        "summary": summary,
        "failures": failures.to_dict(orient="records"),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"RELEASE_PAYLOAD_AUDIT_STATUS={status}")
        for key, value in summary.items():
            print(f"{key.upper()}={value}")
        for row in payload["failures"]:
            print(f"FAIL: {row}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
