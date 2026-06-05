from datetime import datetime
from html import escape

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ParkingFloor(Base):
    __tablename__ = "parking_floors"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
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
    sectors: Mapped[list["ParkingSector"]] = relationship(
        "ParkingSector",
        back_populates="floor",
    )

    def __repr__(self) -> str:
        return f"<ParkingFloor code={self.code} title={self.title}>"

    def __str__(self) -> str:
        return self.code

    def __admin_repr__(self, request) -> str:
        return self.code

    def __admin_select2_repr__(self, request) -> str:
        return escape(self.code)
