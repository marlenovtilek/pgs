from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.parking_zone import ParkingZone
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.schemas.zone_summary import ZoneSummaryItem, ZoneSummaryResponse
from app.domain.value_objects.spot_status import SpotStatus


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

