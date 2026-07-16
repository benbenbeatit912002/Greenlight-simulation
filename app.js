(function () {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const root = byId("simulatorApp");
  const simulator = window.GreenhouseSimulator;
  const model = new simulator.GreenhouseModel({ scenario: "spring", mode: "auto" });

  let isRunning = false;
  let speed = 4;
  let chartMode = "temperature";
  let timerId = null;
  let resizeFrame = null;
  let currentSnapshot = model.snapshot();
  let activeEngine = "browser";
  let engineDisplayState = "browser";
  let engineDisplayReason = "";
  let remoteRevision = null;
  let remoteBusy = false;
  let language = "zh";

  const translations = {
    zh: {
      panelTitle: "氣候控制",
      step: "STEP",
      controlMode: "控制模式",
      autoControl: "自動控制",
      manualControl: "手動控制",
      targetTitle: "自動控制目標",
      ruleController: "規則控制器",
      dayTemperature: "日間溫度",
      nightTemperature: "夜間溫度",
      co2Target: "CO₂ 目標",
      humidityLimit: "濕度上限",
      actuators: "GreenLight 致動器",
      boilerHeating: "鍋爐加熱",
      co2Injection: "CO₂ 注入",
      thermalScreen: "保溫幕",
      roofVentilation: "屋頂通風",
      growLights: "補光燈",
      blackoutScreen: "遮光幕",
      resourceUse: "本次模擬用量",
      perSquareMeter: "每平方米",
      heating: "暖氣",
      supplementalLighting: "補光",
      estimatedCost: "估計成本",
      climateNormal: "氣候狀態正常",
      climateWarning: "氣候限制警示",
      withinLimits: "所有變量皆在 GreenLight 限制範圍內",
      autoAdjusting: "自動調節中",
      dragSliders: "拖曳滑桿調整",
      fullModel: "GreenLight 2 完整模型",
      offlineModel: "科學模型已離線",
      approximateModel: "即時近似模型",
      fullModelNote: "15 分鐘／步 · 28-state GreenLight-Gym2 CasADi 模型 · 阿姆斯特丹實測天氣。六項控制值直接使用 0–1 絕對開度。",
      browserModelNote: "15 分鐘／步 · 6 項 GreenLight 2 控制量。此介面使用簡化氣候動態作即時互動展示；啟用 Python 科學後端後會自動切換完整 28-state 模型。",
      offlineModelNote: "GreenLight-Gym2 連線中斷，已安全切回瀏覽器近似模型。",
      switchToEnglish: "切換為英文",
      switchToChinese: "切換為中文",
      roomBelow15: "室溫低於 15°C",
      roomAbove34: "室溫高於 34°C",
      humidityBelow50: "相對濕度低於 50%",
      humidityAbove85: "相對濕度高於 85%",
      co2Below300: "CO₂ 低於 300 ppm",
      co2Above1600: "CO₂ 高於 1600 ppm",
    },
    en: {
      panelTitle: "Climate controls",
      step: "STEP",
      controlMode: "Control mode",
      autoControl: "Auto control",
      manualControl: "Manual control",
      targetTitle: "Auto-control targets",
      ruleController: "Rule controller",
      dayTemperature: "Day temperature",
      nightTemperature: "Night temperature",
      co2Target: "CO₂ target",
      humidityLimit: "Humidity limit",
      actuators: "GreenLight actuators",
      boilerHeating: "Boiler heating",
      co2Injection: "CO₂ injection",
      thermalScreen: "Thermal screen",
      roofVentilation: "Roof ventilation",
      growLights: "Grow lights",
      blackoutScreen: "Blackout screen",
      resourceUse: "Simulation resource use",
      perSquareMeter: "Per m²",
      heating: "Heating",
      supplementalLighting: "Supplemental lighting",
      estimatedCost: "Estimated cost",
      climateNormal: "Climate status normal",
      climateWarning: "Climate limit warning",
      withinLimits: "All variables are within GreenLight limits",
      autoAdjusting: "Adjusting automatically",
      dragSliders: "Drag sliders to adjust",
      fullModel: "GreenLight 2 full model",
      offlineModel: "Scientific model offline",
      approximateModel: "Real-time approximation",
      fullModelNote: "15 min/step · 28-state GreenLight-Gym2 CasADi model · measured Amsterdam weather. The six controls use absolute 0–1 openings.",
      browserModelNote: "15 min/step · 6 GreenLight 2 control variables. This interface uses simplified climate dynamics for live interaction; it switches to the full 28-state model when the Python scientific backend is available.",
      offlineModelNote: "GreenLight-Gym2 connection lost. Safely switched to the browser approximation.",
      switchToEnglish: "Switch to English",
      switchToChinese: "切換為中文",
      roomBelow15: "Room temperature is below 15°C",
      roomAbove34: "Room temperature is above 34°C",
      humidityBelow50: "Relative humidity is below 50%",
      humidityAbove85: "Relative humidity is above 85%",
      co2Below300: "CO₂ is below 300 ppm",
      co2Above1600: "CO₂ is above 1600 ppm",
    },
  };

  const controls = Array.from(document.querySelectorAll("[data-control]"));
  const modeButtons = Array.from(document.querySelectorAll("[data-mode]"));
  const chartButtons = Array.from(document.querySelectorAll("[data-chart]"));

  try {
    language = window.localStorage.getItem("greenlight-panel-language") === "en" ? "en" : "zh";
  } catch {
    language = "zh";
  }

  function t(key) {
    return translations[language][key] || translations.zh[key] || key;
  }

  function applyLanguage() {
    document.documentElement.lang = "zh-Hant";
    byId("controlPanel").lang = language === "en" ? "en" : "zh-Hant";
    root.dataset.language = language;
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = t(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
      element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
    });
    const toggle = byId("languageToggle");
    setText("languageToggleLabel", language === "zh" ? "EN" : "中文");
    toggle.setAttribute("aria-label", language === "zh" ? t("switchToEnglish") : t("switchToChinese"));
    updateEngineStatus(engineDisplayState, engineDisplayReason);
    updateControls(currentSnapshot);
    updateAlert(currentSnapshot);
  }

  function toggleLanguage() {
    language = language === "zh" ? "en" : "zh";
    try {
      window.localStorage.setItem("greenlight-panel-language", language);
    } catch {
      // The switch remains available even when browser storage is unavailable.
    }
    applyLanguage();
  }

  function setText(id, value) {
    const element = byId(id);
    if (element) element.textContent = value;
  }

  function readTargets() {
    return {
      dayTemp: Number(byId("dayTempTarget").value),
      nightTemp: Number(byId("nightTempTarget").value),
      co2: Number(byId("co2Target").value),
      maxRh: Number(byId("rhTarget").value),
    };
  }

  function readControls() {
    return Object.fromEntries(
      controls.map((input) => [input.dataset.control, Number(input.value) / 100]),
    );
  }

  function updateEngineStatus(engine, reason = "") {
    const badge = byId("engineBadge");
    engineDisplayState = engine;
    engineDisplayReason = reason;
    badge.dataset.engine = engine;
    if (engine === "greenlight2") {
      setText("engineLabel", t("fullModel"));
      setText("modelNote", t("fullModelNote"));
      return;
    }
    if (engine === "error") {
      setText("engineLabel", t("offlineModel"));
      setText("modelNote", `${t("offlineModelNote")}${reason ? ` ${reason}` : ""}`);
      return;
    }
    setText("engineLabel", t("approximateModel"));
    setText("modelNote", t("browserModelNote"));
  }

  async function requestApi(path, payload) {
    const options = {
      headers: { Accept: "application/json" },
    };
    if (payload !== undefined) {
      options.method = "POST";
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(payload);
    }
    const response = await fetch(path, options);
    let body = null;
    try {
      body = await response.json();
    } catch {
      throw new Error(`後端回傳了無效資料（HTTP ${response.status}）`);
    }
    if (!response.ok || body.ok === false) {
      throw new Error(body?.error?.message || `後端請求失敗（HTTP ${response.status}）`);
    }
    return body;
  }

  async function probeBackend() {
    if (!/^https?:$/.test(window.location.protocol)) {
      updateEngineStatus("browser");
      return;
    }
    try {
      const status = await requestApi("/api/status");
      remoteRevision = status.revision;
      if (!status.realModelAvailable) {
        updateEngineStatus("browser");
        return;
      }
      activeEngine = "greenlight2";
      updateEngineStatus("greenlight2");
      const response = await requestApi("/api/reset", {
        seed: 42,
        scenario: byId("scenarioSelect").value,
        mode: currentSnapshot.mode,
        targets: readTargets(),
        expectedRevision: remoteRevision,
      });
      remoteRevision = response.revision;
      render(response.snapshot);
    } catch {
      activeEngine = "browser";
      remoteRevision = null;
      updateEngineStatus("browser");
    }
  }

  async function stepActiveEngine(stepCount) {
    if (activeEngine === "browser") {
      return model.step(stepCount);
    }
    const response = await requestApi("/api/step", {
      steps: stepCount,
      mode: currentSnapshot.mode,
      controls: readControls(),
      targets: readTargets(),
      expectedRevision: remoteRevision,
    });
    remoteRevision = response.revision;
    return response.snapshot;
  }

  async function resetActiveEngine() {
    if (activeEngine === "browser") {
      model.setScenario(byId("scenarioSelect").value);
      model.setMode(currentSnapshot.mode);
      Object.entries(readTargets()).forEach(([name, value]) => model.setTarget(name, value));
      return model.reset();
    }
    const response = await requestApi("/api/reset", {
      seed: 42,
      scenario: byId("scenarioSelect").value,
      mode: currentSnapshot.mode,
      targets: readTargets(),
      expectedRevision: remoteRevision,
    });
    remoteRevision = response.revision;
    return response.snapshot;
  }

  function switchToBrowserFallback(reason) {
    activeEngine = "browser";
    remoteRevision = null;
    model.setScenario(byId("scenarioSelect").value);
    model.setMode(currentSnapshot.mode);
    Object.entries(readTargets()).forEach(([name, value]) => model.setTarget(name, value));
    const snapshot = model.reset();
    if (snapshot.mode === "manual") {
      Object.entries(readControls()).forEach(([name, value]) => model.setControl(name, value));
    }
    updateEngineStatus("error", reason);
    render(model.snapshot());
  }

  function formatClock(minuteOfDay) {
    const hour = Math.floor(minuteOfDay / 60);
    const minute = Math.round(minuteOfDay % 60);
    return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  }

  function formatHour(hour) {
    const totalMinutes = Math.round(hour * 60) % 1440;
    return formatClock(totalMinutes);
  }

  function formatNumber(value, digits = 1) {
    return Number(value).toFixed(digits);
  }

  function setStatus(dotId, value, safeMin, safeMax, warningMargin) {
    const dot = byId(dotId);
    dot.classList.remove("warning", "danger");
    if (value < safeMin || value > safeMax) {
      dot.classList.add("danger");
      return;
    }
    if (value < safeMin + warningMargin || value > safeMax - warningMargin) {
      dot.classList.add("warning");
    }
  }

  function updateScene(snapshot) {
    const { controls: u, outdoor, indoor, crop } = snapshot;
    const daylight = simulator.clamp(outdoor.daylight, 0, 1);
    const solarProgress = simulator.clamp(
      (snapshot.hour - outdoor.sunrise) / Math.max(outdoor.sunset - outdoor.sunrise, 0.1),
      0,
      1,
    );
    const sunX = 10 + solarProgress * 66;
    const sunY = 54 - Math.sin(Math.PI * solarProgress) * 37;
    const fruitScale = simulator.clamp(0.8 + (crop.fruitDryMass - 50) / 70, 0.8, 1.25);
    const condensation = simulator.clamp((indoor.rh - 81) / 12, 0, 0.9);

    root.style.setProperty("--daylight", daylight.toFixed(3));
    root.style.setProperty("--sun-x", `${sunX.toFixed(1)}%`);
    root.style.setProperty("--sun-y", `${sunY.toFixed(1)}%`);
    root.style.setProperty("--cloud-opacity", (0.06 + outdoor.cloud * 0.7 * Math.max(daylight, 0.28)).toFixed(2));
    root.style.setProperty("--lamp-power", u.uLamp.toFixed(3));
    root.style.setProperty("--boiler-power", u.uBoil.toFixed(3));
    root.style.setProperty("--co2-power", u.uCO2.toFixed(3));
    root.style.setProperty("--thermal-position", u.uThScr.toFixed(3));
    root.style.setProperty("--blackout-position", u.uBlScr.toFixed(3));
    root.style.setProperty("--vent-angle", `${(-2 - u.uVent * 25).toFixed(1)}deg`);
    root.style.setProperty("--condensation-opacity", condensation.toFixed(2));
    root.style.setProperty("--fruit-scale", fruitScale.toFixed(2));

    const windLines = byId("windLines");
    windLines.style.opacity = String(simulator.clamp(0.12 + outdoor.wind / 9, 0.15, 0.72));
    windLines.style.setProperty("--wind-duration", `${simulator.clamp(4.2 - outdoor.wind * 0.55, 1.15, 4)}s`);
  }

  function updateControls(snapshot) {
    controls.forEach((input) => {
      const name = input.dataset.control;
      const percent = Math.round(snapshot.controls[name] * 100);
      input.value = String(percent);
      input.disabled = snapshot.mode === "auto";
      input.style.setProperty("--range-value", `${percent}%`);
      setText(`${name}Output`, `${percent}%`);
    });

    modeButtons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.mode === snapshot.mode));
    });

    byId("targetSection").classList.toggle("hidden", snapshot.mode !== "auto");
    setText("actuatorModeHint", snapshot.mode === "auto" ? t("autoAdjusting") : t("dragSliders"));
  }

  function updateAlert(snapshot) {
    const alertBox = byId("alertBox");
    const title = alertBox.querySelector("strong");
    const message = alertBox.querySelector("span");
    const hasViolation = snapshot.violations.length > 0;
    alertBox.classList.toggle("warning", hasViolation);
    title.textContent = hasViolation ? t("climateWarning") : t("climateNormal");
    message.textContent = hasViolation
      ? snapshot.violations.map(translateViolation).join(" · ")
      : t("withinLimits");
  }

  function translateViolation(message) {
    const keys = {
      "室溫低於 15°C": "roomBelow15",
      "室溫高於 34°C": "roomAbove34",
      "相對濕度低於 50%": "humidityBelow50",
      "相對濕度高於 85%": "humidityAbove85",
      "CO₂ 低於 300 ppm": "co2Below300",
      "CO₂ 高於 1600 ppm": "co2Above1600",
    };
    return keys[message] ? t(keys[message]) : message;
  }

  function render(snapshot = currentSnapshot) {
    currentSnapshot = snapshot;
    const { indoor, outdoor, crop, resources, controls: u } = snapshot;
    const tempTarget = outdoor.daylight > 0.06
      ? snapshot.targets.dayTemp
      : snapshot.targets.nightTemp;
    const tempDifference = indoor.airTemp - tempTarget;
    const rhHeadroom = snapshot.targets.maxRh - indoor.rh;

    setText("airTempValue", formatNumber(indoor.airTemp));
    setText(
      "airTempDelta",
      `${tempDifference >= 0 ? "+" : ""}${formatNumber(tempDifference)}°C 對目標`,
    );
    setText("rhValue", formatNumber(indoor.rh, 0));
    setText("rhDelta", rhHeadroom >= 0 ? `距上限 ${formatNumber(rhHeadroom, 0)}%` : `超出 ${formatNumber(-rhHeadroom, 0)}%`);
    setText("co2Value", formatNumber(indoor.co2, 0));
    setText("co2Delta", `目標 ${formatNumber(snapshot.targets.co2, 0)} ppm`);
    setText("pipeTempValue", formatNumber(indoor.pipeTemp));
    setText("boilerState", `鍋爐 ${Math.round(u.uBoil * 100)}%`);
    setText("heatUse", `${formatNumber(resources.heatKwh, 3)} kWh/m²`);

    setStatus("tempStatusDot", indoor.airTemp, 15, 34, 2);
    setStatus("rhStatusDot", indoor.rh, 50, 85, 5);
    setStatus("co2StatusDot", indoor.co2, 300, 1600, 140);

    setText("clockLabel", `第 ${snapshot.dayOfYear} 天・${formatClock(snapshot.minuteOfDay)}`);
    setText("outsideRadiation", formatNumber(outdoor.radiation, 0));
    setText("outsideTemp", formatNumber(outdoor.temperature));
    setText("outsideWind", formatNumber(outdoor.wind));
    setText("stepValue", String(snapshot.modelStep).padStart(4, "0"));

    setText("svgClimateValue", `${formatNumber(indoor.airTemp)}°C · ${formatNumber(indoor.rh, 0)}%`);
    setText("svgCo2Value", `${formatNumber(indoor.co2, 0)} ppm`);
    setText("svgCanopyValue", `${formatNumber(indoor.canopyTemp)}°C`);
    setText("legendVent", `${Math.round(u.uVent * 100)}%`);
    setText("legendThermal", `${Math.round(u.uThScr * 100)}%`);
    setText("legendLamp", `${Math.round(u.uLamp * 100)}%`);
    setText("legendHeat", `${Math.round(u.uBoil * 100)}%`);

    setText("fruitMassValue", formatNumber(crop.fruitDryMass, 2));
    setText("laiValue", formatNumber(crop.leafAreaIndex, 2));
    setText("tempSumValue", formatNumber(crop.tempSum, 1));
    setText("canopy24Value", formatNumber(indoor.canopy24hTemp));

    setText("resourceHeat", formatNumber(resources.heatKwh, 3));
    setText("resourceLamp", formatNumber(resources.lampKwh, 3));
    setText("resourceCo2", formatNumber(resources.co2Kg, 3));
    setText("resourceCost", formatNumber(resources.costEur, 3));

    updateScene(snapshot);
    updateControls(snapshot);
    updateAlert(snapshot);
    drawChart(snapshot.history, snapshot.targets);
  }

  function chartConfiguration(history, targets) {
    const styles = getComputedStyle(document.documentElement);
    const green = styles.getPropertyValue("--green").trim();
    const amber = styles.getPropertyValue("--amber").trim();
    const blue = styles.getPropertyValue("--blue").trim();
    const violet = styles.getPropertyValue("--violet").trim();
    const muted = styles.getPropertyValue("--muted").trim();

    if (chartMode === "humidity") {
      return {
        unit: "%",
        label: "最近 24 小時相對濕度趨勢",
        minSpan: 20,
        series: [
          { label: "室內 RH", color: blue, values: history.map((point) => point.rh) },
          { label: "室外 RH", color: muted, values: history.map((point) => point.outsideRh), dash: [4, 4] },
          { label: "控制上限", color: amber, values: history.map(() => targets.maxRh), dash: [7, 5] },
        ],
      };
    }

    if (chartMode === "co2") {
      return {
        unit: " ppm",
        label: "最近 24 小時室內二氧化碳趨勢",
        minSpan: 300,
        series: [
          { label: "室內 CO₂", color: green, values: history.map((point) => point.co2) },
          { label: "控制目標", color: violet, values: history.map(() => targets.co2), dash: [7, 5] },
        ],
      };
    }

    return {
      unit: "°C",
      label: "最近 24 小時室內、冠層與室外溫度趨勢",
      minSpan: 10,
      series: [
        { label: "室內", color: green, values: history.map((point) => point.airTemp) },
        { label: "冠層", color: amber, values: history.map((point) => point.canopyTemp) },
        { label: "室外", color: blue, values: history.map((point) => point.outsideTemp), dash: [4, 4] },
      ],
    };
  }

  function drawChart(history, targets) {
    const canvas = byId("trendCanvas");
    const empty = byId("chartEmpty");
    const legend = byId("chartLegend");
    const container = canvas.parentElement;
    const rect = container.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    const context = canvas.getContext("2d");
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, rect.width, rect.height);

    const config = chartConfiguration(history, targets);
    canvas.setAttribute("aria-label", config.label);
    legend.replaceChildren();
    config.series.forEach((series) => {
      const item = document.createElement("span");
      const swatch = document.createElement("i");
      swatch.style.setProperty("--legend-color", series.color);
      item.append(swatch, document.createTextNode(series.label));
      legend.append(item);
    });

    if (history.length < 2) {
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");

    const styles = getComputedStyle(document.documentElement);
    const textColor = styles.getPropertyValue("--muted").trim();
    const gridColor = "rgba(177, 216, 198, 0.10)";
    const plot = {
      left: 38,
      right: rect.width - 10,
      top: 10,
      bottom: rect.height - 24,
    };
    const plotWidth = Math.max(1, plot.right - plot.left);
    const plotHeight = Math.max(1, plot.bottom - plot.top);
    const allValues = config.series.flatMap((series) => series.values).filter(Number.isFinite);
    let minValue = Math.min(...allValues);
    let maxValue = Math.max(...allValues);
    const observedSpan = Math.max(maxValue - minValue, config.minSpan);
    const center = (minValue + maxValue) / 2;
    minValue = center - observedSpan * 0.58;
    maxValue = center + observedSpan * 0.58;

    context.font = "9px ui-sans-serif, system-ui, sans-serif";
    context.textBaseline = "middle";
    context.lineWidth = 1;

    for (let tick = 0; tick <= 3; tick += 1) {
      const ratio = tick / 3;
      const y = plot.top + plotHeight * ratio;
      const value = maxValue - (maxValue - minValue) * ratio;
      context.beginPath();
      context.strokeStyle = gridColor;
      context.moveTo(plot.left, y);
      context.lineTo(plot.right, y);
      context.stroke();
      context.fillStyle = textColor;
      context.textAlign = "right";
      const digits = chartMode === "co2" ? 0 : 1;
      context.fillText(`${value.toFixed(digits)}${config.unit}`, plot.left - 7, y);
    }

    const xTickIndexes = [0, Math.floor((history.length - 1) / 3), Math.floor((history.length - 1) * 2 / 3), history.length - 1];
    xTickIndexes.forEach((pointIndex, tickIndex) => {
      const x = plot.left + (pointIndex / Math.max(history.length - 1, 1)) * plotWidth;
      context.fillStyle = textColor;
      context.textAlign = tickIndex === 0 ? "left" : tickIndex === xTickIndexes.length - 1 ? "right" : "center";
      context.fillText(formatHour(history[pointIndex].hour), x, rect.height - 9);
    });

    config.series.forEach((series) => {
      context.beginPath();
      context.strokeStyle = series.color;
      context.lineWidth = series.dash ? 1.35 : 1.8;
      context.lineJoin = "round";
      context.lineCap = "round";
      context.setLineDash(series.dash || []);
      series.values.forEach((value, index) => {
        const x = plot.left + (index / Math.max(series.values.length - 1, 1)) * plotWidth;
        const y = plot.bottom - ((value - minValue) / (maxValue - minValue)) * plotHeight;
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.stroke();
      context.setLineDash([]);

      if (!series.dash) {
        const lastValue = series.values[series.values.length - 1];
        const x = plot.right;
        const y = plot.bottom - ((lastValue - minValue) / (maxValue - minValue)) * plotHeight;
        context.beginPath();
        context.fillStyle = series.color;
        context.arc(x, y, 3, 0, Math.PI * 2);
        context.fill();
      }
    });
  }

  async function runTick() {
    if (!isRunning || remoteBusy) return;
    remoteBusy = true;
    try {
      render(await stepActiveEngine(speed));
    } catch (error) {
      setRunning(false);
      switchToBrowserFallback(error instanceof Error ? error.message : String(error));
    } finally {
      remoteBusy = false;
      if (isRunning) {
        timerId = window.setTimeout(runTick, 700);
      }
    }
  }

  function setRunning(nextRunning) {
    isRunning = nextRunning;
    const playButton = byId("playButton");
    const liveIndicator = byId("liveIndicator");
    playButton.setAttribute("aria-pressed", String(isRunning));
    setText("playLabel", isRunning ? "暫停模擬" : "開始模擬");
    liveIndicator.classList.toggle("running", isRunning);
    liveIndicator.querySelector("span").textContent = isRunning ? "模擬運行中" : "已暫停";

    if (timerId !== null) {
      window.clearTimeout(timerId);
      timerId = null;
    }

    if (isRunning) {
      timerId = window.setTimeout(runTick, 120);
    }
  }

  function bindEvents() {
    byId("languageToggle").addEventListener("click", toggleLanguage);
    byId("playButton").addEventListener("click", () => setRunning(!isRunning));

    byId("resetButton").addEventListener("click", async () => {
      setRunning(false);
      try {
        render(await resetActiveEngine());
      } catch (error) {
        switchToBrowserFallback(error instanceof Error ? error.message : String(error));
      }
    });

    byId("scenarioSelect").addEventListener("change", async (event) => {
      if (activeEngine === "browser") {
        render(model.setScenario(event.target.value));
        return;
      }
      setRunning(false);
      try {
        render(await resetActiveEngine());
      } catch (error) {
        switchToBrowserFallback(error instanceof Error ? error.message : String(error));
      }
    });

    byId("speedSelect").addEventListener("change", (event) => {
      speed = Number(event.target.value);
      if (isRunning) setRunning(true);
    });

    controls.forEach((input) => {
      input.addEventListener("input", () => {
        if (currentSnapshot.mode !== "manual") return;
        const value = Number(input.value) / 100;
        if (activeEngine === "browser") {
          model.setControl(input.dataset.control, value);
          render(model.snapshot());
          return;
        }
        render({
          ...currentSnapshot,
          controls: { ...currentSnapshot.controls, [input.dataset.control]: value },
        });
      });
    });

    modeButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (activeEngine === "browser") {
          render(model.setMode(button.dataset.mode));
          return;
        }
        render({ ...currentSnapshot, mode: button.dataset.mode });
      });
    });

    const targetInputs = [
      ["dayTempTarget", "dayTemp"],
      ["nightTempTarget", "nightTemp"],
      ["co2Target", "co2"],
      ["rhTarget", "maxRh"],
    ];
    targetInputs.forEach(([inputId, targetName]) => {
      byId(inputId).addEventListener("change", (event) => {
        const value = Number(event.target.value);
        if (!Number.isFinite(value)) return;
        if (activeEngine === "browser") {
          model.setTarget(targetName, value);
          render(model.snapshot());
          return;
        }
        render({
          ...currentSnapshot,
          targets: { ...currentSnapshot.targets, [targetName]: value },
        });
      });
    });

    chartButtons.forEach((button) => {
      button.addEventListener("click", () => {
        chartMode = button.dataset.chart;
        chartButtons.forEach((candidate) => {
          candidate.setAttribute("aria-pressed", String(candidate === button));
        });
        drawChart(currentSnapshot.history, currentSnapshot.targets);
      });
    });

    window.addEventListener("resize", () => {
      if (resizeFrame !== null) window.cancelAnimationFrame(resizeFrame);
      resizeFrame = window.requestAnimationFrame(() => {
        drawChart(currentSnapshot.history, currentSnapshot.targets);
        resizeFrame = null;
      });
    });
  }

  applyLanguage();
  bindEvents();
  render(currentSnapshot);
  probeBackend();
}());
