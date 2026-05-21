from enum import StrEnum


class SpotStatus(StrEnum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"
