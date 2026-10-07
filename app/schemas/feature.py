from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeatureResponse(BaseModel):
    """
    Representation of an individual geospatial feature.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique database UUID for this feature")
    file_id: str = Field(..., description="ID of the parent file")
    feature_index: int = Field(..., description="Index of the feature within the dataset")
    geometry_type: str = Field(..., description="Geometry type (e.g. Polygon, LineString, Point)")
    geometry: dict[str, Any] | None = Field(None, description="GeoJSON-compatible geometry representation")
    properties: dict[str, Any] = Field(default_factory=dict, description="Feature attributes and metadata")
