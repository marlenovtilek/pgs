from functools import lru_cache

from app.adapters.led.http import HttpLedDisplayAdapter
from app.adapters.led.mock import mock_led_adapter
from app.core.config import settings
from app.domain.ports.display import DisplayCommandPort


@lru_cache(maxsize=1)
def get_led_display_adapter() -> DisplayCommandPort:
    adapter_name = settings.led_adapter.lower()
    if adapter_name == "mock":
        return mock_led_adapter
    if adapter_name == "http":
        return HttpLedDisplayAdapter(
            path=settings.led_http_path,
            timeout=settings.led_http_timeout,
        )

    raise ValueError(f"Unsupported LED adapter: {settings.led_adapter}")
