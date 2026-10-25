"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const translations = require("../frontend/translations.js");
const { copy } = require("../frontend/climate-upload.js");
const read = (file) => fs.readFileSync(path.join(__dirname, "..", file), "utf8");

test("workflow headings use decimal numbering in both languages", () => {
  for (const language of ["en", "zh"]) {
    ["workflowWeatherStep", "workflowGreenhouseStep", "workflowCompareStep"].forEach((key, i) => {
      assert.ok(translations[language][key].startsWith(i + 1 + ". "), key);
    });
    assert.ok(copy[language].stage.startsWith("1a. "));
    assert.ok(copy[language].windowTitle.startsWith("1b. "));
  }
});

test("live interface has no decorative middle dots but preserves degree-day units", () => {
  const html = read("index.html");
  assert.ok(html.includes("°C·day"));
  assert.doesNotMatch(html.replaceAll("°C·day", ""), /·|&middot;|&#183;/);
  for (const [, asset] of html.matchAll(/src="(frontend\/[^"?]+)\?[^"]+"/g)) {
    assert.doesNotMatch(read(asset), /·|&middot;|&#183;/, asset);
  }
});

test("workflow links remain links without underlining and retain a visible focus indicator", () => {
  const html = read("index.html");
  for (const route of ["weatherImport", "greenhouseSettings", "controllerPlanner"]) {
    assert.ok(html.includes('href="#' + route + '"'));
  }
  const css = read("styles.css");
  const block = css.match(/\.workflow-steps a\s*\{([^}]+)\}/)[1];
  assert.match(block, /text-decoration:\s*none/);
  assert.match(css, /\.workflow-steps a:focus-visible,[\s\S]*?outline:\s*2px solid/);
  assert.match(css, /\.controller-reference-links\s*\{[^}]*flex-wrap:\s*wrap/);
});

test("native disclosure labels and decorative arrows are centered and keyboard focus stays visible", () => {
  const css = read("styles.css");
  const summary = css.match(/\.greenhouse-settings summary\s*\{([^}]+)\}/)[1];
  assert.match(summary, /display:\s*flex/);
  assert.match(summary, /align-items:\s*center/);
  assert.match(summary, /justify-content:\s*center/);
  assert.match(summary, /min-height:\s*44px/);
  assert.match(css, /\.greenhouse-settings summary::before\s*\{[^}]*content:\s*""/);
  assert.match(css, /details\[open\] > summary::before\s*\{[^}]*rotate\(45deg\)/);
  assert.match(css, /\.greenhouse-settings summary:focus-visible,[\s\S]*?outline:\s*2px solid/);
  const settings = read("frontend/greenhouse-settings.js");
  assert.ok(settings.includes('const details = node("details")'));
  assert.ok(settings.includes('details.append(node("summary", t(group)))'));
});
