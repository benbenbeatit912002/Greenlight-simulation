"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { create, resolve } = require("../frontend/pages.js");
const translations = require("../frontend/translations.js");

class Element {
  constructor(dataset = {}) {
    this.dataset = dataset;
    this.attributes = {};
    this.textContent = "";
    this.children = [];
    this.hidden = false;
  }
  append(child) {
    if (child.parent)
      child.parent.children = child.parent.children.filter((item) => item !== child);
    child.parent = this;
    this.children.push(child);
  }
  setAttribute(key, value) {
    this.attributes[key] = value;
  }
  removeAttribute(key) {
    delete this.attributes[key];
  }
  getAttribute(key) {
    return this.attributes[key];
  }
  focus() {
    this.focused = true;
  }
}

function fixture(hash = "") {
  let language = "en";
  const ids = Object.fromEntries(
    [
      "workspaceTitle",
      "workspaceDescription",
      "comparisonWorkspace",
      "runProgressHost",
      "runProgressPanel",
      "workflowWeatherStatus",
      "workflowGreenhouseStatus",
      "workflowComparisonStatus",
    ].map((id) => [id, new Element()]),
  );
  const routes = ["simulation", "weatherImport", "greenhouseSettings", "controllerPlanner"];
  const panels = routes.map((page) => new Element({ page }));
  const links = routes.map((pageLink) => new Element({ pageLink }));
  const comparison = new Element();
  panels[0].append(comparison);
  panels[0].append(ids.runProgressPanel);
  const draft = new Element();
  draft.value = "123.45";
  panels[2].append(draft);
  const docEvents = {};
  const winEvents = {};
  const changes = [];
  const history = [];
  const doc = {
    querySelectorAll: (selector) => (selector === "[data-page]" ? panels : links),
    querySelector: () => comparison,
    getElementById: (id) => {
      assert.ok(ids[id], id);
      return ids[id];
    },
    addEventListener: (name, handler) => (docEvents[name] = handler),
  };
  const win = {
    location: { hash },
    history: {
      pushState: (_state, _title, next) => {
        history.push(next);
        win.location.hash = next;
      },
    },
    addEventListener: (name, handler) => (winEvents[name] = handler),
    scrollTo: () => {},
  };
  const pages = create({
    document: doc,
    window: win,
    t: (key) => translations[language][key],
    onChange: (page) => changes.push(page),
  });
  return {
    pages,
    ids,
    panels,
    links,
    comparison,
    draft,
    history,
    changes,
    docEvents,
    winEvents,
    win,
    language: (value) => (language = value),
  };
}

test("direct page links resolve safely, with live simulation as the default", () => {
  assert.equal(resolve("#weatherImport"), "weatherImport");
  assert.equal(resolve("#greenhouseSettings"), "greenhouseSettings");
  assert.equal(resolve("#controllerPlanner"), "controllerPlanner");
  for (const hash of ["", "#unknown", "#__proto__", "#constructor"]) {
    assert.equal(resolve(hash), "simulation");
  }
  const f = fixture("#weatherImport");
  assert.equal(f.panels[1].hidden, false);
  assert.equal(f.panels[0].hidden, true);
  assert.equal(f.links[1].attributes["aria-current"], "page");
});

test("navigation preserves draft nodes and relocates existing comparison/progress once", () => {
  const f = fixture();
  assert.equal(f.ids.comparisonWorkspace.children[0], f.comparison);
  assert.equal(f.ids.runProgressHost.children[0], f.ids.runProgressPanel);
  for (const page of ["weatherImport", "greenhouseSettings", "controllerPlanner", "simulation"]) {
    f.pages.navigate(page);
    for (const panel of f.panels) assert.equal(panel.hidden, panel.dataset.page !== page);
    assert.equal(f.links.filter((link) => link.attributes["aria-current"] === "page").length, 1);
  }
  assert.equal(f.panels[2].children[0], f.draft);
  assert.equal(f.draft.value, "123.45");
  assert.equal(f.ids.comparisonWorkspace.children.length, 1);
  assert.equal(f.ids.runProgressHost.children.length, 1);
  assert.equal(f.ids.workspaceTitle.focused, true);
});

test("guide links use history, ignore modified clicks, and support back/forward hash changes", () => {
  const f = fixture();
  const link = new Element();
  link.setAttribute("href", "#greenhouseSettings");
  const event = (extra = {}) => ({
    target: { closest: () => link },
    button: 0,
    preventDefault() {
      this.prevented = true;
    },
    ...extra,
  });
  const click = event();
  f.docEvents.click(click);
  assert.equal(click.prevented, true);
  assert.equal(f.history.at(-1), "#greenhouseSettings");
  for (const extra of [
    { ctrlKey: true },
    { metaKey: true },
    { button: 1 },
    { defaultPrevented: true },
  ]) {
    const modified = event(extra);
    f.docEvents.click(modified);
    assert.equal(modified.prevented, undefined);
  }
  assert.equal(f.history.length, 1);
  f.win.location.hash = "#weatherImport";
  f.winEvents.hashchange();
  assert.equal(f.ids.workspaceTitle.textContent, translations.en.pageWeather);
  assert.equal(f.history.length, 1);
});

test("applied summary survives navigation and language changes, without showing draft edits", () => {
  const f = fixture();
  const snapshot = {
    engine: "greenlight-gym2",
    weatherId: "uploaded",
    greenhouse: {
      fields: [{ key: "area" }, { key: "heat" }],
      request: { overrides: { area: 100 } },
    },
  };
  f.pages.renderWorkflow(snapshot, null);
  const appliedText = f.ids.workflowGreenhouseStatus.textContent;
  assert.ok(appliedText.includes("1 user overrides"));
  assert.ok(appliedText.includes("1 editable settings"));
  f.draft.value = "999";
  f.pages.navigate("controllerPlanner");
  assert.equal(f.ids.workflowGreenhouseStatus.textContent, appliedText);
  f.language("zh");
  f.pages.translate();
  assert.equal(f.ids.workflowWeatherStatus.textContent, translations.zh.workflowUploadedActive);
  assert.ok(f.ids.workflowGreenhouseStatus.textContent.includes("1 項自訂"));
  assert.ok(!f.ids.workflowGreenhouseStatus.textContent.includes("{custom}"));
  assert.equal(f.draft.value, "999");
});

test("failed model connection removes stale applied claims, then reconnect restores them", () => {
  const f = fixture();
  const snapshot = {
    engine: "greenlight-gym2",
    greenhouse: { fields: [], request: { overrides: {} } },
  };
  f.pages.renderWorkflow(snapshot, { runId: "old-baseline" });
  assert.equal(f.ids.workflowComparisonStatus.textContent, translations.en.workflowBaselineSaved);
  f.pages.renderWorkflow(null, { runId: "old-baseline" });
  for (const id of [
    "workflowWeatherStatus",
    "workflowGreenhouseStatus",
    "workflowComparisonStatus",
  ]) {
    assert.equal(f.ids[id].textContent, translations.en.workflowUnavailable);
  }
  f.pages.renderWorkflow(snapshot, null);
  assert.equal(
    f.ids.workflowGreenhouseStatus.textContent,
    translations.en.workflowReferenceDefaults,
  );
  assert.equal(f.ids.workflowComparisonStatus.textContent, translations.en.workflowNoBaseline);
});
