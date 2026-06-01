import argparse

from app.adapters.event_bus.mqtt import MqttMessage, MqttSubscriber
from app.adapters.led.mock import mock_led_adapter
from app.contracts.mqtt_topics import SPOT_STATUS_TOPIC
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.mqtt_spot_events import (
    build_spot_event_request_from_mqtt,
    ensure_mqtt_parking_config,
)
from app.services.spot_events import AmbiguousSpotCodeError, process_spot_event


def handle_message(message: MqttMessage, *, auto_create: bool = False) -> None:
    if not isinstance(message.payload, dict):
        print(f"ignored non-json topic={message.topic} payload={message.raw_payload}")
        return

    try:
        request = build_spot_event_request_from_mqtt(
            topic=message.topic,
            payload=message.payload,
        )
    except ValueError as exc:
        print(f"invalid topic={message.topic} error={exc}")
        return

    with SessionLocal() as db:
        if auto_create:
            try:
                created = ensure_mqtt_parking_config(db, request)
            except ValueError as exc:
                print(f"auto_create_failed spot_code={request.spot_code} error={exc}")
                return
            if created:
                print(
                    "auto_created "
                    f"spot_code={request.spot_code} "
                    f"zone_code={request.zone_code}"
                )

        try:
            result = process_spot_event(
                db,
                request,
                display_port=mock_led_adapter,
            )
        except LookupError:
            print(
                "not_found "
                f"spot_code={request.spot_code} "
                f"zone_code={request.zone_code} "
                f"status={request.status.value}"
            )
            return
        except AmbiguousSpotCodeError as exc:
            print(
                "ambiguous "
                f"spot_code={exc.spot_code} "
                f"zone_code={request.zone_code}"
            )
            return

    duplicate = " duplicate=true" if result.is_duplicate else ""
    print(
        "processed "
        f"spot_code={result.response.spot_code} "
        f"status={result.response.status} "
        f"led_commands={result.led_commands_sent}"
        f"{duplicate}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume MQTT spot status events and apply them to PGS."
    )
    parser.add_argument("--host", default=settings.mqtt_host)
    parser.add_argument("--port", type=int, default=settings.mqtt_port)
    parser.add_argument("--client-id", default="pgs-mqtt-spot-consumer")
    parser.add_argument(
        "--auto-create",
        action="store_true",
        help="Create missing zone/row/spot/display records from MQTT payloads.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    subscriber = MqttSubscriber(
        host=args.host,
        port=args.port,
        topics=(SPOT_STATUS_TOPIC,),
        on_message=lambda message: handle_message(message, auto_create=args.auto_create),
        client_id=args.client_id,
        keepalive=settings.mqtt_keepalive,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
    )
    subscriber.loop_forever()


if __name__ == "__main__":
    main()
