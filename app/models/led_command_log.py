from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.admin_repr import admin_select2_text


class LedCommandLog(Base):
    __tablename__ = "led_command_logs"
    __table_args__ = (
        CheckConstraint(
            "status in ('PENDING', 'SENT', 'FAILED')",
            name="ck_led_command_logs_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    display_id: Mapped[int | None] = mapped_column(
        ForeignKey("guidance_displays.id"),
        nullable=True,
        index=True,
    )
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("led_devices.id"),
        nullable=True,
        index=True,
    )
    display_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    device_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    sector_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    display: Mapped["GuidanceDisplay | None"] = relationship(
        "GuidanceDisplay",
        back_populates="command_logs",
    )
    device: Mapped["LedDevice | None"] = relationship(
        "LedDevice",
        back_populates="command_logs",
    )

    def __repr__(self) -> str:
        return f"<LedCommandLog display_code={self.display_code} status={self.status}>"

    def __str__(self) -> str:
        return f"{self.display_code} {self.status}"

    def __admin_repr__(self, request) -> str:
        return f"{self.display_code} {self.status}"

    def __admin_select2_repr__(self, request) -> str:
        return admin_select2_text(self.__admin_repr__(request))
