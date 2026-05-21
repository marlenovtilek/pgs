from app.domain.value_objects.spot_status import SpotStatus


def calculate_zone_summary(statuses: list[SpotStatus]) -> dict[str, int]:
    free = sum(1 for status in statuses if status == SpotStatus.FREE)
    occupied = sum(1 for status in statuses if status == SpotStatus.OCCUPIED)
    offline = sum(1 for status in statuses if status == SpotStatus.OFFLINE)
    unknown = sum(1 for status in statuses if status == SpotStatus.UNKNOWN)
    total = len(statuses)

    return {
        "total": total,
        "free": free,
        "occupied": occupied,
        "offline": offline,
        "unknown": unknown,
    }
