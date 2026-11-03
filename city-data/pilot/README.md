# MAP-3 Lahore pilot

The selected pilot is `central_gulberg`, bounded by WGS84 `74.30,31.45` to `74.38,31.53`. It is selected from the canonical dataset using bounds-intersection selection; no source features are reacquired or mutated.

The candidate score rewards a repeatable development-sized building count, all three canonical height sources, class and road diversity, complex footprints, holes, and enough roads for alignment tests. `central_gulberg` scored 16. `old_city_east` also scored 16, so the documented tie-break prefers more non-fallback height metadata and then more building classes: central_gulberg has 2,114 non-fallback heights and 15 classes versus 44 and 11. The other candidates scored 13 or below.

The pilot contains 4,475 buildings, 9,957 roads, 1,707.135 km of road geometry, 41 explicit heights, 2,073 levels-derived heights, 2,361 fallback heights, 61 accepted multipolygon records, 137 hole rings, 526 complex footprints, and 20 road classes. It remains in the full canonical EPSG:32643/local coordinate frame.

M3B retained rejection counts and reason categories but not rejected relation IDs or geometries. Therefore this pilot cannot associate individual rejected relation IDs without reacquiring the OSM source, which MAP-3 forbids. The pilot does include accepted multipolygons and holes, and the canonical geometry tests pass; no systematic relation-normalization failure is indicated by the available canonical evidence.

Future HIGH and LOW pilot work must consume `lahore_pilot.json` unchanged. No meshes, GLBs, tiles, or renderer assets are included here.
