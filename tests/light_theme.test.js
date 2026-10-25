"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const css = fs.readFileSync(path.join(root, "styles.css"), "utf8");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const rootRule = css.match(/:root\s*\{([^}]+)\}/)[1];
const tokens = Object.fromEntries(
  [...rootRule.matchAll(/(--[\w-]+):\s*(#[\da-f]{6});/gi)].map((match) => [match[1], match[2]]),
);

function luminance(hex) {
  const channels = hex
    .slice(1)
    .match(/../g)
    .map((value) => {
      const channel = parseInt(value, 16) / 255;
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

function contrast(first, second) {
  const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

test("light workspace metadata and white card tokens agree", () => {
  assert.equal(tokens["--bg"], "#f6f9f3");
  assert.equal(tokens["--panel"], "#ffffff");
  assert.match(rootRule, /color-scheme: light/);
  assert.match(html, /name="color-scheme" content="light"/);
  assert.match(html, /name="theme-color" content="#f6f9f3"/);
  assert.doesNotMatch(css, /color-scheme: dark/);
});

test("text and semantic colors remain readable on light workspace surfaces", () => {
  for (const foreground of [
    "--text",
    "--muted",
    "--muted-strong",
    "--green",
    "--mint",
    "--amber",
    "--blue",
    "--violet",
    "--danger",
  ]) {
    for (const background of ["--bg", "--panel", "--panel-strong", "--panel-soft"]) {
      assert.ok(
        contrast(tokens[foreground], tokens[background]) >= 4.5,
        `${foreground} on ${background}`,
      );
    }
  }
  for (const background of ["--green", "--green-hover"]) {
    assert.ok(
      contrast(tokens["--on-accent"], tokens[background]) >= 4.5,
      `button text on ${background}`,
    );
  }
});

test("the day/night scene has its own readable overlay palette", () => {
  const scene = css.match(/\.greenhouse-scene\s*\{([^}]+)\}/)[1];
  assert.match(scene, /--muted: #b4c9be/);
  assert.match(scene, /--text: #eef9f3/);
  assert.match(scene, /var\(--daylight\)/);
});
