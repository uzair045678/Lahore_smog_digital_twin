#!/usr/bin/env python
"""Select and materialize one deterministic canonical Lahore pilot subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time
from collections import Counter

from pyproj import Transformer


def overlaps(bounds: list[float], candidate: dict[str, float]) -> bool:
    west, south, east, north = bounds
    return not (east < candidate["west"] or west > candidate["east"] or north < candidate["south"] or south > candidate["north"])


def polygons(geometry: list) -> list[list[list[float]]]:
    return [geometry] if isinstance(geometry[0][0][0], (int, float)) else geometry


def metrics(buildings: list[dict], roads: list[dict]) -> dict:
    height_sources = Counter(record["height_source"] for record in buildings)
    classes = Counter(record["building_type"] for record in buildings)
    road_classes = Counter(record["highway"] for record in roads)
    complex_count = 0
    hole_count = 0
    vertex_counts: list[int] = []
    multipolygons = 0
    for record in buildings:
        geometry = record["geometry_wgs84"]
        current_polygons = polygons(geometry)
        if record["source_kind"] == "relation":
            multipolygons += 1
        for polygon in current_polygons:
            outer_vertices = len(polygon[0]) - 1
            vertex_counts.append(outer_vertices)
            complex_count += outer_vertices > 6
            hole_count += max(0, len(polygon) - 1)
    return {
        "buildings": len(buildings),
        "roads": len(roads),
        "road_length_km": round(sum(record["length_m"] for record in roads) / 1000, 3),
        "height_sources": dict(height_sources),
        "building_classes": dict(classes),
        "building_class_count": len(classes),
        "road_classes": dict(road_classes),
        "road_class_count": len(road_classes),
        "complex_footprints": complex_count,
        "multipolygons": multipolygons,
        "holes": hole_count,
        "vertex_count": {"min": min(vertex_counts) if vertex_counts else 0, "median": sorted(vertex_counts)[len(vertex_counts) // 2] if vertex_counts else 0, "max": max(vertex_counts) if vertex_counts else 0},
        "explicit_width_roads": sum(record["width_source"] == "explicit" for record in roads),
    }


def score(statistics: dict) -> int:
    sources = statistics["height_sources"]
    return (
        (3 if 2000 <= statistics["buildings"] <= 8000 else 0)
        + (3 if all(sources.get(source, 0) > 0 for source in ("explicit", "levels", "fallback")) else 0)
        + (2 if statistics["building_class_count"] >= 10 else 0)
        + (2 if statistics["road_class_count"] >= 6 else 0)
        + (2 if statistics["complex_footprints"] >= 500 else 0)
        + (2 if statistics["holes"] > 0 else 0)
        + (2 if statistics["roads"] >= 5000 else 0)
    )


def local_bounds(candidate: dict[str, float], transformer: Transformer, origin: tuple[float, float]) -> list[float]:
    ox, oy = origin
    points = [
        transformer.transform(candidate["west"], candidate["south"]),
        transformer.transform(candidate["west"], candidate["north"]),
        transformer.transform(candidate["east"], candidate["south"]),
        transformer.transform(candidate["east"], candidate["north"]),
    ]
    xs = [x - ox for x, _ in points]
    ys = [y - oy for _, y in points]
    return [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)]


def choose_fixtures(buildings: list[dict], roads: list[dict]) -> dict[str, str]:
    ordered = sorted(buildings, key=lambda record: record["building_id"])
    fixtures: dict[str, str] = {}
    fixtures["simple"] = min(ordered, key=lambda r: (len(polygons(r["geometry_wgs84"])[0][0]), r["building_id"]))["building_id"]
    fixtures["irregular"] = max(ordered, key=lambda r: (len(polygons(r["geometry_wgs84"])[0][0]), r["building_id"]))["building_id"]
    for source in ("explicit", "levels", "fallback"):
        fixtures[source] = next(r["building_id"] for r in ordered if r["height_source"] == source)
    fixtures["multipolygon"] = next(r["building_id"] for r in ordered if r["source_kind"] == "relation")
    fixtures["hole"] = next(r["building_id"] for r in ordered if sum(max(0, len(polygon) - 1) for polygon in polygons(r["geometry_wgs84"])) > 0)
    road_ordered = sorted(roads, key=lambda record: record["road_id"])
    for label, classes in {"major": {"motorway", "trunk", "primary"}, "secondary_tertiary": {"secondary", "tertiary"}, "residential": {"residential"}}.items():
        fixtures[label] = next(r["road_id"] for r in road_ordered if r["highway"] in classes)
    fixtures["complex_road"] = max(road_ordered, key=lambda r: (len(r["geometry_wgs84"]), r["road_id"]))["road_id"]
    return fixtures


def build(canonical_path: pathlib.Path, config_path: pathlib.Path, output_path: pathlib.Path) -> dict:
    started = time.perf_counter()
    canonical_bytes = canonical_path.read_bytes()
    canonical = json.loads(canonical_bytes)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    candidates = {}
    for name, candidate in config["candidates"].items():
        buildings = [record for record in canonical["buildings"] if overlaps(record["bounds_wgs84"], candidate)]
        roads = [record for record in canonical["roads"] if overlaps(record["bounds_wgs84"], candidate)]
        statistics = metrics(buildings, roads)
        candidates[name] = {"bounds": candidate, "statistics": statistics, "score": score(statistics)}
    selected_name = config["selected"]
    selected = candidates[selected_name]
    buildings = [record for record in canonical["buildings"] if overlaps(record["bounds_wgs84"], selected["bounds"])]
    roads = [record for record in canonical["roads"] if overlaps(record["bounds_wgs84"], selected["bounds"])]
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
    origin = (canonical["coordinate_system"]["origin"]["easting_m"], canonical["coordinate_system"]["origin"]["northing_m"])
    projected = [transformer.transform(selected["bounds"][key], selected["bounds"][other]) for key, other in (("west", "south"), ("west", "north"), ("east", "south"), ("east", "north"))]
    projected_bounds = [round(min(point[0] for point in projected), 3), round(min(point[1] for point in projected), 3), round(max(point[0] for point in projected), 3), round(max(point[1] for point in projected), 3)]
    pilot = {
        "schema_version": "canonical-lahore-pilot-v1",
        "canonical_schema_version": canonical["schema_version"],
        "canonical_source_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
        "pilot": {"name": selected_name, "selection_rule": config["selection_rule"], "bounds_wgs84": [selected["bounds"][key] for key in ("west", "south", "east", "north")], "bounds_projected_m": projected_bounds, "bounds_local_m": local_bounds(selected["bounds"], transformer, origin), "dimensions_m": [round(projected_bounds[2] - projected_bounds[0], 3), round(projected_bounds[3] - projected_bounds[1], 3)], "approximate_area_km2": round((projected_bounds[2] - projected_bounds[0]) * (projected_bounds[3] - projected_bounds[1]) / 1_000_000, 3), "feature_rule": config["selection_rule"], "candidate_scores": candidates, "rejected_relation_ids": "not retained by M3B canonical output; no source reacquisition performed"},
        "coordinate_system": canonical["coordinate_system"],
        "source": canonical["source"],
        "height_rules": canonical["height_rules"],
        "build_config": canonical["build_config"],
        "bounds_wgs84": [selected["bounds"][key] for key in ("west", "south", "east", "north")],
        "bounds_local_m": local_bounds(selected["bounds"], transformer, origin),
        "buildings": sorted(buildings, key=lambda record: record["building_id"]),
        "roads": sorted(roads, key=lambda record: record["road_id"]),
        "statistics": selected["statistics"],
        "fixtures": choose_fixtures(buildings, roads),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(pilot, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    output_path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    stats = {"pilot_sha256": digest, "size_bytes": len(payload), "generation_seconds": round(time.perf_counter() - started, 3), "statistics": pilot["statistics"], "fixtures": pilot["fixtures"], "candidate_scores": candidates}
    output_path.with_suffix(".stats.json").write_bytes((json.dumps(stats, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(stats, indent=2))
    return pilot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", type=pathlib.Path, default=pathlib.Path("city-data/canonical/lahore.json"))
    parser.add_argument("--config", type=pathlib.Path, default=pathlib.Path("city-data/pilot/config.json"))
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("city-data/pilot/lahore_pilot.json"))
    args = parser.parse_args()
    build(args.canonical, args.config, args.output)


if __name__ == "__main__":
    main()
