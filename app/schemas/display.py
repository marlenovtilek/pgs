from typing import Annotated

from pydantic import AfterValidator, BaseModel

from app.domain.value_objects.arrow_direction import ArrowDirection, is_configurable_arrow_direction


def validate_configurable_arrow_direction(value: ArrowDirection) -> ArrowDirection:
    if not is_configurable_arrow_direction(value.value):
        raise ValueError("FULL is a system state and cannot be configured manually.")
    return value


ConfigurableArrowDirection = Annotated[
    ArrowDirection,
    AfterValidator(validate_configurable_arrow_direction),
]


class DisplayItem(BaseModel):
    sector_code: str
    display_code: str
    display_title: str
    arrow_direction: str
    is_active: bool

class DisplayListResponse(BaseModel):
    items: list[DisplayItem]

class DisplaySummaryResponse(BaseModel):
    display_code: str
    display_title: str
    sector_code: str
    arrow_direction: str
    total_spots: int
    free_spots: int
    occupied_spots: int

class DisplayListSummaryResponse(BaseModel):
    items: list[DisplaySummaryResponse]


class DisplayCreateRequest(BaseModel):
    title: str
    code: str
    sector_code: str
    arrow_direction: ConfigurableArrowDirection
    is_active: bool = True

class DisplayUpdateRequest(BaseModel):
    title: str | None = None
    arrow_direction: ConfigurableArrowDirection | None = None
    is_active: bool | None = None

class DisplayMessageResponse(BaseModel):
    display_code: str
    sector_code: str
    arrow_direction: str
    free_spots: int
    parking_symbol: str
    display_text: str
    message: str

class DisplayMessageListResponse(BaseModel):
    items: list[DisplayMessageResponse]


class EntryDisplayMessageResponse(BaseModel):
    display_code: str
    title: str
    lines: list[str]
    free_spots: int
    message: str
