from app.domain.value_objects.spot_status import SpotStatus
from app.services.mqtt_spot_events import (
    build_spot_event_request_from_mqtt,
    normalize_mqtt_status,
    spot_id_from_topic,
)


def test_spot_id_from_topic_extracts_spot_id():
    assert spot_id_from_topic("parking/spots/B1-C018/status") == "B1-C018"


def test_spot_id_from_topic_rejects_other_topics():
    assert spot_id_from_topic("parking/zones/B1-C/free") is None


def test_normalize_mqtt_status_maps_lowercase_values():
    assert normalize_mqtt_status("free") == SpotStatus.FREE
    assert normalize_mqtt_status("occupied") == SpotStatus.OCCUPIED


def test_build_spot_event_request_from_real_mqtt_payload():
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B1-C017/status",
        payload={
            "spot_id": "B1-C017",
            "zone_id": "B1-C",
            "status": "occupied",
            "plate": "Z188AW",
            "timestamp": "2026-06-01T11:09:57.617346",
        },
    )

    assert request.spot_code == "B1-C017"
    assert request.zone_code == "B1-C"
    assert request.status == SpotStatus.OCCUPIED
    assert request.source == "MQTT"
    assert request.event_id == "B1-C017:occupied:2026-06-01T11:09:57.617346"
    assert request.payload["plate"] == "Z188AW"
