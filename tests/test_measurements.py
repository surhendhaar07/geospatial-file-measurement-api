from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)

from app.schemas.common import MeasurementStatusEnum, MeasurementTypeEnum, MeasurementUnitEnum
from app.services.measurement_service import MeasurementService


def test_polygon_area_measurement():
    # Unit square: 10m x 10m -> 100 m^2
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    result = MeasurementService.calculate_measurement(poly)

    assert result.status == MeasurementStatusEnum.COMPLETED.value
    assert result.measurement_type == MeasurementTypeEnum.AREA.value
    assert result.unit == MeasurementUnitEnum.SQUARE_METERS.value
    assert result.value == 100.0


def test_multipolygon_area_measurement():
    poly1 = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    poly2 = Polygon([(20, 20), (30, 20), (30, 30), (20, 30), (20, 20)])
    multipoly = MultiPolygon([poly1, poly2])
    result = MeasurementService.calculate_measurement(multipoly)

    assert result.status == MeasurementStatusEnum.COMPLETED.value
    assert result.measurement_type == MeasurementTypeEnum.AREA.value
    assert result.unit == MeasurementUnitEnum.SQUARE_METERS.value
    assert result.value == 200.0


def test_linestring_length_measurement():
    # 3-4-5 right triangle hypotenuse + straight segment: length = 5 + 10 = 15m
    line = LineString([(0, 0), (3, 4), (13, 4)])
    result = MeasurementService.calculate_measurement(line)

    assert result.status == MeasurementStatusEnum.COMPLETED.value
    assert result.measurement_type == MeasurementTypeEnum.LENGTH.value
    assert result.unit == MeasurementUnitEnum.METERS.value
    assert result.value == 15.0


def test_multilinestring_length_measurement():
    line1 = LineString([(0, 0), (10, 0)])
    line2 = LineString([(0, 10), (0, 20)])
    multiline = MultiLineString([line1, line2])
    result = MeasurementService.calculate_measurement(multiline)

    assert result.status == MeasurementStatusEnum.COMPLETED.value
    assert result.measurement_type == MeasurementTypeEnum.LENGTH.value
    assert result.unit == MeasurementUnitEnum.METERS.value
    assert result.value == 20.0


def test_point_measurement_not_required():
    pt = Point(50, 100)
    result = MeasurementService.calculate_measurement(pt)

    assert result.status == MeasurementStatusEnum.NOT_REQUIRED.value
    assert result.measurement_type is None
    assert result.value is None
    assert result.unit is None


def test_multipoint_measurement_not_required():
    mpt = MultiPoint([(10, 20), (30, 40)])
    result = MeasurementService.calculate_measurement(mpt)

    assert result.status == MeasurementStatusEnum.NOT_REQUIRED.value
    assert result.value is None


def test_unsupported_geometry_collection_graceful():
    geom_col = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])
    result = MeasurementService.calculate_measurement(geom_col)

    # Must NOT crash, returns NOT_SUPPORTED
    assert result.status == MeasurementStatusEnum.NOT_SUPPORTED.value
    assert result.value is None
    assert result.unit is None


def test_null_or_empty_geometry_graceful():
    empty_poly = Polygon()
    result = MeasurementService.calculate_measurement(empty_poly)
    assert result.status == MeasurementStatusEnum.NOT_SUPPORTED.value

    none_result = MeasurementService.calculate_measurement(None)
    assert none_result.status == MeasurementStatusEnum.NOT_SUPPORTED.value
