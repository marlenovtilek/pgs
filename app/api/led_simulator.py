LED_SIMULATOR_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PGS LED-симулятор</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101114;
      --panel: #050607;
      --panel-edge: #30343a;
      --text: #f5f7fb;
      --muted: #aeb6c2;
      --green: #36ff71;
      --red: #ff3b3b;
      --amber: #ffcf33;
      --blue: #69a7ff;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 2;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 56px;
      padding: 12px 20px;
      border-bottom: 1px solid #25282d;
      background: rgba(16, 17, 20, 0.94);
      backdrop-filter: blur(8px);
    }

    .brand {
      display: flex;
      align-items: baseline;
      gap: 12px;
      min-width: 0;
    }

    h1 {
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
      font-weight: 700;
      letter-spacing: 0;
      white-space: nowrap;
    }

    .status {
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }

    .wrap {
      width: min(1180px, 100%);
      margin: 0 auto;
      padding: 20px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      align-items: stretch;
    }

    .section {
      margin-bottom: 24px;
    }

    .section-title {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 12px;
      color: #dfe6ee;
      font-size: 15px;
      line-height: 1.2;
      font-weight: 700;
      letter-spacing: 0;
    }

    .display {
      min-height: 210px;
      border: 1px solid var(--panel-edge);
      border-radius: 8px;
      background: linear-gradient(180deg, #121418, var(--panel));
      box-shadow: inset 0 0 0 2px #000, 0 10px 26px rgba(0, 0, 0, 0.28);
      padding: 14px;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 12px;
    }

    .display-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.2;
    }

    .code {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .zone {
      color: var(--blue);
      font-weight: 700;
    }

    .led-face {
      min-height: 124px;
      border-radius: 6px;
      border: 1px solid #242a30;
      background:
        radial-gradient(circle at center, rgba(255, 255, 255, 0.04) 1px, transparent 1.2px) 0 0 / 7px 7px,
        #020303;
      display: grid;
      grid-template-columns: auto minmax(76px, 1fr) auto;
      align-items: center;
      gap: 14px;
      padding: 16px;
      overflow: hidden;
    }

    .led-text {
      min-width: 0;
    }

    .line {
      font-family: "Arial Black", Impact, ui-sans-serif, system-ui, sans-serif;
      letter-spacing: 0;
      text-transform: uppercase;
      text-shadow: 0 0 16px currentColor;
      overflow-wrap: anywhere;
    }

    .line.zone-line {
      color: var(--amber);
      font-size: clamp(26px, 4vw, 46px);
      line-height: 1;
    }

    .line.message-line {
      margin-top: 8px;
      color: var(--green);
      font-size: clamp(20px, 3vw, 34px);
      line-height: 1.05;
    }

    .arrow {
      min-width: 64px;
      color: var(--green);
      font-family: "Arial Black", Impact, ui-sans-serif, system-ui, sans-serif;
      font-size: clamp(54px, 8vw, 92px);
      line-height: 0.9;
      text-align: center;
      text-shadow: 0 0 22px currentColor;
      white-space: nowrap;
    }

    .count {
      min-width: 0;
      color: var(--green);
      font-family: "Arial Black", Impact, ui-sans-serif, system-ui, sans-serif;
      font-size: clamp(54px, 8vw, 92px);
      line-height: 0.9;
      text-align: left;
      text-shadow: 0 0 22px currentColor;
    }

    .parking-symbol {
      min-width: 54px;
      color: var(--blue);
      font-family: "Arial Black", Impact, ui-sans-serif, system-ui, sans-serif;
      font-size: clamp(42px, 6vw, 70px);
      line-height: 0.9;
      text-align: center;
      text-shadow: 0 0 18px currentColor;
      border: 1px solid rgba(105, 167, 255, 0.55);
      box-shadow: inset 0 0 18px rgba(105, 167, 255, 0.18);
      padding: 8px 6px;
    }

    .display.full .count,
    .display.full .message-line {
      color: var(--red);
    }

    .entry-display {
      min-height: 320px;
    }

    .entry-display .led-face {
      min-height: 232px;
      grid-template-columns: 1fr;
    }

    .entry-lines {
      display: grid;
      gap: 12px;
      min-width: 0;
    }

    .entry-line {
      color: var(--green);
      font-family: "Arial Black", Impact, ui-sans-serif, system-ui, sans-serif;
      font-size: clamp(22px, 4vw, 44px);
      line-height: 1;
      text-transform: uppercase;
      text-shadow: 0 0 18px currentColor;
      overflow-wrap: anywhere;
    }

    .entry-total {
      color: var(--amber);
      font-family: "Arial Black", Impact, ui-sans-serif, system-ui, sans-serif;
      font-size: clamp(18px, 2.5vw, 30px);
      text-shadow: 0 0 14px currentColor;
    }

    .meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.2;
    }

    .pill {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      border: 1px solid #2e3339;
      border-radius: 999px;
      padding: 5px 8px;
      color: #dce3ea;
    }

    .empty {
      min-height: 180px;
      display: grid;
      place-items: center;
      color: var(--muted);
      border: 1px dashed #343941;
      border-radius: 8px;
      text-align: center;
      padding: 24px;
    }

    .level-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }

    .level-card {
      border: 1px solid var(--panel-edge);
      border-radius: 8px;
      background: #15171b;
      padding: 14px;
      min-width: 0;
    }

    .level-title {
      margin-bottom: 12px;
      color: var(--amber);
      font-size: 20px;
      line-height: 1.2;
      font-weight: 900;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .zone-card {
      border: 1px solid #2b3036;
      border-radius: 8px;
      background: #101216;
      padding: 12px;
      min-width: 0;
    }

    .zone-stack {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .zone-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }

    .zone-card-title {
      color: var(--blue);
      font-size: 18px;
      line-height: 1.2;
      font-weight: 800;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .zone-card-counts {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }

    .spots {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(74px, 1fr));
      gap: 6px;
    }

    .spot {
      min-height: 42px;
      border: 1px solid #30343a;
      border-radius: 6px;
      background: #0b0c0e;
      padding: 7px 6px;
      display: grid;
      grid-template-columns: 1fr auto;
      align-content: center;
      gap: 3px;
      overflow: hidden;
    }

    .spot-code {
      color: #f2f6fb;
      font-size: 11px;
      line-height: 1;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .spot-status {
      font-size: 10px;
      line-height: 1;
      font-weight: 800;
      grid-column: 1 / -1;
    }

    .spot-badge {
      color: var(--blue);
      font-size: 13px;
      line-height: 1;
      font-weight: 900;
      text-shadow: 0 0 10px currentColor;
    }

    .spot.disabled {
      border-color: rgba(105, 167, 255, 0.7);
      box-shadow: inset 0 0 16px rgba(105, 167, 255, 0.12);
    }

    .spot.free {
      border-color: rgba(54, 255, 113, 0.45);
      box-shadow: inset 0 0 14px rgba(54, 255, 113, 0.08);
    }

    .spot.free .spot-status { color: var(--green); }

    .spot.occupied {
      border-color: rgba(255, 59, 59, 0.5);
      box-shadow: inset 0 0 14px rgba(255, 59, 59, 0.08);
    }

    .spot.occupied .spot-status { color: var(--red); }

    .spot.unknown {
      border-color: rgba(255, 207, 51, 0.45);
    }

    .spot.unknown .spot-status { color: var(--amber); }

    .spot.offline {
      opacity: 0.58;
    }

    .spot.offline .spot-status { color: var(--muted); }

    .intro {
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
      max-width: 90ch;
    }

    .hint {
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      max-width: 88ch;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 18px;
      margin: 0 0 16px;
      padding: 10px 14px;
      border: 1px solid var(--panel-edge);
      border-radius: 8px;
      background: #15171b;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #dce3ea;
      font-size: 12px;
      line-height: 1.2;
      white-space: nowrap;
    }

    .swatch {
      width: 16px;
      height: 16px;
      border-radius: 4px;
      border: 1px solid #30343a;
      flex: 0 0 auto;
    }

    .swatch.free { background: rgba(54, 255, 113, 0.22); border-color: rgba(54, 255, 113, 0.6); }
    .swatch.occupied { background: rgba(255, 59, 59, 0.22); border-color: rgba(255, 59, 59, 0.6); }
    .swatch.unknown { background: rgba(255, 207, 51, 0.22); border-color: rgba(255, 207, 51, 0.6); }
    .swatch.offline { background: #0b0c0e; opacity: 0.55; }

    .swatch-badge {
      flex: 0 0 auto;
      color: var(--blue);
      font-size: 15px;
      line-height: 1;
      text-shadow: 0 0 10px currentColor;
    }

    @media (max-width: 560px) {
      .topbar {
        align-items: flex-start;
        flex-direction: column;
      }

      .status {
        white-space: normal;
      }

      .wrap {
        padding: 14px;
      }

      .arrow {
        min-width: 52px;
      }

      .count {
        text-align: left;
      }

      .parking-symbol {
        min-width: 46px;
      }

      .level-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <h1>PGS LED-симулятор</h1>
      <div class="status" id="summary">Загрузка табло</div>
    </div>
    <div class="status" id="updated">Ожидание данных</div>
  </header>
  <main class="wrap">
    <p class="intro">
      Предпросмотр того, что прямо сейчас показывают LED-табло парковки.
      Это копия реальных табло на экране — данные берутся из PGS и обновляются автоматически каждые 2 секунды.
    </p>

    <section class="section">
      <h2 class="section-title">
        <span>Въездное табло</span>
        <span class="status" id="entryCount">0 строк</span>
      </h2>
      <p class="hint">
        Большое табло на въезде. Показывает, сколько свободных мест в каждом секторе и сколько свободно на парковке в целом —
        чтобы водитель ещё на въезде понимал, есть ли смысл заезжать и куда.
      </p>
      <div id="entryDisplay" aria-live="polite"></div>
    </section>

    <section class="section">
      <h2 class="section-title">
        <span>Навигационные табло</span>
        <span class="status" id="displayCount">0 табло</span>
      </h2>
      <p class="hint">
        Маленькие табло на развилках внутри парковки. Стрелка — в какую сторону ехать,
        крупное число — сколько там свободных мест, «P» — обозначение парковки.
        Если свободных мест не осталось, число становится красным.
      </p>
      <div class="grid" id="displayGrid" aria-live="polite"></div>
    </section>

    <section class="section">
      <h2 class="section-title">
        <span>Карта парковки</span>
        <span class="status" id="spotCount">0 мест</span>
      </h2>
      <p class="hint">
        Текущее состояние каждого места, сгруппированное по этажам и секторам. Цвет показывает статус места:
      </p>
      <div class="legend">
        <span class="legend-item"><span class="swatch free"></span>свободно</span>
        <span class="legend-item"><span class="swatch occupied"></span>занято</span>
        <span class="legend-item"><span class="swatch unknown"></span>неизвестно (ещё не было данных)</span>
        <span class="legend-item"><span class="swatch offline"></span>офлайн (нет связи с камерой)</span>
        <span class="legend-item"><span class="swatch-badge">&#9855;</span>место для инвалидов</span>
      </div>
      <div class="level-grid" id="mapGrid" aria-live="polite"></div>
    </section>
  </main>

  <script>
    const displayGrid = document.getElementById("displayGrid");
    const entryDisplay = document.getElementById("entryDisplay");
    const mapGrid = document.getElementById("mapGrid");
    const summary = document.getElementById("summary");
    const updated = document.getElementById("updated");
    const entryCount = document.getElementById("entryCount");
    const displayCount = document.getElementById("displayCount");
    const spotCount = document.getElementById("spotCount");

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function statusClass(status) {
      return String(status || "unknown").toLowerCase();
    }

    function pluralRu(count, one, few, many) {
      const abs = Math.abs(count) % 100;
      const last = abs % 10;
      if (abs > 10 && abs < 20) {
        return many;
      }
      if (last === 1) {
        return one;
      }
      if (last >= 2 && last <= 4) {
        return few;
      }
      return many;
    }

    function countText(count, one, few, many) {
      return `${count} ${pluralRu(count, one, few, many)}`;
    }

    function directionLabel(direction) {
      if (direction === "LEFT") {
        return "налево";
      }
      if (direction === "RIGHT") {
        return "направо";
      }
      if (direction === "AHEAD") {
        return "прямо";
      }
      if (direction === "FULL") {
        return "нет мест";
      }
      return String(direction || "");
    }

    function statusLabel(status) {
      if (status === "FREE") {
        return "СВОБОДНО";
      }
      if (status === "OCCUPIED") {
        return "ЗАНЯТО";
      }
      if (status === "OFFLINE") {
        return "ОФЛАЙН";
      }
      if (status === "UNKNOWN") {
        return "НЕИЗВЕСТНО";
      }
      return String(status || "");
    }

    function displayPillText(item) {
      const direction = directionLabel(item.arrow_direction);
      return `${item.sector_code} ${direction} ${item.free_spots} P`;
    }

    function arrowSymbolHtml(direction) {
      if (direction === "LEFT") {
        return "&#8592;";
      }
      if (direction === "RIGHT") {
        return "&#8594;";
      }
      if (direction === "AHEAD") {
        return "&#8593;";
      }
      if (direction === "FULL") {
        return "";
      }
      return escapeHtml(direction || "");
    }

    function parkingSymbolHtml(item) {
      if (item.arrow_direction === "FULL") {
        return "";
      }
      return `<div class="parking-symbol">${escapeHtml(item.parking_symbol || "P")}</div>`;
    }

    function parseSpotCode(spotCode, fallbackZoneCode) {
      const zoneMatch = String(fallbackZoneCode || "").match(/^([A-Za-z]\\d+)-([A-Za-z]+)$/);
      const cameraZoneMatch = String(spotCode).match(/^([A-Za-z]\\d+)-([A-Za-z]+)-(\\d+)-(\\d+)$/);
      if (cameraZoneMatch) {
        return {
          levelCode: cameraZoneMatch[1],
          sectorCode: cameraZoneMatch[2],
          cameraZoneNumber: cameraZoneMatch[3],
          spotNumber: cameraZoneMatch[4],
          displaySpotNumber: `${cameraZoneMatch[3]}-${cameraZoneMatch[4]}`,
          zoneCode: `${cameraZoneMatch[1]}-${cameraZoneMatch[2]}`,
          cameraZoneCode: `${cameraZoneMatch[1]}-${cameraZoneMatch[2]}-${cameraZoneMatch[3]}`,
        };
      }

      if (zoneMatch) {
        return {
          levelCode: zoneMatch[1],
          sectorCode: zoneMatch[2],
          cameraZoneNumber: "UNKNOWN",
          spotNumber: spotCode,
          displaySpotNumber: spotCode,
          zoneCode: `${zoneMatch[1]}-${zoneMatch[2]}`,
          cameraZoneCode: `${zoneMatch[1]}-${zoneMatch[2]}`,
        };
      }
      return {
        levelCode: "UNKNOWN",
        sectorCode: fallbackZoneCode || "UNKNOWN",
        cameraZoneNumber: "UNKNOWN",
        spotNumber: spotCode,
        displaySpotNumber: spotCode,
        zoneCode: fallbackZoneCode || "UNKNOWN",
        cameraZoneCode: fallbackZoneCode || "UNKNOWN",
      };
    }

    function renderDisplays(items) {
      if (!items.length) {
        displayGrid.innerHTML = '<div class="empty">Нет активных сообщений табло</div>';
        displayCount.textContent = "0 табло";
        summary.textContent = "0 табло";
        return;
      }

      summary.textContent = countText(items.length, "табло", "табло", "табло");
      displayCount.textContent = summary.textContent;
      displayGrid.innerHTML = items.map((item) => {
        const isFull = item.arrow_direction === "FULL" || item.free_spots === 0;
        return `
          <article class="display ${isFull ? "full" : ""}">
            <div class="display-header">
              <span class="code">${escapeHtml(item.display_code)}</span>
              <span class="zone">${escapeHtml(item.sector_code)}</span>
            </div>
            <div class="led-face">
              <div class="arrow">${arrowSymbolHtml(item.arrow_direction)}</div>
              <div class="count">${escapeHtml(item.free_spots)}</div>
              ${parkingSymbolHtml(item)}
            </div>
            <div class="meta">
              <span class="pill">${escapeHtml(displayPillText(item))}</span>
            </div>
          </article>
        `;
      }).join("");
    }

    function renderEntryDisplay(entry) {
      const lines = entry.lines || [];
      if (!lines.length) {
        entryDisplay.innerHTML = '<div class="empty">Нет строк для въездного табло</div>';
        entryCount.textContent = "0 строк";
        return;
      }

      entryCount.textContent = countText(lines.length, "строка", "строки", "строк");
      entryDisplay.innerHTML = `
        <article class="display entry-display">
          <div class="display-header">
            <span class="code">${escapeHtml(entry.display_code)}</span>
            <span class="zone">ВЪЕЗД</span>
          </div>
          <div class="led-face">
            <div class="entry-lines">
              ${lines.map((line) => `<div class="entry-line">${escapeHtml(line)}</div>`).join("")}
            </div>
            <div class="entry-total">${escapeHtml(entry.free_spots)} свободно всего</div>
          </div>
          <div class="meta">
            <span class="pill">${escapeHtml(entry.title)}</span>
          </div>
        </article>
      `;
    }

    function groupSpots(items) {
      return items.reduce((levels, spot) => {
        const parsed = parseSpotCode(spot.spot_code, spot.sector_code);
        const enrichedSpot = { ...spot, ...parsed };
        levels[parsed.levelCode] ??= {};
        levels[parsed.levelCode][parsed.zoneCode] ??= [];
        levels[parsed.levelCode][parsed.zoneCode].push(enrichedSpot);
        return levels;
      }, {});
    }

    function renderParkingMap(items) {
      const activeItems = items.filter((spot) => spot.is_active);
      if (!activeItems.length) {
        mapGrid.innerHTML = '<div class="empty">Нет парковочных мест</div>';
        spotCount.textContent = "0 мест";
        return;
      }

      spotCount.textContent = countText(activeItems.length, "место", "места", "мест");
      const levels = groupSpots(activeItems);
      mapGrid.innerHTML = Object.entries(levels).sort(([a], [b]) => a.localeCompare(b)).map(([levelCode, zones]) => {
        const zoneMarkup = Object.entries(zones).sort(([a], [b]) => a.localeCompare(b)).map(([zoneCode, zoneSpots]) => {
          const free = zoneSpots.filter((spot) => spot.status === "FREE").length;
          const occupied = zoneSpots.filter((spot) => spot.status === "OCCUPIED").length;
          const zoneParts = zoneCode.split("-");
          const zoneLabel = zoneParts[zoneParts.length - 1];
          const sortedSpots = [...zoneSpots].sort((a, b) => {
            const cameraZoneCompare = String(a.cameraZoneNumber).localeCompare(String(b.cameraZoneNumber), undefined, { numeric: true });
            if (cameraZoneCompare !== 0) {
              return cameraZoneCompare;
            }
            return String(a.spotNumber).localeCompare(String(b.spotNumber), undefined, { numeric: true });
          });
          const spotMarkup = sortedSpots.map((spot) => `
            <div class="spot ${statusClass(spot.status)} ${spot.is_disabled ? "disabled" : ""}" title="${escapeHtml(spot.spot_code)} ${escapeHtml(statusLabel(spot.status))}${spot.is_disabled ? " место для инвалидов" : ""}">
              <div class="spot-code">${escapeHtml(spot.displaySpotNumber)}</div>
              ${spot.is_disabled ? '<div class="spot-badge" aria-label="Место для инвалидов">♿</div>' : ""}
              <div class="spot-status">${escapeHtml(statusLabel(spot.status))}</div>
            </div>
          `).join("");
          return `
            <article class="zone-card">
              <div class="zone-card-header">
                <div class="zone-card-title">Сектор ${escapeHtml(zoneLabel)}</div>
                <div class="zone-card-counts">${free} свободно / ${occupied} занято / ${zoneSpots.length} всего</div>
              </div>
              <div class="spots">
                ${spotMarkup}
              </div>
            </article>
          `;
        }).join("");

        return `
          <article class="level-card">
            <div class="level-title">Этаж ${escapeHtml(levelCode)}</div>
            <div class="zone-stack">
              ${zoneMarkup}
            </div>
          </article>
        `;
      }).join("");
    }

    async function refresh() {
      try {
        const [entryResponse, displayResponse, spotsResponse] = await Promise.all([
          fetch("/api/v1/displays/entry-message", { cache: "no-store" }),
          fetch("/api/v1/displays/messages?is_active=true", { cache: "no-store" }),
          fetch("/api/v1/spots", { cache: "no-store" }),
        ]);
        if (!entryResponse.ok) {
          throw new Error(`въездное табло HTTP ${entryResponse.status}`);
        }
        if (!displayResponse.ok) {
          throw new Error(`табло HTTP ${displayResponse.status}`);
        }
        if (!spotsResponse.ok) {
          throw new Error(`парковочные места HTTP ${spotsResponse.status}`);
        }
        const entryData = await entryResponse.json();
        const displayData = await displayResponse.json();
        const spotsData = await spotsResponse.json();
        renderEntryDisplay(entryData);
        renderDisplays(displayData.items || []);
        renderParkingMap(spotsData.items || []);
        updated.textContent = `Обновлено ${new Date().toLocaleTimeString("ru-RU")}`;
      } catch (error) {
        summary.textContent = "Ошибка подключения";
        updated.textContent = error.message;
      }
    }

    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>
"""
