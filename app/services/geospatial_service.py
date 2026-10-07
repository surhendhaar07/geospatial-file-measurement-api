import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import geopandas as gpd
from pyproj import CRS
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

from app.core.exceptions import GeospatialProcessingError
from app.core.logging import logger
from app.services.crs_service import CRSService
from app.utils.geometry_utils import get_geometry_type, sanitize_properties


@dataclass
class ExtractedFeature:
    """Represents a parsed geospatial feature prior to projection and persistence."""
    index: int
    geometry: BaseGeometry | None
    geometry_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDataset:
    """Represents the complete parsed dataset from a geospatial file."""
    features: list[ExtractedFeature]
    source_crs: CRS | None
    bounds: tuple[float, float, float, float] | None = None


class GeospatialService:
    """
    Handles reading, parsing, and feature extraction from Shapefiles and KML files.
    """

    @classmethod
    def read_shapefile(cls, shp_path: str) -> ExtractedDataset:
        """
        Reads an ESRI Shapefile using GeoPandas / PyOGRIO.
        Extracts all features, attributes, geometries, and source CRS.
        """
        try:
            logger.info(f"Reading Shapefile from path: {shp_path}")
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            logger.error(f"Failed to read Shapefile '{shp_path}': {e}", exc_info=True)
            raise GeospatialProcessingError(
                message=f"Failed to read Shapefile: {e!s}",
                details={"file": os.path.basename(shp_path), "error": str(e)}
            )

        return cls._parse_geodataframe(gdf)

    @classmethod
    def read_kml(cls, kml_path: str) -> ExtractedDataset:
        """
        Reads a KML file. Attempts GeoPandas/PyOGRIO first, with a fallback
        to standalone XML KML placemark parser to ensure compatibility across all KML variations.
        """
        logger.info(f"Reading KML from path: {kml_path}")
        
        # Primary attempt: GeoPandas reading
        try:
            gdf = gpd.read_file(kml_path)
            if gdf is not None and not gdf.empty:
                logger.info(f"Successfully loaded KML via GeoPandas. Features: {len(gdf)}")
                # Ensure KML default CRS EPSG:4326 if not set
                if gdf.crs is None:
                    gdf = gdf.set_crs(epsg=4326)
                return cls._parse_geodataframe(gdf)
        except Exception as primary_err:
            logger.warning(f"GeoPandas direct KML read produced: {primary_err}. Falling back to internal KML parser.")

        # Fallback parser using ElementTree and Shapely
        try:
            return cls._parse_kml_fallback(kml_path)
        except Exception as fallback_err:
            logger.error(f"Failed to parse KML '{kml_path}': {fallback_err}", exc_info=True)
            raise GeospatialProcessingError(
                message=f"Failed to parse KML file: {fallback_err!s}",
                details={"file": os.path.basename(kml_path), "error": str(fallback_err)}
            )

    @classmethod
    def _parse_geodataframe(cls, gdf: gpd.GeoDataFrame) -> ExtractedDataset:
        """
        Normalizes a GeoPandas GeoDataFrame into our standardized ExtractedDataset structure.
        """
        source_crs = CRSService.normalize_crs(gdf.crs)

        features: list[ExtractedFeature] = []
        bounds = None

        if not gdf.empty:
            try:
                total_bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
                bounds = (float(total_bounds[0]), float(total_bounds[1]), float(total_bounds[2]), float(total_bounds[3]))
            except Exception:
                bounds = None

        # Extract features
        prop_cols = [c for c in gdf.columns if c != gdf.geometry.name]

        for idx, row in gdf.iterrows():
            geom = row.get(gdf.geometry.name)
            props_raw = {col: row[col] for col in prop_cols}
            sanitized_props = sanitize_properties(props_raw)

            features.append(
                ExtractedFeature(
                    index=len(features),
                    geometry=geom if geom is not None and not geom.is_empty else None,
                    geometry_type=get_geometry_type(geom),
                    properties=sanitized_props
                )
            )

        logger.info(f"Extracted {len(features)} features. Source CRS: {CRSService.format_crs_string(source_crs)}")
        return ExtractedDataset(
            features=features,
            source_crs=source_crs,
            bounds=bounds
        )

    @classmethod
    def _parse_kml_fallback(cls, kml_path: str) -> ExtractedDataset:
        """
        Fallback parser that extracts Placemarks (Points, LineStrings, Polygons)
        directly from KML XML according to OGC KML 2.2 specification.
        """
        tree = ET.parse(kml_path)
        root = tree.getroot()

        # Extract namespace if present
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        features: list[ExtractedFeature] = []
        all_coords: list[tuple[float, float]] = []

        placemarks = root.findall(f".//{ns}Placemark")
        for idx, pm in enumerate(placemarks):
            # Extract basic placemark properties
            name_el = pm.find(f"{ns}name")
            desc_el = pm.find(f"{ns}description")
            
            properties: dict[str, Any] = {}
            if name_el is not None and name_el.text:
                properties["name"] = name_el.text.strip()
            if desc_el is not None and desc_el.text:
                properties["description"] = desc_el.text.strip()

            # Parse ExtendedData if present
            ext_data = pm.find(f"{ns}ExtendedData")
            if ext_data is not None:
                for data_el in ext_data.findall(f"{ns}Data"):
                    data_name = data_el.attrib.get("name")
                    val_el = data_el.find(f"{ns}value")
                    if data_name and val_el is not None and val_el.text:
                        properties[data_name] = val_el.text.strip()

            # Geometry extraction
            geom = None

            # 1. Polygon
            poly_el = pm.find(f".//{ns}Polygon")
            if poly_el is not None:
                coord_el = poly_el.find(f".//{ns}outerBoundaryIs//{ns}coordinates")
                if coord_el is not None and coord_el.text:
                    pts = cls._parse_coord_string(coord_el.text)
                    if len(pts) >= 3:
                        geom = Polygon(pts)
                        all_coords.extend(pts)

            # 2. LineString
            if geom is None:
                line_el = pm.find(f".//{ns}LineString")
                if line_el is not None:
                    coord_el = line_el.find(f".//{ns}coordinates")
                    if coord_el is not None and coord_el.text:
                        pts = cls._parse_coord_string(coord_el.text)
                        if len(pts) >= 2:
                            geom = LineString(pts)
                            all_coords.extend(pts)

            # 3. Point
            if geom is None:
                pt_el = pm.find(f".//{ns}Point")
                if pt_el is not None:
                    coord_el = pt_el.find(f".//{ns}coordinates")
                    if coord_el is not None and coord_el.text:
                        pts = cls._parse_coord_string(coord_el.text)
                        if pts:
                            geom = Point(pts[0])
                            all_coords.append(pts[0])

            features.append(
                ExtractedFeature(
                    index=idx,
                    geometry=geom,
                    geometry_type=get_geometry_type(geom),
                    properties=sanitize_properties(properties)
                )
            )

        # Compute bounding box
        bounds = None
        if all_coords:
            xs = [p[0] for p in all_coords]
            ys = [p[1] for p in all_coords]
            bounds = (min(xs), min(ys), max(xs), max(ys))

        # Standard KML is WGS 84 (EPSG:4326)
        source_crs = CRS.from_epsg(4326)
        return ExtractedDataset(
            features=features,
            source_crs=source_crs,
            bounds=bounds
        )

    @staticmethod
    def _parse_coord_string(coord_str: str) -> list[tuple[float, float]]:
        """
        Parses KML coordinate tuple list (lon,lat[,alt]).
        """
        points: list[tuple[float, float]] = []
        for token in coord_str.strip().split():
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    points.append((lon, lat))
                except ValueError:
                    continue
        return points
