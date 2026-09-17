"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  BROWSER_MODEL_VERSION,
  BROWSER_WEATHER_VERSION,
  CONTROL_NAMES,
  COST_ASSUMPTIONS,
  GreenhouseModel,
  SCENARIOS,
  STEP_MINUTES,
  TARGET_LIMITS,
} = require("../frontend/legacy/simulator-engine.js");

function assertFiniteSnapshot(snapshot) {
  const groups = [
    snapshot.indoor,
    snapshot.outdoor,
    snapshot.crop,
    snapshot.controls,
    snapshot.targets,
    snapshot.resources,
  ];
  for (const group of groups) {
    for (const [name, value] of Object.entries(group)) {
      assert.equal(Number.isFinite(value), true, `${name} must be finite`);
    }
  }
  for (const control of CONTROL_NAMES) {
    assert.ok(snapshot.controls[control] >= 0 && snapshot.controls[control] <= 1);
  }
  assert.ok(snapshot.indoor.airTemp >= -5 && snapshot.indoor.airTemp <= 48);
  assert.ok(snapshot.indoor.rh >= 28 && snapshot.indoor.rh <= 100);
  assert.ok(snapshot.indoor.co2 >= 250 && snapshot.indoor.co2 <= 1800);
  assert.ok(snapshot.crop.leafAreaIndex >= 0.4 && snapshot.crop.leafAreaIndex <= 4.6);
  assert.ok(snapshot.crop.fruitDryMass >= 0);
  assert.ok(Number.isInteger(snapshot.modelStep) && snapshot.modelStep >= 0);
  assert.equal(snapshot.elapsedMinutes, snapshot.modelStep * STEP_MINUTES);
  assert.ok(snapshot.history.length >= 1 && snapshot.history.length <= 97);
  assert.equal(snapshot.history.length, Math.min(snapshot.modelStep + 1, 97));
  assert.equal(
    snapshot.history[snapshot.history.length - 1].elapsedMinutes,
    snapshot.elapsedMinutes,
  );
  for (const point of snapshot.history) {
    for (const [name, value] of Object.entries(point)) {
      assert.equal(Number.isFinite(value), true, `history.${name} must be finite`);
    }
  }
  for (const resource of ["heatKwh", "lampKwh", "co2Kg", "costEur"]) {
    assert.ok(snapshot.resources[resource] >= 0, `${resource} must be non-negative`);
  }
}

function runManual(scenario, controls, steps = 96) {
  const model = new GreenhouseModel({ scenario, mode: "manual" });
  for (const name of CONTROL_NAMES) model.setControl(name, 0);
  for (const [name, value] of Object.entries(controls)) model.setControl(name, value);
  return model.step(steps);
}

test("browser snapshot identifies its model and economic assumptions", () => {
  const snapshot = new GreenhouseModel().snapshot();

  assert.equal(snapshot.engine, "browser-approximation");
  assert.equal(snapshot.modelVersion, BROWSER_MODEL_VERSION);
  assert.equal(snapshot.costModelId, COST_ASSUMPTIONS.id);
  assert.equal(snapshot.weatherFingerprint, `${BROWSER_WEATHER_VERSION}:spring`);
  assert.deepEqual(snapshot.economics, COST_ASSUMPTIONS);
  assert.equal(snapshot.economics.liveTariff, false);
  assert.equal(STEP_MINUTES, 15);
});

