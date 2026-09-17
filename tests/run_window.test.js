"use strict";
const test = require("node:test"),
  assert = require("node:assert/strict");
const { check, dateTime, secondsFromDate, recipe } = require("../frontend/run-window.js");
const bounds = {
  sourceStartSeconds: 0,
  sourceEndSeconds: 129600,
  earliestStartSeconds: 0,
  latestEndSeconds: 86400,
};
test("source-clock arithmetic does not depend on local timezone or daylight saving", () => {
  assert.equal(dateTime(2024, 59 * 86400), "2024-02-29T00:00");
  assert.equal(dateTime(2023, 59 * 86400), "2023-03-01T00:00");
  assert.equal(
    secondsFromDate(2024, "2024-03-31T03:00") - secondsFromDate(2024, "2024-03-31T01:00"),
    7200,
  );
  assert.ok(Number.isNaN(secondsFromDate(2023, "2023-02-29T00:00")));
});
test("short window and final end retain a fixed 15-minute step", () => {
  const result = check(
    "2010",
    "source-local-standard",
    "2010-01-01T09:15",
    "2010-01-01T10:00",
    bounds,
  );
  assert.equal(result.steps, 3);
  assert.equal(result.hours, 0.75);
  assert.equal(check("2010", "UTC", "2010-01-01T23:45", "2010-01-02T00:00", bounds).steps, 1);
  assert.deepEqual(recipe({ ...result.window, totalSteps: 3 }), result.window);
});
test("date range, source year and missing context are rejected", () => {
  for (const args of [
    ["", "UTC", "", ""],
    ["2010", "", "2010-01-01T00:00", "2010-01-02T00:00"],
    ["2010", "UTC", "2010-01-01T09:16", "2010-01-01T10:00"],
    ["2010", "UTC", "2010-01-01T10:00", "2010-01-01T09:15"],
    ["2010", "UTC", "2010-01-01T23:45", "2010-01-02T00:15"],
  ])
    assert.ok(check(...args, bounds).error);
});
