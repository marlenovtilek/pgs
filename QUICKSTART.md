# PGS Quickstart

Короткая инструкция для быстрого продолжения работы с `PGS` на другой машине.

## 1. Пути проектов

- `SmartParking`: `/home/tilek/projects/SmartParking`
- `PGS`: `/home/tilek/projects/pgs`

Основной handoff-документ:

- `CONTEXT.md`

## 2. Открыть правильный репозиторий

Работать нужно в:

`/home/tilek/projects/pgs`

## 3. Проверить окружение

Убедиться, что есть файлы:

- `.env`
- `docker-compose.yml`
- `alembic.ini`

Ожидаемые значения `.env`:

```env
APP_NAME=PGS (Parking Guidance Service)
DEBUG=true
DATABASE_URL=postgresql+psycopg2://pgs:pgs@pgs-db:5432/pgs
```

## 4. Подготовить Docker network

`docker-compose.yml` ожидает внешнюю сеть:

`smartparking_db_network`

Если ее нет, создать один раз:

```bash
docker network create smartparking_db_network
```

## 5. Поднять сервисы

Из `/home/tilek/projects/pgs`:

```bash
docker compose up --build -d
```

Ожидаемые сервисы:

- `pgs-api`
- `pgs-db`

## 6. Применить миграции

```bash
docker compose exec pgs-api alembic upgrade head
```

## 7. Прогнать demo seed

```bash
docker compose exec pgs-api python -m app.simulation.seed_demo_data
```

Ожидаемые demo-объекты:

- зона `A`
- ряд `A1`
- места `A-001` .. `A-010`
- табло `DISP-A-01`

## 8. Базовые smoke-check’и

Health:

```bash
curl http://localhost:8010/api/v1/health
```

Spots:

```bash
curl http://localhost:8010/api/v1/spots
```

Zone summary:

```bash
curl http://localhost:8010/api/v1/zones/summary
curl http://localhost:8010/api/v1/zones/A/summary
```

Displays:

```bash
curl http://localhost:8010/api/v1/displays
curl http://localhost:8010/api/v1/displays/summary
curl http://localhost:8010/api/v1/displays/messages
curl http://localhost:8010/api/v1/displays/DISP-A-01/message
```

Zone messages:

```bash
curl http://localhost:8010/api/v1/zones/A/messages
```

## 9. Проверить ingest spot-event

Пример:

```bash
curl -X POST http://localhost:8010/api/v1/spot-events \
  -H "Content-Type: application/json" \
  -d '{
    "spot_code": "A-001",
    "status": "OCCUPIED",
    "detected_at": "2026-05-26T10:00:00Z",
    "source": "UNV_SERVICE"
  }'
```

После этого перепроверить:

```bash
curl http://localhost:8010/api/v1/zones/A/summary
curl http://localhost:8010/api/v1/displays/DISP-A-01/message
```

## 10. Напоминание по архитектуре

- коллега отвечает за UNV/camera integration;
- коллега отправляет нормализованные spot-level события;
- `PGS` отвечает за:
  - конфиг `zone / row / spot / display`;
  - обновление состояния мест;
  - подсчет summary;
  - сборку display message;
  - LED output logic.

`PGS` не должен напрямую работать с raw camera SDK.

## 11. Что делать дальше

Самый полезный следующий шаг:

- вынести reusable display-message logic в service layer.

Почему:

- сейчас логика сборки message дублируется в:
  - `GET /displays/{display_code}/message`
  - `GET /displays/messages`
  - `GET /zones/{zone_code}/messages`

После этого:

- подключать MQTT subscriber;
- использовать ту же внутреннюю логику и из HTTP, и из MQTT flow.

## 12. Resume prompt для Codex

На другой машине или в новой сессии можно писать так:

```text
Прочитай /home/tilek/projects/pgs/CONTEXT.md и /home/tilek/projects/pgs/QUICKSTART.md, потом продолжим с текущего состояния без повторного анализа проекта с нуля.
```
