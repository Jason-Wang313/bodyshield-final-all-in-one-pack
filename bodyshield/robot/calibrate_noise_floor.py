"""Hardware noise-floor calibration placeholder."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.add_argument("--trials", type=int, default=50)
    parser.parse_args(argv)
    print("BodyShield noise-floor calibration requires explicit hardware readiness confirmation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
