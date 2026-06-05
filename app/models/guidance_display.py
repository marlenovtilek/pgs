from datetime import datetime
from html import escape

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from app.domain.value_objects.arrow_direction import ArrowDirection

class GuidanceDisplay(Base):
    __tablename__ = "guidance_displays"
    __table_args__ = (
        CheckConstraint(
            "arrow_direction in ('LEFT', 'RIGHT', 'AHEAD')",
            name="ck_guidance_displays_arrow_direction_configurable",
        ),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    sector_id: Mapped[int] = mapped_column(ForeignKey("parking_sectors.id"), nullable=False, index=True)
    arrow_direction: Mapped[str] = mapped_column(
        String(20),
        default=ArrowDirection.AHEAD.value,
        nullable=False,
    )
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
    sector: Mapped["ParkingSector"] = relationship(
        "ParkingSector",
        back_populates="displays",
    )

    def __repr__(self) -> str:
        return f"<GuidanceDisplay code={self.code} sector_id={self.sector_id} direction={self.arrow_direction}>"

    def __str__(self) -> str:
        return self.code

    def __admin_repr__(self, request) -> str:
        return self.code

    def __admin_select2_repr__(self, request) -> str:
        return escape(self.code)
