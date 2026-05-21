# ТЗ — SmartParking: PGS + UNV модули

**Тип:** Микросервисная архитектура, отдельно от основного Django проекта  
**Масштаб:** ~1800 мест, крытый паркинг  
**Дата:** 2026-05-19  
**Статус:** Проектирование

---

## 1. Контекст и цели

### Что есть сейчас
Основной проект SmartParking (Django) управляет сессиями, оплатой, барьерами через Dahua/Hikvision камеры на въезде/выезде.

### Что добавляем
Два независимых микросервиса поверх существующего MQTT брокера (EMQX):

| Сервис | Задача |
|---|---|
| `unv-service` | Получает события с UNV камер (статус мест + номера), публикует в MQTT |
| `led-service` | Слушает MQTT, управляет LED экранами (стрелки + табло) |

### Цели
1. Водитель видит стрелку куда ехать (свободные места в зоне)
2. На въезде — табло с общим количеством свободных мест
3. UNV камеры отслеживают статус 1800 мест (≈300 камер по 6 мест)
4. Номера машин на местах пишутся в MQTT (для будущей интеграции)

---

## 2. Scope

### Входит
- `unv-service`: подключение к UNV SDK, парсинг событий, публикация в MQTT
- `led-service`: подписка на MQTT, логика стрелок, управление LED
- MQTT-контракт между сервисами
- Docker Compose для обоих сервисов

### НЕ входит (пока)
- Интеграция с Django сессиями
- Оплата/барьеры
- Авторизация водителей по номеру на месте
- UI панель управления

---

## 3. Домен

### Сущности

```python
# Зона — логическая группа мест (ряд, этаж, секция)
@dataclass
class ParkingZone:
    id: str            # "A1", "B3", "floor_2"
    total_spots: int
    free_spots: int
    led_screen_id: str  # какой LED экран показывает эту зону

# Место
@dataclass  
class ParkingSpot:
    id: str              # "A1-001"
    zone_id: str
    status: SpotStatus   # FREE | OCCUPIED
    camera_id: str       # какая камера смотрит
    plate: str | None    # номер если есть

# Событие с камеры
@dataclass
class SpotEvent:
    camera_id: str
    spot_id: str
    status: SpotStatus
    plate: str | None
    confidence: float
    timestamp: datetime

# Команда LED экрану
@dataclass
class DisplayCommand:
    screen_id: str
    arrow: ArrowDirection   # LEFT | RIGHT | AHEAD | FULL
    free_count: int
    zone_id: str
```

### Value Objects

```python
class SpotStatus(Enum):
    FREE = "free"
    OCCUPIED = "occupied"

class ArrowDirection(Enum):
    LEFT = "left"
    RIGHT = "right"
    AHEAD = "ahead"
    FULL = "full"   # нет мест
```

---

## 4. Архитектура

### Паттерн: Hexagonal Architecture (Ports & Adapters)

Домен не зависит от инфраструктуры. Все внешние зависимости — через интерфейсы (порты).

```
┌─────────────────────────────────────────────┐
│              unv-service                     │
│  ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │UNV SDK   │───▶│ Domain   │───▶│ MQTT   │ │
│  │(Adapter) │    │(Use Case)│    │(Port)  │ │
│  └──────────┘    └──────────┘    └────────┘ │
└─────────────────────────────────────────────┘
                        │ MQTT
┌─────────────────────────────────────────────┐
│              led-service                     │
│  ┌────────┐    ┌──────────┐    ┌──────────┐ │
│  │ MQTT   │───▶│ Domain   │───▶│LED Driver│ │
│  │(Port)  │    │(Use Case)│    │(Adapter) │ │
│  └────────┘    └──────────┘    └──────────┘ │
│                     │                        │
│               ┌─────┴─────┐                 │
│               │   Redis   │                  │
│               │(SpotState)│                  │
│               └───────────┘                 │
└─────────────────────────────────────────────┘
```

