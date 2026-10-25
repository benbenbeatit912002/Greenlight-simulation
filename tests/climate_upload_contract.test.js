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
  assert.equal(copy.en.chooseFile, "Choose file");
  assert.equal(copy.en.noFile, "No file selected");
  assert.equal(copy.zh.chooseFile, "選擇檔案");
  assert.equal(copy.zh.noFile, "尚未選擇檔案");
  assert.match(copy.en.unchanged, /checked in memory/);
  assert.equal(copy.en.useWeather, "Apply weather and dates");
  assert.equal(copy.zh.useWeather, "套用天氣與日期");
  assert.ok(copy.en.unchanged.includes(copy.en.useWeather));
  assert.ok(copy.zh.unchanged.includes(copy.zh.useWeather));
  assert.match(copy.en.windowInitialized, /No simulation steps have run yet/);
  assert.match(copy.zh.windowInitialized, /尚未執行模擬步數/);
  assert.match(copy.en.privacy, /not saved/);
});
