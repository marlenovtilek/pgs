import argparse
import json

from app.adapters.event_bus.mqtt import MqttMessage, MqttSubscriber, default_client_id
from app.contracts.mqtt_topics import MQTT_SUBSCRIBE_TOPICS
from app.core.config import settings


def print_message(message: MqttMessage) -> None:
    if isinstance(message.payload, (dict, list)):
        payload = json.dumps(message.payload, ensure_ascii=False, indent=2)
    else:
        payload = message.raw_payload

    print("-" * 80)
    print(f"received_at: {message.received_at.isoformat()}")
    print(f"topic: {message.topic}")
    print("payload:")
    print(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Listen to PGS MQTT topics and print incoming events."
    )
    parser.add_argument("--host", default=settings.mqtt_host)
    parser.add_argument("--port", type=int, default=settings.mqtt_port)
    parser.add_argument("--client-id", default=default_client_id(settings.mqtt_client_id))
    parser.add_argument("--topic", action="append", dest="topics")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    topics = tuple(args.topics) if args.topics else MQTT_SUBSCRIBE_TOPICS

    subscriber = MqttSubscriber(
        host=args.host,
        port=args.port,
        topics=topics,
        on_message=print_message,
        client_id=args.client_id,
        keepalive=settings.mqtt_keepalive,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
    )
    subscriber.loop_forever()


if __name__ == "__main__":
    main()
