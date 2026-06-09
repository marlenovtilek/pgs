import asyncio

import httpx

from app.simulation.fake_led_server import app, received_commands


def test_fake_led_server_receives_and_lists_commands():
    received_commands.clear()

    async def call_app() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://fake-led",
        ) as client:
            response = await client.post(
                "/api/v1/led/commands",
                json={
                    "display_code": "DISP-B1-A",
                    "sector_code": "B1-A",
                    "free_spots": 93,
                    "arrow_direction": "LEFT",
                    "parking_symbol": "P",
                    "display_text": "LEFT 93 P",
                    "message": "B1-A 93",
                    "device_code": "LED-B1-A",
                },
            )
            list_response = await client.get("/api/v1/led/commands")
            return response, list_response

    response, list_response = asyncio.run(call_app())

    assert response.status_code == 200
    assert response.json()["success"] is True

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["display_text"] == "LEFT 93 P"
