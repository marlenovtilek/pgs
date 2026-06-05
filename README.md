# PGS - Parking Guidance Service

PGS - это микросервис навигации по парковке. Его задача - принимать события о занятости парковочных мест, хранить актуальное состояние парковки, считать количество свободных мест по секторам и формировать команды для LED-табло.

Сервис не распознает номера, не управляет камерами и не решает задачу компьютерного зрения. Эти задачи выполняет внешний SmartParking/UNV слой. PGS получает уже готовые события через MQTT и превращает их в состояние парковки и команды навигации.

## Коротко

PGS делает следующее:

- принимает MQTT-события по парковочным местам;
- создает camera zones и parking spots при приходе валидных MQTT-событий;
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

Если Markdown viewer не рендерит Mermaid, та же схема в plain text:

```text
SmartParking / UNV
        |
        | MQTT: parking/spots/+/status
        v
MQTT broker / EMQX
        |
        v
pgs-mqtt-consumer
        |
        v
PGS domain services <---------- pgs-api / FastAPI
        ^                         ^
        |                         |
        |                         +---------- Starlette Admin
        |
        v
PostgreSQL
        |
        v
DisplayCommandPort
        |
        +--> Mock LED adapter --> Admin LED Simulator
        |
        +--> future Vendor LED adapter --> Real LED hardware
```

### Контейнеры

```mermaid
flowchart TB
    subgraph Docker Compose
        DB[(pgs-db / PostgreSQL)]
        Migrate[pgs-migrate / alembic upgrade head]
        Bootstrap[pgs-bootstrap / base config]
        API[pgs-api / FastAPI]
        Consumer[pgs-mqtt-consumer]
    end

    DB --> Migrate
    Migrate --> Bootstrap
    Bootstrap --> API
    Bootstrap --> Consumer
    Consumer --> DB
    API --> DB
```

Plain text:

```text
docker compose
|
+-- pgs-db
|     PostgreSQL database
|
+-- pgs-migrate
|     waits for pgs-db
|     runs alembic upgrade head
|
+-- pgs-bootstrap
|     waits for migrations
|     creates base floors/sectors/displays/admin user
|
+-- pgs-api
|     FastAPI + Admin + LED simulator
|     reads/writes pgs-db
|
+-- pgs-mqtt-consumer
      listens MQTT broker
      writes spot events into pgs-db
```

Сервисы:

| Сервис | Назначение |
| --- | --- |
| `pgs-db` | PostgreSQL база PGS |
| `pgs-migrate` | применяет Alembic миграции |
| `pgs-bootstrap` | создает базовую конфигурацию и первого администратора |
| `pgs-api` | FastAPI API, админка и LED simulator |
| `pgs-mqtt-consumer` | слушает MQTT и обрабатывает события парковочных мест |

## Модель парковки

Текущая модель:

```mermaid
erDiagram
    ParkingFloor ||--o{ ParkingSector : contains
    ParkingSector ||--o{ ParkingZone : contains
    ParkingZone ||--o{ ParkingSpot : contains
    ParkingSector ||--o{ GuidanceDisplay : targets
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

    SpotOccupancyEvent {
        int id
        int spot_id
        string dedup_key
        string status
        string source
        datetime detected_at
    }
```

Plain text:

```text
ParkingFloor
  id
  code: B1
  title: Floor B1
  |
  +-- ParkingSector
      id
      code: B1-A
      sector_letter: A
      |
      +-- ParkingZone / camera zone
      |   id
      |   code: B1-A-01
      |   zone_number: 01
      |   |
      |   +-- ParkingSpot
      |       id
      |       code: B1-A-01-1
      |       status: FREE / OCCUPIED / OFFLINE / UNKNOWN
      |
      +-- GuidanceDisplay
          id
          code: DISP-B1-A
          arrow_direction: LEFT / RIGHT / AHEAD
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
    Consumer->>DB: ensure camera zone and spot
    Consumer->>DB: save occupancy event
    Consumer->>DB: update parking spot status
    Consumer->>LED: recalculate sector display messages
    LED-->>Consumer: LED command count
```

Plain text:

```text
1. MQTT broker sends:
   topic   = parking/spots/B1-A-01-1/status
   payload = {"status": "free", ...}

2. pgs-mqtt-consumer validates:
   B1-A-01-1 must match FLOOR-SECTOR-CAMERA_ZONE-SPOT

3. PGS finds configured sector:
   B1-A

4. If needed, PGS auto-creates:
   camera zone B1-A-01
   parking spot B1-A-01-1

5. PGS saves occupancy event and updates spot status:
   B1-A-01-1 -> FREE

6. PGS recalculates sector free count:
   B1-A -> 93 free spots

7. PGS builds LED command:
   DISP-B1-A -> LEFT 93 P
```

