"""Fetch Open‑Meteo data.

This module provides a stub that returns sample data in the
`pipeline.schema.WindVector` format. Replace with a real `httpx`
request once the Open‑Meteo API is confirmed.
"""

from typing import List, Dict


def fetch_wind_data() -> List[Dict]:
    """Return a list of wind dicts.

    Sample output format:
    {
        "timestamp": "2026-10-24T12:00:00Z",
        "lat": 31.5,
        "lon": 74.3,
        "speed": 3.2,
        "direction": "from",
        "measured": False,
        "source": "open_meteo"
    }
    """
    # TODO: implement actual Open‑Meteo API call
    return []
