import pytest
from pyproj import CRS
from shapely.geometry import LineString, Polygon

from app.core.exceptions import CRSProcessingError
from app.services.crs_service import CRSService


def test_normalize_crs():
    crs_4326 = CRSService.normalize_crs("EPSG:4326")
    assert crs_4326 is not None
    assert crs_4326.to_epsg() == 4326

    crs_int = CRSService.normalize_crs(3857)
    assert crs_int is not None
    assert crs_int.to_epsg() == 3857

    assert CRSService.normalize_crs(None) is None

    with pytest.raises(CRSProcessingError):
        CRSService.normalize_crs("INVALID_CRS_NOT_EXISTING")


def test_format_crs_string():
    crs = CRS.from_epsg(4326)
    assert CRSService.format_crs_string(crs) == "EPSG:4326"
    assert CRSService.format_crs_string(None) == "EPSG:4326"


def test_utm_selection_northern_hemisphere():
    # Berlin, Germany (approx lat 52.52, lon 13.40) -> UTM Zone 33N -> EPSG:32633
    utm_berlin = CRSService.get_utm_crs_for_latlon(lat=52.52, lon=13.40)
    assert utm_berlin.to_epsg() == 32633

    # Bengaluru, India (approx lat 12.97, lon 77.59) -> UTM Zone 43N -> EPSG:32643
    utm_blr = CRSService.get_utm_crs_for_latlon(lat=12.97, lon=77.59)
    assert utm_blr.to_epsg() == 32643

    # New York City (approx lat 40.71, lon -74.00) -> UTM Zone 18N -> EPSG:32618
    utm_nyc = CRSService.get_utm_crs_for_latlon(lat=40.71, lon=-74.00)
    assert utm_nyc.to_epsg() == 32618


def test_utm_selection_southern_hemisphere():
    # Sydney, Australia (approx lat -33.86, lon 151.20) -> UTM Zone 56S -> EPSG:32756
    utm_sydney = CRSService.get_utm_crs_for_latlon(lat=-33.86, lon=151.20)
    assert utm_sydney.to_epsg() == 32756

    # Sao Paulo, Brazil (approx lat -23.55, lon -46.63) -> UTM Zone 23S -> EPSG:32723
    utm_sp = CRSService.get_utm_crs_for_latlon(lat=-23.55, lon=-46.63)
    assert utm_sp.to_epsg() == 32723


def test_utm_selection_polar_regions():
    # Arctic (> 84 deg N)
    arctic = CRSService.get_utm_crs_for_latlon(lat=85.0, lon=20.0)
    assert arctic.to_epsg() == 32661

    # Antarctic (< -80 deg S)
    antarctic = CRSService.get_utm_crs_for_latlon(lat=-82.0, lon=10.0)
    assert antarctic.to_epsg() == 32761


def test_determine_optimal_projected_crs_already_projected():
    projected_src = CRS.from_epsg(32633)
    optimal = CRSService.determine_optimal_projected_crs(source_crs=projected_src, bounds=None)
    assert optimal.to_epsg() == 32633


def test_geographic_crs_transformation_produces_metric_measurements():
    # Polygon ~ 1km x 1km near Berlin in WGS 84 (EPSG:4326)
    # Notice: 0.01 deg lon ~ 680m, 0.01 deg lat ~ 1110m -> approx 754,800 m^2
    poly_wgs84 = Polygon([
        (13.3888, 52.5170),
        (13.3988, 52.5170),
        (13.3988, 52.5270),
        (13.3888, 52.5270),
        (13.3888, 52.5170)
    ])

    # In degrees, raw area is tiny (~ 0.0001 deg^2)
    raw_degree_area = poly_wgs84.area
    assert raw_degree_area < 0.001

    # Optimal UTM projection for Berlin: EPSG:32633
    target_utm = CRSService.get_utm_crs_for_latlon(lat=52.52, lon=13.39)
    projected_poly = CRSService.transform_geometry(
        geom=poly_wgs84,
        source_crs=CRS.from_epsg(4326),
        target_crs=target_utm
    )

    # Metric area in square meters must be realistic (~ 750,000 sq m)
    metric_area = projected_poly.area
    assert 500_000 < metric_area < 1_000_000

    # LineString transformation verification
    line_wgs84 = LineString([(13.3888, 52.5170), (13.3888, 52.5270)])  # 0.01 deg latitude ~ 1113 meters
    raw_degree_length = line_wgs84.length
    assert raw_degree_length < 0.02

    projected_line = CRSService.transform_geometry(
        geom=line_wgs84,
        source_crs=CRS.from_epsg(4326),
        target_crs=target_utm
    )
    metric_length = projected_line.length
    assert 1000 < metric_length < 1200
