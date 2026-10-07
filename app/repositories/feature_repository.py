from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.feature import FeatureModel


class FeatureRepository:
    """Repository handling CRUD and persistence operations for FeatureModel."""

    @staticmethod
    def bulk_create(db: Session, features: list[FeatureModel]) -> list[FeatureModel]:
        db.add_all(features)
        db.commit()
        return features

    @staticmethod
    def get_by_file_id(db: Session, file_id: str, load_measurement: bool = True) -> list[FeatureModel]:
        stmt = select(FeatureModel).where(FeatureModel.file_id == file_id).order_by(FeatureModel.feature_index)
        if load_measurement:
            stmt = stmt.options(selectinload(FeatureModel.measurement))
        return list(db.scalars(stmt).all())
