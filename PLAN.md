# Lahore Smog Twin — Implementation Plan

A web-first digital twin of Lahore's air quality. Live station readings, wind and forecasts drive a 3D city. Users scrub through time and enter VR from the same page via WebXR.

This document is written to be handed to a coding agent. Build one milestone at a time. Each milestone has acceptance criteria and a ready-to-paste prompt.

---

## Final architecture (authoritative: if anything below conflicts with this section, this section wins)

### Data delivery — Option C (confirmed)
One public GitHub repository contains the frontend, Python ingestion pipeline, and two independent workflows. `deploy-site.yml` builds Vite/Three.js to GitHub Pages on frontend/build changes only. `update-data.yml` runs hourly (and manually), validates the full dataset, and publishes versioned static JSON to a `data` branch; it must not trigger the website build. The frontend checks a small manifest every 10 minutes and reloads data only when its version changes. The browser never calls EPA/Open-Meteo directly.

**Hosting gate:** GitHub raw-content delivery from the `data` branch is a *candidate*, not a guaranteed production API. M1A must test HTTPS, CORS, cache behavior, public access, and version consistency on desktop/mobile/Quest where available. If unsuitable, propose a dedicated static JSON host while preserving one source repository and independent deployments; obtain owner approval before switching.

**Atomicity:** Publish immutable versioned snapshots first and switch `manifest.json` to the new version last. A client must never combine mismatched snapshot versions. Cache immutable snapshots; revalidate the manifest. Do not claim sub-minute delivery guarantees.

**Failure behavior:** Never replace a validated dataset with invalid content. Compute freshness from per-source `observed_at` and `fetched_at`; if pipeline health needs separate reporting, publish a separately validated status record. Do not assume an unchanged `latest.json` can magically change `stale` to true.

Rules that remove ambiguity:
- Project name: **Lahore Smog Twin**. Public GitHub repo, MIT license for original project code (third-party data and map licenses remain separate).
- Map extent: **entire Lahore**, using a verified boundary. All buildings are optional, simplified grey extrusions; selected recognizable landmarks may have basic silhouettes only. No detailed center, Orange Line corridor, facades or architectural reconstruction requirement. Render using LOD, tiling and culling.
- Exactly **one pollutant layer selected at a time**. Default PM2.5; station detail panels can show other available pollutant measurements. Never apply PM2.5 AQI breakpoints to other pollutants.
- Timeline: **past 48 hours, now, next 24-hour forecast**, hourly steps; display observed/modelled/forecast labels and coverage limitations.
- Wind: **Punjab EPA preferred only where accessible, time-aligned, spatially appropriate, and licensed**; Open-Meteo provides gaps and spatial forecast grid. Do not pretend single-station wind is a citywide field.
- Purpose: **public portfolio and educational demonstration**, not a validated exposure or intervention simulation.
- Commute routes, exposure, and scrubber intervention claims are outside V1; any references elsewhere are deferred.
- No backend server, accounts, user tracking, or geolocation requests.

## 0. Decisions already made

- Web first, WebXR on the same page (Three.js). No separate Unity build.
- First release includes: live AQI map by station, wind, time scrubber (past, now, forecast), and VR. Commute routes and exposure are deferred.
- Headset testing is occasional (borrowed device). Develop against the Immersive Web Emulator and do real-device checks in short sessions.
- No backend server. A scheduled pipeline writes static JSON; the site is static.

## 1. Goals and non-goals

**Goals**
- A shareable link that works on phone, desktop and Quest browser.
- Looks distinctive in a 20-30 second screen recording.
- Honest about uncertainty, data freshness, and what is measured vs modelled.

**Non-goals**
- No user accounts, no tracking of user location, no medical advice.
- No claim that exposure numbers are clinically accurate. They are illustrative estimates.
- No full-city building detail. A stylized, performance-budgeted model is the goal.

## 2. Tech stack

