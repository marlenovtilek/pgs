"""Concurrency test for PGS auto-create and event dedup.

Drives several races from independent async sessions against the real
database to confirm the IntegrityError rollback+retry resolves them with
no unhandled errors and no duplicate rows. Self-cleaning.

Run inside the stack:

    docker compose run --rm -v ./scripts:/app/scripts pgs-api \
        python -m scripts.concurrency_test

Exit code is non-zero if any scenario reports unexpected counts or errors.
"""
import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import delete, func, select

from app.core.async_database import AsyncSessionLocal
from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.schemas.spot_event import SpotEventRequest
from app.services.mqtt_spot_events import ensure_mqtt_parking_config_async
from app.services.spot_events import process_spot_event_async

FLOOR = "L8"


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _cleanup(db) -> None:
    sector_ids = select(ParkingSector.id).where(
        ParkingSector.floor_id.in_(select(ParkingFloor.id).where(ParkingFloor.code == FLOOR))
    )
    zone_ids = select(ParkingZone.id).where(ParkingZone.sector_id.in_(sector_ids))
    spot_ids = select(ParkingSpot.id).where(ParkingSpot.zone_id.in_(zone_ids))
    await db.execute(delete(SpotOccupancyEvent).where(SpotOccupancyEvent.spot_id.in_(spot_ids)))
    await db.execute(delete(ParkingSpot).where(ParkingSpot.id.in_(spot_ids)))
    await db.execute(delete(ParkingZone).where(ParkingZone.id.in_(zone_ids)))
    await db.execute(delete(ParkingSector).where(ParkingSector.id.in_(sector_ids)))
    await db.execute(delete(ParkingFloor).where(ParkingFloor.code == FLOOR))
    await db.commit()


async def _count(model, **where) -> int:
    async with AsyncSessionLocal() as db:
        q = select(func.count()).select_from(model)
        for key, value in where.items():
            q = q.where(getattr(model, key) == value)
        return (await db.execute(q)).scalar()


async def _spots_in_zone(zone_code: str) -> int:
    async with AsyncSessionLocal() as db:
        zid = await db.scalar(select(ParkingZone.id).where(ParkingZone.code == zone_code))
        if zid is None:
            return 0
        return await db.scalar(select(func.count()).select_from(ParkingSpot).where(ParkingSpot.zone_id == zid))


async def _ensure_worker(req):
    async with AsyncSessionLocal() as db:
        try:
            await ensure_mqtt_parking_config_async(db, req, create_missing_floor_sector=True)
            return None
        except Exception as exc:  # noqa: BLE001 - report any unhandled race failure
            return repr(exc)


async def _event_worker(req):
    async with AsyncSessionLocal() as db:
        try:
            await process_spot_event_async(db, req, display_port=None)
            return None
        except Exception as exc:  # noqa: BLE001
            return repr(exc)


async def run() -> bool:
    ok = True
    async with AsyncSessionLocal() as db:
        await _cleanup(db)
    try:
        # S1: many concurrent full auto-creates of the SAME new spot.
        req = SpotEventRequest(spot_code="L8-A-01-1", status=SpotStatus.FREE, detected_at=_now(),
                               source="CC", sector_code="L8-A", camera_zone_code="L8-A-01")
        errs = [e for e in await asyncio.gather(*[_ensure_worker(req) for _ in range(12)]) if e]
        floors = await _count(ParkingFloor, code="L8")
        zones = await _count(ParkingZone, code="L8-A-01")
        spots = await _count(ParkingSpot, code="L8-A-01-1")
        s1_ok = floors == 1 and zones == 1 and spots == 1 and not errs
        ok &= s1_ok
        print(f"S1 same-spot x12       : floors={floors} zones={zones} spots={spots} errors={len(errs)} -> {'OK' if s1_ok else 'FAIL'}")

        # S2: concurrent DIFFERENT spots in the SAME new camera zone.
        reqs = [SpotEventRequest(spot_code=f"L8-B-01-{n}", status=SpotStatus.FREE, detected_at=_now(),
                                 source="CC", sector_code="L8-B", camera_zone_code="L8-B-01") for n in range(1, 9)]
        errs = [e for e in await asyncio.gather(*[_ensure_worker(r) for r in reqs]) if e]
        zones = await _count(ParkingZone, code="L8-B-01")
        spots = await _spots_in_zone("L8-B-01")
        s2_ok = zones == 1 and spots == 8 and not errs
        ok &= s2_ok
        print(f"S2 same-zone diff x8   : zones={zones} spots_in_zone={spots} (expect 8) errors={len(errs)} -> {'OK' if s2_ok else 'FAIL'}")

        # S3: dedup race - concurrent identical events on one spot.
        async with AsyncSessionLocal() as db:
            await ensure_mqtt_parking_config_async(
                db,
                SpotEventRequest(spot_code="L8-C-01-1", status=SpotStatus.FREE, detected_at=_now(),
                                 source="CC", sector_code="L8-C", camera_zone_code="L8-C-01"),
                create_missing_floor_sector=True,
            )
        ev = SpotEventRequest(spot_code="L8-C-01-1", status=SpotStatus.OCCUPIED, detected_at=_now(),
                              source="CC", sector_code="L8-C", camera_zone_code="L8-C-01", event_id="dup-1")
        errs = [e for e in await asyncio.gather(*[_event_worker(ev) for _ in range(12)]) if e]
        async with AsyncSessionLocal() as db:
            sid = await db.scalar(select(ParkingSpot.id).where(ParkingSpot.code == "L8-C-01-1"))
            nev = await db.scalar(select(func.count()).select_from(SpotOccupancyEvent).where(SpotOccupancyEvent.spot_id == sid))
        s3_ok = nev == 1 and not errs
        ok &= s3_ok
        print(f"S3 dedup same-event x12: occupancy_events={nev} (expect 1) errors={len(errs)} -> {'OK' if s3_ok else 'FAIL'}")
    finally:
        async with AsyncSessionLocal() as db:
            await _cleanup(db)
        print(f"CLEANUP: remaining {FLOOR} floors={await _count(ParkingFloor, code='L8')}")
    return ok


def main() -> None:
    ok = asyncio.run(run())
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
