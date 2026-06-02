from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.services.zone_summary import (
    get_zone_summary_item,
    get_zone_summary_item_async,
    list_zone_summary_items,
    list_zone_summary_items_async,
)


@dataclass(slots=True)
class ZoneReconciliationResult:
    zone_code: str
    mqtt_free_spots: int
    pgs_free_spots: int | None
    diff: int | None
    total_spots: int | None
    occupied_spots: int | None
    offline_spots: int | None
    unknown_spots: int | None


@dataclass(slots=True)
class TotalReconciliationResult:
    mqtt_free_spots: int
    pgs_free_spots: int
    diff: int


def zone_id_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 4:
        return None
    if parts[0] != "parking" or parts[1] != "zones" or parts[3] != "free":
        return None
    return parts[2]


def is_total_free_topic(topic: str) -> bool:
    return topic == "parking/total/free"


def free_spots_from_payload(payload: dict[str, Any]) -> int:
    free_spots = payload.get("free_spots")
    if not isinstance(free_spots, int):
        raise ValueError("MQTT free event does not include integer free_spots.")
    return free_spots


def reconcile_zone_free_event(
    db: Session,
    *,
    topic: str,
    payload: dict[str, Any],
) -> ZoneReconciliationResult:
    topic_zone_id = zone_id_from_topic(topic)
    payload_zone_id = payload.get("zone_id")
    zone_code = payload_zone_id or topic_zone_id
    if not isinstance(zone_code, str) or not zone_code:
        raise ValueError("MQTT zone free event does not include zone_id.")

    if topic_zone_id is not None and payload_zone_id is not None and topic_zone_id != payload_zone_id:
        raise ValueError(
            f"MQTT zone free topic zone_id '{topic_zone_id}' does not match payload zone_id '{payload_zone_id}'."
        )

    mqtt_free_spots = free_spots_from_payload(payload)
    summary = get_zone_summary_item(db, zone_code)
    if summary is None:
        return ZoneReconciliationResult(
            zone_code=zone_code,
            mqtt_free_spots=mqtt_free_spots,
            pgs_free_spots=None,
            diff=None,
            total_spots=None,
            occupied_spots=None,
            offline_spots=None,
            unknown_spots=None,
        )

    return ZoneReconciliationResult(
        zone_code=zone_code,
        mqtt_free_spots=mqtt_free_spots,
        pgs_free_spots=summary.free_spots,
        diff=mqtt_free_spots - summary.free_spots,
        total_spots=summary.total_spots,
        occupied_spots=summary.occupied_spots,
        offline_spots=summary.offline_spots,
        unknown_spots=summary.unknown_spots,
    )


def reconcile_total_free_event(
    db: Session,
    *,
    payload: dict[str, Any],
) -> TotalReconciliationResult:
    mqtt_free_spots = free_spots_from_payload(payload)
    pgs_free_spots = sum(item.free_spots for item in list_zone_summary_items(db))

    return TotalReconciliationResult(
        mqtt_free_spots=mqtt_free_spots,
        pgs_free_spots=pgs_free_spots,
        diff=mqtt_free_spots - pgs_free_spots,
    )


async def reconcile_zone_free_event_async(
    db: AsyncSession,
    *,
    topic: str,
    payload: dict[str, Any],
) -> ZoneReconciliationResult:
    topic_zone_id = zone_id_from_topic(topic)
    payload_zone_id = payload.get("zone_id")
    zone_code = payload_zone_id or topic_zone_id
    if not isinstance(zone_code, str) or not zone_code:
        raise ValueError("MQTT zone free event does not include zone_id.")

    if topic_zone_id is not None and payload_zone_id is not None and topic_zone_id != payload_zone_id:
        raise ValueError(
            f"MQTT zone free topic zone_id '{topic_zone_id}' does not match payload zone_id '{payload_zone_id}'."
        )

    mqtt_free_spots = free_spots_from_payload(payload)
    summary = await get_zone_summary_item_async(db, zone_code)
    if summary is None:
        return ZoneReconciliationResult(
            zone_code=zone_code,
            mqtt_free_spots=mqtt_free_spots,
            pgs_free_spots=None,
            diff=None,
            total_spots=None,
            occupied_spots=None,
            offline_spots=None,
            unknown_spots=None,
        )

    return ZoneReconciliationResult(
        zone_code=zone_code,
        mqtt_free_spots=mqtt_free_spots,
        pgs_free_spots=summary.free_spots,
        diff=mqtt_free_spots - summary.free_spots,
        total_spots=summary.total_spots,
        occupied_spots=summary.occupied_spots,
        offline_spots=summary.offline_spots,
        unknown_spots=summary.unknown_spots,
    )


async def reconcile_total_free_event_async(
    db: AsyncSession,
    *,
    payload: dict[str, Any],
) -> TotalReconciliationResult:
    mqtt_free_spots = free_spots_from_payload(payload)
    pgs_free_spots = sum(
        item.free_spots for item in await list_zone_summary_items_async(db)
    )

    return TotalReconciliationResult(
        mqtt_free_spots=mqtt_free_spots,
        pgs_free_spots=pgs_free_spots,
        diff=mqtt_free_spots - pgs_free_spots,
    )
