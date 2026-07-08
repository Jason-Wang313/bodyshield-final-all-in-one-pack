"""Verify citation audit and bibliography syntax are present."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    bib = ROOT / "paper" / "references.bib"
    audit = ROOT / "reports" / "CITATION_VERIFICATION_TABLE.md"
    v2_audit = ROOT / "reports" / "citation_verification.md"
    failures: list[str] = []
    bib_text = bib.read_text(encoding="utf-8", errors="ignore") if bib.exists() else ""
    required_keys = {
        "tobin2017domainrandomization",
        "peng2018dynamicsrandomization",
        "openai2018dexterous",
        "gupta2025umionair",
        "wang2026embodisteer",
        "le2025verificationguided",
        "zeng2021mpccbf",
        "jiang2024transic",
    }
    if not bib.exists() or not re.search(r"@\w+\{", bib_text):
        failures.append("paper/references.bib has no BibTeX entries")
    missing = [key for key in sorted(required_keys) if key not in bib_text]
    if missing:
        failures.append(f"paper/references.bib missing required v2 keys: {missing}")
    if not audit.exists() or "Verified" not in audit.read_text(encoding="utf-8", errors="ignore"):
        failures.append("reports/CITATION_VERIFICATION_TABLE.md missing verified rows")
    if not v2_audit.exists() or "Verified" not in v2_audit.read_text(encoding="utf-8", errors="ignore"):
        failures.append("reports/citation_verification.md missing verified rows")
    status = "pass" if not failures else "fail"
    print(f"CITATION_VERIFY_STATUS={status}")
    for failure in failures:
        print(f"FAIL={failure}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
