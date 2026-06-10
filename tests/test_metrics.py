import asyncio

from prometheus_client import REGISTRY
from starlette.testclient import TestClient

from app.adapters.led.mock import MockLedDisplayAdapter
from app.services.led import publish_sector_display_messages

from tests.conftest import seed_display, seed_sector_with_camera_zone, seed_spot


def test_metrics_endpoint_exposes_counters():
    from app.main import app

    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "pgs_led_commands_total" in body
    assert "pgs_spot_events_total" in body


def test_led_sent_metric_increments_on_send(db_session):
    before = REGISTRY.get_sample_value("pgs_led_commands_total", {"status": "sent"}) or 0.0

    zone, camera_zone = seed_sector_with_camera_zone(db_session)
    seed_spot(db_session, camera_zone, code="A-001", status="FREE")
    seed_display(db_session, zone, code="ACTIVE", arrow_direction="LEFT", is_active=True)
    db_session.commit()

    sent = asyncio.run(
        publish_sector_display_messages(
            db_session,
            sector_id=zone.id,
            display_port=MockLedDisplayAdapter(),
        )
    )

    after = REGISTRY.get_sample_value("pgs_led_commands_total", {"status": "sent"}) or 0.0
    assert sent == 1
    assert after == before + 1
