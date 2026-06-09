import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.ports.display import DisplayCommandPort
from app.models.guidance_display import GuidanceDisplay
from app.models.led_command_log import LedCommandLog
from app.models.led_device import LedDevice
from app.models.parking_spot import ParkingSpot
from app.models.parking_sector import ParkingSector
from app.models.parking_zone import ParkingZone
from app.services.display import (
    list_display_messages,
    list_display_messages_async,
    list_display_messages_for_camera_zone,
    list_display_messages_for_camera_zone_async,
)


logger = logging.getLogger(__name__)


def _message_payload(message) -> dict[str, Any]:
    return {
        "display_code": message.display_code,
        "sector_code": message.sector_code,
        "free_spots": message.free_spots,
        "arrow_direction": message.arrow_direction,
        "parking_symbol": message.parking_symbol,
        "display_text": message.display_text,
        "message": message.message,
    }


def _new_command_log(message, display, device, payload: dict[str, Any]) -> LedCommandLog:
    return LedCommandLog(
        display_id=display.id if display is not None else None,
        device_id=device.id if device is not None else None,
        display_code=message.display_code,
        device_code=device.code if device is not None else None,
        sector_code=message.sector_code,
        status="PENDING",
        payload=payload,
    )


def _device_kwargs(device) -> dict[str, Any]:
    return {
        "device_code": device.code if device is not None else None,
        "device_host": device.host if device is not None else None,
        "device_port": device.port if device is not None else None,
        "device_protocol": device.protocol if device is not None else None,
    }


def _display_target(
    db: Session,
    display_code: str,
) -> tuple[GuidanceDisplay | None, LedDevice | None]:
    row = db.execute(
        select(GuidanceDisplay, LedDevice)
        .outerjoin(LedDevice, GuidanceDisplay.led_device_id == LedDevice.id)
        .where(GuidanceDisplay.code == display_code)
    ).first()
    if row is None:
        return None, None
    return row


async def _display_target_async(
    db: AsyncSession,
    display_code: str,
) -> tuple[GuidanceDisplay | None, LedDevice | None]:
    row = (
        await db.execute(
            select(GuidanceDisplay, LedDevice)
            .outerjoin(LedDevice, GuidanceDisplay.led_device_id == LedDevice.id)
            .where(GuidanceDisplay.code == display_code)
        )
    ).first()
    if row is None:
        return None, None
    return row


async def _send_display_message(
    db: Session,
    *,
    message,
    display_port: DisplayCommandPort,
) -> bool:
    display, device = _display_target(db, message.display_code)
    payload = _message_payload(message)
    log = _new_command_log(message, display, device, payload)
    db.add(log)
    db.flush()

    if device is not None and not device.is_active:
        logger.warning(
            "led_send_skipped display=%s device=%s reason=inactive_device",
            message.display_code,
            device.code,
        )
        log.status = "FAILED"
        log.error_message = "LED device is inactive."
        db.commit()
        return False

    try:
        await display_port.show_sector_summary(**payload, **_device_kwargs(device))
    except Exception as exc:
        logger.warning(
            "led_send_failed display=%s device=%s error=%s",
            message.display_code,
            device.code if device is not None else None,
            exc,
        )
        log.status = "FAILED"
        log.error_message = str(exc)
        db.commit()
        return False

    log.status = "SENT"
    log.sent_at = datetime.now(timezone.utc)
    db.commit()
    return True


async def _send_display_message_async(
    db: AsyncSession,
    *,
    message,
    display_port: DisplayCommandPort,
) -> bool:
    display, device = await _display_target_async(db, message.display_code)
    payload = _message_payload(message)
    log = _new_command_log(message, display, device, payload)
    db.add(log)
    await db.flush()

    if device is not None and not device.is_active:
        logger.warning(
            "led_send_skipped display=%s device=%s reason=inactive_device",
            message.display_code,
            device.code,
        )
        log.status = "FAILED"
        log.error_message = "LED device is inactive."
        await db.commit()
        return False

    try:
        await display_port.show_sector_summary(**payload, **_device_kwargs(device))
    except Exception as exc:
        logger.warning(
            "led_send_failed display=%s device=%s error=%s",
            message.display_code,
            device.code if device is not None else None,
            exc,
        )
        log.status = "FAILED"
        log.error_message = str(exc)
        await db.commit()
        return False

    log.status = "SENT"
    log.sent_at = datetime.now(timezone.utc)
    await db.commit()
    return True


async def publish_sector_display_messages(
    db: Session,
    *,
    sector_id: int,
    display_port: DisplayCommandPort,
) -> int:
    sector_code = db.scalar(select(ParkingSector.code).where(ParkingSector.id == sector_id))
    if sector_code is None:
        return 0

    messages = list_display_messages(
        db,
        sector_code=sector_code,
        is_active=True,
    )

    sent = 0
    for message in messages:
        if await _send_display_message(db, message=message, display_port=display_port):
            sent += 1

    return sent


async def publish_spot_display_messages(
    db: Session,
    *,
    spot_id: int,
    display_port: DisplayCommandPort,
) -> int:
    camera_zone_id = db.scalar(
        select(ParkingZone.id)
        .join(ParkingSpot, ParkingSpot.zone_id == ParkingZone.id)
        .where(ParkingSpot.id == spot_id)
    )
    if camera_zone_id is None:
        return 0

    messages = list_display_messages_for_camera_zone(
        db,
        camera_zone_id=camera_zone_id,
        is_active=True,
    )

    sent = 0
    for message in messages:
        if await _send_display_message(db, message=message, display_port=display_port):
            sent += 1

    return sent


async def publish_spot_sector_display_messages(
    db: Session,
    *,
    spot_id: int,
    display_port: DisplayCommandPort,
) -> int:
    return await publish_spot_display_messages(
        db,
        spot_id=spot_id,
        display_port=display_port,
    )


async def publish_sector_display_messages_async(
    db: AsyncSession,
    *,
    sector_id: int,
    display_port: DisplayCommandPort,
) -> int:
    sector_code = await db.scalar(select(ParkingSector.code).where(ParkingSector.id == sector_id))
    if sector_code is None:
        return 0

    messages = await list_display_messages_async(
        db,
        sector_code=sector_code,
        is_active=True,
    )

    sent = 0
    for message in messages:
        if await _send_display_message_async(db, message=message, display_port=display_port):
            sent += 1

    return sent


async def publish_spot_display_messages_async(
    db: AsyncSession,
    *,
    spot_id: int,
    display_port: DisplayCommandPort,
) -> int:
    camera_zone_id = await db.scalar(
        select(ParkingZone.id)
        .join(ParkingSpot, ParkingSpot.zone_id == ParkingZone.id)
        .where(ParkingSpot.id == spot_id)
    )
    if camera_zone_id is None:
        return 0

    messages = await list_display_messages_for_camera_zone_async(
        db,
        camera_zone_id=camera_zone_id,
        is_active=True,
    )

    sent = 0
    for message in messages:
        if await _send_display_message_async(db, message=message, display_port=display_port):
            sent += 1

    return sent


async def publish_spot_sector_display_messages_async(
    db: AsyncSession,
    *,
    spot_id: int,
    display_port: DisplayCommandPort,
) -> int:
    return await publish_spot_display_messages_async(
        db,
        spot_id=spot_id,
        display_port=display_port,
    )
