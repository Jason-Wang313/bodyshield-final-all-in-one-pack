"""Run the external trained-policy benchmark readiness tier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.external_policy_benchmark import readiness_summary, write_external_policy_benchmark_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default=str(ROOT / "configs" / "external_policy_benchmark.example.json"),
        help="Path to the external policy benchmark spec JSON.",
    )
    parser.add_argument("--steps", type=int, default=6, help="Deterministic interface-smoke steps per runnable row.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = write_external_policy_benchmark_artifacts(
        Path(args.spec),
        ROOT / "results",
        ROOT / "reports",
        root=ROOT,
        steps=args.steps,
    )
    summary = readiness_summary(rows)
    print(
        "EXTERNAL_POLICY_BENCHMARK_READINESS "
        f"rows={summary['rows']} fixture_passed={summary['fixtures_passed']} "
        f"external_specs={summary['external_specs']} external_smokes={summary['external_interface_smokes']} "
        f"missing_checkpoints={summary['missing_checkpoints']} failed_rows={summary['failed_rows']}",
        flush=True,
    )
    return 1 if summary["failed_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
