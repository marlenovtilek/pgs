"""Prometheus metrics for PGS.

Counters are module-level singletons registered on the default registry, so
importing this module from any process (API or MQTT consumer) shares the same
metric definitions. Each process exposes its own values:
  - the API serves them at ``GET /metrics``;
  - the MQTT consumer starts a small HTTP server (see consume_spot_events).
"""
from prometheus_client import Counter

# LED display command outcomes (status: "sent" | "failed").
LED_COMMANDS = Counter(
    "pgs_led_commands_total",
    "LED display commands attempted, labelled by outcome.",
    ["status"],
)

# MQTT spot events handled by the consumer, labelled by result, e.g.
# "processed", "duplicate", "invalid", "ignored", "not_found", "ambiguous",
# "auto_create_failed", "auto_create_conflict".
SPOT_EVENTS = Counter(
    "pgs_spot_events_total",
    "MQTT spot events handled, labelled by result.",
    ["result"],
)
