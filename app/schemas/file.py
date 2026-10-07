from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class FileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique file UUID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Type of geospatial file: SHAPEFILE_ZIP or KML")
    file_size: int = Field(..., description="Size of the file in bytes")
    feature_count: int = Field(..., description="Total extracted feature count")
    source_crs: str | None = Field(None, description="Original coordinate reference system detected in the file")
    measurement_crs: str | None = Field(None, description="Projected CRS used for calculating measurements")
    status: str = Field(..., description="Current status: UPLOADED, PROCESSING, COMPLETED, or FAILED")
    uploaded_at: datetime = Field(..., description="UTC timestamp of file upload")
    processed_at: datetime | None = Field(None, description="UTC timestamp when processing finished")
    error_message: str | None = Field(None, description="Detailed error description if processing failed")

    @computed_field
    def crs(self) -> str | None:
        """Convenience alias for source_crs to match assignment specification."""
        return self.source_crs


class FileUploadResponse(BaseModel):
    """Response returned upon initial file upload and processing."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique file UUID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Type of file: SHAPEFILE_ZIP or KML")
    file_size: int = Field(..., description="Size in bytes")
    feature_count: int = Field(..., description="Extracted feature count")
    crs: str | None = Field(None, description="Source CRS")
    source_crs: str | None = Field(None, description="Source CRS")
    measurement_crs: str | None = Field(None, description="Projected CRS used for measurement")
    status: str = Field(..., description="Processing status")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    processed_at: datetime | None = Field(None, description="Processing timestamp")


class FileInfoResponse(FileBase):
    """Detailed file information response."""


class FileListResponse(BaseModel):
    """Paginated or listed files response."""
    items: list[FileInfoResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total count of files stored")