| Layer | Choice |
|---|---|
| Frontend | Vite + TypeScript + Three.js |
| XR | Three.js WebXR (`renderer.xr`), `immersive-vr`; optional `immersive-ar` on Quest passthrough (verify support) |
| UI in 3D | canvas-texture panels or `three-mesh-ui` |
| Pipeline | Python 3.14 (pin tested dependencies: `httpx` or `requests`, `pydantic`, `pytest`; verify package compatibility in CI) |
| Scheduling | GitHub Actions cron (hourly; may be delayed, which is acceptable) |
| Hosting | GitHub Pages (HTTPS is required for WebXR) |
| Tests | Vitest (frontend logic), pytest (pipeline), Playwright (smoke) |

## 3. Repository layout
Single repository, two workflows and a separate data publishing branch:

```text
/
  PLAN.md
  README.md
  .github/workflows/
    deploy-site.yml       # frontend/build changes only
    update-data.yml       # hourly + manual; never builds website
  pipeline/
    fetch_epa.py
    fetch_openmeteo.py
    fetch_aqicn.py        # optional, subject to permissions
    build_latest.py
    schema.py
    config/stations.json
    tests/
  scripts/
    build_city.py
    build_routes.py      # DEFERRED
  web/
    index.html
    src/
      main.ts
      scene/
      xr/
      data/loader.ts
      data/polling.ts
      data/schema.ts
      model/
      ui/
    public/city/
    public/demo/        # clearly labelled snapshot, never live
```

The `data` branch contains `manifest.json` and immutable versioned `latest.json`/`history.json` snapshots. A rolling UI history is 48 hours; retention of seven days in the JSON is acceptable, but the frontend loads only what is needed. Git history is not the authoritative long-term measurement archive.

## 4. Data sources

### 4.1 Live station readings (primary)
- Source: Punjab EPA air quality platform, `https://aqi.punjab.gov.pk/lahore`. It shows hourly readings from about 10 Lahore stations, with PM2.5, PM10, CO, SO2, NO2 and O3 per station.
- No documented public API was found. First step for the agent: inspect the page's network requests (browser devtools / Playwright) for a JSON endpoint behind it. If none exists, parse the HTML.
- Before scraping, check the site's terms and robots rules. Fetch at most once per hour, send an honest User-Agent, and cache.
- Station coordinates are not guaranteed to be on the page. Build `stations.json` by hand (name, lat, lon), verify each against a map, and record the verification date.
- The site has had data-transmission delays before. Always store each station's own "last updated" timestamp and show it in the UI.

### 4.2 Forecast, wind, backfill
- Open-Meteo Air Quality API (CAMS-based model): hourly PM2.5, PM10, NO2, O3, hourly forecast several days ahead, and `past_days` for backfill. Free for non-commercial use, requires attribution (CC BY 4.0).
- Open-Meteo Weather API: hourly wind speed and direction at 10 m. Query a spatial grid over the city where needed; EPA wind is preferred only if timestamp, coverage, units and access are verified. Open-Meteo fills gaps and provides forecast wind.
- Open-Meteo values are model estimates, not measurements. The UI must label them as modelled.

### 4.3 Fallback
- AQICN station API for Lahore (free token stored as a GitHub secret). AQICN labels its data as unvalidated; use only as a fallback and label it.

### 4.4 Geometry
- OpenStreetMap via Overpass (build time only, not at runtime): buildings, roads, Orange Line and station locations. Attribution (ODbL) is required.

### 4.5 Source priority and flags
For each station and hour, record `source` = `epa | aqicn | model` and `measured: boolean`. Priority for compatible pollutant observations: EPA, then authorized AQICN fallback, then explicitly labelled Open-Meteo model. For wind use verified EPA samples where representative and Open-Meteo elsewhere. If all sources fail, keep last valid snapshots; calculate staleness in the client.

## 5. Data contracts
Use versioned, Pydantic-validated data contracts. The JSON examples below are illustrative schema shapes, not real observations.

