// Chart rendering only; model state and playback remain in app.js.
(function (root) {
  "use strict";
  function createRenderer({ byId, t, formatHour }) {
    function chartConfiguration(history, targets, chartMode) {
      const styles = getComputedStyle(document.documentElement);
      const green = styles.getPropertyValue("--green").trim();
      const amber = styles.getPropertyValue("--amber").trim();
      const blue = styles.getPropertyValue("--blue").trim();
      const violet = styles.getPropertyValue("--violet").trim();
      const muted = styles.getPropertyValue("--muted").trim();

      if (chartMode === "humidity") {
        return {
          unit: "%",
          label: t("humidityChart"),
          minSpan: 20,
          series: [
            { label: t("indoorRh"), color: blue, values: history.map((point) => point.rh) },
            {
              label: t("outdoorRh"),
              color: muted,
              values: history.map((point) => point.outsideRh),
              dash: [4, 4],
            },
            {
              label: t("controlLimit"),
              color: amber,
              values: history.map(() => targets.maxRh),
              dash: [7, 5],
            },
          ],
        };
      }

      if (chartMode === "co2") {
        return {
          unit: " ppm",
          label: t("co2Chart"),
          minSpan: 300,
          series: [
            {
              label: t("indoorCo2Series"),
              color: green,
              values: history.map((point) => point.co2),
            },
            {
              label: t("controlTarget"),
              color: violet,
              values: history.map(() => targets.co2),
              dash: [7, 5],
            },
          ],
        };
      }

      return {
        unit: "°C",
        label: t("temperatureChart"),
        minSpan: 10,
        series: [
          { label: t("indoorSeries"), color: green, values: history.map((point) => point.airTemp) },
          {
            label: t("canopySeries"),
            color: amber,
            values: history.map((point) => point.canopyTemp),
          },
          {
            label: t("outdoorSeries"),
            color: blue,
            values: history.map((point) => point.outsideTemp),
            dash: [4, 4],
          },
        ],
      };
    }

    function drawChart(history, targets, chartMode) {
      const canvas = byId("trendCanvas");
      const empty = byId("chartEmpty");
      const legend = byId("chartLegend");
      const container = canvas.parentElement;
      const rect = container.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;

      const context = canvas.getContext("2d");
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      context.clearRect(0, 0, rect.width, rect.height);

      const config = chartConfiguration(history, targets, chartMode);
      canvas.setAttribute("aria-label", config.label);
      legend.replaceChildren();
      config.series.forEach((series) => {
        const item = document.createElement("span");
        const swatch = document.createElement("i");
        swatch.style.setProperty("--legend-color", series.color);
        item.append(swatch, document.createTextNode(series.label));
        legend.append(item);
      });

      if (history.length < 2) {
        empty.classList.remove("hidden");
        return;
      }
      empty.classList.add("hidden");

      const styles = getComputedStyle(document.documentElement);
      const textColor = styles.getPropertyValue("--muted").trim();
      const gridColor = "rgba(177, 216, 198, 0.10)";
      const plot = {
        left: 38,
        right: rect.width - 10,
        top: 10,
        bottom: rect.height - 24,
      };
      const plotWidth = Math.max(1, plot.right - plot.left);
      const plotHeight = Math.max(1, plot.bottom - plot.top);
      const allValues = config.series.flatMap((series) => series.values).filter(Number.isFinite);
      let minValue = Math.min(...allValues);
      let maxValue = Math.max(...allValues);
      const observedSpan = Math.max(maxValue - minValue, config.minSpan);
      const center = (minValue + maxValue) / 2;
      minValue = center - observedSpan * 0.58;
      maxValue = center + observedSpan * 0.58;

      context.font = "9px ui-sans-serif, system-ui, sans-serif";
      context.textBaseline = "middle";
      context.lineWidth = 1;

      for (let tick = 0; tick <= 3; tick += 1) {
        const ratio = tick / 3;
        const y = plot.top + plotHeight * ratio;
        const value = maxValue - (maxValue - minValue) * ratio;
        context.beginPath();
        context.strokeStyle = gridColor;
        context.moveTo(plot.left, y);
        context.lineTo(plot.right, y);
        context.stroke();
        context.fillStyle = textColor;
        context.textAlign = "right";
        const digits = chartMode === "co2" ? 0 : 1;
        context.fillText(`${value.toFixed(digits)}${config.unit}`, plot.left - 7, y);
      }

      const xTickIndexes = [
        0,
        Math.floor((history.length - 1) / 3),
        Math.floor(((history.length - 1) * 2) / 3),
        history.length - 1,
      ];
      xTickIndexes.forEach((pointIndex, tickIndex) => {
        const x = plot.left + (pointIndex / Math.max(history.length - 1, 1)) * plotWidth;
        context.fillStyle = textColor;
        context.textAlign =
          tickIndex === 0 ? "left" : tickIndex === xTickIndexes.length - 1 ? "right" : "center";
        context.fillText(formatHour(history[pointIndex].hour), x, rect.height - 9);
      });

      config.series.forEach((series) => {
        context.beginPath();
        context.strokeStyle = series.color;
        context.lineWidth = series.dash ? 1.35 : 1.8;
        context.lineJoin = "round";
        context.lineCap = "round";
        context.setLineDash(series.dash || []);
        series.values.forEach((value, index) => {
          const x = plot.left + (index / Math.max(series.values.length - 1, 1)) * plotWidth;
          const y = plot.bottom - ((value - minValue) / (maxValue - minValue)) * plotHeight;
          if (index === 0) context.moveTo(x, y);
          else context.lineTo(x, y);
        });
        context.stroke();
        context.setLineDash([]);

        if (!series.dash) {
          const lastValue = series.values[series.values.length - 1];
          const x = plot.right;
          const y = plot.bottom - ((lastValue - minValue) / (maxValue - minValue)) * plotHeight;
          context.beginPath();
          context.fillStyle = series.color;
          context.arc(x, y, 3, 0, Math.PI * 2);
          context.fill();
        }
      });
    }

    return drawChart;
  }
  root.GreenlightCharts = { createRenderer };
})(window);
