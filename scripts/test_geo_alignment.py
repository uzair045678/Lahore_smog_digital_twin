import json, math, sys

sys.stdout.reconfigure(encoding='utf-8')

root = __import__('pathlib').Path(__file__).resolve().parents[1]
city = json.loads((root / "web" / "public" / "city" / "lahore.json").read_text(encoding='utf-8'))
boundary = city["boundary"]
assert len(boundary) > 50, len(boundary)
assert city["station_count"] == 11
for station in city["stations"]:
    assert station["inside_boundary"] is True, station
    xinv = station["x"] / max(1, 111320 * math.cos(31.5204 * math.pi / 180))
    yinv = station["y"] / 110540
    lon = xinv + city["origin"]["lon"]
    lat = yinv + city["origin"]["lat"]
    assert abs(lat - station["lat"]) < 0.1, station
    assert abs(lon - station["lon"]) < 0.1, station

print("PASS: city geometry built from OSM relation", city["boundary_point_count"], "->", len(boundary), "points; stations:", len(city["stations"]), "all inside")
