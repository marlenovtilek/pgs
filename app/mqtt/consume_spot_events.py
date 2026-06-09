import argparse
import asyncio
import logging

from sqlalchemy.exc import IntegrityError

from app.adapters.event_bus.mqtt import AsyncMqttSubscriber, MqttMessage, default_client_id
from app.adapters.led.factory import get_led_display_adapter
from app.contracts.mqtt_topics import SPOT_STATUS_TOPIC
from app.core.async_database import AsyncSessionLocal
from app.core.config import settings
from app.services.mqtt_spot_events import (
    build_spot_event_request_from_mqtt,
    ensure_mqtt_parking_config_async,
)
from app.services.spot_events import AmbiguousSpotCodeError, process_spot_event_async


logger = logging.getLogger(__name__)


async def handle_message(
    message: MqttMessage,
    *,
    auto_create: bool = False,
    auto_create_floor_sector: bool = False,
) -> None:
    if not isinstance(message.payload, dict):
        logger.warning(
            "ignored non-json topic=%s payload=%s",
            message.topic,
            message.raw_payload,
        )
        return

    try:
        request = build_spot_event_request_from_mqtt(
            topic=message.topic,
            payload=message.payload,
        )
    except ValueError as exc:
        logger.warning("invalid topic=%s error=%s", message.topic, exc)
        return

    async with AsyncSessionLocal() as db:
        if auto_create:
            try:
                created = await ensure_mqtt_parking_config_async(
                    db,
                    request,
                    create_missing_floor_sector=auto_create_floor_sector,
                )
            except ValueError as exc:
                logger.warning(
                    "auto_create_failed spot_code=%s error=%s", request.spot_code, exc
                )
                return
            except IntegrityError as exc:
                await db.rollback()
                logger.warning(
                    "auto_create_conflict spot_code=%s error=%s", request.spot_code, exc
                )
                return
            if created:
                logger.info(
                    "auto_created spot_code=%s sector_code=%s",
                    request.spot_code,
                    request.sector_code,
                )

        try:
            result = await process_spot_event_async(
                db,
                request,
                display_port=get_led_display_adapter(),
            )
        except LookupError:
            logger.warning(
                "not_found spot_code=%s sector_code=%s status=%s",
                request.spot_code,
                request.sector_code,
                request.status.value,
            )
            return
        except AmbiguousSpotCodeError as exc:
            logger.warning(
                "ambiguous spot_code=%s sector_code=%s",
                exc.spot_code,
                request.sector_code,
            )
            return

    logger.info(
        "processed spot_code=%s status=%s led_commands=%s duplicate=%s",
        result.response.spot_code,
        result.response.status,
        result.led_commands_sent,
        result.is_duplicate,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume MQTT spot status events and apply them to PGS."
    )
    parser.add_argument("--host", default=settings.mqtt_host)
    parser.add_argument("--port", type=int, default=settings.mqtt_port)
    parser.add_argument("--client-id", default=default_client_id("pgs-mqtt-spot-consumer"))
    parser.add_argument(
        "--auto-create",
        action="store_true",
        help="Create missing camera zones and spots for sectors that already exist in PGS.",
    )
    parser.add_argument(
        "--auto-create-floor-sector",
        action="store_true",
        help="Also create missing floors and sectors from valid MQTT spot codes.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(main_async())


async def main_async() -> None:
    args = parse_args()
    while True:
        try:
            async with AsyncMqttSubscriber(
                host=args.host,
                port=args.port,
                topics=(SPOT_STATUS_TOPIC,),
                client_id=args.client_id,
                keepalive=settings.mqtt_keepalive,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
            ) as subscriber:
                async for message in subscriber.messages():
                    await handle_message(
                        message,
                        auto_create=args.auto_create,
                        auto_create_floor_sector=args.auto_create_floor_sector,
                    )
        except OSError as exc:
            logger.warning(
                "mqtt_connection_unavailable host=%s port=%s error=%s retrying_in=5s",
                args.host,
                args.port,
                exc,
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    main()
