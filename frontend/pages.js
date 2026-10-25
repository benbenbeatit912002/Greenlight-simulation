(function (root) {
  "use strict";
  const routes = {
    simulation: { title: "pageSimulation", description: "pageSimulationDescription" },
    weatherImport: { title: "pageWeather", description: "pageWeatherDescription" },
    greenhouseSettings: { title: "pageGreenhouse", description: "pageGreenhouseDescription" },
    controllerPlanner: { title: "pageControllers", description: "pageControllersDescription" },
  };
  function resolve(hash) {
    const name = hash.replace(/^#/, "");
    return Object.hasOwn(routes, name) ? name : "simulation";
  }
  // Describe applied server state only; an upload preview or a settings draft is not applied.
  function workflowState(snapshot, baseline) {
    if (!snapshot || snapshot.engine !== "greenlight-gym2" || !snapshot.greenhouse) {
      return {
        weather: "workflowUnavailable",
        greenhouse: "workflowUnavailable",
        comparison: "workflowUnavailable",
        values: {},
      };
    }
    const fields = snapshot.greenhouse.fields || [];
    const overrides = snapshot.greenhouse.request?.overrides || {};
    const custom = fields.filter((field) => Object.hasOwn(overrides, field.key)).length;
    return {
      weather: snapshot.weatherId ? "workflowUploadedActive" : "workflowSampleActive",
      greenhouse: custom ? "workflowOverrides" : "workflowReferenceDefaults",
      comparison: baseline ? "workflowBaselineSaved" : "workflowNoBaseline",
      values: { custom, defaults: fields.length - custom },
    };
  }
  function create({ t, onChange, document: doc = root.document, window: win = root }) {
    const panels = Array.from(doc.querySelectorAll("[data-page]"));
    const links = Array.from(doc.querySelectorAll("[data-page-link]"));
    const title = doc.getElementById("workspaceTitle");
    const description = doc.getElementById("workspaceDescription");
    let active = resolve(win.location.hash);
    let snapshot = null;
    let baseline = null;
    function renderWorkflow(next = snapshot, saved = baseline) {
      snapshot = next;
      baseline = saved;
      const state = workflowState(snapshot, baseline);
      for (const [name, id] of [
        ["weather", "workflowWeatherStatus"],
        ["greenhouse", "workflowGreenhouseStatus"],
        ["comparison", "workflowComparisonStatus"],
      ]) {
        const text = t(state[name]).replace(/\{(\w+)\}/g, (match, key) =>
          Object.hasOwn(state.values, key) ? String(state.values[key]) : match,
        );
        const element = doc.getElementById(id);
        if (element.textContent !== text) element.textContent = text;
      }
    }
    // Move the existing nodes once; their model state and event listeners survive navigation.
    doc.getElementById("comparisonWorkspace").append(doc.querySelector(".comparison-section"));
    doc.getElementById("runProgressHost").append(doc.getElementById("runProgressPanel"));
    function translate() {
      title.textContent = t(routes[active].title);
      description.textContent = t(routes[active].description);
      renderWorkflow();
    }
    function show(name, { focus = true } = {}) {
      active = resolve(name);
      for (const panel of panels) panel.hidden = panel.dataset.page !== active;
      for (const link of links) {
        if (link.dataset.pageLink === active) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      }
      translate();
      if (focus) {
        title.focus({ preventScroll: true });
        win.scrollTo({ top: 0, behavior: "instant" });
      }
      onChange?.(active);
    }
    function navigate(name, options) {
      const next = resolve(name);
      if (win.location.hash !== `#${next}`) win.history.pushState(null, "", `#${next}`);
      show(next, options);
    }
    doc.addEventListener("click", (event) => {
      const link = event.target.closest?.('a[href^="#"]');
      if (
        !link ||
        event.defaultPrevented ||
        event.button !== 0 ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey ||
        event.altKey
      )
        return;
      const target = link.getAttribute("href").slice(1);
      if (!Object.hasOwn(routes, target)) return;
      event.preventDefault();
      navigate(target);
    });
    win.addEventListener("hashchange", () => show(win.location.hash));
    show(active, { focus: false });
    return { navigate, translate, renderWorkflow };
  }
  const api = { resolve, workflowState, create };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GreenlightPages = api;
})(typeof window === "object" ? window : globalThis);
