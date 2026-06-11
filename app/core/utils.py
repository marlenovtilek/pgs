"""Небольшие кросс-каттинг хелперы, общие для всего приложения.

Держать файл маленьким и генеричным: доменная логика живёт в своём сервисе,
а не здесь. Сюда попадают только по-настоящему переиспользуемые функции,
которым нет лучшего места.
"""
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Текущее время в UTC с таймзоной.

    Единый источник правды, чтобы все временные метки, которые мы ставим
    в Python-коде, были timezone-aware (а не наивными datetime).
    """
    return datetime.now(timezone.utc)


def parse_comma_set(raw: str | None) -> frozenset[str]:
    """Разобрать строку через запятую в множество непустых значений без пробелов.

    Используется для env-списков (например, DISABLED_SPOT_CODES).
    Для None/пустой строки возвращает пустой frozenset.
    """
    if not raw:
        return frozenset()
    return frozenset(item.strip() for item in raw.split(",") if item.strip())
