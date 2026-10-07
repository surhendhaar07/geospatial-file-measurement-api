import math

import pyproj
import shapely.ops
from pyproj import CRS
from pyproj.exceptions import CRSError
from shapely.geometry.base import BaseGeometry

from app.core.exceptions import CRSProcessingError
from app.core.logging import logger


class CRSService:
    """
    Service responsible for Coordinate Reference System (CRS) detection,
    validation, projected CRS selection (e.g., local UTM zone based on feature centroid),
    and geometric coordinate transformations.
    """

    @staticmethod
    def normalize_crs(crs_input: str | int | CRS | dict | None) -> CRS | None:
        """
        Parses and normalizes any user, GeoPandas, or file CRS representation into a PyProj CRS object.
        Returns None if CRS is not provided.
        """
        if crs_input is None:
            return None
        try:
            if isinstance(crs_input, CRS):
                return crs_input
            return CRS.from_user_input(crs_input)
        except (CRSError, Exception) as e:
            logger.warning(f"Could not parse CRS '{crs_input}': {e}")
            raise CRSProcessingError(
                message=f"Invalid or unrecognized coordinate reference system: '{crs_input}'",
                details={"provided_crs": str(crs_input), "error": str(e)}
            )

    @staticmethod
    def format_crs_string(crs: CRS | None) -> str:
        """
        Formats a PyProj CRS object into a standardized string (e.g., 'EPSG:4326').
        """
        if crs is None:
            return "EPSG:4326"
        epsg = crs.to_epsg()
        if epsg is not None:
            return f"EPSG:{epsg}"
        auth = crs.to_authority()
        if auth:
            return f"{auth[0]}:{auth[1]}"
        return crs.name or "UNKNOWN_CRS"

    @classmethod
    def determine_optimal_projected_crs(
        cls,
        source_crs: CRS | None,
        bounds: tuple[float, float, float, float] | None = None
    ) -> CRS:
        """
        Determines the optimal projected coordinate system for metric measurements:
        1. If source_crs is already projected and utilizes linear metric units, keeps source_crs.
        2. If source_crs is geographic (e.g. EPSG:4326) or unknown, computes the dataset's centroid
           and calculates the appropriate Universal Transverse Mercator (UTM) or Polar Stereographic zone.
        """
        if source_crs is not None and source_crs.is_projected:
            # Check unit of measurement (meters)
            axis_units = [axis.unit_name.lower() for axis in source_crs.axis_info if hasattr(axis, 'unit_name')]
            if any("metre" in u or "meter" in u for u in axis_units):
                logger.info(f"Source CRS '{cls.format_crs_string(source_crs)}' is already projected in metric units.")
                return source_crs

        # If source is geographic or non-metric projected, calculate optimal UTM from bounds
        if bounds is not None:
            minx, miny, maxx, maxy = bounds
            center_lon = (minx + maxx) / 2.0
            center_lat = (miny + maxy) / 2.0
            return cls.get_utm_crs_for_latlon(center_lat, center_lon)

        # Fallback to World Mercator (EPSG:3857) if no bounds provided
        logger.warning("No geographic bounds available for UTM zone calculation; falling back to EPSG:3857.")
        return CRS.from_epsg(3857)

    @classmethod
    def get_utm_crs_for_latlon(cls, lat: float, lon: float) -> CRS:
        """
        Computes the standard UTM EPSG projection code based on geographic latitude and longitude.
        Handles polar exceptions (UPS North / South) for extreme latitudes.
        """
        # Clamp latitude and longitude within physical bounds
        lat = max(-90.0, min(90.0, lat))
        lon = max(-180.0, min(180.0, lon))

        # Polar stereographic for extreme arctic/antarctic latitudes
        if lat > 84.0:
            logger.info("Latitude > 84 deg N detected; selecting Arctic UPS North (EPSG:32661).")
            return CRS.from_epsg(32661)
        if lat < -80.0:
            logger.info("Latitude < 80 deg S detected; selecting Antarctic UPS South (EPSG:32761).")
            return CRS.from_epsg(32761)

        # Calculate standard UTM zone: 1 to 60
        zone = math.floor((lon + 180.0) / 6.0) + 1
        zone = max(1, min(60, zone))

        if lat >= 0:
            epsg_code = 32600 + zone  # WGS 84 / UTM zone XN
        else:
            epsg_code = 32700 + zone  # WGS 84 / UTM zone XS

        logger.info(f"Calculated UTM zone {zone} ({'N' if lat >= 0 else 'S'}) -> EPSG:{epsg_code} for centroid ({lat:.4f}, {lon:.4f})")
        return CRS.from_epsg(epsg_code)

    @classmethod
    def transform_geometry(
        cls,
        geom: BaseGeometry,
        source_crs: CRS | None,
        target_crs: CRS
    ) -> BaseGeometry:
        """
        Transforms a Shapely geometry from source_crs to target_crs.
        If source_crs is None, assumes EPSG:4326.
        """
        if geom is None or geom.is_empty:
            return geom

        src = source_crs if source_crs is not None else CRS.from_epsg(4326)

        # If already matching target projection, return geometry unchanged
        if src == target_crs or src.to_epsg() == target_crs.to_epsg():
            return geom

        try:
            transformer = pyproj.Transformer.from_crs(src, target_crs, always_xy=True)
            projected_geom = shapely.ops.transform(transformer.transform, geom)
            return projected_geom
        except Exception as e:
            logger.error(f"Error transforming geometry from {cls.format_crs_string(src)} to {cls.format_crs_string(target_crs)}: {e}")
            raise CRSProcessingError(
                message=f"Failed to transform geometry coordinates to projected CRS '{cls.format_crs_string(target_crs)}'.",
                details={"source_crs": cls.format_crs_string(src), "target_crs": cls.format_crs_string(target_crs), "error": str(e)}
            )
