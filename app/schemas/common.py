from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FileStatusEnum(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MeasurementStatusEnum(str, Enum):
    COMPLETED = "COMPLETED"
    NOT_REQUIRED = "NOT_REQUIRED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    FAILED = "FAILED"


class MeasurementTypeEnum(str, Enum):
    AREA = "area"
    LENGTH = "length"


class MeasurementUnitEnum(str, Enum):
    SQUARE_METERS = "square_meters"
    METERS = "meters"


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable error description")
    details: Any | None = Field(default=None, description="Additional context or validation errors")


class ErrorResponse(BaseModel):
    error: ErrorDetail = Field(..., description="Top-level standardized error envelope")
