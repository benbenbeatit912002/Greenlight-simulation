/* Pure source-clock arithmetic. Date's UTC methods avoid host timezone/DST shifts. */
(function (root) {
  "use strict";
  const keys = ["sourceYear", "timeConvention", "startSeconds", "endSeconds"];
  const recipe = (window) =>
    window ? Object.fromEntries(keys.map((key) => [key, window[key]])) : null;
  function dateTime(year, seconds) {
    return new Date(Date.UTC(year, 0, 1) + seconds * 1000).toISOString().slice(0, 16);
  }
  function secondsFromDate(year, value) {
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) return NaN;
    const time = Date.parse(`${value}:00Z`);
    if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 16) !== value) return NaN;
    return (time - Date.UTC(year, 0, 1)) / 1000;
  }
  function check(yearText, convention, startText, endText, bounds) {
    const year = Number(yearText);
    if (!Number.isInteger(year) || year < 1900 || year > 2100) return { error: "windowYearError" };
    if (!["source-local-standard", "UTC"].includes(convention))
      return { error: "windowConventionError" };
    const yearSeconds = (Date.UTC(year + 1, 0, 1) - Date.UTC(year, 0, 1)) / 1000;
    if (bounds.sourceEndSeconds > yearSeconds) return { error: "windowYearCoverageError" };
    const start = secondsFromDate(year, startText),
      end = secondsFromDate(year, endText);
    if (![start, end].every((value) => Number.isInteger(value) && value % 900 === 0))
      return { error: "windowGridError" };
    if (start >= end) return { error: "windowOrderError" };
    if (start < bounds.earliestStartSeconds || end > bounds.latestEndSeconds)
      return { error: "windowCoverageError" };
    return {
      window: {
        sourceYear: year,
        timeConvention: convention,
        startSeconds: start,
        endSeconds: end,
      },
      steps: (end - start) / 900,
      hours: (end - start) / 3600,
    };
  }
  const api = { recipe, dateTime, secondsFromDate, check };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.GreenlightRunWindow = api;
})(typeof globalThis === "undefined" ? this : globalThis);
