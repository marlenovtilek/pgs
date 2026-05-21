from pydantic import BaseModel


class SpotListItem(BaseModel):
    zone_code: str
    row_code: str
    spot_code: str
    status: str
    is_active: bool


class SpotListResponse(BaseModel):
    items: list[SpotListItem]


class SpotDetailResponse(BaseModel):
    zone_code: str
    row_code: str
    spot_code: str
    status: str
    is_active: bool
