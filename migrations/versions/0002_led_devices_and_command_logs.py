"""add led devices and command logs

Revision ID: 0002_led_devices
Revises: 0001_initial
Create Date: 2026-06-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_led_devices"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "led_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=50), server_default="TCP", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_led_devices_code"), "led_devices", ["code"], unique=True)

    op.add_column(
        "guidance_displays",
        sa.Column("led_device_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_guidance_displays_led_device_id"),
        "guidance_displays",
        ["led_device_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_guidance_displays_led_device_id_led_devices",
        "guidance_displays",
        "led_devices",
        ["led_device_id"],
        ["id"],
    )

    op.create_table(
        "led_command_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("display_code", sa.String(length=50), nullable=False),
        sa.Column("device_code", sa.String(length=50), nullable=True),
        sa.Column("sector_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('PENDING', 'SENT', 'FAILED')",
            name="ck_led_command_logs_status",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["led_devices.id"]),
        sa.ForeignKeyConstraint(["display_id"], ["guidance_displays.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_led_command_logs_device_code"), "led_command_logs", ["device_code"], unique=False)
    op.create_index(op.f("ix_led_command_logs_device_id"), "led_command_logs", ["device_id"], unique=False)
    op.create_index(op.f("ix_led_command_logs_display_code"), "led_command_logs", ["display_code"], unique=False)
    op.create_index(op.f("ix_led_command_logs_display_id"), "led_command_logs", ["display_id"], unique=False)
    op.create_index(op.f("ix_led_command_logs_status"), "led_command_logs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_led_command_logs_status"), table_name="led_command_logs")
    op.drop_index(op.f("ix_led_command_logs_display_id"), table_name="led_command_logs")
    op.drop_index(op.f("ix_led_command_logs_display_code"), table_name="led_command_logs")
    op.drop_index(op.f("ix_led_command_logs_device_id"), table_name="led_command_logs")
    op.drop_index(op.f("ix_led_command_logs_device_code"), table_name="led_command_logs")
    op.drop_table("led_command_logs")

    op.drop_constraint(
        "fk_guidance_displays_led_device_id_led_devices",
        "guidance_displays",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_guidance_displays_led_device_id"), table_name="guidance_displays")
    op.drop_column("guidance_displays", "led_device_id")

    op.drop_index(op.f("ix_led_devices_code"), table_name="led_devices")
    op.drop_table("led_devices")