- `manifest.json`: `schema_version`, `data_version`, `published_at`, immutable URLs/paths to `latest` and `history` snapshots.
- `latest.json`: `schema_version`, `generated_at`, `stations[]`, `forecast`, `wind`, `source_health`. Each station: verified `id`, `name`, `lat`, `lon`; pollutant values with units, optional/null missing fields, `observed_at`, `fetched_at`, `source`, `measured`, quality flags.
- `history.json`: hourly indexed records retaining source, measurement time, pollutant, units, and whether measured or modelled. The first release shows 48 hours of history; rolling storage can retain seven days.
- `wind`: per-sample timestamp, position/coverage, speed units, direction convention, source and whether measured or modelled. Prefer EPA where suitable; use Open-Meteo for missing spatial or forecast coverage.
- Keep a bundled `web/public/demo/` snapshot clearly labeled as non-live.

**Validation:** Enforce units, timestamps, source attribution, bounds, uniqueness, chronological ordering, and compatibility across files. Missing values must remain null, never be silently replaced by zero. If source data fails, preserve last good published snapshots and show staleness computed by the frontend from observation time. Do not silently merge readings with incompatible averaging periods or AQI standards.

## 6. Model logic (all in `web/src/model/`, fully unit-tested)

### 6.1 PM2.5 to AQI
Store concentrations in source-appropriate units and keep any source-provided AQI and its standard separately. For PM2.5, compute US EPA AQI only when concentration and averaging period are compatible; do not convert other pollutants using PM2.5 breakpoints. Use the current EPA breakpoint table and verify it against EPA's technical documentation (the 2024 revision lowered the Good/Moderate boundary to about 9.0 µg/m³). Keep breakpoints in `config.ts`. Note which scale Punjab EPA itself uses is unconfirmed, so show PM2.5 alongside AQI.

### 6.2 Spatial interpolation
- Inverse-distance weighting over station values, power parameter 2 (configurable), distance capped by a max radius.
- Output an adaptive/tiled grid over the full Lahore extent as Float32Arrays, recomputed for the selected pollutant and time, avoiding unsupported extrapolation.
- Provide `confidence(x, y)` based on distance to the nearest station. The renderer uses it to fade or hatch low-confidence areas.

### 6.3 Time handling
- Timeline from now minus 48 h to now plus 24 h, hourly steps.
- Past 48 h: station history or flagged model backfill. Future 24 h: model forecast; bias correction is optional and must be evaluated per pollutant and data availability before activation. Label forecasts explicitly.

### 6.4 Route exposure — DEFERRED. Do not implement in the first release; kept for a later version.
Inputs: route geometry, mode, departure time, mask on/off.

1. Compute trip duration from route length and mode speed (config).
2. Sample positions along the route at 1-minute steps.
3. At each step, read the interpolated outdoor PM2.5 for that position and that time.
4. Apply a mode infiltration factor (fraction of outdoor PM2.5 reaching the person) and a mask factor.
5. Dose = sum(concentration × minute ventilation × minutes).
6. Output per mode: duration, average outdoor PM2.5, average experienced PM2.5, estimated inhaled dose (µg), and dose relative to the highest mode.

Parameters live in `model/config.ts` and are explicitly labelled as assumptions. Starting values (adjust after a literature check and cite sources in the README):

| Mode | Avg speed km/h | Infiltration | Minute ventilation L/min |
|---|---|---|---|
| Motorbike | 25 | 1.0 | 20 |
| Car, windows closed | 20 | 0.5 | 10 |
| Bus | 15 (+ wait) | 0.8 | 12 |
| Orange Line + walking legs | 30 (+ walk 5) | 0.6 in train, 1.0 walking | 10 train, 25 walking |
| Mask (N95-type, imperfect fit) | n/a | multiply by 0.3 | n/a |

"Best time to leave": evaluate each departure hour in the next 24 h for the chosen route and mode, recommend the lowest-dose window.

The UI must say these are illustrative estimates based on stated assumptions, not medical advice.

## 7. City geometry — greybox only (confirmed)

