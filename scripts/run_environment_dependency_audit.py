"""Run the BodyShield environment and dependency audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.environment_audit import environment_audit_summary, failed_environment_rows, write_environment_dependency_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Pack root.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args(argv)

    rows = write_environment_dependency_reports(args.root)
    summary = environment_audit_summary(rows)
    failures = failed_environment_rows(rows)
    payload = {
        "status": "pass" if summary["required_failures"] == 0 and summary["rows"] > 0 else "fail",
        "summary": summary,
        "failures": failures.to_dict(orient="records"),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ENVIRONMENT_DEPENDENCY_STATUS={payload['status']}")
        print(f"ROWS_CHECKED={summary['rows']}")
        print(f"REQUIRED_FAILURES={summary['required_failures']}")
        for failure in payload["failures"][:20]:
            print(f"FAIL: {failure['kind']} {failure['name']}: {failure['reason']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
