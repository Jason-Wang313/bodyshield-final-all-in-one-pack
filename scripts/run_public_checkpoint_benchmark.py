"""Run the public pretrained SB3 MuJoCo checkpoint benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.public_checkpoint_benchmark import run_public_checkpoint_benchmark


def main() -> int:
    payload = run_public_checkpoint_benchmark(ROOT)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