**Design principle:** This is a pollution and smog data visualization, not an architectural reconstruction. City geometry is background geographic context. Do not spend milestone time on photorealism, detailed building meshes, facades, textures, interiors, or building-by-building height accuracy.

- Verify Lahore's geographic boundary and coordinate reference; use OpenStreetMap/Overpass at **build time only**, respecting usage policy and attribution.
- Build a lightweight city base with administrative outline, major roads, optional district boundaries, and a limited number of grey extruded building footprints or generic grey blocks. Missing building footprints are acceptable.
- Optional simplified silhouettes for a handful of recognizable landmarks, only after pollution visualization is functional. Landmark selection requires no custom asset pipeline in V1.
- No mandatory Orange Line corridor emphasis. A simple line is acceptable as a geographic reference if cheap to generate.
- Reproject lat/lon into local metric coordinates with a documented origin and consistent scale. Keep station locations accurately positioned even if buildings are stylized.
- Tile/cull geometry where useful. Use `InstancedMesh` for repeatable blocks or merged geometry for static tiles; avoid individual draw calls per building.
- Initial **targets, not requirements**: 2,000–5,000 visible simple blocks at the city overview quality tier, ~300k triangles or fewer on Quest, and a mobile-friendly scene. Profile and adjust based on hardware.
- Keep buildings low-contrast grey so the pollutant layer, station markers, and wind remain visually dominant.

**Acceptance:** A recognizable, geographically anchored Lahore overview with a clean greybox city base, visible monitoring stations, and no excessive geometry cost. The visualization must remain useful if all buildings are hidden.

## 8. Rendering (Three.js) — environmental data first

### 8.1 Scene composition

- Orthographic or perspective camera with a default tilted/isometric overview, orbit/pan/zoom on desktop, touch controls on mobile, and a tabletop scale in WebXR.
- Base: neutral ground, verified Lahore boundary, simplified major roads and optional grey blocks.
- Stations: interactive markers/columns located by verified lat/lon; tooltips show selected pollutant, units, source, observation time, and station name. Never use height/color without a legend.
- Pollutant layer: **one selected pollutant at a time**, default PM2.5. Primary visualization is a ground-level color-coded concentration surface; optional subtle translucent haze is secondary and can be toggled off.
- Use a typed grid (`Float32Array`) and `DataTexture`/`ShaderMaterial` or equivalent to render the field efficiently; mask areas outside Lahore and fade low-confidence interpolation. Do not portray interpolation as observed data.
- Wind: lightweight particles or line trails moving through the selected time's wind vector field. Convert meteorological wind direction (direction **from**) into a vector pointing **toward** correctly. Source and temporal alignment must be visible.
- Time changes update GPU textures, station attributes and wind vectors, **not** city geometry. Polling updates state without full-page reload.
- Keep the station layer and heatmap legible if haze is enabled; add accessible non-color indicators and legend labels.

### 8.2 Pollutant and uncertainty rules

- PM2.5 and PM10 typically use µg/m³, but verify actual source units; gases may be reported in ppm, ppb, µg/m³ or other units. Never guess conversions or apply PM2.5 breakpoints to all pollutants.
- AQI is an index, not the same quantity as PM2.5 concentration. Show the source's AQI standard where known; compute US EPA PM2.5 AQI only from compatible PM2.5 concentrations and averaging conventions.
- If fewer than a defensible number of valid observations exist, render station markers without a continuous citywide field. Cap interpolation radius, fade uncertain areas, and label forecast and backfill separately.
- Use source-specific observation times. Never label a successfully fetched but old reading as live.
- Open-Meteo data is modelled; do not silently replace an EPA station observation with a model estimate.

### 8.3 Performance and visual targets

- Start with a 64×64 pollution grid, adaptive particle budget (initially 500–2,000), and one active pollutant texture; tune after profiling.
- Target 60 fps on capable desktop, usable adaptive mobile performance, and 72 fps on a tested Quest configuration; these are targets, not promises.
- Provide quality tiers controlling buildings, particles, resolution and haze. Avoid high overdraw from many transparent fog layers.
- Keep the main scene functional with station markers and a simple heatmap when advanced visual effects are disabled.

