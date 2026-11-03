import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "city-data" / "canonical" / "lahore.json"


def test_canonical_contract_and_identity() -> None:
    city = json.loads(DATA.read_text(encoding="utf-8"))
    assert city["schema_version"] == "canonical-lahore-v1"
    assert city["coordinate_system"]["projected_crs"] == "EPSG:32643"
    building_ids = [record["building_id"] for record in city["buildings"]]
    road_ids = [record["road_id"] for record in city["roads"]]
    assert len(building_ids) == len(set(building_ids))
    assert len(road_ids) == len(set(road_ids))
    assert city["buildings"]
    assert city["roads"]
    for record in city["buildings"]:
        assert record["height_m"] > 0
        assert record["height_source"] in {"explicit", "levels", "fallback"}
        assert record["geometry_status"] in {"direct", "repaired"}
    for record in city["roads"]:
        assert len(record["geometry_wgs84"]) >= 2


def test_canonical_file_matches_recorded_hash() -> None:
    digest = hashlib.sha256(DATA.read_bytes()).hexdigest()
    stats = json.loads(DATA.with_suffix(".stats.json").read_text(encoding="utf-8"))
    assert stats["sha256"] == digest
