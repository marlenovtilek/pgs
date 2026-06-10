LED_SIMULATOR_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PGS LED-симулятор</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0c0d10;
      --text: #f5f7fb;
      --muted: #aeb6c2;
      --green: #38ff74;
      --red: #ff3b3b;
      --amber: #ffb43a;
      --blue: #69a7ff;
      --edge: #30343a;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(1200px 600px at 50% -10%, #16181d, var(--bg));
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 3;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 56px;
      padding: 12px 20px;
      border-bottom: 1px solid #23262b;
      background: rgba(12, 13, 16, 0.94);
      backdrop-filter: blur(8px);
    }

    .brand { display: flex; align-items: baseline; gap: 12px; min-width: 0; }
    h1 { margin: 0; font-size: 18px; line-height: 1.2; font-weight: 800; white-space: nowrap; }
    .status { color: var(--muted); font-size: 13px; white-space: nowrap; }

    .wrap { width: min(1240px, 100%); margin: 0 auto; padding: 22px 20px 48px; }
    .intro { margin: 0 0 22px; color: var(--muted); font-size: 14px; line-height: 1.5; max-width: 92ch; }

    .section { margin-bottom: 30px; }
    .section-title {
      display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
      margin: 0 0 14px; color: #dfe6ee; font-size: 15px; font-weight: 700;
    }

    /* ---- Hardware casing + LED screen (shared) ---- */
    .casing {
      position: relative;
      border-radius: 16px;
      border: 1px solid #000;
      padding: 16px;
      background:
        radial-gradient(circle at 13px 13px, #3a3d42 1.5px, transparent 2.6px),
        radial-gradient(circle at calc(100% - 13px) 13px, #3a3d42 1.5px, transparent 2.6px),
        radial-gradient(circle at 13px calc(100% - 13px), #3a3d42 1.5px, transparent 2.6px),
        radial-gradient(circle at calc(100% - 13px) calc(100% - 13px), #3a3d42 1.5px, transparent 2.6px),
        linear-gradient(160deg, #2b2e33, #15171a 55%, #0a0b0c);
      box-shadow: 0 20px 44px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.06);
    }

    .screen {
      position: relative;
      border-radius: 9px;
      border: 1px solid #1b1f24;
      box-shadow: inset 0 0 0 2px #000, inset 0 0 34px rgba(0, 0, 0, 0.92);
      overflow: hidden;
    }

    .matrix {
      background:
        radial-gradient(circle at center, rgba(255, 255, 255, 0.05) 1px, transparent 1.4px) 0 0 / 6px 6px,
        #050606;
    }

    .matrix::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.16) 0 1px, transparent 1px 3px);
    }

    .led {
      font-family: "Arial Black", Impact, ui-sans-serif, system-ui, sans-serif;
      text-transform: uppercase;
      text-shadow: 0 0 18px currentColor;
      letter-spacing: 0;
    }

    .plate {
      display: flex; align-items: center; justify-content: space-between; gap: 10px;
      margin-bottom: 12px; padding: 4px 4px 10px;
      color: var(--muted); font-size: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .plate .sector { color: var(--blue); font-weight: 700; }

    /* ---- Entry board (big outdoor sign) ---- */
    .entry-board .screen { padding: 22px 26px; }
    .board-caption {
      color: var(--amber); font-size: clamp(13px, 1.6vw, 18px); letter-spacing: 2px;
      margin-bottom: 16px; opacity: 0.92;
    }
    .board-rows { display: grid; gap: 12px; }
    .board-row {
      display: flex; align-items: baseline; justify-content: space-between; gap: 24px;
      border-bottom: 1px dashed rgba(255, 180, 58, 0.14); padding-bottom: 10px;
    }
    .board-row:last-child { border-bottom: 0; }
    .row-code { color: var(--amber); font-size: clamp(30px, 5vw, 60px); line-height: 1; }
    .row-count { color: var(--green); font-size: clamp(34px, 6vw, 70px); line-height: 1; }
    .board-row.zero .row-count { color: var(--red); }
    .board-total {
      margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--muted); font-size: clamp(14px, 1.8vw, 20px);
    }
    .board-total b { color: var(--green); font-size: 1.5em; }

    /* ---- Navigation signs (small parking displays) ---- */
    .signs { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }
    .sign .screen {
      display: grid; grid-template-columns: auto minmax(70px, 1fr) auto; align-items: center;
      gap: 14px; padding: 22px 18px; min-height: 150px;
    }
    .sign-foot {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      margin-top: 12px; color: var(--muted); font-size: 13px;
    }
    .sign-arrow {
      min-width: 70px; text-align: center; color: var(--green);
      font-size: clamp(58px, 9vw, 104px); line-height: 0.85;
    }
    .sign-count {
      min-width: 0; text-align: center; color: var(--green);
      font-size: clamp(58px, 9vw, 104px); line-height: 0.85;
    }
    .sign-p {
      min-width: 58px; text-align: center; color: var(--blue);
      font-size: clamp(40px, 6vw, 72px); line-height: 0.9;
      border: 1px solid rgba(105, 167, 255, 0.5);
      box-shadow: inset 0 0 18px rgba(105, 167, 255, 0.18);
      padding: 10px 8px; border-radius: 4px;
    }
    .sign.full .sign-arrow,
    .sign.full .sign-count { color: var(--red); }
    .sign.full .sign-foot { color: var(--red); }

    .empty {
      min-height: 150px; display: grid; place-items: center; text-align: center; padding: 24px;
      color: var(--muted); border: 1px dashed #343941; border-radius: 12px;
    }

    /* ---- Parking map (secondary, collapsible) ---- */
    .map { border: 1px solid #23262b; border-radius: 12px; background: #121317; }
    .map > summary {
      cursor: pointer; list-style: none; padding: 14px 16px;
      display: flex; align-items: baseline; justify-content: space-between; gap: 12px;
      color: #dfe6ee; font-size: 15px; font-weight: 700;
    }
    .map > summary::-webkit-details-marker { display: none; }
    .map > summary::before { content: "\\25b8"; color: var(--muted); margin-right: 8px; }
    .map[open] > summary::before { content: "\\25be"; }
    .map-body { padding: 4px 16px 16px; }

    .legend {
      display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 0 0 14px;
      padding: 10px 14px; border: 1px solid var(--edge); border-radius: 8px; background: #15171b;
    }
    .legend-item { display: flex; align-items: center; gap: 8px; color: #dce3ea; font-size: 12px; white-space: nowrap; }
    .swatch { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #30343a; flex: 0 0 auto; }
    .swatch.free { background: rgba(56, 255, 116, 0.22); border-color: rgba(56, 255, 116, 0.6); }
    .swatch.occupied { background: rgba(255, 59, 59, 0.22); border-color: rgba(255, 59, 59, 0.6); }
    .swatch.unknown { background: rgba(255, 180, 58, 0.22); border-color: rgba(255, 180, 58, 0.6); }
    .swatch.offline { background: #0b0c0e; opacity: 0.55; }
    .swatch-badge { flex: 0 0 auto; color: var(--blue); font-size: 15px; line-height: 1; text-shadow: 0 0 10px currentColor; }

    .level-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
    .level-card { border: 1px solid var(--edge); border-radius: 8px; background: #15171b; padding: 14px; min-width: 0; }
    .level-title { margin-bottom: 12px; color: var(--amber); font-size: 18px; font-weight: 900; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .zone-stack { display: flex; flex-direction: column; gap: 12px; }
    .zone-card { border: 1px solid #2b3036; border-radius: 8px; background: #101216; padding: 12px; min-width: 0; }
    .zone-card-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
    .zone-card-title { color: var(--blue); font-size: 16px; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .zone-card-counts { color: var(--muted); font-size: 12px; white-space: nowrap; }
    .spots { display: grid; grid-template-columns: repeat(auto-fill, minmax(66px, 1fr)); gap: 6px; }
    .spot {
      min-height: 40px; border: 1px solid #30343a; border-radius: 6px; background: #0b0c0e;
      padding: 6px 6px; display: grid; grid-template-columns: 1fr auto; align-content: center; gap: 3px; overflow: hidden;
    }
    .spot-code { color: #f2f6fb; font-size: 11px; line-height: 1; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .spot-status { font-size: 10px; line-height: 1; font-weight: 800; grid-column: 1 / -1; }
    .spot-badge { color: var(--blue); font-size: 13px; line-height: 1; font-weight: 900; text-shadow: 0 0 10px currentColor; }
    .spot.disabled { border-color: rgba(105, 167, 255, 0.7); box-shadow: inset 0 0 16px rgba(105, 167, 255, 0.12); }
    .spot.free { border-color: rgba(56, 255, 116, 0.45); box-shadow: inset 0 0 14px rgba(56, 255, 116, 0.08); }
    .spot.free .spot-status { color: var(--green); }
    .spot.occupied { border-color: rgba(255, 59, 59, 0.5); box-shadow: inset 0 0 14px rgba(255, 59, 59, 0.08); }
    .spot.occupied .spot-status { color: var(--red); }
    .spot.unknown { border-color: rgba(255, 180, 58, 0.45); }
    .spot.unknown .spot-status { color: var(--amber); }
    .spot.offline { opacity: 0.58; }
    .spot.offline .spot-status { color: var(--muted); }

    @media (max-width: 560px) {
      .topbar { align-items: flex-start; flex-direction: column; }
      .status { white-space: normal; }
      .wrap { padding: 14px; }
      .signs { grid-template-columns: 1fr; }
      .level-grid { grid-template-columns: 1fr; }
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
      Так выглядят LED-табло парковки прямо сейчас — копия реальных экранов.
      Данные берутся из PGS и обновляются автоматически каждые 2 секунды.
    </p>

    <section class="section">
      <h2 class="section-title">
        <span>Въездное табло</span>
        <span class="status" id="entryCount">0 строк</span>
      </h2>
      <div id="entryDisplay" aria-live="polite"></div>
    </section>

    <section class="section">
      <h2 class="section-title">
        <span>Навигационные табло на развилках</span>
        <span class="status" id="displayCount">0 табло</span>
      </h2>
      <div class="signs" id="displayGrid" aria-live="polite"></div>
    </section>

    <section class="section">
      <details class="map" id="mapDetails" open>
        <summary>
          <span>Схема мест</span>
          <span class="status" id="spotCount">0 мест</span>
        </summary>
        <div class="map-body">
          <div class="legend">
            <span class="legend-item"><span class="swatch free"></span>свободно</span>
            <span class="legend-item"><span class="swatch occupied"></span>занято</span>
            <span class="legend-item"><span class="swatch unknown"></span>неизвестно</span>
            <span class="legend-item"><span class="swatch offline"></span>офлайн (нет связи с камерой)</span>
            <span class="legend-item"><span class="swatch-badge">&#9855;</span>место для инвалидов</span>
          </div>
          <div class="level-grid" id="mapGrid" aria-live="polite"></div>
        </div>
      </details>
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
      if (abs > 10 && abs < 20) return many;
      if (last === 1) return one;
      if (last >= 2 && last <= 4) return few;
      return many;
    }

    function countText(count, one, few, many) {
      return `${count} ${pluralRu(count, one, few, many)}`;
    }

    function directionLabel(direction) {
      if (direction === "LEFT") return "налево";
      if (direction === "RIGHT") return "направо";
      if (direction === "AHEAD") return "прямо";
      if (direction === "FULL") return "нет мест";
      return String(direction || "");
    }

    function statusLabel(status) {
      if (status === "FREE") return "СВОБОДНО";
      if (status === "OCCUPIED") return "ЗАНЯТО";
      if (status === "OFFLINE") return "ОФЛАЙН";
      if (status === "UNKNOWN") return "НЕИЗВЕСТНО";
      return String(status || "");
    }

    function arrowSymbolHtml(direction) {
      if (direction === "LEFT") return "&#8592;";
      if (direction === "RIGHT") return "&#8594;";
      if (direction === "AHEAD") return "&#8593;";
      if (direction === "FULL") return "";
      return escapeHtml(direction || "");
    }

    function parkingSymbolHtml(item) {
      if (item.arrow_direction === "FULL") return "";
      return `<div class="sign-p led">${escapeHtml(item.parking_symbol || "P")}</div>`;
    }

    function splitEntryLine(line) {
      const text = String(line).trim();
      const index = text.lastIndexOf(" ");
      if (index === -1) return { code: text, count: "" };
      return { code: text.slice(0, index), count: text.slice(index + 1) };
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

    function renderEntryDisplay(entry) {
      const lines = entry.lines || [];
      if (!lines.length) {
        entryDisplay.innerHTML = '<div class="empty">Нет данных для въездного табло</div>';
        entryCount.textContent = "0 строк";
        return;
      }
      entryCount.textContent = countText(lines.length, "сектор", "сектора", "секторов");
      const rows = lines.map((line) => {
        const { code, count } = splitEntryLine(line);
        const zero = String(count).trim() === "0";
        return `
          <div class="board-row ${zero ? "zero" : ""}">
            <span class="row-code led">${escapeHtml(code)}</span>
            <span class="row-count led">${escapeHtml(count)}</span>
          </div>`;
      }).join("");
      entryDisplay.innerHTML = `
        <div class="entry-board">
          <div class="casing">
            <div class="plate">
              <span>${escapeHtml(entry.display_code)}</span>
              <span class="sector">ВЪЕЗД</span>
            </div>
            <div class="screen matrix">
              <div class="board-caption led">Свободные места</div>
              <div class="board-rows">${rows}</div>
              <div class="board-total">Всего свободно <b class="led">${escapeHtml(entry.free_spots)}</b></div>
            </div>
          </div>
        </div>`;
    }

    function renderDisplays(items) {
      if (!items.length) {
        displayGrid.innerHTML = '<div class="empty">Нет активных табло</div>';
        displayCount.textContent = "0 табло";
        summary.textContent = "0 табло";
        return;
      }
      summary.textContent = countText(items.length, "табло", "табло", "табло");
      displayCount.textContent = summary.textContent;
      displayGrid.innerHTML = items.map((item) => {
        const isFull = item.arrow_direction === "FULL" || item.free_spots === 0;
        return `
          <article class="sign ${isFull ? "full" : ""}">
            <div class="casing">
              <div class="plate">
                <span>${escapeHtml(item.display_code)}</span>
                <span class="sector">${escapeHtml(item.sector_code)}</span>
              </div>
              <div class="screen matrix">
                <div class="sign-arrow led">${arrowSymbolHtml(item.arrow_direction)}</div>
                <div class="sign-count led">${escapeHtml(item.free_spots)}</div>
                ${parkingSymbolHtml(item)}
              </div>
              <div class="sign-foot">
                <span>${escapeHtml(directionLabel(item.arrow_direction))}</span>
                <span>${escapeHtml(item.free_spots)} ${escapeHtml(pluralRu(item.free_spots, "место", "места", "мест"))}</span>
              </div>
            </div>
          </article>`;
      }).join("");
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
            if (cameraZoneCompare !== 0) return cameraZoneCompare;
            return String(a.spotNumber).localeCompare(String(b.spotNumber), undefined, { numeric: true });
          });
          const spotMarkup = sortedSpots.map((spot) => `
            <div class="spot ${statusClass(spot.status)} ${spot.is_disabled ? "disabled" : ""}" title="${escapeHtml(spot.spot_code)} ${escapeHtml(statusLabel(spot.status))}${spot.is_disabled ? " место для инвалидов" : ""}">
              <div class="spot-code">${escapeHtml(spot.displaySpotNumber)}</div>
              ${spot.is_disabled ? '<div class="spot-badge" aria-label="Место для инвалидов">&#9855;</div>' : ""}
              <div class="spot-status">${escapeHtml(statusLabel(spot.status))}</div>
            </div>
          `).join("");
          return `
            <article class="zone-card">
              <div class="zone-card-header">
                <div class="zone-card-title">Сектор ${escapeHtml(zoneLabel)}</div>
                <div class="zone-card-counts">${free} своб. / ${occupied} занято / ${zoneSpots.length} всего</div>
              </div>
              <div class="spots">${spotMarkup}</div>
            </article>`;
        }).join("");
        return `
          <article class="level-card">
            <div class="level-title">Этаж ${escapeHtml(levelCode)}</div>
            <div class="zone-stack">${zoneMarkup}</div>
          </article>`;
      }).join("");
    }

    async function refresh() {
      try {
        const [entryResponse, displayResponse, spotsResponse] = await Promise.all([
          fetch("/api/v1/displays/entry-message", { cache: "no-store" }),
          fetch("/api/v1/displays/messages?is_active=true", { cache: "no-store" }),
          fetch("/api/v1/spots", { cache: "no-store" }),
        ]);
        if (!entryResponse.ok) throw new Error(`въездное табло HTTP ${entryResponse.status}`);
        if (!displayResponse.ok) throw new Error(`табло HTTP ${displayResponse.status}`);
        if (!spotsResponse.ok) throw new Error(`парковочные места HTTP ${spotsResponse.status}`);
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
