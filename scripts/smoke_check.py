"""Fast smoke checks for the BodyShield repository."""

from __future__ import annotations

import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    for path in sorted([*ROOT.glob("bodyshield/**/*.py"), *ROOT.glob("scripts/*.py"), *ROOT.glob("tests/*.py")]):
        if "__pycache__" in path.parts:
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc.msg}")
    required = [
        ROOT / "README.md",
        ROOT / "Makefile",
        ROOT / "pyproject.toml",
        ROOT / "reports" / "PACK_VERIFICATION.md",
        ROOT / "reports" / "CLAIM_LEDGER.md",
        ROOT / "paper" / "main.tex",
        ROOT / "paper" / "bodyshield_non_hardware_draft.pdf",
        ROOT / "release" / "bodyshield_non_hardware_release.zip",
    ]
    for path in required:
        if not path.exists() or path.stat().st_size == 0:
            failures.append(f"missing or empty required artifact: {path.relative_to(ROOT)}")
    if failures:
        print("SMOKE_STATUS=fail")
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("SMOKE_STATUS=pass")
    print("PYTHON_FILES_COMPILED=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
