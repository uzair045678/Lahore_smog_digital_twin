import json
from collections import Counter
from pathlib import Path
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
comparison = json.loads((ROOT / "out/overture-map4lb/comparison.json").read_text(encoding="utf-8"))
context = json.loads((ROOT / "out/overture-map4lb/osm_context.json").read_text(encoding="utf-8"))
project = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
origin = (439112.027, 3487455.809)


def local_position(element):
    if "lat" in element:
        lon, lat = element["lon"], element["lat"]
    elif "center" in element:
        lon, lat = element["center"]["lon"], element["center"]["lat"]
    else:
        return None
    x, y = project.transform(lon, lat)
    return x - origin[0], y - origin[1]


def category(tags):
    value = tags.get("landuse") or tags.get("aeroway") or tags.get("railway") or tags.get("leisure") or tags.get("amenity")
    if value in {"residential", "commercial", "retail", "industrial", "education", "institutional", "school", "college", "university", "hospital", "clinic", "office"}:
        return "developed"
    if value in {"park", "recreation_ground", "pitch", "garden", "cemetery", "farmland", "farmyard", "forest", "grass", "meadow", "vacant", "construction", "aerodrome", "runway", "taxiway", "rail", "railway", "yard"}:
        return "open"
    return "unknown"


elements = []
for element in context.get("elements", []):
    position = local_position(element)
    if position:
        elements.append((position, category(element.get("tags", {})), element.get("tags", {})))


def classify(item):
    west, south, east, north = item["local_bounds_m"]
    matches = [entry for entry in elements if west <= entry[0][0] < east and south <= entry[0][1] < north]
    counts = Counter(entry[1] for entry in matches)
    if counts["developed"] and counts["open"]:
        context_name = "mixed"
    elif counts["developed"]:
        context_name = "likely developed"
    elif counts["open"]:
        context_name = "likely open"
    else:
        context_name = "unknown"
    credible = item["credible_overture_only"]
    return {"grid": item["grid"], "local_bounds_m": item["local_bounds_m"], "context": context_name, "context_tags": sorted({key + "=" + value for _, _, tags in matches for key, value in tags.items() if key in {"landuse", "aeroway", "railway", "leisure", "amenity"}})[:20], "credible_overture_only": credible, "likely_developed": credible if context_name == "likely developed" else 0, "likely_open": credible if context_name == "likely open" else 0, "unknown": credible if context_name in {"mixed", "unknown"} else 0, "obvious_false_positives": 0}


classified = [classify(item) for item in comparison["all_deficient_cells"]]
result = {"schema_version": "low-pilot-context-v1", "method": "OSM Overpass tags assigned by 500m deficient-cell center; unknown preserved", "cells": classified, "summary": {"likely_developed_cells": sum(item["context"] == "likely developed" for item in classified), "likely_open_cells": sum(item["context"] == "likely open" for item in classified), "mixed_cells": sum(item["context"] == "mixed" for item in classified), "unknown_cells": sum(item["context"] == "unknown" for item in classified), "credible_total": sum(item["credible_overture_only"] for item in classified), "likely_developed_candidates": sum(item["likely_developed"] for item in classified), "likely_open_candidates": sum(item["likely_open"] for item in classified), "unknown_candidates": sum(item["unknown"] for item in classified), "obvious_false_positives": 0}}
result["required_five"] = [next(item for item in classified if item["grid"] == grid) for grid in ([7, 8], [0, 5], [12, 0], [13, 7], [1, 2])]
Path(ROOT / "out/overture-map4lb/context_classification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"summary": result["summary"], "required_five": result["required_five"]}, indent=2))
