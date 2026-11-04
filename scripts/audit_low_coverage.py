import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "city-data/pilot/lahore_pilot.json"
OUT = ROOT / "web/public/low-pilot/low_pilot.coverage.json"
GRID_M = 500.0


def points(geometry):
    if geometry and isinstance(geometry[0][0], (int, float)):
        return geometry
    if geometry and isinstance(geometry[0][0][0], (int, float)):
        return geometry[0]
    return geometry[0][0]


def center(record):
    ps = points(record["geometry_local_m"])
    return (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))


def cell_index(x, y, bounds):
    return (math.floor((x - bounds[0]) / GRID_M), math.floor((y - bounds[1]) / GRID_M))


def percentile(values, fraction):
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * fraction))]


pilot = json.loads(PILOT.read_text(encoding="utf-8"))
bounds = pilot["bounds_local_m"]
cells = {}


def get_cell(index):
    return cells.setdefault(index, {"grid": list(index), "building_ids": [], "road_ids": [], "road_length_m": 0.0})


for record in pilot["buildings"]:
    get_cell(cell_index(*center(record), bounds))["building_ids"].append(record["building_id"])
for record in pilot["roads"]:
    c = get_cell(cell_index(*center(record), bounds))
    c["road_ids"].append(record["road_id"])
    c["road_length_m"] += record["length_m"]

road_values = [c["road_length_m"] for c in cells.values() if c["road_length_m"]]
high_road_threshold = percentile(road_values, 0.75)
for c in cells.values():
    c["building_count"] = len(c.pop("building_ids"))
    c["road_count"] = len(c.pop("road_ids"))
    c["building_density_per_km2"] = c["building_count"] / (GRID_M * GRID_M / 1_000_000)
    c["road_density_km_per_km2"] = c["road_length_m"] / 1000 / (GRID_M * GRID_M / 1_000_000)
    c["road_density_class"] = "high" if c["road_length_m"] >= high_road_threshold else "other"

suspicious = sorted((c for c in cells.values() if c["road_density_class"] == "high" and c["building_count"] <= 1), key=lambda c: c["road_length_m"], reverse=True)
for c in suspicious:
    gx, gy = c["grid"]
    c["local_bounds_m"] = [bounds[0] + gx * GRID_M, bounds[1] + gy * GRID_M, bounds[0] + (gx + 1) * GRID_M, bounds[1] + (gy + 1) * GRID_M]

features = json.loads((ROOT / "web/public/low-pilot/low_pilot.features.json").read_text(encoding="utf-8"))["features"]
feature_ids = {item["building_id"] for item in features}
for c in cells.values():
    c["rendered_building_count"] = 0
    c["rendered_building_ids"] = []
for record in pilot["buildings"]:
    c = get_cell(cell_index(*center(record), bounds))
    if record["building_id"] in feature_ids:
        c["rendered_building_count"] += 1
        if c in suspicious:
            c["rendered_building_ids"].append(record["building_id"])

result = {
    "schema_version": "low-pilot-coverage-v1",
    "grid_size_m": GRID_M,
    "bounds_local_m": bounds,
    "cell_count": len(cells),
    "high_road_threshold_m": high_road_threshold,
    "cells": sorted(cells.values(), key=lambda c: c["grid"]),
    "suspicious_areas": suspicious[:10],
    "high_road_low_building_cells": sum(c["road_density_class"] == "high" and c["building_count"] <= 1 for c in cells.values()),
    "high_road_zero_building_cells": sum(c["road_density_class"] == "high" and c["building_count"] == 0 for c in cells.values()),
    "canonical_building_count": len(pilot["buildings"]),
    "rendered_feature_count": len(feature_ids),
}
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({k: result[k] for k in ("grid_size_m", "cell_count", "high_road_threshold_m", "high_road_low_building_cells", "high_road_zero_building_cells", "canonical_building_count", "rendered_feature_count")}, indent=2))
