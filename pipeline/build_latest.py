"""Build `latest.json`, `history.json` and `manifest.json` from live sources.

Source priority per PLAN.md section 4.5: EPA first, then AQICN (token, not
configured yet), then explicitly labelled Open-Meteo model values. Missing
values stay null; they are never replaced by zero.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List

from . import fetch_epa, fetch_openmeteo
from .schema import (
    Manifest,
    PollutantReading,
    Source,
    Station,
    WindVector,
    validate_history,
    validate_latest,
    validate_manifest,
)

SCHEMA_VERSION = "1.0"
CITY_CENTER = (31.5204, 74.3167)


def _readings(station: Dict) -> List[Dict]:
    """Convert a station's pollutant values into validated readings."""
    readings = []
    for pollutant, concentration in station["pollutants"].items():
        reading = PollutantReading(
            pollutant=pollutant,
            concentration=concentration,
            units=fetch_epa.POLLUTANT_UNITS[pollutant],
            measured=station["measured"],
            observed_at=station["observed_at"],
            source=Source(station["source"]),
        )
        readings.append(reading.model_dump(mode="json"))
    return readings


def _stations(raw_stations: List[Dict], fetched_at: datetime) -> List[Dict]:
    stations = []
    for raw in raw_stations:
        station = Station(
            id=raw["id"],
            name=raw["name"],
            lat=raw["lat"],
            lon=raw["lon"],
            observed_at=raw["observed_at"],
            fetched_at=fetched_at,
            source=Source(raw["source"]),
            measured=raw["measured"],
            aqi=raw["aqi"],
            aqi_standard=raw["aqi_standard"],
            aqi_category=raw["aqi_category"],
            aqi_range=raw["aqi_range"],
            major_pollutant=raw["major_pollutant"],
            temperature=raw["temperature"],
            humidity=raw["humidity"],
            quality_flags={"pollutant_flags": raw["pollutant_flags"]},
        )
        stations.append(station.model_dump(mode="json"))
    return stations


def _wind() -> List[Dict]:
    """Open-Meteo wind on a coarse Lahore grid; EPA wind units are unverified.

    Limited to the timeline window in PLAN.md section 6.3 (past 48 h to
    next 24 h).
    """
    now = datetime.now(timezone.utc)
    window_start = now.timestamp() - 48 * 3600
    window_end = now.timestamp() + 24 * 3600
    samples: List[Dict] = []
    for sample in fetch_openmeteo.fetch_wind_grid():
        timestamp = datetime.fromisoformat(sample["timestamp"]).timestamp()
        if not (window_start <= timestamp <= window_end):
            continue
        samples.append(WindVector(**sample).model_dump(mode="json"))
    return samples


def assemble_latest() -> Dict:
    """Fetch sources and return the full `latest.json` payload."""
    fetched_at = datetime.now(timezone.utc)
    try:
        epa = fetch_epa.fetch_lahore()
        raw_stations = epa["stations"]
        hourly_forecast = {
            entry["timestamp"]: entry
            for entry in epa["forecast"]
            if entry["timestamp"]
        }
        source_health = {
            "epa": {
                "status": "ok",
                "stations": len(raw_stations),
                "observed_at": epa["city"]["observed_at"],
            }
        }
    except Exception as exc:  # fall back to the labelled model source
        fallback = fetch_openmeteo.fetch_city_fallback(*CITY_CENTER)
        raw_stations = [
            {
                "id": "city-center",
                "name": "Lahore city center (modelled)",
                "lat": CITY_CENTER[0],
                "lon": CITY_CENTER[1],
                "aqi": None,
                "aqi_standard": None,
                "aqi_category": None,
                "aqi_range": None,
                "major_pollutant": None,
                "temperature": None,
                "humidity": None,
                "pollutants": {
                    name: values["concentration"]
                    for name, values in fallback["pollutants"].items()
                },
                "pollutant_flags": None,
                "observed_at": fallback["timestamp"],
                "source": "open_meteo",
                "measured": False,
            }
        ]
        source_health = {"epa": {"status": "error", "error": str(exc)}}
        hourly_forecast = {}

    stations = _stations(raw_stations, fetched_at)
    measurements = {raw["id"]: _readings(raw) for raw in raw_stations}

    try:
        wind = _wind()
    except Exception as exc:
        wind = []
        source_health["open_meteo"] = {"status": "error", "error": str(exc)}

    latest = {
        "schema_version": SCHEMA_VERSION,
        "data_version": fetched_at.strftime("%Y-%m-%dT%H-%M-%SZ"),
        "generated_at": fetched_at.isoformat(),
        "city": epa["city"] if source_health.get("epa", {}).get("status") == "ok" else {},
        "stations": stations,
        "measurements": measurements,
        "forecast": {"hourly": hourly_forecast, "wind": wind},
        "source_health": source_health,
    }
    return validate_latest(latest)


def assemble_history() -> Dict:
    """Return the `history.json` payload (48 h of city-average EPA records)."""
    fetched_at = datetime.now(timezone.utc)
    try:
        epa = fetch_epa.fetch_lahore()
        records = epa["history"][-48:]
        status = "ok"
    except Exception as exc:
        records = []
        status = f"error: {exc}"
    history = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": fetched_at.isoformat(),
        "records": records,
        "source_health": {"epa": {"status": status}},
    }
    validate_history(history)
    return history


def write_json(data: Dict, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def main() -> None:
    out_dir = os.environ.get("SMOG_OUT_DIR", "out")
    latest_path = os.path.join(out_dir, "latest.json")
    history_path = os.path.join(out_dir, "history.json")
    manifest_path = os.path.join(out_dir, "manifest.json")

    latest = assemble_latest()
    write_json(latest, latest_path)

    history = assemble_history()
    write_json(history, history_path)

    manifest = Manifest(
        schema_version=SCHEMA_VERSION,
        data_version=latest["data_version"],
        published_at=datetime.now(timezone.utc),
        latest_url="latest.json",
        history_url="history.json",
    )
    write_json(validate_manifest(manifest.model_dump(mode="json")).model_dump(mode="json"), manifest_path)

    print(f"Wrote {latest_path}, {history_path} and {manifest_path}")


if __name__ == "__main__":
    main()
