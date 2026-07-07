"""Build and inspect the BodyShield portable non-hardware release bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bodyshield.release_bundle import inspect_release_bundle, write_release_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Pack root.")
    parser.add_argument("--json", action="store_true", help="Print JSON inspection output.")
    args = parser.parse_args(argv)

    result = write_release_bundle(args.root)
    inspection = inspect_release_bundle(args.root)
    if args.json:
        print(json.dumps({"created": result.__dict__, "inspection": inspection}, indent=2, sort_keys=True))
    else:
        print(f"RELEASE_BUNDLE_STATUS={inspection['status']}")
        print(f"ZIP={result.zip_path}")
        print(f"ZIP_SHA256={result.zip_sha256}")
        print(f"PAYLOAD_FILES={result.payload_files}")
    return 0 if inspection["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
