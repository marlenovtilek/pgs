# SmartParking PGS — Симуляция

**Связано с:** [[Architecture]] | [[Tech Stack]]
**Дата:** 2026-05-19

---

## Принцип

Симуляция и прод используют **одну и ту же архитектуру**.
Меняется только адаптер — через переменную окружения.
Код сервисов не трогается при переходе на реальное оборудование.

```mermaid
flowchart LR
    subgraph CORE["Неизменяемое ядро"]
        UC[Use Cases\nDomain Logic]
        REDIS[(Redis)]
        EMQX{{EMQX}}
    end

    subgraph SIM["Режим: СИМУЛЯЦИЯ"]
        MS[mock_unv\nскрипт]
        MD[mock_led\nдашборд]
    end

    subgraph PROD["Режим: ПРОД"]
        SDK[UNV SDK\nреальные камеры]
        LED[Dahua / TCP\nреальные экраны]
    end

    MS -->|ICameraPort| UC
    SDK -->|ICameraPort| UC
    UC -->|IDisplayPort| MD
    UC -->|IDisplayPort| LED
    UC <--> REDIS
    UC <--> EMQX
```

---

## Компоненты симуляции

### mock_unv — имитация UNV камер

**Что делает:**
- Знает карту всех зон и мест (из `zones.json`)
- По таймеру случайно меняет статус места (свободно → занято → свободно)
- Публикует в MQTT те же топики что публиковал бы настоящий `unv-service`

**Режимы работы:**
- **Случайный** — места меняются случайно каждые N секунд
- **Сценарий** — заранее заданная последовательность событий для теста

---

### mock_session — имитация Django сессий

**Что делает:**
- Публикует в MQTT `parking/session/created`
- Имитирует что машина въехала и шлагбаум открылся
- Запускается вручную для тестирования реакции LED

---

### Dashboard — визуализация

**Что делает:**
- FastAPI сервер с WebSocket
- Слушает все MQTT топики
- Показывает в браузере в реальном времени:
  - Карту мест (зелёный = свободно, красный = занято)
  - Что показывает каждый LED экран (стрелки + цифры)
  - Табло на въезде

```mermaid
flowchart LR
    EMQX{{EMQX}} -->|все топики| DASH[Dashboard\nFastAPI]
    DASH -->|WebSocket| BROWSER[Браузер\nкарта парковки]
    BROWSER --> SPOTS[🟩🟥🟩 места]
    BROWSER --> LEDS[← 44 | → 12 LED экраны]
    BROWSER --> BOARD[Свободно: 1799 табло]
```

---

## Сценарии для тестирования

```mermaid
flowchart TD
    S1[Сценарий 1\nМашина въезжает\nи паркуется]
    S2[Сценарий 2\nМашина уезжает]
    S3[Сценарий 3\nЗона полностью заполняется]
    S4[Сценарий 4\nКамера уходит в офлайн]
    S5[Сценарий 5\nRush hour\nМного машин одновременно]

    S1 --> CHECK1{LED обновил стрелки?\nТабло изменилось?}
    S2 --> CHECK2{Место освободилось?\nТабло +1?}
    S3 --> CHECK3{LED показывает ЗАНЯТО?}
    S4 --> CHECK4{LED остался на\nпоследнем значении?}
    S5 --> CHECK5{Счётчики корректны?\nНет race condition?}
```

---

## Переход на прод

```mermaid
flowchart TD
    NOW[Сейчас:\nСимуляция работает]
    UNV_ARRIVES[Приехала UNV камера]
    LED_ARRIVES[Куплен LED экран]
    FULL_PROD[Полный прод]

    NOW -->|CAMERA_DRIVER=mock| UNV_ARRIVES
    UNV_ARRIVES -->|CAMERA_DRIVER=unv_sdk\nLED_DRIVER=mock| LED_ARRIVES
    LED_ARRIVES -->|CAMERA_DRIVER=unv_sdk\nLED_DRIVER=dahua| FULL_PROD

    NOTE1[Меняем только .env\nКод не трогаем]
    UNV_ARRIVES -.-> NOTE1
    LED_ARRIVES -.-> NOTE1
```

**Порядок перехода:**
1. Симуляция → тестируем всю логику без железа
2. Приехала UNV камера → переключаем `CAMERA_DRIVER=unv_sdk`, LED ещё mock
3. Купили LED экран → переключаем `LED_DRIVER=dahua`
4. Всё на проде — dashboard можно оставить для мониторинга

---

*[[Architecture]] — полная архитектура*
*[[Tech Stack]] — технологии*
