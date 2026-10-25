"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "frontend/climate-upload.js"), "utf8");

function fixture() {
  function element(tag = "div") {
    const handlers = new Map();
    return {
      tagName: tag.toUpperCase(),
      dataset: {},
      textContent: "",
      disabled: false,
      children: [],
      attributes: {},
      addEventListener(name, handler) {
        handlers.set(name, handler);
      },
      emit(name, event = {}) {
        return handlers.get(name)?.(event);
      },
      append(...children) {
        this.children.push(...children);
      },
      replaceChildren(...children) {
        this.children = children;
      },
      setAttribute(name, value) {
        this.attributes[name] = value;
      },
      set innerHTML(_) {
        throw new Error("Weather filenames must not be inserted as HTML");
      },
    };
  }
  const ids = Object.fromEntries(
    [
      "weatherImport",
      "weatherUploadForm",
      "weatherFile",
      "weatherFileLabel",
      "weatherChooseButton",
      "weatherFileName",
      "weatherCheckButton",
      "weatherUploadStatus",
      "weatherPreview",
    ].map((id) => [id, element()]),
  );
  ids.weatherFile.files = [];
  let nativeClicks = 0;
  ids.weatherFile.click = () => nativeClicks++;
  ids.weatherFileLabel.dataset.weatherI18n = "file";
  ids.weatherChooseButton.dataset.weatherI18n = "chooseFile";
  ids.weatherImport.querySelectorAll = () => [ids.weatherFileLabel, ids.weatherChooseButton];
  const document = {
    documentElement: { lang: "en" },
    getElementById: (id) => ids[id],
    createElement: element,
  };
  let onLanguageChange;
  const requests = [];
  let respond;
  vm.runInNewContext(source, {
    document,
    AbortController,
    window: { setTimeout: () => 1, clearTimeout: () => {} },
    MutationObserver: class {
      constructor(callback) {
        onLanguageChange = callback;
      }
      observe(target, options) {
        assert.equal(target, document.documentElement);
        assert.deepEqual(Array.from(options.attributeFilter), ["lang"]);
      }
    },
    fetch: (url, options) => {
      requests.push({ url, options });
      return new Promise((resolve) => (respond = resolve));
    },
  });
  return {
    ids,
    requests,
    get nativeClicks() {
      return nativeClicks;
    },
    language(lang) {
      document.documentElement.lang = lang;
      onLanguageChange();
    },
    select(file) {
      ids.weatherFile.files = file ? [file] : [];
      ids.weatherFile.emit("change");
    },
    submit() {
      return ids.weatherUploadForm.emit("submit", { preventDefault() {} });
    },
    respond(payload) {
      respond({
        ok: payload.ok,
        headers: { get: () => "application/json" },
        json: async () => payload,
      });
    },
  };
}

test("file button and empty message follow both interface languages", () => {
  const ui = fixture();
  assert.equal(ui.ids.weatherChooseButton.textContent, "Choose file");
  assert.equal(ui.ids.weatherFileName.textContent, "No file selected");
  ui.language("zh-TW");
  assert.equal(ui.ids.weatherChooseButton.textContent, "選擇檔案");
  assert.equal(ui.ids.weatherFileName.textContent, "尚未選擇檔案");
  ui.language("en");
  assert.equal(ui.ids.weatherChooseButton.textContent, "Choose file");
  assert.equal(ui.ids.weatherFileName.textContent, "No file selected");
  assert.equal(ui.requests.length, 0);
});

test("choosing or translating preserves the actual file and treats its name as text", () => {
  const ui = fixture();
  const file = { name: '<img src=x onerror="bad()">-氣候.xlsx', size: 100 };
  ui.select(file);
  const originalFiles = ui.ids.weatherFile.files;
  ui.ids.weatherChooseButton.emit("click");
  assert.equal(ui.nativeClicks, 1);
  // Opening and cancelling the native dialog does not reset its existing FileList.
  assert.equal(ui.ids.weatherFile.files, originalFiles);
  for (const lang of ["zh-TW", "en"]) {
    ui.language(lang);
    assert.equal(ui.ids.weatherFile.files, originalFiles);
    assert.equal(ui.ids.weatherFile.files[0], file);
    assert.equal(ui.ids.weatherFileName.textContent, file.name);
  }
  assert.equal(ui.requests.length, 0);
  ui.select(null);
  assert.equal(ui.ids.weatherFileName.textContent, "No file selected");
});

