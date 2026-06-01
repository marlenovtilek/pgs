from app.adapters.event_bus.mqtt import decode_payload
from app.contracts.mqtt_topics import MQTT_SUBSCRIBE_TOPICS


def test_decode_payload_parses_json():
    payload, raw_payload = decode_payload(b'{"status":"OCCUPIED"}')

    assert payload == {"status": "OCCUPIED"}
    assert raw_payload == '{"status":"OCCUPIED"}'


def test_decode_payload_keeps_plain_text():
    payload, raw_payload = decode_payload(b"online")

    assert payload == "online"
    assert raw_payload == "online"


def test_mqtt_subscribe_topics_match_camera_contract():
    assert MQTT_SUBSCRIBE_TOPICS == (
        "parking/cameras/+/health",
        "parking/spots/+/status",
        "parking/zones/+/free",
        "parking/total/free",
    )
