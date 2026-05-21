from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domain.value_objects.spot_status import SpotStatus


class SpotOccupancyEvent(Base):
    __tablename__ = "spot_occupancy_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("guidance_cameras.id"), nullable=False, index=True)
    spot_id: Mapped[int] = mapped_column(ForeignKey("parking_spots.id"), nullable=False, index=True)
    event_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), default="SIMULATOR", nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SpotOccupancyEvent camera_id={self.camera_id} spot_id={self.spot_id} status={self.status}>"