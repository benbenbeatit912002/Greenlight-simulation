# Scheduled control and fair comparisons

Set a daily schedule for the six greenhouse controls and compare it with automatic control. This is **open-loop control**: equipment follows the chosen times and levels rather than responding to indoor conditions. It is not an optimizer, MPC or a hardware controller. All simulated responses come from the full GreenLight-Gym2 model.

## Research basis and upstream capabilities

- E. J. van Henten and J. Bontsema (2008), [Open-loop optimal temperature control in greenhouses](https://doi.org/10.17660/ActaHortic.2008.801.72), Acta Horticulturae 801, 629–636. The study optimizes a heating profile with known weather and examines control resolution and thermal screens. Its conclusions concern its own model and objective, not validation of this dashboard. We use a manually prescribed schedule, not the paper's optimization algorithm.
- [Optimal control of greenhouse climate](https://doi.org/10.1016/B978-0-08-041273-3.50010-0) (1991), IFAC Proceedings 24(11), 27–32, provides earlier greenhouse optimal-control context. Forecast and model errors limit direct application of open-loop solutions.
- [GreenLight-Gym2](https://github.com/BartvLaatum/GreenLight-Gym2) exposes an environment action interface and a rule-based controller. External scheduled actions can already drive its model. No ready-made daily schedule editor was found in the inspected upstream controller components.
- The [GreenLight platform](https://github.com/davkat1/GreenLight) also contains a [constant-control example for the Van Henten 2003 model](https://github.com/davkat1/GreenLight/blob/main/greenlight/models/van_henten_2003/definition/main_evh2003_constant_control.json). This is evidence of prescribed-input support, not the same model definition as the 28-state GreenLight-Gym2 greenhouse used here.

GreenLight already accepts prescribed control inputs. This project adds the schedule editor, equipment timeline and comparison checks around that model interface.

## Select equipment for MPC

On **3. Run & compare**, under **Model predictive control (MPC)**, check the devices the optimizer may move. Select **Initialize with this selection**, then press **Start simulation**. Leave all six unchecked to start normal rule-based control. You can edit the next selection during a run; it has no effect until you initialize a new run. The active ownership line lists what was actually applied.

Every 15 minutes the existing rules calculate all six commands from the current simulated greenhouse. Only the selected entries can be replaced by MPC. A rule-owned screen can still open or close; its position is not frozen. The optimizer predicts with the full GreenLight integrator using up to two recorded weather intervals, never beyond the run end. It tests one candidate command per selected device across this short horizon and holds the other devices at their current rule outputs. It applies the combined command for only 15 minutes before recalculating. Recorded future weather is assumed known; this is not a weather forecast service.

The experimental objective tracks day/night air-temperature targets, penalizes excess humidity and daytime CO₂ shortfall, and discourages equipment effort and abrupt changes. Positive outdoor shortwave marks daytime in this objective. It does not optimize profit, cumulative lighting or yield. An unsuccessful solve pauses before applying a command; there is no hidden switch to another controller. MPC advances one physical interval at a time. Exports include the selected devices and policy version. Use the same conditions and duration when comparing with a rule-based baseline.

The 30 minutes describe the integration horizon, not an information cutoff for the whole controller. GreenLight's existing rules can use the recorded total radiation for the whole source day when deciding on lighting. A morning plan may therefore depend on later sunshine. These are retrospective what-if comparisons, not a real-time forecasting test.

Only MPC-owned devices have a move limit: up to 20 percentage points per 15-minute step relative to their last applied output (for example, 50% can move to 30–70%). This is a controller design limit, not a change to the plant or the original rules.

## Using the panel

1. Select weather and greenhouse settings. For an uploaded workbook, set the source year, clock convention, and simulation window before initialization. Use the [public examples](public-weather-examples.md) if needed.
2. Under **Equipment control and comparison**, choose temperature and RH evaluation limits. These limits score the run; they do not secretly override actuator commands.
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

Run `uv run --no-sync python -B scripts/check.py` for software checks. With the pinned model installed, run `uv run --no-sync python -B examples/fetch_public_weather.py`, then `uv run --no-sync python -B scripts/check_controller_weather.py` for the weather comparison tests. These perform automatic, scheduled and batched-scheduled 72-hour runs for three sites and check matched initial conditions, finite states, cumulative resources, exact stopping and consistent batching. They do not establish predictive accuracy or agronomic safety.
