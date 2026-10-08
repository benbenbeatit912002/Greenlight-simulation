"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const plan = require("../frontend/control-plan.js");

test("schedule switches on boundaries and repeats after midnight", () => {
  const schedule = plan.example();
  assert.equal(plan.at(schedule, 359).uBoil, 0.35);
  assert.equal(plan.at(schedule, 360).uBoil, 0.5);
  assert.equal(plan.at(schedule, 600).uBoil, 0.15);
  assert.equal(plan.at(schedule, 1440 + 360).uBoil, 0.5);
  assert.throws(() => plan.minute("06:07"));
  assert.throws(() => plan.minute("24:00"));
});

test("schedule rejects missing commands and duplicate times", () => {
  const value = plan.example();
  delete value.entries[0].controls.uVent;
  assert.throws(() => plan.validate(value));
  const duplicate = plan.example();
  duplicate.entries[1].time = "00:00";
  assert.throws(() => plan.validate(duplicate));
});

test("uncertain reset and stale-revision errors require connection recovery", () => {
  for (const code of [
    "INVALID_REQUEST",
    "INVALID_CONFIGURATION",
    "RESET_REJECTED",
    "INVALID_WINDOW",
    "WEATHER_EXPIRED",
  ])
    assert.equal(plan.isNonMutatingRejection({ code }), true);
  for (const error of [
    new Error("Network lost"),
    { code: "REVISION_CONFLICT" },
    { code: "MODEL_ERROR" },
  ])
    assert.equal(plan.isNonMutatingRejection(error), false);
});

function summary(runId) {
  return {
    runId,
    modelStep: 96,
    elapsedMinutes: 1440,
    engine: "greenlight2",
    modelVersion: "version",
    weatherFingerprint: "weather",
    configurationFingerprint: "config",
    costModelId: "cost",
    initialStateFingerprint: "initial",
    climateMetrics: { method: "method", limitsFingerprint: "limits", evaluatedMinutes: 1440 },
    strategyChanged: false,
  };
}
test("comparison needs identical forcing, initialization, limits and horizon", () => {
  const base = summary("baseline");
  assert.equal(plan.comparisonIssue(base, summary("candidate")), null);
  for (const key of [
    "weatherFingerprint",
    "configurationFingerprint",
    "initialStateFingerprint",
    "modelVersion",
  ])
    assert.equal(
      plan.comparisonIssue(base, { ...summary("candidate"), [key]: "different" }),
      "conditions",
    );
  assert.equal(plan.comparisonIssue(base, { ...summary("candidate"), modelStep: 95 }), "horizon");
  assert.equal(
    plan.comparisonIssue(base, { ...summary("candidate"), strategyChanged: true }),
    "strategy",
  );
  assert.equal(
    plan.comparisonIssue(base, {
      ...summary("candidate"),
      climateMetrics: { ...base.climateMetrics, limitsFingerprint: "different" },
    }),
    "limits",
  );
  assert.equal(
    plan.comparisonIssue(base, { ...summary("candidate"), modelStep: 0 }, { ignoreHorizon: true }),
    null,
  );
  assert.equal(plan.comparisonIssue(base, base), "sameRun");
});
