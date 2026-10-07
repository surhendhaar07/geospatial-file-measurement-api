from shapely.geometry import (
    LinearRing,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry

from app.core.logging import logger
from app.schemas.common import MeasurementStatusEnum, MeasurementTypeEnum, MeasurementUnitEnum


class MeasurementResult:
    def __init__(
        self,
        measurement_type: str | None,
        value: float | None,
        unit: str | None,
        status: str,
        message: str | None = None
    ):
        self.measurement_type = measurement_type
        self.value = value
        self.unit = unit
        self.status = status
        self.message = message


class MeasurementService:
    """
    Calculates geometric measurements on projected geometries:
    - Polygon / MultiPolygon -> Area (square_meters)
    - LineString / MultiLineString / LinearRing -> Length (meters)
    - Point / MultiPoint -> Measurement not required (NOT_REQUIRED)
    - Unsupported / empty geometries -> Gracefully handled (NOT_SUPPORTED)
    """

    @classmethod
    def calculate_measurement(cls, projected_geom: BaseGeometry | None) -> MeasurementResult:
        """
        Inspects the projected geometry and computes the appropriate measurement.
        Ensures unsupported geometry types never crash the service.
        """
        if projected_geom is None or projected_geom.is_empty:
            return MeasurementResult(
                measurement_type=None,
                value=None,
                unit=None,
                status=MeasurementStatusEnum.NOT_SUPPORTED.value,
                message="Geometry is null or empty."
            )

        geom_type = getattr(projected_geom, "geom_type", type(projected_geom).__name__)

        try:
            # 1. Polygons and MultiPolygons -> Area in square meters
            if isinstance(projected_geom, (Polygon, MultiPolygon)) or geom_type in {"Polygon", "MultiPolygon"}:
                area_val = round(float(projected_geom.area), 4)
                return MeasurementResult(
                    measurement_type=MeasurementTypeEnum.AREA.value,
                    value=area_val,
                    unit=MeasurementUnitEnum.SQUARE_METERS.value,
                    status=MeasurementStatusEnum.COMPLETED.value
                )

            # 2. LineStrings and MultiLineStrings -> Length in meters
            if isinstance(projected_geom, (LineString, MultiLineString, LinearRing)) or geom_type in {"LineString", "MultiLineString", "LinearRing"}:
                length_val = round(float(projected_geom.length), 4)
                return MeasurementResult(
                    measurement_type=MeasurementTypeEnum.LENGTH.value,
                    value=length_val,
                    unit=MeasurementUnitEnum.METERS.value,
                    status=MeasurementStatusEnum.COMPLETED.value
                )

            # 3. Points and MultiPoints -> No measurement required
            if isinstance(projected_geom, (Point, MultiPoint)) or geom_type in {"Point", "MultiPoint"}:
                return MeasurementResult(
                    measurement_type=None,
                    value=None,
                    unit=None,
                    status=MeasurementStatusEnum.NOT_REQUIRED.value,
                    message="Point geometry does not require area or length measurement."
                )

            # 4. Any other geometry (e.g. GeometryCollection) -> Unsupported gracefully
            logger.warning(f"Unsupported geometry type encountered for measurement: {geom_type}")
            return MeasurementResult(
                measurement_type=None,
                value=None,
                unit=None,
                status=MeasurementStatusEnum.NOT_SUPPORTED.value,
                message=f"Measurement is not supported for geometry type '{geom_type}'."
            )

        except Exception as e:
            logger.error(f"Error calculating measurement for geometry type {geom_type}: {e}", exc_info=True)
            return MeasurementResult(
                measurement_type=None,
                value=None,
                unit=None,
                status=MeasurementStatusEnum.FAILED.value,
                message=f"Calculation error: {e!s}"
            )
