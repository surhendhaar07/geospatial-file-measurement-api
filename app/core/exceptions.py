from typing import Any


class GeospatialAPIException(Exception):
    """
    Base class for all domain-specific application exceptions.
    """
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Any | None = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class InvalidFileError(GeospatialAPIException):
    """Raised when an uploaded file fails general validation."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message,
            code="INVALID_FILE",
            status_code=400,
            details=details
        )


class EmptyFileError(InvalidFileError):
    """Raised when an uploaded file is empty."""
    def __init__(self, message: str = "Uploaded file is empty (0 bytes)."):
        super().__init__(
            message=message,
            details={"reason": "empty_file"}
        )
        self.code = "EMPTY_FILE"


class UnsupportedFileTypeError(GeospatialAPIException):
    """Raised when a file extension or MIME type is not supported."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message,
            code="UNSUPPORTED_FILE_TYPE",
            status_code=400,
            details=details
        )


class FileSizeExceededError(GeospatialAPIException):
    """Raised when the uploaded file exceeds size limits."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message,
            code="FILE_SIZE_EXCEEDED",
            status_code=413,
            details=details
        )


class CorruptedArchiveError(InvalidFileError):
    """Raised when a zip archive is malformed or corrupted."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message=message, details=details)
        self.code = "CORRUPTED_ARCHIVE"


class PathTraversalError(InvalidFileError):
    """Raised when a zip archive contains unsafe paths (Zip Slip)."""
    def __init__(self, message: str = "Archive contains unsafe file paths (Zip Slip detected)."):
        super().__init__(message=message)
        self.code = "PATH_TRAVERSAL_DETECTED"


class InvalidShapefileError(InvalidFileError):
    """Raised when a shapefile zip archive is missing mandatory components or has multiple ambiguous shapefiles."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message=message, details=details)
        self.code = "INVALID_SHAPEFILE"


class InvalidKMLError(InvalidFileError):
    """Raised when a KML file is invalid or cannot be parsed."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message=message, details=details)
        self.code = "INVALID_KML"


class GeospatialProcessingError(GeospatialAPIException):
    """Raised when reading or extracting features from geospatial data fails."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message,
            code="GEOSPATIAL_PROCESSING_ERROR",
            status_code=422,
            details=details
        )


class CRSProcessingError(GeospatialAPIException):
    """Raised when CRS identification or transformation fails."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message,
            code="CRS_PROCESSING_ERROR",
            status_code=422,
            details=details
        )


class MeasurementError(GeospatialAPIException):
    """Raised when measurement calculation encounters an unexpected failure."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message,
            code="MEASUREMENT_ERROR",
            status_code=422,
            details=details
        )


class EntityNotFoundError(GeospatialAPIException):
    """Raised when a requested resource (e.g., file metadata) is not found."""
    def __init__(self, message: str = "Requested resource not found.", details: Any | None = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details
        )


class FileStorageError(GeospatialAPIException):
    """Raised when filesystem write or cleanup fails."""
    def __init__(self, message: str, details: Any | None = None):
        super().__init__(
            message=message,
            code="FILE_STORAGE_ERROR",
            status_code=500,
            details=details
        )
