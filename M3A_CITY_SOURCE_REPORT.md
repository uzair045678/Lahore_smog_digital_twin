# M3A — Lahore City Source and Coverage Evaluation

**Evaluation date:** 2026-11-03 (Asia/Karachi)  
**Status:** Complete for M3A source/coverage evaluation. The existing production baseline was not changed.

## Scope and method

This report evaluates the existing Lahore boundary, the current city pipeline, OSM access, and a bounded Overture building extraction. It does not normalize geometry, generate city assets, choose tiles, or alter the renderer.

The approved extraction bounds are the bounding box of the existing OSM district relation `16117666`:

```text
south 31.2005939   north 31.7134238
west  74.0068490   east  74.6546712
```

The outer relation geometry contains 1,642 points. Its approximate footprint is 1,696.6 km², with an extent of about 56.7 km north/south by 61.5 km east/west. The area calculation is a local equirectangular shoelace estimate, suitable for bounding the evaluation rather than for production GIS work.

No permanent extraction buffer is part of the current baseline. M3B should use a small processing buffer (for example, 100 m) only to avoid edge truncation, then clip features back to the verified boundary. That would not expand the city product into the surrounding region.

## Existing city baseline

| Item | Evidence |
|---|---|
| Current source | `scripts/sources/lahore_boundary.json`, OSM relation `16117666`; station registry `pipeline/config/stations.json` |
| Current geometry | `web/public/city/lahore.json`: 184 simplified boundary points, 11 stations, 0 roads, 0 buildings |
| Projection | Build script uses a local equirectangular approximation around 31.5204, 74.3587 |
| Current renderer | `CityScene.ts` renders the boundary and stations; it does not load buildings |
| Main limitations | No building footprints, no roads, no height metadata, no provenance per feature, and no tiled runtime representation |

The existing `scripts/build_city.py` is therefore a reference/greybox baseline only. It is not evidence of building or road coverage.

## OSM evaluation

