from fastapi import FastAPI

from app.api.led_simulator import LED_SIMULATOR_HTML
from app.core.database import engine
from app.domain.value_objects.arrow_direction import ARROW_DIRECTION_CHOICES
from app.models.guidance_display import GuidanceDisplay
from app.models.led_command_log import LedCommandLog
from app.models.led_device import LedDevice
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
        from starlette_admin.i18n import I18nConfig

        from app.admin_auth import PGSAdminAuthProvider
    except ModuleNotFoundError:
        return

    admin_field_labels = {
        "id": "ID",
        "floor": "Этаж",
        "sector": "Сектор",
        "zone": "Зона камеры",
        "spot": "Парковочное место",
        "display": "Табло",
        "device": "LED-устройство",
        "led_device": "LED-устройство",
        "zones": "Зоны камер",
        "code": "Код",
        "title": "Название",
        "username": "Логин",
        "sector_letter": "Буква сектора",
        "zone_number": "Номер зоны",
        "status": "Статус",
        "arrow_direction": "Стрелка",
        "host": "Хост",
        "port": "Порт",
        "protocol": "Протокол",
        "display_code": "Код табло",
        "device_code": "Код устройства",
        "sector_code": "Код сектора",
        "event_id": "ID события",
        "dedup_key": "Ключ дедупликации",
        "source": "Источник",
        "payload": "Данные",
        "error_message": "Ошибка",
        "sort_order": "Порядок сортировки",
        "is_active": "Активно",
        "detected_at": "Время обнаружения",
        "created_at": "Создано",
        "updated_at": "Обновлено",
        "sent_at": "Отправлено",
    }

    class RussianModelView(ModelView):
        field_labels = {}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            labels = {**admin_field_labels, **self.field_labels}
            for field in self.fields:
                if field.name in labels:
                    field.label = labels[field.name]

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

    class ParkingFloorAdmin(RussianModelView):
        fields = ["id", "code", "title", "sort_order", "is_active", "created_at", "updated_at"]
        name = "Этаж"
        label = "Этажи"
        icon = "fa-solid fa-layer-group"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class ParkingSectorAdmin(RussianModelView):
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
        name = "Сектор"
        label = "Секторы"
        icon = "fa-solid fa-table-cells-large"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class ParkingZoneAdmin(RussianModelView):
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
        name = "Зона камеры"
        label = "Зоны камер"
        icon = "fa-solid fa-video"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class ParkingSpotAdmin(RussianModelView):
        fields = ["id", "zone", "code", "status", "sort_order", "is_active", "created_at", "updated_at"]
        name = "Парковочное место"
        label = "Парковочные места"
        icon = "fa-solid fa-square-parking"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["sort_order", "code"]

    class GuidanceDisplayAdmin(RussianModelView):
        fields = [
            "id",
            "sector",
            "led_device",
            "code",
            "title",
            "zones",
            EnumField(
                "arrow_direction",
                choices=ARROW_DIRECTION_CHOICES,
                label="Стрелка",
            ),
            "is_active",
            "created_at",
            "updated_at",
        ]
        name = "Навигационное табло"
        label = "Навигационные табло"
        icon = "fa-solid fa-signs-post"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]

    class LedDeviceAdmin(RussianModelView):
        fields = [
            "id",
            "code",
            "title",
            "host",
            "port",
            "protocol",
            "is_active",
            "created_at",
            "updated_at",
        ]
        name = "LED-устройство"
        label = "LED-устройства"
        icon = "fa-solid fa-tower-broadcast"
        exclude_fields_from_create = ["created_at", "updated_at"]
        exclude_fields_from_edit = ["created_at", "updated_at"]
        fields_default_sort = ["code"]

    class LedCommandLogAdmin(RussianModelView):
        fields = [
            "id",
            "display",
            "device",
            "display_code",
            "device_code",
            "sector_code",
            "status",
            "payload",
            "error_message",
            "created_at",
            "sent_at",
        ]
        name = "Журнал LED-команд"
        label = "Журнал LED-команд"
        icon = "fa-solid fa-paper-plane"
        fields_default_sort = [("created_at", True)]

        def can_create(self, request: Request) -> bool:
            return False

        def can_edit(self, request: Request) -> bool:
            return False

        def can_delete(self, request: Request) -> bool:
            return False

    class SpotOccupancyEventAdmin(RussianModelView):
        fields = ["id", "spot", "event_id", "dedup_key", "status", "source", "payload", "detected_at", "created_at"]
        name = "Событие места"
        label = "События мест"
        icon = "fa-solid fa-clock-rotate-left"
        fields_default_sort = [("created_at", True)]

        def can_create(self, request: Request) -> bool:
            return False

        def can_edit(self, request: Request) -> bool:
            return False

        def can_delete(self, request: Request) -> bool:
            return False

    class UserAdmin(RussianModelView):
        fields = ["id", "username", "is_active", "created_at", "updated_at"]
        name = "Пользователь"
        label = "Пользователи"
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
        title="Админка PGS",
        base_url="/admin",
        templates_dir="app/templates",
        statics_dir="app/static/admin",
        auth_provider=PGSAdminAuthProvider(),
        i18n_config=I18nConfig(default_locale="ru", language_switcher=["ru"]),
    )
    admin.add_view(
        LedSimulatorAdmin(
            label="LED-симулятор",
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
    admin.add_view(LedDeviceAdmin(LedDevice))
    admin.add_view(GuidanceDisplayAdmin(GuidanceDisplay))
    admin.add_view(LedCommandLogAdmin(LedCommandLog))
    admin.add_view(SpotOccupancyEventAdmin(SpotOccupancyEvent))
    admin.add_view(UserAdmin(User))
    admin.mount_to(app)
