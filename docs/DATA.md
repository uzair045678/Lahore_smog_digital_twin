# Data sources and processing

## Punjab EPA

- Page: `https://aqi.punjab.gov.pk/lahore`
- robots.txt permits crawling (`Disallow:` blank). No documented JSON API found; `/api/stations/{id}/current` returns 404.
- Sensor readings are parsed from the embedded Livewire snapshot (`wire:snapshot`)
- Fetch rate: at most once per hour, honest User-Agent (see `pipeline/fetch_epa.py`)
- Per-station readings retain their observed timestamp; history is 7 days city-average
- AQI bands follow Punjab EPA's published table (0-50, 51-100, ..., 401-500). The label for 51-100 is “Satisfactory” rather than EPA “Moderate”.
- Wind is reported in the feed but treated as unverified; Open-Meteo provides the spatial grid for the 3D scene.

## Open-Meteo

- Air Quality API: PM10, PM2.5, NO2, O3, SO2 via CAMS, plus forecast and past history
- Weather API: hourly wind speed/direction at 10 m (spatial grid over Lahore)
- values are modelled, not measured, and labelled as such in the UI
- License: CC BY 4.0, non-commercial; attribution displayed in UI and footer

## Fallback

- AQICN token optional; currently not configured in this repository. If enabled, AQICN data should be labelled unvalidated.

## Unit conventions

- PM2.5, PM10, NO2, SO2, O3: µg/m³
- CO: mg/m³ (verified against Open-Meteo’s mg/m³ outputs, but still clearly labelled in UI)

## City geometry

- Lahore district boundary: OpenStreetMap relation 16117666, boundary fetched at build time via Overpass and cached in `scripts/sources/lahore_boundary.json`.
- Stations: Punjab EPA feed lat/lon.
- Coordinates projected to local meters with an equirectangular approximation centered near Lahore city centre.

## Data branch layout

- `manifest.json` at branch root
- `snapshots/<data_version>/latest.json`
- `snapshots/<data_version>/history.json`
- Latest immutable: new snapshot, then last-switch manifest, then old snapshot cleanup (7 days)
- Raw GitHub delivery uses ACAO: *, so it is browser readable.
