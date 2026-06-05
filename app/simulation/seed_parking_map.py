import argparse

from app.core.database import SessionLocal
from app.domain.value_objects.arrow_direction import ArrowDirection
from app.domain.value_objects.spot_status import SpotStatus
from app.services.parking_config import (
    deactivate_unlisted_displays,
    deactivate_unlisted_zone_spots,
    parse_zone_spec,
    seed_zone_spots,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed parking sectors, camera zones, spots, and default displays."
    )
    parser.add_argument(
        "--zone-spec",
        action="append",
        required=True,
        help="Repeatable spec like B1-A=B1-A-01-1..B1-A-01-6.",
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
    parser.add_argument(
        "--update-existing-status",
        action="store_true",
        help="Set existing spots in the zone specs to the requested initial status.",
    )
    parser.add_argument(
        "--deactivate-missing-spots",
        action="store_true",
        help="Deactivate spots in each seeded zone that are not present in the zone spec.",
    )
    parser.add_argument(
        "--deactivate-other-displays",
        action="store_true",
        help="Deactivate displays whose zones are not included in the zone specs.",
    )
    parser.add_argument(
        "--deactivate-other-zone-spots",
        action="store_true",
        help="Deactivate active spots whose zones are not included in the zone specs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initial_status = SpotStatus(args.initial_status)
    arrow_direction = ArrowDirection(args.arrow_direction)

    with SessionLocal() as db:
        active_zone_codes: set[str] = set()
        zone_spot_codes: dict[str, list[str]] = {}
        for raw_spec in args.zone_spec:
            zone_code, spot_codes = parse_zone_spec(raw_spec)
            active_zone_codes.add(zone_code)
            zone_spot_codes.setdefault(zone_code, []).extend(spot_codes)

        for zone_code, spot_codes in zone_spot_codes.items():
            result = seed_zone_spots(
                db,
                zone_code=zone_code,
                spot_codes=spot_codes,
                initial_status=initial_status,
                arrow_direction=arrow_direction,
                update_existing_status=args.update_existing_status,
                deactivate_missing_spots=args.deactivate_missing_spots,
            )
            print(
                f"{zone_code}: "
                f"spots={len(spot_codes)} "
                f"zones_created={result.zones_created} "
                f"spots_created={result.spots_created} "
                f"spots_updated={result.spots_updated} "
                f"spots_activated={result.spots_activated} "
                f"spots_deactivated={result.spots_deactivated} "
                f"displays_created={result.displays_created}"
            )
        if args.deactivate_other_displays:
            displays_updated = deactivate_unlisted_displays(
                db,
                active_zone_codes=active_zone_codes,
            )
            print(f"displays_updated={displays_updated}")
        if args.deactivate_other_zone_spots:
            spots_deactivated = deactivate_unlisted_zone_spots(
                db,
                active_zone_codes=active_zone_codes,
            )
            print(f"other_zone_spots_deactivated={spots_deactivated}")


if __name__ == "__main__":
    main()
