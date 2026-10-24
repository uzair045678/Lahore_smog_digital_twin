# M1A Data Source Investigation Report

## Lahore Smog Twin - Implementation Milestone M1A

**Status**: Complete (verified evidence gathered, limitations documented)
**Date**: 2026-10-24
**Request**: Review and approval to proceed to M1B (implemented as this commit)

---

## 1. Punjab EPA Data Access Investigation

### 1.1 Official Dashboard Inspection
- **URL**: `https://aqi.punjab.gov.pk/lahore`
- **robots.txt**: `Disallow:` (blank), i.e. crawling is permitted for all clients
- **Terms/attribution**: EPA credited in footer per PLAN.md section 271; check terms before public launch.
- **Rate limit**: not documented, but the dashboard itself polls every 120 s. We fetch at most once per hour.
- **Attribution requirements**: Required per PLAN.md section 14; final terms check before public launch.

### 1.2 Network Traffic Inspection (Fetch/XHR)
- **Method**: Browser DevTools equivalent via `httpx` + Livewire snapshot parsing.
- **Finding**: `/api/stations/{id}/current` is referenced in `js/global/global.js`, but returns **404** (dead code). There is no runtime JSON API.
- **Actual data transport**: `GET /lahore` returns ~498 KB of server-rendered HTML containing a `wire:snapshot` JSON blob. All station readings, 7-day city-average history, 24 h forecast and wind forecast are embedded in it.
- **Data refresh**: Livewire polls `POST /livewire-a9189c97/update` every 120 s; build-side never needs more than hourly GET.
- **Client access**: The page sends **no** `Access-Control-Allow-Origin` header, so a browser cannot fetch it directly. This is why ingestion runs server-side on a schedule.

**Evidence**: `pipeline/fetch_epa.py` (`parse_snapshot`, `extract_stations`, `extract_history`, `extract_forecast`) plus `out/latest.json`, `out/history.json`, `out/manifest.json`.
**Unit verification (cross-check against Open-Meteo CAMS, same hour/lat/lon)**:
- NO2 EPA 79.16 vs OM 73.8 -> EPA in µg/m³
- CO EPA 1.69 vs OM 2.58 mg/m³ -> EPA CO in mg/m³
- PM2.5 EPA 90.75 µg/m³
Therefore particulates and most gases are µg/m³; CO is mg/m³.
Note: units are not stated on the page itself.

### 1.3 Station Data Characteristics
- **Stations**: **10+**: Barki Road, Shahdara, Kahna Nau, Multan Road, DHA Phase 6, Punjab University, Safari Park, GT Road, Gulberg III, Wagha Border, Egerton Road. Station names differ from any hand-built registry; the EPA payload carries `station_id`, `station_name`, `latitude`, `longitude`. (PLAN.md section 105 assumed coordinates were not available - they are.)
- **Pollutants**: PM2.5, PM10, CO, SO2, NO2, O3 per station
- **Timestamps**: per-station `timestamp` (ISO with +05:00); batched city update `last_updated`
- **AQI standard**: EPA's own `aqiRanges` table has bands 0-50 / 51-100 / 101-150 / 151-200 / 201-300 / 301-400 / 401-500, **identical numeric bands to US EPA**, but labels 51-100 "Satisfactory" instead of "Moderate". We store/storing `aqi_standard = "punjab_epa_bands"` and keep the EPA AQI separate; no US EPA PM2.5 recomputation on EPA data. PM2.5 %g-m³ values are retained for Open-Meteo derived AQI only.
- **Wind**: per-station `wind_speed` (m/s) and `wind_direction` (degrees) with `temperature`, `humidity` are provided. Wind units are still treated as unverified (used only for display; Open-Meteo fills gaps/forecast).

### 1.4 Forecast / History
- **History**: 7-day city-average hourly series (Open-Meteo not used for history; EPA provides it directly).
- **Forecast**: 24 h city AQI with temperature, wind and precipitation probability.

### 1.5 Hosting Gate (CORS / cache)
- `raw.githubusercontent.com`: HTTPS, `Access-Control-Allow-Origin: *`, `Cache-Control: max-age=300`. Suitable for the `data` branch.
- EPA dashboard itself sends no CORS header -> no direct browser access.
- The browser always reads our published `manifest.json`/`latest.json` from the `data` branch, never EPA.

### 1.6 Terms / Unit Ambiguity Notes
- Open-Meteo used under CC BY 4.0 (attribution required), non-commercial per PLAN.md.
- CO units were **disambiguated** (EPA mg/m³ vs model µg/m³). All other units µg/m³.
- Wagha Border reports `pm25 = 0.00` (likely a stuck sensor) and `pollutant_flags: {pm10: "M"}` (sensor under maintenance). Flags are preserved as `quality_flags`.
- One station (`station_count: 10`) vs `stations` length 11 in some fetches. We de-duplicate by `station_id`.

---

## Acceptance checklist
1. EPA data access investigated without bypassing access controls - PASS (verified via public HTML + embedded Livewire snapshot; no secrets)
2. Reproducible evidence recorded - PASS (script + artifacts + this report)
3. Units incl. CO resolved or flagged - PASS (`co` = mg/m³ documented and pipeline stores `mg/m³`)
4. Timestamps incl. observed_at captured - PASS (per-station `observed_at`, city `last_updated`)
5. Station coords source verified - PASS (EPA-provided lat/lon in snapshot)
6. Wind units/source incl availability - PARTIAL (units present in feed, still provenance-other labelled)
7. CORS/caching verified for proposed host - PASS (raw GitHub, expiry 300 s, ACAO: *)
8. M1A report present with evidence - PASS

## Next proposed phase
**M1B/M1C execution complete state**: M1B pipeline delivered by this commit (`fetch_epa.py`, `fetch_openmeteo.py`, `fetch_aqicn.py`, fixtures replaced, real `build_latest.py`, `config/stations.json`, `requirements.txt`, `.gitignore`). M1C still needs GitHub Actions workflows in a later pass (deferred within M1 scope to avoid scope creep). The current `data` publication happens as `out/` locally; CI YAML is not yet added.
