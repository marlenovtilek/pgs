from datetime import datetime
from typing import Any

from app.domain.value_objects.spot_status import SpotStatus
from app.schemas.spot_event import SpotEventRequest


MQTT_STATUS_MAP = {
    "free": SpotStatus.FREE,
    "occupied": SpotStatus.OCCUPIED,
    "offline": SpotStatus.OFFLINE,
    "unknown": SpotStatus.UNKNOWN,
}


def spot_id_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 4:
        return None
    if parts[0] != "parking" or parts[1] != "spots" or parts[3] != "status":
        return None
    return parts[2]


def parse_mqtt_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_mqtt_status(value: str) -> SpotStatus:
    status = MQTT_STATUS_MAP.get(value.lower())
    if status is None:
        raise ValueError(f"Unsupported MQTT spot status: {value}")
    return status


def build_spot_event_request_from_mqtt(
    *,
    topic: str,
    payload: dict[str, Any],
) -> SpotEventRequest:
    topic_spot_id = spot_id_from_topic(topic)
    payload_spot_id = payload.get("spot_id")
    spot_id = payload_spot_id or topic_spot_id
    if not spot_id:
        raise ValueError("MQTT spot status event does not include spot_id.")

    if topic_spot_id is not None and payload_spot_id is not None and topic_spot_id != payload_spot_id:
        raise ValueError(
            f"MQTT spot status topic spot_id '{topic_spot_id}' does not match payload spot_id '{payload_spot_id}'."
        )

    status = payload.get("status")
    if not isinstance(status, str):
        raise ValueError("MQTT spot status event does not include string status.")

    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, str):
        raise ValueError("MQTT spot status event does not include string timestamp.")

    event_id = f"{spot_id}:{status}:{timestamp}"

    return SpotEventRequest(
        spot_code=spot_id,
        zone_code=payload.get("zone_id"),
        status=normalize_mqtt_status(status),
        detected_at=parse_mqtt_timestamp(timestamp),
        source="MQTT",
        event_id=event_id,
        payload=payload,
    )
