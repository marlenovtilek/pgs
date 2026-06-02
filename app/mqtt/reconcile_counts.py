import argparse

from app.adapters.event_bus.mqtt import MqttMessage, MqttSubscriber, default_client_id
from app.contracts.mqtt_topics import TOTAL_FREE_TOPIC, ZONE_FREE_TOPIC
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.mqtt_reconciliation import (
    is_total_free_topic,
    reconcile_total_free_event,
    reconcile_zone_free_event,
    zone_id_from_topic,
)


def handle_message(message: MqttMessage) -> None:
    if not isinstance(message.payload, dict):
        print(f"ignored non-json topic={message.topic} payload={message.raw_payload}")
        return

    with SessionLocal() as db:
        try:
            if zone_id_from_topic(message.topic) is not None:
                result = reconcile_zone_free_event(
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
                result = reconcile_total_free_event(db, payload=message.payload)
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
    args = parse_args()
    subscriber = MqttSubscriber(
        host=args.host,
        port=args.port,
        topics=(ZONE_FREE_TOPIC, TOTAL_FREE_TOPIC),
        on_message=handle_message,
        client_id=args.client_id,
        keepalive=settings.mqtt_keepalive,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
    )
    subscriber.loop_forever()


if __name__ == "__main__":
    main()