test("invalid model inputs fail before they can create NaN state", () => {
  assert.throws(() => new GreenhouseModel({ scenario: "unknown" }), /Unknown weather scenario/);
  assert.throws(() => new GreenhouseModel({ mode: "remote-control" }), /Unknown control mode/);

  const model = new GreenhouseModel();
  assert.throws(() => model.setScenario("unknown"), /Unknown weather scenario/);
  assert.throws(() => model.setMode("remote-control"), /Unknown control mode/);
  assert.throws(() => model.setControl("unknown", 0.5), /Unknown GreenLight control/);
  assert.throws(() => model.setTarget("unknown", 20), /Unknown target/);
  assert.throws(() => model.setControl("uBoil", Number.NaN), /finite number/);
  assert.throws(() => model.setTarget("dayTemp", Number.POSITIVE_INFINITY), /finite number/);
  assert.throws(() => model.setTarget("dayTemp", TARGET_LIMITS.dayTemp[1] + 1), /between/);
  assert.throws(() => model.step(0), /integer between 1 and 192/);
  assert.throws(() => model.step(1.5), /integer between 1 and 192/);
  assert.throws(() => model.step(193), /integer between 1 and 192/);
  assert.throws(() => model.step(Number.NaN), /integer between 1 and 192/);

  assert.equal(model.setControl("uBoil", -1), 0);
  assert.equal(model.setControl("uBoil", 2), 1);
});

test("all weather scenarios are deterministic and stay within software bounds", () => {
  for (const scenario of Object.keys(SCENARIOS)) {
    const first = new GreenhouseModel({ scenario, mode: "auto" });
    const second = new GreenhouseModel({ scenario, mode: "auto" });
    let previousResources = { ...first.snapshot().resources };

    for (let index = 0; index < 192; index += 1) {
      const snapshot = first.step(1);
      assertFiniteSnapshot(snapshot);
      for (const resource of ["heatKwh", "lampKwh", "co2Kg", "costEur"]) {
        assert.ok(
          snapshot.resources[resource] >= previousResources[resource],
          `${scenario} ${resource} must be cumulative`,
        );
      }
      previousResources = { ...snapshot.resources };
    }

    assert.deepEqual(first.snapshot(), second.step(192));
  }
});

test("manual actuator changes produce directionally plausible responses", () => {
  const heatOff = runManual("winter", {});
  const heatFull = runManual("winter", { uBoil: 1 });
  assert.ok(heatFull.indoor.airTemp > heatOff.indoor.airTemp + 10);
  assert.ok(heatFull.resources.heatKwh > heatOff.resources.heatKwh);

  const ventClosed = runManual("summer", {});
  const ventFull = runManual("summer", { uVent: 1 });
  assert.ok(ventFull.indoor.airTemp < ventClosed.indoor.airTemp - 2);

  const co2Off = runManual("spring", {});
  const co2Full = runManual("spring", { uCO2: 1 });
  assert.ok(co2Full.indoor.co2 > co2Off.indoor.co2 + 1000);
  assert.ok(co2Full.resources.co2Kg > co2Off.resources.co2Kg);

  const lampOff = runManual("cloudy", {});
  const lampFull = runManual("cloudy", { uLamp: 1 });
  assert.ok(lampFull.indoor.insideRadiation > lampOff.indoor.insideRadiation + 100);
  assert.ok(lampFull.resources.lampKwh > lampOff.resources.lampKwh);
});

test("reset clears the horizon and cumulative resources without changing provenance", () => {
  const model = new GreenhouseModel({ scenario: "winter", mode: "manual" });
  model.setTarget("nightTemp", 18);
  model.setControl("uBoil", 1);
  model.step(24);

  const reset = model.reset();
  assert.equal(reset.modelStep, 0);
  assert.equal(reset.elapsedMinutes, 0);
  assert.equal(reset.scenario, "winter");
  assert.equal(reset.mode, "manual");
  assert.equal(reset.targets.nightTemp, 18);
  assert.equal(reset.modelVersion, BROWSER_MODEL_VERSION);
  assert.equal(reset.costModelId, COST_ASSUMPTIONS.id);
  assert.equal(reset.weatherFingerprint, `${BROWSER_WEATHER_VERSION}:winter`);
  assert.deepEqual(reset.resources, { heatKwh: 0, lampKwh: 0, co2Kg: 0, costEur: 0 });
});
