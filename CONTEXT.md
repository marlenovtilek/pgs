# Контекст PGS / SmartParking

Последнее обновление: 2026-05-26  
Контекст создания: этот документ собран после нескольких дней проектирования и реализации новой подсистемы `PGS` рядом с существующим проектом `SmartParking`.  
Назначение: позволить продолжить работу с другого компьютера или из нового Codex-чата без повторного пересказа архитектуры, границ ответственности, текущего состояния и следующих шагов.

## 1. Зачем нужен этот документ

Это handoff-документ по текущему состоянию проекта `PGS`.

Он должен отвечать на вопросы:

- что такое `PGS`;
- почему его вынесли из `SmartParking`;
- что уже реализовано;
- что пока не реализовано намеренно;
- как `PGS` связан с сервисом коллеги для UNV/камер;
- какие файлы и точки входа самые важные;
- что делать дальше.

Цель в том, чтобы новая Codex-сессия на другом компьютере могла прочитать этот файл и продолжить работу почти без повторного анализа.

## 2. Какие репозитории участвуют

Сейчас есть два разных кодовых пространства, которые важны для этой задачи.

### 2.1 SmartParking

Путь:

`/home/tilek/projects/SmartParking`

Это основной действующий проект. Он построен как Django-монолит и содержит:

- въезд и выезд;
- парковочные сессии;
- биллинг и оплату;
- шлагбаумы;
- админку и backoffice;
- dashboards;
- авторизацию;
- существующие интеграции по камерам и смежную бизнес-логику.

### 2.2 PGS

Путь:

`/home/tilek/projects/pgs`

Это новый отдельный FastAPI-сервис для guidance-логики.

Он не является частью Django-runtime.

У него свои:

- FastAPI-приложение;
- PostgreSQL-база;
- Alembic-миграции;
- Dockerfile;
- docker-compose;
- модели;
- схемы;
- endpoint-слой;
- LED-ориентированная логика.

## 3. Главная продуктовая цель

Новый `PGS` реализует модель `free-space guidance`, а не назначение конкретного места конкретной машине.

Это значит:

- система не резервирует и не назначает место машине;
- система показывает общую навигацию;
- большие LED-табло показывают количество свободных и занятых мест, либо свободные места по зонам;
- маленькие LED-экраны показывают направление к свободным местам;
- система работает как общая навигация, а не как персональный маршрут для конкретного автомобиля.

Примеры ожидаемого поведения:

- `Zone A -> 24`
- `Zone B <- 8`
- стрелочные табло, которые всегда указывают в сторону доступных мест.

## 4. Какая архитектура сейчас считается правильной

Текущее согласованное направление:

### `PGS core + LED module`

Это означает:

- коллега отвечает за интеграцию с UNV/камерами;
- коллега нормализует наблюдения камер в события по конкретным местам;
- `PGS` владеет топологией парковки и guidance-логикой;
- `PGS` считает свободные и занятые места на основе spot-level событий;
- `PGS` сам решает, что должен показывать каждый display;
- `PGS` сам отправляет или готовит данные для LED-табло.

Важно:

- `PGS` — это не просто тупой LED-gateway;
- `PGS` — это не сервис SDK-камер;
- `PGS` — это guidance-ядро плюс LED-выходной модуль.

## 5. Разделение ответственности

### 5.1 Коллега / сервис со стороны камер

Сервис коллеги должен:

- общаться с UNV и другими guidance-камерами;
- знать, какая камера смотрит на какие места;
- нормализовать сырые наблюдения;
- публиковать spot-level события занятости;
- не считать guidance summary как главный источник истины для `PGS`;
- не решать, что показывать на LED.

Пример:

Одна камера смотрит на три места:

- `A1`
- `A2`
- `A3`

Сервис коллеги публикует нормализованные состояния:

- `A1 = OCCUPIED`
- `A2 = FREE`
- `A3 = FREE`

### 5.2 PGS

`PGS` должен:

- хранить конфиг парковки:
  - zone
  - row
  - spot
  - display
- хранить или обновлять текущее состояние мест;
- хранить историю событий;
- считать zone summary;
- собирать display message;
- готовить выход для больших и маленьких LED;
- отдавать admin/debug/configuration API;
- в будущем подписываться на MQTT и обрабатывать события внутри сервиса.

### 5.3 SmartParking

`SmartParking` по-прежнему отвечает за:

