"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const translations = require("../frontend/translations.js");

test("public translation keys and substitutions exist in both languages", () => {
  assert.deepEqual(Object.keys(translations.en).sort(), Object.keys(translations.zh).sort());
  const html = fs.readFileSync(path.join(__dirname, "../index.html"), "utf8");
  for (const [, key] of html.matchAll(/data-i18n(?:-aria-label)?="([^"]+)"/g)) {
    assert.equal(typeof translations.en[key], "string", key);
    assert.equal(typeof translations.zh[key], "string", key);
  }
  for (const key of Object.keys(translations.en)) {
    const tokens = (text) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();
    assert.deepEqual(tokens(translations.en[key]), tokens(translations.zh[key]), key);
  }
});
