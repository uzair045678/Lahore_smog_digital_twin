"""Fetch AQICN (World Air Quality Index) data.

The API requires a token, stored as a GitHub secret (`AQICN_TOKEN`) and never
committed. Until a token is configured this module reports that no data is
available so the pipeline falls back to the labelled Open-Meteo model source.
AQICN labels its data as unvalidated.
"""

import os
from typing import Dict, List

AQICN_TOKEN_ENV = "AQICN_TOKEN"


def fetch_aqicn_data() -> List[Dict]:
    """Return AQICN pollutant readings, or an empty list without a token."""
    if not os.environ.get(AQICN_TOKEN_ENV):
        return []
    raise NotImplementedError(
        "AQICN token present but the AQICN request is not implemented yet; "
        "remove the token to fall back to the Open-Meteo model source."
    )
