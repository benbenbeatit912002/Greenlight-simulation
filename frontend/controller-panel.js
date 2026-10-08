(function (root) {
  "use strict";
  const plan = root.GreenlightControlPlan;
  const labels = {
    uBoil: "boilerHeating",
    uCO2: "co2Injection",
    uThScr: "thermalScreen",
    uVent: "roofVentilation",
    uLamp: "supplementalLighting",
    uBlScr: "blackoutScreen",
  };
  const displayOrder = ["uBoil", "uThScr", "uBlScr", "uVent", "uCO2", "uLamp"];
  function create({ byId, t, initialize, replay }) {
    let busy = false,
      snapshot = null,
      baseline = null,
      candidate = null;
    const rows = byId("scheduleRows");
    const message = byId("scheduleMessage");
    function setMessage(text, error = false) {
      message.textContent = text;
      message.dataset.error = String(error);
    }
    function addRow(row) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      const time = document.createElement("input");
      Object.assign(time, { type: "time", step: "900", required: true, value: row.time });
      time.dataset.scheduleTime = "true";
      td.append(time);
      tr.append(td);
      for (const key of displayOrder) {
        const cell = document.createElement("td");
        const input = document.createElement("input");
        Object.assign(input, {
          type: "number",
          min: "0",
          max: "100",
          step: "1",
          required: true,
          value: String(Math.round(row.controls[key] * 100)),
        });
        input.dataset.scheduleControl = key;
        cell.append(input);
        tr.append(cell);
      }
      const cell = document.createElement("td"),
        remove = document.createElement("button");
      remove.type = "button";
      remove.className = "schedule-remove";
      remove.addEventListener("click", () => {
        tr.remove();
        refreshDraft();
        translate();
      });
      cell.append(remove);
      tr.append(cell);
      rows.append(tr);
    }
    function readDraft() {
      const entries = Array.from(rows.children).map((tr) => {
        const controls = {};
        tr.querySelectorAll("[data-schedule-control]").forEach((input) => {
          if (input.value === "" || !input.checkValidity())
            throw new Error(t("scheduleValuesError"));
          controls[input.dataset.scheduleControl] = Number(input.value) / 100;
        });
        return { time: tr.querySelector("[data-schedule-time]").value, controls };
      });
      return plan.validate({ schemaVersion: 1, entries });
    }
    function readLimits() {
      const result = {};
      for (const key of Object.keys(plan.limits)) {
        const input = byId(`limit${key}`);
        if (input.value === "" || !input.checkValidity()) throw new Error(t("scheduleLimitsError"));
        result[key] = Number(input.value);
      }
      if (
        result.temperatureMin >= result.temperatureMax ||
        result.humidityMin >= result.humidityMax
      )
        throw new Error(t("scheduleLimitsError"));
      return result;
    }
    function clock(minute) {
      minute = ((minute % 1440) + 1440) % 1440;
      return `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
    }
    function timeline(container, segments) {
      container.replaceChildren();
      if (!segments.length) {
        container.textContent = t("timelineNoSteps");
        return;
      }
      for (const key of displayOrder) {
        const row = document.createElement("div"),
          label = document.createElement("span"),
          track = document.createElement("div");
        row.className = "equipment-row";
        label.textContent = t(labels[key]);
        track.className = "equipment-track";
        track.setAttribute("role", "img");
        track.setAttribute(
          "aria-label",
          `${t(labels[key])}: ${segments.map((s) => `${s.label} ${Math.round(s.controls[key] * 100)}%`).join(", ")}`,
        );
        for (const segment of segments) {
          const part = document.createElement("span");
          part.style.width = `${segment.width}%`;
          part.style.setProperty("--command", String(segment.controls[key]));
          part.title = `${segment.label}: ${Math.round(segment.controls[key] * 100)}%`;
          track.append(part);
        }
        row.append(label, track);
        container.append(row);
      }
    }
    function refreshDraft() {
      try {
        const draft = readDraft();
        timeline(
          byId("scheduleTimeline"),
          draft.entries.map((row, i) => {
            const end = draft.entries[i + 1] ? plan.minute(draft.entries[i + 1].time) : 1440;
            return {
              controls: row.controls,
              width: (end - plan.minute(row.time)) / 14.4,
              label: `${row.time}–${end === 1440 ? "24:00" : clock(end)}`,
            };
          }),
        );
        setMessage(t("scheduleDraftReady"));
      } catch (error) {
        byId("scheduleTimeline").replaceChildren();
        setMessage(error.message, true);
      }
    }
    async function apply(mode) {
      try {
        const settings = { mode, evaluationLimits: readLimits() };
        if (mode === "schedule") settings.schedule = readDraft();
        busy = true;
        updateButtons();
        await initialize(settings);
        setMessage(t(mode === "schedule" ? "scheduleApplied" : "automaticInitialized"));
      } catch (error) {
        setMessage(error.message, true);
      } finally {
        busy = false;
        updateButtons();
      }
    }
    function updateButtons() {
      const available = Boolean(snapshot) && !busy;
      byId("applyScheduleButton").disabled = !available;
      byId("automaticBaselineButton").disabled = !available;
      byId("runToBaselineButton").disabled =
        !available ||
        !baseline ||
        !candidate ||
        plan.comparisonIssue(baseline, candidate, { ignoreHorizon: true }) !== null ||
        candidate.modelStep >= baseline.modelStep;
      byId("addScheduleRow").disabled = busy || rows.children.length >= 96;
    }
    function renderComparison() {
      const issue = plan.comparisonIssue(baseline, candidate);
      const output = byId("climateComparisonRows");
      output.replaceChildren();
      byId("controllerCompareNote").textContent = t(
        issue ? `scheduleCompare_${issue}` : "scheduleCompareReady",
      );
      if (issue) return;
      const descriptors = [
        ["meanTemperature", "meanTemperature", "°C", 2],
        ["minTemperature", "minTemperature", "°C", 2],
        ["maxTemperature", "maxTemperature", "°C", 2],
        ["meanHumidity", "meanHumidity", "%", 2],
        ["temperatureOutsideMinutes", "temperatureOutside", "min", 0],
        ["humidityOutsideMinutes", "humidityOutside", "min", 0],
        ["eitherOutsideMinutes", "eitherOutside", "min", 0],
      ];
      const add = (label, a, b, unit, digits) => {
        const row = document.createElement("tr");
        for (const value of [
          label,
          `${a.toFixed(digits)} ${unit}`,
          `${b.toFixed(digits)} ${unit}`,
          `${b - a > 0 ? "+" : ""}${(b - a).toFixed(digits)} ${unit}`,
        ]) {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.append(cell);
        }
        output.append(row);
      };
      for (const [key, label, unit, digits] of descriptors)
        add(t(label), baseline.climateMetrics[key], candidate.climateMetrics[key], unit, digits);
      add(t("heating"), baseline.resources.heatKwh, candidate.resources.heatKwh, "kWh/m²", 3);
    }
    function render(nextSnapshot, nextBaseline, nextCandidate) {
      snapshot = nextSnapshot;
      baseline = nextBaseline;
      candidate = nextCandidate;
      const history = snapshot?.controlHistory || [];
      timeline(
        byId("appliedTimeline"),
        history.map((point) => ({
          controls: point.applied,
          width: 100 / history.length,
          label: `${clock(point.minuteOfDay)}–${clock(point.minuteOfDay + 15)}`,
        })),
      );
      byId("appliedTimelineClock").textContent = history.length
        ? `${t("elapsedTime")}: ${history[0].elapsedMinutes}–${history.at(-1).elapsedMinutes + 15} min`
        : "";
      byId("activeControllerText").textContent = snapshot
        ? `${t("activeController")}: ${t(snapshot.mode === "schedule" ? "scheduledControl" : snapshot.mode === "auto" ? "autoControl" : "manualControl")}`
        : t("offlineModelNote");
      const limits = snapshot?.climateMetrics?.limits;
      byId("appliedComparisonLimits").textContent = limits
        ? `${t("appliedEvaluationLimits")}: ${limits.temperatureMin}–${limits.temperatureMax} °C · ${limits.humidityMin}–${limits.humidityMax}% RH`
        : "";
      renderComparison();
      updateButtons();
    }
    function translate() {
      Array.from(rows.children).forEach((tr, i) => {
        tr.querySelector("[data-schedule-time]").setAttribute(
          "aria-label",
          `${t("scheduleTime")} ${i + 1}`,
        );
        tr.querySelectorAll("[data-schedule-control]").forEach((input) =>
          input.setAttribute(
            "aria-label",
            `${t(labels[input.dataset.scheduleControl])} (%) ${i + 1}`,
          ),
        );
        const button = tr.querySelector("button");
        button.textContent = t("removeScheduleRow");
        button.disabled = i === 0;
        button.setAttribute("aria-label", `${t("removeScheduleRow")} ${i + 1}`);
      });
      refreshDraft();
      render(snapshot, baseline, candidate);
    }
    plan.example().entries.forEach(addRow);
    rows.addEventListener("input", refreshDraft);
    byId("addScheduleRow").addEventListener("click", () => {
      try {
        const draft = readDraft(),
          last = draft.entries.at(-1),
          next = plan.minute(last.time) + 60;
        if (next >= 1440) throw new Error(t("scheduleDayFull"));
        addRow({ time: clock(next), controls: { ...last.controls } });
        translate();
      } catch (error) {
        setMessage(error.message, true);
      }
    });
    byId("applyScheduleButton").addEventListener("click", () => apply("schedule"));
    byId("automaticBaselineButton").addEventListener("click", () => apply("auto"));
    byId("runToBaselineButton").addEventListener("click", () => replay());
    translate();
    return { render, translate, readDraft };
  }
  root.GreenlightControllerPanel = { create };
})(window);
