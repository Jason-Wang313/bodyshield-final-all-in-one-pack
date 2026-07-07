import json
from pathlib import Path


def test_data_schema_has_trial_id():
    schema = json.loads(Path("trial_schema.schema.json").read_text(encoding="utf-8"))
    assert "trial_id" in schema["properties"]
