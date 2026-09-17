from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

from backend.greenhouse_config import (
    apply_initial_state,
    apply_parameters,
    field_metadata,
    initial_values,
    parameter_values,
    validate_config,
)
from backend.model_defaults import ADAPTER_VERSION as ADAPTER_VERSION
from backend.model_defaults import CONTROL_NAMES as CONTROL_NAMES
from backend.model_defaults import DEFAULT_TARGETS as DEFAULT_TARGETS
from backend.model_defaults import RULE_BASED_DEFAULTS as RULE_BASED_DEFAULTS
from backend.model_defaults import SCENARIOS as SCENARIOS
from backend.provenance import _array_fingerprint as _array_fingerprint
from backend.provenance import _git_revision as _git_revision
from backend.provenance import _loaded_source_fingerprint as _loaded_source_fingerprint
from backend.run_window import STEP_SECONDS, source_datetime, validate_window
from backend.weather_conversion import prepare_uploaded_weather
from backend.weather_source import single_year_loader


class InMemoryWeatherRepository:
    """Weather repository for a validated upload; it never reads or writes a file."""

    def __init__(self, weather_data: Any) -> None:
        self.weather_data = weather_data.copy()

    def load(self, **_: Any) -> Any:
        return self.weather_data.copy()


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, float(value)))


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def default_source_path() -> Path:
    configured = os.environ.get("GREENLIGHT_GYM_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    raise RuntimeError("Set GREENLIGHT_GYM_PATH to a compatible GreenLight-Gym2 source checkout.")


class PreservedRunResetError(RuntimeError):
    """A candidate failed while the previous environment remained untouched."""


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
            import casadi as ca
            import gl_gym  # noqa: F401 - importing registers the environment
            import gymnasium as gym
            import numpy as np
            from gl_gym.components.rule_based import RuleBasedController
            from gl_gym.components.weather import WeatherRepository
            from gl_gym.core.types import RewardContext, StepContext
            from gl_gym.environments.utils import (
                co2dens2ppm,
                co2ppm2dens,
                computeisDay,
                dailLightSum,
                load_weather_data,
                rh2vaporDens,
                satVp,
                soilTempNl,
                vaporDens2pres,
            )
            from gl_gym.models.GreenLight.aux_states import update as update_aux
        except Exception as exc:  # pragma: no cover - exact import depends on host
            raise RuntimeError(
                "GL-Gym2 dependencies are unavailable. Install the optional "
                "greenlight dependency group before starting the scientific model."
            ) from exc

        self._gym = gym
        self._np = np
        self._rule_based_controller_class = RuleBasedController
        self._step_context_class = StepContext
        self._reward_context_class = RewardContext
        self._sat_vp = satVp
        self._co2_density_to_ppm = co2dens2ppm
        self._compute_is_day = computeisDay
        self._co2_ppm_to_density = co2ppm2dens
        self._daily_light_sum = dailLightSum
        self._rh_to_vapor_density = rh2vaporDens
        self._soil_temperature = soilTempNl
        self._vapor_density_to_pressure = vaporDens2pres

        try:
            self.package_version = importlib.metadata.version("gl-gym")
        except importlib.metadata.PackageNotFoundError:
            self.package_version = "local-source"
        self.git_revision = _git_revision(self.source_path)

        self._weather_data_dir = self.source_path / "gl_gym" / "data" / "weather"
        self._default_weather_repository = WeatherRepository(
            self._weather_data_dir,
            single_year_loader(load_weather_data),
        )
        try:
            self.env = self._make_environment(
                self._default_weather_repository,
                season_length=60,
                pred_horizon=0.5,
            )
        except Exception as exc:  # pragma: no cover - needs optional native deps
            raise RuntimeError(f"GL-Gym2 could not be initialized: {exc}") from exc

        self.core = self.env.unwrapped
        # Reuse precisely the auxiliary equations used by the upstream ODE.
        x, u, d, p = (
            ca.SX.sym(name, size) for name, size in (("x", 28), ("u", 6), ("d", 10), ("p", 208))
        )
        aux = update_aux(x, u, d, p)
        self._aux_function = ca.Function(
            "simulator_outputs", [x, u, d, p], [aux[[31, 42, 43, 191, 220, 37, 222]]]
        )
        self.source_fingerprint = _loaded_source_fingerprint(self.source_path)
        source_identity = (
            f"git.{self.git_revision}"
            if self.git_revision
            else f"sha256.{self.source_fingerprint or 'unversioned'}"
        )
        package_identity = (
            "source-checkout" if self.package_version == "local-source" else self.package_version
        )
        self.parameter_fingerprint = _array_fingerprint(
            self._np,
            self.core.parameter_provider.base_p,
        )
        self._model_identifier_prefix = (
            f"gl-gym2@{package_identity}+{source_identity}.adapter.{ADAPTER_VERSION}"
        )
        self.model_identifier = (
            self._model_identifier_prefix + f".params.{self.parameter_fingerprint}"
        )
        self.greenhouse_config = {"schemaVersion": 1, "overrides": {}}
        self.greenhouse_summary = None
        self.initial_state_fingerprint = "unversioned"
        self.configuration_fingerprint = "unversioned"
        self.weather_fingerprint = "unversioned"
        self.run_id = ""
        self.weather_id: str | None = None
        self.weather_label: str | None = None
        self._custom_weather_active = False
        self._custom_weather_days = 60
        self.run_window: dict[str, Any] | None = None
        self._uploaded_prepared: Mapping[str, Any] | None = None
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
        self._pending_previous_environment = None
        self.reset({})

    def _make_environment(
        self, weather_repository: Any, *, season_length: int, pred_horizon: float
    ) -> Any:
        return self._gym.make(
            "gl_gym/GreenLightTomato-v0",
            normalize_actions=False,
            weather_data_dir=self._weather_data_dir,
            weather_repository=weather_repository,
            season_length=season_length,
            pred_horizon=pred_horizon,
        )

    def _replace_environment(
        self, weather_repository: Any, *, season_length: int, pred_horizon: float
    ) -> None:
        previous = self.env
        candidate = self._make_environment(
            weather_repository,
            season_length=season_length,
            pred_horizon=pred_horizon,
        )
        self.env = candidate
        self.core = candidate.unwrapped
        self._pending_previous_environment = previous

    def prepare_uploaded_weather(self, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """Convert an upload without changing the current run."""
        return prepare_uploaded_weather(
            records,
            np=self._np,
            dt=self.core.dt,
            rh_to_vapor_density=self._rh_to_vapor_density,
            vapor_density_to_pressure=self._vapor_density_to_pressure,
            co2_ppm_to_density=self._co2_ppm_to_density,
            soil_temperature=self._soil_temperature,
            daily_light_sum=self._daily_light_sum,
            compute_is_day=self._compute_is_day,
        )

    def _activate_uploaded_weather(
        self, prepared: Mapping[str, Any], request: Mapping[str, Any]
    ) -> None:
        window = validate_window(request.get("runWindow"), prepared["coverage"])
        start_index = (window["startSeconds"] - prepared["gridStartSeconds"]) // STEP_SECONDS
        row_count = window["totalSteps"] + window["lookaheadSeconds"] // STEP_SECONDS + 1
        weather = self._np.asarray(prepared["weather"], dtype=self._np.float64)[
            start_index : start_index + row_count
        ]
        if len(weather) != row_count:
            raise ValueError("The uploaded weather does not cover this window and look-ahead.")
        self._replace_environment(
            InMemoryWeatherRepository(weather),
            season_length=max(1, math.ceil(window["totalSteps"] / 96)),
            pred_horizon=float(prepared.get("predHorizonDays", 0.5)),
        )
        self._custom_weather_active = True
        self._custom_weather_days = int(prepared["seasonLengthDays"])
        self.weather_id = str(request.get("_weather_id", self.weather_id or "")) or None
        self.weather_label = str(
            request.get("_weather_label", self.weather_label or "Uploaded weather")
        )
        self.run_window = window
        self._uploaded_prepared = prepared

    def _activate_default_weather(self) -> None:
        # Every initialized run gets a candidate environment. Parameter/state
        # edits must never mutate the healthy previous solver before success.
        if self.run_id:
            self._replace_environment(
                self._default_weather_repository,
                season_length=60,
                pred_horizon=0.5,
            )
        self._custom_weather_active = False
        self._custom_weather_days = 60
        self.weather_id = None
        self.weather_label = None
        self.run_window = None
        self._uploaded_prepared = None

    def metadata(self) -> dict[str, Any]:
        uploaded = self._custom_weather_active
        return {
            "active": self.kind,
            "scientific": True,
            "model": "GreenLight 2 / GreenLightTomato-v0",
            "version": self.package_version,
            "modelIdentifier": self.model_identifier,
            "gitRevision": self.git_revision,
            "sourceFingerprint": self.source_fingerprint or "unversioned",
            "parameterFingerprint": self.parameter_fingerprint or "unversioned",
            "initialStateFingerprint": self.initial_state_fingerprint,
            "configurationFingerprint": self.configuration_fingerprint,
            "weatherFingerprint": self.weather_fingerprint,
            "adapterVersion": ADAPTER_VERSION,
            "stateCount": 28,
            "controlCount": 6,
            "stepMinutes": self.step_minutes,
            "weather": self.weather_label if uploaded else "Amsterdam recorded weather",
            "weatherSource": "uploaded-in-memory" if uploaded else "recorded-Amsterdam-2010",
            "sourceLabel": "GreenLight-Gym2 source checkout (read-only import)",
            "outputSource": "gl_gym.models.GreenLight.aux_states.update",
            "weatherFile": None if uploaded else "gl_gym/data/weather/Amsterdam/2010.csv",
        }

    def close(self) -> None:
        self.env.close()

    def reset(self, request: Mapping[str, Any] | None = None) -> dict[str, Any]:
        request = request or {}
        reset_started = False
        previous_state = self._capture_run_state()
        try:
            config = validate_config(request.get("greenhouseConfig", self.greenhouse_config))
            effective_parameters = apply_parameters(self.core.base_p, config)
            self.mode = str(request.get("mode", self.mode))
            if self.mode not in {"auto", "manual"}:
                raise ValueError("mode must be 'auto' or 'manual'")

            scenario = self._select_reset_scenario(request)
            seed = int(request.get("seed", 42))

            # The run-local provider supplies the effective vector to reset.
            # Upstream base_p and every source file remain unchanged.
            self.core.parameter_provider.base_p = effective_parameters.copy()

            reset_started = True
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
            default_initial = self._initialize_run_state(config)
            self._describe_configuration(config, default_initial)
            self._begin_run_history()
            snapshot = self.snapshot()
            previous_environment = getattr(self, "_pending_previous_environment", None)
            if previous_environment is not None:
                previous_environment.close()
                self._pending_previous_environment = None
            return snapshot
        except Exception as exc:
            previous_environment = getattr(self, "_pending_previous_environment", None)
            preserved = previous_environment is not None or not reset_started
            if previous_environment is not None:
                failed_environment = self.env
                self.env = previous_environment
                self.core = previous_state["core"]
                self._pending_previous_environment = None
                failed_environment.close()
            self._restore_run_state(previous_state)
            if preserved and not isinstance(exc, ValueError):
                raise PreservedRunResetError(
                    "Candidate initialization failed; the previous run is unchanged."
                ) from exc
            raise

    def _capture_run_state(self):
        """Capture the state restored when candidate initialization fails."""
        previous_state = {
            "greenhouse_config": self.greenhouse_config,
            "greenhouse_summary": self.greenhouse_summary,
            "parameter_fingerprint": self.parameter_fingerprint,
            "initial_state_fingerprint": self.initial_state_fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "model_identifier": self.model_identifier,
            "core": self.core,
            "mode": self.mode,
            "targets": dict(self.targets),
            "scenario_key": self.scenario_key,
            "weather_fingerprint": self.weather_fingerprint,
            "weather_id": self.weather_id,
            "weather_label": self.weather_label,
            "custom_weather_active": self._custom_weather_active,
            "custom_weather_days": self._custom_weather_days,
            "obs": self.obs,
            "run_id": self.run_id,
            "resources": dict(self.resources),
            "history": list(self.history),
            "terminated": self.terminated,
            "truncated": self.truncated,
            "last_reward": self.last_reward,
            "last_info": dict(self.last_info),
            "run_window": self.run_window,
            "uploaded_prepared": self._uploaded_prepared,
        }
        return previous_state

    def _select_reset_scenario(self, request):
        """Select a candidate weather environment and controller targets."""
        scenario_key = str(request.get("scenario", self.scenario_key))
        if scenario_key == "uploaded":
            prepared = request.get("_prepared_weather", self._uploaded_prepared)
            if prepared is not None:
                if "runWindow" not in request and self.run_window:
                    request = {
                        **request,
                        "runWindow": {
                            key: self.run_window[key]
                            for key in (
                                "sourceYear",
                                "timeConvention",
                                "startSeconds",
                                "endSeconds",
                            )
                        },
                    }
                self._activate_uploaded_weather(prepared, request)
            if not self._custom_weather_active:
                raise ValueError("No uploaded weather is active.")
        elif scenario_key in SCENARIOS:
            self._activate_default_weather()
        else:
            raise ValueError(f"unknown scenario: {scenario_key}")
        self._apply_targets(request.get("targets"))
        self.scenario_key = scenario_key
        scenario = (
            {
                "location": "Uploaded",
                "growth_year": self.run_window["sourceYear"],
                "start_day": 1 + self.run_window["startSeconds"] // 86400,
            }
            if self._custom_weather_active
            else SCENARIOS[scenario_key]
        )
        return scenario

    def _initialize_run_state(self, config):
        """Apply the source clock, initial conditions and reward limits."""
        if self.run_window:
            start_seconds = self.run_window["startSeconds"]
            self.core.N = self.run_window["totalSteps"]
            self.core.hour_of_day = (start_seconds % 86400) / 3600
            self.core.day_of_year = 1 + start_seconds / 86400
            self.core.x[27] = start_seconds / 86400
            self.core.x_prev = self.core.x.copy()
            self.obs = self.core.obs = self.core._get_obs()
        default_initial = initial_values(
            self.core.x,
            sat_vp=self._sat_vp,
            co2_density_to_ppm=self._co2_density_to_ppm,
        )
        self.core.x = apply_initial_state(
            self.core.x,
            config,
            sat_vp=self._sat_vp,
            co2_density_to_ppm=self._co2_density_to_ppm,
            co2_ppm_to_density=self._co2_ppm_to_density,
        )
        self.core.x_prev = self.core.x.copy()
        self.obs = self.core.obs = self.core._get_obs()
        # Upstream reward normalization caches equipment-dependent limits
        # at construction. Refresh them using this run's actual parameters.
        reward_context = self._reward_context_class(
            t=0,
            dt=self.core.dt,
            Np=self.core.Np,
            x_prev=self.core.x_prev,
            x=self.core.x,
            u=self.core.u,
            p=self.core.p,
            d=self.core.weather_data,
            obs=self.obs,
            day_of_year=self.core.day_of_year,
            hour_of_day=self.core.hour_of_day,
            constraints_low=self.core.constraints_low,
            constraints_high=self.core.constraints_high,
        )
        reward = self.core.reward_fn
        reward.max_profit = reward.max_profit_reward(reward_context)
        reward.min_profit = reward.min_profit_reward(reward_context)
        return default_initial

    def _describe_configuration(self, config, default_initial):
        """Record the effective parameter and initial-state identities."""
        self.greenhouse_config = config
        if self.run_window and any(key.startswith("initial") for key in config["overrides"]):
            self.run_window["initialization"] = (
                "Run-configured initial states; unspecified states use GreenLight defaults; no warm-up"
            )
        self.parameter_fingerprint = _array_fingerprint(self._np, self.core.p)
        self.initial_state_fingerprint = _array_fingerprint(self._np, self.core.x)
        self.model_identifier = (
            self._model_identifier_prefix + f".params.{self.parameter_fingerprint}"
        )
        self.configuration_fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "parameters": self.parameter_fingerprint,
                    "initial": self.initial_state_fingerprint,
                    "window": self.run_window,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        self.greenhouse_summary = {
            "request": config,
            "fields": field_metadata(),
            "defaults": {**parameter_values(self.core.base_p), **default_initial},
            "effective": {
                **parameter_values(self.core.p),
                **initial_values(
                    self.core.x,
                    sat_vp=self._sat_vp,
                    co2_density_to_ppm=self._co2_density_to_ppm,
                ),
            },
            "floorAreaM2": float(self.core.p[46]),
            "mainAirVolumeM3": float(self.core.p[46] * self.core.p[48]),
            "topAirVolumeM3": float(self.core.p[46] * (self.core.p[49] - self.core.p[48])),
            "boilerCapacityKw": float(self.core.p[108] / 1000),
            "lampCapacityKw": float(self.core.p[172] * self.core.p[46] / 1000),
            "co2CapacityKgH": float(self.core.p[109] * 3600 / 1e6),
            "initialLai": float(self.core.p[142] * self.core.x[23]),
            "warmupHours": 0,
            "calibrated": False,
        }
        next(field for field in self.greenhouse_summary["fields"] if field["key"] == "initialLeaf")[
            "max"
        ] = float(self.core.p[144] / 1000)

    def _begin_run_history(self):
        """Start a new run identity and zero its cumulative resources."""
        self.weather_fingerprint = (
            _array_fingerprint(self._np, self.core.weather_data) or "unversioned"
        )
        self.run_id = uuid.uuid4().hex
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

    def _restore_run_state(self, previous_state):
        """Restore bookkeeping after the previous solver has been recovered."""
        self.mode = previous_state["mode"]
        self.targets = previous_state["targets"]
        self.scenario_key = previous_state["scenario_key"]
        self.weather_fingerprint = previous_state["weather_fingerprint"]
        self.weather_id = previous_state["weather_id"]
        self.weather_label = previous_state["weather_label"]
        self._custom_weather_active = previous_state["custom_weather_active"]
        self._custom_weather_days = previous_state["custom_weather_days"]
        self.obs = previous_state["obs"]
        self.run_id = previous_state["run_id"]
        self.resources = previous_state["resources"]
        self.history = previous_state["history"]
        self.terminated = previous_state["terminated"]
        self.truncated = previous_state["truncated"]
        self.last_reward = previous_state["last_reward"]
        self.last_info = previous_state["last_info"]
        self.run_window = previous_state["run_window"]
        self._uploaded_prepared = previous_state["uploaded_prepared"]
        for name in (
            "greenhouse_config",
            "greenhouse_summary",
            "parameter_fingerprint",
            "initial_state_fingerprint",
            "configuration_fingerprint",
            "model_identifier",
        ):
            setattr(self, name, previous_state[name])

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
            if self.run_window and self.core.timestep >= self.run_window["totalSteps"]:
                self.terminated = True
                break

            if self.mode == "auto":
                action = self._controller_action()
            else:
                action = self._manual_action(manual_controls)

            self.obs, reward, terminated, truncated, info = self.env.step(action)
            self.terminated = bool(terminated)
            if self.run_window and self.core.timestep >= self.run_window["totalSteps"]:
                # Upstream checks termination before incrementing its step counter.
                self.terminated = self.core.terminated = True
            self.truncated = bool(truncated)
            if self.truncated or not self._np.isfinite(self.core.x).all():
                self.truncated = True
                raise RuntimeError(
                    "GreenLight integration failed. Reset the model before continuing."
                )
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
        aux = self._aux_values()
        dt = float(self.core.dt)
        heat_kwh = float(aux[4]) * dt / 3600 * 1e-3
        lamp_kwh = float(aux[5]) * dt / 3600 * 1e-3
        co2_kg = float(aux[6]) * dt * 1e-6
        step_cost = float(info.get("variable_costs", 0.0))
        self.resources["heatKwh"] += heat_kwh
        self.resources["lampKwh"] += lamp_kwh
        self.resources["co2Kg"] += co2_kg
        self.resources["costEur"] += step_cost

    def _aux_values(self):
        # Upstream observations use the forcing of the just-completed step,
        # then increment timestep. Reset uses the first forcing row.
        forcing_index = max(0, int(self.core.timestep) - 1)
        values = self._np.asarray(
            self._aux_function(
                self.core.x,
                self.core.u,
                self.core.weather_data[forcing_index],
                self.core.p,
            ),
            dtype=self._np.float64,
        ).reshape(-1)
        if not self._np.isfinite(values).all():
            raise RuntimeError("GreenLight returned non-finite auxiliary outputs.")
        return values

    def _read_values(self) -> dict[str, Any]:
        climate = self._np.asarray(self.obs["IndoorClimateObservations"], dtype=self._np.float64)
        weather = self._np.asarray(self.obs["WeatherObservations"], dtype=self._np.float64)
        crop = self._np.asarray(self.obs["BasicCropObservations"], dtype=self._np.float64)
        controls = self._np.asarray(self.core.u, dtype=self._np.float64)
        aux = self._aux_values()
        return {
            "climate": climate,
            "weather": weather,
            "crop": crop,
            "controls": controls,
            "canopyTemp": float(self.core.x[4]),
            "leafAreaIndex": float(aux[0]),
            "insideRadiation": float(aux[1] + aux[2]),
            "canopyAbsorbedPar": float(aux[3]),
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
        if self.truncated:
            raise RuntimeError("GreenLight integration failed. Reset is required.")
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
        scenario = (
            {"label": self.weather_label or "Uploaded weather"}
            if self._custom_weather_active
            else SCENARIOS[self.scenario_key]
        )

        snapshot = {
            "runId": self.run_id,
            "greenhouse": self.greenhouse_summary,
            "parameterFingerprint": self.parameter_fingerprint,
            "initialStateFingerprint": self.initial_state_fingerprint,
            "configurationFingerprint": self.configuration_fingerprint,
            "modelReady": True,
            "runWindow": self.run_window,
            "runProgress": self._run_progress(),
            "modelStep": int(self.core.timestep),
            "elapsedMinutes": int(self.core.timestep * self.step_minutes),
            "dayOfYear": int(math.floor(float(self.core.day_of_year))),
            "hour": hour,
            "minuteOfDay": minute_of_day,
            "mode": self.mode,
            "scenario": self.scenario_key,
            "scenarioLabel": scenario["label"],
            "weatherId": self.weather_id,
            "engine": self.kind,
            "modelVersion": self.model_identifier,
            "costModelId": "greenlight-gym2-variable-costs",
            "weatherFingerprint": self.weather_fingerprint,
            "indoor": {
                "airTemp": _round(climate[1]),
                "canopyTemp": _round(values["canopyTemp"]),
                "canopy24hTemp": _round(crop[0]),
                "pipeTemp": _round(climate[3]),
                "rh": _round(climate[2]),
                "co2": _round(climate[0], 0),
                "insideRadiation": _round(values["insideRadiation"], 0),
                "canopyAbsorbedPar": _round(values["canopyAbsorbedPar"], 1),
            },
            "outdoor": {
                "temperature": _round(weather[1]),
                "rh": _round(weather[2]),
                "radiation": _round(weather[0], 0),
                "wind": _round(weather[4]),
                "co2": _round(weather[3], 0),
                "daylight": daylight,
                "cloud": None,
                "sunrise": sunrise,
                "sunset": sunset,
            },
            "crop": {
                "fruitDryMass": _round(float(crop[1]) / 1000.0),
                "tempSum": _round(crop[2], 1),
                "leafAreaIndex": _round(values["leafAreaIndex"]),
            },
            "controls": {
                name: _round(controls[index], 4) for index, name in enumerate(CONTROL_NAMES)
            },
            "targets": {name: float(value) for name, value in self.targets.items()},
            "resources": {name: _round(value, 3) for name, value in self.resources.items()},
            "wholeGreenhouseResources": {
                name: _round(value * float(self.core.p[46]), 3)
                for name, value in self.resources.items()
            },
            "economics": {
                "id": "greenlight-gym2-variable-costs",
                "currency": "EUR",
                "source": "GreenLight-Gym2 info.variable_costs",
                "liveTariff": False,
            },
            "violations": violations,
            "episode": {
                "terminated": self.terminated,
                "truncated": self.truncated,
            },
            "reward": _round(self.last_reward, 6),
            "outputDefinitions": {
                "insideRadiation": "Above-canopy global radiation from sun + top lamps, a[42] + a[43], W/m2; excludes interlighting",
                "canopyAbsorbedPar": "Canopy-absorbed PAR photons, a[191], umol/m2/s",
                "forcingIndex": max(0, int(self.core.timestep) - 1),
                "weatherInput": (
                    "Uploaded Amsterdam-format rows converted in memory; CO2 concentration is consumed, "
                    "soil temperature uses the upstream soilTempNl estimate, and the ?? column remains unused."
                    if self._custom_weather_active
                    else "Recorded Amsterdam/2010.csv converted by the upstream load_weather_data function."
                ),
                "scene": "Illustrative animation, not a spatial radiation or geometry simulation",
            },
            "history": [
                {name: _round(value, 4) for name, value in point.items()} for point in self.history
            ],
        }
        return snapshot

    def _sun_window(self) -> tuple[float | None, float | None]:
        if self.run_window and self._uploaded_prepared:
            absolute = self.run_window["startSeconds"] + self.core.timestep * STEP_SECONDS
            midnight = int(absolute // 86400) * 86400
            offset = (midnight - self._uploaded_prepared["gridStartSeconds"]) // STEP_SECONDS
            raw = self._uploaded_prepared["weather"]
            if offset < 0 or offset + 96 >= len(raw):
                return None, None
            indices = self._np.flatnonzero(raw[offset : offset + 96, 0] > 0)
            if not len(indices):
                return None, None
            return float(indices[0]) / 4, float(indices[-1] + 1) / 4
        steps_per_day = int(24 * 60 / self.step_minutes)
        day_index = int(self.core.timestep // steps_per_day)
        start = day_index * steps_per_day
        radiation = self._np.asarray(
            self.core.weather_data[start : start + steps_per_day, 0],
            dtype=self._np.float64,
        )
        daylight_indices = self._np.flatnonzero(radiation > 0)
        if daylight_indices.size == 0:
            return None, None
        sunrise = float(daylight_indices[0]) * self.step_minutes / 60
        sunset = float(daylight_indices[-1] + 1) * self.step_minutes / 60
        return sunrise, sunset

    def _run_progress(self) -> dict[str, Any] | None:
        if not self.run_window:
            return None
        completed = min(int(self.core.timestep), self.run_window["totalSteps"])
        seconds = self.run_window["startSeconds"] + completed * STEP_SECONDS
        return {
            "completedSteps": completed,
            "totalSteps": self.run_window["totalSteps"],
            "percent": round(100 * completed / self.run_window["totalSteps"], 2),
            "currentDateTime": source_datetime(self.run_window["sourceYear"], seconds),
            "status": "completed" if completed == self.run_window["totalSteps"] else "ready",
        }
