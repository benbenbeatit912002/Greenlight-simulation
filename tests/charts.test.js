"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function chartHarness() {
  const calls = [];
  const context = new Proxy(
    {},
    {
      get:
        (_, name) =>
        (...args) =>
          calls.push([name, ...args]),
      set: () => true,
    },
  );
  const element = () => ({
    style: { setProperty() {} },
    classList: { add() {}, remove() {} },
    append() {},
    replaceChildren() {},
    setAttribute(name, value) {
      this[name] = value;
    },
  });
  const canvas = Object.assign(element(), {
    parentElement: { getBoundingClientRect: () => ({ width: 640, height: 200 }) },
    getContext: () => context,
  });
  const elements = { trendCanvas: canvas, chartEmpty: element(), chartLegend: element() };
  const sandbox = {
    window: { devicePixelRatio: 1 },
    document: { documentElement: {}, createElement: element, createTextNode: (text) => text },
    getComputedStyle: () => ({ getPropertyValue: () => "#abcdef" }),
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, "../frontend/charts.js"), "utf8"),
    sandbox,
  );
  const render = sandbox.window.GreenlightCharts.createRenderer({
    byId: (id) => elements[id],
    t: (key) => key,
    formatHour: (hour) => String(hour),
  });
  return { render, calls, canvas };
}

for (const [mode, label] of [
  ["temperature", "temperatureChart"],
  ["humidity", "humidityChart"],
  ["co2", "co2Chart"],
]) {
  test(`${mode} chart renders the correct series without nonfinite coordinates`, () => {
    const { render, calls, canvas } = chartHarness();
    const history = [0, 1, 2].map((index) => ({
      hour: index,
      airTemp: 20 + index,
      canopyTemp: 21 + index,
      outsideTemp: 10 + index,
      rh: 70 + index,
      outsideRh: 80 + index,
      co2: 700 + index * 20,
    }));
    render(history, { maxRh: 82, co2: 900 }, mode);
    assert.equal(canvas["aria-label"], label);
    assert.ok(calls.some(([name]) => name === "stroke"));
    for (const [, ...arguments_] of calls) {
      for (const value of arguments_) {
        if (typeof value === "number") assert.ok(Number.isFinite(value));
      }
    }
  });
}
