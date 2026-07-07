"""Verify citation audit and bibliography syntax are present."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    bib = ROOT / "paper" / "references.bib"
    audit = ROOT / "reports" / "CITATION_VERIFICATION_TABLE.md"
    failures: list[str] = []
    if not bib.exists() or not re.search(r"@\w+\{", bib.read_text(encoding="utf-8", errors="ignore")):
        failures.append("paper/references.bib has no BibTeX entries")
    if not audit.exists() or "Verified" not in audit.read_text(encoding="utf-8", errors="ignore"):
        failures.append("reports/CITATION_VERIFICATION_TABLE.md missing verified rows")
    status = "pass" if not failures else "fail"
    print(f"CITATION_VERIFY_STATUS={status}")
    for failure in failures:
        print(f"FAIL={failure}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
