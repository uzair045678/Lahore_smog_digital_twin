"""Fetch Open-Meteo wind and modelled air quality.

Open-Meteo values are CAMS model estimates, never measurements. They fill
wind coverage (EPA wind units are unverified) and act as the fallback source
when EPA is unavailable. Attribution: CC BY 4.0, non-commercial use.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import httpx

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 30.0
# Open-Meteo returns naive local times when `timezone` is set; Pakistan has no
# DST, so the offset is fixed.
LOCAL_OFFSET = "+05:00"


def _stamp(value: str) -> str:
    """Attach the Pakistan offset to a naive Open-Meteo timestamp."""
    return value if value.endswith(("Z", "+05:00")) else value + LOCAL_OFFSET

POLLUTANT_KEYS = {
    "pm25": "pm2_5",
    "pm10": "pm10",
    "co": "carbon_monoxide",
    "no2": "nitrogen_dioxide",
    "so2": "sulphur_dioxide",
    "o3": "ozone",
}
POLLUTANT_UNITS = {
    "pm25": "µg/m³",
    "pm10": "µg/m³",
    "co": "µg/m³",
    "no2": "µg/m³",
    "so2": "µg/m³",
    "o3": "µg/m³",
}

# Coarse grid over the Lahore extent for the wind field.
LAHORE_LATS = [31.36, 31.52, 31.64]
LAHORE_LONS = [74.20, 74.36, 74.55]


def _hourly(response: httpx.Response) -> Dict:
    response.raise_for_status()
    return response.json().get("hourly", {})


def fetch_wind_grid(
    points: Optional[List[tuple]] = None,
    past_days: int = 2,
    forecast_days: int = 1,
) -> List[Dict]:
    """Return hourly wind samples for a spatial grid of points.

    `points` is a list of (lat, lon) tuples. One request fetches the whole
    grid. Speed is in m/s, direction is meteorological ("from").
    """
    if not points:
        points = [
            (lat, lon)
            for lat in LAHORE_LATS
            for lon in LAHORE_LONS
        ]
    params = {
        "latitude": ",".join(str(p[0]) for p in points),
        "longitude": ",".join(str(p[1]) for p in points),
        "hourly": "wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": "Asia/Karachi",
    }
    response = httpx.get(WEATHER_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    grids = payload if isinstance(payload, list) else [payload]

    samples: List[Dict] = []
    for grid in grids:
        hourly = grid.get("hourly", {})
        times = hourly.get("time", [])
        speeds = hourly.get("wind_speed_10m", [])
        directions = hourly.get("wind_direction_10m", [])
        position = {"lat": grid.get("latitude"), "lon": grid.get("longitude")}
        for i, timestamp in enumerate(times):
            speed = speeds[i] if i < len(speeds) else None
            if speed is None:
                continue
            samples.append(
                {
                    "timestamp": _stamp(timestamp),
                    "position": position,
                    "coverage": "grid",
                    "speed": speed,
                    "units": "m/s",
                    "direction": "from",
                    "direction_degrees": directions[i] if i < len(directions) else None,
                    "measured": False,
                    "source": "open_meteo",
                }
            )
    return samples


def fetch_wind_data(
    lat: float = 31.5204,
    lon: float = 74.3167,
    past_days: int = 2,
    forecast_days: int = 2,
) -> List[Dict]:
    """Return hourly wind samples (speed in m/s, direction from)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": "Asia/Karachi",
    }
    data = _hourly(httpx.get(WEATHER_URL, params=params, timeout=TIMEOUT))
    times = data.get("time", [])
    speeds = data.get("wind_speed_10m", [])
    directions = data.get("wind_direction_10m", [])
    samples = []
    for i, timestamp in enumerate(times):
        speed = speeds[i] if i < len(speeds) else None
        if speed is None:
            continue
        samples.append(
            {
                    "timestamp": _stamp(timestamp),
                "position": {"lat": lat, "lon": lon},
                "coverage": "station",
                "speed": speed,
                "units": "m/s",
                "direction": "from",
                "direction_degrees": directions[i] if i < len(directions) else None,
                "measured": False,
                "source": "open_meteo",
            }
        )
    return samples


def fetch_air_quality(
    lat: float = 31.5204,
    lon: float = 74.3167,
    past_days: int = 2,
    forecast_days: int = 2,
) -> List[Dict]:
    """Return hourly modelled pollutant samples for one point."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(POLLUTANT_KEYS.values()),
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": "Asia/Karachi",
    }
    data = _hourly(httpx.get(AIR_QUALITY_URL, params=params, timeout=TIMEOUT))
    times = data.get("time", [])
    samples = []
    for i, timestamp in enumerate(times):
        pollutants = {}
        for name, key in POLLUTANT_KEYS.items():
            series = data.get(key, [])
            value = series[i] if i < len(series) else None
            pollutants[name] = {
                "concentration": value,
                "units": POLLUTANT_UNITS[name],
                "measured": False,
                "source": "open_meteo",
            }
        samples.append({"timestamp": timestamp, "pollutants": pollutants})
    return samples


def fetch_city_fallback(
    lat: float = 31.5204,
    lon: float = 74.3167,
) -> Dict:
    """Return a single modelled city-average reading used when EPA fails."""
    samples = fetch_air_quality(lat, lon, past_days=0, forecast_days=1)
    if not samples:
        raise RuntimeError("Open-Meteo returned no data")
    return {"timestamp": samples[0]["timestamp"], "pollutants": samples[0]["pollutants"]}
