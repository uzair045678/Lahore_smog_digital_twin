"""Utility functions for pipeline configuration.

Currently provides a ``load`` function to read ``stations.json``.
"""

import json
import pathlib

DEFAULT_STATIONS_FILE = "stations.json"


def load(stations_file: str | None = None) -> dict:
    """Return the stations configuration dictionary.

    Parameters
    ----------
    stations_file:
        Optional path relative to the ``config`` directory.
        Defaults to :data:`DEFAULT_STATIONS_FILE`.
    """
    station_path = pathlib.Path(__file__).parent / (stations_file or DEFAULT_STATIONS_FILE)
    with open(station_path, "r", encoding="utf-8") as fh:
        return json.load(fh)

__all__ = ["load"]