- въезд и выезд;
- распознавание номеров на воротах;
- `ParkingSession`;
- оплату и биллинг;
- управление шлагбаумами;
- dashboards и backoffice.

Новая guidance-логика по местам не должна жить в `SmartParking`.

## 6. Как должна выглядеть коммуникация

Ожидаемый рабочий event-flow:

`UNV/camera service -> MQTT -> PGS -> обновление состояния -> guidance calculation -> LED output`

Важно:

- MQTT — это будущий основной real-time вход для событий;
- FastAPI-endpoint’ы все еще нужны для:
  - CRUD;
  - тестов;
  - симуляции;
  - dashboard/debug чтения;
  - ручной проверки.

Предпочтительная будущая схема:

- MQTT subscriber внутри `PGS`;
- не `MQTT -> self HTTP -> DB`;
- а прямая внутренняя обработка в коде.

## 7. Почему PGS был вынесен из SmartParking

Изначально работа стартовала внутри:

`SmartParking/services/pgs`

Потом код был вынесен в:

`/home/tilek/projects/pgs`

Это было сделано потому что `PGS`:

- операционно отделим;
- ориентирован на устройства и события;
- не тесно связан с биллингом и `ParkingSession`;
- удобнее развивать как отдельный FastAPI-сервис.

Пользователь также инициализировал отдельный git-репозиторий в `/home/tilek/projects/pgs`.

## 8. Текущая структура PGS

Текущий обзор `/home/tilek/projects/pgs`:

- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `alembic.ini`
- `app/`
- `migrations/`
- `SMARTPARKING_GUIDANCE_TECH_SPEC_SHORT.md`
- `college/`

### 8.1 Обзор папки `app/`

- `app/main.py`
  - bootstrap FastAPI-приложения
- `app/api/`
  - роутеры и HTTP-endpoint’ы
- `app/core/`
  - конфиг и база
- `app/models/`
  - SQLAlchemy ORM-модели
- `app/schemas/`
  - Pydantic-схемы request/response
- `app/services/`
  - service-layer helpers
- `app/domain/`
  - enum’ы, порты, сущности, use case’ы
- `app/adapters/`
  - заготовки под LED, MQTT, Redis, persistence
- `app/simulation/`
  - локальный seed
- `app/contracts/`
  - MQTT topic constants

## 9. Точки входа в PGS

### 9.1 FastAPI app

Файл:

`app/main.py`

Что делает:

- создает FastAPI app;
- подключает `api_router`.

### 9.2 Верхний API-router

Файл:

`app/api/router.py`

Что делает:

- подключает `v1` router с префиксом `/api/v1`.

### 9.3 Активные роутеры v1

Файл:

`app/api/v1/router.py`

Сейчас подключены:

- `health`
- `spot_events`
- `spots`
- `zones`
- `display`

## 10. Текущая модель данных

Это основные активные сущности в `PGS`.

### 10.1 `ParkingZone`

Файл:

`app/models/parking_zone.py`

Назначение:

- верхний уровень группировки парковки.

Ключевые поля:

- `id`
- `title`
- `code`
- `level`
- `is_active`
- timestamps

### 10.2 `ParkingRow`

Файл:

`app/models/parking_row.py`

Назначение:

- подраздел внутри зоны.

Ключевые поля:

- `zone_id`
- `title`
- `code`
- `sort_order`
- `is_active`

Ограничения:

- уникальность по `(zone_id, code)`.

### 10.3 `ParkingSpot`

Файл:

`app/models/parking_spot.py`

Назначение:

- отдельное парковочное место.

Ключевые поля:

- `row_id`
- `code`
- `status`
- `sort_order`
- `is_active`

Ограничения:

- уникальность по `(row_id, code)`.

Статусы:

- `FREE`
- `OCCUPIED`
- `OFFLINE`
- `UNKNOWN`

### 10.4 `SpotOccupancyEvent`

Файл:

`app/models/spot_occupancy_event.py`

Назначение:

- история событий по изменениям состояния мест.

Ключевые поля:

- `spot_id`
- `event_id`
- `dedup_key`
- `status`
- `source`
- `payload`
- `detected_at`
- `created_at`

Важно:

- сущность теперь spot-centric;
- старый `camera_id` из runtime-логики убран.

### 10.5 `GuidanceDisplay`

Файл:

`app/models/guidance_display.py`

Назначение:

- физическое или логическое guidance-табло.

Ключевые поля:

