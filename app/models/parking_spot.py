from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.value_objects.spot_status import SpotStatus


class ParkingSpot(Base):
    __tablename__ = "parking_spots"
    __table_args__ = (
        UniqueConstraint("row_id", "code", name="uq_parking_spots_row_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    row_id: Mapped[int] = mapped_column(ForeignKey("parking_rows.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=SpotStatus.UNKNOWN.value, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ParkingSpot row_id={self.row_id} code={self.code} status={self.status}>"
