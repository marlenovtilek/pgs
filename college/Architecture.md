# SmartParking PGS — Архитектура

**Связано с:** [[Tech Stack]] |  [[Claude Notes]]
**Дата:** 2026-05-19
**Статус:** Проектирование

---

## Принцип

Два независимых микросервиса поверх существующего проекта.
Основной Django проект не трогаем — только добавляем новые сервисы рядом.
Симуляция и прод используют **одинаковую архитектуру** — меняется только конфиг.

---

## Общая картина системы

```mermaid
flowchart TD
    CAR([🚗 Машина])

    subgraph EXISTING["Существующий проект (Django)"]
        ANPR[ANPR камера\nвъезд/выезд]
        BARRIER[Шлагбаум]
        SESSION[Сессия создана]
        ANPR --> BARRIER --> SESSION
    end

    subgraph NEW["Новые микросервисы"]
        UNV[unv-service]
        LED[led-service]
        REDIS[(Redis\nсостояние мест)]
        UNV <--> REDIS
        LED <--> REDIS
    end

    subgraph HW["Оборудование"]
        CAM[UNV Камеры\n~300 штук\n6 мест каждая]
        ARROWS[LED Стрелки\nна развилках]
        BOARD[Табло на въезде\nСвободно: 1799]
    end

    EMQX{{EMQX\nMQTT Broker}}

    CAR --> EXISTING
    SESSION -->|MQTT: session/created| EMQX
    CAM -->|SDK события| UNV
    UNV -->|MQTT: zones/status| EMQX
    EMQX -->|подписка| LED
    LED --> ARROWS
    LED --> BOARD
```

---

## Слои архитектуры — Hexagonal

```mermaid
flowchart LR
    subgraph SVC["Каждый микросервис"]
        direction TB
        subgraph DOMAIN["Domain (ядро)"]
            E[Entities]
            P[Ports - интерфейсы]
            UC[Use Cases]
        end
        subgraph ADAPTERS["Adapters"]
            IN[Входящие\nMQTT / SDK]
            OUT[Исходящие\nRedis / MQTT / LED]
        end
        subgraph INFRA["Infrastructure"]
            FW[FastAPI\nhealth endpoint]
            CFG[Config\n.env]
        end
    end

    IN -->|через Port| UC
    UC -->|через Port| OUT
    INFRA -.->|собирает| DOMAIN
    INFRA -.->|собирает| ADAPTERS
```

**Правило:** Domain не знает ни про FastAPI, ни про Redis, ни про MQTT.
Всё внешнее — через интерфейсы (Ports). Это позволяет менять mock на реальное без изменения бизнес-логики.

---

## Сценарий 1 — Машина въезжает и паркуется

```mermaid
sequenceDiagram
    actor Driver as 🚗 Водитель
    participant Django as Django\n(существующий)
    participant EMQX as EMQX Broker
    participant LED as led-service
    participant Screen as LED Стрелки
    participant UNV as UNV Камера
    participant UNVSvc as unv-service
    participant Redis as Redis
    participant Board as Табло

    Driver->>Django: подъехал к шлагбауму
    Django->>Django: открыл шлагбаум\nсоздал сессию
    Django->>EMQX: parking/session/created
    EMQX->>LED: доставил событие
    LED->>Redis: запросил свободные по зонам
    Redis-->>LED: A→44, B→12, C→8
    LED->>Screen: показать ← 44 | → 12 | ↑ 8

    Driver->>Driver: едет по стрелкам\nпаркуется в зоне A

    UNV->>UNVSvc: место A-003 занято (SDK событие)
    UNVSvc->>Redis: zone:A:free = 43\nspot:A-003 = occupied
    UNVSvc->>EMQX: parking/zones/A/status\nparking/total/free
    EMQX->>LED: доставил статус
    LED->>Screen: обновить ← 43 | → 12 | ↑ 8
    LED->>Board: Свободно: 1799
```

---

## Сценарий 2 — Зона заполнена

```mermaid
sequenceDiagram
    participant UNVSvc as unv-service
    participant EMQX as EMQX Broker
    participant LED as led-service
    participant Screen as LED Экран зоны A

    UNVSvc->>EMQX: zone A: free=0
    EMQX->>LED: доставил
    LED->>LED: calculate_arrow:\nвсе направления = 0
    LED->>Screen: показать ЗАНЯТО 🔴
```

