
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.measurement import MeasurementModel


class MeasurementRepository:
    """Repository handling CRUD and persistence operations for MeasurementModel."""

    @staticmethod
    def bulk_create(db: Session, measurements: list[MeasurementModel]) -> list[MeasurementModel]:
        db.add_all(measurements)
        db.commit()
        return measurements

    @staticmethod
    def get_by_feature_id(db: Session, feature_id: str) -> MeasurementModel | None:
        stmt = select(MeasurementModel).where(MeasurementModel.feature_id == feature_id)
        return db.scalar(stmt)
