from app.domain.use_cases import calculate_zone_summary
from app.domain.value_objects.spot_status import SpotStatus


def test_calculate_zone_summary_counts_all_statuses():
    summary = calculate_zone_summary(
        [
            SpotStatus.FREE,
            SpotStatus.FREE,
            SpotStatus.OCCUPIED,
            SpotStatus.OFFLINE,
            SpotStatus.UNKNOWN,
        ]
    )

    assert summary == {
        "total": 5,
        "free": 2,
        "occupied": 1,
        "offline": 1,
        "unknown": 1,
    }
