"""Run config and schema integrity checks for the BodyShield non-hardware pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.config_schema_audit import config_schema_summary, failed_config_schema_rows, write_config_schema_audit_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root to audit.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args(argv)

    rows = write_config_schema_audit_reports(args.root)
    summary = config_schema_summary(rows)
    failures = failed_config_schema_rows(rows)
    status = "pass" if summary["checks"] > 0 and failures.empty else "fail"
    payload = {
        "status": status,
        "summary": summary,
        "failures": failures.head(20).to_dict(orient="records"),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"CONFIG_SCHEMA_STATUS={status}")
        print(f"CHECKS={summary['checks']}")
        print(f"FAILED={summary['failed']}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
