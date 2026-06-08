import asyncio

from app.adapters.led.mock import MockLedDisplayAdapter
from app.services.led import publish_sector_display_messages, publish_spot_display_messages

from tests.conftest import seed_display, seed_spot, seed_sector_with_camera_zone


def test_publish_sector_display_messages_sends_active_display_commands(db_session):
    zone, camera_zone = seed_sector_with_camera_zone(db_session)
    seed_spot(db_session, camera_zone, code="A-001", status="FREE")
    seed_spot(db_session, camera_zone, code="A-002", status="OCCUPIED")
    seed_display(db_session, zone, code="ACTIVE", arrow_direction="LEFT", is_active=True)
    seed_display(db_session, zone, code="INACTIVE", arrow_direction="RIGHT", is_active=False)
    db_session.commit()
    adapter = MockLedDisplayAdapter()

    sent = asyncio.run(
        publish_sector_display_messages(
            db_session,
            sector_id=zone.id,
            display_port=adapter,
        )
    )

    assert sent == 1
    assert len(adapter.commands) == 1
    assert adapter.commands[0].display_code == "ACTIVE"
    assert adapter.commands[0].parking_symbol == "P"
    assert adapter.commands[0].display_text == "LEFT 1 P"
    assert adapter.commands[0].message == "A LEFT 1"


def test_publish_spot_display_messages_sends_only_connected_display_commands(db_session):
    sector, camera_zone_01 = seed_sector_with_camera_zone(
        db_session,
        sector_code="B1-A",
        camera_zone_code="B1-A-01",
    )
    _, camera_zone_02 = seed_sector_with_camera_zone(
        db_session,
        sector_code="B1-A",
        camera_zone_code="B1-A-02",
    )
    spot_01 = seed_spot(db_session, camera_zone_01, code="B1-A-01-1", status="FREE")
    seed_spot(db_session, camera_zone_02, code="B1-A-02-1", status="FREE")
    seed_display(
        db_session,
        sector,
        code="DISP-LINE-02-LEFT",
        arrow_direction="LEFT",
        camera_zones=[camera_zone_01],
    )
    seed_display(
        db_session,
        sector,
        code="DISP-LINE-02-RIGHT",
        arrow_direction="RIGHT",
        camera_zones=[camera_zone_02],
    )
    db_session.commit()
    adapter = MockLedDisplayAdapter()

    sent = asyncio.run(
        publish_spot_display_messages(
            db_session,
            spot_id=spot_01.id,
            display_port=adapter,
        )
    )

    assert sent == 1
    assert len(adapter.commands) == 1
    assert adapter.commands[0].display_code == "DISP-LINE-02-LEFT"
    assert adapter.commands[0].display_text == "LEFT 1 P"
