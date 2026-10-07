import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.feature import FeatureModel


class MeasurementModel(Base):
    """
    Represents the calculated measurement associated with a geospatial feature.
    """
    __tablename__ = "measurements"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    feature_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    measurement_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="COMPLETED",
        nullable=False,
        index=True
    )

    # Relationships
    feature: Mapped["FeatureModel"] = relationship("FeatureModel", back_populates="measurement")

    def __repr__(self) -> str:
        return f"<MeasurementModel(id='{self.id}', type='{self.measurement_type}', value={self.value}, status='{self.status}')>"
