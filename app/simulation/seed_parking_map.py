import argparse

from app.core.database import SessionLocal
from app.domain.value_objects.arrow_direction import ArrowDirection
from app.domain.value_objects.spot_status import SpotStatus
from app.services.parking_config import parse_zone_spec, seed_zone_spots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed parking zones, spots, rows, and default displays."
    )
    parser.add_argument(
        "--zone-spec",
        action="append",
        required=True,
        help="Repeatable spec like B1-C=B1-C001..B1-C064 or B2-C=B2-C01..B2-C06.",
    )
    parser.add_argument(
        "--initial-status",
        choices=[status.value for status in SpotStatus],
        default=SpotStatus.UNKNOWN.value,
    )
    parser.add_argument(
        "--arrow-direction",
        choices=[direction.value for direction in ArrowDirection],
        default=ArrowDirection.AHEAD.value,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initial_status = SpotStatus(args.initial_status)
    arrow_direction = ArrowDirection(args.arrow_direction)

    with SessionLocal() as db:
        for raw_spec in args.zone_spec:
            zone_code, spot_codes = parse_zone_spec(raw_spec)
            result = seed_zone_spots(
                db,
                zone_code=zone_code,
                spot_codes=spot_codes,
                initial_status=initial_status,
                arrow_direction=arrow_direction,
            )
            print(
                f"{zone_code}: "
                f"spots={len(spot_codes)} "
                f"zones_created={result.zones_created} "
                f"rows_created={result.rows_created} "
                f"spots_created={result.spots_created} "
                f"displays_created={result.displays_created}"
            )


if __name__ == "__main__":
    main()
