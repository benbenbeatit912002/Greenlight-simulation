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
  let baselineRun = null;
  let currentRunId = createRunId();

  const BASELINE_STORAGE_KEY = "greenlight-decision-baseline-v1";

  const translations = {
    zh: {
      documentTitle: "GreenLight 2 溫室模擬器",
      metaDescription: "結合科學 Python 後端與瀏覽器安全回退模式的 GreenLight 2 互動溫室氣候與控制模擬器。",
      brandSubtitle: "溫室模擬器",
      runControls: "模擬執行控制",
      weatherScenario: "天氣情境",
      scenarioSpring: "春季晴天",
      scenarioCloudy: "多雲寒冷",
      scenarioSummer: "夏季炎熱",
      scenarioWinter: "冬季低溫",
      speed: "速度",
      resetSimulation: "重設模擬",
      startSimulation: "開始模擬",
      pauseSimulation: "暫停模擬",
      simulationRunning: "模擬運行中",
      simulationPaused: "已暫停",
      showcaseTitle: "在決策進入溫室前，先看見氣候與作物的反應。",
      showcaseBody: "以實測天氣、28-state GreenLight 模型與六項致動器，探索控制策略如何改變溫度、濕度、CO₂、作物與資源使用。",
      exploreControls: "開始探索控制",
      howItWorks: "了解運作方式",
      stateVariables: "狀態變數",
      stepDuration: "每個模型步長",
      measuredWeather: "阿姆斯特丹實測天氣",
      projectHighlights: "專案重點",
      simulationStatus: "溫室即時狀態",
      indoorAir: "室內空氣",
      relativeHumidity: "相對濕度",
      indoorCo2: "室內 CO₂",
      heatingPipe: "加熱管道",
      greenhouseSection: "互動溫室剖面",
      outdoorWeather: "室外天氣",
      greenhouseTitle: "GreenLight 2 溫室剖面即時狀態",
      greenhouseDescription: "畫面依據通風窗、保溫幕、遮光幕、燈光、暖氣、二氧化碳與作物狀態同步變化。",
      indoorClimate: "室內氣候",
      co2Concentration: "CO₂ 濃度",
      canopyTemperature: "冠層溫度",
      actuatorStatus: "溫室致動器狀態",
      ventShort: "窗",
      thermalShort: "保溫幕",
      lampShort: "燈",
      heatingShort: "暖氣",
      environmentTrends: "環境趨勢",
      chartVariable: "選擇圖表變量",
      temperature: "溫度",
      humidity: "濕度",
      chartEmpty: "開始模擬後會顯示趨勢",
      tomatoCrop: "番茄作物",
      fruitingStage: "結果期",
      fruitDryMass: "果實乾物質",
      leafAreaIndex: "葉面積指數",
      temperatureSum: "溫度積分",
      canopy24h: "冠層 24h",
      tourKicker: "PROJECT WALKTHROUGH",
      tourTitle: "用三步理解這座數位溫室",
      tourBody: "從天氣與控制目標開始，觀察模型如何連結氣候、致動器、作物生長與資源使用。",
      tourStepOneTitle: "選擇情境",
      tourStepOneBody: "切換季節與實測天氣條件，建立不同的溫室外部擾動。",
      tourStepTwoTitle: "比較控制策略",
      tourStepTwoBody: "使用規則控制器，或手動調整六項 GreenLight 絕對控制量。",
      tourStepThreeTitle: "閱讀系統反應",
      tourStepThreeBody: "追蹤氣候、作物、限制警示、能源、CO₂ 與估計成本。",
      liveEngine: "LIVE ENGINE",
      modelTransparency: "介面會清楚標示目前引擎；近似模型不會冒充科學結果。",
      goToControls: "前往控制面板",
      closeTour: "關閉導覽",
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
      comparisonTitle: "方案比較工作台",
      decisionSupport: "決策支援",
      comparisonIntro: "先儲存一個完整模擬結果，再重設並以相同步數測試另一個策略。",
      saveBaseline: "儲存目前結果為基準",
      replaceBaseline: "以目前結果取代基準",
      clearBaseline: "清除",
      comparisonEmpty: "先執行至少一步模擬，便可儲存基準方案。",
      comparisonReadyToSave: "目前結果已可儲存為基準方案。",
      baselineNeedsRun: "請先執行至少一步模擬。",
      baselineRun: "基準方案",
      candidateRun: "目前方案",
      heatingDelta: "暖氣差異",
      lightingDelta: "補光差異",
      co2UseDelta: "CO₂ 差異",
      costDelta: "成本差異",
      fruitMassDelta: "果實乾物質差異",
      endStateAlerts: "終點警示",
      comparisonCaution: "綠色只表示較低資源使用或較高果實乾物質，不代表整體策略較佳，也不構成生產建議。",
      comparisonNeedsCandidate: "基準已儲存。請重設模擬，再把候選方案運行到第 {step} 步。",
      comparisonReady: "可比較：兩個方案皆運行 {steps} 步（{hours} 小時）。",
      comparisonStepMismatch: "請把目前方案運行到第 {steps} 步；目前為第 {current} 步。步數一致前不顯示差異。",
      comparisonEngineMismatch: "模型引擎不同，無法安全比較。基準：{baseline}；目前：{candidate}。",
      comparisonWeatherMatch: "天氣情境一致，適合隔離控制策略差異。",
      comparisonWeatherDifference: "天氣情境不同；結果同時包含天氣與控制差異。",
      comparisonMeta: "STEP {step} · {mode} · {engine}",
      comparisonAutoStrategy: "日 {day}°C · 夜 {night}°C · CO₂ {co2} ppm · RH ≤ {rh}%",
      comparisonManualStrategy: "鍋爐 {boil}% · CO₂ {co2}% · 保溫幕 {thermal}% · 通風 {vent}% · 燈 {lamp}% · 遮光 {blackout}%",
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
      fullModelTour: "目前連接 28-state GreenLight-Gym2 CasADi 模型與阿姆斯特丹實測天氣。",
      browserModelTour: "目前使用瀏覽器近似模型，適合免安裝互動展示，不代表完整科學結果。",
      offlineModelTour: "科學後端已離線；互動已安全切換至瀏覽器近似模型。",
      switchToEnglish: "切換為英文",
      switchToChinese: "切換為中文",
      roomBelow15: "室溫低於 15°C",
      roomAbove34: "室溫高於 34°C",
      humidityBelow50: "相對濕度低於 50%",
      humidityAbove85: "相對濕度高於 85%",
      co2Below300: "CO₂ 低於 300 ppm",
      co2Above1600: "CO₂ 高於 1600 ppm",
      backendInvalidResponse: "後端回傳了無效資料（HTTP {status}）",
      backendRequestFailed: "後端請求失敗（HTTP {status}）",
      temperatureDelta: "{value}°C 對目標",
      humidityRemaining: "距上限 {value}%",
      humidityExceeded: "超出 {value}%",
      co2TargetValue: "目標 {value} ppm",
      boilerValue: "鍋爐 {value}%",
      dayClock: "第 {day} 天・{time}",
      humidityChart: "最近 24 小時相對濕度趨勢",
      indoorRh: "室內 RH",
      outdoorRh: "室外 RH",
      controlLimit: "控制上限",
      co2Chart: "最近 24 小時室內二氧化碳趨勢",
      indoorCo2Series: "室內 CO₂",
      controlTarget: "控制目標",
      temperatureChart: "最近 24 小時室內、冠層與室外溫度趨勢",
      indoorSeries: "室內",
      canopySeries: "冠層",
      outdoorSeries: "室外",
    },
    en: {
      documentTitle: "GreenLight 2 Greenhouse Simulator",
      metaDescription: "Interactive GreenLight 2 greenhouse climate and control simulator with a scientific Python backend and browser-safe fallback.",
      brandSubtitle: "Greenhouse simulator",
      runControls: "Simulation run controls",
      weatherScenario: "Weather scenario",
      scenarioSpring: "Clear spring",
      scenarioCloudy: "Cold and cloudy",
      scenarioSummer: "Hot summer",
      scenarioWinter: "Cold winter",
      speed: "Speed",
      resetSimulation: "Reset simulation",
      startSimulation: "Start simulation",
      pauseSimulation: "Pause simulation",
      simulationRunning: "Simulation running",
      simulationPaused: "Paused",
      showcaseTitle: "See climate and crop responses before decisions reach the greenhouse.",
      showcaseBody: "Explore how control strategies change temperature, humidity, CO₂, crop state, and resource use with measured weather, a 28-state GreenLight model, and six actuators.",
      exploreControls: "Explore the controls",
      howItWorks: "How it works",
      stateVariables: "state variables",
      stepDuration: "per model step",
      measuredWeather: "measured Amsterdam weather",
      projectHighlights: "Project highlights",
      simulationStatus: "Live greenhouse status",
      indoorAir: "Indoor air",
      relativeHumidity: "Relative humidity",
      indoorCo2: "Indoor CO₂",
      heatingPipe: "Heating pipe",
      greenhouseSection: "Interactive greenhouse cross-section",
      outdoorWeather: "Outdoor weather",
      greenhouseTitle: "Live GreenLight 2 greenhouse cross-section",
      greenhouseDescription: "The view responds to ventilation, thermal and blackout screens, lighting, heating, carbon dioxide, and crop state.",
      indoorClimate: "Indoor climate",
      co2Concentration: "CO₂ concentration",
      canopyTemperature: "Canopy temperature",
      actuatorStatus: "Greenhouse actuator status",
      ventShort: "Vent",
      thermalShort: "Thermal",
      lampShort: "Lamp",
      heatingShort: "Heat",
      environmentTrends: "Environment trends",
      chartVariable: "Select chart variable",
      temperature: "Temperature",
      humidity: "Humidity",
      chartEmpty: "Trends appear after the simulation starts",
      tomatoCrop: "Tomato crop",
      fruitingStage: "Fruiting stage",
      fruitDryMass: "Fruit dry mass",
      leafAreaIndex: "Leaf area index",
      temperatureSum: "Temperature sum",
      canopy24h: "Canopy 24h",
      tourKicker: "PROJECT WALKTHROUGH",
      tourTitle: "Understand the digital greenhouse in three steps",
      tourBody: "Start with weather and control targets, then watch the model connect climate, actuators, crop growth, and resource use.",
      tourStepOneTitle: "Choose a scenario",
      tourStepOneBody: "Switch seasons and measured weather conditions to create different outdoor disturbances.",
      tourStepTwoTitle: "Compare control strategies",
      tourStepTwoBody: "Use the rule-based controller or manually adjust the six absolute GreenLight controls.",
      tourStepThreeTitle: "Read the system response",
      tourStepThreeBody: "Track climate, crop state, limit warnings, energy, CO₂, and estimated cost.",
      liveEngine: "LIVE ENGINE",
      modelTransparency: "The interface always identifies the active engine; the approximation is never presented as a scientific result.",
      goToControls: "Go to the controls",
      closeTour: "Close walkthrough",
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
      comparisonTitle: "Strategy comparison workbench",
      decisionSupport: "Decision support",
      comparisonIntro: "Save one completed run, then reset and test another strategy for the same number of steps.",
      saveBaseline: "Save current result as baseline",
      replaceBaseline: "Replace baseline with current result",
      clearBaseline: "Clear",
      comparisonEmpty: "Run at least one simulation step to save a baseline.",
      comparisonReadyToSave: "The current result is ready to save as a baseline.",
      baselineNeedsRun: "Run at least one simulation step first.",
      baselineRun: "Baseline",
      candidateRun: "Current run",
      heatingDelta: "Heating delta",
      lightingDelta: "Lighting delta",
      co2UseDelta: "CO₂ delta",
      costDelta: "Cost delta",
      fruitMassDelta: "Fruit dry-mass delta",
      endStateAlerts: "End-state alerts",
      comparisonCaution: "Green only marks lower resource use or higher fruit dry mass; it is not an overall winner and is not production advice.",
      comparisonNeedsCandidate: "Baseline saved. Reset, then run the candidate strategy to step {step}.",
      comparisonReady: "Comparable: both runs cover {steps} steps ({hours} hours).",
      comparisonStepMismatch: "Run the current strategy to step {steps}; it is now at step {current}. Deltas stay hidden until horizons match.",
      comparisonEngineMismatch: "The model engines differ, so comparison is blocked. Baseline: {baseline}; current: {candidate}.",
      comparisonWeatherMatch: "Weather scenarios match, which helps isolate control-strategy effects.",
      comparisonWeatherDifference: "Weather scenarios differ; the result combines weather and control effects.",
      comparisonMeta: "STEP {step} · {mode} · {engine}",
      comparisonAutoStrategy: "Day {day}°C · night {night}°C · CO₂ {co2} ppm · RH ≤ {rh}%",
      comparisonManualStrategy: "Boiler {boil}% · CO₂ {co2}% · thermal {thermal}% · vent {vent}% · lamp {lamp}% · blackout {blackout}%",
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
      fullModelTour: "Connected to the 28-state GreenLight-Gym2 CasADi model with measured Amsterdam weather.",
      browserModelTour: "Using the browser approximation for installation-free interaction; it is not a full scientific result.",
      offlineModelTour: "The scientific backend is offline; interaction has safely switched to the browser approximation.",
      switchToEnglish: "Switch to English",
      switchToChinese: "切換為中文",
      roomBelow15: "Room temperature is below 15°C",
      roomAbove34: "Room temperature is above 34°C",
      humidityBelow50: "Relative humidity is below 50%",
      humidityAbove85: "Relative humidity is above 85%",
      co2Below300: "CO₂ is below 300 ppm",
      co2Above1600: "CO₂ is above 1600 ppm",
      backendInvalidResponse: "The backend returned invalid data (HTTP {status})",
      backendRequestFailed: "Backend request failed (HTTP {status})",
      temperatureDelta: "{value}°C from target",
      humidityRemaining: "{value}% below limit",
      humidityExceeded: "{value}% above limit",
      co2TargetValue: "Target {value} ppm",
      boilerValue: "Boiler {value}%",
      dayClock: "Day {day} · {time}",
      humidityChart: "Relative humidity over the last 24 hours",
      indoorRh: "Indoor RH",
      outdoorRh: "Outdoor RH",
      controlLimit: "Control limit",
      co2Chart: "Indoor carbon dioxide over the last 24 hours",
      indoorCo2Series: "Indoor CO₂",
      controlTarget: "Control target",
      temperatureChart: "Indoor, canopy, and outdoor temperature over the last 24 hours",
      indoorSeries: "Indoor",
      canopySeries: "Canopy",
      outdoorSeries: "Outdoor",
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

  function formatTranslation(key, replacements = {}) {
    return t(key).replace(/\{([A-Za-z0-9_]+)\}/g, (match, name) => (
      Object.prototype.hasOwnProperty.call(replacements, name)
        ? String(replacements[name])
        : match
    ));
  }

  function applyLanguage() {
    const documentLanguage = language === "en" ? "en" : "zh-Hant";
    document.documentElement.lang = documentLanguage;
    byId("controlPanel").lang = documentLanguage;
    root.dataset.language = language;
    document.title = t("documentTitle");
    const description = document.querySelector('meta[name="description"]');
    if (description) description.setAttribute("content", t("metaDescription"));
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
    updateRunStateCopy();
    render(currentSnapshot);
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

  function createRunId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function createRunSummary(snapshot) {
    return {
      schemaVersion: 1,
      runId: currentRunId,
      savedAt: new Date().toISOString(),
      modelStep: Number(snapshot.modelStep),
      elapsedMinutes: Number(snapshot.elapsedMinutes),
      scenario: String(snapshot.scenario),
      scenarioLabel: String(snapshot.scenarioLabel || snapshot.scenario),
      mode: String(snapshot.mode),
      engine: activeEngine === "greenlight2" ? "greenlight2" : "browser",
      targets: { ...snapshot.targets },
      controls: { ...snapshot.controls },
      resources: {
        heatKwh: Number(snapshot.resources.heatKwh),
        lampKwh: Number(snapshot.resources.lampKwh),
        co2Kg: Number(snapshot.resources.co2Kg),
        costEur: Number(snapshot.resources.costEur),
      },
      crop: { fruitDryMass: Number(snapshot.crop.fruitDryMass) },
      alertCount: Array.isArray(snapshot.violations) ? snapshot.violations.length : 0,
    };
  }

  function isRunSummary(value) {
    if (!value || value.schemaVersion !== 1 || typeof value.runId !== "string") return false;
    if (typeof value.scenario !== "string" || !["auto", "manual"].includes(value.mode)) return false;
    if (!["browser", "greenlight2"].includes(value.engine)) return false;
    const numericValues = [
      value.modelStep,
      value.elapsedMinutes,
      value.resources?.heatKwh,
      value.resources?.lampKwh,
      value.resources?.co2Kg,
      value.resources?.costEur,
      value.crop?.fruitDryMass,
      value.alertCount,
      value.targets?.dayTemp,
      value.targets?.nightTemp,
      value.targets?.co2,
      value.targets?.maxRh,
      value.controls?.uBoil,
      value.controls?.uCO2,
      value.controls?.uThScr,
      value.controls?.uVent,
      value.controls?.uLamp,
      value.controls?.uBlScr,
    ];
    return numericValues.every((item) => typeof item === "number" && Number.isFinite(item));
  }

  function restoreBaselineRun() {
    try {
      const stored = window.localStorage.getItem(BASELINE_STORAGE_KEY);
      if (!stored) return;
      const parsed = JSON.parse(stored);
      if (isRunSummary(parsed)) baselineRun = parsed;
    } catch {
      // Comparison remains available in memory when storage is blocked or invalid.
    }
  }

  function translatedScenario(summary) {
    const scenarioKeys = {
      spring: "scenarioSpring",
      cloudy: "scenarioCloudy",
      summer: "scenarioSummer",
      winter: "scenarioWinter",
    };
    const key = scenarioKeys[summary.scenario];
    return key ? t(key) : summary.scenarioLabel;
  }

  function comparisonEngineLabel(engine) {
    return t(engine === "greenlight2" ? "fullModel" : "approximateModel");
  }

  function comparisonRunMeta(summary) {
    return formatTranslation("comparisonMeta", {
      step: String(summary.modelStep).padStart(4, "0"),
      mode: t(summary.mode === "manual" ? "manualControl" : "autoControl"),
      engine: comparisonEngineLabel(summary.engine),
    });
  }

  function comparisonStrategy(summary) {
    if (summary.mode === "manual") {
      return formatTranslation("comparisonManualStrategy", {
        boil: Math.round(summary.controls.uBoil * 100),
        co2: Math.round(summary.controls.uCO2 * 100),
        thermal: Math.round(summary.controls.uThScr * 100),
        vent: Math.round(summary.controls.uVent * 100),
        lamp: Math.round(summary.controls.uLamp * 100),
        blackout: Math.round(summary.controls.uBlScr * 100),
      });
    }
    return formatTranslation("comparisonAutoStrategy", {
      day: formatNumber(summary.targets.dayTemp),
      night: formatNumber(summary.targets.nightTemp),
      co2: formatNumber(summary.targets.co2, 0),
      rh: formatNumber(summary.targets.maxRh, 0),
    });
  }

  function clearComparisonDeltas() {
    [
      "comparisonHeatDelta",
      "comparisonLampDelta",
      "comparisonCo2Delta",
      "comparisonCostDelta",
      "comparisonFruitDelta",
      "comparisonAlertDelta",
    ].forEach((id) => {
      const element = byId(id);
      element.textContent = "—";
      delete element.dataset.impact;
    });
  }

  function setComparisonDelta(id, candidateValue, baselineValue, digits, unit, preferredDirection) {
    const element = byId(id);
    const rawDelta = candidateValue - baselineValue;
    const tolerance = (10 ** -digits) / 2;
    const delta = Math.abs(rawDelta) < tolerance ? 0 : rawDelta;
    const sign = delta > 0 ? "+" : delta < 0 ? "−" : "";
    element.textContent = `${sign}${formatNumber(Math.abs(delta), digits)} ${unit}`;
    element.dataset.impact = "neutral";
    if (delta === 0) return;
    const preferred = preferredDirection === "lower" ? delta < 0 : delta > 0;
    element.dataset.impact = preferred ? "favourable" : "unfavourable";
  }

  function setAlertComparison(candidateCount, baselineCount) {
    const element = byId("comparisonAlertDelta");
    element.textContent = `${baselineCount} → ${candidateCount}`;
    element.dataset.impact = candidateCount === baselineCount
      ? "neutral"
      : candidateCount < baselineCount ? "favourable" : "unfavourable";
  }

  function renderComparison(snapshot) {
    const saveButton = byId("saveBaselineButton");
    const clearButton = byId("clearBaselineButton");
    const empty = byId("comparisonEmpty");
    const content = byId("comparisonContent");
    const canSave = Number(snapshot.modelStep) > 0;

    saveButton.disabled = !canSave;
    saveButton.title = canSave ? "" : t("baselineNeedsRun");
    saveButton.textContent = t(baselineRun ? "replaceBaseline" : "saveBaseline");
    clearButton.disabled = !baselineRun;
    empty.classList.toggle("hidden", Boolean(baselineRun));
    content.classList.toggle("hidden", !baselineRun);

    if (!baselineRun) {
      empty.textContent = t(canSave ? "comparisonReadyToSave" : "comparisonEmpty");
      clearComparisonDeltas();
      return;
    }

    const candidate = createRunSummary(snapshot);
    setText("baselineScenario", translatedScenario(baselineRun));
    setText("candidateScenario", translatedScenario(candidate));
    setText("baselineMeta", comparisonRunMeta(baselineRun));
    setText("candidateMeta", comparisonRunMeta(candidate));
    const baselineStrategy = comparisonStrategy(baselineRun);
    const candidateStrategy = comparisonStrategy(candidate);
    setText("baselineStrategy", baselineStrategy);
    setText("candidateStrategy", candidateStrategy);
    byId("baselineStrategy").title = baselineStrategy;
    byId("candidateStrategy").title = candidateStrategy;

    const status = byId("comparisonStatus");
    const sameEngine = baselineRun.engine === candidate.engine;
    const sameRun = baselineRun.runId === candidate.runId;
    const sameHorizon = baselineRun.modelStep === candidate.modelStep && candidate.modelStep > 0;
    let comparable = false;

    if (!sameEngine) {
      status.dataset.state = "blocked";
      status.textContent = formatTranslation("comparisonEngineMismatch", {
        baseline: comparisonEngineLabel(baselineRun.engine),
        candidate: comparisonEngineLabel(candidate.engine),
      });
    } else if (sameRun) {
      status.dataset.state = "pending";
      status.textContent = formatTranslation("comparisonNeedsCandidate", {
        step: baselineRun.modelStep,
      });
    } else if (!sameHorizon) {
      status.dataset.state = "pending";
      status.textContent = formatTranslation("comparisonStepMismatch", {
        steps: baselineRun.modelStep,
        current: candidate.modelStep,
      });
    } else {
      status.dataset.state = "ready";
      status.textContent = formatTranslation("comparisonReady", {
        steps: candidate.modelStep,
        hours: formatNumber(candidate.elapsedMinutes / 60, 2),
      });
      comparable = true;
    }

    const sameWeather = baselineRun.scenario === candidate.scenario;
    const context = byId("comparisonContext");
    context.dataset.state = sameWeather ? "matched" : "changed";
    context.textContent = t(sameWeather ? "comparisonWeatherMatch" : "comparisonWeatherDifference");

    if (!comparable) {
      clearComparisonDeltas();
      return;
    }

    setComparisonDelta("comparisonHeatDelta", candidate.resources.heatKwh, baselineRun.resources.heatKwh, 3, "kWh/m²", "lower");
    setComparisonDelta("comparisonLampDelta", candidate.resources.lampKwh, baselineRun.resources.lampKwh, 3, "kWh/m²", "lower");
    setComparisonDelta("comparisonCo2Delta", candidate.resources.co2Kg, baselineRun.resources.co2Kg, 3, "kg/m²", "lower");
    setComparisonDelta("comparisonCostDelta", candidate.resources.costEur, baselineRun.resources.costEur, 3, "€/m²", "lower");
    setComparisonDelta("comparisonFruitDelta", candidate.crop.fruitDryMass, baselineRun.crop.fruitDryMass, 2, "g/m²", "higher");
    setAlertComparison(candidate.alertCount, baselineRun.alertCount);
  }

  function saveBaseline() {
    if (Number(currentSnapshot.modelStep) <= 0) return;
    baselineRun = createRunSummary(currentSnapshot);
    try {
      window.localStorage.setItem(BASELINE_STORAGE_KEY, JSON.stringify(baselineRun));
    } catch {
      // The saved comparison remains usable for this page session.
    }
    renderComparison(currentSnapshot);
  }

  function clearBaseline() {
    baselineRun = null;
    try {
      window.localStorage.removeItem(BASELINE_STORAGE_KEY);
    } catch {
      // Clearing the in-memory baseline is sufficient when storage is blocked.
    }
    renderComparison(currentSnapshot);
  }

  function updateEngineStatus(engine, reason = "") {
    const badge = byId("engineBadge");
    const tourCard = byId("tourModelCard");
    engineDisplayState = engine;
    engineDisplayReason = reason;
    badge.dataset.engine = engine;
    if (tourCard) tourCard.dataset.engine = engine;
    let labelKey = "approximateModel";
    let note = t("browserModelNote");
    let tourDescription = t("browserModelTour");
    if (engine === "greenlight2") {
      labelKey = "fullModel";
      note = t("fullModelNote");
      tourDescription = t("fullModelTour");
    } else if (engine === "error") {
      labelKey = "offlineModel";
      note = t("offlineModelNote");
      tourDescription = t("offlineModelTour");
    }
    setText("engineLabel", t(labelKey));
    setText("modelNote", note);
    setText("tourModelTitle", t(labelKey));
    setText("tourEngineDescription", tourDescription);
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
      throw new Error(formatTranslation("backendInvalidResponse", { status: response.status }));
    }
    if (!response.ok || body.ok === false) {
      throw new Error(body?.error?.message || formatTranslation("backendRequestFailed", { status: response.status }));
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
      currentRunId = createRunId();
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
      const snapshot = model.reset();
      currentRunId = createRunId();
      return snapshot;
    }
    const response = await requestApi("/api/reset", {
      seed: 42,
      scenario: byId("scenarioSelect").value,
      mode: currentSnapshot.mode,
      targets: readTargets(),
      expectedRevision: remoteRevision,
    });
    remoteRevision = response.revision;
    currentRunId = createRunId();
    return response.snapshot;
  }

  function switchToBrowserFallback(reason) {
    activeEngine = "browser";
    remoteRevision = null;
    model.setScenario(byId("scenarioSelect").value);
    model.setMode(currentSnapshot.mode);
    Object.entries(readTargets()).forEach(([name, value]) => model.setTarget(name, value));
    const snapshot = model.reset();
    currentRunId = createRunId();
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
      formatTranslation("temperatureDelta", {
        value: `${tempDifference >= 0 ? "+" : ""}${formatNumber(tempDifference)}`,
      }),
    );
    setText("rhValue", formatNumber(indoor.rh, 0));
    setText(
      "rhDelta",
      formatTranslation(rhHeadroom >= 0 ? "humidityRemaining" : "humidityExceeded", {
        value: formatNumber(Math.abs(rhHeadroom), 0),
      }),
    );
    setText("co2Value", formatNumber(indoor.co2, 0));
    setText("co2Delta", formatTranslation("co2TargetValue", { value: formatNumber(snapshot.targets.co2, 0) }));
    setText("pipeTempValue", formatNumber(indoor.pipeTemp));
    setText("boilerState", formatTranslation("boilerValue", { value: Math.round(u.uBoil * 100) }));
    setText("heatUse", `${formatNumber(resources.heatKwh, 3)} kWh/m²`);

    setStatus("tempStatusDot", indoor.airTemp, 15, 34, 2);
    setStatus("rhStatusDot", indoor.rh, 50, 85, 5);
    setStatus("co2StatusDot", indoor.co2, 300, 1600, 140);

    setText("clockLabel", formatTranslation("dayClock", {
      day: snapshot.dayOfYear,
      time: formatClock(snapshot.minuteOfDay),
    }));
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

    renderComparison(snapshot);
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
        label: t("humidityChart"),
        minSpan: 20,
        series: [
          { label: t("indoorRh"), color: blue, values: history.map((point) => point.rh) },
          { label: t("outdoorRh"), color: muted, values: history.map((point) => point.outsideRh), dash: [4, 4] },
          { label: t("controlLimit"), color: amber, values: history.map(() => targets.maxRh), dash: [7, 5] },
        ],
      };
    }

    if (chartMode === "co2") {
      return {
        unit: " ppm",
        label: t("co2Chart"),
        minSpan: 300,
        series: [
          { label: t("indoorCo2Series"), color: green, values: history.map((point) => point.co2) },
          { label: t("controlTarget"), color: violet, values: history.map(() => targets.co2), dash: [7, 5] },
        ],
      };
    }

    return {
      unit: "°C",
      label: t("temperatureChart"),
      minSpan: 10,
      series: [
        { label: t("indoorSeries"), color: green, values: history.map((point) => point.airTemp) },
        { label: t("canopySeries"), color: amber, values: history.map((point) => point.canopyTemp) },
        { label: t("outdoorSeries"), color: blue, values: history.map((point) => point.outsideTemp), dash: [4, 4] },
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
    liveIndicator.classList.toggle("running", isRunning);
    updateRunStateCopy();

    if (timerId !== null) {
      window.clearTimeout(timerId);
      timerId = null;
    }

    if (isRunning) {
      timerId = window.setTimeout(runTick, 120);
    }
  }

  function updateRunStateCopy() {
    setText("playLabel", isRunning ? t("pauseSimulation") : t("startSimulation"));
    const liveIndicator = byId("liveIndicator");
    if (liveIndicator) {
      liveIndicator.querySelector("span").textContent = isRunning
        ? t("simulationRunning")
        : t("simulationPaused");
    }
  }

  function focusSimulatorControls() {
    const dialog = byId("projectDialog");
    if (dialog?.open) dialog.close();
    const controlPanel = byId("controlPanel");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    controlPanel.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    byId("playButton").focus({ preventScroll: true });
  }

  function openProjectDialog() {
    const dialog = byId("projectDialog");
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }

  function closeProjectDialog() {
    const dialog = byId("projectDialog");
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
  }

  function bindEvents() {
    byId("languageToggle").addEventListener("click", toggleLanguage);
    byId("playButton").addEventListener("click", () => setRunning(!isRunning));
    byId("saveBaselineButton").addEventListener("click", saveBaseline);
    byId("clearBaselineButton").addEventListener("click", clearBaseline);
    byId("showcaseStartButton").addEventListener("click", focusSimulatorControls);
    byId("tourButton").addEventListener("click", openProjectDialog);
    byId("tourCloseButton").addEventListener("click", closeProjectDialog);
    byId("tourExploreButton").addEventListener("click", focusSimulatorControls);
    byId("projectDialog").addEventListener("click", (event) => {
      if (event.target === byId("projectDialog")) closeProjectDialog();
    });

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
        const snapshot = model.setScenario(event.target.value);
        currentRunId = createRunId();
        render(snapshot);
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

  restoreBaselineRun();
  applyLanguage();
  bindEvents();
  render(currentSnapshot);
  probeBackend();
}());
