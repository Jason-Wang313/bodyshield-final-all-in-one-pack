from pathlib import Path

from bodyshield.analysis.claim_ledger import REQUIRED_COLUMNS, validate_claim_ledger


def test_claim_ledger_has_v2_columns_if_generated():
    path = Path("reports/claim_ledger.csv")
    if not path.exists():
        return
    problems = validate_claim_ledger(path)
    assert not problems
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    for column in REQUIRED_COLUMNS:
        assert column in header

