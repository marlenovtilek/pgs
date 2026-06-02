from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.parking_zone import ParkingZone
from app.schemas.display import DisplayMessageListResponse
from app.schemas.zone_summary import ZoneSummaryItem, ZoneSummaryResponse
from app.services.display import list_display_messages
from app.services.zone_summary import get_zone_summary_item, list_zone_summary_items


router = APIRouter(tags=["zones"])

@router.get("/zones/summary", response_model=ZoneSummaryResponse)
def get_zones_summary(db: Session = Depends(get_db)) -> ZoneSummaryResponse:
    return ZoneSummaryResponse(items=list_zone_summary_items(db))

@router.get("/zones/{zone_code}/summary", response_model=ZoneSummaryItem)
def get_zone_summary(zone_code: str, db: Session = Depends(get_db)) -> ZoneSummaryItem:
    summary = get_zone_summary_item(db, zone_code)
    if summary is None:
        raise HTTPException(status_code=404, detail="Zone not found.")

    return summary

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
