# Assumptions behind the model logic

## Pollutant and AQI

- Only PM2.5 is converted to US EPA AQI using the 2024 breakpoints. Other pollutants keep their own units; AQI must never be applied to non-PM2.5.
- `pm25ToAqi(0.0–9.0)` => `0–50`; `9.1–35.4` => `51–100`; `35.5–55.4` => `101–150`; `55.5–125.4` => `151–200`; `125.5–225.4` => `201–300`; `225.5–325.4` => `301–400`; `325.5–500.4` => `401–500`; values above 500.4 report `500`.
- PM2.5 averaging period is assumed to be 24 hour.

## Interpolation

- Inverse distance weighting with power 2 and 15 km max radius. If no station is within 15 km, no city field is drawn.
- Confidence falls to zero at 15 km.
- Weather interpolation is represented as station-level markers first; interpolation is labelled as modelled.

## Time

- Scene timeline: 48 hours history + current + 24 hours forecast, hourly.
- Historical city averages are broadcast only as city-average markers. Station observations do not exist for those hours; the scene applies the trend as a proportional scale labelled as a modelled or selected-state view.

## Quality

- Rendering budget is target only: 64×64 pollution grid, 500–2000 particles, all buildings simplified.
- Only one pollutant is active at any time (default PM2.5).
- Missing values stay null and are not zero.
- If all sources fail, last good snapshots remain visible, stale state shown.

## Assumption updates

- All changes must be recorded in `docs/DATA.md`.
- See `PLAN.md` section 6.4 for future commute routes (deferred).
- Exposure and single-site wind replacement are explicitly out of scope for V1.
