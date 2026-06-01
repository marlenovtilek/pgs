CAMERA_HEALTH_TOPIC = "parking/cameras/+/health"
SPOT_STATUS_TOPIC = "parking/spots/+/status"
ZONE_FREE_TOPIC = "parking/zones/+/free"
TOTAL_FREE_TOPIC = "parking/total/free"

MQTT_SUBSCRIBE_TOPICS = (
    CAMERA_HEALTH_TOPIC,
    SPOT_STATUS_TOPIC,
    ZONE_FREE_TOPIC,
    TOTAL_FREE_TOPIC,
)


def spot_status_topic(spot_id: str) -> str:
    return f"parking/spots/{spot_id}/status"


def zone_free_topic(zone_id: str) -> str:
    return f"parking/zones/{zone_id}/free"
