"""Emergency-stop monitor placeholder."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--armed", action="store_true")
    parser.parse_args(argv)
    print("BodyShield emergency-stop monitor is not armed in the non-hardware phase.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
