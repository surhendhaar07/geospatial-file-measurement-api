from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeatureMeasurementItem(BaseModel):
    """
    Measurement result for a single feature within a geospatial file.
    """
    model_config = ConfigDict(from_attributes=True)

    feature_id: int = Field(..., description="Index of the feature within the uploaded dataset (0-indexed)")
    geometry_type: str = Field(..., description="Type of geometry, e.g., Polygon, LineString, Point")
    measurement_type: str | None = Field(None, description="Type of measurement calculated ('area', 'length', or null)")
    value: float | None = Field(None, description="Calculated measurement value, rounded to 4 decimal places")
    unit: str | None = Field(None, description="Measurement unit ('square_meters', 'meters', or null)")
    status: str = Field(..., description="Measurement status: COMPLETED, NOT_REQUIRED, NOT_SUPPORTED, or FAILED")
    properties: dict[str, Any] | None = Field(default_factory=dict, description="Feature attributes/properties")


class FileMeasurementsResponse(BaseModel):
    """
    Full measurements payload returned for a processed geospatial file.
    """
    model_config = ConfigDict(from_attributes=True)

    file_id: str = Field(..., description="Unique file identifier (UUID)")
    filename: str = Field(..., description="Original name of the uploaded file")
    feature_count: int = Field(..., description="Total count of features processed")
    source_crs: str | None = Field(None, description="Detected source coordinate reference system, e.g., EPSG:4326")
    measurement_crs: str | None = Field(None, description="Projected CRS used for measurement calculations, e.g., EPSG:32633")
    measurements: list[FeatureMeasurementItem] = Field(default_factory=list, description="Array of feature measurements")
