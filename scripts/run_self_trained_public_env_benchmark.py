"""Run the self-trained public Gymnasium environment benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.self_trained_public_env import write_self_trained_public_env_artifacts


def main() -> int:
    payload = write_self_trained_public_env_artifacts(ROOT)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
