import math
from datetime import date, datetime
from typing import Any

import shapely.geometry
from shapely.geometry.base import BaseGeometry


def geometry_to_geojson_dict(geom: BaseGeometry | None) -> dict[str, Any] | None:
    """
    Safely converts a Shapely geometry object to a standard GeoJSON mapping dictionary.
    Returns None if geom is None or empty.
    """
    if geom is None or geom.is_empty:
        return None
    try:
        return shapely.geometry.mapping(geom)
    except Exception:
        return None


def get_geometry_type(geom: BaseGeometry | None) -> str:
    """
    Returns the string name of the geometry type (e.g. 'Polygon', 'LineString', 'Point').
    Returns 'Unknown' if None or unidentifiable.
    """
    if geom is None:
        return "None"
    return getattr(geom, "geom_type", type(geom).__name__)


def sanitize_properties(props: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitizes property values so that they are strictly JSON-compliant.
    Converts dates/datetimes to ISO strings, floats with NaN/Inf to None/str, etc.
    """
    sanitized: dict[str, Any] = {}
    for k, v in props.items():
        if isinstance(v, (datetime, date)):
            sanitized[k] = v.isoformat()
        elif isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                sanitized[k] = None
            else:
                sanitized[k] = v
        elif isinstance(v, bytes):
            sanitized[k] = v.decode("utf-8", errors="replace")
        elif isinstance(v, (str, int, bool)) or v is None:
            sanitized[k] = v
        elif isinstance(v, dict):
            sanitized[k] = sanitize_properties(v)
        elif isinstance(v, (list, tuple)):
            sanitized[k] = [
                x.isoformat() if isinstance(x, (datetime, date)) else x
                for x in v
            ]
        else:
            sanitized[k] = str(v)
    return sanitized