## 9. UI

- Top bar: title, observation-time freshness (not merely fetch time), measured vs modelled indicator, and selected pollutant.
- Left or bottom panel: time scrubber with Past / Now / Forecast segments and play button.
- Route panel: deferred, not in the first release.
- Pollutant selector: exactly one active pollution layer; default PM2.5. Legend changes units/thresholds for selected pollutant; never reuse AQI thresholds incorrectly. Colorblind-safe shapes/patterns.
- Station detail card: all pollutants, source, last-updated time.
- Footer: attributions and the disclaimer.
- Mobile-first layout, 16px gutters, no horizontal scroll, dark/light handling.
- Copy tone: informative, not alarmist, with a plain-language takeaway (for example, which hours are forecast to be cleaner).

## 10. Routes — DEFERRED. Do not implement in the first release.

A "preset route" is a fixed origin-destination pair that ships with the app. The user picks one from a dropdown; they cannot enter arbitrary addresses in the first release (that would need a live routing server).

Proposed presets (pending owner confirmation; the agent must not change them without asking):
1. Gulberg Main Market to Lahore Railway Station (central, mixed modes).
2. Thokar Niaz Baig to Lahore Railway Station (runs along the Orange Line, so all four modes apply).
3. Johar Town to Walled City / Delhi Gate (cross-city, a route where the Orange Line is not the natural option).

The Orange Line mode is offered only for routes where both endpoints are within a reasonable walk of Orange Line stations; otherwise show the other three modes and say why Orange Line is unavailable. The agent must verify station locations against OSM and report any endpoint it cannot route.
- `scripts/build_routes.py` generates route geometry per mode using a routing engine (OSRM or openrouteservice, offline at build time, respecting their usage policies) and the Orange Line path from OSM.
- Store as GeoJSON in `web/public/routes/`. No live routing at runtime, which keeps the site static and robust.
- Verify the Orange Line geometry and station order against OSM, noting that parts of the line are elevated and parts are underground.

## 11. WebXR

- Add an "Enter VR" button using Three.js's XR button helper. Only show it if `navigator.xr` reports `immersive-vr` support. Session start requires a user tap.
- Scale the city to a tabletop model (about 1 m wide). Grab with controllers or hands to move, rotate and scale.
- Interaction: point or pinch a station to open its card, a floating wrist or panel UI for the time scrubber. Support controllers as a fallback when hand tracking is unavailable.
- Optional stretch: `immersive-ar` passthrough on Quest for a tabletop in the real room. Verify browser support on the current Quest firmware before building.
- Test loop: develop with the Immersive Web Emulator extension, then run a short real-headset checklist: loads over HTTPS, enter/exit VR, hand tracking, readable panel text, stable frame rate, comfortable scale.

## 12. Pipeline and deployment

- Option C is confirmed: `deploy-site.yml` publishes the website only on frontend/build changes; `update-data.yml` runs hourly and publishes validated data snapshots and a manifest independently to the `data` branch. Use concurrency control so runs never overlap.
- Test GitHub raw-content delivery for CORS, cache behavior, consistency, and availability before accepting it. If unsuitable, request approval for another static JSON host.
- Publish immutable versioned snapshots first and update the manifest last. The client loads matching versions only.
- Schedule is best-effort, not an hourly freshness guarantee. Use source observation timestamps and report delayed or failed ingestion clearly.
- Secrets: optional AQICN token. Never commit tokens.
- The browser never calls the EPA or Open-Meteo directly. The app reads data from the location defined by the chosen data delivery method.
- Frontend must work if data is old: show the stale banner, never crash.

## 13. Quality, testing, privacy

- Unit tests: AQI conversion at every breakpoint edge, IDW (known values, single station, far-from-station), time alignment, forecast bias correction.
- Pipeline tests: parsing fixtures from saved EPA/Open-Meteo responses, schema validation failures, fallback ordering.
- Playwright smoke test: page loads, scene renders, scrubber changes the displayed time.
- Lighthouse on mobile, with a performance budget for initial load (target under about 5 MB over the wire for first paint of the scene).
- Privacy: no analytics that identify users, no geolocation requests, no third-party trackers.

