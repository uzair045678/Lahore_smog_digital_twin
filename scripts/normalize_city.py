#!/usr/bin/env python
"""Build the deterministic, rendering-independent canonical Lahore dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
from collections import Counter
from dataclasses import dataclass

import osmium
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, mapping
from shapely.ops import polygonize, transform, unary_union


BOUNDARY_PATH = pathlib.Path("scripts/sources/lahore_boundary.json")
ORIGIN_LAT = 31.5204
ORIGIN_LON = 74.3587
FLOOR_HEIGHT_M = 3.2
PROCESSING_BUFFER_DEG = 0.001
HEIGHT_MAX_M = 150.0
LEVELS_MAX = 100.0
WGS84_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
UTM_TO_WGS84 = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)


def boundary_geometry() -> tuple[object, tuple[float, float, float, float]]:
    raw = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    lines = [
        LineString([(p["lon"], p["lat"]) for p in member.get("geometry", [])])
        for member in raw.get("members", [])
        if member.get("role") == "outer" and len(member.get("geometry", [])) > 1
    ]
    polygons = list(polygonize(unary_union(lines)))
    if len(polygons) != 1:
        raise ValueError(f"expected one boundary polygon, found {len(polygons)}")
    geometry = polygons[0]
    return geometry, geometry.bounds


def finite_number(value: str | None, *, maximum: float) -> float | None:
    if value is None:
        return None
    match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*(m|metre|meter|ft|feet|')?\s*", str(value), re.I)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "m").lower()
    if unit in {"ft", "feet", "'"}:
        number *= 0.3048
    if not math.isfinite(number) or number <= 0 or number > maximum:
        return None
    return number


def parse_levels(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", str(value))
    if not match:
        return None
    number = float(match.group(1))
    return number if math.isfinite(number) and 0 < number <= LEVELS_MAX else None


def fallback_height(building_type: str) -> float:
    if building_type in {"apartments", "hotel", "office", "commercial"}:
        return 12.0
    if building_type in {"industrial", "warehouse", "retail"}:
        return 8.0
    if building_type in {"school", "hospital", "university", "college", "institutional"}:
        return 9.0
    return 6.0


def classify(tags: dict[str, str]) -> str:
    value = tags.get("building", "unknown").lower()
    known = {
        "residential", "commercial", "industrial", "retail", "apartments", "house",
        "school", "hospital", "warehouse", "university", "college", "hotel", "office",
    }
    return value if value in known else "other" if value not in {"yes", "unknown"} else "unknown"


def coordinates(geometry: object) -> list[list[list[float]]]:
    value = mapping(geometry)
    if value["type"] == "Polygon":
        return [[list(point) for point in ring] for ring in value["coordinates"]]
    if value["type"] == "MultiPolygon":
        return [[[list(point) for point in ring] for ring in polygon] for polygon in value["coordinates"]]
    raise ValueError(f"expected polygon geometry, got {value['type']}")


def project_geometry(geometry: object, transformer: Transformer) -> object:
    return transform(lambda x, y, z=None: transformer.transform(x, y), geometry)


def normalized_geometry(geometry: object, boundary: object) -> tuple[object | None, str]:
    if geometry.is_empty:
        return None, "rejected_empty"
    clipped = geometry.intersection(boundary)
    if clipped.is_empty:
        return None, "rejected_outside_boundary"
    if not clipped.is_valid:
        repaired = clipped.buffer(0)
        if repaired.is_empty or not repaired.is_valid:
            return None, "rejected_invalid_geometry"
        clipped = repaired
        status = "repaired"
    else:
        status = "direct"
    if clipped.geom_type not in {"Polygon", "MultiPolygon"}:
        return None, "rejected_non_polygon"
    return clipped, status


def normalized_line(geometry: object, boundary: object) -> object | None:
    clipped = geometry.intersection(boundary)
    if clipped.is_empty or clipped.geom_type not in {"LineString", "MultiLineString"}:
        return None
    return clipped


def line_coordinates(geometry: object) -> list:
    value = mapping(geometry)
    if value["type"] == "LineString":
        return [list(point) for point in value["coordinates"]]
    if value["type"] == "MultiLineString":
        return [[[point[0], point[1]] for point in line] for line in value["coordinates"]]
    raise ValueError(f"expected line geometry, got {value['type']}")


@dataclass(frozen=True)
class WayData:
    id: int
    tags: dict[str, str]
    points: list[tuple[float, float]]


@dataclass(frozen=True)
class MemberData:
    type: str
    ref: int
    role: str


@dataclass(frozen=True)
class RelationData:
    id: int
    tags: dict[str, str]
    members: list[MemberData]


def way_geometry(way: WayData) -> object | None:
    points = way.points
    if len(points) < 4 or points[0] != points[-1]:
        return None
    return Polygon(points)


def relation_geometry(relation: RelationData, ways: dict[int, WayData]) -> object | None:
    outer_lines: list[LineString] = []
    inner_lines: list[LineString] = []
    missing = False
    for member in relation.members:
        if member.type != "w":
            continue
        way = ways.get(member.ref)
        if way is None:
            missing = True
            continue
        points = way.points
        if len(points) < 2:
            missing = True
            continue
        (inner_lines if member.role == "inner" else outer_lines).append(LineString(points))
    if missing or not outer_lines:
        return None
    outers = list(polygonize(unary_union(outer_lines)))
    if not outers:
        return None
    geometry = unary_union(outers)
    inners = list(polygonize(unary_union(inner_lines))) if inner_lines else []
    if inners:
        geometry = geometry.difference(unary_union(inners))
    return geometry


@dataclass
class RawData:
    ways: dict[int, WayData]
    relations: list[RelationData]


class Collector(osmium.SimpleHandler):
    def __init__(self, bounds: tuple[float, float, float, float]) -> None:
        super().__init__()
        self.bounds = bounds
        self.ways: dict[int, WayData] = {}
        self.relations: list[RelationData] = []

    def _in_processing_bounds(self, way: object) -> bool:
        west, south, east, north = self.bounds
        return any(west <= lon <= east and south <= lat <= north for lon, lat in way)

    def way(self, way: object) -> None:
        points = [(node.lon, node.lat) for node in way.nodes if node.location.valid()]
        if self._in_processing_bounds(points):
            self.ways[way.id] = WayData(way.id, dict(way.tags), points)

    def relation(self, relation: object) -> None:
        if relation.tags.get("building") and relation.tags.get("type") == "multipolygon":
            self.relations.append(RelationData(relation.id, dict(relation.tags), [MemberData(member.type, member.ref, member.role) for member in relation.members]))


def height_for(tags: dict[str, str], building_type: str) -> tuple[float, str, str | None]:
    raw_height = tags.get("height")
    explicit = finite_number(raw_height, maximum=HEIGHT_MAX_M)
    if explicit is not None:
        return round(explicit, 3), "explicit", None
    raw_levels = tags.get("building:levels")
    levels = parse_levels(raw_levels)
    if levels is not None:
        return round(levels * FLOOR_HEIGHT_M, 3), "levels", None
    malformed = "height" if raw_height is not None else "levels" if raw_levels is not None else None
    return fallback_height(building_type), "fallback", malformed


def make_record(building_id: str, source_id: int, tags: dict[str, str], geometry: object, status: str, source_kind: str) -> dict:
    building_type = classify(tags)
    height_m, height_source, malformed = height_for(tags, building_type)
    local = project_geometry(geometry, WGS84_TO_UTM)
    origin_x, origin_y = WGS84_TO_UTM.transform(ORIGIN_LON, ORIGIN_LAT)
    local = transform(lambda x, y, z=None: (x - origin_x, y - origin_y), local)
    return {
        "building_id": building_id,
        "source": "osm",
        "source_id": str(source_id),
        "source_kind": source_kind,
        "geometry_wgs84": coordinates(geometry),
        "geometry_local_m": coordinates(local),
        "bounds_wgs84": [round(v, 7) for v in geometry.bounds],
        "bounds_local_m": [round(v, 3) for v in local.bounds],
        "height_m": height_m,
        "height_source": height_source,
        "building_levels": parse_levels(tags.get("building:levels")),
        "building_type": building_type,
        "original_building_tag": tags.get("building"),
        "geometry_status": status,
        "malformed_height_or_levels": malformed,
    }


def road_record(way: WayData, boundary: object) -> dict | None:
    points = way.points
    if len(points) < 2:
        return None
    geometry = normalized_line(LineString(points), boundary)
    if geometry is None:
        return None
    local = project_geometry(geometry, WGS84_TO_UTM)
    origin_x, origin_y = WGS84_TO_UTM.transform(ORIGIN_LON, ORIGIN_LAT)
    local = transform(lambda x, y, z=None: (x - origin_x, y - origin_y), local)
    tags = way.tags
    width = finite_number(tags.get("width"), maximum=100.0)
    return {
        "road_id": f"osm_way_{way.id}",
        "source": "osm",
        "source_id": str(way.id),
        "geometry_wgs84": line_coordinates(geometry),
        "geometry_local_m": line_coordinates(local),
        "bounds_wgs84": [round(v, 7) for v in geometry.bounds],
        "bounds_local_m": [round(v, 3) for v in local.bounds],
        "length_m": round(local.length, 3),
        "highway": tags.get("highway", "unknown"),
        "name": tags.get("name"),
        "width_m": round(width, 3) if width is not None else None,
        "width_source": "explicit" if width is not None else "missing",
        "lanes": tags.get("lanes"),
        "bridge": tags.get("bridge"),
        "tunnel": tags.get("tunnel"),
    }


def build(source: pathlib.Path, output: pathlib.Path) -> dict:
    boundary, bounds = boundary_geometry()
    west, south, east, north = bounds
    processing_bounds = (west - PROCESSING_BUFFER_DEG, south - PROCESSING_BUFFER_DEG, east + PROCESSING_BUFFER_DEG, north + PROCESSING_BUFFER_DEG)
    collector = Collector(processing_bounds)
    collector.apply_file(str(source), locations=True, idx="flex_mem")
    building_relations = {relation.id: relation for relation in collector.relations}
    buildings: list[dict] = []
    stats = Counter()
    used_relation_members: set[int] = set()
    for relation_id in sorted(building_relations):
        relation = building_relations[relation_id]
        geometry = relation_geometry(relation, collector.ways)
        if geometry is None:
            stats["rejected"] += 1
            stats["relation_rejections"] += 1
            stats["reject_relation_missing_members_or_invalid_ring"] += 1
            continue
        normalized, status = normalized_geometry(geometry, boundary)
        if normalized is None:
            stats["rejected"] += 1
            stats["relation_rejections"] += 1
            stats[f"reject_relation_{status}"] += 1
            continue
        buildings.append(make_record(f"osm_relation_{relation_id}", relation_id, dict(relation.tags), normalized, status, "relation"))
        stats["accepted_relations"] += 1
        stats[status] += 1
        used_relation_members.update(member.ref for member in relation.members if member.type == "w")
    for way_id in sorted(collector.ways):
        way = collector.ways[way_id]
        tags = dict(way.tags)
        if "building" not in tags or way_id in used_relation_members:
            if "building" in tags and way_id in used_relation_members:
                stats["duplicates_removed"] += 1
            continue
        geometry = way_geometry(way)
        if geometry is None:
            stats["rejected"] += 1
            stats["way_rejections"] += 1
            stats["reject_way_unclosed_or_degenerate"] += 1
            continue
        normalized, status = normalized_geometry(geometry, boundary)
        if normalized is None:
            stats["rejected"] += 1
            stats["way_rejections"] += 1
            stats[f"reject_way_{status}"] += 1
            continue
        buildings.append(make_record(f"osm_way_{way_id}", way_id, tags, normalized, status, "way"))
        stats["accepted_ways"] += 1
        stats[status] += 1
    roads = [record for way in collector.ways.values() if way.tags.get("highway") and (record := road_record(way, boundary))]
    buildings.sort(key=lambda record: record["building_id"])
    roads.sort(key=lambda record: record["road_id"])
    origin_x, origin_y = WGS84_TO_UTM.transform(ORIGIN_LON, ORIGIN_LAT)
    city = {
        "schema_version": "canonical-lahore-v1",
        "source": {"provider": "Geofabrik", "source": "OpenStreetMap", "license": "ODbL 1.0", "source_url": "https://download.geofabrik.de/asia/pakistan-latest.osm.pbf", "snapshot": "pakistan-latest through 2026-11-01T21:21:36Z", "boundary_source": "OSM relation 16117666", "processing_bounds": list(processing_bounds), "final_boundary": "scripts/sources/lahore_boundary.json"},
        "coordinate_system": {"source_crs": "EPSG:4326", "projected_crs": "EPSG:32643", "origin": {"lat": ORIGIN_LAT, "lon": ORIGIN_LON, "easting_m": round(origin_x, 3), "northing_m": round(origin_y, 3), "axes": "x east, y north"}},
        "height_rules": {"floor_height_m": FLOOR_HEIGHT_M, "max_explicit_height_m": HEIGHT_MAX_M, "max_levels": LEVELS_MAX, "fallback_by_type_m": {"apartments/commercial/hotel/office": 12.0, "industrial/warehouse/retail": 8.0, "school/hospital/university/college/institutional": 9.0, "other": 6.0}},
        "build_config": {"geometry_repair": "safe shapely buffer(0) only", "boundary_filter": "final polygon intersection", "canonical_format": "deterministically ordered JSON", "rendering_data": False},
        "bounds_wgs84": [round(v, 7) for v in boundary.bounds],
        "bounds_local_m": [round(v, 3) for v in transform(lambda x, y, z=None: (x - origin_x, y - origin_y), project_geometry(boundary, WGS84_TO_UTM)).bounds],
        "buildings": buildings,
        "roads": roads,
        "statistics": {**dict(stats), "canonical_buildings": len(buildings), "canonical_roads": len(roads), "building_height_sources": dict(Counter(record["height_source"] for record in buildings)), "malformed_height_or_levels": dict(Counter(record["malformed_height_or_levels"] for record in buildings if record["malformed_height_or_levels"])), "building_types": dict(Counter(record["building_type"] for record in buildings)), "road_classes": dict(Counter(record["highway"] for record in roads)), "road_width_sources": dict(Counter(record["width_source"] for record in roads)), "road_total_length_m": round(sum(record["length_m"] for record in roads), 3)},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(city, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    output.write_bytes(payload.encode("utf-8"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    stats_path = output.with_suffix(".stats.json")
    stats_path.write_bytes((json.dumps({"sha256": digest, "size_bytes": len(payload.encode()), "statistics": city["statistics"]}, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"output": str(output), "stats": str(stats_path), "sha256": digest, "size_bytes": len(payload.encode()), "statistics": city["statistics"]}, indent=2))
    return city


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("city-data/canonical/lahore.json"))
    args = parser.parse_args()
    build(args.source, args.output)


if __name__ == "__main__":
    main()
