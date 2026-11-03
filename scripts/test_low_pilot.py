import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
pilot = json.loads((ROOT / "city-data/pilot/lahore_pilot.json").read_text(encoding="utf-8"))
stats = json.loads((ROOT / "web/public/low-pilot/low_pilot.stats.json").read_text(encoding="utf-8"))
features = json.loads((ROOT / "web/public/low-pilot/low_pilot.features.json").read_text(encoding="utf-8"))


def test_low_asset_and_counts():
    assert (ROOT / "web/public/low-pilot/low_pilot.glb").stat().st_size > 0
    assert stats["geometry"]["buildingsGenerated"] == len(pilot["buildings"]) == 4475
    assert stats["geometry"]["buildingsFailed"] == 0
    assert stats["geometry"]["renderedRoadRecords"] == len(pilot["roads"]) == 9957
    assert stats["geometry"]["omittedRoadRecords"] == 0


def test_low_safety_and_height_consistency():
    geometry = stats["geometry"]
    assert geometry["maxAreaError"] <= stats["config"]["max_area_error"]
    assert geometry["maxCentroidDisplacementM"] <= stats["config"]["max_centroid_displacement_m"]
    assert geometry["holesRetained"] == 137
    assert geometry["holesOmitted"] == 0
    canonical_heights = {record["building_id"]: record["height_m"] for record in pilot["buildings"]}
    assert {item["building_id"] for item in features["features"]} == set(canonical_heights)
    assert all(item.get("height_m") == canonical_heights[item["building_id"]] for item in features["features"])


def test_low_isolated_from_high_output():
    assert not list((ROOT / "web/public/low-pilot").glob("*high*"))
