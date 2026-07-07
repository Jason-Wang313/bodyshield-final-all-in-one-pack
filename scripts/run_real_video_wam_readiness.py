"""Run the real-video WAM readiness tier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.real_video_wam_readiness import readiness_summary, write_real_video_wam_readiness_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        default=str(ROOT / "configs" / "real_video_wam_readiness.example.json"),
        help="Path to the real-video WAM readiness spec JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = write_real_video_wam_readiness_artifacts(
        Path(args.spec),
        ROOT / "results",
        ROOT / "reports",
        root=ROOT,
    )
    summary = readiness_summary(rows)
    print(
        "REAL_VIDEO_WAM_READINESS "
        f"rows={summary['rows']} fixture_smokes={summary['fixture_smokes']} "
        f"real_dataset_specs={summary['real_dataset_specs']} real_dataset_smokes={summary['real_dataset_smokes']} "
        f"missing_datasets={summary['missing_datasets']} failed_rows={summary['failed_rows']}",
        flush=True,
    )
    return 1 if summary["failed_rows"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
