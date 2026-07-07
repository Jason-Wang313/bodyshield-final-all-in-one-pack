"""Video audit entry point for existing synthetic media."""

from __future__ import annotations

from bodyshield.visual_artifact_audit import write_visual_artifact_reports


def main() -> int:
    rows = write_visual_artifact_reports(".")
    failed = rows[rows["status"] == "fail"]
    print(f"VIDEO_AUDIT_STATUS={'pass' if failed.empty else 'fail'}")
    return 0 if failed.empty else 1


if __name__ == "__main__":
    raise SystemExit(main())
