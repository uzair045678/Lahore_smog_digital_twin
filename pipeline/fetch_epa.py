"""Fetch live readings from the Punjab EPA Lahore dashboard.

There is no public JSON API: the dashboard's `/api/stations/{id}/current`
route returns 404. Current readings are embedded in the server-rendered page
as a Livewire snapshot (`wire:snapshot`) that contains JSON, which this module
extracts.

Units were cross-checked against Open-Meteo (CAMS) values for the same hour
and coordinates (NO2 79.16 EPA vs 73.8 µg/m³ OM; CO 1.69 EPA vs 2.58 mg/m³
OM), so EPA gases/particulates are µg/m³ and CO is mg/m³.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, Iterator, List, Optional

import httpx

EPA_URL = "https://aqi.punjab.gov.pk/lahore"
USER_AGENT = (
    "LahoreSmogTwin/0.1 (educational demo; "
    "+https://github.com/uzair045678/Lahore_smog_digital_twin)"
)
SNAPSHOT_RE = re.compile(r'wire:snapshot="(.*?)"', re.S)

POLLUTANT_UNITS = {
    "pm25": "µg/m³",
    "pm10": "µg/m³",
    "no2": "µg/m³",
    "so2": "µg/m³",
    "o3": "µg/m³",
    "co": "mg/m³",
}


def _walk(node: Any) -> Iterator[Dict]:
    """Yield every dict inside a nested JSON structure."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _iso(value: Any) -> Optional[str]:
    """Livewire encodes timestamps as ["iso", {...}]; return the ISO part."""
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, str):
        return value
    return None


def _number(value: Any) -> Optional[float]:
    """EPA sends pollutant values as strings; '' and null mean missing."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _flags(value: Any) -> Dict[str, str]:
    """Livewire sends pollutant flags as a list of dicts; flatten to {name: flag}."""
    flags: Dict[str, str] = {}
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                for name, flag in item.items():
                    if name != "s":
                        flags[name] = flag
    return flags


def parse_snapshot(page_html: str) -> Dict:
    """Return the decoded Livewire snapshot JSON from the dashboard HTML."""
    match = SNAPSHOT_RE.search(page_html)
    if not match:
        raise ValueError("Livewire snapshot not found in page HTML")
    return json.loads(html.unescape(match.group(1)))


def extract_stations(snapshot: Dict) -> List[Dict]:
    """Return current readings for every station in the snapshot.

    The snapshot repeats the station list in several places, so stations are
    de-duplicated by their EPA station id.
    """
    stations: Dict[str, Dict] = {}
    for node in _walk(snapshot):
        if "station_id" not in node or "station_name" not in node:
            continue
        station_id = str(node["station_id"])
        if station_id in stations:
            continue
        band = next(
            (b for b in node.get("aqi_range", []) if isinstance(b, dict) and "range" in b),
            {},
        )
        stations[station_id] = {
                "id": str(node["station_id"]),
                "name": node["station_name"],
                "district": node.get("district"),
                "lat": _number(node.get("latitude")),
                "lon": _number(node.get("longitude")),
                "aqi": node.get("aqi"),
                "aqi_standard": "punjab_epa_bands",
                "aqi_category": band.get("health_index"),
                "aqi_range": band.get("range"),
                "major_pollutant": node.get("major_pollutant"),
                "pollutants": {
                    key: _number(node.get(key))
                    for key in ("pm25", "pm10", "no2", "so2", "o3", "co")
                },
                "pollutant_flags": _flags(node.get("pollutant_flags")),
                "temperature": _number(node.get("temperature")),
                "humidity": _number(node.get("humidity")),
                "wind_speed": _number(node.get("wind_speed")),
                "wind_direction": _number(node.get("wind_direction")),
                "observed_at": _iso(node.get("timestamp")),
                "source": "epa",
                "measured": True,
            }
    return list(stations.values())


def extract_history(snapshot: Dict) -> List[Dict]:
    """Return the city-average hourly history records (oldest first)."""
    records = []
    for node in _walk(snapshot):
        if "station_names" not in node or "datetime" not in node:
            continue
        records.append(
            {
                "timestamp": _iso(node.get("datetime")),
                "aqi": node.get("aqi"),
                "aqi_range": next(
                    (
                        b.get("range")
                        for b in node.get("aqi_range", [])
                        if isinstance(b, dict) and "range" in b
                    ),
                    None,
                ),
                "station_count": node.get("station_count"),
                "pollutants": {
                    key: _number(node.get(key))
                    for key in ("pm25", "pm10", "no2", "so2", "o3", "co")
                },
                "temperature": _number(node.get("temperature")),
                "humidity": _number(node.get("humidity")),
                "wind_speed": _number(node.get("wind_speed")),
                "wind_direction": _number(node.get("wind_direction")),
                "source": "epa",
                "measured": True,
            }
        )
    records.sort(key=lambda r: r["timestamp"] or "")
    return records


def extract_forecast(snapshot: Dict) -> List[Dict]:
    """Return the next-hours city forecast (oldest first)."""
    forecast = []
    for node in _walk(snapshot):
        if "datetime" not in node or "aqi" not in node or "precipitation_probability" not in node:
            continue
        forecast.append(
            {
                "timestamp": _iso(node.get("datetime")),
                "aqi": node.get("aqi"),
                "aqi_category": node.get("aqi_health_index"),
                "temperature": _number(node.get("temperature")),
                "wind_speed": _number(node.get("wind_speed")),
                "wind_direction": _number(node.get("wind_direction")),
                "precipitation_probability": node.get("precipitation_probability"),
                "source": "epa",
                "measured": False,
            }
        )
    forecast.sort(key=lambda f: f["timestamp"] or "")
    return forecast


def fetch_lahore(url: str = EPA_URL, timeout: float = 30.0) -> Dict:
    """Fetch and parse the EPA Lahore dashboard.

    Returns a dict with `stations`, `history`, `forecast` and `city` keys.
    """
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()
    snapshot = parse_snapshot(response.text)
    page = snapshot.get("data", {}).get("pageData", [{}])[0]
    city_data = (page.get("lahoreData") or [{}])[0]
    city = {
        "district": city_data.get("district"),
        "average_aqi": city_data.get("average_aqi"),
        "yesterday_aqi": city_data.get("yesterday_aqi"),
        "station_count": city_data.get("station_count"),
        "observed_at": _iso(city_data.get("last_updated")),
    }
    return {
        "city": city,
        "stations": extract_stations(snapshot),
        "history": extract_history(snapshot),
        "forecast": extract_forecast(snapshot),
    }


def fetch_station_data() -> List[Dict]:
    """Return current readings for every EPA station."""
    return fetch_lahore()["stations"]
