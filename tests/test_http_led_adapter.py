import asyncio
import json

import pytest
import httpx

from app.adapters.led.http import HttpLedDisplayAdapter


def test_http_led_adapter_posts_display_command():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"success": True})

    adapter = HttpLedDisplayAdapter(
        path="/api/v1/led/commands",
        timeout=1.0,
        transport=httpx.MockTransport(handler),
    )

    asyncio.run(
        adapter.show_sector_summary(
            display_code="DISP-B1-A",
            sector_code="B1-A",
            free_spots=93,
            arrow_direction="LEFT",
            parking_symbol="P",
            display_text="LEFT 93 P",
            message="B1-A 93",
            device_code="LED-B1-A",
            device_host="pgs-fake-led",
            device_port=9000,
            device_protocol="HTTP",
        )
    )

    assert len(requests) == 1
    assert str(requests[0].url) == "http://pgs-fake-led:9000/api/v1/led/commands"
    assert requests[0].method == "POST"
    payload = json.loads(requests[0].read())
    assert payload == {
        "display_code": "DISP-B1-A",
        "sector_code": "B1-A",
        "free_spots": 93,
        "arrow_direction": "LEFT",
        "parking_symbol": "P",
        "display_text": "LEFT 93 P",
        "message": "B1-A 93",
        "device_code": "LED-B1-A",
    }
    assert requests[0].headers["content-type"] == "application/json"


def _run_show(adapter: HttpLedDisplayAdapter) -> None:
    asyncio.run(
        adapter.show_sector_summary(
            display_code="DISP-B1-A",
            sector_code="B1-A",
            free_spots=93,
            arrow_direction="LEFT",
            parking_symbol="P",
            display_text="LEFT 93 P",
            message="B1-A 93",
            device_code="LED-B1-A",
            device_host="pgs-fake-led",
            device_port=9000,
            device_protocol="HTTP",
        )
    )


def test_http_led_adapter_propagates_timeout():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    adapter = HttpLedDisplayAdapter(
        path="/api/v1/led/commands",
        timeout=0.5,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.TimeoutException):
        _run_show(adapter)


def test_http_led_adapter_raises_on_server_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "device unavailable"})

    adapter = HttpLedDisplayAdapter(
        path="/api/v1/led/commands",
        timeout=1.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.HTTPStatusError):
        _run_show(adapter)


def test_http_led_adapter_rejects_non_http_protocol():
    adapter = HttpLedDisplayAdapter(path="/commands", timeout=1.0)

    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        asyncio.run(
            adapter.show_sector_summary(
                display_code="DISP-B1-A",
                sector_code="B1-A",
                free_spots=93,
                arrow_direction="LEFT",
                parking_symbol="P",
                display_text="LEFT 93 P",
                message="B1-A 93",
                device_code="LED-B1-A",
                device_host="pgs-fake-led",
                device_port=9000,
                device_protocol="TCP",
            )
        )
