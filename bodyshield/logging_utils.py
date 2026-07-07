"""Logging helpers for JSONL experiment records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_jsonl(path: Path | str, record: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


__all__ = ["append_jsonl", "read_jsonl"]
