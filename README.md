# PGS - Parking Guidance Service

PGS - это микросервис навигации по парковке. Его задача - принимать события о занятости парковочных мест, хранить актуальное состояние парковки, считать количество свободных мест для настроенных LED-табло и формировать команды для отображения.

Сервис не распознает номера, не управляет камерами и не решает задачу компьютерного зрения. Эти задачи выполняет внешний SmartParking/UNV слой. PGS получает уже готовые события через MQTT и превращает их в состояние парковки и команды навигации.

## Коротко

PGS делает следующее:

- принимает MQTT-события по парковочным местам;
- создает этажи, сектора, camera zones и parking spots при приходе валидных MQTT-событий;
- хранит структуру парковки: этажи, сектора, camera zones, места;
- считает свободные/занятые места;
- формирует сообщения для LED-табло;
- показывает текущее состояние в LED simulator;
- предоставляет REST API;
- предоставляет админку для настройки этажей, секторов, мест и табло;
- защищает админку логином/паролем;
- может защищать API через `Bearer API_TOKEN`.

Главный поток:

```text
MQTT event
-> PGS updates ParkingSpot
-> PGS recalculates free spots
-> PGS builds LED display command
-> LED simulator / future real LED adapter
```

## Архитектура

```mermaid
flowchart LR
    SmartParking[SmartParking / UNV events] -->|MQTT| MQTTBroker[MQTT broker / EMQX]
    MQTTBroker -->|parking/spots/+/status| Consumer[pgs-mqtt-consumer]
    Consumer --> Service[PGS domain services]
    API[pgs-api / FastAPI] --> Service
    Admin[Starlette Admin] --> Service
    Service --> DB[(PostgreSQL)]
    Service --> LedPort[DisplayCommandPort]
    LedPort --> MockLED[Mock LED adapter]
    MockLED --> Simulator[Admin LED Simulator]
    LedPort -. future .-> RealLED[Real LED hardware adapter]
```

### Контейнеры

```mermaid
flowchart TB
    subgraph Docker Compose
        DB[(pgs-db / PostgreSQL)]
        Migrate[pgs-migrate / alembic upgrade head]
        AdminBootstrap[pgs-admin-bootstrap / admin user]
        ParkingBootstrap[pgs-parking-bootstrap / demo base config]
        API[pgs-api / FastAPI]
        Consumer[pgs-mqtt-consumer]
    end

    DB --> Migrate
    Migrate --> AdminBootstrap
    AdminBootstrap --> API
    AdminBootstrap --> Consumer
    Migrate -. demo profile .-> ParkingBootstrap
    Consumer --> DB
    API --> DB
```

Сервисы:

| Сервис | Назначение |
| --- | --- |
| `pgs-db` | PostgreSQL база PGS |
| `pgs-migrate` | применяет Alembic миграции |
| `pgs-admin-bootstrap` | создает первого администратора из `.env`, если он настроен |
| `pgs-parking-bootstrap` | demo-only сервис, создает пример этажей/секторов/табло только при `--profile demo` |
| `pgs-api` | FastAPI API, админка и LED simulator |
| `pgs-mqtt-consumer` | слушает MQTT, обрабатывает события и создает структуру парковки из валидных кодов мест |

## Модель парковки

Текущая модель:

```mermaid
erDiagram
    ParkingFloor ||--o{ ParkingSector : contains
    ParkingSector ||--o{ ParkingZone : contains
    ParkingZone ||--o{ ParkingSpot : contains
    ParkingSector ||--o{ GuidanceDisplay : places
    GuidanceDisplay ||--o{ GuidanceDisplayZone : connects
    ParkingZone ||--o{ GuidanceDisplayZone : feeds
    ParkingSpot ||--o{ SpotOccupancyEvent : has

    ParkingFloor {
        int id
        string code
        string title
        bool is_active
    }

    ParkingSector {
        int id
        int floor_id
        string code
        string sector_letter
        string title
        bool is_active
    }

    ParkingZone {
        int id
        int sector_id
        string code
        string zone_number
        string title
        bool is_active
    }

    ParkingSpot {
        int id
        int zone_id
        string code
        string status
        bool is_active
    }

    GuidanceDisplay {
        int id
        int sector_id
        string code
        string arrow_direction
        bool is_active
    }

    GuidanceDisplayZone {
        int display_id
        int zone_id
        int sort_order
    }

    SpotOccupancyEvent {
        int id
        int spot_id
        string dedup_key
        string status
        string source
        datetime detected_at
    }
```

