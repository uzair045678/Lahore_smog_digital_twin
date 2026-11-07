import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = json.loads((ROOT / "city-data/pilot/lahore_pilot.json").read_text(encoding="utf-8"))
STATS = json.loads((ROOT / "web/public/high-pilot/high_pilot.stats.json").read_text(encoding="utf-8"))


def test_high_asset_matches_canonical_pilot() -> None:
    geometry = STATS["geometry"]
    assert STATS["schema_version"] == "high-pilot-stats-v2"
    assert STATS["config"]["variant"] == "high"
    assert geometry["buildingsGenerated"] == len(PILOT["buildings"]) == 4475
    assert geometry["buildingsFailed"] == 0
    assert geometry["renderedRoadRecords"] == len(PILOT["roads"]) == 9957
    assert geometry["holesRetained"] == 137
    assert (ROOT / "web/public/high-pilot/high_pilot.glb").stat().st_size == STATS["assetBytes"]
