from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.common import ErrorResponse
from app.schemas.file import FileInfoResponse, FileListResponse, FileUploadResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a geospatial file",
    description=(
        "Upload a geospatial file (either a `.zip` archive containing an ESRI Shapefile or a `.kml` file). "
        "The file is validated, safely extracted, features and geometries are parsed, "
        "source CRS is identified, geographic coordinates are reprojected into an optimal metric UTM zone, "
        "and area/length measurements are calculated and persisted."
    ),
    responses={
        201: {"description": "File successfully uploaded, parsed, and processed."},
        400: {"model": ErrorResponse, "description": "Invalid file format, empty file, or corrupted archive."},
        422: {"model": ErrorResponse, "description": "Geospatial parsing or CRS processing failure."},
        500: {"model": ErrorResponse, "description": "Internal server or storage error."}
    }
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.zip Shapefile archive or .kml file)"),
    db: Session = Depends(get_db)
) -> FileUploadResponse:
    """
    Handles geospatial file upload and immediate measurement processing.
    """
    return await FileService.process_upload(db=db, upload_file=file)


@router.get(
    "/{id}/",
    response_model=FileInfoResponse,
    summary="Get file metadata and processing status",
    description="Retrieves metadata, processing state, feature count, and CRS information for a specific file by UUID.",
    responses={
        200: {"description": "File metadata and processing status successfully retrieved."},
        404: {"model": ErrorResponse, "description": "File not found."}
    }
)
def get_file(
    id: str,
    db: Session = Depends(get_db)
) -> FileInfoResponse:
    """
    Retrieves file metadata by unique ID.
    """
    return FileService.get_file_info(db=db, file_id=id)


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List uploaded geospatial files",
    description="Retrieves a paginated list of all uploaded and processed geospatial files.",
    responses={
        200: {"description": "List of files successfully retrieved."}
    }
)
def list_files(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    db: Session = Depends(get_db)
) -> FileListResponse:
    """
    Lists files with pagination.
    """
    items, total = FileService.list_files(db=db, skip=skip, limit=limit)
    return FileListResponse(items=items, total=total)
