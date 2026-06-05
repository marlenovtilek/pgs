from datetime import datetime
from html import escape

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ParkingSector(Base):
    __tablename__ = "parking_sectors"
    __table_args__ = (
        UniqueConstraint("floor_id", "code", name="uq_parking_sectors_floor_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("parking_floors.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    sector_letter: Mapped[str] = mapped_column(String(20), nullable=False)
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
    floor: Mapped["ParkingFloor"] = relationship(
        "ParkingFloor",
        back_populates="sectors",
    )
    zones: Mapped[list["ParkingZone"]] = relationship(
        "ParkingZone",
        back_populates="sector",
    )
    displays: Mapped[list["GuidanceDisplay"]] = relationship(
        "GuidanceDisplay",
        back_populates="sector",
    )

    def __repr__(self) -> str:
        return f"<ParkingSector code={self.code} floor_id={self.floor_id}>"

    def __str__(self) -> str:
        return self.code

    def __admin_repr__(self, request) -> str:
        return self.code

    def __admin_select2_repr__(self, request) -> str:
        return escape(self.code)
