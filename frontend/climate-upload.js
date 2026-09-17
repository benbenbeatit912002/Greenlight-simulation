/* Weather import is validated in memory. Selecting the explicit action can stage it for the full model. */
(function () {
  "use strict";
  const MAX_BYTES = 2 * 1024 * 1024;
  const MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const copy = {
    en: {
      title: "Import your outdoor weather",
      intro: "Check an Excel workbook before connecting it to a greenhouse model.",
      stage: "Step 1 · Validate and run",
      template: "Download Excel template",
      file: "Weather workbook (.xlsx)",
      check: "Check weather data",
      checking: "Checking workbook…",
      privacy:
        "Checked on this computer, in memory only. The workbook is not saved or uploaded to GitHub.",
      limits:
        "Up to 2 MiB and 10,000 records. Amsterdam's nine columns, one row every 300 seconds. Values only, no formulas.",
      empty: "Choose a workbook to see its coverage, ranges and first five records.",
      valid: "Data checks passed · preview only",
      ready: "Data checks passed · ready to initialize GreenLight",
      unchanged:
        "The workbook is checked in memory and converted for the model. Select Run with this weather to initialize a full GreenLight simulation.",
      useWeather: "Run with this weather",
      failed: "Could not validate this workbook",
      select: "Choose a nonempty .xlsx workbook no larger than 2 MiB.",
      unavailable:
        "The local server could not check the file. Start the updated Python server and try again.",
      timeout: "The check timed out. Try a smaller workbook or retry.",
      rows: "Records",
      interval: "Interval (minutes)",
      start: "Start (source time)",
      end: "End (source time)",
      preview: "First five records",
      additional: "Missing additional model columns",
      none: "None — model compatibility still needs verification.",
      noFill: "No values were filled, interpolated or assumed.",
      issue: "Data issues (up to 30)",
      row: "Row",
      column: "Column",
      reason: "Details",
      minmax: "Observed input ranges",
      minimum: "Minimum",
      maximum: "Maximum",
      hash: "Workbook SHA-256",
      scroll: "Scroll tables horizontally to see every column.",
      windowTitle: "Step 2 · Simulation dates",
      windowYear: "Weather source year",
      windowConvention: "Clock used in your file",
      windowChoose: "Choose a time convention",
      windowLocal: "Local standard time (fixed clock, no daylight saving)",
      windowUtc: "UTC",
      windowStart: "Simulation start",
      windowEnd: "Simulation end (exclusive)",
      windowSourceRange: "Uploaded weather coverage",
      windowUsableRange: "Selectable simulation range",
      windowHours: "hours",
      windowSteps: "steps",
      windowYearError: "Enter the actual weather source year (1900–2100).",
      windowConventionError: "Choose the clock convention used in the weather file.",
      windowYearCoverageError:
        "The weather exceeds this source year. Check the year and leap-day data.",
      windowGridError: "Choose start and end times on 15-minute boundaries.",
      windowOrderError: "End must be at least 15 minutes after start.",
      windowCoverageError:
        "Stay inside the selectable range; complete day context and 12-hour look-ahead must be uploaded.",
      windowAssumptions:
        "Initialization uses the applied greenhouse/initial-state settings at the selected start; unspecified states use GreenLight defaults, with 0 hours of warm-up. Upload each simulated day's midnight-to-midnight weather and at least 12 hours after the chosen end. No missing weather is filled. Each physical step stays at 15 minutes.",
      windowInitializing: "Initializing the selected simulation…",
      windowInitialized: "Selected window initialized. Press Start simulation to run.",
      tutorialTitle: "Excel tutorial — match Amsterdam/2010.csv",
      tutorialDownload:
        "1. Download the template. Keep the Weather sheet and replace every synthetic example row with your own outdoor measurements. Instructions is optional.",
      tutorialHeaders:
        "2. Keep the nine row-1 headers exactly as shown below, in the same order. Spaces, capitalization and the literal ?? header matter.",
      tutorialTime:
        "3. time is numeric seconds since the start of the source year: 0, 300, 600… Each row is 5 minutes. A selected continuous window may start later in the year. The source has no timezone column; do not silently convert to UTC or apply daylight saving.",
      tutorialValues:
        "4. Enter numeric values only. RH=86 means 86%, not an Excel 0.86 fraction. Radiation is instantaneous global irradiance (W/m²), not PAR or accumulated energy. No blank rows, formulas or missing values.",
      tutorialPreview:
        "5. Save as .xlsx and click Check weather data. Upload at most 10,000 rows (about 34 days), not the whole year. Provide at least 36 hours so the full model can keep its 0.5-day look-ahead, then select Run with this weather.",
      tutorialColumns: "Exact Amsterdam CSV column order",
      tutorialUnit: "Unit",
      tutorialUse: "Current GreenLight loader behavior",
      useTime: "Time base and soil-temperature estimate",
      useRadiation: "Outdoor global radiation input",
      useWind: "Outdoor wind input",
      useAir: "Outdoor air-temperature input",
      useSky: "Effective sky-temperature input",
      useUnknown:
        "Unknown source column. Retained for format compatibility, not consumed by the loader. Do not interpret it as soil temperature.",
      useCo2:
        "Consumed by the uploaded-weather converter as outdoor CO2. Built-in Amsterdam loading retains the upstream 400 ppm assumption.",
      useDay: "Retained but not consumed; time supplies the time base.",
      useRh: "Outdoor RH, converted to vapor pressure",
      tutorialAssumptions:
        "The full uploaded-weather path consumes CO2 concentration and estimates soil temperature with soilTempNl(time). Built-in Amsterdam loading keeps the upstream 400 ppm assumption. Matching the file format does not establish accuracy for another greenhouse.",
      tutorialSource:
        "Reference: gl_gym/data/weather/Amsterdam/2010.csv and gl_gym/environments/utils.py (load_weather_data). The template uses synthetic examples; it does not publish the protected weather dataset.",
    },
    zh: {
      title: "匯入你的室外氣候",
      intro: "檢查 Excel 氣候資料，通過後可接入完整 GreenLight 模型。",
      stage: "第一階段 · 檢查並執行",
      template: "下載 Excel 範本",
      file: "氣候資料檔案（.xlsx）",
      check: "檢查氣候資料",
      checking: "正在檢查檔案…",
      privacy: "只在這台電腦的記憶體中檢查，不儲存檔案，也不會上傳 GitHub。",
      limits:
        "上限 2 MiB、10,000 筆。使用 Amsterdam 的 9 欄格式，每 300 秒一筆。只接受數值，不接受公式。",
      empty: "選擇檔案後，可查看涵蓋時間、數值範圍與前五筆資料。",
      valid: "資料檢查通過 · 僅供預覽",
      ready: "資料檢查通過 · 可以初始化 GreenLight",
      unchanged:
        "檔案已在記憶體中檢查並轉換。按下「使用這份天氣模擬」後，才會初始化完整 GreenLight 模型。",
      useWeather: "使用這份天氣模擬",
      failed: "這份檔案未通過檢查",
      select: "請選擇非空白、大小不超過 2 MiB 的 .xlsx 檔案。",
      unavailable: "本機伺服器無法檢查檔案，請確認已啟動更新後的 Python 伺服器。",
      timeout: "檢查逾時，請使用較小檔案或重試。",
      rows: "資料筆數",
      interval: "間隔（分鐘）",
      start: "開始（來源時間）",
      end: "結束（來源時間）",
      preview: "前五筆資料",
      additional: "缺少的額外模型欄位",
      none: "無，但仍需驗證模型相容性。",
      noFill: "沒有自動補值、插值或假設資料。",
      issue: "資料問題（最多顯示 30 項）",
      row: "Excel 列",
      column: "欄位",
      reason: "詳細原因",
      minmax: "輸入數值範圍",
      minimum: "最小值",
      maximum: "最大值",
      hash: "檔案 SHA-256",
      scroll: "表格可左右滑動，查看全部欄位。",
      windowTitle: "第二階段 · 模擬起訖時間",
      windowYear: "氣候資料的實際年份",
      windowConvention: "檔案使用的時間基準",
      windowChoose: "請選擇時間基準",
      windowLocal: "當地標準時間（固定時鐘，不套用夏令時間）",
      windowUtc: "UTC",
      windowStart: "開始時間",
      windowEnd: "結束時間（不含終點之後的區間）",
      windowSourceRange: "上傳氣候涵蓋範圍",
      windowUsableRange: "可選模擬範圍",
      windowHours: "小時",
      windowSteps: "步",
      windowYearError: "請填氣候資料的實際年份（1900–2100）。",
      windowConventionError: "請選擇氣候檔案使用的時間基準。",
      windowYearCoverageError: "資料超出所選年份，請確認年份與閏日資料。",
      windowGridError: "開始與結束時間必須對齊每 15 分鐘。",
      windowOrderError: "結束時間必須比開始時間晚至少 15 分鐘。",
      windowCoverageError: "請選在可用範圍內；必須包含整日資料與結束後 12 小時的前瞻氣候。",
      windowAssumptions:
        "初始化：在所選開始時間使用已套用的溫室／初始狀態設定，未指定者沿用 GreenLight 預設值；暖機為 0 小時。需每個模擬日期從午夜到下一午夜的資料，另需結束後至少 12 小時。缺少的氣候不會補造，每步固定 15 分鐘。",
      windowInitializing: "正在初始化所選模擬區間…",
      windowInitialized: "區間已初始化，按「開始模擬」即可執行。",
      tutorialTitle: "Excel 格式教學（與 Amsterdam/2010.csv 對齊）",
      tutorialDownload:
        "1. 下載範本。保留 Weather 工作表，將全部合成範例列換成你的室外量測資料。Instructions 工作表可保留。",
      tutorialHeaders:
        "2. 第一列必須使用下方 9 個欄名，順序、空格與大小寫完全一致。?? 也是原始欄名，請保留。",
      tutorialTime:
        "3. time 是從資料年份年初起算的秒數：0、300、600……每筆間隔 5 分鐘。可選擇年內較晚開始的連續區段。原始資料沒有時區欄，不應自行轉為 UTC 或套用夏令時間。",
      tutorialValues:
        "4. 只貼上數值。RH=86 代表 86%，不是 Excel 的 0.86。輻射是即時全球輻照度（W/m²），不是 PAR 或累積能量。不可有空白列、公式或缺值。",
      tutorialPreview:
        "5. 存成 .xlsx，按「檢查氣候資料」。最多 10,000 筆（約 34 天），不要上傳整年。請提供至少 36 小時，讓完整模型保留 0.5 天的前瞻資料，再按「使用這份天氣模擬」。",
      tutorialColumns: "Amsterdam CSV 原始欄位順序",
      tutorialUnit: "單位",
      tutorialUse: "目前 GreenLight 讀取程式的處理",
      useTime: "時間基準與土壤溫度估算",
      useRadiation: "室外全球輻射輸入",
      useWind: "室外風速輸入",
      useAir: "室外空氣溫度輸入",
      useSky: "有效天空溫度輸入",
      useUnknown: "原始欄位意義未明，保留格式但讀取程式未使用。不能當成土壤溫度。",
      useCo2: "自訂氣候模型會讀取室外 CO₂。內建 Amsterdam 讀取路徑仍採用上游固定 400 ppm 假設。",
      useDay: "保留但目前未讀取，時間基準使用 time。",
      useRh: "室外相對濕度，轉換為水氣壓力",
      tutorialAssumptions:
        "自訂氣候路徑會讀取 CO₂，並使用 soilTempNl(time) 估算土壤溫度；內建 Amsterdam 路徑仍採用上游固定 400 ppm 假設。格式相同不代表已針對另一座溫室校正。",
      tutorialSource:
        "參考 gl_gym/data/weather/Amsterdam/2010.csv 與 gl_gym/environments/utils.py 的 load_weather_data。範本是合成範例，不會公開受保護的氣候資料。",
    },
  };
  function validateFile(file) {
    return Boolean(file && /\.xlsx$/i.test(file.name) && file.size > 0 && file.size <= MAX_BYTES);
  }
  if (typeof module !== "undefined" && module.exports)
    module.exports = { validateFile, MAX_BYTES, copy };
  if (typeof document === "undefined") return;
  const panel = document.getElementById("weatherImport");
  if (!panel) return;
  const form = document.getElementById("weatherUploadForm");
  const fileInput = document.getElementById("weatherFile");
  const button = document.getElementById("weatherCheckButton");
  const status = document.getElementById("weatherUploadStatus");
  const output = document.getElementById("weatherPreview");
  let busy = false;
  let result = null;
  let error = null;
  let activating = false;
  let activationMessage = "";
  let windowInput = { year: "", convention: "", start: "", end: "" };
  const t = (key) => copy[document.documentElement.lang.startsWith("zh") ? "zh" : "en"][key];
  function node(tag, text) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = String(text);
    return element;
  }
  function table(title, columns, rows) {
    const wrapper = node("div");
    wrapper.className = "weather-table-scroll";
    wrapper.tabIndex = 0;
    wrapper.setAttribute("role", "region");
    wrapper.setAttribute("aria-label", title);
    const grid = node("table");
    grid.append(node("caption", title));
    const head = node("thead");
    const tr = node("tr");
    columns.forEach((column) => {
      const cell = node("th", column);
      cell.scope = "col";
      tr.append(cell);
    });
    head.append(tr);
    grid.append(head);
    const body = node("tbody");
    rows.forEach((row) => {
      const line = node("tr");
      row.forEach((value) => line.append(node("td", value ?? "—")));
      body.append(line);
    });
    grid.append(body);
    wrapper.append(grid);
    return wrapper;
  }
  function render() {
    panel.querySelectorAll("[data-weather-i18n]").forEach((element) => {
      const translated = t(element.dataset.weatherI18n);
      element.textContent =
        element.tagName === "LI" ? translated.replace(/^\d+\.\s*/, "") : translated;
    });
    button.disabled = busy || activating;
    fileInput.disabled = busy || activating;
    form.setAttribute("aria-busy", String(busy));
    button.textContent = t(busy ? "checking" : "check");
    output.replaceChildren();
    const conversionReady = Boolean(result?.conversionReady);
    status.textContent = t(
      busy
        ? "checking"
        : error
          ? "failed"
          : result
            ? conversionReady
              ? "ready"
              : "valid"
            : "empty",
    );
    if (error) {
      output.append(node("p", error.key ? t(error.key) : error.message));
      if (error.issues?.length)
        output.append(
          table(
            t("issue"),
            [t("row"), t("column"), t("reason")],
            error.issues.map((item) => [item.row, item.column, item.message]),
          ),
        );
    }
    if (!result) return;
    if (Array.isArray(result.warnings) && result.warnings.length) {
      const warnings = node("ul");
      warnings.className = "weather-warnings";
      result.warnings.forEach((message) => warnings.append(node("li", message)));
      output.append(warnings);
    }
    const summary = node("dl");
    summary.className = "weather-summary";
    [
      ["rows", result.rowCount],
      ["interval", result.intervalMinutes],
      ["start", result.start],
      ["end", result.end],
    ].forEach(([key, value]) => {
      const display =
        key === "start" || key === "end" ? value.replace("T", " ").replace("Z", "") : value;
      const item = node("div");
      item.append(node("dt", t(key)), node("dd", display));
      summary.append(item);
    });
    output.append(summary, node("p", conversionReady ? t("unchanged") : t("noFill")));
    if (conversionReady && result.coverage) renderWindow();
    output.append(
      node("p", `${t("additional")}: ${result.missingModelColumns.join(", ") || t("none")}`),
    );
    output.append(node("p", t("scroll")));
    output.append(
      table(
        t("preview"),
        result.columns,
        result.preview.map((record) => result.columns.map((column) => record[column])),
      ),
    );
    output.append(
      table(
        t("minmax"),
        [t("column"), t("minimum"), t("maximum")],
        Object.entries(result.ranges).map(([column, values]) => [column, values.min, values.max]),
      ),
    );
    const fingerprint = node("p", `${t("hash")}: ${result.sha256}`);
    fingerprint.className = "weather-fingerprint";
    output.append(fingerprint);
  }

  function renderWindow() {
    const helper = window.GreenlightRunWindow;
    const bounds = result.coverage;
    const section = node("fieldset");
    section.className = "run-window";
    section.disabled = activating;
    section.append(node("legend", t("windowTitle")));
    const grid = node("div");
    grid.className = "run-window-grid";
    const field = (id, key, type, value) => {
      const label = node("label", t(key));
      label.htmlFor = id;
      const input = node("input");
      input.id = id;
      input.type = type;
      input.value = value;
      label.append(input);
      grid.append(label);
      return input;
    };
    const year = field("weatherSourceYear", "windowYear", "number", windowInput.year);
    year.min = "1900";
    year.max = "2100";
    year.step = "1";
    year.placeholder = "2010";
    const label = node("label", t("windowConvention"));
    label.htmlFor = "weatherTimeConvention";
    const convention = node("select");
    convention.id = "weatherTimeConvention";
    [
      ["", "windowChoose"],
      ["source-local-standard", "windowLocal"],
      ["UTC", "windowUtc"],
    ].forEach(([value, key]) => {
      const option = node("option", t(key));
      option.value = value;
      convention.append(option);
    });
    convention.value = windowInput.convention;
    label.append(convention);
    grid.append(label);
    const start = field("simulationStart", "windowStart", "datetime-local", windowInput.start);
    const end = field("simulationEnd", "windowEnd", "datetime-local", windowInput.end);
    const sourceRange = node("p"),
      usableRange = node("p");
    function updateBounds() {
      const y = Number(year.value),
        valid = Number.isInteger(y) && y >= 1900 && y <= 2100;
      for (const input of [start, end]) {
        input.step = "900";
        input.disabled = !valid;
        input.min = valid ? helper.dateTime(y, bounds.earliestStartSeconds) : "";
        input.max = valid ? helper.dateTime(y, bounds.latestEndSeconds) : "";
      }
      sourceRange.hidden = usableRange.hidden = !valid;
      if (valid) {
        const date = (seconds) => helper.dateTime(y, seconds).replace("T", " ");
        sourceRange.textContent = `${t("windowSourceRange")}: ${date(bounds.sourceStartSeconds)} → ${date(bounds.sourceEndSeconds)}`;
        usableRange.textContent = `${t("windowUsableRange")}: ${date(bounds.earliestStartSeconds)} → ${date(bounds.latestEndSeconds)}`;
      }
    }
    year.addEventListener("change", () => {
      windowInput.year = year.value;
      windowInput.start = "";
      windowInput.end = "";
      const y = Number(year.value);
      if (Number.isInteger(y) && y >= 1900 && y <= 2100) {
        windowInput.start = helper.dateTime(y, bounds.earliestStartSeconds);
        windowInput.end = helper.dateTime(
          y,
          Math.min(bounds.latestEndSeconds, bounds.earliestStartSeconds + 86400),
        );
      }
      start.value = windowInput.start;
      end.value = windowInput.end;
      activationMessage = "";
      updateBounds();
      updateSummary();
    });
    [
      [convention, "convention"],
      [start, "start"],
      [end, "end"],
    ].forEach(([input, key]) => {
      input.addEventListener("change", () => {
        windowInput[key] = input.value;
        activationMessage = "";
        updateSummary();
      });
    });
    section.append(grid, sourceRange, usableRange);
    let checked;
    const message = node("p");
    message.id = "runWindowSummary";
    message.setAttribute("role", "status");
    section.append(message, node("p", t("windowAssumptions")));
    const runButton = node("button", t(activating ? "windowInitializing" : "useWeather"));
    runButton.type = "button";
    runButton.className = "showcase-primary weather-use-button";
    const response = node("p");
    response.setAttribute("role", "status");
    function updateSummary() {
      checked = helper.check(
        windowInput.year,
        windowInput.convention,
        windowInput.start,
        windowInput.end,
        bounds,
      );
      message.textContent = checked.error
        ? t(checked.error)
        : `${checked.hours} ${t("windowHours")} · ${checked.steps} ${t("windowSteps")} · 15 min/${t("windowSteps")}`;
      message.classList.toggle("run-window-error", Boolean(checked.error));
      runButton.disabled = Boolean(checked.error) || activating;
      response.textContent =
        activationMessage === "windowInitialized" ? t(activationMessage) : activationMessage;
      response.hidden = !activationMessage;
    }
    runButton.addEventListener("click", () => {
      activating = true;
      activationMessage = "";
      const detail = {
        weatherId: result.weatherId,
        runWindow: checked.window,
        complete: (errorMessage) => {
          activating = false;
          activationMessage = errorMessage || "windowInitialized";
          render();
        },
      };
      render();
      document.dispatchEvent(new CustomEvent("greenlight-weather-selected", { detail }));
    });
    section.append(runButton, response);
    updateBounds();
    updateSummary();
    output.append(section);
  }
  fileInput.addEventListener("change", () => {
    result = null;
    error = null;
    render();
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    result = null;
    error = null;
    const file = fileInput.files[0];
    if (!validateFile(file)) {
      error = { key: "select" };
      render();
      return;
    }
    busy = true;
    render();
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch("/api/weather/preview", {
        method: "POST",
        headers: { "Content-Type": MIME, "X-GreenLight-Upload": "1" },
        body: file,
        signal: controller.signal,
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.headers.get("content-type")?.includes("application/json"))
        throw new Error("server");
      const payload = await response.json();
      if (!response.ok || !payload.ok) error = payload.error || { key: "unavailable" };
      else if (!payload.weather || typeof payload.weather.conversionReady !== "boolean")
        throw new Error("contract");
      else result = payload.weather;
    } catch (cause) {
      error = { key: cause.name === "AbortError" ? "timeout" : "unavailable" };
    } finally {
      window.clearTimeout(timeout);
      busy = false;
      render();
    }
  });
  new MutationObserver(render).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang"],
  });
  render();
})();
