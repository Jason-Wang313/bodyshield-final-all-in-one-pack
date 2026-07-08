"""Build/copy canonical paper target PDFs requested by reviewer workflows."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
REPORTS = ROOT / "reports"


def _redact(text: str) -> str:
    redacted = text.replace(str(ROOT), "<PACK_ROOT>").replace(ROOT.as_posix(), "<PACK_ROOT>")
    redacted = redacted.replace(str(Path.home()), "<USER_HOME>").replace(Path.home().as_posix(), "<USER_HOME>")
    redacted = re.sub(r"[A-Za-z]:[\\/]+Users[\\/][A-Za-z0-9_.-]+", "<USER_HOME>", redacted)
    redacted = re.sub(r"/Users/[A-Za-z0-9_.-]+", "<USER_HOME>", redacted)
    return redacted


def _run(cmd: list[str], cwd: Path, log: list[str]) -> int:
    completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    log.append(f"$ {' '.join(cmd)}")
    log.append(completed.stdout)
    log.append(completed.stderr)
    return completed.returncode


def _copy_main() -> str:
    source = PAPER / "bodyshield_non_hardware_draft.pdf"
    target = PAPER / "main.pdf"
    if not source.exists():
        return "missing bodyshield_non_hardware_draft.pdf"
    shutil.copy2(source, target)
    shutil.copy2(source, PAPER / "bodyshield.pdf")
    return "copied existing non-hardware draft PDF"


def _build_supplement() -> str:
    source = PAPER / "supplement.tex"
    if not source.exists():
        shutil.copy2(PAPER / "supplementary.tex", source)
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        return "pdflatex unavailable"
    build = PAPER / "build_supplement"
    build.mkdir(parents=True, exist_ok=True)
    for old in build.glob("supplement.*"):
        old.unlink()
    log: list[str] = []
    cmd = [pdflatex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(source)]
    if _run(cmd, ROOT, log) != 0:
        (REPORTS / "SUPPLEMENT_BUILD_LOG.txt").write_text(_redact("\n".join(log)), encoding="utf-8")
        return "supplement pdflatex returned nonzero"
    built = build / "supplement.pdf"
    if not built.exists():
        return "supplement PDF missing after build"
    shutil.copy2(built, PAPER / "supplement.pdf")
    (REPORTS / "SUPPLEMENT_BUILD_LOG.txt").write_text(_redact("\n".join(log)), encoding="utf-8")
    return "written"


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    status = {"main_pdf": _copy_main(), "supplement_pdf": _build_supplement()}
    (REPORTS / "PAPER_TARGET_BUILD_STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    print(f"MAIN_PDF={status['main_pdf']}")
    print(f"SUPPLEMENT_PDF={status['supplement_pdf']}")
    return 0 if (PAPER / "main.pdf").exists() and (PAPER / "supplement.pdf").exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