## 14. Attribution and legal checklist

- OpenStreetMap contributors (ODbL), shown in the footer.
- Open-Meteo, CC BY 4.0, non-commercial use only. If the project is ever monetized, review this.
- Punjab EPA credited as a data source; check terms before scraping and before public launch.
- AQICN if used, per their terms.
- Disclaimer: informational, illustrative, not medical advice; not affiliated with any government body.

## 15. Milestones (give the agent one at a time)

### M1 — Scaffold and data pipeline
**Deliver**: split into M1A source-access investigation, M1B fetchers/schema/valid local snapshots, M1C independent website/data workflows with tested browser JSON access. Do not implement M1B before owner reviews M1A.
**Accept**: running the pipeline locally produces valid JSON; tests pass; failure of one source falls back correctly; no secrets in repo.
**Prompt**: "Read PLAN.md. Implement M1A only: investigate Punjab EPA public data access, endpoint responses, licensing and timestamp/units/station metadata. Do not write a scraper or workflow yet. Provide a reproducible evidence report and ask for review before M1B."

### M2 — Model logic
**Deliver**: AQI conversion, IDW with confidence, time alignment with forecast bias correction, with full unit tests.
**Accept**: all tests pass; config holds all assumptions; no rendering code yet.
**Prompt**: "Implement milestone M2 per PLAN.md section 6 as pure TypeScript modules with Vitest tests. Verify the EPA PM2.5 breakpoints against official documentation and cite the source in a comment."

### M3 — Greybox city geometry
**Deliver**: `build_city.py`, simplified greybox blocks and major roads for Lahore, geographic alignment tests, and a preview page. No detailed architecture or landmark modelling required.
**Accept**: low draw-call/triangle cost, correct station alignment, clean overview on desktop, buildings can be hidden without losing data utility.
**Prompt**: "Implement milestone M3 per PLAN.md section 7. Keep geometry minimal and greyboxed. Report geographic alignment, triangle count, draw calls, and file sizes. Show a screenshot; do not create detailed buildings."

### M4 — 3D scene with live data
**Deliver**: station columns, primary pollution heatmap, optional subtle haze, wind particles, orbit camera, data loader, freshness banner, pollutant selector and legend.
**Accept**: renders from `latest.json`; selected pollutant and source labels work; stale state works; heatmap remains readable; frame rate meets budget on desktop.
**Prompt**: "Implement milestone M4 per PLAN.md sections 8-9. Prioritize readable PM2.5 heatmap, station markers, source labels, and wind over building details. Use the model modules from M2."

### M5 — Time scrubber
**Deliver**: timeline UI, past/forecast labelling, play mode, measured vs modelled indicator.
**Accept**: scrubbing updates columns, fog and wind; forecast clearly labelled.

### M6 — DEFERRED (routes and exposure): skip this milestone and go from M5 to M7
**Deliver**: `build_routes.py`, preset routes, route panel, mode and mask toggles, comparison card, best time to leave, disclaimers.
**Accept**: results match unit-tested math; assumptions are visible in the UI; Orange Line route verified.
**Prompt**: "Implement milestone M6 per PLAN.md sections 6.4 and 10. Show the assumptions table in an info panel."

### M7 — WebXR
**Deliver**: Enter VR, tabletop scaling and manipulation, station selection, XR panel UI, quality auto-scaling.
**Accept**: works in the emulator; passes the real-headset checklist in section 11 on a borrowed device.
**Prompt**: "Implement milestone M7 per PLAN.md section 11. Give me a short device checklist to run on the headset, and list anything you could not verify without hardware."

