"""Fetch AQICN (World Air Quality Index) data.

The actual API requires a token; store it as a GitHub Secret.
Return the data in the format expected by `pipeline.schema.PollutantReading`.
"""

from typing import List, Dict


def fetch_aqicn_data() -> List[Dict]:
    """Return a list of AQICN pollutant readings.
    """
    # TODO: implement HTTP request with token
    return []
