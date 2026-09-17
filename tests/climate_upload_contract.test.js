"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { validateFile, MAX_BYTES, copy } = require("../frontend/climate-upload.js");
test("workbook extension and size boundaries", () => {
  assert.equal(validateFile({ name: "WEATHER.XLSX", size: MAX_BYTES }), true);
  for (const file of [
    null,
    { name: "weather.xlsm", size: 1 },
    { name: "weather.xlsx", size: 0 },
    { name: "weather.xlsx", size: MAX_BYTES + 1 },
  ]) {
    assert.equal(validateFile(file), false);
  }
});
test("weather UI translations are complete and explain explicit model activation", () => {
  assert.deepEqual(Object.keys(copy.en).sort(), Object.keys(copy.zh).sort());
  assert.match(copy.en.unchanged, /checked in memory/);
  assert.match(copy.en.useWeather, /Run with this weather/);
  assert.match(copy.en.privacy, /not saved/);
});
