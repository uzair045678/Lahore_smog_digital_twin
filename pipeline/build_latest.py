"""Build `latest.json` from fetched data.

This script demonstrates the construction of the output snapshot using
the schemas defined in ``schema.py``. Replace stub datasets with real
calls from ``fetch_epa.py``/``fetch_openmeteo.py``/``fetch_aqicn.py``.
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict

from .schema import Station, PollutantReading, Forecast, WindVector, Manifest
from .config import stations

MAX_STATIONS = 10


def assemble_latest() -> Dict:
    # Load station config
    station_cfg = stations.load()
    stations_list = []

    # Stub loop – replace with real fetch logic
    for cfg in station_cfg["stations"][:MAX_STATIONS]:
        station = Station(
            id=cfg["id"],
            name=cfg["name"],
            lat=cfg["lat"],
            lon=cfg["lon"],
        )
        # Add placeholder pollutant readings
        station_readings = [
            PollutantReading(
                pollutant="pm25",
                concentration=35.0,
                units="µg/m³",
                observed_at=datetime.now(timezone.utc),
                measured=True,
                source=station.source,
            )
        ]
        stations_list.append(
            {
                "station": station.model_dump(),
                "readings": [r.model_dump() for r in station_readings],
            }
        )

    latest = {
        "schema_version": "1.0",
        "data_version": datetime.now(timezone.utc).isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stations": [s["station"] for s in stations_list],
        "measurements": [s["readings"] for s in stations_list],
    }
    return latest


def write_json(data: Dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # Create output directory if needed
    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)
    latest_path = os.path.join(out_dir, "latest.json")
    manifest_path = os.path.join(out_dir, "manifest.json")

    latest = assemble_latest()
    write_json(latest, latest_path)

    # Output a simple manifest
    manifest = Manifest(
        schema_version="1.0",
        data_version=latest["data_version"],
        published_at=datetime.now(timezone.utc),
        latest_url=f"{latest_path}",
        history_url="history.json",  # placeholder
    )
    write_json(manifest.model_dump(), manifest_path)

    print(f"Wrote {latest_path} and {manifest_path}")
