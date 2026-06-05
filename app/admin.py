from fastapi import FastAPI

from app.api.led_simulator import LED_SIMULATOR_HTML
from app.core.database import engine
from app.domain.value_objects.arrow_direction import ARROW_DIRECTION_CHOICES
from app.models.guidance_display import GuidanceDisplay
from app.models.parking_floor import ParkingFloor
from app.models.parking_sector import ParkingSector
from app.models.parking_spot import ParkingSpot
from app.models.parking_zone import ParkingZone
from app.models.spot_occupancy_event import SpotOccupancyEvent
from app.models.user import User


def setup_admin(app: FastAPI) -> None:
    try:
        from starlette.requests import Request
        from starlette_admin import CustomView, EnumField
        from starlette_admin.contrib.sqla import Admin, ModelView

        from app.admin_auth import PGSAdminAuthProvider
    except ModuleNotFoundError:
        return

    class LedSimulatorAdmin(CustomView):
        async def render(self, request: Request, templates):
            return templates.TemplateResponse(
                request=request,
                name=self.template_path,
                context={
                    "title": self.title(request),
                    "led_simulator_html": LED_SIMULATOR_HTML,
                },
            )

    class ParkingFloorAdmin(ModelView):
        fields = ["id", "code", "title", "sort_order", "is_active", "created_at", "updated_at"]
        name = "Floor"
        label = "Floors"
        icon = "fa-solid fa-layer-group"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class ParkingSectorAdmin(ModelView):
        fields = [
            "id",
            "floor",
            "code",
            "sector_letter",
            "title",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        name = "Sector"
        label = "Sectors"
        icon = "fa-solid fa-table-cells-large"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class ParkingZoneAdmin(ModelView):
        fields = [
            "id",
            "sector",
            "code",
            "zone_number",
            "title",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        name = "Camera Zone"
        label = "Camera Zones"
        icon = "fa-solid fa-video"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class ParkingSpotAdmin(ModelView):
        fields = ["id", "zone", "code", "status", "sort_order", "is_active", "created_at", "updated_at"]
        name = "Parking Spot"
        label = "Parking Spots"
        icon = "fa-solid fa-square-parking"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class GuidanceDisplayAdmin(ModelView):
        fields = [
            "id",
            "sector",
            "code",
            "title",
            EnumField(
                "arrow_direction",
                choices=ARROW_DIRECTION_CHOICES,
                label="Arrow direction",
            ),
            "is_active",
            "created_at",
            "updated_at",
        ]
        name = "Guidance Display"
        label = "Guidance Displays"
        icon = "fa-solid fa-signs-post"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]

    class SpotOccupancyEventAdmin(ModelView):
        fields = ["id", "spot", "event_id", "dedup_key", "status", "source", "payload", "detected_at", "created_at"]
        name = "Spot Event"
        label = "Spot Events"
        icon = "fa-solid fa-clock-rotate-left"
        fields_default_sort = [("created_at", True)]

        def can_create(self, request: Request) -> bool:
            return False

        def can_edit(self, request: Request) -> bool:
            return False

        def can_delete(self, request: Request) -> bool:
            return False

    class UserAdmin(ModelView):
        fields = ["id", "username", "is_active", "created_at", "updated_at"]
        name = "User"
        label = "Users"
        icon = "fa-solid fa-user"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["username"]

        def can_create(self, request: Request) -> bool:
            return False

        def can_delete(self, request: Request) -> bool:
            return False

    admin = Admin(
        engine,
        title="PGS Admin",
        base_url="/admin",
        templates_dir="app/templates",
        auth_provider=PGSAdminAuthProvider(),
    )
    admin.add_view(
        LedSimulatorAdmin(
            label="LED Simulator",
            icon="fa-solid fa-display",
            path="/led-simulator",
            template_path="admin/led_simulator.html",
            name="led-simulator",
        )
    )
    admin.add_view(ParkingFloorAdmin(ParkingFloor))
    admin.add_view(ParkingSectorAdmin(ParkingSector))
    admin.add_view(ParkingZoneAdmin(ParkingZone))
    admin.add_view(ParkingSpotAdmin(ParkingSpot))
    admin.add_view(GuidanceDisplayAdmin(GuidanceDisplay))
    admin.add_view(SpotOccupancyEventAdmin(SpotOccupancyEvent))
    admin.add_view(UserAdmin(User))
    admin.mount_to(app)
