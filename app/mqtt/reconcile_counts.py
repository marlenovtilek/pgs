import argparse
import asyncio

from app.adapters.event_bus.mqtt import AsyncMqttSubscriber, MqttMessage, default_client_id
from app.contracts.mqtt_topics import TOTAL_FREE_TOPIC, ZONE_FREE_TOPIC
from app.core.async_database import AsyncSessionLocal
from app.core.config import settings
from app.services.mqtt_reconciliation import (
    is_total_free_topic,
    reconcile_total_free_event_async,
    reconcile_zone_free_event_async,
    zone_id_from_topic,
)


async def handle_message(message: MqttMessage) -> None:
    if not isinstance(message.payload, dict):
        print(f"ignored non-json topic={message.topic} payload={message.raw_payload}")
        return

    async with AsyncSessionLocal() as db:
        try:
            if zone_id_from_topic(message.topic) is not None:
                result = await reconcile_zone_free_event_async(
                    db,
                    topic=message.topic,
                    payload=message.payload,
                )
                if result.pgs_free_spots is None:
                    print(
                        "zone_missing "
                        f"zone={result.zone_code} "
                        f"mqtt_free={result.mqtt_free_spots}"
                    )
                    return

                print(
                    "zone "
                    f"zone={result.zone_code} "
                    f"mqtt_free={result.mqtt_free_spots} "
                    f"pgs_free={result.pgs_free_spots} "
                    f"diff={result.diff} "
                    f"total={result.total_spots} "
                    f"occupied={result.occupied_spots} "
                    f"unknown={result.unknown_spots} "
                    f"offline={result.offline_spots}"
                )
                return

            if is_total_free_topic(message.topic):
                result = await reconcile_total_free_event_async(
                    db,
                    payload=message.payload,
                )
                print(
                    "total "
                    f"mqtt_free={result.mqtt_free_spots} "
                    f"pgs_free={result.pgs_free_spots} "
                    f"diff={result.diff}"
                )
                return

        except ValueError as exc:
            print(f"invalid topic={message.topic} error={exc}")

    print(f"ignored topic={message.topic}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare MQTT free counters with PGS-calculated counters."
    )
    parser.add_argument("--host", default=settings.mqtt_host)
    parser.add_argument("--port", type=int, default=settings.mqtt_port)
    parser.add_argument("--client-id", default=default_client_id("pgs-mqtt-reconcile"))
    return parser.parse_args()


def main() -> None:
    asyncio.run(main_async())


async def main_async() -> None:
    args = parse_args()
    async with AsyncMqttSubscriber(
        host=args.host,
        port=args.port,
        topics=(ZONE_FREE_TOPIC, TOTAL_FREE_TOPIC),
        client_id=args.client_id,
        keepalive=settings.mqtt_keepalive,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
    ) as subscriber:
        async for message in subscriber.messages():
            await handle_message(message)


if __name__ == "__main__":
    main()
