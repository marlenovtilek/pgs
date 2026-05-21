from typing import Protocol


class EventBusPort(Protocol):
    async def publish(self, topic: str, payload: dict) -> None:
        """Publish a normalized event to the external event bus."""
