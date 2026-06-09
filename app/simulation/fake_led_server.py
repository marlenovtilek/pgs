from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field


class FakeLedCommandRequest(BaseModel):
    display_code: str
    sector_code: str
    free_spots: int = Field(ge=0)
    arrow_direction: str
    parking_symbol: str
    display_text: str
    message: str
    device_code: str | None = None


app = FastAPI(title="PGS Fake LED Server")
received_commands: list[dict[str, Any]] = []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/led/commands")
async def receive_led_command(request: FakeLedCommandRequest) -> dict[str, Any]:
    received_at = datetime.now(timezone.utc).isoformat()
    command = request.model_dump()
    received_commands.append(
        {
            "received_at": received_at,
            **command,
        }
    )
    print(
        "fake_led_received "
        f"display_code={request.display_code} "
        f"device_code={request.device_code} "
        f"text={request.display_text}"
    )
    return {
        "success": True,
        "received_at": received_at,
        "display_code": request.display_code,
        "device_code": request.device_code,
    }


@app.get("/api/v1/led/commands")
async def list_received_led_commands() -> dict[str, list[dict[str, Any]]]:
    return {"items": received_commands}
