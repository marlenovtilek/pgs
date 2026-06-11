from __future__ import annotations

import asyncio
import json
import os
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt

from app.core.utils import now_utc


@dataclass(slots=True)
class MqttMessage:
    topic: str
    payload: Any
    raw_payload: str
    received_at: datetime


def decode_payload(raw_payload: bytes) -> tuple[Any, str]:
    text = raw_payload.decode("utf-8", errors="replace")
    try:
        return json.loads(text), text
    except json.JSONDecodeError:
        return text, text


def default_client_id(prefix: str) -> str:
    hostname = socket.gethostname()
    return f"{prefix}-{hostname}-{os.getpid()}"


class MqttSubscriber:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        topics: Iterable[str],
        on_message: Callable[[MqttMessage], None],
        client_id: str,
        keepalive: int = 60,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.topics = tuple(topics)
        self.keepalive = keepalive
        self.on_message = on_message

        self.client = self._create_client(client_id=client_id)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        if username is not None:
            self.client.username_pw_set(username, password=password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _create_client(self, *, client_id: str):
        if hasattr(mqtt, "CallbackAPIVersion"):
            return mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
            )
        return mqtt.Client(client_id=client_id)

    def connect(self) -> None:
        self.client.connect(self.host, self.port, self.keepalive)

    def loop_forever(self) -> None:
        self.connect()
        self.client.loop_forever()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if not _is_success_reason_code(reason_code):
            print(f"MQTT connect failed: {reason_code}")
            return

        print(f"MQTT connected: {self.host}:{self.port}")
        for topic in self.topics:
            client.subscribe(topic)
            print(f"MQTT subscribed: {topic}")

    def _on_disconnect(self, client, userdata, *args) -> None:
        reason_code = args[-2] if len(args) >= 2 else args[-1] if args else "unknown"
        print(f"MQTT disconnected: {reason_code}")

    def _on_message(self, client, userdata, message) -> None:
        payload, raw_payload = decode_payload(message.payload)
        self.on_message(
            MqttMessage(
                topic=message.topic,
                payload=payload,
                raw_payload=raw_payload,
                received_at=now_utc(),
            )
        )


class AsyncMqttSubscriber:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        topics: Iterable[str],
        client_id: str,
        keepalive: int = 60,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.loop = asyncio.get_running_loop()
        self.queue: asyncio.Queue[MqttMessage] = asyncio.Queue()
        self.subscriber = MqttSubscriber(
            host=host,
            port=port,
            topics=topics,
            on_message=self._enqueue_message,
            client_id=client_id,
            keepalive=keepalive,
            username=username,
            password=password,
        )

    def _enqueue_message(self, message: MqttMessage) -> None:
        self.loop.call_soon_threadsafe(self.queue.put_nowait, message)

    async def __aenter__(self) -> "AsyncMqttSubscriber":
        self.subscriber.connect()
        self.subscriber.client.loop_start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.subscriber.client.disconnect()
        self.subscriber.client.loop_stop()

    async def messages(self):
        while True:
            yield await self.queue.get()


def _is_success_reason_code(reason_code) -> bool:
    if reason_code == 0:
        return True
    return str(reason_code) == "Success"
