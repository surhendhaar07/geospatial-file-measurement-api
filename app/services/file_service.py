import os
import shutil
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    EntityNotFoundError,
    GeospatialAPIException,
    GeospatialProcessingError,
)
from app.core.logging import logger
from app.models.feature import FeatureModel
from app.models.file import FileModel
from app.models.measurement import MeasurementModel
from app.repositories.feature_repository import FeatureRepository
from app.repositories.file_repository import FileRepository
from app.repositories.measurement_repository import MeasurementRepository
from app.schemas.file import FileInfoResponse, FileUploadResponse
from app.schemas.measurement import FeatureMeasurementItem, FileMeasurementsResponse
from app.services.crs_service import CRSService
from app.services.geospatial_service import ExtractedDataset, GeospatialService
from app.services.measurement_service import MeasurementService
from app.utils.file_validation import (
    locate_and_validate_shapefile,
    validate_file_extension,
    validate_file_size,
    validate_kml_content,
    validate_zip_safe_extraction,
)
from app.utils.geometry_utils import geometry_to_geojson_dict

settings = get_settings()


class FileService:
    """
    Orchestrates file upload, safe storage, geospatial extraction,
    CRS transformation, measurement computation, and persistence.
    """

    @classmethod
    async def process_upload(cls, db: Session, upload_file: UploadFile) -> FileUploadResponse:
        """
        Receives an uploaded geospatial file, validates it, extracts features,
        projects geometries to a metric CRS, calculates measurements, and persists records.
        """
        filename = upload_file.filename or "unknown_file"
        logger.info(f"Received file upload request: '{filename}'")

        # 1. Extension validation
        extension = validate_file_extension(filename)
        file_type = "SHAPEFILE_ZIP" if extension == ".zip" else "KML"

        # Unique IDs and safe storage paths
        file_id = str(uuid.uuid4())
        upload_dir = os.path.abspath(os.path.join(settings.UPLOAD_DIR, file_id))
        temp_extract_dir = os.path.abspath(os.path.join(settings.TEMP_DIR, file_id))
        os.makedirs(upload_dir, exist_ok=True)

        saved_file_path = os.path.join(upload_dir, f"source{extension}")

        # Initial database record
        file_record = FileModel(
            id=file_id,
            filename=filename,
            file_type=file_type,
            file_size=0,
            status="PROCESSING",
            uploaded_at=datetime.now(timezone.utc)
        )
        FileRepository.create(db, file_record)

        try:
            # 2. Stream upload to disk to avoid unbounded memory usage
            total_bytes = 0
            with open(saved_file_path, "wb") as buffer:
                while chunk := await upload_file.read(1024 * 64):  # 64KB chunks
                    total_bytes += len(chunk)
                    if total_bytes > settings.max_upload_size_bytes:
                        raise GeospatialProcessingError(
                            f"File size exceeded maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                        )
                    buffer.write(chunk)

            # Validate size
            validate_file_size(total_bytes, settings.max_upload_size_bytes)
            file_record.file_size = total_bytes
            FileRepository.update(db, file_record)

            # 3. Geospatial extraction
            dataset: ExtractedDataset
            if file_type == "SHAPEFILE_ZIP":
                os.makedirs(temp_extract_dir, exist_ok=True)
                extracted_files = validate_zip_safe_extraction(saved_file_path, temp_extract_dir)
                shp_path = locate_and_validate_shapefile(extracted_files)
                dataset = GeospatialService.read_shapefile(shp_path)
            else:  # KML
                validate_kml_content(saved_file_path)
                dataset = GeospatialService.read_kml(saved_file_path)

            if not dataset.features:
                logger.warning(f"File '{filename}' contains 0 geospatial features.")

            # 4. CRS determination and optimal projection selection
            source_crs_str = CRSService.format_crs_string(dataset.source_crs)
            target_projected_crs = CRSService.determine_optimal_projected_crs(
                source_crs=dataset.source_crs,
                bounds=dataset.bounds
            )
            target_crs_str = CRSService.format_crs_string(target_projected_crs)

            logger.info(f"File '{filename}': Source CRS = {source_crs_str}, Projected Measurement CRS = {target_crs_str}")

            # 5. Process features and compute measurements
            feature_models: list[FeatureModel] = []
            measurement_models: list[MeasurementModel] = []

            for extracted in dataset.features:
                feature_id = str(uuid.uuid4())
                geom_geojson = geometry_to_geojson_dict(extracted.geometry)

                # Reproject geometry for measurement
                projected_geom = None
                if extracted.geometry is not None:
                    try:
                        projected_geom = CRSService.transform_geometry(
                            geom=extracted.geometry,
                            source_crs=dataset.source_crs,
                            target_crs=target_projected_crs
                        )
                    except Exception as trans_err:
                        logger.warning(f"Failed to project geometry for feature index {extracted.index}: {trans_err}")

                meas_result = MeasurementService.calculate_measurement(projected_geom)

                feat_model = FeatureModel(
                    id=feature_id,
                    file_id=file_id,
                    feature_index=extracted.index,
                    geometry_type=extracted.geometry_type,
                    geometry=geom_geojson,
                    properties=extracted.properties
                )
                feature_models.append(feat_model)

                meas_model = MeasurementModel(
                    id=str(uuid.uuid4()),
                    feature_id=feature_id,
                    measurement_type=meas_result.measurement_type,
                    value=meas_result.value,
                    unit=meas_result.unit,
                    status=meas_result.status
                )
                measurement_models.append(meas_model)

            # 6. Bulk persistence
            FeatureRepository.bulk_create(db, feature_models)
            MeasurementRepository.bulk_create(db, measurement_models)

            # Update file status
            file_record.feature_count = len(feature_models)
            file_record.source_crs = source_crs_str
            file_record.measurement_crs = target_crs_str
            file_record.status = "COMPLETED"
            file_record.processed_at = datetime.now(timezone.utc)
            FileRepository.update(db, file_record)

            logger.info(f"Successfully processed file '{filename}' with {len(feature_models)} features.")

            return FileUploadResponse(
                id=file_record.id,
                filename=file_record.filename,
                file_type=file_record.file_type,
                file_size=file_record.file_size,
                feature_count=file_record.feature_count,
                crs=file_record.source_crs,
                source_crs=file_record.source_crs,
                measurement_crs=file_record.measurement_crs,
                status=file_record.status,
                uploaded_at=file_record.uploaded_at,
                processed_at=file_record.processed_at
            )

        except Exception as e:
            logger.error(f"Error during file processing for '{filename}': {e!s}", exc_info=True)
            file_record.status = "FAILED"
            file_record.error_message = str(e)
            file_record.processed_at = datetime.now(timezone.utc)
            FileRepository.update(db, file_record)

            if isinstance(e, GeospatialAPIException):
                raise
            raise GeospatialProcessingError(f"Processing failed: {e!s}")

        finally:
            # Clean up temporary uncompressed files
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir, ignore_errors=True)

    @classmethod
    def get_file_info(cls, db: Session, file_id: str) -> FileInfoResponse:
        """
        Retrieves metadata and processing status for an uploaded file.
        """
        file_record = FileRepository.get_by_id(db, file_id)
        if not file_record:
            raise EntityNotFoundError(f"File with ID '{file_id}' not found.")
        return FileInfoResponse.model_validate(file_record)

    @classmethod
    def list_files(cls, db: Session, skip: int = 0, limit: int = 100) -> tuple[list[FileInfoResponse], int]:
        """
        Lists uploaded files with pagination.
        """
        records, total = FileRepository.list_files(db, skip=skip, limit=limit)
        return [FileInfoResponse.model_validate(r) for r in records], total

    @classmethod
    def get_measurements(cls, db: Session, file_id: str) -> FileMeasurementsResponse:
        """
        Retrieves feature-level measurement calculations for a processed file.
        """
        file_record = FileRepository.get_by_id(db, file_id)
        if not file_record:
            raise EntityNotFoundError(f"File with ID '{file_id}' not found.")

        features = FeatureRepository.get_by_file_id(db, file_id, load_measurement=True)

        measurement_items: list[FeatureMeasurementItem] = []
        for feat in features:
            meas = feat.measurement
            measurement_items.append(
                FeatureMeasurementItem(
                    feature_id=feat.feature_index,
                    geometry_type=feat.geometry_type,
                    measurement_type=meas.measurement_type if meas else None,
                    value=meas.value if meas else None,
                    unit=meas.unit if meas else None,
                    status=meas.status if meas else "FAILED",
                    properties=feat.properties,
                    geometry=feat.geometry
                )
            )

        return FileMeasurementsResponse(
            file_id=file_record.id,
            filename=file_record.filename,
            feature_count=file_record.feature_count,
            source_crs=file_record.source_crs,
            measurement_crs=file_record.measurement_crs,
            measurements=measurement_items
        )
