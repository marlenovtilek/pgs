from datetime import datetime
from html import escape

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class ParkingZone(Base):
    __tablename__ = "parking_zones"
    __table_args__ = (
        UniqueConstraint("sector_id", "code", name="uq_parking_zones_sector_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("parking_sectors.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    zone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    sector: Mapped["ParkingSector"] = relationship(
        "ParkingSector",
        back_populates="zones",
    )
    spots: Mapped[list["ParkingSpot"]] = relationship(
        "ParkingSpot",
        back_populates="zone",
    )
    displays: Mapped[list["GuidanceDisplay"]] = relationship(
        "GuidanceDisplay",
        secondary="guidance_display_zones",
        back_populates="zones",
    )

    def __repr__(self) -> str:
        return f"<ParkingZone code={self.code} sector_id={self.sector_id}>"

    def __str__(self) -> str:
        return self.code

    def __admin_repr__(self, request) -> str:
        return self.code

    def __admin_select2_repr__(self, request) -> str:
        return f"<span>{escape(self.code)}</span>"
    