Иерархия:

```text
ParkingFloor
  -> ParkingSector
      -> ParkingZone / camera zone
          -> ParkingSpot
```

Пример кода места:

```text
B1-A-01-1
```

Расшифровка:

| Часть | Значение |
| --- | --- |
| `B1` | этаж |
| `A` | сектор |
| `01` | camera zone, то есть зона камеры |
| `1` | номер места внутри camera zone |

Имена полей в API:

| Поле | Пример | Что означает |
| --- | --- | --- |
| `sector_code` | `B1-A` | этаж + сектор |
| `camera_zone_code` | `B1-A-01` | зона камеры внутри сектора |
| `spot_code` | `B1-A-01-1` | конкретное парковочное место |

Пример:

```text
B1-A-01-1
B1-A-01-2
B1-A-01-3
B1-A-01-4
B1-A-01-5
B1-A-01-6
```

Одна camera zone обычно соответствует группе мест, за которыми наблюдает одна камера или видеодатчик.

## MQTT

PGS подписывается на события парковочных мест:

```text
parking/spots/+/status
```

Есть вспомогательный listener для просмотра всех известных топиков:

```text
parking/cameras/+/health
parking/spots/+/status
parking/zones/+/free
parking/total/free
```

Основной consumer сейчас обрабатывает только spot status:

```text
parking/spots/<spot_id>/status
```

### Ожидаемый формат spot_id

PGS принимает новый формат:

```text
FLOOR-SECTOR-CAMERA_ZONE-SPOT
```

Пример:

```text
B1-A-01-1
```

Старые форматы вроде `B1-C009`, `B1-C-009`, `B2-C04` для основного MQTT consumer считаются неподдерживаемыми и игнорируются.

### Пример MQTT-события

Topic:

```text
parking/spots/B1-A-01-1/status
```

Payload:

```json
{
  "spot_id": "B1-A-01-1",
  "zone_id": "B1-A-01",
  "status": "free",
  "plate": null,
  "timestamp": "2026-06-04T10:30:00"
}
```

Поддерживаемые значения `status`:

```text
free
occupied
offline
unknown
```

В базе они сохраняются как:

```text
FREE
OCCUPIED
OFFLINE
UNKNOWN
```

### Как обрабатывается событие

```mermaid
sequenceDiagram
    participant MQTT as MQTT broker
    participant Consumer as pgs-mqtt-consumer
    participant Parser as MQTT parser
    participant DB as PostgreSQL
    participant LED as Display service

    MQTT->>Consumer: parking/spots/B1-A-01-1/status
    Consumer->>Parser: validate topic + payload
    Parser-->>Consumer: SpotEventRequest
    Consumer->>DB: ensure floor, sector, camera zone and spot
    Consumer->>DB: save occupancy event
    Consumer->>DB: update parking spot status
    Consumer->>LED: recalculate displays connected to camera zone
    LED-->>Consumer: LED command count
```

### Auto-create

`pgs-mqtt-consumer` в compose запускается с:

```text
--auto-create --auto-create-floor-sector
```

Это значит:

- если floor еще не существует, consumer создает его из `spot_id`;
- если sector еще не существует, consumer создает его из `spot_id`;
- если camera zone еще не существует, consumer создает ее из `spot_id`;
- если parking spot еще не существует, consumer создает его из `spot_id`;
- после этого событие сохраняется и статус места обновляется.

Поэтому PGS можно запускать на чистой БД без заранее прошитого парковочного каркаса.

Пример auto-create:

```text
MQTT spot_id: B1-A-01-1

создаст:
ParkingFloor  -> B1
ParkingSector -> B1-A
ParkingZone   -> B1-A-01
ParkingSpot   -> B1-A-01-1
```