- `title`
- `code`
- `zone_id`
- `arrow_direction`
- `is_active`
- timestamps

Поддерживаемые направления:

- `LEFT`
- `RIGHT`
- `AHEAD`
- `FULL`

## 11. Важные domain-файлы

### 11.1 Enum статуса места

Файл:

`app/domain/value_objects/spot_status.py`

Текущие значения:

- `FREE`
- `OCCUPIED`
- `OFFLINE`
- `UNKNOWN`

### 11.2 Enum направления стрелки

Файл:

`app/domain/value_objects/arrow_direction.py`

Текущие значения:

- `LEFT`
- `RIGHT`
- `AHEAD`
- `FULL`

### 11.3 Подсчет zone summary

Файл:

`app/domain/use_cases/calculate_zone_summary.py`

Назначение:

- считает:
  - `total`
  - `free`
  - `occupied`
  - `offline`
  - `unknown`

### 11.4 Hook для обработки spot event

Файл:

`app/domain/use_cases/process_spot_event.py`

Текущее состояние:

- файл есть;
- пока это простой stub;
- возвращает событие без изменений;
- задуман как будущая точка для нормализации, dedup и дополнительных бизнес-правил.

## 12. Рефакторинг camera-layer, который уже был сделан

Это исторически важный момент.

Изначально `PGS` имел camera-centric форму:

- camera endpoint;
- camera schema;
- `GuidanceCamera`;
- camera references в event model.

Позже это намеренно убрали из активного runtime, потому что камера-интеграция относится к сервису коллеги.

Что было сделано:

- старый camera API удален;
- старая camera schema удалена;
- `GuidanceCamera` убран из активного runtime;
- `SpotOccupancyEvent` больше не содержит `camera_id`;
- основной write path теперь `spot-events`.

Текущее правило:

- `PGS` принимает нормализованные события по местам;
- `PGS` не работает напрямую с UNV SDK и ONVIF.

## 13. Текущий набор API

Эти endpoint’ы существуют в активном коде и реально собирались/проверялись во время работы.

### 13.1 Health

- `GET /api/v1/health`

### 13.2 Spot events

- `POST /api/v1/spot-events`

Это текущий write/ingest HTTP-вход для тестов и симуляции.

Request schema:

- `spot_code`
- `status`
- `detected_at`
- `source`
- `event_id`
- `payload`

Логика:

- ищет spot по коду;
- строит dedup key;
- проверяет дубликат;
- создает `SpotOccupancyEvent`;
- обновляет текущий `ParkingSpot.status`.

### 13.3 Spots

- `GET /api/v1/spots`
- `GET /api/v1/spots/{spot_code}`

Список поддерживает фильтры:

- `status`
- `zone_code`

### 13.4 Zones

- `GET /api/v1/zones/summary`
- `GET /api/v1/zones/{zone_code}/summary`
- `GET /api/v1/zones/{zone_code}/messages`

`zone messages` сейчас поддерживает фильтр:

- `is_active`

### 13.5 Displays

- `GET /api/v1/displays`
- `POST /api/v1/displays`
- `GET /api/v1/displays/summary`
- `GET /api/v1/displays/messages`
- `GET /api/v1/displays/{display_code}`
- `PATCH /api/v1/displays/{display_code}`
- `GET /api/v1/displays/{display_code}/summary`
- `GET /api/v1/displays/{display_code}/message`

Текущие фильтры display list:

- `zone_code`
- `is_active`

Текущие фильтры display summary:

- `zone_code`

Текущие фильтры display messages:

- `zone_code`
- `is_active`

## 14. Важные детали текущей реализации API

### 14.1 Порядок роутов в `display.py`

Из-за матчинга FastAPI статические роуты должны стоять выше динамических.

Примеры:

- `/displays/summary` должен быть выше `/displays/{display_code}`;
- `/displays/messages` должен быть выше `/displays/{display_code}`.

Это уже было реальной причиной багов при разработке.

### 14.2 Логика сборки display-message сейчас дублируется

Сейчас в нескольких endpoint’ах повторяется одна и та же внутренняя логика:

- найти зону display;
- получить статусы мест этой зоны;
- посчитать summary;
- собрать `message`.

Эта дубликация есть в:

- single display message;
- display messages list;
- zone messages.

Это известный техдолг и ближайшая цель для рефакторинга.

### 14.3 Service layer существует только частично

Уже есть service layer для spots:

