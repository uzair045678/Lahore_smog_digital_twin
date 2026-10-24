"""Pydantic-validated data contracts for Lahore Smog Twin pipeline.

These schemas enforce units, timestamps, source attribution, bounds and
cross-field compatibility per PLAN.md sections 122-131. Missing values must
remain null, never silently replaced by zero.

Field order matters: in Pydantic v2 a field validator only sees fields
declared before it, so `measured` must precede `units`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


class Source(str, Enum):
    EPA = "epa"
    AQICN = "aqicn"
    MODEL = "model"
    OPEN_METEO = "open_meteo"


class MeasurementType(str, Enum):
    MEASURED = "measured"
    MODELLED = "modelled"


class Pollutant(str, Enum):
    PM25 = "pm25"
    PM10 = "pm10"
    CO = "co"
    SO2 = "so2"
    NO2 = "no2"
    O3 = "o3"


class WindDirectionConvention(str, Enum):
    FROM = "from"  # meteorological: direction the wind is coming FROM
    TOWARD = "toward"  # vector: direction the wind is pointing TO


class Station(BaseModel):
    id: str
    name: str
    lat: float = Field(..., ge=24.0, le=32.0)  # Lahore approx range
    lon: float = Field(..., ge=65.0, le=75.0)
    altitude: Optional[float] = None
    # Per-station last updated timestamp from source
    observed_at: Optional[datetime] = None
    # When the data was fetched/imported into the pipeline
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Data source priority
    source: Source = Source.EPA
    # Whether the pollutant values are measured or modelled
    measured: Optional[bool] = None
    # Source-provided AQI (station level, not per pollutant) and its band
    aqi: Optional[int] = None
    aqi_standard: Optional[str] = None
    aqi_category: Optional[str] = None
    aqi_range: Optional[str] = None
    major_pollutant: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    # Quality flags
    quality_flags: Optional[dict[str, Any]] = None

    @validator("lat")
    def lat_range(cls, v):
        if not (24.0 <= v <= 32.0):
            raise ValueError("Latitude out of Lahore region range")
        return v

    @validator("lon")
    def lon_range(cls, v):
        if not (65.0 <= v <= 75.0):
            raise ValueError("Longitude out of Lahore region range")
        return v


class PollutantReading(BaseModel):
    pollutant: Pollutant
    # Source-provided concentration value and units
    concentration: Optional[float] = None
    # Whether this reading is measured or modelled (declared before units so
    # the units validator can see it)
    measured: Optional[bool] = None
    # Units as provided by the source; expected µg/m³ for particulates and
    # most gases, mg/m³ for CO
    units: Optional[str] = None
    # Observation timestamp from the source
    observed_at: Optional[datetime] = None
    # Source of this reading
    source: Source = Source.EPA

    @validator("units")
    def units_not_null_for_measured(cls, v, values):
        if values.get("measured") and v is None:
            raise ValueError("Units required when measured=True")
        return v


class WindVector(BaseModel):
    """Per-sample wind vector per PLAN.md section 128."""

    timestamp: datetime
    # Position/coverage - for grid cells or station footprint
    position: Optional[dict[str, float]] = None  # {lat, lon}
    # How the sample covers space: "grid" for a spatial grid point,
    # "station" for a single monitoring station
    coverage: str = "grid"
    speed: float  # m/s or km/h depending on source
    units: str = "m/s"
    direction: WindDirectionConvention = WindDirectionConvention.FROM
    direction_degrees: Optional[float] = None
    # Whether measured or modelled
    measured: bool = False
    source: Source = Source.OPEN_METEO

    @validator("direction")
    def direction_must_be_enum(cls, v):
        if v not in WindDirectionConvention:
            raise ValueError(f"Invalid wind direction convention: {v}")
        return v


class Forecast(BaseModel):
    """Hourly forecast for the next 24 hours per PLAN.md section 145."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Hourly steps; key is ISO timestamp, value is PollutantReading or null
    hourly: dict[str, Optional[PollutantReading]] = Field(default_factory=dict)
    # Wind forecast
    wind: list[WindVector] = Field(default_factory=list)


class Manifest(BaseModel):
    """manifest.json per PLAN.md section 125-126."""

    schema_version: str = "1.0"
    data_version: str
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Immutable URLs/paths to latest and history snapshots
    latest_url: str
    history_url: str


class SourceHealth(BaseModel):
    """Per-source health status for PLAN.md section 128."""

    epa: Optional[dict] = None
    aqicn: Optional[dict] = None
    open_meteo: Optional[dict] = None
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Validation helpers


def validate_manifest(data: dict) -> Manifest:
    """Validate manifest.json contents."""
    return Manifest(**data)


def validate_latest(data: dict) -> dict:
    """Validate latest.json; return the data unchanged if it is valid."""
    for s in data.get("stations", []):
        try:
            Station(**s)
        except Exception as e:
            # Per PLAN.md: never replace validated dataset with invalid content
            raise ValueError(f"Invalid station data: {e}") from e
    for readings in data.get("measurements", {}).values():
        for r in readings:
            try:
                PollutantReading(**r)
            except Exception as e:
                raise ValueError(f"Invalid reading data: {e}") from e
    for w in data.get("forecast", {}).get("wind", []):
        try:
            WindVector(**w)
        except Exception as e:
            raise ValueError(f"Invalid wind data: {e}") from e
    return data


def validate_history(data: dict) -> list:
    """Validate history.json hourly records."""
    records = data.get("records", [])
    validated = []
    for r in records:
        try:
            if "timestamp" not in r or "pollutants" not in r:
                raise ValueError("History record missing required fields")
            validated.append(r)
        except Exception as e:
            raise ValueError(f"Invalid history record: {e}") from e
    return validated