Важно: LED-табло, стрелки и связи табло с camera zones из MQTT не создаются, потому что это физическая схема установки оборудования. Их нужно настроить в админке или загрузить отдельным конфигом.

## LED-логика

PGS формирует команды для LED-табло.

Есть два типа отображения:

1. Маленькие навигационные LED-экраны.
2. Большое въездное табло.

### Маленькие LED-табло

Маленькое табло показывает:

```text
стрелка + количество свободных мест + P
```

Примеры:

```text
← 93 P
→ 0 P
↑ 12 P
```

Где:

| Элемент | Значение |
| --- | --- |
| `←`, `→`, `↑` | направление движения |
| `93` | количество свободных мест |
| `P` | parking indicator |

Стрелка не считается автоматически из MQTT. Она настраивается вручную для конкретного табло, потому что зависит от физического места установки.

Количество свободных мест считается не по всему сектору, а по camera zones, подключенным к конкретному табло.

Пример:

```text
DISP-LINE-01-RIGHT -> RIGHT -> zones: B1-A-01, B1-A-02
DISP-LINE-02-LEFT  -> LEFT  -> zones: B1-A-03, B1-A-04
DISP-LINE-02-RIGHT -> RIGHT -> zones: B1-A-05, B1-A-06
```

Если `DISP-LINE-01-RIGHT` подключен к двум camera zones:

```text
B1-A-01 -> 3 free
B1-A-02 -> 4 free
```

то маленькое табло покажет:

```text
→ 7 P
```

Если свободных мест `0`, стрелка остается той же, а число становится `0`:

```text
→ 0 P
```

В simulator число `0` отображается красным.

### Почему стрелка хранится у табло

Стрелка - это свойство не сектора, а конкретного физического табло.

Один и тот же сектор может быть показан с разных точек парковки разными стрелками:

```text
Display 1 -> B1-A -> LEFT
Display 2 -> B1-A -> AHEAD
Display 3 -> B1-A -> RIGHT
```

Поэтому `arrow_direction` хранится в `GuidanceDisplay`.

### Константы стрелок

Ручная настройка поддерживает:

```text
LEFT
RIGHT
AHEAD
```

`FULL` не используется как ручная настройка для маленьких табло. В текущей логике маленький экран всегда показывает стрелку, число и `P`, даже если число равно `0`.

### Большое въездное табло

Въездное табло показывает список секторов и свободных мест:

```text
B1-A 142
B1-B 121
B1-C 73
```

Оно не обязано показывать стрелки, потому что работает как общий summary display.

### LED simulator

LED simulator доступен в админке:

```text
/admin/led-simulator
```

Публичный `/led-simulator` отключен. Симулятор встроен в admin и доступен после логина.

Симулятор показывает:

- entry display;
- zone display debug;
- parking map;
- состояние parking spots;
- disabled parking badge для специальных мест.

### Реальное LED-оборудование

Сейчас готова бизнес-логика и mock adapter:

```text
app/adapters/led/mock.py
app/adapters/led/vendor.py
```

Реальная отправка на физическое LED-оборудование пока не реализована. Для этого нужен протокол/API/SDK от поставщика оборудования, например для `MW7725-FO-D` или `PKS2502-RG`.

Будущий adapter должен реализовать порт:

```text
DisplayCommandPort
```

Команда уже содержит готовые данные:

```json
{
  "display_code": "DISP-B1-A",
  "sector_code": "B1-A",
  "arrow_direction": "LEFT",
  "free_spots": 93,
  "parking_symbol": "P",
  "display_text": "LEFT 93 P",
  "message": "B1-A 93"
}
```

## REST API

Все API находятся под:

```text
/api/v1
```

### Health

| Method | Path | Auth | Назначение |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | нет | Проверка, что API работает |

### Auth

| Method | Path | Auth | Назначение |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | нет | Регистрация, если включена |
| `POST` | `/api/v1/auth/login` | нет | Логин, выставляет httpOnly cookie |
| `POST` | `/api/v1/auth/logout` | нет | Logout, очищает auth cookie если она есть |
| `GET` | `/api/v1/auth/me` | cookie | Текущий пользователь |