- `app/services/spots.py`

Но пока нет чистого переиспользуемого сервиса для сборки display message.

Это как раз был следующий запланированный шаг перед тем, как обсуждение ушло в архитектуру и handoff-документы.

## 15. Текущее состояние service layer

### 15.1 `app/services/spots.py`

Уже реализован и используется.

Содержит:

- базовый select builder;
- логику списка мест;
- логику одного места.

### 15.2 `app/services/zone_summary.py`

Сейчас фактически только переэкспортирует `calculate_zone_summary`.

### 15.3 `app/services/display.py`

Файл существует, но не является тем самым главным reusable display-message service.

Следующий логичный шаг — создать или переработать сервисный модуль для:

- сборки одного `DisplayMessageResponse` по display;
- дальнейшего переиспользования в нескольких endpoint’ах;
- будущего использования из MQTT subscriber и LED sender flow.

## 16. Текущие adapters и ports

Они существуют в основном как заготовки или интерфейсы для будущих шагов.

### 16.1 LED adapters

Файлы:

- `app/adapters/led/mock.py`
- `app/adapters/led/vendor.py`

Текущее состояние:

- это пока заглушки;
- реальной интеграции с железом еще нет.

### 16.2 Event bus adapter

Файл:

`app/adapters/event_bus/mqtt.py`

Текущее состояние:

- пока заглушка;
- рабочий subscriber/publisher еще не реализован.

### 16.3 Redis/state/persistence placeholders

Файлы:

- `app/adapters/state/redis.py`
- `app/adapters/persistence/postgres.py`

Текущее состояние:

- пока заглушки.

### 16.4 Ports

Файлы:

- `app/domain/ports/display.py`
- `app/domain/ports/event_bus.py`
- `app/domain/ports/state_store.py`

Они описывают предполагаемые интерфейсы, например:

- вывод display command;
- публикацию в event bus;
- работу со state store.

Пока они не подключены к реальной runtime-логике.

## 17. Текущий MQTT-contract

Полноценного production-ready MQTT subscriber в коде пока нет.

Есть небольшой contract-файл:

`app/contracts/mqtt_topics.py`

Текущие constants:

- `SPOT_EVENTS_TOPIC = "parking/spots/events"`
- `ZONE_STATUS_TOPIC_TEMPLATE = "parking/zones/{zone_code}/status"`

Но это нужно считать предварительным слоем.

Архитектурно сейчас правильнее считать главным входом:

- spot-level события от коллеги;
- `PGS` сам считает summary;
- `PGS` сам строит display messages.

Поэтому самым важным будущим topic’ом должен быть именно topic событий по местам, а не готовые zone counters как источник истины для `PGS`.

## 18. База, запуск и локальная среда

### 18.1 Environment

`.env` и `.env.example` сейчас содержат:

- `APP_NAME=PGS (Parking Guidance Service)`
- `DEBUG=true`
- `DATABASE_URL=postgresql+psycopg2://pgs:pgs@pgs-db:5432/pgs`

### 18.2 Docker compose

`docker-compose.yml` определяет:

- `pgs-api`
- `pgs-db`

Порты:

- API на хосте: `8010`
- Postgres на хосте: `5435`

Также используется внешняя Docker-сеть:

- `smartparking_db_network`

Если запускать на новой машине, нужно убедиться, что такая внешняя сеть существует, либо скорректировать compose.

### 18.3 Как ожидается локальный запуск

Обычный local workflow:

1. при необходимости создать docker network;
2. выполнить `docker compose up --build -d`;
3. применить миграции;
4. прогнать seed;
5. проверить endpoint’ы через `curl` или docs.

### 18.4 Seed

Файл:

`app/simulation/seed_demo_data.py`

Текущее поведение:

- создает зону `A`;
- создает ряд `A1`;
- создает 10 мест: `A-001` ... `A-010`;
- создает одно табло:
  - `DISP-A-01`
  - `Display A Entrance`

Seed сделан idempotent для этих demo-объектов.

## 19. Состояние миграций

Текущий набор миграций включает:

- `a2fdbd69b798_create_parking_zones_table.py`
- `0f6b9dcf5b9a_create_parking_rows_table.py`
- `40f0490e6ffc_create_parking_spots_table.py`
- `cd1a959a8635_create_guidance_cameras_table.py`
- `fdf989e20d29_create_spot_occupancy_events_table.py`
- `8680ade4f45b_create_guidance_displays_table.py`
- `33d66d76dca9_remove_camera_layer_from_pgs.py`