---

## Сценарий 3 — Камера отключилась

```mermaid
sequenceDiagram
    participant UNV as UNV Камера
    participant UNVSvc as unv-service
    participant Redis as Redis
    participant EMQX as EMQX Broker
    participant LED as led-service
    participant Screen as LED Экран

    UNV->>UNV: офлайн
    Note over UNVSvc: нет heartbeat 60 сек
    UNVSvc->>Redis: camera:cam_001 TTL истёк
    UNVSvc->>EMQX: parking/cameras/cam_001/health\nstatus=offline
    EMQX->>LED: алерт
    Note over LED: места этой камеры\nостаются в последнем\nизвестном состоянии
    Note over Screen: LED не меняется\nпоказывает последнее значение
```

---

## Сценарий 4 — Рестарт сервиса

```mermaid
flowchart TD
    START([Сервис стартует])
    REDIS[Подключиться к Redis]
    LOAD[Загрузить текущее состояние\nвсех зон из Redis]
    MQTT[Подключиться к EMQX]
    SUB[Подписаться на топики]
    RESTORE[Отправить команды LED\nвосстановить актуальное отображение]
    READY([Сервис готов])

    START --> REDIS --> LOAD --> MQTT --> SUB --> RESTORE --> READY
```

Redis сохраняет состояние между рестартами.
Сервис восстанавливает картину без ожидания новых событий с камер.

---

## Сценарий 5 — Переход с симуляции на прод

```mermaid
flowchart LR
    subgraph SIM["Симуляция (сейчас)"]
        M1[mock_unv\nскрипт меняет места]
        M2[mock_led\nлогирует + дашборд]
    end

    subgraph SAME["Одинаково в обоих режимах"]
        UC[Use Cases]
        REDIS[(Redis)]
        EMQX{{EMQX}}
    end

    subgraph PROD["Прод (позже)"]
        P1[UNV SDK\nреальные камеры]
        P2[Dahua/TCP\nреальные LED]
    end

    ENV[.env\nCAMERA_DRIVER=mock\nLED_DRIVER=mock]
    ENV2[.env\nCAMERA_DRIVER=unv_sdk\nLED_DRIVER=dahua]

    SIM -->|через Port| SAME
    PROD -->|через Port| SAME
    ENV -.->|выбирает| SIM
    ENV2 -.->|выбирает| PROD
```

---

## Структура репозитория

```
smartparking-pgs/
│
├── unv-service/
│   ├── domain/          ← бизнес-логика, без зависимостей
│   ├── adapters/
│   │   ├── camera/      ← unv_sdk | onvif | mock
│   │   ├── mqtt/        ← publisher
│   │   └── redis/       ← repository
│   ├── config.py
│   └── main.py          ← FastAPI app + DI сборка
│
├── led-service/
│   ├── domain/          ← логика стрелок, без зависимостей
│   ├── adapters/
│   │   ├── display/     ← dahua | tcp | websocket | mock
│   │   ├── mqtt/        ← subscriber
│   │   └── redis/       ← repository
│   ├── config.py
│   └── main.py
│
├── simulator/           ← имитация оборудования
│   ├── mock_unv        ← имитирует UNV камеры
│   ├── mock_session    ← имитирует Django сессии
│   └── dashboard       ← веб-визуализация LED и мест
│
├── config/
│   ├── zones.json       ← карта зон и смежностей
│   ├── cameras.json     ← какая камера какие места
│   └── screens.json     ← какой LED на какой зоне
│
└── docker-compose.yml
```

---

## Redis — схема ключей

```
zone:{id}:free      → количество свободных (атомарный счётчик)
zone:{id}:total     → общее количество
zone:{id}:left      → смежная зона слева
zone:{id}:right     → смежная зона справа
zone:{id}:ahead     → смежная зона прямо
zone:{id}:screen    → id LED экрана этой зоны

spot:{id}:status    → free | occupied
spot:{id}:plate     → номер машины
spot:{id}:ts        → время последнего изменения

parking:total:free  → глобальный счётчик (для табло)
parking:total:total → 1800

camera:{id}:alive   → 1 (TTL 60 сек, истекает = камера offline)
```

---

*[[Tech Stack]] — технологии и почему*
*[[Simulation]] — как устроена симуляция*
*[[Claude Notes]] — заметки для будущих сессий*
