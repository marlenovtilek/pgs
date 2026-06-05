"""refactor parking hierarchy

Revision ID: 6b8d2f4c9a10
Revises: 8680ade4f45b
Create Date: 2026-06-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6b8d2f4c9a10"
down_revision: Union[str, Sequence[str], None] = "8680ade4f45b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "parking_floors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["floor_id"], ["parking_floors.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("floor_id", "code", name="uq_parking_sectors_floor_code"),
    )
    op.create_index(op.f("ix_parking_sectors_code"), "parking_sectors", ["code"], unique=True)
    op.create_index(op.f("ix_parking_sectors_floor_id"), "parking_sectors", ["floor_id"], unique=False)

    op.add_column("parking_zones", sa.Column("sector_id", sa.Integer(), nullable=True))
    op.add_column("parking_zones", sa.Column("zone_number", sa.String(length=20), nullable=True))
    op.add_column("parking_zones", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.create_index(op.f("ix_parking_zones_sector_id"), "parking_zones", ["sector_id"], unique=False)
    op.create_foreign_key(
        "fk_parking_zones_sector_id_parking_sectors",
        "parking_zones",
        "parking_sectors",
        ["sector_id"],
        ["id"],
    )

    op.add_column("parking_spots", sa.Column("zone_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_parking_spots_zone_id"), "parking_spots", ["zone_id"], unique=False)
    op.create_foreign_key(
        "fk_parking_spots_zone_id_parking_zones",
        "parking_spots",
        "parking_zones",
        ["zone_id"],
        ["id"],
    )
    op.alter_column("parking_spots", "row_id", existing_type=sa.Integer(), nullable=True)

    op.add_column("guidance_displays", sa.Column("sector_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_guidance_displays_sector_id"), "guidance_displays", ["sector_id"], unique=False)
    op.create_foreign_key(
        "fk_guidance_displays_sector_id_parking_sectors",
        "guidance_displays",
        "parking_sectors",
        ["sector_id"],
        ["id"],
    )
    op.alter_column("guidance_displays", "zone_id", existing_type=sa.Integer(), nullable=True)

    metadata = sa.MetaData()
    floors = sa.Table("parking_floors", metadata, autoload_with=bind)
    sectors = sa.Table("parking_sectors", metadata, autoload_with=bind)
    zones = sa.Table("parking_zones", metadata, autoload_with=bind)
    rows = sa.Table("parking_rows", metadata, autoload_with=bind)
    spots = sa.Table("parking_spots", metadata, autoload_with=bind)
    displays = sa.Table("guidance_displays", metadata, autoload_with=bind)

    floor_ids: dict[str, int] = {}
    sector_ids: dict[int, int] = {}

    for old_zone in bind.execute(sa.select(zones)).mappings():
        floor_code, sector_letter = _split_sector_code(old_zone["code"])
        floor_id = floor_ids.get(floor_code)
        if floor_id is None:
            floor_id = bind.execute(
                floors.insert()
                .values(
                    title=f"Floor {floor_code}",
                    code=floor_code,
                    sort_order=_sort_order(floor_code),
                    is_active=True,
                )
                .returning(floors.c.id)
            ).scalar_one()
            floor_ids[floor_code] = floor_id

        sector_id = bind.execute(
            sectors.insert()
            .values(
                floor_id=floor_id,
                title=f"Sector {old_zone['code']}",
                code=old_zone["code"],
                sector_letter=sector_letter,
                sort_order=_sort_order(sector_letter),
                is_active=old_zone["is_active"],
            )
            .returning(sectors.c.id)
        ).scalar_one()
        sector_ids[old_zone["id"]] = sector_id

        bind.execute(
            zones.update()
            .where(zones.c.id == old_zone["id"])
            .values(
                sector_id=sector_id,
                zone_number=old_zone["code"],
                sort_order=0,
                is_active=False,
            )
        )

    for old_row in bind.execute(sa.select(rows)).mappings():
        sector_id = sector_ids[old_row["zone_id"]]
        existing_zone = bind.execute(
            sa.select(zones.c.id).where(zones.c.code == old_row["code"])
        ).scalar()
        if existing_zone is None:
            camera_zone_id = bind.execute(
                zones.insert()
                .values(
                    sector_id=sector_id,
                    title=f"Camera Zone {old_row['code']}",
                    code=old_row["code"],
                    zone_number=_last_code_part(old_row["code"]),
                    sort_order=old_row["sort_order"],
                    is_active=old_row["is_active"],
                )
                .returning(zones.c.id)
            ).scalar_one()
        else:
            camera_zone_id = existing_zone
            bind.execute(
                zones.update()
                .where(zones.c.id == camera_zone_id)
                .values(
                    sector_id=sector_id,
                    zone_number=_last_code_part(old_row["code"]),
                    sort_order=old_row["sort_order"],
                    is_active=old_row["is_active"],
                )
            )

        bind.execute(
            spots.update()
            .where(spots.c.row_id == old_row["id"])
            .values(zone_id=camera_zone_id)
        )

    for display in bind.execute(sa.select(displays)).mappings():
        sector_id = sector_ids.get(display["zone_id"])
        if sector_id is not None:
            bind.execute(
                displays.update()
                .where(displays.c.id == display["id"])
                .values(sector_id=sector_id)
            )

    op.alter_column("parking_zones", "sector_id", nullable=False)
    op.alter_column("parking_zones", "zone_number", nullable=False)
    op.alter_column("parking_spots", "zone_id", nullable=False)
    op.alter_column("guidance_displays", "sector_id", nullable=False)
    op.create_unique_constraint("uq_parking_zones_sector_code", "parking_zones", ["sector_id", "code"])
    op.create_unique_constraint("uq_parking_spots_zone_code", "parking_spots", ["zone_id", "code"])


def downgrade() -> None:
    op.drop_constraint("uq_parking_spots_zone_code", "parking_spots", type_="unique")
    op.drop_constraint("uq_parking_zones_sector_code", "parking_zones", type_="unique")
    op.alter_column("guidance_displays", "zone_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("fk_guidance_displays_sector_id_parking_sectors", "guidance_displays", type_="foreignkey")
    op.drop_index(op.f("ix_guidance_displays_sector_id"), table_name="guidance_displays")
    op.drop_column("guidance_displays", "sector_id")
    op.alter_column("parking_spots", "row_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("fk_parking_spots_zone_id_parking_zones", "parking_spots", type_="foreignkey")
    op.drop_index(op.f("ix_parking_spots_zone_id"), table_name="parking_spots")
    op.drop_column("parking_spots", "zone_id")
    op.drop_constraint("fk_parking_zones_sector_id_parking_sectors", "parking_zones", type_="foreignkey")
    op.drop_index(op.f("ix_parking_zones_sector_id"), table_name="parking_zones")
    op.drop_column("parking_zones", "sort_order")
    op.drop_column("parking_zones", "zone_number")
    op.drop_column("parking_zones", "sector_id")
    op.drop_index(op.f("ix_parking_sectors_floor_id"), table_name="parking_sectors")
    op.drop_index(op.f("ix_parking_sectors_code"), table_name="parking_sectors")
    op.drop_table("parking_sectors")
    op.drop_index(op.f("ix_parking_floors_code"), table_name="parking_floors")
    op.drop_table("parking_floors")


def _split_sector_code(code: str) -> tuple[str, str]:
    if "-" not in code:
        return "UNKNOWN", code
    return tuple(code.split("-", maxsplit=1))  # type: ignore[return-value]


def _sort_order(value: str) -> int:
    digits = ""
    for char in reversed(value):
        if not char.isdigit():
            break
        digits = char + digits
    return int(digits) if digits else 0


def _last_code_part(code: str) -> str:
    return code.rsplit("-", maxsplit=1)[-1]
