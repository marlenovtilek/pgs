from app.domain.entities.spot_event import SpotEventEntity


def process_spot_event(event: SpotEventEntity) -> SpotEventEntity:
    """Normalize/validate event flow entry-point.

    For now this use case simply returns the event unchanged and acts as
    a stable hook for future deduplication and business rules.
    """

    return event
