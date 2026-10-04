/* Draft settings are local UI state; only explicit initialization changes a run. */
(function () {
  "use strict";
  // Geometry helpers use the same aggregate areas/heights as the full model.
  // Length and width are calculator inputs, not extra spatial model parameters.
  function rectangleArea(length, width, bounds = { min: 1, max: 2000 }) {
    if (![length, width].every((v) => Number.isFinite(v) && v > 0)) return null;
    const area = length * width;
    return Number.isFinite(area) && area >= bounds.min && area <= bounds.max ? area : null;
  }
  function airVolumes({ floorArea, mainHeight, totalHeight }) {
    if (
      ![floorArea, mainHeight, totalHeight].every((v) => Number.isFinite(v) && v > 0) ||
      totalHeight - mainHeight < 0.1 - 1e-9
    )
      return null;
    const main = floorArea * mainHeight;
    const top = floorArea * (totalHeight - mainHeight);
    const total = floorArea * totalHeight;
    return [main, top, total].every(Number.isFinite) ? { main, top, total } : null;
  }
  if (typeof module === "object" && module.exports) module.exports = { rectangleArea, airVolumes };
  if (typeof document === "undefined") return;
  const panel = document.getElementById("greenhouseSettings");
  const text = {
    en: {
      title: "Step 3 · Greenhouse and initial state",
      intro:
        "Review model defaults or enter overrides. Leave a field blank to inherit its default. Apply settings only when you want to initialize a new run.",
      geometry: "Greenhouse dimensions and air volume",
      sizeCalculator: "Start with length × width",
      sizeIntro:
        "For a rectangular floor, enter its length and width in metres. This tool changes only the floor-area draft, not the active simulation.",
      length: "Floor length (m)",
      width: "Floor width (m)",
      sizeButton: "Copy floor area to draft",
      sizeEmpty: "Enter both dimensions to calculate floor area.",
      sizeInvalid: "Use positive dimensions with a floor area inside the supported range:",
      sizeResult: "Calculated floor area",
      sizeCopied: "This area is in the draft. Review cover/vent areas, then apply settings below.",
      sizeNotCopied: "Not copied to the draft. Select Copy floor area to draft.",
      sizeNote:
        "Length and width are a calculator only and are not saved on reload. GreenLight uses aggregate areas and heights, not a 3D floor plan. Cover and vent areas are never guessed or resized.",
      spacePreview: "Space preview · settings draft",
      previewInvalid: "Correct the greenhouse settings to preview air volumes.",
      floorPreview: "Floor area",
      mainVolume: "Main-compartment volume",
      topVolume: "Top-compartment volume",
      totalVolume: "Total air volume",
      heightHelp:
        "Main-compartment height defines the lower air volume. Mean greenhouse height = total air volume ÷ floor area; it is not the roof-ridge height. Total volume = floor area × mean height. Cover area includes the roof and walls; enter your actual design.",
      equipment: "Installed equipment",
      cover: "Cover properties",
      initial: "Initial main-air conditions",
      crop: "Initial tomato crop",
      assumptions:
        "Area fields are independent: changing floor area does not resize the cover or vents. Boiler and CO₂ capacities are per floor area; total capacities update automatically. Zero capacity disables output, not the physical presence of equipment or leakage. Cover settings retain other material/screen properties: no named material preset is implied.",
      initialNote:
        "Only the named initial states change. Top air, surfaces and soil retain GreenLight defaults. Changing main-air temperature preserves its default RH and CO₂ ppm unless overridden. LAI is derived from leaf dry mass. Tomato defaults describe an established crop, not a seedling. No warm-up or greenhouse calibration is performed.",
      defaults: "Use model defaults",
      apply: "Apply settings and initialize",
      applying: "Initializing…",
      inherited: "Model default",
      review: "Review settings before applying",
      noChanges: "No unapplied changes.",
      pending: "Unapplied changes — the active run is unchanged.",
      active: "Applied settings",
      offline: "Connect the full model to load supported settings.",
      invalid: "Check the highlighted input and its supported range.",
      geometryError:
        "Cover area must cover floor area, roof vent area must not exceed floor area, and total height must exceed main height by at least 0.1 m.",
      success: "Settings applied to a new run. Press Start simulation.",
      field: "Setting",
      value: "Next run",
      origin: "Source",
      override: "User override",
      total: "Whole-greenhouse resources",
      totals: "Installed totals",
      volume: "Air volume (main / top)",
      boiler: "Boiler",
      lamp: "Top lamps",
      co2: "CO₂ source",
      heat: "Heating",
      electricity: "Lighting",
      cost: "Estimated cost",
      changed: "changed settings",
      draftWarning:
        "Weather selection and the top reset button keep applied settings. Use the button below to apply this draft.",
    },
    zh: {
      title: "第三階段 · 溫室設定與初始狀態",
      intro: "查看模型預設值或輸入自訂值；欄位留空即沿用預設值。按下套用後才會初始化新的模擬。",
      geometry: "溫室尺寸與空間",
      sizeCalculator: "從長 × 寬開始設定",
      sizeIntro: "矩形地板可直接輸入長、寬（公尺）。換算只填入地板面積草稿，不會立刻改變目前模擬。",
      length: "地板長度（m）",
      width: "地板寬度（m）",
      sizeButton: "將地板面積填入草稿",
      sizeEmpty: "輸入長、寬後即可計算地板面積。",
      sizeInvalid: "長、寬須為正數，換算地板面積須在支援範圍內：",
      sizeResult: "換算地板面積",
      sizeCopied: "此面積已在草稿中。請確認覆蓋與通風口面積，再按下方套用。",
      sizeNotCopied: "尚未填入草稿，請按「將地板面積填入草稿」。",
      sizeNote:
        "長、寬只是換算工具，重新整理後不保留。GreenLight 使用總面積與高度，不解析三維平面配置；覆蓋與通風口面積不會被猜測或自動縮放。",
      spacePreview: "空間預覽 · 設定草稿",
      previewInvalid: "請修正溫室設定後再預覽空氣體積。",
      floorPreview: "地板面積",
      mainVolume: "主空氣室體積",
      topVolume: "頂部空氣室體積",
      totalVolume: "總空氣體積",
      heightHelp:
        "主空氣室高度決定下層空間；溫室平均高度＝總空氣體積 ÷ 地板面積，不是屋脊最高點。總體積＝地板面積 × 平均高度。覆蓋面積包含屋頂與牆面，請填寫你的實際設計。",
      equipment: "已安裝設備",
      cover: "覆蓋材料參數",
      initial: "主空氣室初始條件",
      crop: "番茄作物初始狀態",
      assumptions:
        "面積欄位彼此獨立：改地板面積不會自動改覆蓋或通風口面積。供暖與 CO₂ 容量以每平方米輸入，全溫室容量會同步換算。容量為 0 只停用輸出，並不移除設備實體或漏風。覆蓋材料的其他參數與幕簾仍沿用預設值，不代表已選定某種材料。",
      initialNote:
        "只改變列出的初始狀態；頂部空氣、表面與土壤仍採 GreenLight 預設值。只改主空氣室溫度時會維持原本 RH 與 CO₂ ppm，除非另行指定。LAI 由葉片乾重計算；番茄預設值為已有生長量的作物，並非幼苗。沒有暖機，也不代表已完成溫室校正。",
      defaults: "使用模型預設值",
      apply: "套用設定並初始化",
      applying: "正在初始化…",
      inherited: "模型預設",
      review: "套用前確認設定",
      noChanges: "沒有尚未套用的變更。",
      pending: "尚未套用：目前模擬不會改變。",
      active: "已套用設定",
      offline: "連接完整模型後會載入可設定項目。",
      invalid: "請檢查標記的欄位與可接受範圍。",
      geometryError:
        "覆蓋面積不可小於地板面積；通風口面積不可大於地板面積；平均高度須比主空氣室至少高 0.1 公尺。",
      success: "已套用至新的模擬，按「開始模擬」即可執行。",
      field: "設定",
      value: "下次模擬",
      origin: "來源",
      override: "自訂",
      total: "全溫室累計資源",
      totals: "設備總容量",
      volume: "空氣體積（主室／頂部）",
      boiler: "供暖",
      lamp: "頂部補光燈",
      co2: "CO₂ 供應",
      heat: "供暖",
      electricity: "補光用電",
      cost: "估算費用",
      changed: "項變更",
      draftWarning: "選擇天氣或上方重設按鈕會保留已套用設定；請用下方按鈕套用這份草稿。",
    },
  };
  let snapshot = null,
    config = null,
    raw = {},
    dirty = false,
    busy = false,
    available = false,
    message = "";
  let form,
    fields = new Map(),
    status,
    review,
    applyButton,
    defaultsButton,
    sizeButton,
    sizeStatus,
    volumePreview;
  const sizeInputs = new Map();
  const language = () => (document.documentElement.lang.startsWith("zh") ? "zh" : "en");
  const t = (key) => text[language()][key];
  const label = (field) => field[language()];
  const number = (value) =>
    Number(value).toLocaleString(language() === "zh" ? "zh-TW" : "en", {
      maximumFractionDigits: 3,
    });
  const node = (tag, content) => {
    const element = document.createElement(tag);
    if (content !== undefined) element.textContent = content;
    return element;
  };
  const resetDraft = () => {
    raw = Object.fromEntries(
      Object.entries(config.request.overrides).map(([k, v]) => [k, String(v)]),
    );
    dirty = false;
    fields.forEach((input, key) => {
      input.value = raw[key] ?? "";
    });
  };

  function collect() {
    const overrides = {};
    let error = "";
    for (const field of config.fields) {
      const input = fields.get(field.key),
        value = raw[field.key] ?? "";
      const invalid =
        input.validity.badInput ||
        (value.trim() !== "" &&
          (!Number.isFinite(Number(value)) ||
            Number(value) < field.min ||
            Number(value) > field.max));
      input.setAttribute("aria-invalid", String(invalid));
      if (invalid) error = t("invalid");
      if (value.trim() !== "") overrides[field.key] = Number(value);
    }
    const v = { ...config.defaults, ...overrides };
    if (
      !error &&
      (v.coverArea < v.floorArea ||
        v.roofVentArea > v.floorArea ||
        v.totalHeight - v.mainHeight < 0.1 - 1e-9)
    )
      error = t("geometryError");
    return { request: { schemaVersion: 1, overrides }, values: v, error };
  }
  function refresh() {
    if (!config || !form) return;
    const checked = collect();
    form.disabled = busy || !available;
    applyButton.disabled = busy || !available || Boolean(checked.error);
    defaultsButton.disabled = busy || !available;
    applyButton.textContent = t(busy ? "applying" : "apply");
    const changed = config.fields.filter(
      (f) => checked.request.overrides[f.key] !== config.request.overrides[f.key],
    ).length;
    status.textContent = !available
      ? t("offline")
      : checked.error ||
        message ||
        (changed ? `${t("pending")} ${changed} ${t("changed")}` : t("noChanges"));
    status.classList.toggle("run-window-error", Boolean(checked.error));
    review.replaceChildren();
    const table = node("table"),
      head = node("tr");
    ["field", "value", "origin"].forEach((k) => {
      const th = node("th", t(k));
      th.scope = "col";
      head.append(th);
    });
    const thead = node("thead");
    thead.append(head);
    table.append(thead);
    const body = node("tbody");
    for (const field of config.fields) {
      const tr = node("tr");
      [
        label(field),
        `${number(checked.values[field.key])} ${field.unit}`,
        t(field.key in checked.request.overrides ? "override" : "inherited"),
      ].forEach((v) => tr.append(node("td", v)));
      body.append(tr);
    }
    table.append(body);
    review.append(table);
    refreshGeometry(checked);
    refreshActive();
  }
  function sizeArea() {
    if ([...sizeInputs.values()].some((input) => input.validity.badInput || !input.value.trim()))
      return null;
    return rectangleArea(
      Number(sizeInputs.get("length").value),
      Number(sizeInputs.get("width").value),
      config.fields.find((field) => field.key === "floorArea"),
    );
  }
  function refreshGeometry(checked) {
    if (!sizeButton) return;
    const area = sizeArea();
    const empty = [...sizeInputs.values()].every(
      (input) => !input.value && !input.validity.badInput,
    );
    sizeInputs.forEach((input) =>
      input.setAttribute("aria-invalid", String(!empty && area === null)),
    );
    sizeButton.disabled = busy || !available || area === null;
    const bounds = config.fields.find((field) => field.key === "floorArea");
    sizeStatus.textContent = empty
      ? t("sizeEmpty")
      : area === null
        ? `${t("sizeInvalid")} ${bounds.min}–${number(bounds.max)} m².`
        : `${t("sizeResult")}: ${number(area)} m². ${t(Number(raw.floorArea) === area ? "sizeCopied" : "sizeNotCopied")}`;
    sizeStatus.classList.toggle("run-window-error", !empty && area === null);
    volumePreview.replaceChildren(node("h3", t("spacePreview")));
    const volumes = checked.error ? null : airVolumes(checked.values);
    if (!volumes) {
      volumePreview.append(node("p", t("previewInvalid")));
      return;
    }
    const list = node("dl");
    list.className = "greenhouse-volume-grid";
    for (const [key, value, unit] of [
      ["floorPreview", checked.values.floorArea, "m²"],
      ["mainVolume", volumes.main, "m³"],
      ["topVolume", volumes.top, "m³"],
      ["totalVolume", volumes.total, "m³"],
    ]) {
      const item = node("div");
      const valueNode = node("dd", `${number(value)} ${unit}`);
      valueNode.id = `gh-preview-${key}`;
      item.append(node("dt", t(key)), valueNode);
      list.append(item);
    }
    volumePreview.append(list);
  }
  function buildSizeCalculator() {
    const calculator = node("section");
    calculator.className = "greenhouse-size-calculator";
    calculator.setAttribute("aria-labelledby", "greenhouseSizeTitle");
    const title = node("h3", t("sizeCalculator"));
    title.id = "greenhouseSizeTitle";
    calculator.append(title, node("p", t("sizeIntro")));
    const grid = node("div");
    grid.className = "run-window-grid";
    for (const key of ["length", "width"]) {
      let input = sizeInputs.get(key);
      if (!input) {
        input = node("input");
        input.id = `gh-size-${key}`;
        input.type = "number";
        input.min = "0";
        input.step = "any";
        input.addEventListener("input", () => refresh());
        sizeInputs.set(key, input);
      }
      input.setAttribute("aria-describedby", "greenhouseSizeStatus greenhouseSizeNote");
      const wrapper = node("label", t(key));
      wrapper.htmlFor = input.id;
      wrapper.append(input);
      grid.append(wrapper);
    }
    calculator.append(grid);
    sizeStatus = node("p");
    sizeStatus.id = "greenhouseSizeStatus";
    sizeStatus.setAttribute("role", "status");
    sizeButton = node("button", t("sizeButton"));
    sizeButton.id = "greenhouseCopyArea";
    sizeButton.type = "button";
    sizeButton.className = "showcase-secondary";
    sizeButton.addEventListener("click", () => {
      const area = sizeArea();
      if (area === null || busy || !available) return;
      raw.floorArea = String(area);
      fields.get("floorArea").value = raw.floorArea;
      dirty = true;
      message = "";
      refresh();
    });
    const note = node("p", t("sizeNote"));
    note.id = "greenhouseSizeNote";
    calculator.append(sizeStatus, sizeButton, note);
    return calculator;
  }
  function refreshActive() {
    const active = document.getElementById("greenhouseActive"),
      totals = document.getElementById("greenhouseResourceTotals");
    if (!active || !config) return;
    active.textContent = `${t("active")}: ${number(config.floorAreaM2)} m² · ${t("volume")}: ${number(config.mainAirVolumeM3)} / ${number(config.topAirVolumeM3)} m³. ${t("totals")}: ${t("boiler")} ${number(config.boilerCapacityKw)} kW · ${t("lamp")} ${number(config.lampCapacityKw)} kW · ${t("co2")} ${number(config.co2CapacityKgH)} kg/h · LAI ${number(config.initialLai)}.`;
    const r = snapshot?.wholeGreenhouseResources;
    totals.hidden = !r || !available;
    if (r)
      totals.textContent = `${t("total")}: ${t("heat")} ${number(r.heatKwh)} kWh · ${t("electricity")} ${number(r.lampKwh)} kWh · CO₂ ${number(r.co2Kg)} kg · ${t("cost")} €${number(r.costEur)}.`;
  }
  function build() {
    panel.setAttribute("aria-label", t("title"));
    const openGroups = new Set(
      [...panel.querySelectorAll("details[data-group][open]")].map((e) => e.dataset.group),
    );
    panel.replaceChildren(node("h2", t("title")), node("p", t("intro")));
    if (!config) {
      panel.append(node("p", t("offline")));
      return;
    }
    const active = node("p");
    active.id = "greenhouseActive";
    panel.append(active);
    form = node("fieldset");
    form.className = "greenhouse-fields";
    const legend = node("legend", t("review"));
    legend.className = "sr-only";
    form.append(legend);
    const previousFields = fields;
    fields = new Map();
    for (const group of ["geometry", "equipment", "cover", "initial", "crop"]) {
      const details = node("details");
      details.dataset.group = group;
      details.open = openGroups.has(group) || (previousFields.size === 0 && group === "geometry");
      details.append(node("summary", t(group)));
      if (group === "geometry") details.append(buildSizeCalculator());
      const grid = node("div");
      grid.className = "run-window-grid";
      for (const field of config.fields.filter((f) => f.group === group)) {
        const wrapper = node("label", `${label(field)} (${field.unit})`),
          existing = previousFields.get(field.key),
          input = existing || node("input");
        input.id = `gh-${field.key}`;
        wrapper.htmlFor = input.id;
        input.type = "number";
        input.step = "any";
        input.min = field.min;
        input.max = field.max;
        // Reuse native number inputs: incomplete text (e.g. 1e) is held by the
        // browser, even though .value is empty. Replacing it would lose badInput.
        if (!existing) input.value = raw[field.key] ?? "";
        input.placeholder = number(config.defaults[field.key]);
        const hint = node(
          "small",
          `${t("inherited")}: ${number(config.defaults[field.key])} ${field.unit} · ${field.min}–${number(field.max)}`,
        );
        hint.id = `gh-help-${field.key}`;
        input.setAttribute("aria-describedby", hint.id);
        if (!existing)
          input.addEventListener("input", () => {
            raw[field.key] = input.value;
            dirty = true;
            message = "";
            refresh();
          });
        fields.set(field.key, input);
        wrapper.append(input, hint);
        grid.append(wrapper);
      }
      details.append(grid);
      if (group === "geometry") {
        details.append(node("p", t("heightHelp")));
        volumePreview = node("section");
        volumePreview.id = "greenhouseVolumePreview";
        details.append(volumePreview);
      }
      form.append(details);
    }
    panel.append(form, node("p", t("assumptions")), node("p", t("initialNote")));
    const reviewDetails = node("details");
    reviewDetails.append(node("summary", t("review")));
    review = node("div");
    review.className = "weather-table-scroll";
    review.tabIndex = 0;
    review.setAttribute("role", "region");
    review.setAttribute("aria-label", t("review"));
    reviewDetails.append(review);
    panel.append(reviewDetails, node("p", t("draftWarning")));
    status = node("p");
    status.id = "greenhouseConfigStatus";
    status.setAttribute("role", "status");
    panel.append(status);
    const actions = node("div");
    actions.className = "showcase-actions";
    defaultsButton = node("button", t("defaults"));
    defaultsButton.id = "greenhouseDefaults";
    defaultsButton.type = "button";
    defaultsButton.className = "showcase-secondary";
    defaultsButton.addEventListener("click", () => {
      raw = {};
      dirty = true;
      message = "";
      fields.forEach((input) => {
        input.value = "";
      });
      sizeInputs.forEach((input) => {
        input.value = "";
      });
      refresh();
    });
    applyButton = node("button", t("apply"));
    applyButton.id = "greenhouseApply";
    applyButton.type = "button";
    applyButton.className = "showcase-primary";
    applyButton.addEventListener("click", () => {
      const checked = collect();
      if (checked.error || busy || !available) return;
      busy = true;
      message = "";
      refresh();
      document.dispatchEvent(
        new CustomEvent("greenlight-configuration-selected", {
          detail: {
            config: checked.request,
            complete(error) {
              busy = false;
              message = error || t("success");
              if (!error) {
                resetDraft();
                build();
              } else refresh();
            },
          },
        }),
      );
    });
    actions.append(defaultsButton, applyButton);
    panel.append(actions);
    const totals = node("p");
    totals.id = "greenhouseResourceTotals";
    panel.append(totals);
    refresh();
  }
  window.GreenlightSettings = {
    sync(next) {
      const changed = next?.runId !== snapshot?.runId;
      const wasAvailable = available;
      snapshot = next;
      config = next?.greenhouse || null;
      available = Boolean(config);
      if (!config) {
        build();
        return;
      }
      if (changed || !form) {
        if (!dirty) resetDraft();
        build();
      } else if (!wasAvailable) refresh();
      else refreshActive();
    },
    setBusy(value) {
      busy = value;
      refresh();
    },
    unavailable() {
      available = false;
      refresh();
    },
  };
  new MutationObserver(build).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["lang"],
  });
  build();
})();