### Паттерны

| Паттерн | Где применяется |
|---|---|
| **Hexagonal (Ports & Adapters)** | Общая архитектура обоих сервисов |
| **Strategy** | Разные типы LED (Dahua CGI / TCP / WebSocket) |
| **Adapter** | UNV SDK → общий SpotEvent формат |
| **Observer** | MQTT pub/sub между сервисами |
| **Repository** | Redis хранит состояние мест и зон |
| **Factory** | Создание LED driver по конфигу |
| **Command** | DisplayCommand — объект команды LED |

---

## 5. UNV Service

### Структура
```
unv-service/
├── domain/
│   ├── entities.py          # SpotEvent, ParkingSpot
│   ├── ports.py             # ICameraPort, IEventBus, ISpotRepository
│   └── use_cases.py         # ProcessSpotEventUseCase
├── adapters/
│   ├── unv_sdk_adapter.py   # UNV SDK → ICameraPort
│   ├── onvif_adapter.py     # ONVIF fallback → ICameraPort
│   ├── mqtt_publisher.py    # IEventBus через paho-mqtt
│   └── redis_repository.py  # ISpotRepository через Redis
├── config.py                # pydantic-settings
├── main.py                  # точка входа
└── Dockerfile
```

### Порты (интерфейсы)

```python
# domain/ports.py
from abc import ABC, abstractmethod

class ICameraPort(ABC):
    @abstractmethod
    async def subscribe(self, callback: Callable[[SpotEvent], None]) -> None:
        """Подписаться на события камеры"""

class IEventBus(ABC):
    @abstractmethod
    async def publish(self, topic: str, payload: dict) -> None:
        """Опубликовать событие"""

class ISpotRepository(ABC):
    @abstractmethod
    async def save_spot(self, spot: ParkingSpot) -> None: ...
    
    @abstractmethod
    async def get_zone_free_count(self, zone_id: str) -> int: ...
```

### Use Case

```python
# domain/use_cases.py
class ProcessSpotEventUseCase:
    def __init__(self, repo: ISpotRepository, event_bus: IEventBus):
        self._repo = repo
        self._bus = event_bus

    async def execute(self, event: SpotEvent) -> None:
        spot = ParkingSpot(
            id=event.spot_id,
            zone_id=self._resolve_zone(event.camera_id),
            status=event.status,
            camera_id=event.camera_id,
            plate=event.plate,
        )
        await self._repo.save_spot(spot)
        free = await self._repo.get_zone_free_count(spot.zone_id)

        await self._bus.publish(
            topic=f"parking/zones/{spot.zone_id}/status",
            payload={"zone_id": spot.zone_id, "free_spots": free},
        )
```

### UNV SDK Adapter

```python
# adapters/unv_sdk_adapter.py
class UNVSdkAdapter(ICameraPort):
    """
    UNV OpenNetSDK (C библиотека через ctypes/cffi)
    Или HTTP callback если камера поддерживает push
    """
    def __init__(self, cameras: list[UNVCameraConfig]):
        self._cameras = cameras

    async def subscribe(self, callback):
        for cam in self._cameras:
            # UNV SDK вызывает callback при DetectRegion событии
            sdk.register_callback(cam.ip, cam.channel, self._on_event(callback))

    def _on_event(self, callback):
        def handler(raw_event):
            events = self._parse(raw_event)
            for e in events:
                asyncio.create_task(callback(e))
        return handler

    def _parse(self, raw) -> list[SpotEvent]:
        # Парсим 6 зон из одного события камеры
        return [
            SpotEvent(
                camera_id=raw["camera_id"],
                spot_id=f"{raw['camera_id']}-{region['id']}",
                status=SpotStatus.FREE if region["status"] == 0 else SpotStatus.OCCUPIED,
                plate=region.get("plate"),
                confidence=region.get("confidence", 1.0),
                timestamp=datetime.utcnow(),
            )
            for region in raw["regions"]  # до 6 регионов
        ]
```

