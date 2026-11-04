import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
pilot = json.loads((ROOT / "city-data/pilot/lahore_pilot.json").read_text(encoding="utf-8"))
stats = json.loads((ROOT / "web/public/low-pilot/low_pilot.stats.json").read_text(encoding="utf-8"))
features = json.loads((ROOT / "web/public/low-pilot/low_pilot.features.json").read_text(encoding="utf-8"))
coverage = json.loads((ROOT / "web/public/low-pilot/low_pilot.coverage.json").read_text(encoding="utf-8"))
viewer_source = (ROOT / "web/src/lowPilot.ts").read_text(encoding="utf-8")


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


def test_coverage_audit_matches_rendered_features():
    assert coverage["grid_size_m"] == 500.0
    assert coverage["canonical_building_count"] == 4475
    assert coverage["rendered_feature_count"] == 4475
    assert coverage["high_road_low_building_cells"] >= 5
    assert coverage["high_road_zero_building_cells"] >= 5


def test_low_rendering_configuration_and_bounds():
    assert stats["coordinate_bounds"] == pilot["bounds_local_m"]
    assert set(stats["roadHierarchy"]) == {"major", "secondary", "local", "minor"}
    assert sum(item["records"] for item in stats["roadHierarchy"].values()) == 9957
    assert stats["meshes"] == stats["materials"] == 9


def test_benchmark_modes_do_not_hide_gltf_root():
    assert 'if (object === model) return;' in viewer_source
    assert 'mode === "roads"' in viewer_source
    assert 'mode === "buildings"' in viewer_source
    assert 'FOREGROUND CONDITION LOST' in viewer_source
