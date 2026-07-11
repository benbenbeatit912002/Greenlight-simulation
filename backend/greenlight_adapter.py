from __future__ import annotations

import importlib.metadata
import math
import os
import sys
from pathlib import Path
from typing import Any, Mapping


CONTROL_NAMES = (
    "uBoil",
    "uCO2",
    "uThScr",
    "uVent",
    "uLamp",
    "uBlScr",
)

DEFAULT_TARGETS = {
    "dayTemp": 21.5,
    "nightTemp": 17.5,
    "co2": 900.0,
    "maxRh": 82.0,
}

# These presets select real Amsterdam weather windows. Their labels deliberately
# say "recorded" rather than promising a synthetic, constant weather condition.
SCENARIOS = {
    "spring": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 59,
        "label": "阿姆斯特丹 2010・春季實測",
    },
    "cloudy": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 305,
        "label": "阿姆斯特丹 2010・晚秋實測",
    },
    "summer": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 172,
        "label": "阿姆斯特丹 2010・夏季實測",
    },
    "winter": {
        "location": "Amsterdam",
        "growth_year": 2010,
        "start_day": 1,
        "label": "阿姆斯特丹 2010・冬季實測",
    },
}

RULE_BASED_DEFAULTS = {
    "lamps_on": 0,
    "lamps_off": 18,
    "lamps_day_start": -1,
    "lamps_day_stop": 366,
    "lamps_off_sun": 400,
    "lamp_rad_sum_limit": 10,
    "heat_correction": 0,
    "heat_deadzone": 5,
    "vent_heat_Pband": 4,
    "mech_dehumid_Pband": 2,
    "vent_rh_Pband": 5,
    "t_vent_off": 1,
    "vent_cold_Pband": -1,
    "thScrSpDay": 5,
    "thScrSpNight": 10,
    "thScrPband": -1,
    "thScrDeadZone": 4,
    "thScrRh": -2,
    "thScrRhPband": 2,
    "lampExtraHeat": 2,
    "blScrExtraRh": 100,
    "tHeatBand": -1,
    "co2Band": -100,
    "useBlScr": 1,
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, float(value)))


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def default_source_path() -> Path:
    configured = os.environ.get("GREENLIGHT_GYM_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "GreenLight-Gym2-practice" / "GreenLight-Gym2"


class GreenLightGymAdapter:
    """Stateful adapter around the local 28-state GreenLight-Gym2 model."""

    kind = "greenlight-gym2"
    scientific = True
    step_minutes = 15

    def __init__(self, source_path: str | Path | None = None) -> None:
        self.source_path = Path(source_path or default_source_path()).resolve()
        if not (self.source_path / "gl_gym" / "__init__.py").is_file():
            raise RuntimeError(f"GL-Gym2 source not found at {self.source_path}")

        source_text = str(self.source_path)
        if source_text not in sys.path:
            sys.path.insert(0, source_text)
        # Import sibling source read-only; do not create __pycache__ files in
        # either practice repository.
        sys.dont_write_bytecode = True

        try:
            import gymnasium as gym
            import numpy as np
            import gl_gym  # noqa: F401 - importing registers the environment
            from gl_gym.components.rule_based import RuleBasedController
            from gl_gym.core.types import StepContext
        except Exception as exc:  # pragma: no cover - exact import depends on host
            raise RuntimeError(
                "GL-Gym2 dependencies are unavailable. Install the optional "
                "greenlight dependency group before starting the scientific model."
            ) from exc

        self._gym = gym
        self._np = np
        self._rule_based_controller_class = RuleBasedController
        self._step_context_class = StepContext

        try:
            self.package_version = importlib.metadata.version("gl-gym")
        except importlib.metadata.PackageNotFoundError:
            self.package_version = "local-source"

        try:
            self.env = gym.make(
                "gl_gym/GreenLightTomato-v0",
                normalize_actions=False,
                weather_data_dir=self.source_path / "gl_gym" / "data" / "weather",
            )
        except Exception as exc:  # pragma: no cover - needs optional native deps
            raise RuntimeError(f"GL-Gym2 could not be initialized: {exc}") from exc

        self.core = self.env.unwrapped
        self.mode = "auto"
        self.targets = dict(DEFAULT_TARGETS)
        self.scenario_key = "spring"
        self.history: list[dict[str, float]] = []
        self.resources = {
            "heatKwh": 0.0,
            "lampKwh": 0.0,
            "co2Kg": 0.0,
            "costEur": 0.0,
        }
        self.terminated = False
        self.truncated = False
        self.last_reward = 0.0
        self.last_info: dict[str, Any] = {}
        self.obs: Mapping[str, Any] = {}
        self.reset({})

    def metadata(self) -> dict[str, Any]:
        return {
            "active": self.kind,
            "scientific": True,
            "model": "GreenLight 2 / GreenLightTomato-v0",
            "version": self.package_version,
            "stateCount": 28,
            "controlCount": 6,
            "stepMinutes": self.step_minutes,
            "weather": "Amsterdam recorded weather",
            "sourcePath": str(self.source_path),
        }

    def close(self) -> None:
        self.env.close()

    def reset(self, request: Mapping[str, Any] | None = None) -> dict[str, Any]:
        request = request or {}
        self.mode = str(request.get("mode", self.mode))
        if self.mode not in {"auto", "manual"}:
            raise ValueError("mode must be 'auto' or 'manual'")

        self._apply_targets(request.get("targets"))
        scenario_key = str(request.get("scenario", self.scenario_key))
        if scenario_key not in SCENARIOS:
            raise ValueError(f"unknown scenario: {scenario_key}")
        self.scenario_key = scenario_key
        scenario = SCENARIOS[scenario_key]
        seed = int(request.get("seed", 42))

        self.obs, _ = self.env.reset(
            seed=seed,
            options={
                "scenario": {
                    "location": scenario["location"],
                    "growth_year": scenario["growth_year"],
                    "start_day": scenario["start_day"],
                }
            },
        )
        self.resources = {
            "heatKwh": 0.0,
            "lampKwh": 0.0,
            "co2Kg": 0.0,
            "costEur": 0.0,
        }
        self.history = []
        self.terminated = False
        self.truncated = False
        self.last_reward = 0.0
        self.last_info = {}
        self._record_history()
        return self.snapshot()

    def step(self, request: Mapping[str, Any]) -> dict[str, Any]:
        steps = int(request.get("steps", 1))
        if not 1 <= steps <= 192:
            raise ValueError("steps must be between 1 and 192")

        mode = str(request.get("mode", self.mode))
        if mode not in {"auto", "manual"}:
            raise ValueError("mode must be 'auto' or 'manual'")
        self.mode = mode
        self._apply_targets(request.get("targets"))

        manual_controls = request.get("controls")
        for _ in range(steps):
            if self.terminated or self.truncated:
                break

            if self.mode == "auto":
                action = self._controller_action()
            else:
                action = self._manual_action(manual_controls)

            self.obs, reward, terminated, truncated, info = self.env.step(action)
            self.terminated = bool(terminated)
            self.truncated = bool(truncated)
            self.last_reward = float(reward)
            self.last_info = dict(info)
            self._accumulate_resources(action, info)
            self._record_history()

        return self.snapshot()

    def _apply_targets(self, targets: Any) -> None:
        if targets is None:
            return
        if not isinstance(targets, Mapping):
            raise ValueError("targets must be an object")
        for name in DEFAULT_TARGETS:
            if name in targets:
                self.targets[name] = float(targets[name])

    def _manual_action(self, controls: Any):
        if not isinstance(controls, Mapping):
            raise ValueError("manual mode requires a controls object")
        missing = [name for name in CONTROL_NAMES if name not in controls]
        if missing:
            raise ValueError(f"missing controls: {', '.join(missing)}")
        values = [_clamp(float(controls[name]), 0.0, 1.0) for name in CONTROL_NAMES]
        return self._np.asarray(values, dtype=self._np.float32)

    def _controller_action(self):
        params = {
            **RULE_BASED_DEFAULTS,
            "temp_setpoint_day": self.targets["dayTemp"],
            "temp_setpoint_night": self.targets["nightTemp"],
            "co2_day": self.targets["co2"],
            "rh_max": self.targets["maxRh"],
            "rhMax": self.targets["maxRh"],
        }
        controller = self._rule_based_controller_class(**params)
        context = self._step_context_class(
            t=self.core.timestep,
            dt=self.core.dt,
            Np=self.core.Np,
            x_prev=self.core.x_prev,
            x=self.core.x,
            u=self.core.u,
            p=self.core.p,
            d=self.core.weather_data,
            hour_of_day=self.core.hour_of_day,
            day_of_year=self.core.day_of_year,
        )
        action = controller.predict(context)
        return self._np.clip(
            self._np.asarray(action, dtype=self._np.float32),
            0.0,
            1.0,
        )

    def _accumulate_resources(self, action, info: Mapping[str, Any]) -> None:
        p = self.core.p
        dt = float(self.core.dt)
        heat_kwh = float(action[0]) * float(p[108]) / float(p[46]) * dt / 3600 * 1e-3
        lamp_kwh = float(action[4]) * float(p[172]) * dt / 3600 * 1e-3
        co2_kg = float(action[1]) * float(p[109]) / float(p[46]) * dt * 1e-6
        step_cost = float(info.get("variable_costs", 0.0))
        self.resources["heatKwh"] += heat_kwh
        self.resources["lampKwh"] += lamp_kwh
        self.resources["co2Kg"] += co2_kg
        self.resources["costEur"] += step_cost

    def _read_values(self) -> dict[str, Any]:
        climate = self._np.asarray(
            self.obs["IndoorClimateObservations"], dtype=self._np.float64
        )
        weather = self._np.asarray(
            self.obs["WeatherObservations"], dtype=self._np.float64
        )
        crop = self._np.asarray(
            self.obs["BasicCropObservations"], dtype=self._np.float64
        )
        controls = self._np.asarray(self.core.u, dtype=self._np.float64)
        leaf_area_index = float(self.core.x[23]) * float(self.core.p[142])
        inside_radiation = float(weather[0]) * _clamp(
            0.82 - controls[2] * 0.22 - controls[5] * 0.68,
            0.08,
            0.82,
        ) + controls[4] * 165.0
        return {
            "climate": climate,
            "weather": weather,
            "crop": crop,
            "controls": controls,
            "canopyTemp": float(self.core.x[4]),
            "leafAreaIndex": leaf_area_index,
            "insideRadiation": inside_radiation,
        }

    def _record_history(self) -> None:
        values = self._read_values()
        climate = values["climate"]
        weather = values["weather"]
        self.history.append(
            {
                "elapsedMinutes": float(self.core.timestep * self.step_minutes),
                "hour": float(self.core.hour_of_day),
                "airTemp": float(climate[1]),
                "canopyTemp": float(values["canopyTemp"]),
                "outsideTemp": float(weather[1]),
                "outsideRh": float(weather[2]),
                "rh": float(climate[2]),
                "co2": float(climate[0]),
            }
        )
        if len(self.history) > 97:
            self.history.pop(0)

    def snapshot(self) -> dict[str, Any]:
        values = self._read_values()
        climate = values["climate"]
        weather = values["weather"]
        crop = values["crop"]
        controls = values["controls"]
        air_temp = float(climate[1])
        rh = float(climate[2])
        co2 = float(climate[0])

        violations: list[str] = []
        if air_temp < 15:
            violations.append("室溫低於 15°C")
        if air_temp > 34:
            violations.append("室溫高於 34°C")
        if rh < 50:
            violations.append("相對濕度低於 50%")
        if rh > 85:
            violations.append("相對濕度高於 85%")
        if co2 < 300:
            violations.append("CO₂ 低於 300 ppm")
        if co2 > 1600:
            violations.append("CO₂ 高於 1600 ppm")

        hour = float(self.core.hour_of_day) % 24
        minute_of_day = int(round(hour * 60)) % 1440
        daylight = 1.0 if float(weather[0]) > 0 else 0.0
        sunrise, sunset = self._sun_window()
        scenario = SCENARIOS[self.scenario_key]

        snapshot = {
            "modelStep": int(self.core.timestep),
            "elapsedMinutes": int(self.core.timestep * self.step_minutes),
            "dayOfYear": int(math.floor(float(self.core.day_of_year))),
            "hour": hour,
            "minuteOfDay": minute_of_day,
            "mode": self.mode,
            "scenario": self.scenario_key,
            "scenarioLabel": scenario["label"],
            "engine": self.kind,
            "indoor": {
                "airTemp": _round(climate[1]),
                "canopyTemp": _round(values["canopyTemp"]),
                "canopy24hTemp": _round(crop[0]),
                "pipeTemp": _round(climate[3]),
                "rh": _round(climate[2]),
                "co2": _round(climate[0], 0),
                "insideRadiation": _round(values["insideRadiation"], 0),
            },
            "outdoor": {
                "temperature": _round(weather[1]),
                "rh": _round(weather[2]),
                "radiation": _round(weather[0], 0),
                "wind": _round(weather[4]),
                "co2": _round(weather[3], 0),
                "daylight": daylight,
                "cloud": 0.0,
                "sunrise": sunrise,
                "sunset": sunset,
            },
            "crop": {
                "fruitDryMass": _round(float(crop[1]) / 1000.0),
                "tempSum": _round(crop[2], 1),
                "leafAreaIndex": _round(values["leafAreaIndex"]),
            },
            "controls": {
                name: _round(controls[index], 4)
                for index, name in enumerate(CONTROL_NAMES)
            },
            "targets": {name: float(value) for name, value in self.targets.items()},
            "resources": {
                name: _round(value, 3) for name, value in self.resources.items()
            },
            "violations": violations,
            "episode": {
                "terminated": self.terminated,
                "truncated": self.truncated,
            },
            "reward": _round(self.last_reward, 6),
            "history": [
                {name: _round(value, 4) for name, value in point.items()}
                for point in self.history
            ],
        }
        return snapshot

    def _sun_window(self) -> tuple[float, float]:
        steps_per_day = int(24 * 60 / self.step_minutes)
        day_index = int(self.core.timestep // steps_per_day)
        start = day_index * steps_per_day
        radiation = self._np.asarray(
            self.core.weather_data[start : start + steps_per_day, 0],
            dtype=self._np.float64,
        )
        daylight_indices = self._np.flatnonzero(radiation > 0)
        if daylight_indices.size == 0:
            return 6.0, 18.0
        sunrise = float(daylight_indices[0]) * self.step_minutes / 60
        sunset = float(daylight_indices[-1] + 1) * self.step_minutes / 60
        return sunrise, sunset
