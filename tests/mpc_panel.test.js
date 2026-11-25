"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const plan = require("../frontend/control-plan.js");
const strings = require("../frontend/translations.js");
const project = path.join(__dirname, "..");

function harness() {
  const elements = new Map();
  const make = () => ({
    children: [],
    dataset: {},
    textContent: "",
    disabled: false,
    listeners: {},
    addEventListener(name, fn) {
      this.listeners[name] = fn;
    },
    replaceChildren() {
      this.children = [];
    },
    checkValidity() {
      return true;
    },
  });
  const byId = (id) => {
    if (!elements.has(id)) elements.set(id, make());
    return elements.get(id);
  };
  for (const [k, v] of Object.entries(plan.limits)) byId("limit" + k).value = String(v);
  const boxes = plan.names.map((value) => ({ ...make(), value, checked: false }));
  const doc = {
    querySelectorAll(selector) {
      assert.equal(selector, 'input[name="mpcDevice"]');
      return boxes;
    },
  };
  const root = { GreenlightControlPlan: { ...plan, example: () => ({ entries: [] }) } };
  const context = { window: root, document: doc };
  vm.runInNewContext(
    fs.readFileSync(path.join(project, "frontend/controller-panel.js"), "utf8"),
    context,
  );
  const requests = [];
  const panel = root.GreenlightControllerPanel.create({
    byId,
    t: (key) => strings.en[key],
    initialize: async (s) => {
      requests.push(JSON.parse(JSON.stringify(s)));
    },
    replay: () => {},
  });
  return { byId, boxes, panel, requests };
}

test("all six draft checkboxes map to real device names and localized labels", () => {
  const html = fs.readFileSync(path.join(project, "index.html"), "utf8");
  const values = Array.from(html.matchAll(/name="mpcDevice"\s+value="([^"]+)"/g), (m) => m[1]);
  assert.deepEqual(values.sort(), [...plan.names].sort());
  for (const lang of ["en", "zh"])
    for (const key of ["mpcInstructions", "mpcApplied", "mpcStopped", "mpcRules", "applyMpc"])
      assert.ok(strings[lang][key]);
});

test("only Apply sends a new run; an empty choice uses ordinary automatic control", async () => {
  const { boxes, byId, panel, requests } = harness();
  const snap = { mode: "auto", runId: "one", modelStep: 0, controlHistory: [] };
  panel.render(snap, null, null);
  boxes.find((x) => x.value === "uBoil").checked = true;
  boxes.find((x) => x.value === "uVent").checked = true;
  assert.equal(requests.length, 0);
  assert.match(byId("mpcOwnership").textContent, /Auto/i);
  await byId("applyMpcButton").listeners.click();
  assert.deepEqual(requests[0], {
    mode: "mpc",
    mpcDevices: ["uBoil", "uVent"],
    evaluationLimits: plan.limits,
  });
  panel.render({ ...snap, runId: "new", mode: "mpc", mpcDevices: ["uBoil", "uVent"] }, null, null);
  for (const box of boxes) box.checked = false;
  boxes[0].listeners.change();
  assert.equal(byId("mpcMessage").textContent, strings.en.mpcDraftChanged);
  panel.translate();
  assert.match(byId("mpcOwnership").textContent, /MPC:.*[Hh]eating.*[Vv]entilation/);
  assert.match(byId("mpcOwnership").textContent, /Rule-based/);
  await byId("applyMpcButton").listeners.click();
  assert.deepEqual(requests[1], { mode: "auto", evaluationLimits: plan.limits });
  panel.notifyMpcStop();
  assert.equal(byId("mpcMessage").textContent, strings.en.mpcStopped);
  panel.render(null, null, null);
  assert.equal(byId("applyMpcButton").disabled, true);
});

test("unapplied draft survives reconnect and a separate reset; latest input error wins", async () => {
  const { byId, boxes, panel } = harness();
  const s = {
    mode: "mpc",
    runId: "active",
    modelStep: 1,
    controlHistory: [],
    mpcDevices: ["uBoil"],
  };
  panel.render(s, null, null);
  const vent = boxes.find((b) => b.value === "uVent");
  vent.checked = true;
  vent.listeners.change();
  panel.render(null, null, null);
  panel.render(s, null, null);
  panel.render({ ...s, runId: "reset" }, null, null);
  assert.equal(vent.checked, true);
  panel.notifyMpcStop();
  byId("limittemperatureMin").value = "";
  await byId("applyMpcButton").listeners.click();
  assert.equal(byId("mpcMessage").textContent, strings.en.scheduleLimitsError);
});

test("explicit recovery restarts from confirmed MPC ownership, limits and uploaded window", () => {
  const s = {
    mode: "mpc",
    scenario: "uploaded",
    seed: 9,
    targets: { dayTemp: 22 },
    greenhouse: { request: { schemaVersion: 1, overrides: { floorArea: 144 } } },
    climateMetrics: { limits: plan.limits },
    mpcDevices: ["uBoil", "uLamp"],
    mpcPolicy: "policy",
    weatherId: "active",
    runWindow: { startSeconds: 900 },
  };
  assert.deepEqual(
    plan.recoverySettings(s, (w) => w),
    {
      mode: "mpc",
      scenario: "uploaded",
      seed: 9,
      targets: s.targets,
      greenhouseConfig: s.greenhouse.request,
      evaluationLimits: plan.limits,
      mpcDevices: s.mpcDevices,
      mpcPolicy: "policy",
      weatherId: "active",
      runWindow: s.runWindow,
    },
  );
  const fallback = plan.recoverySettings(null);
  assert.deepEqual(fallback, {
    mode: "auto",
    scenario: "spring",
    seed: 42,
    greenhouseConfig: { schemaVersion: 1, overrides: {} },
  });
  // The backend retains the prior greenhouse when the field is omitted.
  assert.deepEqual((fallback.greenhouseConfig ?? s.greenhouse.request).overrides, {});
});
