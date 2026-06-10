"""Sequential load test for PGS spot-event processing.

Builds an isolated parking structure (a dedicated floor), drives many spot
events through the real async processing path, reports throughput, then
removes all of its own data.

Run inside the stack:

    docker compose run --rm -v ./scripts:/app/scripts pgs-api \
        python -m scripts.load_test

Options: --zones, --spots-per-zone, --floor (see --help).
"""
import argparse
import asyncio
import time
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.adapters.led.mock import MockLedDisplayAdapter
from app.core.async_database import AsyncSessionLocal
from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay, guidance_display_zones
from app.models.led_command_log import LedCommandLog
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.schemas.spot_event import SpotEventRequest
from app.services.spot_events import process_spot_event_async


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _cleanup(db, floor_code: str) -> None:
    sector_ids = select(ParkingSector.id).where(
        ParkingSector.floor_id.in_(select(ParkingFloor.id).where(ParkingFloor.code == floor_code))
    )
    zone_ids = select(ParkingZone.id).where(ParkingZone.sector_id.in_(sector_ids))
    spot_ids = select(ParkingSpot.id).where(ParkingSpot.zone_id.in_(zone_ids))
    display_ids = select(GuidanceDisplay.id).where(GuidanceDisplay.sector_id.in_(sector_ids))
    await db.execute(delete(LedCommandLog).where(LedCommandLog.display_id.in_(display_ids)))
    await db.execute(delete(SpotOccupancyEvent).where(SpotOccupancyEvent.spot_id.in_(spot_ids)))
    await db.execute(delete(guidance_display_zones).where(guidance_display_zones.c.display_id.in_(display_ids)))
    await db.execute(delete(GuidanceDisplay).where(GuidanceDisplay.id.in_(display_ids)))
    await db.execute(delete(ParkingSpot).where(ParkingSpot.id.in_(spot_ids)))
    await db.execute(delete(ParkingZone).where(ParkingZone.id.in_(zone_ids)))
    await db.execute(delete(ParkingSector).where(ParkingSector.id.in_(sector_ids)))
    await db.execute(delete(ParkingFloor).where(ParkingFloor.code == floor_code))
    await db.commit()


async def run(floor_code: str, sector_code: str, n_zones: int, n_per_zone: int) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await _cleanup(db, floor_code)

            t = time.perf_counter()
            floor = ParkingFloor(title="LoadTest", code=floor_code, sort_order=1, is_active=True)
            db.add(floor)
            await db.flush()
            sector = ParkingSector(
                floor_id=floor.id, title="LT Sector", code=sector_code,
                sector_letter=sector_code.split("-")[-1], sort_order=1, is_active=True,
            )
            db.add(sector)
            await db.flush()
            zones = [
                ParkingZone(
                    sector_id=sector.id, title=f"CZ {sector_code}-{z:03d}",
                    code=f"{sector_code}-{z:03d}", zone_number=f"{z:03d}", sort_order=z, is_active=True,
                )
                for z in range(1, n_zones + 1)
            ]
            db.add_all(zones)
            await db.flush()
            spots = [
                ParkingSpot(
                    zone_id=zone.id, code=f"{zone.code}-{s}", status=SpotStatus.FREE.value,
                    sort_order=s, is_active=True,
                )
                for zone in zones for s in range(1, n_per_zone + 1)
            ]
            db.add_all(spots)
            await db.flush()
            display = GuidanceDisplay(
                title="LT Display", code="LT-DISP-ALL", sector_id=sector.id,
                arrow_direction="AHEAD", is_active=True,
            )
            display.zones = zones
            db.add(display)
            await db.commit()
            print(f"SETUP  : {len(zones)} zones + {len(spots)} spots + 1 display in {time.perf_counter() - t:.2f}s")

            spot_codes = [sp.code for sp in spots]
            t = time.perf_counter()
            for i, code in enumerate(spot_codes):
                req = SpotEventRequest(
                    spot_code=code, status=SpotStatus.OCCUPIED, detected_at=_now(),
                    source="LT", event_id=f"ing-{i}",
                )
                await process_spot_event_async(db, req, display_port=None)
            dt = time.perf_counter() - t
            print(f"INGEST : {len(spot_codes)} events (no display) in {dt:.2f}s = {len(spot_codes) / dt:.0f} ev/s")

            adapter = MockLedDisplayAdapter()
            recalc = [f"{z.code}-1" for z in zones]
            t = time.perf_counter()
            for i, code in enumerate(recalc):
                req = SpotEventRequest(
                    spot_code=code, status=SpotStatus.FREE, detected_at=_now(),
                    source="LT", event_id=f"rec-{i}",
                )
                await process_spot_event_async(db, req, display_port=adapter)
            dt = time.perf_counter() - t
            print(f"RECALC : {len(recalc)} events (display sums {len(spots)} spots each) in {dt:.2f}s = {len(recalc) / dt:.0f} ev/s")
        finally:
            await _cleanup(db, floor_code)
            left = (await db.execute(select(ParkingFloor.id).where(ParkingFloor.code == floor_code))).all()
            print(f"CLEANUP: load-test data removed (remaining {floor_code} floor rows={len(left)})")


def main() -> None:
    parser = argparse.ArgumentParser(description="PGS sequential load test (self-cleaning).")
    parser.add_argument("--floor", default="L9", help="isolated floor code (letter+digits, e.g. L9)")
    parser.add_argument("--sector", default="L9-Z", help="isolated sector code")
    parser.add_argument("--zones", type=int, default=300, help="camera zones to create")
    parser.add_argument("--spots-per-zone", type=int, default=6, help="spots per camera zone")
    args = parser.parse_args()
    asyncio.run(run(args.floor, args.sector, args.zones, args.spots_per_zone))


if __name__ == "__main__":
    main()
