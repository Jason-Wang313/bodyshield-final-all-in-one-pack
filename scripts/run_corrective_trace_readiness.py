"""Run the corrective-trace readiness tier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.corrective_trace_readiness import readiness_summary, write_corrective_trace_readiness_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default=str(ROOT / "configs" / "corrective_trace_readiness.example.json"),
        help="Path to the corrective-trace readiness spec JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = write_corrective_trace_readiness_artifacts(
        Path(args.spec),
        ROOT / "results",
        ROOT / "reports",
        root=ROOT,
    )
    summary = readiness_summary(rows)
    print(
        "CORRECTIVE_TRACE_READINESS "
        f"rows={summary['rows']} fixture_smokes={summary['fixture_smokes']} "
        f"trace_dataset_specs={summary['trace_dataset_specs']} trace_dataset_smokes={summary['trace_dataset_smokes']} "
        f"missing_datasets={summary['missing_datasets']} failed_rows={summary['failed_rows']}",
        flush=True,
    )
    return 1 if summary["failed_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
