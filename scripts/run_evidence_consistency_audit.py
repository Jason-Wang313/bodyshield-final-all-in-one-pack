"""Run the BodyShield evidence-reference consistency audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.evidence_consistency import evidence_consistency_summary, failed_references, write_evidence_consistency_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Pack root.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args(argv)

    rows = write_evidence_consistency_reports(args.root)
    summary = evidence_consistency_summary(rows)
    failures = failed_references(rows)
    payload = {
        "status": "pass" if summary["missing"] == 0 and summary["rows"] > 0 else "fail",
        "summary": summary,
        "failures": failures.to_dict(orient="records"),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"EVIDENCE_CONSISTENCY_STATUS={payload['status']}")
        print(f"REFERENCES_CHECKED={summary['rows']}")
        print(f"MISSING_REFERENCES={summary['missing']}")
        for failure in payload["failures"][:20]:
            print(f"FAIL: {failure['document']} -> {failure['reference']}: {failure['detail']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
