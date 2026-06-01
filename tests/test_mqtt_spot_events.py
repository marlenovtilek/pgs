from app.domain.value_objects.spot_status import SpotStatus
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_row import ParkingRow
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.services.mqtt_spot_events import (
    build_spot_event_request_from_mqtt,
    ensure_mqtt_parking_config,
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


def test_ensure_mqtt_parking_config_creates_missing_zone_row_spot_and_display(db_session):
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

    created = ensure_mqtt_parking_config(db_session, request)

    zone = db_session.query(ParkingZone).filter_by(code="B1-C").one()
    row = db_session.query(ParkingRow).filter_by(zone_id=zone.id, code="B1-C").one()
    spot = db_session.query(ParkingSpot).filter_by(row_id=row.id, code="B1-C017").one()
    display = db_session.query(GuidanceDisplay).filter_by(code="DISP-B1-C").one()

    assert created is True
    assert spot.status == "UNKNOWN"
    assert spot.sort_order == 17
    assert display.zone_id == zone.id


def test_ensure_mqtt_parking_config_is_idempotent(db_session):
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B2-C04/status",
        payload={
            "spot_id": "B2-C04",
            "zone_id": "B2-C",
            "status": "free",
            "plate": None,
            "timestamp": "2026-06-01T11:10:51.305574",
        },
    )

    first = ensure_mqtt_parking_config(db_session, request)
    second = ensure_mqtt_parking_config(db_session, request)

    assert first is True
    assert second is False
    assert db_session.query(ParkingZone).count() == 1
    assert db_session.query(ParkingRow).count() == 1
    assert db_session.query(ParkingSpot).count() == 1
    assert db_session.query(GuidanceDisplay).count() == 1
