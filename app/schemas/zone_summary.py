from pydantic import BaseModel

class ZoneSummaryItem(BaseModel):
    zone_code: str
    zone_title: str
    total_spots: int
    free_spots: int
    occupied_spots: int
    offline_spots: int
    unknown_spots: int


class ZoneSummaryResponse(BaseModel):
    items: list[ZoneSummaryItem]
