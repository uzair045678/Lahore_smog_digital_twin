#!/usr/bin/env python
"""Build the Lahore greybox city base used by the web scene.

Inputs (build-time only):
  scripts/sources/lahore_boundary.json  Overpass relation geometry
  pipeline/config/stations.json         EPA station registry
  scripts/sources/lahore_roads.json     optional cached Overpass roads

Output:
  web/public/city/lahore.json
"""

import json
import pathlib
import os

ORIGIN_LAT = 31.5204
ORIGIN_LON = 74.3587
METERS_PER_DEG_LAT = 110540
METERS_PER_DEG_LON = 111320


def project(lat, lon):
    x = (lon - ORIGIN_LON) * METERS_PER_DEG_LON * _cos_lat(lat)
    y = (lat - ORIGIN_LAT) * METERS_PER_DEG_LAT
    return x, y


def _cos_lat(lat):
    import math
    return math.cos(lat * 3.141592653589793 / 180.0)


def _point_in_polygon(point, polygon):
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, (px, py) in enumerate(polygon):
        pj_x, pj_y = polygon[j]
        if ((py > y) != (pj_y > y)) and (x < (pj_x - px) * (y - py) / (pj_y - py) + px):
            inside = not inside
        j = i
    return inside


def _flatten_members(members):
    points = []
    for member in members:
        if member.get('role') == 'outer':
            points.extend([ (p['lat'], p['lon']) for p in member.get('geometry', [])])
    return points


def _simplify(points, max_points=180):
    if len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    out = [points[i] for i in range(0, len(points), step)]
    if out[0] != points[0]:
        out.insert(0, points[0])
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def build():
    source_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "sources" / "lahore_boundary.json"
    if not source_path.exists():
        raise FileNotFoundError("Run Overpass query and cache it in scripts/sources/lahore_boundary.json first.")
    boundary_raw = json.loads(source_path.read_text(encoding='utf-8'))
    members = boundary_raw.get('members', [])
    raw_points = _flatten_members(members)
    if not raw_points:
        raise ValueError("Boundary asset has no outer coordinates")
    simplified = _simplify(raw_points)

    lat_sum = sum(p[0] for p in simplified)
    lon_sum = sum(p[1] for p in simplified)
    centroid = (lat_sum / len(simplified), lon_sum / len(simplified))

    station_path = pathlib.Path(__file__).resolve().parents[1] / "pipeline" / "config" / "stations.json"
    stations_cfg = json.loads(station_path.read_text(encoding='utf-8'))['stations']
    station_points = []

    # Proper polygon in projected space
    polygon_projected = [project(lat, lon) for lat, lon in simplified]
    polygon_xy = [ (x, y) for x, y in polygon_projected ]

    station_data = []
    for station in stations_cfg:
        x, y = project(station['lat'], station['lon'])
        inside = _point_in_polygon((x, y), polygon_xy)
        station_data.append({
            "id": station["id"],
            "name": station["name"],
            "verified_at": station.get("verified_at"),
            "lat": station["lat"],
            "lon": station["lon"],
            "x": round(x, 2),
            "y": round(y, 2),
            "inside_boundary": inside,
            "verified": True,
        })

    roads_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "sources" / "lahore_roads.json"
    roads = []
    if roads_path.exists():
        roads_raw = json.loads(roads_path.read_text(encoding='utf-8'))
        for way in roads_raw.get('ways', []):
            geom = [(p['lat'], p['lon']) for p in way.get('geometry', [])]
            if len(geom) < 2:
                continue
            simplified_way = _simplify(geom, max_points=30)
            roads.append({
                "id": way.get('id'),
                "type": way.get('tags', {}).get('highway', 'unknown'),
                "coords": [ { "lat": p[0], "lon": p[1], "x": project(p[0], p[1])[0], "y": project(p[0], p[1])[1] } for p in simplified_way ],
            })

    city = {
        "coordinate_system": "local-meters",
        "origin": {
            "lat": ORIGIN_LAT,
            "lon": ORIGIN_LON,
            "z": 0,
            "description": "Equirectangular approximation centered near the Lahore city center; x east, y north in meters.",
        },
        "projection": {
            "type": "equirectangular",
            "cos_lat": round(_cos_lat(ORIGIN_LAT), 6),
            "lat_m_per_deg": METERS_PER_DEG_LAT,
            "lon_m_per_deg": METERS_PER_DEG_LON * _cos_lat(ORIGIN_LAT),
        },
        "boundary": [
            { "lat": lat, "lon": lon, "x": round(project(lat, lon)[0], 2), "y": round(project(lat, lon)[1], 2) }
            for lat, lon in simplified
        ],
        "boundary_point_count": len(raw_points),
        "boundary_simplified_count": len(simplified),
        "station_count": len(station_data),
        "stations": station_data,
        "roads": roads,
        "road_count": len(roads),
        "greybox_blocks": [],
        "sources": {
            "boundary": "OpenStreetMap relation 16117666 (Lahore district), fetched build-time only",
            "stations": "pipeline/config/stations.json (Punjab EPA)",
        },
        "notes": [
            "Projection uses a simple local equirectangular approximation for display. Precise GIS reprojection (if required) may later switch to pyproj.",
            "Missing buildings or simplified points are acceptable per PLAN section 7.",
        ],
    }

    out_dir = pathlib.Path(__file__).resolve().parents[1] / "web" / "public" / "city"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "lahore.json"
    out_path.write_text(json.dumps(city, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}")
    print("boundary", len(raw_points), "->", len(simplified), "stations", len(station_data), "roads", len(roads), "all_inside", all(s["inside_boundary"] for s in station_data))


if __name__ == "__main__":
    build()