test("invalid workbooks still fail locally without a request", async () => {
  const ui = fixture();
  ui.select({ name: "weather.csv", size: 100 });
  await ui.submit();
  assert.equal(ui.requests.length, 0);
  assert.equal(ui.ids.weatherFileName.textContent, "weather.csv");
  assert.equal(ui.ids.weatherUploadStatus.textContent, "Could not validate this workbook");
  assert.equal(ui.ids.weatherChooseButton.disabled, false);
});

test("checking disables both picker controls and preserves selection across language changes", async () => {
  const ui = fixture();
  const file = { name: "weather.xlsx", size: 100 };
  ui.select(file);
  const pending = ui.submit();
  assert.equal(ui.requests.length, 1);
  assert.equal(ui.requests[0].url, "/api/weather/preview");
  assert.equal(ui.requests[0].options.body, file);
  assert.equal(ui.requests[0].options.method, "POST");
  assert.equal(ui.requests[0].options.credentials, "same-origin");
  ui.language("zh-TW");
  for (const id of ["weatherChooseButton", "weatherFile", "weatherCheckButton"]) {
    assert.equal(ui.ids[id].disabled, true);
  }
  assert.equal(ui.ids.weatherFileName.textContent, file.name);
  ui.respond({ ok: false, error: { key: "unavailable" } });
  await pending;
  for (const id of ["weatherChooseButton", "weatherFile", "weatherCheckButton"]) {
    assert.equal(ui.ids[id].disabled, false);
  }
  assert.equal(ui.ids.weatherFileName.textContent, file.name);
  assert.equal(ui.ids.weatherChooseButton.textContent, "選擇檔案");
});

test("successful workbook preview survives translation without another upload", async () => {
  const ui = fixture();
  const file = { name: "weather.xlsx", size: 100 };
  ui.select(file);
  const pending = ui.submit();
  ui.respond({
    ok: true,
    weather: {
      conversionReady: false,
      rowCount: 2,
      intervalMinutes: 5,
      start: "2023-01-01T00:00:00Z",
      end: "2023-01-01T00:05:00Z",
      missingModelColumns: [],
      columns: [],
      preview: [],
      ranges: {},
      sha256: "example",
    },
  });
  await pending;
  assert.equal(ui.ids.weatherUploadStatus.textContent, "Data checks passed, preview only");
  ui.language("zh-TW");
  assert.equal(ui.ids.weatherUploadStatus.textContent, "資料檢查通過, 僅供預覽");
  assert.equal(ui.ids.weatherFileName.textContent, file.name);
  assert.equal(ui.requests.length, 1);
  assert.ok(ui.ids.weatherPreview.children.length > 0);
});

test("picker markup provides a keyboard button, hidden native input and filename status", () => {
  const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
  const css = fs.readFileSync(path.join(root, "styles.css"), "utf8");
  const input = html.match(/<input\s+id="weatherFile"[\s\S]*?\/>/)[0];
  assert.match(input, /type="file"/);
  assert.match(input, /accept="\.xlsx"/);
  assert.match(input, /\shidden\s/);
  const button = html.match(/<button[^>]*id="weatherChooseButton"[^>]*>/)[0];
  assert.match(button, /type="button"/);
  assert.match(
    button,
    /aria-describedby="weatherFileLabel weatherFileName weatherLimits weatherPrivacy"/,
  );
  assert.match(html, /id="weatherFileName"[^>]*role="status"[^>]*aria-atomic="true"/);
  assert.match(css, /\.weather-file-button:focus-visible\s*\{[^}]*outline:/);
  assert.match(css, /\.weather-file-name\s*\{[^}]*overflow-wrap: anywhere/);
  assert.match(css, /\.weather-file-control\s*\{[^}]*flex: 0 1 auto/);
});
