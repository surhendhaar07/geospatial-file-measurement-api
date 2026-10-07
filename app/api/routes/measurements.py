from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.common import ErrorResponse
from app.schemas.measurement import FileMeasurementsResponse
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Measurements"])


@router.get(
    "/{id}/measurements/",
    response_model=FileMeasurementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get measurements for features in a file",
    description=(
        "Retrieves feature-level measurement results for the specified file. "
        "Polygon features report area in square meters. "
        "LineString features report length in meters. "
        "Point features return measurement as null with status NOT_REQUIRED. "
        "Unsupported geometries are returned with status NOT_SUPPORTED without crashing the API."
    ),
    responses={
        200: {"description": "Feature measurements successfully retrieved."},
        404: {"model": ErrorResponse, "description": "File not found."}
    }
)
def get_measurements(
    id: str,
    db: Session = Depends(get_db)
) -> FileMeasurementsResponse:
    """
    Returns calculated measurements for all features in a file.
    """
    return FileService.get_measurements(db=db, file_id=id)
