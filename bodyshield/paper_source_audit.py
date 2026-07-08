"""Audit paper source, bibliography, build output, and local evidence links."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


DEFAULT_EXPECTED_BIB_KEYS: tuple[str, ...] = (
    "bahl2023vrb",
    "cadene2024lerobot",
    "chen2022domainrandomization",
    "muratore2022randomizedsim",
    "routray2025vipra",
    "vuong2019pickdr",
    "tobin2017domainrandomization",
    "peng2018dynamicsrandomization",
    "openai2018dexterous",
    "gupta2025umionair",
    "wang2026embodisteer",
    "le2025verificationguided",
    "zeng2021mpccbf",
    "jiang2024transic",
)
DEFAULT_REQUIRED_TEX_TERMS: tuple[str, ...] = (
    "analytic-simulation evidence",
    "generated frames rather than real camera videos",
    "one public SB3/RL-Zoo HalfCheetah checkpoint rollout",
    "broader trained-policy suites, manipulation/foundation-policy checkpoints",
    "Hardware placeholder only",
)
DEFAULT_REQUIRED_PDF_TERMS: tuple[str, ...] = (
    "BodyShield",
    "analytic",
    "generated frames",
    "real camera",
    "real robot results",
)
DEFAULT_REQUIRED_LOCAL_REFS: tuple[str, ...] = ("data_schema.json", "results/")

CITATION_PATTERN = re.compile(r"\\(?:cite|citep|citet|citealt|citealp|citeauthor|citeyear)(?:\[[^\]]*\])*\{([^}]*)\}")
BIB_KEY_PATTERN = re.compile(r"@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,")
LABEL_PATTERN = re.compile(r"\\label\{([^}]*)\}")
REF_PATTERN = re.compile(r"\\(?:ref|eqref|pageref|autoref)\{([^}]*)\}")
BIBLIOGRAPHY_PATTERN = re.compile(r"\\bibliography\{([^}]*)\}")
INCLUDEGRAPHICS_PATTERN = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}")
PATH_PATTERN = re.compile(r"\\path\{([^}]*)\}")
TABLE_PATTERN = re.compile(r"\\begin\{table\}(.+?)\\end\{table\}", re.DOTALL)


def _row(artifact: str, check: str, status: str, detail: str, observed: str = "", expected: str = "") -> dict[str, str]:
    return {
        "artifact": artifact,
        "check": check,
        "status": status,
        "detail": detail,
        "observed": observed,
        "expected": expected,
    }


def _pass(artifact: str, check: str, detail: str, observed: str = "", expected: str = "") -> dict[str, str]:
    return _row(artifact, check, "pass", detail, observed, expected)


def _fail(artifact: str, check: str, detail: str, observed: str = "", expected: str = "") -> dict[str, str]:
    return _row(artifact, check, "fail", detail, observed, expected)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _norm_rel(path: str) -> str:
    return path.replace("\\", "/").strip()


def _citation_keys(tex_text: str) -> set[str]:
    keys: set[str] = set()
    for match in CITATION_PATTERN.finditer(tex_text):
        keys.update(key.strip() for key in match.group(1).split(",") if key.strip())
    return keys


def _bib_keys(bib_text: str) -> set[str]:
    return {match.group(1).strip() for match in BIB_KEY_PATTERN.finditer(bib_text)}


def _bibliography_paths(root: Path, tex_dir: Path, tex_text: str) -> list[Path]:
    paths: list[Path] = []
    for match in BIBLIOGRAPHY_PATTERN.finditer(tex_text):
        for raw_name in match.group(1).split(","):
            name = raw_name.strip()
            if not name:
                continue
            rel = Path(name if name.endswith(".bib") else f"{name}.bib")
            paths.extend([tex_dir / rel, root / rel])
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def _figure_candidates(root: Path, tex_dir: Path, raw_path: str) -> list[Path]:
    rel = Path(_norm_rel(raw_path))
    bases = [root / rel, tex_dir / rel]
    if rel.suffix:
        return bases
    candidates: list[Path] = []
    for base in bases:
        candidates.extend(base.with_suffix(suffix) for suffix in (".pdf", ".png", ".jpg", ".jpeg"))
    return candidates


def _local_path_refs(tex_text: str) -> set[str]:
    refs = {_norm_rel(match.group(1)) for match in PATH_PATTERN.finditer(tex_text)}
    return {ref for ref in refs if ref and not re.match(r"^[A-Za-z]+://", ref)}


def _path_exists(root: Path, ref: str) -> bool:
    normalized = _norm_rel(ref)
    if "*" in normalized:
        return bool(list(root.glob(normalized)))
    path = root / normalized.rstrip("/")
    return path.exists() and (path.is_dir() or path.stat().st_size > 0)


def _pdf_rows(
    root: Path,
    pdf_path: Path,
    build_pdf_path: Path,
    expected_page_count: int | None,
    required_pdf_terms: tuple[str, ...],
) -> list[dict[str, str]]:
    rel_pdf = pdf_path.relative_to(root).as_posix() if pdf_path.is_relative_to(root) else str(pdf_path)
    rows: list[dict[str, str]] = []
    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        return [_fail(rel_pdf, "pdf_exists_nonempty", "paper PDF missing or empty")]
    rows.append(_pass(rel_pdf, "pdf_exists_nonempty", "paper PDF exists and is nonempty", str(pdf_path.stat().st_size), ">0 bytes"))
    try:
        reader = PdfReader(str(pdf_path))
        trailer_root = reader.trailer.get("/Root", {})
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return rows + [_fail(rel_pdf, "pdf_readable_pages", f"could not read PDF: {exc}")]

    page_status = expected_page_count is None or len(reader.pages) == expected_page_count
    rows.append(
        _row(
            rel_pdf,
            "pdf_readable_pages",
            "pass" if page_status else "fail",
            "paper PDF opens and has expected page count",
            str(len(reader.pages)),
            "any" if expected_page_count is None else str(expected_page_count),
        )
    )
    unsafe = {
        "encrypted": reader.is_encrypted,
        "open_action": bool(trailer_root.get("/OpenAction")),
        "acroform": bool(trailer_root.get("/AcroForm")),
        "names": bool(trailer_root.get("/Names")),
    }
    unsafe_hits = sorted(name for name, hit in unsafe.items() if hit)
    rows.append(
        _row(
            rel_pdf,
            "pdf_safe_structure",
            "pass" if not unsafe_hits else "fail",
            "paper PDF has no interactive/unsafe structure flags",
            ",".join(unsafe_hits),
            "none",
        )
    )
    bad_tokens = [token for token in ("??", "[?]", "undefined", "Citation") if token in text]
    rows.append(
        _row(
            rel_pdf,
            "pdf_unresolved_markers_absent",
            "pass" if not bad_tokens else "fail",
            f"PDF extracted text unresolved markers={bad_tokens}",
            ",".join(bad_tokens),
            "none",
        )
    )
    lower_text = text.lower()
    missing_terms = [term for term in required_pdf_terms if term.lower() not in lower_text]
    rows.append(
        _row(
            rel_pdf,
            "pdf_boundary_terms_present",
            "pass" if not missing_terms else "fail",
            f"required PDF boundary terms missing={missing_terms}",
            str(len(required_pdf_terms) - len(missing_terms)),
            str(len(required_pdf_terms)),
        )
    )

    rel_build = build_pdf_path.relative_to(root).as_posix() if build_pdf_path.is_relative_to(root) else str(build_pdf_path)
    if build_pdf_path.exists() and build_pdf_path.stat().st_size > 0:
        pdf_sha = _sha256(pdf_path)
        build_sha = _sha256(build_pdf_path)
        rows.append(
            _row(
                rel_pdf,
                "pdf_matches_build_output",
                "pass" if pdf_sha == build_sha else "fail",
                "exported paper PDF matches paper/build/main.pdf when build output is available",
                pdf_sha,
                build_sha,
            )
        )
    else:
        rows.append(
            _pass(
                rel_build,
                "pdf_matches_build_output",
                "paper/build/main.pdf is absent, as in release payloads; exported PDF was inspected directly",
                "absent",
                "match when present",
            )
        )
    return rows


def run_paper_source_audit(
    root: Path | str = ".",
    expected_bib_keys: tuple[str, ...] = DEFAULT_EXPECTED_BIB_KEYS,
    expected_page_count: int | None = None,
    required_pdf_terms: tuple[str, ...] = DEFAULT_REQUIRED_PDF_TERMS,
    required_tex_terms: tuple[str, ...] = DEFAULT_REQUIRED_TEX_TERMS,
    required_local_refs: tuple[str, ...] = DEFAULT_REQUIRED_LOCAL_REFS,
    expected_min_tables: int = 1,
) -> pd.DataFrame:
    root_path = Path(root).resolve()
    paper_dir = root_path / "paper"
    reports_dir = root_path / "reports"
    tex_path = paper_dir / "main.tex"
    bib_path = paper_dir / "references.bib"
    pdf_path = paper_dir / "bodyshield_non_hardware_draft.pdf"
    build_pdf_path = paper_dir / "build" / "main.pdf"
    build_status_path = reports_dir / "PAPER_BUILD_STATUS.json"
    build_log_path = reports_dir / "PAPER_BUILD_LOG.txt"

    rows: list[dict[str, str]] = []
    for path, check, detail in (
        (tex_path, "tex_exists_nonempty", "paper TeX source exists and is nonempty"),
        (bib_path, "bib_exists_nonempty", "paper BibTeX source exists and is nonempty"),
    ):
        rel = path.relative_to(root_path).as_posix()
        rows.append(
            _row(
                rel,
                check,
                "pass" if path.exists() and path.stat().st_size > 0 else "fail",
                detail,
                str(path.stat().st_size) if path.exists() else "missing",
                ">0 bytes",
            )
        )

    tex_text = _text(tex_path)
    bib_text = _text(bib_path)

    cited = _citation_keys(tex_text)
    bib_keys = _bib_keys(bib_text)
    missing_cites = sorted(cited - bib_keys)
    rows.append(
        _row(
            "paper/main.tex",
            "tex_citations_resolve",
            "pass" if cited and not missing_cites else "fail",
            f"citation keys missing from bibliography={missing_cites}",
            ",".join(sorted(cited)),
            "all cited keys in paper/references.bib",
        )
    )
    missing_expected_bib = sorted(set(expected_bib_keys) - bib_keys)
    rows.append(
        _row(
            "paper/references.bib",
            "bib_required_keys_present",
            "pass" if not missing_expected_bib else "fail",
            f"expected bibliography keys missing={missing_expected_bib}",
            str(len(set(expected_bib_keys) - set(missing_expected_bib))),
            str(len(expected_bib_keys)),
        )
    )

    bibliography_paths = _bibliography_paths(root_path, paper_dir, tex_text)
    unresolved_bibliographies = sorted(
        raw for raw in {path.name for path in bibliography_paths} if not any(candidate.exists() for candidate in bibliography_paths if candidate.name == raw)
    )
    rows.append(
        _row(
            "paper/main.tex",
            "tex_bibliography_files_resolve",
            "pass" if bibliography_paths and not unresolved_bibliographies else "fail",
            f"bibliography declarations missing={unresolved_bibliographies}",
            ",".join(sorted({path.name for path in bibliography_paths})),
            "at least one existing .bib file",
        )
    )

    labels = set(LABEL_PATTERN.findall(tex_text))
    refs = set(REF_PATTERN.findall(tex_text))
    missing_refs = sorted(refs - labels)
    rows.append(
        _row(
            "paper/main.tex",
            "tex_refs_resolve",
            "pass" if refs and not missing_refs else "fail",
            f"label references missing={missing_refs}",
            ",".join(sorted(refs)),
            "all refs have labels",
        )
    )

    figure_refs = [_norm_rel(match.group(1)) for match in INCLUDEGRAPHICS_PATTERN.finditer(tex_text)]
    missing_figures = sorted(ref for ref in figure_refs if not any(path.exists() and path.stat().st_size > 0 for path in _figure_candidates(root_path, paper_dir, ref)))
    rows.append(
        _row(
            "paper/main.tex",
            "tex_figure_paths_resolve",
            "pass" if not missing_figures else "fail",
            f"includegraphics paths missing={missing_figures}",
            str(len(figure_refs) - len(missing_figures)),
            str(len(figure_refs)),
        )
    )

    path_refs = _local_path_refs(tex_text)
    missing_path_refs = sorted(ref for ref in path_refs if not _path_exists(root_path, ref))
    rows.append(
        _row(
            "paper/main.tex",
            "tex_local_paths_resolve",
            "pass" if not missing_path_refs else "fail",
            f"local \\path references missing={missing_path_refs}",
            ",".join(sorted(path_refs)),
            "all local paths exist",
        )
    )
    missing_required_refs = [ref for ref in required_local_refs if ref not in path_refs and ref not in tex_text]
    rows.append(
        _row(
            "paper/main.tex",
            "tex_required_result_refs_present",
            "pass" if not missing_required_refs else "fail",
            f"required local evidence refs missing from TeX={missing_required_refs}",
            str(len(required_local_refs) - len(missing_required_refs)),
            str(len(required_local_refs)),
        )
    )

    missing_tex_terms = [term for term in required_tex_terms if term not in tex_text]
    rows.append(
        _row(
            "paper/main.tex",
            "tex_boundary_terms_present",
            "pass" if not missing_tex_terms else "fail",
            f"required TeX boundary terms missing={missing_tex_terms}",
            str(len(required_tex_terms) - len(missing_tex_terms)),
            str(len(required_tex_terms)),
        )
    )
    tex_bad_tokens = [token for token in ("??", "\\cite{?}", "undefined", "Citation") if token in tex_text]
    rows.append(
        _row(
            "paper/main.tex",
            "tex_unresolved_markers_absent",
            "pass" if not tex_bad_tokens else "fail",
            f"TeX unresolved markers={tex_bad_tokens}",
            ",".join(tex_bad_tokens),
            "none",
        )
    )

    tables = TABLE_PATTERN.findall(tex_text)
    bad_tables = [
        str(index)
        for index, table_text in enumerate(tables, start=1)
        if "\\caption" not in table_text or "\\label" not in table_text
    ]
    table_status = len(tables) >= expected_min_tables and not bad_tables
    rows.append(
        _row(
            "paper/main.tex",
            "tex_tables_have_captions_and_labels",
            "pass" if table_status else "fail",
            f"tables missing caption or label={bad_tables}",
            str(len(tables)),
            f">={expected_min_tables}",
        )
    )

    if build_status_path.exists() and build_status_path.stat().st_size > 0:
        try:
            status_payload = json.loads(build_status_path.read_text(encoding="utf-8"))
            build_ok = status_payload.get("status") == "written" and status_payload.get("output") == "paper\\bodyshield_non_hardware_draft.pdf"
            rows.append(
                _row(
                    "reports/PAPER_BUILD_STATUS.json",
                    "paper_build_status_written",
                    "pass" if build_ok else "fail",
                    "paper build status JSON records the expected written output",
                    f"status={status_payload.get('status')}; output={status_payload.get('output')}",
                    "status=written; output=paper\\bodyshield_non_hardware_draft.pdf",
                )
            )
        except json.JSONDecodeError as exc:
            rows.append(_fail("reports/PAPER_BUILD_STATUS.json", "paper_build_status_written", f"could not parse JSON: {exc}"))
    else:
        rows.append(_fail("reports/PAPER_BUILD_STATUS.json", "paper_build_status_written", "paper build status JSON missing or empty"))

    log_hits: list[str] = []
    log_paths = [build_log_path, paper_dir / "build" / "main.log"]
    for log_path in log_paths:
        if not log_path.exists() or log_path.stat().st_size <= 0:
            if log_path == build_log_path:
                log_hits.append(f"{log_path.relative_to(root_path).as_posix()}:missing")
            continue
        log_text = _text(log_path)
        for pattern in ("LaTeX Warning", "undefined", "Citation", "Reference", "Overfull"):
            if pattern in log_text:
                log_hits.append(f"{log_path.relative_to(root_path).as_posix()}:{pattern}")
    rows.append(
        _row(
            "reports/PAPER_BUILD_LOG.txt",
            "paper_build_log_clean",
            "pass" if not log_hits else "fail",
            f"build log unresolved/warning markers={log_hits}",
            str(len(log_hits)),
            "0",
        )
    )

    rows.extend(_pdf_rows(root_path, pdf_path, build_pdf_path, expected_page_count, required_pdf_terms))
    return pd.DataFrame(rows)


def paper_source_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_paper_source_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_paper_source_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = paper_source_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_paper_source_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Paper Source Audit

Status: `{status}`

This audit checks the paper TeX source, bibliography, labels, local path references, table structure, build status/logs, exported PDF readability, source-output consistency, and explicit evidence-boundary wording.

| metric | value |
|---|---:|
| checks | {summary['checks']} |
| passed | {summary['passed']} |
| failed | {summary['failed']} |
| artifacts audited | {summary['artifacts']} |

## Display Rows

{body}
""",
        encoding="utf-8",
    )


def write_paper_source_audit_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_paper_source_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "paper_source_audit.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    write_paper_source_report(reports / "PAPER_SOURCE_AUDIT.md", rows)
    return rows
