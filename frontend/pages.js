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
  function create({ t, onChange, document: doc = root.document, window: win = root }) {
    const panels = Array.from(doc.querySelectorAll("[data-page]"));
    const links = Array.from(doc.querySelectorAll("[data-page-link]"));
    const title = doc.getElementById("workspaceTitle");
    const description = doc.getElementById("workspaceDescription");
    let active = resolve(win.location.hash);
    // Move the existing nodes once; their model state and event listeners survive navigation.
    doc.getElementById("comparisonWorkspace").append(doc.querySelector(".comparison-section"));
    doc.getElementById("runProgressHost").append(doc.getElementById("runProgressPanel"));
    function translate() {
      title.textContent = t(routes[active].title);
      description.textContent = t(routes[active].description);
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
    return { navigate, translate };
  }
  const api = { resolve, create };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GreenlightPages = api;
})(typeof window === "object" ? window : globalThis);
