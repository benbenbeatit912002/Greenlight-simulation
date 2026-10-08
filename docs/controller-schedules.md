# Scheduled control and fair comparisons

This dashboard now supports a **prescribed daily open-loop schedule**. It is not an optimal-control solver, MPC, automatic regional calibration, or hardware controller. Every simulated response still comes from the full GreenLight-Gym2 model; no browser climate approximation is used.

## Research basis and upstream capabilities

- E. J. van Henten and J. Bontsema (2008), [Open-loop optimal temperature control in greenhouses](https://doi.org/10.17660/ActaHortic.2008.801.72), Acta Horticulturae 801, 629–636. The study optimizes a heating profile with known weather and examines control resolution and thermal screens. Its conclusions concern its own model and objective, not validation of this dashboard. We use a manually prescribed schedule, not the paper's optimization algorithm.
- [Optimal control of greenhouse climate](https://doi.org/10.1016/B978-0-08-041273-3.50010-0) (1991), IFAC Proceedings 24(11), 27–32, provides earlier greenhouse optimal-control context. Forecast and model errors limit direct application of open-loop solutions.
- [GreenLight-Gym2](https://github.com/BartvLaatum/GreenLight-Gym2) exposes an environment action interface and a rule-based controller. External scheduled actions can already drive its model. No ready-made daily schedule editor was found in the inspected upstream controller components.
- The [GreenLight platform](https://github.com/davkat1/GreenLight) also contains a [constant-control example for the Van Henten 2003 model](https://github.com/davkat1/GreenLight/blob/main/greenlight/models/van_henten_2003/definition/main_evh2003_constant_control.json). This is evidence of prescribed-input support, not the same model definition as the 28-state GreenLight-Gym2 greenhouse used here.

It would therefore be inaccurate to say that GreenLight cannot run open-loop controls. This project adds the user-facing editor, scheduling adapter, audit timeline, and guarded comparisons around the existing scientific action interface.

## Using the panel

1. Select weather and greenhouse settings. For an uploaded workbook, set the source year, clock convention, and simulation window before initialization. Use the [public examples](public-weather-examples.md) if needed.
2. Under **Controller schedules and comparison**, choose temperature and RH evaluation limits. These limits score the run; they do not secretly override actuator commands.
3. Click **Initialize automatic baseline**. Run the model for the desired duration, pause, and use **Save baseline** in the comparison panel. Keep this baseline until the experiment is complete.
4. Edit the schedule. Every row specifies all six actuators. The first row must be 00:00; subsequent times must be unique, ascending, and on a 15-minute boundary.
5. Click **Apply schedule and initialize**. This starts a fresh run from the same selected weather, greenhouse configuration, seed, and initial state. Draft changes do not affect an active run until applied.
6. Click **Run to saved baseline duration**. The model stops at the baseline's exact step count; playback speed changes request batching only.
7. Compare whole-run temperature, RH, heating use, and time outside the chosen limits. The equipment timeline shows the latest 24 hours of actual applied commands; the climate metrics include the entire run.

### Actuator and time semantics

| Field | Meaning of 0–100% |
| --- | --- |
| Heating | Fraction of configured boiler capacity, not an indoor temperature setpoint |
| Thermal screen | 0% open; 100% closed |
| Blackout screen | 0% open; 100% closed |
| Roof ventilation | Fractional vent opening |
| CO₂ injection | Fraction of configured injection capacity |
| Supplemental lighting | Fraction of configured lighting power |

Schedules repeat every source-clock day. A row holds its commands until the next row; the last row holds until midnight. Weather timestamps, not the computer's timezone or playback wall clock, determine switching. There is no interpolation of control levels. All six commands are open-loop; no undisclosed automatic safety controller is mixed into scheduled mode. This is a simulation experiment, not a greenhouse operating recommendation.

The four-row default is an intentionally simple teaching example. It is not tuned to any site and can produce very poor climate conditions. Preview the schedule, inspect results, and revise it before drawing conclusions.

### Fairness and metric definitions

Comparisons require full-model identity, identical effective weather, greenhouse configuration, initial-state fingerprint, resource-cost definition, scoring limits, physical step count, and elapsed duration. Runs must have different run IDs. Mixed strategies are rejected after changing mode or automatic targets during a run. Reset to begin a clean strategy comparison.

Climate averages are duration-weighted **end-of-step** samples. A 15-minute interval is counted outside a limit if its ending sample is outside the inclusive bounds. Thus exposure is an estimate at 15-minute resolution, not an exact continuous-time threshold integral. “Either outside” is the union of temperature and RH violations, not their sum. Heating is the existing full-model auxiliary resource accounting in kWh/m²; it is not a browser estimate or live utility bill.

At initialization the metrics have zero evaluated minutes and no mean/min/max. A saved zero-step run cannot be compared. Baseline data is local to this browser (schema v3); older summaries without the new provenance/metrics are ignored.

## API and tests

`POST /api/reset` accepts `mode: "schedule"`, `schedule: {schemaVersion: 1, entries: [{time: "00:00", controls: {uBoil: 0.35, uCO2: 0, uThScr: 1, uVent: 0.05, uLamp: 0, uBlScr: 1}}]}`, and `evaluationLimits: {temperatureMin: 15, temperatureMax: 34, humidityMin: 50, humidityMax: 85}`. Normal revision checks still apply. Schedules cannot be edited through `/api/step`.

Malformed schedules, missing actuators, non-finite values, overlaps, duplicate times, and unsupported keys fail without applying a partial reset. Schedules are selected before each fixed 900-second model action, including inside batched requests.

Run `python -B scripts/check.py` for offline checks. With a read-only `GREENLIGHT_GYM_PATH` and the documented project-local cache environment, run `python -B examples/fetch_public_weather.py` followed by `python -B scripts/check_controller_weather.py` for opt-in numerical robustness checks. The latter performs automatic, scheduled, and batched-scheduled 72-hour runs for three sites and verifies matched initial conditions, finite states, resource monotonicity, exact stopping, and batch invariance. It does not establish predictive accuracy or agronomic safety.
