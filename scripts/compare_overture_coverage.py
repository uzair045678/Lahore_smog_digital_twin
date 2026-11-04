import json
import math
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape, box
from shapely.ops import transform
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
PILOT = json.loads((ROOT / "city-data/pilot/lahore_pilot.json").read_text(encoding="utf-8"))
COVERAGE = json.loads((ROOT / "web/public/low-pilot/low_pilot.coverage.json").read_text(encoding="utf-8"))
OVERTURE_PATH = ROOT / "out/overture-map4lb/lahore_buildings.geojson"
OUT = ROOT / "out/overture-map4lb/comparison.json"
PROJECT = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
ORIGIN = (PILOT["coordinate_system"]["origin"]["easting_m"], PILOT["coordinate_system"]["origin"]["northing_m"])


def to_local(x, y, z=None):
    projected_x, projected_y = PROJECT.transform(x, y)
    return projected_x - ORIGIN[0], projected_y - ORIGIN[1]


def center(record):
    points = record["geometry_local_m"]
    if points and isinstance(points[0][0], (int, float)):
        ring = points
    elif points and isinstance(points[0][0][0], (int, float)):
        ring = points[0]
    else:
        ring = points[0][0]
    return sum(point[0] for point in ring) / len(ring), sum(point[1] for point in ring) / len(ring)


def clean(geometry):
    return geometry if geometry.is_valid else geometry.buffer(0)


def wgs84_shape(record):
    coordinates = record["geometry_wgs84"]
    geometry_type = "Polygon" if coordinates and isinstance(coordinates[0][0][0], (int, float)) else "MultiPolygon"
    return shape({"type": geometry_type, "coordinates": coordinates})


def iou(left, right):
    union = left.union(right).area
    return left.intersection(right).area / union if union else 0.0


def cell_for_local(x, y):
    for cell in deficient_cells:
        if cell["local_bounds_m"][0] <= x < cell["local_bounds_m"][2] and cell["local_bounds_m"][1] <= y < cell["local_bounds_m"][3]:
            return tuple(cell["grid"])
    return None


def cell_polygon(cell):
    west, south, east, north = cell["local_bounds_m"]
    return box(west, south, east, north)


def compare_cell(cell, osm_by_cell, overture_by_cell):
    key = tuple(cell["grid"]); osm = osm_by_cell.get(key, []); overture = overture_by_cell.get(key, [])
    matches = []; used = set()
    for osm_id, osm_geometry in osm:
        candidates = []
        for index, (overture_id, overture_geometry, _credible) in enumerate(overture):
            if index in used or not osm_geometry.bounds or not overture_geometry.bounds:
                continue
            if not osm_geometry.intersects(overture_geometry):
                continue
            overlap = iou(osm_geometry, overture_geometry); distance = osm_geometry.centroid.distance(overture_geometry.centroid)
            area_ratio = min(osm_geometry.area, overture_geometry.area) / max(osm_geometry.area, overture_geometry.area) if osm_geometry.area and overture_geometry.area else 0
            if overlap >= 0.20 or (distance <= 15 and area_ratio >= 0.25):
                candidates.append((overlap, -distance, area_ratio, index, overture_id))
        if candidates:
            overlap, negative_distance, area_ratio, index, overture_id = max(candidates)
            used.add(index); matches.append({"osm_id": osm_id, "overture_id": overture_id, "iou": overlap, "centroid_distance_m": -negative_distance, "area_ratio": area_ratio})
    return {"grid": cell["grid"], "local_bounds_m": cell["local_bounds_m"], "osm": len(osm), "overture": len(overture), "matched": len(matches), "overture_only": len(overture) - len(used), "credible_overture_only": sum(item[2] for index, item in enumerate(overture) if index not in used), "osm_only": len(osm) - len(matches), "matches": matches}


overture_geojson = json.loads(OVERTURE_PATH.read_text(encoding="utf-8"))
all_cells = COVERAGE["cells"]
deficient_cells = [cell for cell in all_cells if cell["road_density_class"] == "high" and cell["building_count"] <= 1]
osm_by_cell = {}
for record in PILOT["buildings"]:
    key = cell_for_local(*center(record))
    if key is not None:
        osm_by_cell.setdefault(key, []).append((record["building_id"], clean(transform(to_local, wgs84_shape(record)))))

overture_by_cell = {}
for feature in overture_geojson["features"]:
    geometry = clean(transform(to_local, shape(feature["geometry"])))
    if geometry.is_empty:
        continue
    centroid = geometry.centroid
    key = cell_for_local(centroid.x, centroid.y)
    if key is not None:
        sources = feature.get("properties", {}).get("sources", [])
        confidence = max((float(source.get("confidence") or 0) for source in sources), default=1.0)
        credible = geometry.area >= 20 and not feature.get("properties", {}).get("is_underground", False) and confidence >= 0.7
        overture_by_cell.setdefault(key, []).append((str(feature.get("id", "")), geometry, credible))

results = [compare_cell(cell, osm_by_cell, overture_by_cell) for cell in deficient_cells]
required = [[7, 8], [0, 5], [12, 0], [13, 7], [1, 2]]
required_results = [next(result for result in results if result["grid"] == grid) for grid in required]
result = {
    "schema_version": "low-pilot-overture-comparison-v1",
    "release_method": "Overture bounded CLI download, current release",
    "matching": {"projection": "EPSG:32643", "iou_threshold": 0.20, "centroid_distance_m": 15, "minimum_area_ratio": 0.25, "one_to_one": True},
    "overture_bbox_feature_count": len(overture_geojson["features"]),
    "deficient_cell_count": len(results),
    "required_five": required_results,
    "all_deficient_cells": results,
    "totals": {key: sum(item[key] for item in results) for key in ("osm", "overture", "matched", "overture_only", "credible_overture_only", "osm_only")},
}
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"required_five": required_results, "totals": result["totals"]}, indent=2))
