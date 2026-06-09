from typing import Any

import httpx


class HttpLedDisplayAdapter:
    def __init__(
        self,
        *,
        path: str,
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.path = path if path.startswith("/") else f"/{path}"
        self.timeout = timeout
        self.transport = transport

    async def show_sector_summary(
        self,
        *,
        display_code: str,
        sector_code: str,
        free_spots: int,
        arrow_direction: str,
        parking_symbol: str,
        display_text: str,
        message: str,
        device_code: str | None = None,
        device_host: str | None = None,
        device_port: int | None = None,
        device_protocol: str | None = None,
    ) -> None:
        if not device_host or device_port is None:
            raise ValueError("HTTP LED adapter requires led device host and port.")

        scheme = self._scheme_from_protocol(device_protocol)
        payload: dict[str, Any] = {
            "display_code": display_code,
            "sector_code": sector_code,
            "free_spots": free_spots,
            "arrow_direction": arrow_direction,
            "parking_symbol": parking_symbol,
            "display_text": display_text,
            "message": message,
            "device_code": device_code,
        }
        url = f"{scheme}://{device_host}:{device_port}{self.path}"

        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

    @staticmethod
    def _scheme_from_protocol(device_protocol: str | None) -> str:
        protocol = (device_protocol or "HTTP").upper()
        if protocol == "HTTP":
            return "http"
        if protocol == "HTTPS":
            return "https"
        raise ValueError(
            "HTTP LED adapter requires device protocol HTTP or HTTPS, "
            f"got {protocol}."
        )