### M8 — Polish, docs, launch
**Deliver**: mobile layout pass, accessibility pass, README with architecture diagram, data and assumption docs, demo mode (a recorded data snapshot for screenshots), Lighthouse report, deployed link.
**Accept**: all section 13 checks pass; attributions present.

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| EPA data has no API or blocks scraping | Inspect for hidden endpoint; fall back to AQICN and Open-Meteo, labelled; keep a documented manual-snapshot option for demos |
| Station data delays or gaps | Per-station freshness, stale banner, never fabricate values |
| Sparse stations make interpolation misleading | Confidence fade, "model estimate" labelling, no precise claims between stations |
| Quest performance | Triangle and particle budgets, XR quality tier, early device test |
| Exposure numbers misread as medical | Prominent "illustrative" label, visible assumptions, relative comparisons first |
| Terms or attribution issues | Section 14 checklist before public launch |

## 17. Content kit for LinkedIn (after M5, refine after M8)

1. First post: 20-30 s screen recording of the live city, wind and time scrubber with a plain-language hook about Lahore's current AQI. Link to the live demo.
2. Carousel case study: problem, data sources, system diagram, design decisions (color accessibility, uncertainty display, tone), limitations.
3. Weekly "Lahore this week" clips as the season peaks.
4. VR post: headset footage of the tabletop city with a link that opens on Quest.

## 18. Confirmed decisions and unresolved blockers

**Confirmed by owner:** Entire Lahore with simplified outer areas; one selected pollutant layer at a time; past 48 h and next 24 h; EPA wind preferred with Open-Meteo gap filling; public educational/portfolio use; Option C data architecture.

**Blockers before M1B:**
1. Does Punjab EPA expose an accessible endpoint or permitted export, and what are the terms/rate limits? Document actual requests/responses, not assumptions.
2. What timestamps, averaging windows, AQI standard, units and station identifiers does EPA actually provide? Is station wind available per timestamp/location?
3. Which station coordinates and city boundary are verified, and what does sparse coverage imply for interpolated regions?
4. Can a browser reliably retrieve versioned JSON from the proposed `data` branch hosting, with correct CORS/cache behavior? Test rather than assume.
5. Can the selected Open-Meteo and AQICN usage terms support this public demonstration, including attribution and redistribution?

**Non-blocking decisions for later milestones:** exact city boundary polygon, default PM2.5 legend/scale, mobile performance tiers, and whether a future V2 adds defensible intervention modelling. These should not delay M1A.

## 19. Next coding-agent task — M1A (do not skip)

**Goal:** Establish a reproducible, permitted source of real station readings before implementing ingestion or the full Three.js scene.

1. Inspect the official Punjab EPA Lahore dashboard and publicly documented resources. Check terms, robots rules, access restrictions and attribution. Do not assume an API exists.
2. With browser developer tools/Playwright, inspect Fetch/XHR traffic for station data. Record only verified endpoints, methods, sample field names, timestamps and units; do not expose secrets or bypass access controls. If no usable endpoint exists, assess permitted HTML parsing and official data access requests.
3. Check whether wind data is available with geographic coordinates and compatible observation times. Document fallback to Open-Meteo for gaps and forecasts.
4. Verify whether the proposed static JSON endpoint supports browser CORS and acceptable cache behavior. Do not mistake successful curl access for browser compatibility.
5. Write `M1A_DATA_SOURCE_REPORT.md` with evidence, unresolved constraints, legal/access considerations and a recommended implementation path.
6. **Stop and request review.** Do not begin M1B, website deployment or detailed Three.js work yet.

**Acceptance:** Every source claim is either backed by a reproducible observation or explicitly marked unverified. No invented endpoint URLs, station coordinates, source terms or update guarantees.

## 20. Owner-confirmed scope freeze

- Entire Lahore with simplified outer areas; greybox buildings throughout, with optional minor landmark silhouettes.
- One active pollutant layer at a time, default PM2.5.
- Past 48 hours and next 24-hour forecast.
- Punjab EPA wind preferred where suitable; Open-Meteo for missing coverage.
- Public educational and portfolio demonstration, not commercial/clinical/operational decision support.
- Option C: single repository, separate website and data deployment workflows.
- No route/exposure feature, detailed building reconstruction, or validated scrubber intervention simulation in V1.

