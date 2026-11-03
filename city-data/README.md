# Canonical Lahore geographic dataset

`canonical/lahore.json` is the rendering-independent MAP-2/M3B output. It is generated offline from a temporary Geofabrik Pakistan OpenStreetMap PBF with `scripts/normalize_city.py`.

The final inclusion boundary is the existing OpenStreetMap relation 16117666 in `scripts/sources/lahore_boundary.json`; the rectangular bounds are only a deterministic processing optimization with a 0.001° buffer. Geometry is projected from WGS84 (`EPSG:4326`) to UTM Zone 43N (`EPSG:32643`) and then translated to local meters around the existing Lahore origin (31.5204, 74.3587). X is east and Y is north.

Building height precedence is valid explicit metres/feet, valid `building:levels` multiplied by 3.2 m, then a deterministic type-based fallback. Every accepted height records `explicit`, `levels`, or `fallback`. Invalid geometry is repaired only with Shapely `buffer(0)` when the result remains a polygon; otherwise it is rejected. Building multipolygon relations are emitted as relation records and their member ways are not emitted separately.

The dataset describes geography and provenance only. It contains no HIGH/LOW materials, meshes, tiles, renderer settings, or production `lahore.json` replacement. Both future representations must consume this exact file.
