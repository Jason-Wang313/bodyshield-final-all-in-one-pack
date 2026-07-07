"""Build the ICRA-style BodyShield paper draft if LaTeX tools are available."""

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


def _run(cmd: list[str], cwd: Path, log_parts: list[str]) -> int:
    completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    log_parts.append(f"$ {' '.join(cmd)}")
    log_parts.append(completed.stdout)
    log_parts.append(completed.stderr)
    return completed.returncode


def main() -> int:
    REPORTS.mkdir(exist_ok=True)
    tex = PAPER / "bodyshield_icra.tex"
    output = PAPER / "bodyshield_icra.pdf"
    build = PAPER / "build_icra"
    build.mkdir(parents=True, exist_ok=True)
    log_parts: list[str] = []
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    status = {"status": "failed", "output": str(output.relative_to(ROOT)), "reason": ""}
    if not tex.exists():
        status["reason"] = "paper/bodyshield_icra.tex missing"
    elif not pdflatex:
        status["reason"] = "pdflatex unavailable"
    else:
        for generated in build.glob("bodyshield_icra.*"):
            generated.unlink()
        shutil.copy2(PAPER / "references.bib", build / "references.bib")
        commands = [[pdflatex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(tex)]]
        if bibtex:
            commands.append([bibtex, "bodyshield_icra"])
        commands.extend([[pdflatex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={build}", str(tex)]] * 2)
        ok = True
        for cmd in commands:
            cwd = build if bibtex and cmd[0] == bibtex else ROOT
            if _run(cmd, cwd, log_parts) != 0:
                ok = False
                status["reason"] = f"{Path(cmd[0]).name} returned nonzero"
                break
        built = build / "bodyshield_icra.pdf"
        if ok and built.exists():
            shutil.copy2(built, output)
            status = {"status": "written", "output": str(output.relative_to(ROOT)), "reason": "pdflatex/bibtex succeeded"}
        elif ok:
            status["reason"] = "LaTeX ran but output PDF was missing"
    (REPORTS / "BODYSHIELD_ICRA_BUILD_STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    (REPORTS / "BODYSHIELD_ICRA_BUILD_LOG.txt").write_text(_redact("\n".join(log_parts)), encoding="utf-8", errors="ignore")
    print(f"BODYSHIELD_ICRA_BUILD_STATUS={status['status']}")
    print(f"OUTPUT={status['output']}")
    if status["status"] != "written":
        print(f"REASON={status['reason']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
