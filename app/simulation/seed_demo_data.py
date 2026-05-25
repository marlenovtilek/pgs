from sqlalchemy import select

from app.core.database import SessionLocal
from app.domain.value_objects.spot_status import SpotStatus
from app.models import ParkingRow, ParkingSpot, ParkingZone, GuidanceDisplay
from app.domain.value_objects.arrow_direction import ArrowDirection


def get_or_create_zone() -> ParkingZone:
    with SessionLocal() as db:
        zone = db.scalar(select(ParkingZone).where(ParkingZone.code == "A"))
        if zone is not None:
            return zone

        zone = ParkingZone(
            title="Zone A",
            code="A",
            level="P1",
            is_active=True,
        )
        db.add(zone)
        db.commit()
        db.refresh(zone)
        return zone


def get_or_create_row(zone_id: int) -> ParkingRow:
    with SessionLocal() as db:
        row = db.scalar(
            select(ParkingRow).where(
                ParkingRow.zone_id == zone_id,
                ParkingRow.code == "A1",
            )
        )
        if row is not None:
            return row

        row = ParkingRow(
            zone_id=zone_id,
            title="Row A1",
            code="A1",
            sort_order=1,
            is_active=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row


def seed_spots(row_id: int, total_spots: int = 10) -> None:
    with SessionLocal() as db:
        for number in range(1, total_spots + 1):
            spot_code = f"A-{number:03d}"
            existing_spot = db.scalar(
                select(ParkingSpot).where(
                    ParkingSpot.row_id == row_id,
                    ParkingSpot.code == spot_code,
                )
            )
            if existing_spot is not None:
                continue

            db.add(
                ParkingSpot(
                    row_id=row_id,
                    code=spot_code,
                    status=SpotStatus.FREE.value,
                    sort_order=number,
                    is_active=True,
                )
            )

        db.commit()


def get_or_create_display(zone_id: int) -> GuidanceDisplay:

    with SessionLocal() as db:
        guidance_display = db.scalar(select(GuidanceDisplay).where(GuidanceDisplay.code == "DISP-A-01"))
        if guidance_display is not None:
            return guidance_display
        
        guidance_display = GuidanceDisplay(
            title="Display A Entrance",
            code="DISP-A-01",
            zone_id=zone_id,
            arrow_direction=ArrowDirection.AHEAD.value,
            is_active=True,
        )

        db.add(guidance_display)
        db.commit()
        db.refresh(guidance_display)
        return guidance_display
        


def main() -> None:
    zone = get_or_create_zone()
    row = get_or_create_row(zone_id=zone.id)
    seed_spots(row_id=row.id, total_spots=10)
    display = get_or_create_display(zone_id=zone.id)

    print("Demo data is ready:")
    print(f"Zone: {zone.code} ({zone.title})")
    print(f"Row: {row.code} ({row.title})")
    print("Spots: A-001 .. A-010")
    print(f"Display: {display.code} ({display.title})")


if __name__ == "__main__":
    main()
