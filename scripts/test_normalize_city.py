from normalize_city import (
    FLOOR_HEIGHT_M,
    ORIGIN_LAT,
    ORIGIN_LON,
    WGS84_TO_UTM,
    UTM_TO_WGS84,
    WayData,
    MemberData,
    RelationData,
    boundary_geometry,
    finite_number,
    height_for,
    normalized_geometry,
    relation_geometry,
)
from shapely.geometry import Polygon
import pytest


def test_projection_round_trip_and_orientation() -> None:
    easting, northing = WGS84_TO_UTM.transform(ORIGIN_LON, ORIGIN_LAT)
    east2, north2 = WGS84_TO_UTM.transform(ORIGIN_LON + 0.01, ORIGIN_LAT + 0.01)
    lon, lat = UTM_TO_WGS84.transform(easting, northing)
    assert abs(lon - ORIGIN_LON) < 1e-8
    assert abs(lat - ORIGIN_LAT) < 1e-8
    assert east2 > easting and north2 > northing
    assert 900 < east2 - easting < 1100
    assert 1000 < north2 - northing < 1200


def test_height_precedence_and_malformed_values() -> None:
    assert finite_number("12 m", maximum=150) == 12
    assert round(finite_number("39 ft", maximum=150), 3) == 11.887
    assert finite_number("12-15", maximum=150) is None
    assert height_for({"height": "12", "building:levels": "3"}, "house") == (12.0, "explicit", None)
    assert height_for({"building:levels": "3"}, "house")[1:] == ("levels", None)
    assert height_for({"building:levels": "3"}, "house")[0] == pytest.approx(3 * FLOOR_HEIGHT_M)
    assert height_for({"height": "unknown"}, "house") == (6.0, "fallback", "height")


def test_multipolygon_relation_preserves_hole() -> None:
    outer = WayData(1, {}, [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    inner = WayData(2, {}, [(3, 3), (7, 3), (7, 7), (3, 7), (3, 3)])
    relation = RelationData(3, {"building": "yes", "type": "multipolygon"}, [MemberData("w", 1, "outer"), MemberData("w", 2, "inner")])
    geometry = relation_geometry(relation, {1: outer, 2: inner})
    assert geometry is not None
    assert len(geometry.interiors) == 1
    assert geometry.area == 84


def test_boundary_is_one_polygon_and_invalid_geometry_is_repaired_or_rejected() -> None:
    boundary, bounds = boundary_geometry()
    assert boundary.is_valid
    assert bounds[0] < bounds[2] and bounds[1] < bounds[3]
    geometry, status = normalized_geometry(Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]), boundary)
    assert geometry is None or status in {"repaired", "rejected_outside_boundary"}
