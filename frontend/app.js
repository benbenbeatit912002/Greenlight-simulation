(function () {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const root = byId("simulatorApp");
  const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));

  let isRunning = false;
  let speed = 4;
  let chartMode = "temperature";
  let timerId = null;
  let resizeFrame = null;
  let currentSnapshot = null;
  let activeEngine = "unavailable";
  let engineDisplayState = "error";
  let engineDisplayReason = "";
  let remoteRevision = null;
  let remoteBusy = false;
  let connectionBusy = false;
  let language = "zh";
  let baselineRun = null;
  let currentRunId = createRunId();
  let selectedWeatherId = null;
  let selectedRunWindow = null;
  let resetBusy = false;
  let pendingStep = Promise.resolve();
  let selectedGreenhouseConfig = { schemaVersion: 1, overrides: {} };

  const BASELINE_STORAGE_KEY = "greenlight-decision-baseline-v2";
  const PROVENANCE_SENTINELS = ["unknown", "unversioned", "local-source"];

  const translations = window.GreenlightTranslations;
  const renderChart = window.GreenlightCharts.createRenderer({ byId, t, formatHour });

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
    return t(key).replace(/\{([A-Za-z0-9_]+)\}/g, (match, name) =>
      Object.prototype.hasOwnProperty.call(replacements, name) ? String(replacements[name]) : match,
    );
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
    toggle.setAttribute(
      "aria-label",
      language === "zh" ? t("switchToEnglish") : t("switchToChinese"),
    );
    byId("languageToggleTop").textContent = language === "zh" ? "EN" : "中文";
    byId("languageToggleTop").setAttribute("aria-label", toggle.getAttribute("aria-label"));
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
    const readBoundedTarget = (inputId, targetName) => {
      const input = byId(inputId);
      const value = Number(input.value);
      const minimum = Number(input.min);
      const maximum = Number(input.max);
      if (!Number.isFinite(value) || value < minimum || value > maximum || !input.checkValidity()) {
        const fallback = Number(currentSnapshot?.targets[targetName] ?? input.defaultValue);
        input.value = String(fallback);
        return fallback;
      }
      return value;
    };
    return {
      dayTemp: readBoundedTarget("dayTempTarget", "dayTemp"),
      nightTemp: readBoundedTarget("nightTempTarget", "nightTemp"),
      co2: readBoundedTarget("co2Target", "co2"),
      maxRh: readBoundedTarget("rhTarget", "maxRh"),
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
      schemaVersion: 2,
      runId: currentRunId,
      savedAt: new Date().toISOString(),
      modelStep: Number(snapshot.modelStep),
      elapsedMinutes: Number(snapshot.elapsedMinutes),
      scenario: String(snapshot.scenario),
      scenarioLabel: String(snapshot.scenarioLabel || snapshot.scenario),
      mode: String(snapshot.mode),
      engine: activeEngine === "greenlight2" ? "greenlight2" : "browser",
      modelVersion: String(snapshot.modelVersion || "unknown"),
      costModelId: String(snapshot.costModelId || "unknown"),
      weatherFingerprint: String(snapshot.weatherFingerprint || "unknown"),
      configurationFingerprint: String(snapshot.configurationFingerprint || "unknown"),
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
    if (!value || value.schemaVersion !== 2 || typeof value.runId !== "string") return false;
    if (typeof value.scenario !== "string" || !["auto", "manual"].includes(value.mode))
      return false;
    if (!["browser", "greenlight2"].includes(value.engine)) return false;
    if (typeof value.modelVersion !== "string" || !value.modelVersion) return false;
    if (typeof value.costModelId !== "string" || !value.costModelId) return false;
    if (typeof value.weatherFingerprint !== "string" || !value.weatherFingerprint) return false;
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
      uploaded: "uploadedWeather",
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
      version: displayModelVersion(summary.modelVersion),
    });
  }

  function displayModelVersion(version) {
    return version
      .replace(/(git\.[0-9a-f]{8})[0-9a-f]{32}/gi, "$1")
      .replace(/(sha256\.[0-9a-f]{8})[0-9a-f]{56}/gi, "$1")
      .replace(/(params\.[0-9a-f]{8})[0-9a-f]{56}/gi, "$1");
  }

  function displayFingerprint(value) {
    return value.replace(/([0-9a-f]{8})[0-9a-f]{32,56}/gi, "$1");
  }

  function comparisonModelLabel(summary) {
    return `${comparisonEngineLabel(summary.engine)} ${displayModelVersion(summary.modelVersion)} / ${summary.costModelId} / weather ${displayFingerprint(summary.weatherFingerprint)}`;
  }

  function hasComparableProvenance(summary) {
    return [
      summary.modelVersion,
      summary.costModelId,
      summary.weatherFingerprint,
      summary.configurationFingerprint,
    ].every(
      (value) =>
        typeof value === "string" &&
        value.length > 0 &&
        !PROVENANCE_SENTINELS.some((sentinel) => value.toLowerCase().includes(sentinel)),
    );
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
    const tolerance = 10 ** -digits / 2;
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
    element.dataset.impact =
      candidateCount === baselineCount
        ? "neutral"
        : candidateCount < baselineCount
          ? "favourable"
          : "unfavourable";
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
    const sameWeatherEvidence =
      baselineRun.scenario !== candidate.scenario ||
      baselineRun.weatherFingerprint === candidate.weatherFingerprint;
    const sameModel =
      hasComparableProvenance(baselineRun) &&
      hasComparableProvenance(candidate) &&
      baselineRun.modelVersion === candidate.modelVersion &&
      baselineRun.costModelId === candidate.costModelId &&
      baselineRun.configurationFingerprint === candidate.configurationFingerprint &&
      sameWeatherEvidence;
    const sameRun = baselineRun.runId === candidate.runId;
    const sameHorizon = baselineRun.modelStep === candidate.modelStep && candidate.modelStep > 0;
    let comparable = false;

    if (!sameEngine) {
      status.dataset.state = "blocked";
      status.textContent = formatTranslation("comparisonEngineMismatch", {
        baseline: comparisonEngineLabel(baselineRun.engine),
        candidate: comparisonEngineLabel(candidate.engine),
      });
    } else if (!sameModel) {
      status.dataset.state = "blocked";
      status.textContent = formatTranslation("comparisonModelMismatch", {
        baseline: comparisonModelLabel(baselineRun),
        candidate: comparisonModelLabel(candidate),
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

    setComparisonDelta(
      "comparisonHeatDelta",
      candidate.resources.heatKwh,
      baselineRun.resources.heatKwh,
      3,
      "kWh/m²",
      "lower",
    );
    setComparisonDelta(
      "comparisonLampDelta",
      candidate.resources.lampKwh,
      baselineRun.resources.lampKwh,
      3,
      "kWh/m²",
      "lower",
    );
    setComparisonDelta(
      "comparisonCo2Delta",
      candidate.resources.co2Kg,
      baselineRun.resources.co2Kg,
      3,
      "kg/m²",
      "lower",
    );
    setComparisonDelta(
      "comparisonCostDelta",
      candidate.resources.costEur,
      baselineRun.resources.costEur,
      3,
      "€/m²",
      "lower",
    );
    setComparisonDelta(
      "comparisonFruitDelta",
      candidate.crop.fruitDryMass,
      baselineRun.crop.fruitDryMass,
      2,
      "g/m²",
      "higher",
    );
    setAlertComparison(candidate.alertCount, baselineRun.alertCount);
  }

  function saveBaseline() {
    if (!currentSnapshot) return;
    if (Number(currentSnapshot.modelStep) <= 0) return;
    baselineRun = createRunSummary(currentSnapshot);
    try {
      window.localStorage.setItem(BASELINE_STORAGE_KEY, JSON.stringify(baselineRun));
    } catch {
      // The saved comparison remains usable for this page session.
    }
    if (currentSnapshot) renderComparison(currentSnapshot);
  }

  function clearBaseline() {
    baselineRun = null;
    try {
      window.localStorage.removeItem(BASELINE_STORAGE_KEY);
    } catch {
      // Clearing the in-memory baseline is sufficient when storage is blocked.
    }
    if (currentSnapshot) renderComparison(currentSnapshot);
  }

  function updateEngineStatus(engine, reason = "") {
    const badge = byId("engineBadge");
    const tourCard = byId("tourModelCard");
    engineDisplayState = engine;
    engineDisplayReason = reason;
    badge.dataset.engine = engine;
    if (tourCard) tourCard.dataset.engine = engine;
    let labelKey = "offlineModel";
    let note = t("offlineModelNote");
    let tourDescription = t("offlineModelTour");
    if (engine === "greenlight2") {
      labelKey = "fullModel";
      const uploaded = Boolean(selectedWeatherId || currentSnapshot?.weatherId);
      note = t(uploaded ? "fullModelUploadedNote" : "fullModelNote");
      tourDescription = t(uploaded ? "fullModelUploadedTour" : "fullModelTour");
    } else if (engine === "error") {
      labelKey = "offlineModel";
      note = t("offlineModelNote");
      tourDescription = t("offlineModelTour");
    }
    setText("engineLabel", t(labelKey));
    setText("modelNote", note);
    setText("tourModelTitle", t(labelKey));
    setText("tourEngineDescription", tourDescription);
    setText("modelConnectionText", note);
    setText("modelConnectionReason", reason);
    byId("retryModelButton").hidden = engine === "greenlight2";
    byId("retryModelButton").disabled = connectionBusy;
    ["playButton", "resetButton", "scenarioSelect"].forEach((id) => {
      byId(id).disabled = engine !== "greenlight2";
    });
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
      const error = new Error(
        body?.error?.message ||
          formatTranslation("backendRequestFailed", { status: response.status }),
      );
      error.code = body?.error?.code;
      error.revision = body?.revision;
      throw error;
    }
    return body;
  }

  async function probeBackend(allowRecovery = false) {
    if (connectionBusy) return;
    connectionBusy = true;
    byId("retryModelButton").disabled = true;
    try {
      let status;
      try {
        status = await requestApi("/api/status");
      } catch (error) {
        if (!allowRecovery || error.code !== "MODEL_ERROR") throw error;
        status = await requestApi("/api/reset", {
          seed: 42,
          scenario: selectedWeatherId ? "uploaded" : byId("scenarioSelect").value,
          ...(selectedWeatherId
            ? { weatherId: selectedWeatherId, runWindow: selectedRunWindow }
            : {}),
          mode: "auto",
          targets: readTargets(),
          expectedRevision: error.revision,
          greenhouseConfig: selectedGreenhouseConfig,
        });
      }
      requireScientificResponse(status);
      activeEngine = "greenlight2";
      remoteRevision = status.revision;
      currentRunId = status.snapshot.runId;
      selectedWeatherId = status.snapshot.weatherId || null;
      selectedRunWindow = window.GreenlightRunWindow.recipe(status.snapshot.runWindow);
      updateEngineStatus("greenlight2");
      byId("scenarioSelect").value = status.snapshot.scenario;
      const targetIds = {
        dayTemp: "dayTempTarget",
        nightTemp: "nightTempTarget",
        co2: "co2Target",
        maxRh: "rhTarget",
      };
      Object.entries(targetIds).forEach(([key, id]) => {
        byId(id).value = status.snapshot.targets[key];
      });
      render(status.snapshot);
    } catch (error) {
      showModelUnavailable(error instanceof Error ? error.message : String(error));
    } finally {
      connectionBusy = false;
      byId("retryModelButton").disabled = false;
    }
  }

  function requireScientificResponse(response) {
    if (
      response.engine?.scientific !== true ||
      response.engine.active !== "greenlight-gym2" ||
      response.snapshot?.engine !== "greenlight-gym2" ||
      response.snapshot.episode?.truncated ||
      typeof response.snapshot.runId !== "string" ||
      !response.snapshot.runId
    ) {
      throw new Error(response.engine?.fallbackReason || t("offlineModelNote"));
    }
  }

  async function stepActiveEngine(stepCount) {
    if (activeEngine !== "greenlight2" || !currentSnapshot) throw new Error(t("offlineModelNote"));
    const response = await requestApi("/api/step", {
      steps: stepCount,
      mode: currentSnapshot.mode,
      controls: readControls(),
      targets: readTargets(),
      expectedRevision: remoteRevision,
    });
    remoteRevision = response.revision;
    requireScientificResponse(response);
    return response.snapshot;
  }

  async function resetActiveEngine(greenhouseConfig = selectedGreenhouseConfig) {
    if (activeEngine !== "greenlight2" || !currentSnapshot) throw new Error(t("offlineModelNote"));
    if (resetBusy) throw new Error(t("simulationInitializing"));
    resetBusy = true;
    window.GreenlightSettings.setBusy(true);
    setRunning(false);
    try {
      await pendingStep;
      if (activeEngine !== "greenlight2" || !currentSnapshot)
        throw new Error(t("offlineModelNote"));
      const response = await requestApi("/api/reset", {
        seed: 42,
        scenario: selectedWeatherId ? "uploaded" : byId("scenarioSelect").value,
        ...(selectedWeatherId
          ? { weatherId: selectedWeatherId, runWindow: selectedRunWindow }
          : {}),
        mode: currentSnapshot.mode,
        targets: readTargets(),
        expectedRevision: remoteRevision,
        greenhouseConfig,
      });
      remoteRevision = response.revision;
      requireScientificResponse(response);
      currentRunId = response.snapshot.runId;
      selectedRunWindow = window.GreenlightRunWindow.recipe(response.snapshot.runWindow);
      return response.snapshot;
    } finally {
      resetBusy = false;
      window.GreenlightSettings.setBusy(false);
      updateRunStateCopy();
    }
  }

  function showModelUnavailable(reason) {
    setRunning(false);
    activeEngine = "unavailable";
    remoteRevision = null;
    currentSnapshot = null;
    window.GreenlightSettings.unavailable();
    byId("runProgressPanel").hidden = true;
    root.classList.add("model-unavailable");
    updateEngineStatus("error", reason);
  }

  function showResetFailure(error) {
    if (error.code === "RESET_REJECTED" && currentSnapshot) {
      selectedWeatherId = currentSnapshot.weatherId || null;
      selectedRunWindow = window.GreenlightRunWindow.recipe(currentSnapshot.runWindow);
      byId("scenarioSelect").value = currentSnapshot.scenario;
      updateRunStateCopy();
      renderRunProgress();
      setText("runProgressText", error.message);
    } else {
      showModelUnavailable(error instanceof Error ? error.message : String(error));
    }
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
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
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
    const daylight = clamp(outdoor.daylight, 0, 1);
    const solarProgress = clamp(
      (snapshot.hour - outdoor.sunrise) / Math.max(outdoor.sunset - outdoor.sunrise, 0.1),
      0,
      1,
    );
    const sunX = 10 + solarProgress * 66;
    const sunY = 54 - Math.sin(Math.PI * solarProgress) * 37;
    const fruitScale = clamp(0.8 + (crop.fruitDryMass - 50) / 70, 0.8, 1.25);
    const condensation = clamp((indoor.rh - 81) / 12, 0, 0.9);

    root.style.setProperty("--daylight", daylight.toFixed(3));
    root.style.setProperty("--sun-x", `${sunX.toFixed(1)}%`);
    root.style.setProperty("--sun-y", `${sunY.toFixed(1)}%`);
    root.style.setProperty(
      "--cloud-opacity",
      outdoor.cloud === null
        ? "0"
        : (0.06 + outdoor.cloud * 0.7 * Math.max(daylight, 0.28)).toFixed(2),
    );
    root.style.setProperty("--lamp-power", u.uLamp.toFixed(3));
    root.style.setProperty("--boiler-power", u.uBoil.toFixed(3));
    root.style.setProperty("--co2-power", u.uCO2.toFixed(3));
    root.style.setProperty("--thermal-position", u.uThScr.toFixed(3));
    root.style.setProperty("--blackout-position", u.uBlScr.toFixed(3));
    root.style.setProperty("--vent-angle", `${(-2 - u.uVent * 25).toFixed(1)}deg`);
    root.style.setProperty("--condensation-opacity", condensation.toFixed(2));
    root.style.setProperty("--fruit-scale", fruitScale.toFixed(2));

    const windLines = byId("windLines");
    windLines.style.opacity = String(clamp(0.12 + outdoor.wind / 9, 0.15, 0.72));
    windLines.style.setProperty("--wind-duration", `${clamp(4.2 - outdoor.wind * 0.55, 1.15, 4)}s`);
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
    if (!snapshot) return;
    root.classList.remove("model-unavailable");
    currentSnapshot = snapshot;
    selectedGreenhouseConfig = snapshot.greenhouse?.request || selectedGreenhouseConfig;
    window.GreenlightSettings.sync(snapshot);
    currentRunId = snapshot.runId;
    const { indoor, outdoor, crop, resources, controls: u } = snapshot;
    const tempTarget =
      outdoor.daylight > 0.06 ? snapshot.targets.dayTemp : snapshot.targets.nightTemp;
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
    setText(
      "co2Delta",
      formatTranslation("co2TargetValue", { value: formatNumber(snapshot.targets.co2, 0) }),
    );
    setText("pipeTempValue", formatNumber(indoor.pipeTemp));
    setText("insideRadiationValue", formatNumber(indoor.insideRadiation, 0));
    setText("absorbedParValue", formatNumber(indoor.canopyAbsorbedPar, 1));
    setText("boilerState", formatTranslation("boilerValue", { value: Math.round(u.uBoil * 100) }));
    setText("heatUse", `${formatNumber(resources.heatKwh, 3)} kWh/m²`);

    setStatus("tempStatusDot", indoor.airTemp, 15, 34, 2);
    setStatus("rhStatusDot", indoor.rh, 50, 85, 5);
    setStatus("co2StatusDot", indoor.co2, 300, 1600, 140);

    setText(
      "clockLabel",
      formatTranslation("dayClock", {
        day: snapshot.dayOfYear,
        time: formatClock(snapshot.minuteOfDay),
      }),
    );
    setText("outsideRadiation", formatNumber(outdoor.radiation, 0));
    setText("outsideTemp", formatNumber(outdoor.temperature));
    setText("outsideWind", formatNumber(outdoor.wind));
    setText("stepValue", String(snapshot.modelStep).padStart(4, "0"));

    setText(
      "svgClimateValue",
      `${formatNumber(indoor.airTemp)}°C · ${formatNumber(indoor.rh, 0)}%`,
    );
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
    updateEngineStatus("greenlight2");
    updateRunStateCopy();
    renderRunProgress();
    updateAlert(snapshot);
    drawChart(snapshot.history, snapshot.targets);
  }

  function drawChart(history, targets) {
    renderChart(history, targets, chartMode);
  }

  async function runTick() {
    if (!isRunning || remoteBusy || resetBusy) return;
    remoteBusy = true;
    try {
      const stepRequest = stepActiveEngine(speed);
      // Settlement-only barrier: a past rejected step cannot poison later resets.
      pendingStep = stepRequest.then(
        () => undefined,
        () => undefined,
      );
      render(await stepRequest);
      if (currentSnapshot.episode?.terminated) setRunning(false);
    } catch (error) {
      setRunning(false);
      showModelUnavailable(error instanceof Error ? error.message : String(error));
    } finally {
      remoteBusy = false;
      if (isRunning) {
        timerId = window.setTimeout(runTick, 700);
      }
    }
  }

  function setRunning(nextRunning) {
    isRunning =
      nextRunning &&
      !resetBusy &&
      activeEngine === "greenlight2" &&
      Boolean(currentSnapshot) &&
      !currentSnapshot.episode?.terminated;
    const playButton = byId("playButton");
    const liveIndicator = byId("liveIndicator");
    playButton.setAttribute("aria-pressed", String(isRunning));
    liveIndicator.classList.toggle("running", isRunning);
    updateRunStateCopy();
    renderRunProgress();

    if (timerId !== null) {
      window.clearTimeout(timerId);
      timerId = null;
    }

    if (isRunning) {
      timerId = window.setTimeout(runTick, 120);
    }
  }

  function updateRunStateCopy() {
    const completed = Boolean(currentSnapshot?.episode?.terminated);
    setText(
      "playLabel",
      completed
        ? t("simulationCompleted")
        : isRunning
          ? t("pauseSimulation")
          : t("startSimulation"),
    );
    byId("playButton").disabled = completed || resetBusy || activeEngine !== "greenlight2";
    byId("resetButton").disabled = resetBusy || activeEngine !== "greenlight2";
    byId("scenarioSelect").disabled = resetBusy || activeEngine !== "greenlight2";
    const liveIndicator = byId("liveIndicator");
    if (liveIndicator) {
      liveIndicator.querySelector("span").textContent = completed
        ? t("simulationCompleted")
        : isRunning
          ? t("simulationRunning")
          : t("simulationPaused");
    }
  }

  function renderRunProgress() {
    const panel = byId("runProgressPanel"),
      progress = currentSnapshot?.runProgress,
      range = currentSnapshot?.runWindow;
    panel.hidden = !progress || !range;
    if (panel.hidden) return;
    const state = resetBusy
      ? "simulationInitializing"
      : progress.status === "completed"
        ? "simulationCompleted"
        : isRunning
          ? "simulationRunning"
          : progress.completedSteps
            ? "simulationPaused"
            : "simulationReady";
    setText("runProgressTitle", t("progressTitle"));
    setText(
      "runProgressRange",
      `${range.startDateTime.replace("T", " ")} → ${range.endDateTime.replace("T", " ")} (${range.timeConvention === "UTC" ? "UTC" : language === "zh" ? "來源當地標準時間" : "source local standard time"})`,
    );
    byId("runProgressBar").value = progress.percent;
    setText(
      "runProgressText",
      `${t(state)} · ${progress.completedSteps}/${progress.totalSteps} ${t("progressSteps")} (${formatNumber(progress.percent, 1)}%) · ${t("progressClock")}: ${progress.currentDateTime.replace("T", " ")}`,
    );
    setText("runProgressNote", t("progressNote"));
  }

  function focusSimulatorControls() {
    const dialog = byId("projectDialog");
    if (dialog?.open) dialog.close();
    if (!currentSnapshot) {
      byId("retryModelButton").focus();
      return;
    }
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
    byId("languageToggleTop").addEventListener("click", toggleLanguage);
    byId("retryModelButton").addEventListener("click", () => probeBackend(true));
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
        showResetFailure(error);
      }
    });

    byId("scenarioSelect").addEventListener("change", async () => {
      if (byId("scenarioSelect").value !== "uploaded") {
        selectedWeatherId = null;
        selectedRunWindow = null;
      }
      if (byId("scenarioSelect").value === "uploaded" && !selectedWeatherId) {
        byId("scenarioSelect").value = "spring";
        return;
      }
      setRunning(false);
      try {
        render(await resetActiveEngine());
      } catch (error) {
        showResetFailure(error);
      }
    });

    document.addEventListener("greenlight-configuration-selected", async (event) => {
      const complete = event.detail?.complete || (() => {});
      if (resetBusy || activeEngine !== "greenlight2" || !currentSnapshot) {
        complete(t("offlineModelNote"));
        return;
      }
      setRunning(false);
      try {
        render(await resetActiveEngine(event.detail.config));
        complete();
      } catch (error) {
        if (!["INVALID_CONFIGURATION", "INVALID_REQUEST", "RESET_REJECTED"].includes(error.code))
          showResetFailure(error);
        complete(error instanceof Error ? error.message : String(error));
      }
    });

    document.addEventListener("greenlight-weather-selected", async (event) => {
      const weatherId = event.detail?.weatherId;
      const complete = event.detail?.complete || (() => {});
      if (!weatherId || activeEngine !== "greenlight2" || !currentSnapshot) {
        complete(t("offlineModelNote"));
        return;
      }
      if (resetBusy) {
        complete(t("simulationInitializing"));
        return;
      }
      const previousId = selectedWeatherId,
        previousWindow = selectedRunWindow;
      selectedWeatherId = weatherId;
      selectedRunWindow = event.detail.runWindow;
      byId("scenarioSelect").value = "uploaded";
      updateEngineStatus("greenlight2");
      setRunning(false);
      try {
        render(await resetActiveEngine());
        complete();
      } catch (error) {
        selectedWeatherId = previousId;
        selectedRunWindow = previousWindow;
        byId("scenarioSelect").value = currentSnapshot?.scenario || "spring";
        if (
          ["INVALID_WINDOW", "INVALID_REQUEST", "WEATHER_EXPIRED", "RESET_REJECTED"].includes(
            error.code,
          )
        ) {
          updateEngineStatus("greenlight2");
          updateRunStateCopy();
          renderRunProgress();
        } else {
          showModelUnavailable(error instanceof Error ? error.message : String(error));
        }
        complete(error instanceof Error ? error.message : String(error));
      }
    });

    byId("speedSelect").addEventListener("change", (event) => {
      speed = Number(event.target.value);
      if (isRunning) setRunning(true);
    });

    controls.forEach((input) => {
      input.addEventListener("input", () => {
        if (currentSnapshot?.mode !== "manual") return;
        const value = Number(input.value) / 100;
        render({
          ...currentSnapshot,
          controls: { ...currentSnapshot.controls, [input.dataset.control]: value },
        });
      });
    });

    modeButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (!currentSnapshot) return;
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
      byId(inputId).addEventListener("change", () => {
        const value = readTargets()[targetName];
        if (!currentSnapshot) return;
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
        if (currentSnapshot) drawChart(currentSnapshot.history, currentSnapshot.targets);
      });
    });

    window.addEventListener("resize", () => {
      if (resizeFrame !== null) window.cancelAnimationFrame(resizeFrame);
      resizeFrame = window.requestAnimationFrame(() => {
        if (currentSnapshot) drawChart(currentSnapshot.history, currentSnapshot.targets);
        resizeFrame = null;
      });
    });
  }

  restoreBaselineRun();
  applyLanguage();
  bindEvents();
  render(currentSnapshot);
  probeBackend();
})();
