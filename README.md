# Lahore Smog Twin

A web-first, open-source educational 3D visualisation of Lahore's air quality. Station readings, wind, time scrubbing, and WebXR merge into one shareable page; commute/exposure modelling is intentionally deferred.

- **Live app:** https://uzair045678.github.io/Lahore_smog_digital_twin (GitHub Pages)
- **Status:** M1–M7 implemented. M8 polish/documentation in progress.

## Architecture

Option C per `PLAN.md`: one repository, two independent workflows.

```
Browser (Three.js/WebXR)
    |
    | poll every 10 min
    v
raw.githubusercontent.com/.../data/manifest.json
    |
    +-- snapshots/<version>/latest.json
    +-- snapshots/<version>/history.json
    ^
    |
GitHub Actions (hourly): update-data.yml
    |
    +-- Python pipeline (Punjab EPA -> Pydantic -> Open-Meteo fallback)
    +-- publish immutable snapshots + switch manifest.json
deploy-site.yml: only rebuilds website on web/ changes and never on data pushes
```

## Tech stack

- Frontend: Vite + TypeScript + Three.js/WebXR
- Pipeline: Python 3.14, `httpx`, `pydantic`, `pytest`
- Scheduler: GitHub Actions cron (hourly, best-effort)
- Hosting: GitHub Pages (HTTPS) + raw GitHub for data JSON

## Run locally

### Web

```bash
cd web
npm install
npm test
npx tsc --noEmit
npm run build
npm run dev
```

Open `http://localhost:5173`.

### Pipeline

```bash
python -m pip install -r requirements.txt
python -m pipeline.build_latest
python -m pytest pipeline/tests
```

Outputs are in `out/` (ignored by git; served from the `data` branch in production).

## Data source

Primary: Punjab EPA dashboard (`https://aqi.punjab.gov.pk/lahore`), parsed from the server-rendered Livewire snapshot. Open-Meteo fills gaps and provides spatial/forecast wind. AQICN remains optional and unconfigured.

Attribution and legal checklist: see `docs/DATA.md` and `docs/ASSUMPTIONS.md`.

## Accessibility and limitations

- One pollutant layer at a time (default PM2.5)
- Concentrations shown only with PM2.5 breakpoints for AQI; other pollutants retain their units
- Historical/future station values are city-trend scaled (not measured stations)
- No user accounts, tracking, geolocation, or live routing
- Values older than 2 hours are marked stale/risk-grade

## License

MIT for original project code. Third-party data, OSM, Open-Meteo, and map licenses remain separate. See `docs/DATA.md`.
