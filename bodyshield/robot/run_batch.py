"""Autonomous hardware batch entry point.

This command refuses to run until a real bounded robot API and safety gate are
implemented and confirmed.  It never sends raw motor commands.
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--autonomous", action="store_true")
    parser.add_argument("--require-safety-green", action="store_true")
    parser.parse_args()
    print("Refusing hardware batch: non-hardware phase is complete only after user safety confirmation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