По умолчанию регистрация отключена:

```env
AUTH_REGISTRATION_ENABLED=false
```

Первый администратор создается через bootstrap, если заданы:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-password
```

### Protected API

Если `API_TOKEN` задан, protected endpoints требуют:

```text
Authorization: Bearer <API_TOKEN>
```

Если `API_TOKEN` пустой, token-check выключен.

Также protected API доступен из браузера после admin login за счет admin cookie. Это нужно, чтобы `/admin/led-simulator` мог читать API.

### Spots

| Method | Path | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/spots` | Список мест |
| `GET` | `/api/v1/spots/{spot_code}` | Детали места |

Фильтры:

```text
status=FREE
sector_code=B1-A
```

Пример:

```bash
curl http://localhost:8010/api/v1/spots \
  -H "Authorization: Bearer <API_TOKEN>"
```

### Sector summaries

`sector_code` - это код сектора, например `B1-A`.

| Method | Path | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/zones/summary` | Summary по всем секторам |
| `GET` | `/api/v1/zones/{sector_code}/summary` | Summary по сектору |
| `GET` | `/api/v1/zones/{sector_code}/messages` | LED messages по сектору |

Пример:

```bash
curl http://localhost:8010/api/v1/zones/summary \
  -H "Authorization: Bearer <API_TOKEN>"
```

### Displays

В API поле `sector_code` у display означает сектор, где физически находится табло. Поле `camera_zone_codes` означает camera zones, свободные места которых суммируются этим табло.

| Method | Path | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/displays` | Список табло |
| `GET` | `/api/v1/displays/summary` | Summary по табло |
| `GET` | `/api/v1/displays/messages` | Готовые LED-команды |
| `GET` | `/api/v1/displays/entry-message` | Въездное табло |
| `POST` | `/api/v1/displays` | Создать табло |
| `GET` | `/api/v1/displays/{display_code}` | Получить табло |
| `GET` | `/api/v1/displays/{display_code}/summary` | Summary конкретного табло |
| `PATCH` | `/api/v1/displays/{display_code}` | Обновить табло |
| `GET` | `/api/v1/displays/{display_code}/message` | Команда конкретного табло |

Пример:

```bash
curl "http://localhost:8010/api/v1/displays/messages?is_active=true" \
  -H "Authorization: Bearer <API_TOKEN>"
```

### Spot events

| Method | Path | Назначение |
| --- | --- | --- |
| `POST` | `/api/v1/spot-events` | Ручная отправка события по месту |

Обычно spot events приходят через MQTT. Этот endpoint полезен для ручной проверки.

## Админка

Админка доступна по адресу:

```text
http://localhost:8010/admin/login
```

В админке есть:

- LED Simulator;
- Floors;
- Sectors;
- Camera Zones;
- Parking Spots;
- Guidance Displays;
- Spot Events;
- Users.

Основная ручная настройка для LED:

```text
Guidance Display
  -> sector
  -> zones
  -> code
  -> title
  -> arrow_direction
  -> is_active
```

`arrow_direction` выбирается из списка:

```text
Left
Right
Ahead
```

## Auth и безопасность

### Admin auth

Админка защищена login/password.

Пароли хешируются через PBKDF2-HMAC-SHA256. Пароль в чистом виде в базе не хранится.

### API token

Для защиты API задается:

```env
API_TOKEN=your-token
```

После этого protected endpoints нужно вызывать так:

```bash
curl http://localhost:8010/api/v1/spots \
  -H "Authorization: Bearer your-token"
```

### Важные env-переменные для продакшена

Обязательно заменить:

```env
AUTH_SECRET_KEY=change-this-secret-in-production
ADMIN_PASSWORD=change-this-password
API_TOKEN=your-token
```

`AUTH_COOKIE_SECURE=true` стоит включать, если сервис работает через HTTPS.

## Запуск локально

### 1. Подготовить `.env`

Скопировать пример:

```bash
cp .env.example .env
```

Пример `.env`:

```env
APP_NAME=PGS (Parking Guidance Service)
DEBUG=true
PYTHONUNBUFFERED=1
DATABASE_URL=postgresql+psycopg2://pgs:pgs@pgs-db:5432/pgs

MQTT_HOST=10.210.10.25
MQTT_PORT=1883
MQTT_CLIENT_ID=pgs-mqtt-listener

AUTH_SECRET_KEY=local-dev-secret
AUTH_COOKIE_NAME=pgs_auth
AUTH_COOKIE_MAX_AGE=604800
AUTH_COOKIE_SECURE=false
AUTH_REGISTRATION_ENABLED=false

API_TOKEN=pgs-dev-token
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

### 2. Проверить Docker network

В `docker-compose.yml` используется внешняя сеть:

```text
smartparking_db_network
```

Если сети нет:

```bash
docker network create smartparking_db_network
```

Эта сеть нужна, чтобы PGS мог быть в одной Docker-сети со SmartParking/EMQX, когда они запускаются рядом.

### 3. Запустить проект

```bash
docker compose up --build
```

Или в фоне:

```bash
docker compose up --build -d
```

После старта:

- API: `http://localhost:8010`
- Admin: `http://localhost:8010/admin/login`
- PostgreSQL на хосте: `localhost:5435`

### 4. Проверить API

Health:

```bash
curl http://localhost:8010/api/v1/health
```

Protected API:

```bash
curl http://localhost:8010/api/v1/spots \
  -H "Authorization: Bearer pgs-dev-token"
```

Displays:

```bash
curl "http://localhost:8010/api/v1/displays/messages?is_active=true" \
  -H "Authorization: Bearer pgs-dev-token"
```

### 5. Зайти в админку

```text
http://localhost:8010/admin/login
```

Логин и пароль берутся из `.env`:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

### 6. Открыть LED simulator

После логина:

```text
http://localhost:8010/admin/led-simulator
```

## Ручной запуск MQTT listener

Для визуального просмотра MQTT-событий:

```bash
docker compose exec pgs-api python -m app.mqtt.listen \
  --host 10.210.10.25 \
  --port 1883
```

Для обработки spot events:

```bash
docker compose exec pgs-api python -m app.mqtt.consume_spot_events \
  --host 10.210.10.25 \
  --port 1883 \
  --auto-create \
  --auto-create-floor-sector
```

В compose `pgs-mqtt-consumer` уже запускается автоматически.

## Bootstrap

Обычный `docker compose up` не создает парковочный каркас заранее. Это сделано специально, чтобы PGS оставался динамичным микросервисом и мог работать на другой парковке без переписывания seed-данных.

Автоматически запускается только:

```text
pgs-admin-bootstrap
```

Он создает первого пользователя админки, если в `.env` заданы:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-password
```

### Demo parking bootstrap

Для локального demo-сценария есть отдельный сервис:

```text
pgs-parking-bootstrap
```

Он не запускается по умолчанию. Его можно запустить через profile:

```bash
docker compose --profile demo up pgs-parking-bootstrap
```

По умолчанию demo bootstrap создает:

```text
Floor: B1
Sectors: B1-A, B1-B, B1-C
Displays: DISP-B1-A, DISP-B1-B, DISP-B1-C
```

Он не создает parking spots заранее.

В основном рабочем сценарии parking spots, camera zones, sectors и floors создаются при приходе MQTT-событий.

Ручной запуск:

```bash
docker compose exec pgs-api python -m app.simulation.bootstrap_admin_user
```

Ручной запуск demo parking config:

```bash
docker compose exec pgs-api python -m app.simulation.bootstrap_parking_config
```

С кастомными секторами:

```bash
docker compose exec pgs-api python -m app.simulation.bootstrap_parking_config \
  --sector B1-A \
  --sector B1-B \
  --sector B1-C
```

## Seed parking map

Есть дополнительный скрипт для ручного наполнения карты:

```bash
docker compose exec pgs-api python -m app.simulation.seed_parking_map \
  --sector-spec B1-A=B1-A-01-1..B1-A-01-6 \
  --initial-status UNKNOWN
