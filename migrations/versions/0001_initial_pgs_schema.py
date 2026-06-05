"""initial pgs schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "parking_floors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parking_floors_code"), "parking_floors", ["code"], unique=True)

    op.create_table(
        "parking_sectors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("floor_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("sector_letter", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["floor_id"], ["parking_floors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("floor_id", "code", name="uq_parking_sectors_floor_code"),
    )
    op.create_index(op.f("ix_parking_sectors_code"), "parking_sectors", ["code"], unique=True)
    op.create_index(op.f("ix_parking_sectors_floor_id"), "parking_sectors", ["floor_id"], unique=False)

    op.create_table(
        "parking_zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sector_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("zone_number", sa.String(length=20), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sector_id"], ["parking_sectors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sector_id", "code", name="uq_parking_zones_sector_code"),
    )
    op.create_index(op.f("ix_parking_zones_code"), "parking_zones", ["code"], unique=True)
    op.create_index(op.f("ix_parking_zones_sector_id"), "parking_zones", ["sector_id"], unique=False)

    op.create_table(
        "parking_spots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="UNKNOWN", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["parking_zones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("zone_id", "code", name="uq_parking_spots_zone_code"),
    )
    op.create_index(op.f("ix_parking_spots_status"), "parking_spots", ["status"], unique=False)
    op.create_index(op.f("ix_parking_spots_zone_id"), "parking_spots", ["zone_id"], unique=False)

    op.create_table(
        "guidance_displays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("sector_id", sa.Integer(), nullable=False),
        sa.Column("arrow_direction", sa.String(length=20), server_default="AHEAD", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "arrow_direction in ('LEFT', 'RIGHT', 'AHEAD')",
            name="ck_guidance_displays_arrow_direction_configurable",
        ),
        sa.ForeignKeyConstraint(["sector_id"], ["parking_sectors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guidance_displays_code"), "guidance_displays", ["code"], unique=True)
    op.create_index(op.f("ix_guidance_displays_sector_id"), "guidance_displays", ["sector_id"], unique=False)

    op.create_table(
        "spot_occupancy_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spot_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=100), nullable=True),
        sa.Column("dedup_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), server_default="UNV_SERVICE", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["spot_id"], ["parking_spots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_spot_occupancy_events_dedup_key"), "spot_occupancy_events", ["dedup_key"], unique=True)
    op.create_index(op.f("ix_spot_occupancy_events_detected_at"), "spot_occupancy_events", ["detected_at"], unique=False)
    op.create_index(op.f("ix_spot_occupancy_events_spot_id"), "spot_occupancy_events", ["spot_id"], unique=False)
    op.create_index(op.f("ix_spot_occupancy_events_status"), "spot_occupancy_events", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_spot_occupancy_events_status"), table_name="spot_occupancy_events")
    op.drop_index(op.f("ix_spot_occupancy_events_spot_id"), table_name="spot_occupancy_events")
    op.drop_index(op.f("ix_spot_occupancy_events_detected_at"), table_name="spot_occupancy_events")
    op.drop_index(op.f("ix_spot_occupancy_events_dedup_key"), table_name="spot_occupancy_events")
    op.drop_table("spot_occupancy_events")

    op.drop_index(op.f("ix_guidance_displays_sector_id"), table_name="guidance_displays")
    op.drop_index(op.f("ix_guidance_displays_code"), table_name="guidance_displays")
    op.drop_table("guidance_displays")

    op.drop_index(op.f("ix_parking_spots_zone_id"), table_name="parking_spots")
    op.drop_index(op.f("ix_parking_spots_status"), table_name="parking_spots")
    op.drop_table("parking_spots")

    op.drop_index(op.f("ix_parking_zones_sector_id"), table_name="parking_zones")
    op.drop_index(op.f("ix_parking_zones_code"), table_name="parking_zones")
    op.drop_table("parking_zones")

    op.drop_index(op.f("ix_parking_sectors_floor_id"), table_name="parking_sectors")
    op.drop_index(op.f("ix_parking_sectors_code"), table_name="parking_sectors")
    op.drop_table("parking_sectors")

    op.drop_index(op.f("ix_parking_floors_code"), table_name="parking_floors")
    op.drop_table("parking_floors")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
