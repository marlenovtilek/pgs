"""restrict display arrow directions

Revision ID: a7e2c9d4f130
Revises: 9c1a7e2b4d30
Create Date: 2026-06-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a7e2c9d4f130"
down_revision: Union[str, Sequence[str], None] = "9c1a7e2b4d30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "update guidance_displays set arrow_direction = 'AHEAD' "
        "where arrow_direction not in ('LEFT', 'RIGHT', 'AHEAD')"
    )
    op.create_check_constraint(
        "ck_guidance_displays_arrow_direction_configurable",
        "guidance_displays",
        "arrow_direction in ('LEFT', 'RIGHT', 'AHEAD')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_guidance_displays_arrow_direction_configurable",
        "guidance_displays",
        type_="check",
    )
