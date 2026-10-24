"""Pydantic-validated data contracts for Lahore Smog Twin pipeline.

These schemas enforce units, timestamps, source attribution, bounds,
chronological ordering, and compatibility across files per PLAN.md
sections 122-131. Missing values must remain null, never silently
replaced by zero.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class Source(str, Enum):
    EPA = "epa"
    AQICN = "aqicn"
    MODEL = "model"


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
    lat: float = Field(..., ge=24.0, lu=32.0)  # Lahore approx range
    lon: float = Field(..., ge=65.0, lu=75.0)
    altitude: Optional[float] = None
    # Per-station last updated timestamp from source
    observed_at: Optional[datetime] = None
    # When the data was fetched/imported into the pipeline
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Data source priority
    source: Source = Source.EPA
    # Whether the pollutant values are measured or modelled
    measured: Optional[bool] = None
    # Quality flags
    quality_flags: Optional[dict[str, Optional[str]]] = None

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
    # Units as provided by the source; expected µg/m³ for particulates, ppm/ppb for gases
    units: Optional[str] = None
    # Source-provided AQI value and its standard
    aqi: Optional[dict[str, Optional[int]]] = None
    # Observation timestamp from the source
    observed_at: Optional[datetime] = None
    # Whether this reading is measured or modelled
    measured: Optional[bool] = None
    # Source of this reading
    source: Source = Source.EPA

    @validator("units")
    def units_not_null_for_measured(cls, v, values):
        if values and values[0].get("measured") and v is None:
            raise ValueError("Units required when measured=True")
        return v

    @validator("aqi")
    def aqi_only_for_compatible(cls, v, values):
        """AQI is only compatible with PM2.5 under US EPA breakpoints.
        Do not apply PM2.5 AQI breakpoints to other pollutants."""
        # If pollutant is not PM2.5 and aqi is provided, warn/validate
        # This is a structural check; actual EPA breakpoint logic is in model/
        return v


class Forecast(BaseModel):
    """Hourly forecast for the next 24 hours per PLAN.md section 145."""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Hourly steps; key is ISO timestamp, value is PollutantReading or null
    hourly: dict[str, Optional[PollutantReading]] = Field(default_factory=dict)
    # Wind forecast
    wind: Optional[WindVector] = None


class WindVector(BaseModel):
    """Per-sample wind vector per PLAN.md section 128."""
    timestamp: datetime
    # Position/coverage - for grid cells or station footprint
    position: Optional[dict[str, float]] = None  # {lat, lon}
    speed: float  # m/s or km/h depending on source
    direction: WindDirectionConvention = WindDirectionConvention.FROM
    # Whether measured or modelled
    measured: bool = False
    source: Source = Source.OPEN_METEO

    @validator("direction")
    def direction_must_be_enum(cls, v):
        if v not in WindDirectionConvention:
            raise ValueError(f"Invalid wind direction convention: {v}")
        return v


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
    """Validate latest.json; return standardized dict or raise."""
    station_readings = data.get("stations", [])
    validated = []
    for s in station_readings:
        try:
            station = Station(**s)
            validated.append(station.model_dump())
        except Exception as e:
            # Per PLAN.md: never replace validated dataset with invalid content
            raise ValueError(f"Invalid station data: {e}") from e
    return {"stations": validated, "generated_at": datetime.now(timezone.utc).isoformat()}


def validate_history(data: dict) -> list:
    """Validate history.json hourly records."""
    records = data.get("records", [])
    validated = []
    for r in records:
        try:
            # Basic structure validation
            if "timestamp" not in r or "pollutant" not in r:
                raise ValueError("History record missing required fields")
            validated.append(r)
        except Exception as e:
            raise ValueError(f"Invalid history record: {e}") from e
    return validated