from app.services.parking_codes import (
    is_new_parking_spot_code,
    parse_parking_spot_code,
    camera_zone_code_from_spot_code,
    sector_code_from_spot_code,
)


def test_parse_parking_spot_code_splits_new_camera_zone_format():
    parsed = parse_parking_spot_code("B1-A-01-1")

    assert parsed is not None
    assert parsed.level_code == "B1"
    assert parsed.sector_letter == "A"
    assert parsed.sector_code == "B1-A"
    assert parsed.camera_zone_number == "01"
    assert parsed.spot_number == "1"
    assert parsed.camera_zone_code == "B1-A-01"


def test_is_new_parking_spot_code_accepts_only_camera_zone_format():
    assert is_new_parking_spot_code("B1-A-01-1") is True
    assert is_new_parking_spot_code("B1-B-036") is False
    assert is_new_parking_spot_code("B1-C009") is False


def test_parse_parking_spot_code_rejects_old_formats():
    assert parse_parking_spot_code("B1-C009") is None
    assert parse_parking_spot_code("B1-B-036") is None


def test_sector_code_from_spot_code_returns_floor_sector():
    assert sector_code_from_spot_code("B2-C-04-2") == "B2-C"


def test_camera_zone_code_from_spot_code_returns_camera_zone():
    assert camera_zone_code_from_spot_code("B2-C-04-2") == "B2-C-04"


def test_parse_parking_spot_code_rejects_unknown_format():
    assert parse_parking_spot_code("A-001") is None
