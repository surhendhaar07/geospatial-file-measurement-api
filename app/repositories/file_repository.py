
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.file import FileModel


class FileRepository:
    """Repository handling CRUD and persistence operations for FileModel."""

    @staticmethod
    def create(db: Session, file_model: FileModel) -> FileModel:
        db.add(file_model)
        db.commit()
        db.refresh(file_model)
        return file_model

    @staticmethod
    def get_by_id(db: Session, file_id: str, load_features: bool = False) -> FileModel | None:
        stmt = select(FileModel).where(FileModel.id == file_id)
        if load_features:
            stmt = stmt.options(selectinload(FileModel.features))
        return db.scalar(stmt)

    @staticmethod
    def list_files(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[FileModel], int]:
        total_stmt = select(func.count(FileModel.id))
        total = db.scalar(total_stmt) or 0

        stmt = select(FileModel).order_by(FileModel.uploaded_at.desc()).offset(skip).limit(limit)
        items = list(db.scalars(stmt).all())
        return items, total

    @staticmethod
    def update(db: Session, file_model: FileModel) -> FileModel:
        db.commit()
        db.refresh(file_model)
        return file_model

    @staticmethod
    def delete(db: Session, file_model: FileModel) -> None:
        db.delete(file_model)
        db.commit()
