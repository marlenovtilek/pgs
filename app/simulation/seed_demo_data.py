from sqlalchemy import select

from app.core.database import SessionLocal
from app.domain.value_objects.spot_status import SpotStatus
from app.models import GuidanceCamera, ParkingRow, ParkingSpot, ParkingZone


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


def get_or_create_camera(zone_id: int, spots_count: int = 10) -> GuidanceCamera:
    with SessionLocal() as db:
        camera = db.scalar(
            select(GuidanceCamera).where(GuidanceCamera.code == "CAM-001")
        )
        if camera is not None:
            camera.spots_count = spots_count
            db.commit()
            db.refresh(camera)
            return camera

        camera = GuidanceCamera(
            title="Demo Camera 1",
            code="CAM-001",
            zone_id=zone_id,
            vendor="UNV",
            spots_count=spots_count,
            is_active=True,
        )
        db.add(camera)
        db.commit()
        db.refresh(camera)
        return camera


def main() -> None:
    zone = get_or_create_zone()
    row = get_or_create_row(zone_id=zone.id)
    seed_spots(row_id=row.id, total_spots=10)
    camera = get_or_create_camera(zone_id=zone.id, spots_count=10)

    print("Demo data is ready:")
    print(f"Zone: {zone.code} ({zone.title})")
    print(f"Row: {row.code} ({row.title})")
    print("Spots: A-001 .. A-010")
    print(f"Camera: {camera.code} ({camera.title})")


if __name__ == "__main__":
    main()
