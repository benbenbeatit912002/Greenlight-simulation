(function (globalScope) {
  "use strict";

  const STEP_MINUTES = 15;
  const BROWSER_MODEL_VERSION = "2026.07";
  const BROWSER_WEATHER_VERSION = "synthetic-weather-2026.07";
  const COST_ASSUMPTIONS = Object.freeze({
    id: "browser-fixed-eur-2026-07",
    currency: "EUR",
    heatEurPerKwh: 0.09,
    lampEurPerKwh: 0.3,
    co2EurPerKg: 0.3,
    liveTariff: false,
  });
  const TARGET_LIMITS = Object.freeze({
    dayTemp: Object.freeze([16, 30]),
    nightTemp: Object.freeze([12, 24]),
    co2: Object.freeze([400, 1500]),
    maxRh: Object.freeze([60, 90]),
  });
  const CONTROL_NAMES = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"];

  const SCENARIOS = {
    spring: {
      label: "阿姆斯特丹・春季晴天",
      meanTemp: 9.5,
      tempAmplitude: 5.8,
      radiationPeak: 610,
      rhBase: 77,
      windBase: 2.8,
      dayLength: 11.3,
      cloud: 0.12,
    },
    cloudy: {
      label: "多雲寒冷",
      meanTemp: 5.5,
      tempAmplitude: 3.2,
      radiationPeak: 270,
      rhBase: 86,
      windBase: 4.2,
      dayLength: 10.5,
      cloud: 0.68,
    },
    summer: {
      label: "夏季炎熱",
      meanTemp: 20.5,
      tempAmplitude: 7.4,
      radiationPeak: 790,
      rhBase: 64,
      windBase: 2.1,
      dayLength: 16.1,
      cloud: 0.08,
    },
    winter: {
      label: "冬季低溫",
      meanTemp: 1.5,
      tempAmplitude: 3.8,
      radiationPeak: 225,
      rhBase: 88,
      windBase: 3.6,
      dayLength: 8.1,
      cloud: 0.45,
    },
  };

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function approach(current, target, maxDelta) {
    return current + clamp(target - current, -maxDelta, maxDelta);
  }

  function round(value, digits = 2) {
    const factor = 10 ** digits;
    return Math.round(value * factor) / factor;
  }

  function circularHourDistance(hour, center) {
    const raw = Math.abs(hour - center) % 24;
    return Math.min(raw, 24 - raw);
  }

  class GreenhouseModel {
    constructor(options = {}) {
      const scenario = options.scenario || "spring";
      const mode = options.mode || "auto";
      if (!Object.prototype.hasOwnProperty.call(SCENARIOS, scenario)) {
        throw new Error(`Unknown weather scenario: ${scenario}`);
      }
      if (mode !== "auto" && mode !== "manual") {
        throw new Error(`Unknown control mode: ${mode}`);
      }
      this.scenarioKey = scenario;
      this.mode = mode;
      this.targets = {
        dayTemp: 21.5,
        nightTemp: 17.5,
        co2: 900,
        maxRh: 82,
      };
      this.reset();
    }

    reset() {
      this.elapsedMinutes = 0;
      this.startDay = 59;
      this.startHour = 6;
      this.controls = {
        uBoil: 0.38,
        uCO2: 0.18,
        uThScr: 0.46,
        uVent: 0.05,
        uLamp: 0.34,
        uBlScr: 0,
      };
      this.state = {
        airTemp: 19.2,
        canopyTemp: 18.9,
        canopy24hTemp: 19.1,
        pipeTemp: 39,
        rh: 73,
        co2: 690,
        fruitDryMass: 55.34,
        tempSum: 3097.8,
        leafAreaIndex: 2.35,
        cumulativeHeatKwh: 0,
        cumulativeLampKwh: 0,
        cumulativeCo2Kg: 0,
      };
      this.history = [];
      this._recordHistory();
      return this.snapshot();
    }

    setScenario(key) {
      if (!Object.prototype.hasOwnProperty.call(SCENARIOS, key)) {
        throw new Error(`Unknown weather scenario: ${key}`);
      }
      this.scenarioKey = key;
      return this.snapshot();
    }

    setMode(mode) {
      if (mode !== "auto" && mode !== "manual") {
        throw new Error(`Unknown control mode: ${mode}`);
      }
      this.mode = mode;
      return this.snapshot();
    }

    setControl(name, value) {
      if (!CONTROL_NAMES.includes(name)) {
        throw new Error(`Unknown GreenLight control: ${name}`);
      }
      const numericValue = Number(value);
      if (!Number.isFinite(numericValue)) {
        throw new TypeError(`Control ${name} must be a finite number`);
      }
      this.controls[name] = clamp(numericValue, 0, 1);
      return this.controls[name];
    }

    setTarget(name, value) {
      if (!Object.prototype.hasOwnProperty.call(this.targets, name)) {
        throw new Error(`Unknown target: ${name}`);
      }
      const numericValue = Number(value);
      const [minimum, maximum] = TARGET_LIMITS[name];
      if (!Number.isFinite(numericValue)) {
        throw new TypeError(`Target ${name} must be a finite number`);
      }
      if (numericValue < minimum || numericValue > maximum) {
        throw new RangeError(`Target ${name} must be between ${minimum} and ${maximum}`);
      }
      this.targets[name] = numericValue;
      return this.targets[name];
    }

    getClock() {
      const totalMinutes = this.startHour * 60 + this.elapsedMinutes;
      const dayOffset = Math.floor(totalMinutes / 1440);
      const minuteOfDay = ((totalMinutes % 1440) + 1440) % 1440;
      return {
        dayOfYear: this.startDay + dayOffset,
        hour: minuteOfDay / 60,
        minuteOfDay,
        dayOffset,
      };
    }

    getWeather(clock = this.getClock()) {
      const scenario = SCENARIOS[this.scenarioKey];
      const sunrise = 12 - scenario.dayLength / 2;
      const sunset = 12 + scenario.dayLength / 2;
      const solarProgress = clamp((clock.hour - sunrise) / Math.max(scenario.dayLength, 0.1), 0, 1);
      const sunShape =
        clock.hour >= sunrise && clock.hour <= sunset ? Math.sin(Math.PI * solarProgress) : 0;
      const passingClouds =
        1 - scenario.cloud * (0.76 + 0.18 * Math.sin((clock.hour + clock.dayOffset * 1.7) * 1.91));
      const radiation = Math.max(0, scenario.radiationPeak * sunShape * passingClouds);
      const dailyPhase = ((clock.hour - 8) / 24) * Math.PI * 2;
      const temperature = scenario.meanTemp + scenario.tempAmplitude * Math.sin(dailyPhase);
      const rh = clamp(
        scenario.rhBase - 16 * sunShape + 3 * Math.cos(clock.hour * 0.7 + clock.dayOffset),
        35,
        98,
      );
      const wind = clamp(
        scenario.windBase +
          0.7 * Math.sin(clock.hour * 0.83) +
          0.35 * Math.cos(clock.dayOffset * 1.3),
        0.4,
        8.5,
      );

      return {
        temperature,
        rh,
        radiation,
        wind,
        co2: 420,
        sunrise,
        sunset,
        daylight: sunShape,
        cloud: scenario.cloud,
      };
    }

    _runController(weather, clock) {
      const isDay = weather.daylight > 0.06;
      const tempTarget = isDay ? this.targets.dayTemp : this.targets.nightTemp;
      const tempError = tempTarget - this.state.airTemp;
      const rhExcess = this.state.rh - this.targets.maxRh;
      const co2Error = this.targets.co2 - this.state.co2;
      const cheapSolarLight = weather.radiation < 360 && clock.hour < 20;

      const desired = {
        uBoil: clamp(tempError * 0.15 + (isDay ? 0.1 : 0.04), 0, 1),
        uCO2: isDay && this.controls.uVent < 0.32 ? clamp(co2Error / 720, 0, 0.82) : 0,
        uThScr: !isDay
          ? clamp(0.72 + Math.max(0, 9 - weather.temperature) * 0.025, 0, 1)
          : clamp((80 - this.state.rh) / 100, 0, 0.24),
        uVent: clamp(
          Math.max(0, this.state.airTemp - tempTarget) * 0.18 + Math.max(0, rhExcess) * 0.04,
          0,
          1,
        ),
        uLamp: isDay && cheapSolarLight ? clamp((390 - weather.radiation) / 390, 0, 0.82) : 0,
        uBlScr:
          weather.radiation > 650 && this.state.airTemp > tempTarget + 1.5
            ? clamp((weather.radiation - 620) / 250, 0, 0.78)
            : 0,
      };

      CONTROL_NAMES.forEach((name) => {
        this.controls[name] = approach(this.controls[name], desired[name], 0.1);
      });
    }

    step(stepCount = 1) {
      const numericCount = Number(stepCount);
      if (!Number.isInteger(numericCount) || numericCount < 1 || numericCount > 192) {
        throw new RangeError("Step count must be an integer between 1 and 192");
      }
      for (let index = 0; index < numericCount; index += 1) {
        this._stepOnce();
      }
      return this.snapshot();
    }

    _stepOnce() {
      const dt = STEP_MINUTES / 60;
      const clock = this.getClock();
      const weather = this.getWeather(clock);

      if (this.mode === "auto") {
        this._runController(weather, clock);
      }

      const u = this.controls;
      const transmission = clamp(0.82 - u.uThScr * 0.22 - u.uBlScr * 0.68, 0.08, 0.82);
      const insideRadiation = weather.radiation * transmission + u.uLamp * 165;
      const ventExchange =
        (0.06 + u.uVent * 1.85) * (0.78 + weather.wind * 0.09) * (1 - u.uThScr * 0.34);
      const pipeTarget = 22 + 58 * u.uBoil;

      this.state.pipeTemp += (pipeTarget - this.state.pipeTemp) * (dt / 1.15);

      const pipeHeat = Math.max(0, this.state.pipeTemp - this.state.airTemp) * 0.085;
      const solarHeat = insideRadiation * 0.0051;
      const lampHeat = u.uLamp * 0.9;
      const envelopeLoss =
        (this.state.airTemp - weather.temperature) *
        (0.105 + ventExchange * 0.55) *
        (1 - u.uThScr * 0.24);
      const cropCooling = clamp(insideRadiation / 720, 0, 1) * this.state.leafAreaIndex * 0.16;
      const airTempRate = pipeHeat + solarHeat + lampHeat - envelopeLoss - cropCooling;
      this.state.airTemp = clamp(this.state.airTemp + airTempRate * dt, -5, 48);

      const canopyTarget = this.state.airTemp + insideRadiation * 0.0024 - cropCooling * 0.28;
      this.state.canopyTemp += (canopyTarget - this.state.canopyTemp) * (dt / 0.38);
      this.state.canopy24hTemp += (this.state.canopyTemp - this.state.canopy24hTemp) * (dt / 24);

      const lightFactor = insideRadiation / (insideRadiation + 170);
      const co2Factor = this.state.co2 / (this.state.co2 + 420);
      const tempFactor = Math.exp(-1 * ((this.state.canopyTemp - 22) / 10) ** 2);
      const photosynthesis =
        lightFactor * co2Factor * tempFactor * clamp(this.state.leafAreaIndex / 2.5, 0.4, 1.3);
      const transpiration = lightFactor * tempFactor * (0.85 + this.state.leafAreaIndex * 0.14);

      const rhExchange = (weather.rh - this.state.rh) * (0.035 + ventExchange * 0.48);
      const rhGeneration = transpiration * 5.2;
      const heatingDrying = Math.max(0, airTempRate) * 1.25 + u.uBoil * 0.75;
      this.state.rh = clamp(
        this.state.rh + (rhExchange + rhGeneration - heatingDrying) * dt,
        28,
        100,
      );

      const co2Dosing = u.uCO2 * 1180;
      const co2Exchange = (weather.co2 - this.state.co2) * (0.055 + ventExchange * 1.25);
      const cropUptake = photosynthesis * 132;
      this.state.co2 = clamp(
        this.state.co2 + (co2Dosing + co2Exchange - cropUptake) * dt,
        250,
        1800,
      );

      const growthRate = 0.19 * photosynthesis;
      this.state.fruitDryMass += growthRate * dt;
      this.state.tempSum += (Math.max(0, this.state.canopyTemp) * dt) / 24;
      this.state.leafAreaIndex = clamp(
        this.state.leafAreaIndex + photosynthesis * 0.00028 * dt,
        0.4,
        4.6,
      );

      this.state.cumulativeHeatKwh += u.uBoil * 0.13 * dt;
      this.state.cumulativeLampKwh += u.uLamp * 0.116 * dt;
      this.state.cumulativeCo2Kg += u.uCO2 * 0.018 * dt;

      this.elapsedMinutes += STEP_MINUTES;
      this._recordHistory();
    }

    _recordHistory() {
      const clock = this.getClock();
      const weather = this.getWeather(clock);
      this.history.push({
        elapsedMinutes: this.elapsedMinutes,
        hour: clock.hour,
        airTemp: this.state.airTemp,
        canopyTemp: this.state.canopyTemp,
        outsideTemp: weather.temperature,
        outsideRh: weather.rh,
        rh: this.state.rh,
        co2: this.state.co2,
      });
      if (this.history.length > 97) {
        this.history.shift();
      }
    }

    _violations() {
      const violations = [];
      if (this.state.airTemp < 15) violations.push("室溫低於 15°C");
      if (this.state.airTemp > 34) violations.push("室溫高於 34°C");
      if (this.state.rh < 50) violations.push("相對濕度低於 50%");
      if (this.state.rh > 85) violations.push("相對濕度高於 85%");
      if (this.state.co2 < 300) violations.push("CO₂ 低於 300 ppm");
      if (this.state.co2 > 1600) violations.push("CO₂ 高於 1600 ppm");
      return violations;
    }

    snapshot() {
      const clock = this.getClock();
      const weather = this.getWeather(clock);
      const cost =
        this.state.cumulativeHeatKwh * COST_ASSUMPTIONS.heatEurPerKwh +
        this.state.cumulativeLampKwh * COST_ASSUMPTIONS.lampEurPerKwh +
        this.state.cumulativeCo2Kg * COST_ASSUMPTIONS.co2EurPerKg;

      return {
        engine: "browser-approximation",
        modelVersion: BROWSER_MODEL_VERSION,
        costModelId: COST_ASSUMPTIONS.id,
        weatherFingerprint: `${BROWSER_WEATHER_VERSION}:${this.scenarioKey}`,
        modelStep: Math.floor(this.elapsedMinutes / STEP_MINUTES),
        elapsedMinutes: this.elapsedMinutes,
        dayOfYear: clock.dayOfYear,
        hour: clock.hour,
        minuteOfDay: clock.minuteOfDay,
        mode: this.mode,
        scenario: this.scenarioKey,
        scenarioLabel: SCENARIOS[this.scenarioKey].label,
        indoor: {
          airTemp: round(this.state.airTemp),
          canopyTemp: round(this.state.canopyTemp),
          canopy24hTemp: round(this.state.canopy24hTemp),
          pipeTemp: round(this.state.pipeTemp),
          rh: round(this.state.rh),
          co2: round(this.state.co2, 0),
          insideRadiation: round(
            weather.radiation *
              clamp(0.82 - this.controls.uThScr * 0.22 - this.controls.uBlScr * 0.68, 0.08, 0.82) +
              this.controls.uLamp * 165,
            0,
          ),
        },
        outdoor: {
          temperature: round(weather.temperature),
          rh: round(weather.rh),
          radiation: round(weather.radiation, 0),
          wind: round(weather.wind),
          daylight: round(weather.daylight, 3),
          cloud: weather.cloud,
          sunrise: weather.sunrise,
          sunset: weather.sunset,
        },
        crop: {
          fruitDryMass: round(this.state.fruitDryMass),
          tempSum: round(this.state.tempSum, 1),
          leafAreaIndex: round(this.state.leafAreaIndex),
        },
        controls: { ...this.controls },
        targets: { ...this.targets },
        resources: {
          heatKwh: round(this.state.cumulativeHeatKwh, 3),
          lampKwh: round(this.state.cumulativeLampKwh, 3),
          co2Kg: round(this.state.cumulativeCo2Kg, 3),
          costEur: round(cost, 3),
        },
        economics: { ...COST_ASSUMPTIONS },
        violations: this._violations(),
        history: this.history.map((point) => ({ ...point })),
      };
    }
  }

  const api = {
    GreenhouseModel,
    SCENARIOS,
    CONTROL_NAMES,
    STEP_MINUTES,
    BROWSER_MODEL_VERSION,
    BROWSER_WEATHER_VERSION,
    COST_ASSUMPTIONS,
    TARGET_LIMITS,
    clamp,
    circularHourDistance,
  };

  globalScope.GreenhouseSimulator = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