---

## 6. LED Service

### Структура
```
led-service/
├── domain/
│   ├── entities.py          # DisplayCommand, ParkingZone
│   ├── ports.py             # IDisplayPort, IZoneRepository, IEventBus
│   ├── use_cases.py         # CalculateArrowUseCase, SendCommandUseCase
│   └── arrow_calculator.py  # чистая логика стрелок
├── adapters/
│   ├── mqtt_subscriber.py   # слушает зоны
│   ├── redis_repository.py  # состояние зон
│   ├── display/
│   │   ├── factory.py           # создаёт нужный driver по конфигу
│   │   ├── dahua_display.py     # Strategy: Dahua CGI API
│   │   ├── tcp_display.py       # Strategy: TCP socket (китайские)
│   │   └── websocket_display.py # Strategy: TV/планшет
├── config.py
├── main.py
└── Dockerfile
```

### Strategy — LED Driver

```python
# domain/ports.py
class IDisplayPort(ABC):
    @abstractmethod
    async def send(self, command: DisplayCommand) -> None: ...

# adapters/display/factory.py — Factory Pattern
class DisplayFactory:
    _drivers = {
        "dahua": DahuaDisplayAdapter,
        "tcp":   TCPDisplayAdapter,
        "ws":    WebSocketDisplayAdapter,
    }

    @classmethod
    def create(cls, config: DisplayConfig) -> IDisplayPort:
        driver_cls = cls._drivers.get(config.type)
        if not driver_cls:
            raise ValueError(f"Unknown display type: {config.type}")
        return driver_cls(config)
```

### Arrow Calculator

```python
# domain/arrow_calculator.py — чистая функция, без зависимостей
def calculate_arrow(
    current_zone: str,
    adjacent_zones: dict[str, int],  # zone_id → free_count
) -> ArrowDirection:
    """
    Определяет куда показывать стрелку на развилке.
    adjacent_zones: {"left": 0, "right": 45, "ahead": 12}
    """
    if not any(adjacent_zones.values()):
        return ArrowDirection.FULL

    best = max(adjacent_zones, key=adjacent_zones.get)
    return ArrowDirection[best.upper()]
```

### Use Cases

```python
class CalculateAndSendUseCase:
    def __init__(self, zone_repo: IZoneRepository,
                 display_factory: DisplayFactory,
                 displays: list[DisplayConfig]):
        self._repo = zone_repo
        self._factory = display_factory
        self._displays = {d.screen_id: display_factory.create(d) for d in displays}

    async def execute(self, zone_id: str) -> None:
        zone = await self._repo.get_zone(zone_id)
        adjacent = await self._repo.get_adjacent_zones(zone_id)

        arrow = calculate_arrow(zone_id, {k: v.free_spots for k, v in adjacent.items()})

        cmd = DisplayCommand(
            screen_id=zone.led_screen_id,
            arrow=arrow,
            free_count=zone.free_spots,
            zone_id=zone_id,
        )
        display = self._displays[zone.led_screen_id]
        await display.send(cmd)
```

---

## 7. MQTT Контракт

### Топики

```
# unv-service публикует:
parking/zones/{zone_id}/status          # статус зоны
parking/spots/{spot_id}/status          # статус конкретного места
parking/spots/{spot_id}/plate           # номер на месте

# led-service слушает:
parking/zones/{zone_id}/status
parking/total/free                      # общий счётчик (для табло на въезде)

# led-service публикует:
parking/led/{screen_id}/command         # команда экрану (для мониторинга)
```

### Схемы payload (Pydantic)

```python
class ZoneStatusPayload(BaseModel):
    zone_id: str
    free_spots: int
    total_spots: int
    timestamp: datetime

class SpotPlatePayload(BaseModel):
    spot_id: str
    zone_id: str
    plate: str
    confidence: float
    timestamp: datetime

class LEDCommandPayload(BaseModel):
    screen_id: str
    arrow: ArrowDirection
    free_count: int
    zone_id: str
```

