from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

from app.domain.value_objects.arrow_direction import ArrowDirection

class GuidanceDisplay(Base):
    __tablename__ = "guidance_displays"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("parking_zones.id"), nullable=False, index=True)
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

    def __repr__(self) -> str:
        return f"<GuidanceDisplay code={self.code} zone_id={self.zone_id} direction={self.arrow_direction}>"