OSM remains the primary candidate under PLAN.md. A temporary regional PBF was obtained from [Geofabrik's Pakistan download](https://download.geofabrik.de/asia/pakistan.html) and filtered locally against the existing boundary. The provider listed the current extract as 150 MB, last modified 2026-11-01, containing OSM data through `2026-11-01T21:21:36Z`. The raw PBF was not committed.

Measured building ways inside the boundary:

| Measure | Count | Percentage |
|---|---:|---:|
| Building ways examined | 28,698 | 100.000% |
| Valid closed polygon ways | 28,695 | 99.990% |
| Invalid or unclosed ways | 3 | 0.010% |
| Explicit numeric `height` | 1,158 | 4.035% |
| Numeric `building:levels` | 13,760 | 47.948% |
| Both height and levels | 1,002 | 3.491% |
| Neither height nor levels | 14,782 | 51.509% |

The height and level percentages overlap because the `both` row is included in each source-tag total. Numeric parsing was conservative; malformed height strings were treated as missing in this evaluation and require an explicit categorized audit during M3B normalization. Building relations were observed in the regional PBF but were not counted as footprints because relation-member reconstruction belongs to normalization; the simple-way total must not be read as a complete multipolygon total.

Building type counts were led by `house` (15,167), `yes` (11,347), `commercial` (688), `industrial` (349), `residential` (290), `school` (161), and `university` (120). This is useful metadata but not a claim that every generic `yes` feature has a reliable semantic type.

The 10×10 density check shows strong spatial variation rather than uniform coverage. The densest valid-polygon cells contained 10,553, 4,100, 2,073, 1,787 and 1,590 building ways; many peripheral cells were empty or contained only 1–12 features. Empty cells are not automatically mapping gaps because the boundary includes agricultural, institutional, airport and other low-building land; M3B should classify land context before interpreting them.

Road measurements inside the boundary:

| Class | Ways | Approx. length km |
|---|---:|---:|
| motorway | 202 | 187.64 |
| motorway_link | 295 | 94.04 |
| trunk | 216 | 242.05 |
| trunk_link | 214 | 27.71 |
| primary | 650 | 504.88 |
| primary_link | 463 | 39.25 |
| secondary | 1,572 | 877.41 |
| tertiary | 2,814 | 1,561.74 |
| residential | 66,420 | 11,909.55 |
| service | 10,575 | 968.26 |
| unclassified | 3,348 | 1,568.81 |
| living_street | 10,907 | 1,043.46 |

The extract is sufficient to represent recognizable major roads and a simplified LOW road network. Lengths are geodesic sums of source way vertices and are preliminary; clipping, deduplication and relation handling remain M3B work.

## Overture evaluation

Overture was evaluated only after inspecting the OSM baseline. A temporary, non-repository extraction was made with the official `overturemaps` client using the exact boundary bounding box:

```text
type: building
bbox: 74.0068490,31.2005939,74.6546712,31.7134238
format: GeoJSON Sequence
release selected by client: current release at evaluation time
```

Measured result:

| Measure | Result |
|---|---:|
| Features | 1,501,503 |
| Features with geometry | 1,501,503 (100.000%) |
| Temporary raw size | 842,119,268 bytes |
| Explicit Overture `height` | 1,634 (0.109%) |
| Overture floor metadata (`num_floors` or `building:levels`) | 14,237 (0.948%) |
| Neither of those metadata fields | 1,485,632 (98.943%) |
| Malformed GeoJSON records | 0 |

The output source labels were: Google Open Buildings 833,932; Microsoft ML Buildings 637,911; OpenStreetMap 29,660. These are source contributions in the Overture result, not an OSM/Overture overlap measurement.

A 0.10° × 0.10° central Lahore probe returned 161,288 features in 92,227,768 bytes. It had 46 explicit heights (0.029%), 4,620 level values (2.864%), and 97.107% with neither field. This probe demonstrates the scale and metadata sparsity but is not used to extrapolate citywide coverage.

The OSM-versus-Overture measurements are not direct one-to-one overlap measurements: Overture combines multiple upstream datasets and the temporary Overture result was not normalized against OSM identities. The Overture result contains 29,660 features labeled as OSM, compared with 28,698 OSM building ways measured locally; this is only a source-composition sanity check, not an overlap rate. A defensible duplicate/geometry-disagreement analysis belongs in M3B only if supplementation is still justified.

## Source comparison and provisional recommendation

### OSM strengths

- Primary source required by the approved plan.
- Provides editable building/road tags, highway classes, `height`, and `building:levels` where mapped.
- ODbL provenance is well understood and the existing Lahore boundary is already sourced from OSM.
- Likely better suited to a reproducible, selective, road-aware city pipeline than blindly ingesting every footprint from a composite dataset.

### OSM weaknesses

- Coverage and metadata completeness for Lahore were not measurable from the public endpoints during this run.
- The current repository has no building or road extract.
- Missing heights will require the deterministic fallback policy specified by PLAN.md.

### Overture strengths

- Bounded cloud extraction is reproducible and returned complete geometries for the measured extraction.
- It provides very large footprint coverage and source provenance fields.
- It can combine multiple upstream footprint sources.

### Overture weaknesses

- The measured result is very large (842 MB raw for buildings alone) and 98.943% lacks the evaluated height/level metadata.
- It introduces multiple upstream licenses, attribution obligations, duplicate/reconciliation complexity, and possible OSM-derived content.
- No measured Lahore-specific improvement over OSM can be claimed until a comparable OSM extract is available.

### Source strategy

**OSM only for the canonical dataset.**

The measured OSM baseline already provides 28,698 building ways and a substantial classified road network across the approved boundary. Overture adds 1.50 million composite footprints but supplies height or level metadata for only 1.057% of them and would add considerable reconciliation and licensing complexity. Selective Overture supplementation is not justified by the current evidence. If a later spatial audit finds a material, localized OSM gap, it can be reconsidered without changing the HIGH/LOW shared-canonical architecture.

## Roads

The current production city has `road_count: 0`, and `scripts/sources/lahore_roads.json` does not exist. Therefore recognizable major-road structure and a simplified LOW road representation are not yet demonstrated. No road mesh or road asset was generated in M3A.

## CRS preliminary evaluation

The approved bounds span approximately 74.01°E–74.65°E and 31.20°N–31.71°N. UTM Zone 43N covers longitudes 72°E–78°E, so EPSG:32643 contains the entire extraction area and avoids a zone boundary. Its metric coordinates are appropriate for the roughly 57–62 km city extent and for using one common projected frame for stations, roads, buildings and the boundary.

The repository does not currently depend on `pyproj`, so no numerical CRS distortion benchmark was added or run in M3A. The existing equirectangular transform remains unchanged. **Recommendation for M3B:** validate EPSG:32643 with a reproducible projection check and replace the approximation only after alignment tests cover stations, boundary, roads and future buildings.

## Licensing and provenance

- **OSM:** OpenStreetMap contributors; ODbL. Required attribution should link to `https://www.openstreetmap.org/copyright` and preserve applicable database/share-alike obligations. Boundary source currently records relation `16117666`; the next extract must record source date, endpoint, query and exact bounds.
- **Overture:** Overture Maps building data is distributed under the documented theme terms and includes upstream-source obligations. The measured result includes OpenStreetMap, Google Open Buildings and Microsoft ML Buildings contributions, so attribution and license review must cover those upstream datasets before any redistribution.
- **Endpoints/methods used:** existing cached OSM relation; Geofabrik Pakistan PBF, filtered locally with an isolated `uv` environment using `osmium` and `shapely`; Overpass public API attempts; OSM map API probe; official Overture Maps Python client with bounded bbox. Temporary PBF and Overture files were kept outside the repository and are not production assets.

## Data/performance implications

- Existing boundary JSON: 66,948 bytes; current production city JSON contains no buildings or roads.
- OSM PBF source: approximately 158 MB on disk; 28,698 building ways and more than 100,000 road ways in the approved boundary.
- Overture buildings alone: 842,119,268 bytes raw for 1.50 million features. This is not suitable for direct browser JSON delivery and reinforces the need for normalized, tiled browser-native assets in later subphases.
- The Overture result's metadata sparsity means a deterministic height strategy will be needed even if Overture is later used.
- No final tile size, runtime format, geometry budget, or HIGH/LOW asset was selected; those are M3C–M3E work and were intentionally skipped.

## Regression tests

- Geographic alignment: **PASS** — `python scripts/test_geo_alignment.py`; 1,642 source boundary points simplified to 184, 11 stations, all inside.
- Frontend: **PASS** — `npm test -- --run`; 5 files, 25 tests.
- TypeScript: **PASS** — `npx tsc --noEmit`.
- Production build: **PASS** — `npm run build`; Vite build succeeded. Existing chunk-size warning remains.

## M3A conclusion

The production city was not modified. M3A source and coverage evidence is now sufficient to recommend OSM-only and proceed to owner review for M3B. The OSM scan remains a preliminary way-level evaluation: multipolygon reconstruction, exact malformed-tag categories, clipping, deduplication and canonical normalization are intentionally deferred.

