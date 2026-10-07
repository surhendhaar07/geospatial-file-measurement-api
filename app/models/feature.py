import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.file import FileModel
    from app.models.measurement import MeasurementModel


class FeatureModel(Base):
    """
    Represents an extracted geospatial feature from a file.
    Stores metadata, geometry in GeoJSON-compatible format, and feature properties.
    """
    __tablename__ = "features"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    feature_index: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    file: Mapped["FileModel"] = relationship("FileModel", back_populates="features")
    measurement: Mapped[Optional["MeasurementModel"]] = relationship(
        "MeasurementModel",
        back_populates="feature",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FeatureModel(id='{self.id}', index={self.feature_index}, type='{self.geometry_type}')>"