### Auto-create

`pgs-mqtt-consumer` запускается с:

```text
--auto-create
```

Это значит:

- если сектор уже настроен в PGS, consumer может автоматически создать missing camera zone;
- если spot еще не существует, consumer может автоматически создать spot;
- floor/sector по умолчанию не создаются из MQTT, их нужно иметь заранее через bootstrap или админку.

Для разработки есть флаг:

```text
--auto-create-floor-sector
```

Он может создавать floor/sector из MQTT, но это development-only режим. В compose он не используется.

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

Пример:

```text
DISP-B1-A -> сектор B1-A -> LEFT
DISP-B1-B -> сектор B1-B -> RIGHT
DISP-B1-C -> сектор B1-C -> AHEAD
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
  "zone_code": "B1-A",
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
zone_code=B1-A
```

Пример:

```bash
curl http://localhost:8010/api/v1/spots \
  -H "Authorization: Bearer <API_TOKEN>"
```

### Zones

В API название `zone_code` исторически используется для кода сектора, например `B1-A`.

| Method | Path | Назначение |
| --- | --- | --- |
| `GET` | `/api/v1/zones/summary` | Summary по всем секторам |
| `GET` | `/api/v1/zones/{zone_code}/summary` | Summary по сектору |
| `GET` | `/api/v1/zones/{zone_code}/messages` | LED messages по сектору |

Пример:

```bash
curl http://localhost:8010/api/v1/zones/summary \
  -H "Authorization: Bearer <API_TOKEN>"
```

### Displays

В API поле `zone_code` у display тоже означает сектор, к которому привязано табло.

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
  --auto-create
```

В compose `pgs-mqtt-consumer` уже запускается автоматически.

## Bootstrap

`pgs-bootstrap` запускается автоматически в compose.

По умолчанию он создает:

```text
Floor: B1
Sectors: B1-A, B1-B, B1-C
Displays: DISP-B1-A, DISP-B1-B, DISP-B1-C
```

Он не создает parking spots заранее.

Parking spots создаются при приходе MQTT-событий.

Ручной запуск:

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
  --zone-spec B1-A=B1-A-01-1..B1-A-01-6 \
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
60 passed
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
app/simulation/bootstrap_parking_config.py - базовая конфигурация
app/api/led_simulator.py             - HTML/JS LED simulator
```

## Текущее состояние

Готово:

- FastAPI API;
- PostgreSQL schema и миграции;
- MQTT consumer;
- auto-create camera zones/spots;
- admin login;
- API token guard;
- Starlette Admin;
- LED simulator;
- логика маленьких LED-табло `arrow + count + P`;
- entry display summary;
- базовый bootstrap;
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
  "zone_code": "B1-A",
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
    Migrate --> Bootstrap[Bootstrap B1 sectors and displays]
    Bootstrap --> Admin[Admin login]
    Bootstrap --> MQTT[MQTT consumer listens]
    MQTT --> Event[Spot status event arrives]
    Event --> Validate[Validate new spot code]
    Validate --> AutoCreate[Auto-create camera zone and spot]
    AutoCreate --> Update[Update spot status]
    Update --> Count[Count free spots by sector]
    Count --> Command[Build LED command]
    Command --> Simulator[Admin LED simulator updates]
    Command -. future .-> Hardware[Real LED display]
```

Plain text:

```text
docker compose up
  |
  v
pgs-migrate
  |
  v
pgs-bootstrap
  |
  +--> creates B1, B1-A, B1-B, B1-C
  +--> creates initial guidance displays
  +--> creates admin user
  |
  v
pgs-api starts
  |
  +--> /api/v1
  +--> /admin
  +--> /admin/led-simulator
  |
  v
pgs-mqtt-consumer starts
  |
  v
MQTT event arrives
  |
  v
PGS validates spot code
  |
  v
PGS creates/updates camera zone and spot
  |
  v
PGS recalculates free spots
  |
  v
PGS produces LED message
  |
  +--> LED simulator now
  +--> real LED adapter in the future
```

Ожидаемый результат:

```text
MQTT событие пришло
-> spot создан или обновлен
-> sector summary изменился
-> displays/messages изменились
-> LED simulator показывает новое число
```
