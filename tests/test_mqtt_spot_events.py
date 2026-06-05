import pytest

from app.domain.value_objects.spot_status import SpotStatus
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.services.mqtt_spot_events import (
    build_spot_event_request_from_mqtt,
    ensure_mqtt_parking_config,
    normalize_mqtt_status,
    spot_id_from_topic,
)


def _seed_sector(db_session, sector_code: str = "B1-A") -> ParkingSector:
    floor_code, sector_letter = sector_code.split("-", maxsplit=1)
    floor = ParkingFloor(
        title=f"Floor {floor_code}",
        code=floor_code,
        sort_order=1,
        is_active=True,
    )
    db_session.add(floor)
    db_session.flush()

    sector = ParkingSector(
        floor_id=floor.id,
        title=f"Sector {sector_code}",
        code=sector_code,
        sector_letter=sector_letter,
        sort_order=1,
        is_active=True,
    )
    db_session.add(sector)
    db_session.flush()
    return sector


def test_spot_id_from_topic_extracts_spot_id():
    assert spot_id_from_topic("parking/spots/B1-A-01-1/status") == "B1-A-01-1"


def test_spot_id_from_topic_rejects_other_topics():
    assert spot_id_from_topic("parking/zones/B1-C/free") is None


def test_normalize_mqtt_status_maps_lowercase_values():
    assert normalize_mqtt_status("free") == SpotStatus.FREE
    assert normalize_mqtt_status("occupied") == SpotStatus.OCCUPIED


def test_build_spot_event_request_from_real_mqtt_payload():
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B1-A-01-1/status",
        payload={
            "spot_id": "B1-A-01-1",
            "zone_id": "B1-A",
            "status": "occupied",
            "plate": "Z188AW",
            "timestamp": "2026-06-01T11:09:57.617346",
        },
    )

    assert request.spot_code == "B1-A-01-1"
    assert request.sector_code == "B1-A"
    assert request.status == SpotStatus.OCCUPIED
    assert request.source == "MQTT"
    assert request.event_id == "B1-A-01-1:occupied:2026-06-01T11:09:57.617346"
    assert request.payload["plate"] == "Z188AW"


def test_build_spot_event_request_treats_payload_camera_zone_as_camera_zone_code():
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B1-A-16-2/status",
        payload={
            "spot_id": "B1-A-16-2",
            "zone_id": "B1-A-16",
            "status": "free",
            "plate": None,
            "timestamp": "2026-06-01T11:09:57.617346",
        },
    )

    assert request.sector_code == "B1-A"
    assert request.camera_zone_code == "B1-A-16"


def test_build_spot_event_request_rejects_legacy_spot_format():
    with pytest.raises(ValueError, match="Unsupported MQTT spot_id format"):
        build_spot_event_request_from_mqtt(
            topic="parking/spots/B1-B-036/status",
            payload={
                "spot_id": "B1-B-036",
                "zone_id": "B1-B",
                "status": "free",
                "plate": None,
                "timestamp": "2026-06-01T11:09:57.617346",
            },
        )


def test_ensure_mqtt_parking_config_creates_missing_zone_and_spot_for_configured_sector(db_session):
    _seed_sector(db_session, "B1-A")
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B1-A-01-1/status",
        payload={
            "spot_id": "B1-A-01-1",
            "zone_id": "B1-A",
            "status": "occupied",
            "plate": "Z188AW",
            "timestamp": "2026-06-01T11:09:57.617346",
        },
    )

    created = ensure_mqtt_parking_config(db_session, request)

    sector = db_session.query(ParkingSector).filter_by(code="B1-A").one()
    zone = db_session.query(ParkingZone).filter_by(sector_id=sector.id, code="B1-A-01").one()
    spot = db_session.query(ParkingSpot).filter_by(zone_id=zone.id, code="B1-A-01-1").one()

    assert created is True
    assert spot.status == "UNKNOWN"
    assert spot.sort_order == 1


def test_ensure_mqtt_parking_config_rejects_unconfigured_sector(db_session):
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B3-A-01-1/status",
        payload={
            "spot_id": "B3-A-01-1",
            "zone_id": "B3-A",
            "status": "free",
            "plate": None,
            "timestamp": "2026-06-01T11:10:51.305574",
        },
    )

    with pytest.raises(ValueError, match="Sector B3-A is not configured"):
        ensure_mqtt_parking_config(db_session, request)

    assert db_session.query(ParkingSector).count() == 0
    assert db_session.query(ParkingZone).count() == 0
    assert db_session.query(ParkingSpot).count() == 0


def test_ensure_mqtt_parking_config_can_create_floor_sector_in_development_mode(db_session):
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B3-A-01-1/status",
        payload={
            "spot_id": "B3-A-01-1",
            "zone_id": "B3-A",
            "status": "free",
            "plate": None,
            "timestamp": "2026-06-01T11:10:51.305574",
        },
    )

    created = ensure_mqtt_parking_config(
        db_session,
        request,
        create_missing_floor_sector=True,
    )

    assert created is True
    assert db_session.query(ParkingSector).filter_by(code="B3-A").one()
    assert db_session.query(ParkingZone).count() == 1
    assert db_session.query(ParkingSpot).count() == 1


def test_ensure_mqtt_parking_config_is_idempotent(db_session):
    _seed_sector(db_session, "B2-C")
    request = build_spot_event_request_from_mqtt(
        topic="parking/spots/B2-C-04-2/status",
        payload={
            "spot_id": "B2-C-04-2",
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
    assert db_session.query(ParkingSector).count() == 1
    assert db_session.query(ParkingZone).count() == 1
    assert db_session.query(ParkingSpot).count() == 1