Важный исторический момент:

- `cd1a...` и `fdf9...` остаются как история схемы;
- `33d66...` — это cleanup-миграция, которая снимает активную зависимость от camera-layer.

На момент последних проверок:

- Alembic head был выровнен;
- pending autogenerated migration changes не было.

## 20. Что реально проверялось во время разработки

Во время последних сессий вручную проверялись:

- `seed_demo_data`
- `POST /api/v1/spot-events`
- `GET /api/v1/spots`
- `GET /api/v1/spots/{spot_code}`
- `GET /api/v1/zones/summary`
- `GET /api/v1/zones/{zone_code}/summary`
- `GET /api/v1/zones/{zone_code}/messages`
- `GET /api/v1/displays`
- `GET /api/v1/displays/summary`
- `GET /api/v1/displays/messages`
- `GET /api/v1/displays/{display_code}`
- `GET /api/v1/displays/{display_code}/summary`
- `GET /api/v1/displays/{display_code}/message`
- `POST /api/v1/displays`
- `PATCH /api/v1/displays/{display_code}`

Среди реально работающих результатов были:

- корректные display summary payload’ы;
- display message payload’ы вроде `A AHEAD 8`;
- zone messages для всех display внутри зоны `A`.

## 21. Текущий известный техдолг

Это основные не-блокирующие проблемы.

### 21.1 Дублирование логики display-message

Логику сборки сообщений нужно вынести в сервис.

### 21.2 Неровный стиль и форматирование

Некоторые API-файлы, особенно `display.py` и `zones.py`, имеют шероховатости:

- плотные импорты;
- неровные переносы строк;
- смешанный стиль оформления.

Логика рабочая, но cleanup еще нужен.

### 21.3 Заглушки adapters пока не подключены

MQTT, Redis и реальный LED vendor layer пока не реализованы до конца.

### 21.4 Нет subscriber-ingest path

Сейчас spot events входят через HTTP-endpoint для тестов и симуляции.

MQTT subscriber path еще не реализован.

### 21.5 Нет отдельного display-message service

Это самый близкий и полезный следующий рефакторинг.

## 22. Рекомендуемые следующие технические шаги

Если продолжать реализацию, разумно идти так:

### Шаг 1

Вынести переиспользуемую внутреннюю логику сборки display message в service layer.

Цель:

- одна функция принимает `db` и `display`;
- возвращает `DisplayMessageResponse` или `None`.

Это затем можно использовать в:

- `GET /displays/{display_code}/message`
- `GET /displays/messages`
- `GET /zones/{zone_code}/messages`

### Шаг 2

Перевести существующие endpoint’ы на этот shared service, чтобы убрать дублирование.

### Шаг 3

Зафиксировать финальный MQTT payload contract с коллегой.

Наиболее вероятно правильное направление:

- либо single-spot event;
- либо batch event от одной камеры на несколько мест.

### Шаг 4

Реализовать MQTT subscriber внутри `PGS`.

Желаемый внутренний flow:

- получить MQTT event;
- нормализовать payload, если нужно;
- вызвать внутреннюю spot-event processing logic;
- обновить состояние в БД;
- пересчитать нужные display messages;
- отправить обновление в LED output.

### Шаг 5

Сделать реальный LED output adapter.

### Шаг 6

При необходимости добавить историю и audit по исходящим display commands.

## 23. Что не надо возвращать обратно

Если продолжать разработку, не надо случайно скатиться назад к camera-centric дизайну.

Нужно избегать:

- прямой работы с UNV SDK внутри `PGS`;
- возврата `GuidanceCamera` в активный runtime;
- зависимости `PGS` от сырых camera protocol;
- дублирования ответственности сервиса коллеги.

Текущий целевой контракт:

- коллега делает raw camera work;
- `PGS` потребляет нормализованные события по местам.

## 24. Краткая структура SmartParking

Этот раздел нужен, потому что пользователь просил, чтобы в handoff была и структура `SmartParking`.

Корень:

`/home/tilek/projects/SmartParking`

### 24.1 Основные верхнеуровневые operational-файлы

- `docker-compose.yml`
- `docker-compose.dev.yml`
- `docker-compose.prod.yml`
- `Dockerfile`
- `Dockerfile.daphne`
- `requirements.txt`
- `entrypoints/`
- `nginx/`
- `launcher/`

