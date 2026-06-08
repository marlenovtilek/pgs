from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector


def sort_order_from_code(value: str) -> int:
    digits = ""
    for char in reversed(value):
        if not char.isdigit():
            break
        digits = char + digits
    return int(digits) if digits else 0


def split_sector_code(sector_code: str) -> tuple[str, str]:
    if "-" not in sector_code:
        raise ValueError("Sector code must look like FLOOR-SECTOR, for example B1-A.")
    floor_code, sector_letter = sector_code.split("-", maxsplit=1)
    return floor_code, sector_letter


def get_or_create_floor(
    db: Session,
    floor_code: str,
) -> tuple[ParkingFloor, bool]:
    floor = db.scalar(select(ParkingFloor).where(ParkingFloor.code == floor_code))
    if floor is not None:
        return floor, False

    floor = ParkingFloor(
        title=f"Floor {floor_code}",
        code=floor_code,
        sort_order=sort_order_from_code(floor_code),
        is_active=True,
    )
    db.add(floor)
    db.flush()
    return floor, True


def get_or_create_sector(
    db: Session,
    floor: ParkingFloor,
    sector_code: str,
    sector_letter: str,
) -> tuple[ParkingSector, bool]:
    sector = db.scalar(select(ParkingSector).where(ParkingSector.code == sector_code))
    if sector is not None:
        return sector, False

    sector = ParkingSector(
        floor_id=floor.id,
        title=f"Sector {sector_code}",
        code=sector_code,
        sector_letter=sector_letter,
        sort_order=sort_order_from_code(sector_letter),
        is_active=True,
    )
    db.add(sector)
    db.flush()
    return sector, True


async def get_or_create_floor_async(
    db: AsyncSession,
    floor_code: str,
) -> tuple[ParkingFloor, bool]:
    floor = await db.scalar(select(ParkingFloor).where(ParkingFloor.code == floor_code))
    if floor is not None:
        return floor, False

    floor = ParkingFloor(
        title=f"Floor {floor_code}",
        code=floor_code,
        sort_order=sort_order_from_code(floor_code),
        is_active=True,
    )
    db.add(floor)
    await db.flush()
    return floor, True


async def get_or_create_sector_async(
    db: AsyncSession,
    floor: ParkingFloor,
    sector_code: str,
    sector_letter: str,
) -> tuple[ParkingSector, bool]:
    sector = await db.scalar(select(ParkingSector).where(ParkingSector.code == sector_code))
    if sector is not None:
        return sector, False

    sector = ParkingSector(
        floor_id=floor.id,
        title=f"Sector {sector_code}",
        code=sector_code,
        sector_letter=sector_letter,
        sort_order=sort_order_from_code(sector_letter),
        is_active=True,
    )
    db.add(sector)
    await db.flush()
    return sector, True