```

Этот скрипт нужен для разработки или ручной подготовки карты. Основной рабочий сценарий сейчас - auto-create из MQTT.

## Тесты

Запуск тестов:

```bash
docker compose run --rm -v ./tests:/app/tests pgs-api python -m pytest
```

Последняя проверка проекта:

```text
66 passed
```

## Миграции

Миграции запускаются автоматически через `pgs-migrate`.

Ручной запуск:

```bash
docker compose run --rm pgs-migrate
```

Текущие важные миграции:

- создание базовых таблиц парковки;
- удаление активного camera-layer;
- рефакторинг иерархии `floor -> sector -> camera zone -> spot`;
- создание таблицы users;
- ограничение `GuidanceDisplay.arrow_direction` на `LEFT`, `RIGHT`, `AHEAD`.

## Основные файлы

```text
app/main.py                          - FastAPI app
app/admin.py                         - Starlette Admin
app/admin_auth.py                    - auth provider для админки
app/api/v1/                          - REST API
app/contracts/mqtt_topics.py         - MQTT topics
app/mqtt/consume_spot_events.py      - основной MQTT consumer
app/services/mqtt_spot_events.py     - парсинг MQTT событий
app/services/spot_events.py          - обработка spot events
app/services/display.py              - расчет LED сообщений
app/services/led.py                  - публикация LED команд
app/adapters/led/mock.py             - mock LED adapter
app/adapters/led/vendor.py           - будущий vendor adapter
app/models/                          - SQLAlchemy models
app/simulation/bootstrap_admin_user.py - создание первого admin-пользователя
app/simulation/bootstrap_parking_config.py - demo-конфигурация парковки
app/api/led_simulator.py             - HTML/JS LED simulator
```

## Текущее состояние

Готово:

- FastAPI API;
- PostgreSQL schema и миграции;
- MQTT consumer;
- auto-create floors/sectors/camera zones/spots;
- admin login;
- API token guard;
- Starlette Admin;
- LED simulator;
- логика маленьких LED-табло `arrow + count + P`;
- entry display summary;
- динамический auto-create `floor -> sector -> camera zone -> spot` из MQTT;
- отдельный admin bootstrap;
- demo parking bootstrap через compose profile;
- тесты.

Не готово:

- реальная отправка команд на физические LED-табло;
- vendor adapter для конкретного оборудования;
- точная интеграция с протоколом `MW7725-FO-D` / `PKS2502-RG`;
- умная маршрутизация, где PGS сам выбирает лучший сектор вместо статической стрелки.

## Будущая интеграция с реальным LED

Сейчас PGS уже формирует готовую команду:

```json
{
  "display_code": "DISP-B1-A",
  "sector_code": "B1-A",
  "arrow_direction": "LEFT",
  "free_spots": 93,
  "parking_symbol": "P",
  "display_text": "LEFT 93 P",
  "message": "B1-A 93"
}
```

Следующий шаг - заменить mock adapter на реальный adapter:

```text
DisplayCommandPort
  -> VendorLedDisplayAdapter
      -> hardware protocol
```

Для этого нужно получить от поставщика:

- IP/порт табло;
- протокол обмена;
- формат команды;
- формат стрелок;
- формат символа `P`;
- требования по кодировке;
- необходимость авторизации;
- подтверждение доставки команды.

## Полный end-to-end сценарий

```mermaid
flowchart TD
    Start[Start docker compose] --> Migrate[Alembic migrations]
    Migrate --> AdminBootstrap[Create admin user if configured]
    AdminBootstrap --> Admin[Admin login]
    AdminBootstrap --> MQTT[MQTT consumer listens]
    MQTT --> Event[Spot status event arrives]
    Event --> Validate[Validate new spot code]
    Validate --> AutoCreate[Auto-create floor, sector, camera zone and spot]
    AutoCreate --> Update[Update spot status]
    Update --> Count[Count free spots by connected camera zones]
    Count --> Command[Build LED command]
    Command --> Simulator[Admin LED simulator updates]
    Command -. future .-> Hardware[Real LED display]
```

Ожидаемый результат:

```text
MQTT событие пришло
-> spot создан или обновлен
-> display summary изменился
-> displays/messages изменились
-> LED simulator показывает новое число
```
