// PGS admin enhancements: dark theme + colored status badges in list tables.
// Loaded from app/templates/base.html. Pure DOM cosmetics — does not touch the
// data DataTables sends to the server, so sorting/search stay intact.
(function () {
  "use strict";

  // Map raw stored status values -> Russian label + badge class.
  // Spot statuses (FREE/OCCUPIED/OFFLINE/UNKNOWN) and LED command statuses
  // (PENDING/SENT/FAILED) are the only values that ever fill a whole cell.
  var STATUS = {
    FREE: { ru: "Свободно", cls: "pgs-badge pgs-badge--free" },
    OCCUPIED: { ru: "Занято", cls: "pgs-badge pgs-badge--occupied" },
    OFFLINE: { ru: "Офлайн", cls: "pgs-badge pgs-badge--offline" },
    UNKNOWN: { ru: "Неизвестно", cls: "pgs-badge pgs-badge--unknown" },
    PENDING: { ru: "Ожидает", cls: "pgs-badge pgs-badge--pending" },
    SENT: { ru: "Отправлено", cls: "pgs-badge pgs-badge--sent" },
    FAILED: { ru: "Ошибка", cls: "pgs-badge pgs-badge--failed" }
  };

  function ensureDarkTheme() {
    document.documentElement.setAttribute("data-bs-theme", "dark");
  }

  function decorate() {
    var cells = document.querySelectorAll("td:not([data-pgs-badged])");
    for (var i = 0; i < cells.length; i++) {
      var td = cells[i];
      var text = (td.textContent || "").trim();
      var meta = STATUS[text];
      if (!meta) {
        continue;
      }
      td.setAttribute("data-pgs-badged", "1");
      var span = document.createElement("span");
      span.className = meta.cls;
      span.textContent = meta.ru;
      span.title = text;
      td.textContent = "";
      td.appendChild(span);
    }
  }

  function init() {
    ensureDarkTheme();
    decorate();

    if (!window.MutationObserver) {
      return;
    }
    // DataTables rebuilds rows on every redraw (pagination/search/sort), wiping
    // our badges. Re-decorate after each mutation; disconnect while we mutate so
    // our own appendChild calls don't retrigger the observer in a loop.
    var observer = new MutationObserver(function () {
      observer.disconnect();
      decorate();
      observer.observe(document.body, { childList: true, subtree: true });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Set the theme attribute as early as possible to avoid a light-theme flash.
  ensureDarkTheme();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
