import json
import pathlib

import pytest

loader = pathlib.Path("out/latest.json")

@ pytest.mark.skip(reason="stub pipeline, no real data")
def test_latest_structure():
    with open(loader, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "schema_version" in data
    assert "stations" in data
    assert isinstance(data["stations"], list)