---

## 21. Mandatory phase-by-phase execution protocol (authoritative)

**This section is a binding instruction to every coding agent working on this repository.** It overrides any earlier milestone prompt that might imply implementing several phases at once. A milestone is not complete merely because code was written.

### 21.1 Work on exactly one phase

1. Read `PLAN.md` and identify the **current approved phase** before modifying files. Start with **M1A** unless the owner has explicitly approved a later phase.
2. State the phase goal, in-scope files, dependencies, acceptance criteria, and proposed tests before implementation. Keep the scope narrow. If the phase is too large, split it into numbered subphases and complete only the first approved subphase.
3. Implement **only the current phase**. Do not silently begin the next phase, implement deferred features, or refactor unrelated code.
4. If a blocking ambiguity or permission issue arises, stop and ask the owner rather than inventing facts, credentials, API endpoints, coordinates, or test results.

### 21.2 Test your own work before asking the owner

After implementation, the agent must independently run the relevant checks in its environment:

- Format, lint and type-check any changed code when tooling exists.
- Run targeted unit tests, then the applicable broader regression tests (pytest, Vitest, Playwright, build checks, or equivalent).
- Exercise realistic success, missing-data, stale-data and failure paths appropriate to the phase; validate schemas, timestamps, and provenance for data work.
- For UI phases, launch a local preview and inspect the rendered behavior, console errors, responsiveness, and interactions using available browser tooling. Capture a screenshot or brief evidence where possible.
- For deployment phases, verify actual published artifacts, CORS and caching in a browser, workflow logs, and data version consistency. Never claim a live deployment passed if credentials, network, device or permissions prevented verification.
- For VR phases, test in an emulator first and clearly mark headset-only checks as **not verified** until tested on real hardware.

**Never fabricate a test, screenshot, benchmark, browser inspection, source-access check, or passing result.** If a check cannot be run, explain precisely why and provide the owner with a reproducible manual check. If tests fail, fix the failure and rerun them before requesting approval, unless a genuine blocker requires the owner's decision.

### 21.3 Mandatory end-of-phase report

At the end of **every** phase or approved subphase, report in this exact order:

1. **Phase and status:** Complete / Partially complete / Blocked.
2. **Implemented:** What changed, with relevant file paths.
3. **Self-tests performed:** Exact commands or procedures, results, and evidence. Distinguish PASS, FAIL, and NOT RUN.
4. **Limitations and risks:** Remaining issues, assumptions, unverified integrations and known regressions.
5. **How you can test it:** Numbered, practical owner-side steps, including setup commands, expected visible results, and what to check if something fails. Make instructions usable by someone who did not write the code.
6. **Acceptance checklist:** Each criterion marked PASS / FAIL / NOT VERIFIED.
7. **Next proposed phase:** Name, scope, dependencies, and what approval is needed.
8. **Approval request:** Explicitly ask, **“Please test this phase and tell me whether to proceed to [next phase].”**

### 21.4 Hard approval gate

**STOP after the report.** Wait for the owner to test, review, and explicitly authorize the next phase. Do not infer approval from silence, successful CI, a passing local test, or the agent's own assessment. If the owner reports a bug, fix and retest **within the same phase**, issue an updated report, and ask for approval again. Never proceed while critical acceptance criteria fail.

### 21.5 Phase sequence

Follow the phase breakdown already defined in this plan: **M1A → M1B → M1C → M2 → M3 → M4 → M5 → M7 → M8**. **M6 is deferred**. Further split any large phase into small reviewable subphases without changing this order unless the owner explicitly approves a change. For M1A, the deliverable is an evidence-backed source-access report, not a working scraper or website.

### 21.6 Definition of done

A phase is ready for owner review only when its scoped deliverables exist, relevant automated checks have been run (or limitations disclosed), a reproducible owner test procedure is supplied, and acceptance results are documented. **A phase is approved only when the owner explicitly says to proceed.**
