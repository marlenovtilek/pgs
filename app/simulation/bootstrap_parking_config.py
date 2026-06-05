import argparse

from app.core.config import settings
from app.core.database import SessionLocal
from app.domain.value_objects.arrow_direction import ArrowDirection
from app.services.parking_config import seed_sector_display_config
from app.services.users import UserAlreadyExistsError, create_user


DEFAULT_SECTORS = ["B1-A", "B1-B", "B1-C"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create base floors, sectors, and LED displays without pre-creating spots."
    )
    parser.add_argument(
        "--sector",
        action="append",
        help="Repeatable sector code like B1-A. Defaults to B1-A, B1-B, B1-C.",
    )
    parser.add_argument(
        "--arrow-direction",
        choices=[direction.value for direction in ArrowDirection],
        default=ArrowDirection.AHEAD.value,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sector_codes = args.sector or DEFAULT_SECTORS
    arrow_direction = ArrowDirection(args.arrow_direction)

    with SessionLocal() as db:
        result = seed_sector_display_config(
            db,
            sector_codes=sector_codes,
            arrow_direction=arrow_direction,
        )
        admin_user_state = _ensure_admin_user(db)

    print(
        "base_config: "
        f"sectors={','.join(sector_codes)} "
        f"floors_created={result.floors_created} "
        f"sectors_created={result.sectors_created} "
        f"displays_created={result.displays_created} "
        f"admin_user={admin_user_state}"
    )


def _ensure_admin_user(db) -> str:
    if not settings.admin_username or not settings.admin_password:
        return "not_configured"

    try:
        create_user(
            db,
            username=settings.admin_username,
            password=settings.admin_password,
        )
    except UserAlreadyExistsError:
        return "exists"
    return "created"


if __name__ == "__main__":
    main()
