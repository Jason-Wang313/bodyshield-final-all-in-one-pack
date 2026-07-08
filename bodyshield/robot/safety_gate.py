"""Hardware safety gate placeholder."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true")
    parser.add_argument("--config", default=None)
    parser.parse_args(argv)
    print("BodyShield safety gate is not green: hardware phase requires explicit user confirmation and physical checks.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
