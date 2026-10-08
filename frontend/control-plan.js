(function (root) {
  "use strict";
  const names = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"];
  const limits = { temperatureMin: 15, temperatureMax: 34, humidityMin: 50, humidityMax: 85 };
  function minute(time) {
    if (typeof time !== "string" || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time))
      throw new Error("Use HH:MM times.");
    const [hour, minutes] = time.split(":").map(Number);
    if (minutes % 15) throw new Error("Use 15-minute schedule boundaries.");
    return hour * 60 + minutes;
  }
  function validate(schedule) {
    if (
      !schedule ||
      schedule.schemaVersion !== 1 ||
      !Array.isArray(schedule.entries) ||
      !schedule.entries.length ||
      schedule.entries.length > 96
    )
      throw new Error("Provide 1 to 96 schedule rows.");
    let previous = -1;
    for (const row of schedule.entries) {
      const current = minute(row.time);
      if (current <= previous) throw new Error("Times must be unique and in ascending order.");
      previous = current;
      if (
        !row.controls ||
        Object.keys(row.controls).length !== names.length ||
        !names.every(
          (key) =>
            typeof row.controls[key] === "number" &&
            Number.isFinite(row.controls[key]) &&
            row.controls[key] >= 0 &&
            row.controls[key] <= 1,
        )
      )
        throw new Error("Every row needs six actuator values from 0 to 100%.");
    }
    if (schedule.entries[0].time !== "00:00") throw new Error("Start the schedule at 00:00.");
    return schedule;
  }
  function at(schedule, sourceMinute) {
    validate(schedule);
    const now = ((sourceMinute % 1440) + 1440) % 1440;
    let selected = schedule.entries[0];
    for (const row of schedule.entries) {
      if (minute(row.time) > now) break;
      selected = row;
    }
    return { ...selected.controls };
  }
  function example() {
    return {
      schemaVersion: 1,
      entries: [
        {
          time: "00:00",
          controls: { uBoil: 0.35, uCO2: 0, uThScr: 1, uVent: 0.05, uLamp: 0, uBlScr: 1 },
        },
        {
          time: "06:00",
          controls: { uBoil: 0.5, uCO2: 0.1, uThScr: 0.5, uVent: 0.1, uLamp: 0, uBlScr: 0 },
        },
        {
          time: "10:00",
          controls: { uBoil: 0.15, uCO2: 0.1, uThScr: 0, uVent: 0.25, uLamp: 0, uBlScr: 0 },
        },
        {
          time: "18:00",
          controls: { uBoil: 0.35, uCO2: 0, uThScr: 1, uVent: 0.05, uLamp: 0, uBlScr: 1 },
        },
      ],
    };
  }
  function comparisonIssue(baseline, candidate, { ignoreHorizon = false } = {}) {
    if (!baseline || !candidate) return "missing";
    const keys = [
      "engine",
      "modelVersion",
      "weatherFingerprint",
      "configurationFingerprint",
      "costModelId",
      "initialStateFingerprint",
    ];
    if (
      keys.some(
        (key) =>
          !baseline[key] ||
          /unknown|unversioned|local-source/i.test(baseline[key]) ||
          baseline[key] !== candidate[key],
      )
    )
      return "conditions";
    if (baseline.engine !== "greenlight2") return "conditions";
    if (
      !baseline.climateMetrics ||
      !candidate.climateMetrics ||
      baseline.climateMetrics.method !== candidate.climateMetrics.method ||
      baseline.climateMetrics.limitsFingerprint !== candidate.climateMetrics.limitsFingerprint
    )
      return "limits";
    if (baseline.strategyChanged || candidate.strategyChanged) return "strategy";
    if (baseline.runId === candidate.runId) return "sameRun";
    if (
      !ignoreHorizon &&
      (baseline.modelStep !== candidate.modelStep ||
        baseline.elapsedMinutes !== candidate.elapsedMinutes ||
        candidate.modelStep <= 0 ||
        candidate.climateMetrics.evaluatedMinutes !== candidate.elapsedMinutes ||
        baseline.climateMetrics.evaluatedMinutes !== baseline.elapsedMinutes)
    )
      return "horizon";
    return null;
  }
  function isNonMutatingRejection(error) {
    return [
      "INVALID_CONFIGURATION",
      "INVALID_REQUEST",
      "RESET_REJECTED",
      "INVALID_WINDOW",
      "WEATHER_EXPIRED",
    ].includes(error?.code);
  }
  const api = {
    names,
    limits,
    minute,
    validate,
    at,
    example,
    comparisonIssue,
    isNonMutatingRejection,
  };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GreenlightControlPlan = api;
})(typeof window === "object" ? window : globalThis);
