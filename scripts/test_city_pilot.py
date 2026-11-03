import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "city-data/canonical/lahore.json"
PILOT = ROOT / "city-data/pilot/lahore_pilot.json"


def test_pilot_ids_and_values_are_canonical() -> None:
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    buildings = {record["building_id"]: record for record in canonical["buildings"]}
    roads = {record["road_id"]: record for record in canonical["roads"]}
    assert pilot["canonical_source_sha256"] == hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
    assert all(record["building_id"] in buildings for record in pilot["buildings"])
    assert all(record["road_id"] in roads for record in pilot["roads"])
    for record in pilot["buildings"]:
        source = buildings[record["building_id"]]
        assert record["height_m"] == source["height_m"]
        assert record["height_source"] == source["height_source"]
        assert record["geometry_local_m"] == source["geometry_local_m"]
    for record in pilot["roads"]:
        assert record["geometry_local_m"] == roads[record["road_id"]]["geometry_local_m"]


def test_pilot_sidecar_hash_and_selection() -> None:
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    sidecar = json.loads(PILOT.with_suffix(".stats.json").read_text(encoding="utf-8"))
    assert sidecar["pilot_sha256"] == hashlib.sha256(PILOT.read_bytes()).hexdigest()
    assert pilot["pilot"]["name"] == "central_gulberg"
    assert set(pilot["statistics"]["height_sources"]) == {"explicit", "levels", "fallback"}
    assert pilot["statistics"]["road_class_count"] >= 6
