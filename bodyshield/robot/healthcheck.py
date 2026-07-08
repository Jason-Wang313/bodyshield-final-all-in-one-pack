"""Hardware healthcheck placeholder."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None)
    parser.parse_args(argv)
    print("BodyShield hardware healthcheck is not enabled: user safety confirmation is required first.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
