from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.async_database import get_async_db
from app.models.parking_zone import ParkingZone
from app.schemas.display import DisplayMessageListResponse
from app.schemas.zone_summary import ZoneSummaryItem, ZoneSummaryResponse
from app.services.display import list_display_messages_async
from app.services.zone_summary import (
    get_zone_summary_item_async,
    list_zone_summary_items_async,
)


router = APIRouter(tags=["zones"])

@router.get("/zones/summary", response_model=ZoneSummaryResponse)
async def get_zones_summary(
    db: AsyncSession = Depends(get_async_db),
) -> ZoneSummaryResponse:
    return ZoneSummaryResponse(items=await list_zone_summary_items_async(db))

@router.get("/zones/{zone_code}/summary", response_model=ZoneSummaryItem)
async def get_zone_summary(
    zone_code: str,
    db: AsyncSession = Depends(get_async_db),
) -> ZoneSummaryItem:
    summary = await get_zone_summary_item_async(db, zone_code)
    if summary is None:
        raise HTTPException(status_code=404, detail="Zone not found.")

    return summary

@router.get("/zones/{zone_code}/messages", response_model=DisplayMessageListResponse)
async def get_zone_messages(
    zone_code: str,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> DisplayMessageListResponse:
    zone = await db.scalar(
        select(ParkingZone).where(ParkingZone.code == zone_code)
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found.")

    return DisplayMessageListResponse(
        items=await list_display_messages_async(
            db,
            zone_code=zone.code,
            is_active=is_active,
        )
    )
