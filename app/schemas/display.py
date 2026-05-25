from pydantic import BaseModel


class DisplayItem(BaseModel):
    zone_code: str
    display_code: str
    display_title: str
    arrow_direction: str
    is_active: bool

class DisplayListResponse(BaseModel):
    items: list[DisplayItem]

class DisplaySummaryResponse(BaseModel):
    display_code: str
    display_title: str
    zone_code: str
    arrow_direction: str
    total_spots: int
    free_spots: int
    occupied_spots: int

class DisplayListSummaryResponse(BaseModel):
    items: list[DisplaySummaryResponse]


class DisplayCreateRequest(BaseModel):
    title: str
    code: str
    zone_code: str
    arrow_direction: str
    is_active: bool = True

class DisplayUpdateRequest(BaseModel):
    title: str | None = None
    arrow_direction: str | None = None
    is_active: bool | None = None

class DisplayMessageResponse(BaseModel):
    display_code: str
    zone_code: str
    arrow_direction: str
    free_spots: int
    message: str

class DisplayMessageListResponse(BaseModel):
    items: list[DisplayMessageResponse]

