"""remove camera layer from pgs

Revision ID: 33d66d76dca9
Revises: fdf989e20d29
Create Date: 2026-05-21 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "33d66d76dca9"
down_revision: Union[str, Sequence[str], None] = "fdf989e20d29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_guidance_cameras_zone_id"), table_name="guidance_cameras")
    op.drop_index(op.f("ix_guidance_cameras_code"), table_name="guidance_cameras")
    op.drop_table("guidance_cameras")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "guidance_cameras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("vendor", sa.String(length=50), nullable=False),
        sa.Column("spots_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["parking_zones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guidance_cameras_code"), "guidance_cameras", ["code"], unique=True)
    op.create_index(op.f("ix_guidance_cameras_zone_id"), "guidance_cameras", ["zone_id"], unique=False)
