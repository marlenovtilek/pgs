from datetime import datetime
from html import escape

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.value_objects.spot_status import SpotStatus


class ParkingSpot(Base):
    __tablename__ = "parking_spots"
    __table_args__ = (
        UniqueConstraint("zone_id", "code", name="uq_parking_spots_zone_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("parking_zones.id"), nullable=False, index=True)
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
    zone: Mapped["ParkingZone"] = relationship(
        "ParkingZone",
        back_populates="spots",
    )
    events: Mapped[list["SpotOccupancyEvent"]] = relationship(
        "SpotOccupancyEvent",
        back_populates="spot",
    )

    def __repr__(self) -> str:
        return f"<ParkingSpot zone_id={self.zone_id} code={self.code} status={self.status}>"

    def __str__(self) -> str:
        return self.code

    def __admin_repr__(self, request) -> str:
        return self.code

    def __admin_select2_repr__(self, request) -> str:
        return f"<span>{escape(self.code)}</span>"
