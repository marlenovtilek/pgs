from app.services.parking_codes import (
    is_new_parking_spot_code,
    parse_parking_spot_code,
    row_code_from_spot_code,
    zone_code_from_spot_code,
)


def test_parse_parking_spot_code_splits_new_camera_zone_format():
    parsed = parse_parking_spot_code("B1-A-01-1")

    assert parsed is not None
    assert parsed.level_code == "B1"
    assert parsed.sector_code == "A"
    assert parsed.camera_zone_number == "01"
    assert parsed.spot_number == "1"
    assert parsed.zone_code == "B1-A"
    assert parsed.camera_zone_code == "B1-A-01"


def test_is_new_parking_spot_code_accepts_only_camera_zone_format():
    assert is_new_parking_spot_code("B1-A-01-1") is True
    assert is_new_parking_spot_code("B1-B-036") is False
    assert is_new_parking_spot_code("B1-C009") is False


def test_parse_parking_spot_code_normalizes_legacy_format_to_camera_zone():
    parsed = parse_parking_spot_code("B1-C009")

    assert parsed is not None
    assert parsed.level_code == "B1"
    assert parsed.zone_letter == "C"
    assert parsed.camera_zone_number == "02"
    assert parsed.spot_number == "3"
    assert parsed.zone_code == "B1-C"
    assert parsed.camera_zone_code == "B1-C-02"


def test_parse_parking_spot_code_normalizes_hyphenated_legacy_format():
    parsed = parse_parking_spot_code("B1-B-036")

    assert parsed is not None
    assert parsed.level_code == "B1"
    assert parsed.sector_code == "B"
    assert parsed.camera_zone_number == "06"
    assert parsed.spot_number == "6"
    assert parsed.zone_code == "B1-B"
    assert parsed.camera_zone_code == "B1-B-06"


def test_zone_code_from_spot_code_returns_level_zone():
    assert zone_code_from_spot_code("B2-C-04-2") == "B2-C"


def test_row_code_from_spot_code_returns_camera_zone():
    assert row_code_from_spot_code("B2-C-04-2") == "B2-C-04"


def test_parse_parking_spot_code_rejects_unknown_format():
    assert parse_parking_spot_code("A-001") is None