### 24.2 Основной Django source root

Исходный код находится под:

`src/`

Главные app-level директории:

- `src/config`
- `src/parking`
- `src/billing`
- `src/common`
- `src/dashboards`
- `src/user_auth`
- `src/scripts`
- `src/templates`
- `src/static`
- `src/locale`

### 24.3 Картина по URL

Файл:

`src/config/urls.py`

Из него видно основные routing-области:

- `admin/`
- `parking/`
- `dashboards/`
- `parking/auth/`
- `billing/`
- token endpoint’ы;
- swagger/redoc.

Это подтверждает, что `SmartParking` остается широким монолитом со множеством бизнес-направлений за пределами guidance.

### 24.4 Роль `src/parking`

Это самый релевантный существующий модуль `SmartParking`.

Он содержит:

- `admin/`
- `api/`
- `controllers/`
- `jobs/`
- `management/`
- `services/`
- `views/`
- `ws/`

Внутри `src/parking/services/` есть крупные направления:

- `barrier/`
- `camera/`
- `error_log/`
- `parking_logic/`
- `wallet_history/`

Это одна из причин, почему `PGS` и был отделен:

- в `SmartParking` уже очень много gate/session/payment/camera логики;
- guidance-состояние только запутает монолит, если оставить его внутри.

### 24.5 `src/billing`

Содержит логику биллинга и оплат, а также bank integration.

Примеры из дерева:

- payment handlers;
- MBank dynamic/static payment service code;
- QR code logic;
- billing views и serializers.

Это еще раз показывает, что guidance-состояние не должно жить в этом же сервисе.

### 24.6 `src/dashboards`

Содержит dashboard/reporting логику.

Примеры:

- transaction service;
- parking reports;
- report views.

### 24.7 `src/common`

Содержит общие части проекта и management commands.

### 24.8 `src/user_auth`

Модуль аутентификации.

## 25. Связь между SmartParking и PGS

Сейчас целевая связь такая:

### SmartParking

- gate and session system;
- payment system;
- admin/backoffice;
- dashboards.

### PGS

- parking topology для guidance;
- occupancy state для guidance;
- zone и display summary;
- display messages;
- LED output.

Главное правило:

- держать их как соседние системы;
- не делать общего runtime-слоя;
- интегрировать через API и events, а не через прямую запись в чужие таблицы.

## 26. Практический чеклист для продолжения на другом компьютере

Если нужно продолжить работу в другом месте, самый быстрый путь такой:

1. открыть оба репозитория, если нужно:
   - `SmartParking`
   - `pgs`
2. полностью прочитать этот файл;
3. открыть сначала эти файлы в `PGS`:
   - `app/api/v1/display.py`
   - `app/api/v1/zones.py`
   - `app/api/v1/spot_events.py`
   - `app/services/spots.py`
   - `app/domain/use_cases/calculate_zone_summary.py`
4. помнить согласованную архитектуру:
   - коллега публикует нормализованные spot-level события;
   - `PGS` считает guidance;
   - LED — это модуль/выходной слой внутри `PGS`;
5. продолжать со следующего рекомендуемого шага:
   - вынести reusable display-message service;
6. только потом переходить к:
   - MQTT subscriber implementation;
   - LED adapter wiring.

## 27. Шаблон resume prompt для другой Codex-сессии

Если открыть этот репозиторий в новой Codex-сессии, хороший стартовый prompt будет таким:

`Прочитай CONTEXT.md, считай его текущим handoff-документом проекта, потом посмотри /home/tilek/projects/pgs и продолжай со следующего рекомендованного шага без повторного анализа архитектуры с нуля.`

## 28. Итоговое состояние проекта

Текущая зрелость:

- архитектурное направление уже прояснено;
- camera-layer убран из активного runtime;
- HTTP-ingest для spot-events уже есть;
- display CRUD/read/message/summary API уже есть;
- zone summary/message API уже есть;
- seed и миграции работают;
- guidance-логика уже видна в API.

Что еще не сделано:

- reusable internal display-message service;
- MQTT subscriber;
- реальный LED adapter;
- end-to-end event-bus integration с сервисом коллеги.

Проект уже не на стадии чистого scaffolding.

У него уже есть:

- реальный FastAPI-сервис;
- реальная схема БД;
- рабочий guidance-domain HTTP API;
- понятное направление для следующей integration-фазы.
