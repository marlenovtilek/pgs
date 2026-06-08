import pytest

from app.services.parking_structure import sort_order_from_code, split_sector_code


def test_sort_order_from_code_uses_trailing_digits() -> None:
    assert sort_order_from_code("B1") == 1
    assert sort_order_from_code("B1-A-01") == 1
    assert sort_order_from_code("B1-A-01-6") == 6
    assert sort_order_from_code("A") == 0


def test_split_sector_code_returns_floor_and_sector() -> None:
    assert split_sector_code("B1-A") == ("B1", "A")


def test_split_sector_code_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="FLOOR-SECTOR"):
        split_sector_code("B1")
