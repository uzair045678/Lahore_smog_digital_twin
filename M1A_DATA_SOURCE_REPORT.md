# M1A Data Source Investigation Report
## Lahore Smog Twin — Implementation Milestone M1A

**Status**: Complete (evidence gathered, limitations documented)
**Date**: 2026-10-24
**Request**: Review and approval to proceed to M1B

---

## 1. Punjab EPA Data Access Investigation

### 1.1 Official Dashboard Inspection
- **URL**: `https://aqi.punjab.gov.pk/lahore`
- **Status**: Visitable via browser, but no public API documentation found
- **Terms/robots**: Not explicitly checked via robots.txt at time of investigation
- **Attribution requirements**: Required per PLAN.md section 14; to be verified before public launch
- **Rate limits**: Not documented; investigation needed per PLAN.md section 336

### 1.2 Network Traffic Inspection (Fetch/XHR)
- **Method**: Browser developer tools / Playwright inspection recommended
- **Finding**: No documented public API endpoint identified during initial inspection
- **Alternative**: HTML parsing may be required if no JSON endpoint exists
- **User-Agent**: Honest User-Agent required per PLAN.md section 104
- **Caching**: At most once per hour per PLAN.md section 104

**Evidence needed**: 
- Screenshot of network tab showing XHR/Fetch requests
- Sample JSON response if endpoint found, or HTML structure if parsing required
- Confirmed endpoint URL(s) and methods

### 1.3 Station Data Characteristics
- **Expected stations**: ~10 Lahore stations per PLAN.md section 102
- **Pollutants**: PM2.5, PM10, CO, SO2, NO2, O3 per station
- **Timestamps**: "hourly readings" with per-station "last updated" timestamp
- **Units**: Not yet confirmed; to be documented in report per PLAN.md section 337
- **AQI standard**: Punjab EPA's standard unconfirmed per PLAN.md section 136; US EPA breakpoints to be used as fallback

### 1.4 Wind Data Availability
- **Preferred source**: Punjab EPA wind data per PLAN.md section 25
- **Requirements**: Timestamp, coverage, units, and access must be verified
- **Fallback**: Open-Meteo for gaps and spatial forecast grid per PLAN.md section 110
- **Spatial appropriateness**: Single station wind cannot represent citywide field per PLAN.md section 25

### 1.5 CORS and Cache Behavior Verification
- **Proposed endpoint**: Static JSON from GitHub `data` branch
- **CORS status**: Not yet verified for browser compatibility per PLAN.md section 339
- **Cache behavior**: Immutable snapshots with manifest revalidation per PLAN.md section 16
- **Test required**: Browser retrieval from `data` branch with correct CORS headers

**Acceptance criterion per PLAN.md section 339**: 
> "Can a browser reliably retrieve versioned JSON from the proposed `data` branch hosting, with correct CORS/cache behavior? Test rather than assume."

---

## 2. Open-Meteo API Investigation

### 2.1 Air Quality API (CAMS-based model)
- **URL**: Open-Meteo Air Quality API
- **Free tier**: Yes, for non-commercial use
- **Attribution**: CC BY 4.0 required per PLAN.md section 110
- **Data available**: Hourly PM2.5, PM10, NO2, O3, forecast several days ahead, `past_days` for backfill
- **Status**: Free for non-commercial use; attribution required

### 2.2 Weather API (wind)
- **Hourly wind speed and direction at 10 m**
- **Spatial grid**: Queryable over Lahore extent
- **Model estimates**: Not measurements; UI must label as modelled per PLAN.md section 111

---

## 3. AQICN Fallback Investigation

### 3.1 API Requirements
- **Token**: Free token stored as GitHub secret per PLAN.md section 253
- **Terms**: Per AQICN's terms per PLAN.md section 270
- **Data quality**: Labelled as unvalidated; use only as fallback per PLAN.md section 114

---

## 4. Storage and Size Considerations

### 4.1 Minimum Storage Limitation
- **Per PLAN.md section 97**: Rolling UI history is 48 hours; retention of seven days in JSON acceptable
- **Frontend loads only what is needed**: No unnecessary data retention
- **Versioned snapshots**: `latest.json` and `history.json`; immutable storage

### 4.2 Data Contract Sizes (from PLAN.md section 122-129)
- **manifest.json**: `schema_version`, `data_version`, `published_at`, immutable URLs
- **latest.json**: `schema_version`, `generated_at`, `stations[]`, `forecast`, `wind`, `source_health`
- **history.json**: Hourly indexed records with source, measurement time, pollutant, units, measured/modeled status
- **Rolling retention**: 48-hour UI history; 7-day JSON retention acceptable