---

## 8. Технологический стек

| Слой | Технология | Причина |
|---|---|---|
| Фреймворк | **FastAPI** | Async, легковесный, не Django overhead |
| Валидация | **Pydantic v2** | Схемы MQTT payload, конфиги |
| MQTT | **paho-mqtt** или **aiomqtt** | aiomqtt для async |
| Кэш/состояние | **Redis** | Быстрое хранение 1800 статусов мест |
| UNV камера | **UNV OpenNetSDK** (ctypes) или **ONVIF** (onvif-zeep) | SDK если есть, ONVIF как fallback |
| LED Dahua | **requests + HTTPDigestAuth** | Уже используется в проекте |
| Конфиг | **pydantic-settings** + `.env` | Типизированный конфиг |
| Деплой | **Docker + docker-compose** | Изолированные контейнеры |
| Брокер | **EMQX** (уже есть) | Уже в docker-compose проекта |

### Зависимости (requirements.txt)

```
fastapi>=0.115
uvicorn[standard]
pydantic>=2.0
pydantic-settings
aiomqtt
redis[asyncio]
onvif-zeep          # если нет UNV SDK
requests
httpx
```

---

## 9. Docker Compose

```yaml
# добавить в существующий docker-compose.yml или отдельный файл

services:
  unv-service:
    build: ./unv-service
    environment:
      - MQTT_BROKER=emqx
      - REDIS_URL=redis://redis:6379
      - UNV_CAMERAS_CONFIG=/config/cameras.json
    volumes:
      - ./config:/config
    depends_on: [emqx, redis]
    restart: unless-stopped

  led-service:
    build: ./led-service
    environment:
      - MQTT_BROKER=emqx
      - REDIS_URL=redis://redis:6379
      - LED_SCREENS_CONFIG=/config/screens.json
    volumes:
      - ./config:/config
    depends_on: [emqx, redis]
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
```

---

## 10. Конфигурация (config файлы)

```json
// config/cameras.json — каждая UNV камера + её места
[
  {
    "id": "cam_A1_001",
    "ip": "192.168.1.101",
    "zone_id": "A1",
    "spots": ["A1-001", "A1-002", "A1-003", "A1-004", "A1-005", "A1-006"]
  }
]

// config/screens.json — LED экраны
[
  {
    "screen_id": "led_entry_main",
    "type": "dahua",
    "ip": "192.168.1.200",
    "zone_coverage": ["A1", "A2", "B1"]
  },
  {
    "screen_id": "led_row_A",
    "type": "tcp",
    "ip": "192.168.1.201",
    "port": 5005,
    "zone_coverage": ["A1", "A2"]
  }
]
```

---

## 11. Нефункциональные требования

| Требование | Значение |
|---|---|
| Задержка обновления LED | < 2 сек после события камеры |
| Uptime | 99.5% (restart: unless-stopped) |
| Масштаб | 1800 мест, ~300 камер |
| Потеря событий | Допустимо (MQTT QoS 0), не критично |
| Хранение состояния | Redis TTL 24h, пересчёт при рестарте |

---

## 12. Открытые вопросы

### UNV камера
- [ ] Точная модель (нужен datasheet)
- [ ] Протокол: push callback или pull polling?
- [ ] Тестовый доступ к камере

### LED экраны
- [ ] Марка и модель физических экранов
- [ ] Протокол: Dahua / TCP / другой?
- [ ] Сколько экранов: на въезде + сколько внутри?
- [ ] Нужен ли WebSocket экран (TV/планшет) как временное решение?

### Зоны
- [ ] Схема 1800 мест: сколько зон, как называются?
- [ ] Какие LED на каких развилках?


---
 
*Создано: 2026-05-19*
