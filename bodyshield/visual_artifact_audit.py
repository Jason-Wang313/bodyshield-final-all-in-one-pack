"""Visual artifact integrity audit for generated figures and GIF media."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd
from PIL import Image, ImageChops, ImageSequence, ImageStat
from pypdf import PdfReader


EXPECTED_FIGURE_STEMS: tuple[str, ...] = (
    "bodyshield_mechanism",
    "breaking_search_comparison",
    "bodybreak_minimality_audit",
    "repair_seen_heldout",
    "nominal_vs_radius",
    "high_fidelity_summary",
    "trajectory_wam_summary",
    "visual_wam_summary",
    "neural_wam_summary",
    "mujoco_residual_policy_summary",
    "mujoco_residual_gate_ablation",
    "corrective_adaptation_summary",
)

CAPTION_PATH_PATTERN = re.compile(r"`(results/(?:figures/[^`]+|videos/bodyshield_synthetic_\*\.gif))`")


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


def _png_rows(path: Path, root: Path) -> list[dict[str, str]]:
    rel = path.relative_to(root).as_posix()
    rows: list[dict[str, str]] = []
    if not path.exists() or path.stat().st_size <= 0:
        return [_fail(rel, "png_exists_nonempty", "PNG missing or empty")]
    rows.append(_pass(rel, "png_exists_nonempty", "PNG exists and is nonempty", str(path.stat().st_size), ">0 bytes"))
    try:
        image = Image.open(path)
        image.load()
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return rows + [_fail(rel, "png_readable", f"PNG could not be read: {exc}")]
    width, height = image.size
    rows.append(_pass(rel, "png_readable", "PNG opens successfully", f"{width}x{height}"))
    rows.append(
        _row(
            rel,
            "png_min_dimensions",
            "pass" if width >= 300 and height >= 150 else "fail",
            "PNG dimensions are large enough for inspection",
            f"{width}x{height}",
            ">=300x150",
        )
    )
    gray = image.convert("L")
    variance = float(ImageStat.Stat(gray).var[0])
    extrema = gray.getextrema()
    rows.append(
        _row(
            rel,
            "png_nonblank_variance",
            "pass" if variance >= 10.0 and (extrema[1] - extrema[0]) >= 10 else "fail",
            "PNG has nonblank pixel variation",
            f"variance={variance:.3f}; extrema={extrema}",
            "variance>=10 and range>=10",
        )
    )
    return rows


def _pdf_rows(path: Path, root: Path) -> list[dict[str, str]]:
    rel = path.relative_to(root).as_posix()
    rows: list[dict[str, str]] = []
    if not path.exists() or path.stat().st_size <= 0:
        return [_fail(rel, "pdf_exists_nonempty", "PDF missing or empty")]
    rows.append(_pass(rel, "pdf_exists_nonempty", "PDF exists and is nonempty", str(path.stat().st_size), ">0 bytes"))
    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        page = reader.pages[0] if reader.pages else None
        trailer_root = reader.trailer.get("/Root", {})
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return rows + [_fail(rel, "pdf_readable", f"PDF could not be read: {exc}")]
    rows.append(_pass(rel, "pdf_readable", "PDF opens successfully", f"pages={page_count}"))
    rows.append(
        _row(rel, "pdf_one_page", "pass" if page_count == 1 else "fail", "figure PDF has exactly one page", str(page_count), "1")
    )
    unsafe = {
        "encrypted": reader.is_encrypted,
        "open_action": bool(trailer_root.get("/OpenAction")),
        "acroform": bool(trailer_root.get("/AcroForm")),
        "names": bool(trailer_root.get("/Names")),
    }
    unsafe_hits = sorted(name for name, hit in unsafe.items() if hit)
    rows.append(
        _row(rel, "pdf_safe_structure", "pass" if not unsafe_hits else "fail", "PDF has no interactive/unsafe structure flags", ",".join(unsafe_hits), "none")
    )
    if page is not None:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        rows.append(
            _row(
                rel,
                "pdf_min_dimensions",
                "pass" if width >= 100.0 and height >= 100.0 else "fail",
                "PDF media box is inspectable",
                f"{width:.1f}x{height:.1f}",
                ">=100x100 pt",
            )
        )
    return rows


def _caption_rows(root: Path, expected_stems: tuple[str, ...]) -> list[dict[str, str]]:
    path = root / "reports" / "FIGURE_CAPTIONS.md"
    rel = "reports/FIGURE_CAPTIONS.md"
    if not path.exists() or path.stat().st_size <= 0:
        return [_fail(rel, "caption_report_exists_nonempty", "caption report missing or empty")]
    text = path.read_text(encoding="utf-8", errors="ignore")
    rows: list[dict[str, str]] = [
        _pass(rel, "caption_report_exists_nonempty", "caption report exists and is nonempty", str(path.stat().st_size), ">0 bytes")
    ]
    referenced = set(CAPTION_PATH_PATTERN.findall(text))
    expected_paths = {f"results/figures/{stem}.pdf" for stem in expected_stems}
    missing = sorted(expected_paths - referenced)
    unexpected = sorted(path for path in referenced if path.startswith("results/figures/") and path not in expected_paths)
    rows.append(
        _row(
            rel,
            "caption_figure_paths_match_expected",
            "pass" if not missing and not unexpected else "fail",
            f"caption figure refs missing={missing}; unexpected={unexpected}",
            str(len(referenced)),
            str(len(expected_paths)),
        )
    )
    gif_heading_ok = "results/videos/bodyshield_synthetic_*.gif" in referenced
    rows.append(
        _row(
            rel,
            "caption_gif_heading_present",
            "pass" if gif_heading_ok else "fail",
            "caption report includes synthetic GIF media heading",
            str(gif_heading_ok),
            "True",
        )
    )
    for ref in sorted(referenced):
        if "*" in ref:
            matched = list((root / "results" / "videos").glob("bodyshield_synthetic_*.gif"))
            rows.append(
                _row(ref, "caption_reference_resolves", "pass" if matched else "fail", "caption glob resolves", str(len(matched)), ">0")
            )
        else:
            target = root / ref
            rows.append(
                _row(ref, "caption_reference_resolves", "pass" if target.exists() and target.stat().st_size > 0 else "fail", "caption target exists and is nonempty", str(target.exists()), "True")
            )
    return rows


def _figure_pair_rows(root: Path, expected_stems: tuple[str, ...]) -> list[dict[str, str]]:
    figures = root / "results" / "figures"
    rows: list[dict[str, str]] = []
    expected = set(expected_stems)
    pdf_stems = {path.stem for path in figures.glob("*.pdf")} if figures.exists() else set()
    png_stems = {path.stem for path in figures.glob("*.png")} if figures.exists() else set()
    all_stems = pdf_stems | png_stems
    missing = sorted(expected - all_stems)
    unexpected = sorted(all_stems - expected)
    rows.append(
        _row(
            "results/figures",
            "figure_stems_match_expected",
            "pass" if not missing and not unexpected else "fail",
            f"figure stems missing={missing}; unexpected={unexpected}",
            ",".join(sorted(all_stems)),
            ",".join(expected_stems),
        )
    )
    for stem in expected_stems:
        pdf = figures / f"{stem}.pdf"
        png = figures / f"{stem}.png"
        pair_ok = pdf.exists() and pdf.stat().st_size > 0 and png.exists() and png.stat().st_size > 0
        rows.append(
            _row(
                f"results/figures/{stem}",
                "pdf_png_pair_exists",
                "pass" if pair_ok else "fail",
                "figure has both PDF and PNG exports",
                f"pdf={pdf.exists()}; png={png.exists()}",
                "pdf=True; png=True",
            )
        )
        rows.extend(_pdf_rows(pdf, root))
        rows.extend(_png_rows(png, root))
    return rows


def _gif_rows(root: Path) -> list[dict[str, str]]:
    manifest = root / "results" / "simulation_rollout_videos.csv"
    rel_manifest = "results/simulation_rollout_videos.csv"
    rows: list[dict[str, str]] = []
    if not manifest.exists() or manifest.stat().st_size <= 0:
        return [_fail(rel_manifest, "gif_manifest_exists_nonempty", "GIF manifest missing or empty")]
    records = list(csv.DictReader(manifest.open(newline="", encoding="utf-8")))
    rows.append(
        _row(rel_manifest, "gif_manifest_row_count", "pass" if len(records) == 3 else "fail", "GIF manifest has expected rows", str(len(records)), "3")
    )
    for record in records:
        rel = str(record.get("path", ""))
        path = root / rel
        if not path.exists() or path.stat().st_size <= 0:
            rows.append(_fail(rel, "gif_exists_nonempty", "GIF missing or empty"))
            continue
        rows.append(_pass(rel, "gif_exists_nonempty", "GIF exists and is nonempty", str(path.stat().st_size), ">0 bytes"))
        try:
            image = Image.open(path)
            frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]
        except Exception as exc:  # pragma: no cover - defensive reporting path
            rows.append(_fail(rel, "gif_readable", f"GIF could not be read: {exc}"))
            continue
        expected_frames = int(float(record.get("frames", 0) or 0))
        expected_size = int(float(record.get("frame_size_px", 0) or 0))
        rows.append(_pass(rel, "gif_readable", "GIF opens successfully", f"frames={len(frames)}; size={image.size}"))
        rows.append(
            _row(rel, "gif_frame_count_matches_manifest", "pass" if len(frames) == expected_frames else "fail", "GIF frame count matches manifest", str(len(frames)), str(expected_frames))
        )
        rows.append(
            _row(rel, "gif_dimensions_match_manifest", "pass" if image.size == (expected_size * 6, expected_size * 6 + 24) else "fail", "GIF dimensions match renderer convention and manifest frame size", f"{image.size}", f"{expected_size * 6}x{expected_size * 6 + 24}")
        )
        if frames:
            variance = float(ImageStat.Stat(frames[0].convert("L")).var[0])
            rows.append(
                _row(rel, "gif_nonblank_first_frame", "pass" if variance >= 10.0 else "fail", "GIF first frame is nonblank", f"variance={variance:.3f}", ">=10")
            )
        moving = any(ImageChops.difference(frames[i], frames[i + 1]).getbbox() for i in range(max(0, len(frames) - 1)))
        rows.append(_row(rel, "gif_has_motion", "pass" if moving else "fail", "GIF has frame-to-frame motion", str(moving), "True"))
    return rows


def run_visual_artifact_audit(root: Path | str = ".", expected_stems: tuple[str, ...] = EXPECTED_FIGURE_STEMS) -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    rows.extend(_figure_pair_rows(root_path, expected_stems))
    rows.extend(_caption_rows(root_path, expected_stems))
    rows.extend(_gif_rows(root_path))
    return pd.DataFrame(rows)


def visual_artifact_summary(rows: pd.DataFrame) -> dict[str, int]:
    if rows.empty:
        return {"checks": 0, "passed": 0, "failed": 0, "artifacts": 0}
    statuses = rows["status"].astype(str)
    return {
        "checks": int(len(rows)),
        "passed": int((statuses == "pass").sum()),
        "failed": int((statuses != "pass").sum()),
        "artifacts": int(rows["artifact"].nunique()),
    }


def failed_visual_artifact_rows(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return rows
    return rows[rows["status"].astype(str) != "pass"].copy()


def write_visual_artifact_report(path: Path | str, rows: pd.DataFrame) -> None:
    path = Path(path)
    summary = visual_artifact_summary(rows)
    status = "pass" if summary["checks"] > 0 and summary["failed"] == 0 else "fail"
    failures = failed_visual_artifact_rows(rows)
    display = failures if not failures.empty else rows.head(120)
    body = display.to_markdown(index=False)
    path.write_text(
        f"""# Visual Artifact Audit

Status: `{status}`

This audit checks generated figure PDF/PNG pairs, PNG dimensions and nonblank pixel variation, PDF readability and safe one-page structure, figure-caption coverage, and synthetic GIF frame count, dimensions, nonblank content, and motion.

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


def write_visual_artifact_reports(root: Path | str = ".") -> pd.DataFrame:
    root_path = Path(root).resolve()
    rows = run_visual_artifact_audit(root_path)
    results = root_path / "results"
    reports = root_path / "reports"
    results.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    rows.to_csv(results / "visual_artifact_audit.csv", index=False)
    write_visual_artifact_report(reports / "VISUAL_ARTIFACT_AUDIT.md", rows)
    return rows