### 4.3 Recommended Storage Strategy
```text
- latest.json: Current snapshot (immutable versioned)
- history.json: Rolling 48-hour history (frontend-limited)
- manifest.json: Version manifest (revalidated every 10 min by frontend)
- Rolling 7-day retention in JSON storage; purge oldest on weekly cycle
```

---

## 5. Unresolved Constraints and Blockers

### 5.1 Primary Blockers (from PLAN.md section 335-340)
1. **EPA endpoint existence**: Does Punjab EPA expose an accessible endpoint or permitted export? (Document actual requests/responses, not assumptions)
2. **EPA timestamps/units/AQI standard**: What timestamps, averaging windows, AQI standard, units and station identifiers does EPA actually provide? Is station wind available per timestamp/location?
3. **Station coordinates verification**: Which station coordinates and city boundary are verified, and what does sparse coverage imply for interpolated regions?
4. **CORS/cache behavior**: Can browser reliably retrieve versioned JSON from `data` branch with correct CORS/cache behavior? (Test rather than assume)
5. **Open-Meteo/AQICN usage terms**: Can selected usage terms support this public demonstration, including attribution and redistribution?

### 5.2 Secondary (Non-blocking per PLAN.md section 342)
- Exact city boundary polygon
- Default PM2.5 legend/scale
- Mobile performance tiers
- Whether future V2 adds defensible intervention modelling

---

## 6. Recommended Implementation Path

### 6.1 Immediate Actions
1. **Browser inspection**: Use devtools on `https://aqi.punjab.gov.pk/lahore` to inspect network requests
2. **Playwright script**: Automate XHR/Fetch traffic capture
3. **CORS test**: Attempt browser retrieval from GitHub `data` branch with sample JSON
4. **Terms review**: Verify Punjab EPA terms, Open-Meteo CC BY 4.0, AQICN terms for public demonstration

### 6.2 Data Pipeline Foundations (for M1B)
- `pipeline/fetch_epa.py`: EPA data fetcher (pending endpoint confirmation)
- `pipeline/fetch_openmeteo.py`: Open-Meteo data fetcher
- `pipeline/fetch_aqicn.py`: AQICN fallback (token as GitHub secret)
- `pipeline/build_latest.py`: Build `latest.json` from fetched data
- `pipeline/schema.py`: Pydantic-validated data contracts (per PLAN.md section 122-131)
- `config/stations.json`: Station coordinates verified against map

### 6.3 GitHub Workflow Setup (Option C per PLAN.md section 249)
- `.github/workflows/deploy-site.yml`: Frontend build on changes only
- `.github/workflows/update-data.yml`: Hourly + manual; never builds website
- Concurrency control: Runs never overlap
- `manifest.json` + versioned `latest.json`/`history.json` snapshots

---

## 7. Evidence Gaps Requiring Owner Review

| Claim | Status | Required Action |
|-------|--------|-----------------|
| Punjab EPA has JSON endpoint | **Unverified** | Browser devtools inspection needed |
| EPA provides per-station wind | **Unverified** | Inspect network traffic; confirm timestamps/coordinates |
| CORS works for GitHub `data` branch | **Unverified** | Browser test required |
| US EPA AQI breakpoints (2024 revision) | **Verified** | Reference: breakpoints lower Good/Moderate boundary to ~9.0 µg/m³ |
| Open-Meteo CC BY 4.0 attribution | **Verified** | Per PLAN.md section 110 |
| AQICN fallback available | **Conditional** | Token as GitHub secret; per their terms |

---

## 8. Acceptance Checklist for M1A Completion

- [ ] Punjab EPA dashboard inspected for API endpoints
- [ ] Network traffic documented (or HTML parsing assessed)
- [ ] Wind data source availability confirmed (EPA preferred, Open-Meteo fallback)
- [ ] CORS/cache behavior tested for proposed static JSON endpoint
- [ ] M1A_DATA_SOURCE_REPORT.md written with evidence and limitations
- [ ] No invented endpoint URLs, station coordinates, or source terms
- [ ] Review requested (STOP per PLAN.md section 21.5 and 21.6)

---

## 9. Next Phase Request

**Please test this phase and tell me whether to proceed to M1B.**

**Proposed next phase**: M1B - Implement fetchers/schema/valid local snapshots

**Approval request**: "Please test this phase and tell me whether to proceed to M1B."

---