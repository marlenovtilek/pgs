from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.use_cases import calculate_zone_summary
from app.models.parking_zone import ParkingZone
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.schemas.display import DisplayMessageListResponse
from app.schemas.zone_summary import ZoneSummaryItem, ZoneSummaryResponse
from app.domain.value_objects.spot_status import SpotStatus
from app.services.display import list_display_messages


router = APIRouter(tags=["zones"])

@router.get("/zones/summary", response_model=ZoneSummaryResponse)
def get_zones_summary(db: Session = Depends(get_db)) -> ZoneSummaryResponse:
    statement = (
        select(
            ParkingZone.code.label("zone_code"),
            ParkingZone.title.label("zone_title"),
            func.count(ParkingSpot.id).label("total_spots"),
            func.sum(
                case(
                    (ParkingSpot.status == SpotStatus.FREE.value, 1),
                    else_=0,
                )
            ).label("free_spots"),
            func.sum(
                case(
                    (ParkingSpot.status == SpotStatus.OCCUPIED.value, 1),
                    else_=0,
                )
            ).label("occupied_spots"),
        )
        .join(ParkingRow, ParkingRow.zone_id == ParkingZone.id)
        .join(ParkingSpot, ParkingSpot.row_id == ParkingRow.id)
        .group_by(ParkingZone.id, ParkingZone.code, ParkingZone.title)
        .order_by(ParkingZone.code)
    )

    rows = db.execute(statement).all()

    items = [
        ZoneSummaryItem(
            zone_code=row.zone_code,
            zone_title=row.zone_title,
            total_spots=row.total_spots,
            free_spots=row.free_spots or 0,
            occupied_spots=row.occupied_spots or 0,
        )
        for row in rows
    ]
    
    return ZoneSummaryResponse(items=items)

@router.get("/zones/{zone_code}/summary", response_model=ZoneSummaryItem)
def get_zone_summary(zone_code: str, db: Session = Depends(get_db)) -> ZoneSummaryItem:
    zone = db.scalar(
        select(ParkingZone).where(ParkingZone.code == zone_code)
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found.")
        
    rows = db.execute(
        select(ParkingSpot.status)
        .join(ParkingRow, ParkingSpot.row_id == ParkingRow.id)
        .where(ParkingRow.zone_id == zone.id)
    ).all()

    statuses = [SpotStatus(row.status) for row in rows]

    summary = calculate_zone_summary(statuses)
    
    return ZoneSummaryItem(
        zone_code=zone.code,
        zone_title=zone.title,
        total_spots=summary["total"],
        free_spots=summary["free"],
        occupied_spots=summary["occupied"],
    )

@router.get("/zones/{zone_code}/messages", response_model=DisplayMessageListResponse)
def get_zone_messages(zone_code: str, is_active: bool | None = None, db: Session = Depends(get_db),) -> DisplayMessageListResponse:
    zone = db.scalar(
        select(ParkingZone).where(ParkingZone.code == zone_code)
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found.")

    return DisplayMessageListResponse(
        items=list_display_messages(
            db,
            zone_code=zone.code,
            is_active=is_active,
        )
    )
