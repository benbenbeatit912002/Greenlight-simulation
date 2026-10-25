"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { workflowState } = require("../frontend/pages.js");
const translations = require("../frontend/translations.js");

function snapshot(overrides = {}) {
  return {
    engine: "greenlight-gym2",
    weatherId: null,
    greenhouse: {
      fields: [{ key: "floorArea" }, { key: "heatingCapacity" }, { key: "initialTemperature" }],
      request: { overrides },
    },
  };
}

test("unknown or offline applied inputs are not labelled as reference defaults", () => {
  for (const value of [null, {}, { engine: "error" }, { engine: "greenlight-gym2" }]) {
    const result = workflowState(value, { runId: "saved" });
    assert.equal(result.weather, "workflowUnavailable");
    assert.equal(result.greenhouse, "workflowUnavailable");
    assert.equal(result.comparison, "workflowUnavailable");
  }
});

test("bundled reference run needs neither uploaded weather nor indoor observations", () => {
  const result = workflowState(snapshot(), null);
  assert.equal(result.weather, "workflowSampleActive");
  assert.equal(result.greenhouse, "workflowReferenceDefaults");
  assert.equal(result.comparison, "workflowNoBaseline");
  assert.deepEqual(result.values, { custom: 0, defaults: 3 });
});

test("uploaded weather does not imply greenhouse calibration or non-default settings", () => {
  const result = workflowState({ ...snapshot(), weatherId: "weather-token" }, null);
  assert.equal(result.weather, "workflowUploadedActive");
  assert.equal(result.greenhouse, "workflowReferenceDefaults");
});

test("applied override counts include zero and ignore unknown or inherited properties", () => {
  const overrides = Object.assign(Object.create({ initialTemperature: 18 }), {
    heatingCapacity: 0,
    unsupportedKey: 123,
  });
  const result = workflowState(snapshot(overrides), null);
  assert.equal(result.greenhouse, "workflowOverrides");
  assert.deepEqual(result.values, { custom: 1, defaults: 2 });
});

test("workflow summary does not mutate inputs or claim that saved runs match", () => {
  const applied = snapshot({ floorArea: 100 });
  const saved = { runId: "old-run", weatherFingerprint: "different-weather" };
  const before = JSON.stringify({ applied, saved });
  const result = workflowState(applied, saved);
  assert.equal(result.comparison, "workflowBaselineSaved");
  assert.equal(JSON.stringify({ applied, saved }), before);
  assert.match(translations.en[result.comparison], /matching conditions/);
});

test("all workflow statuses and interpolation tokens are bilingual", () => {
  for (const value of [
    null,
    snapshot(),
    { ...snapshot({ floorArea: 100 }), weatherId: "weather-token" },
  ]) {
    for (const saved of [null, { runId: "saved" }]) {
      const result = workflowState(value, saved);
      for (const name of ["weather", "greenhouse", "comparison"]) {
        for (const language of ["en", "zh"]) {
          const copy = translations[language][result[name]];
          assert.equal(typeof copy, "string");
          for (const [, key] of copy.matchAll(/\{(\w+)\}/g)) {
            assert.equal(typeof result.values[key], "number");
          }
        }
      }
    }
  }
});

test("guide exposes navigation and assumptions, not a measurement-upload prerequisite", () => {
  const html = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");
  for (const id of [
    "workflowWeatherStatus",
    "workflowGreenhouseStatus",
    "workflowComparisonStatus",
  ]) {
    assert.match(html, new RegExp('id="' + id + '" role="status"'));
  }
  for (const key of [
    "workflowWeatherStep",
    "workflowGreenhouseStep",
    "workflowCompareStep",
    "workflowScope",
    "workflowWeatherAssumption",
    "workflowGreenhouseAssumption",
    "workflowOutputsAssumption",
    "workflowCompareAssumption",
  ]) {
    assert.ok(html.includes('data-i18n="' + key + '"'), key);
  }
  assert.match(translations.en.workflowIntro, /No indoor measurements needed/);
  assert.match(translations.en.workflowWeatherAssumption, /does not calibrate/);
  assert.match(translations.en.workflowCompareAssumption, /new baseline/);
});

test("workflow summary is refreshed from rendered snapshots and cleared on model errors", () => {
  const app = fs.readFileSync(path.join(__dirname, "../frontend/app.js"), "utf8");
  assert.ok(app.includes("pages?.renderWorkflow(snapshot, baselineRun)"));
  assert.ok(app.includes("pages?.renderWorkflow(null, baselineRun)"));
});

test("reference labels allow dependent capacity recalculation rather than frozen parameters", () => {
  assert.match(translations.en.workflowOverrides, /Dependent capacities are recalculated/);
  assert.match(translations.zh.workflowOverrides, /相關容量.*重新計算/);
  assert.match(translations.en.workflowGreenhouseAssumption, /applied dimensions and equipment/);
  assert.doesNotMatch(translations.en.workflowOverrides, /Other model parameters are unchanged/);
});
