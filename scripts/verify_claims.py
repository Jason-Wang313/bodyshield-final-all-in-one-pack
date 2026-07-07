"""Verify that required claim-ledger artifacts exist and contain bounded claims."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    paths = [ROOT / "reports" / "CLAIM_LEDGER.md", ROOT / "reports" / "claim_ledger.csv"]
    missing = [path.relative_to(ROOT).as_posix() for path in paths if not path.exists() or path.stat().st_size == 0]
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in paths if path.exists())
    banned = ["non-rejectable", "guarantees deployment", "solves cross-embodiment transfer"]
    hits = [phrase for phrase in banned if phrase in text.lower()]
    status = "pass" if not missing and not hits else "fail"
    print(f"CLAIM_VERIFY_STATUS={status}")
    if missing:
        print(f"MISSING={missing}")
    if hits:
        print(f"BANNED={hits}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
