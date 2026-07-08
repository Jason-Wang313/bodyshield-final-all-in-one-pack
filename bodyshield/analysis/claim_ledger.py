"""Claim-ledger loading and validation helpers."""

from __future__ import annotations

import csv
from pathlib import Path


REQUIRED_COLUMNS = (
    "claim_id",
    "paper_section",
    "claim_text",
    "claim_type",
    "evidence_artifacts",
    "trial_ids_or_config_ids",
    "tested_scope",
    "comparison_class",
    "status",
    "limitations",
    "strongest_alternative_explanation",
    "wording_allowed",
)


def load_claim_ledger(path: str | Path = "reports/claim_ledger.csv") -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_claim_ledger(path: str | Path = "reports/claim_ledger.csv") -> list[str]:
    rows = load_claim_ledger(path)
    problems: list[str] = []
    if not rows:
        return ["claim ledger has no rows"]
    missing = [column for column in REQUIRED_COLUMNS if column not in rows[0]]
    if missing:
        problems.append(f"missing columns: {missing}")
    for index, row in enumerate(rows, start=2):
        for column in REQUIRED_COLUMNS:
            if column in row and not str(row[column]).strip():
                problems.append(f"row {index} has empty {column}")
    return problems


__all__ = ["REQUIRED_COLUMNS", "load_claim_ledger", "validate_claim_ledger"]

