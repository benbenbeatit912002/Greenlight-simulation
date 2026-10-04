"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { rectangleArea, airVolumes } = require("../frontend/greenhouse-settings.js");

test("rectangular dimensions yield only floor area within model bounds", () => {
  assert.equal(rectangleArea(20, 10), 200);
  assert.equal(rectangleArea(10, 20), 200);
  assert.equal(rectangleArea(0.5, 2), 1);
  assert.equal(rectangleArea(20, 100), 2000);
  assert.equal(rectangleArea(10, 10, { min: 1, max: 99 }), null);
  assert.ok(Math.abs(rectangleArea(12.3, 10.1) - 124.23) < 1e-10);
});

test("missing, nonnumeric, nonfinite, nonpositive and oversized dimensions are rejected", () => {
  for (const value of [undefined, null, "", "12", true, NaN, Infinity, -1, 0]) {
    assert.equal(rectangleArea(value, 12), null);
    assert.equal(rectangleArea(12, value), null);
  }
  assert.equal(rectangleArea(0.1, 0.1), null);
  assert.equal(rectangleArea(2000, 2000), null);
  assert.equal(rectangleArea(1e308, 1e308), null);
});

test("air volumes follow GreenLight aggregate geometry without changing inputs", () => {
  const values = Object.freeze({ floorArea: 200, mainHeight: 4, totalHeight: 5 });
  assert.deepEqual(airVolumes(values), { main: 800, top: 200, total: 1000 });
  assert.deepEqual(airVolumes({ ...values, floorArea: 400 }), {
    main: 1600,
    top: 400,
    total: 2000,
  });
  const boundary = airVolumes({ floorArea: 100, mainHeight: 5.7, totalHeight: 5.8 });
  assert.ok(Math.abs(boundary.top - 10) < 1e-10);
  assert.ok(Math.abs(boundary.total - boundary.main - boundary.top) < 1e-10);
});

test("invalid or overflowing volume geometry produces no preview", () => {
  for (const values of [
    { floorArea: 200, mainHeight: 5, totalHeight: 5 },
    { floorArea: 200, mainHeight: 5, totalHeight: 5.05 },
    { floorArea: 200, mainHeight: 6, totalHeight: 5 },
    { floorArea: 0, mainHeight: 4, totalHeight: 5 },
    { floorArea: "200", mainHeight: 4, totalHeight: 5 },
    { floorArea: 200, mainHeight: NaN, totalHeight: 5 },
    { floorArea: 1e308, mainHeight: 4, totalHeight: 5 },
  ])
    assert.equal(airVolumes(values), null);
});
