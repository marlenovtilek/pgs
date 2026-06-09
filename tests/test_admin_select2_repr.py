from app.models.guidance_display import GuidanceDisplay
from app.models.led_command_log import LedCommandLog
from app.models.led_device import LedDevice
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.models.user import User
from app.models.admin_repr import admin_select2_text


def test_admin_select2_reprs_return_html_fragments():
    models = [
        ParkingFloor(code="B1", title="Floor B1"),
        ParkingSector(code="B1-A", title="Sector B1-A", sector_letter="A", floor_id=1),
        ParkingZone(code="B1-A-01", title="Camera Zone B1-A-01", zone_number="01", sector_id=1),
        ParkingSpot(code="B1-A-01-1", zone_id=1),
        GuidanceDisplay(code="DISP-LINE-01-RIGHT", title="Line 01 Right", sector_id=1),
        LedDevice(code="LED-01", title="LED 01", host="192.168.1.50", port=5000),
        LedCommandLog(display_code="DISP-LINE-01-RIGHT", sector_code="B1-A", status="SENT", payload={}),
        User(username="admin", password_hash="hash"),
    ]

    for model in models:
        assert model.__admin_select2_repr__(None).startswith("<span>")
        assert model.__admin_select2_repr__(None).endswith("</span>")


def test_admin_select2_text_escapes_html():
    assert admin_select2_text("B1-<A>") == "<span>B1-&lt;A&gt;</span>"
