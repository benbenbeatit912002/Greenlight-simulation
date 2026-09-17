# Implementation Plan: Local Weather to Greenhouse Simulation

Created: 2026-09-08. Updated: 2026-09-15. Status: M1/M2 and the first bounded M3 release implemented; advanced M3 settings and M4/M5 remain planned.

## Objective and present baseline

Let a visitor upload outdoor weather, define a simulation window and greenhouse, run the GreenLight 2 model, and inspect climate, crop and resource outputs. Later, let users calibrate a small set of greenhouse parameters against measured observations.

The application has a bilingual dashboard, a scientific GreenLight-Gym2 adapter, six manual/automatic controls, model-derived auxiliary outputs, comparisons, and Excel validation/preview. M1 uploads drive the full model in memory. M2 adds source-year/calendar selection, coverage validation, fixed-step progress, pause and exact endpoint stopping. The first M3 release adds 22 run-local greenhouse/equipment/cover and initial-state inputs with validation, provenance and a draft/apply interface.

This plan governs the new feature sequence. Older PRODUCT_STRATEGY.md references to public browser approximation fallback are stale: retain the current scientific-only behavior, with simulation disabled when the scientific engine is unavailable.

## Delivery order and user flow

Implement M1 weather execution, M2 time selection, M3 greenhouse/initial-state configuration, M4 reproducible results, then M5 calibration. M1-M4 form the first publicly demonstrable release. Calibration is a separate research milestone.

The interface should guide users through:

1. **Weather:** download the template, upload measurements, review units and coverage.
2. **Time:** choose the start and end within valid coverage.
3. **Greenhouse:** review defaults and enter supported dimensions, equipment and initial conditions.
4. **Run:** review the complete settings, initialize, play/pause and inspect progress.
5. **Results:** inspect trends, resource totals and assumptions; explicitly download a report or recipe.
6. **Calibration (later):** supply indoor measurements and historical controls, fit selected parameters and inspect independent validation results.

Country/location are descriptive metadata. Selecting a country must not silently select physical parameters or claim predictive validity there.

## M0 — Preserve the baseline and define contracts

1. Record Git status and preserve existing modified/untracked files. Commit/push only as part of a user-authorized Git task.
2. Run relevant baseline tests in the simulator's own environment. Record the source/model identifier and existing behavior before modifying it.
3. Define versioned schemas for WeatherDataset, RunWindow, GreenhouseConfig, InitialState and RunRecipe. Specify names, units, bounds, defaults, optional fields and error messages before connecting forms.
4. Keep all new modules inside this repository. Import only necessary protected source with Python -B and disabled bytecode; preserve the exact authorized Amsterdam/2010.csv exception. Do not search other datasets.
5. Set explicit project-local temporary/cache paths for every execution. No additional paid API or service is required.

Exit condition: documented contracts and a recorded working baseline; no protected repository changes.

## M1 — Uploaded weather drives the full model

### Data contract

1. Preserve the current Amsterdam nine-column XLSX schema and existing validation limits. The older UTC schema remains preview-only until it has its own tested converter. The first full-model upload path requires at least 36 hours of coverage for the current 24-hour run window plus 0.5-day controller look-ahead.
2. Retain exact original values and source units in memory. Separate workbook validity from scientific-run readiness.
3. Add source metadata: location label, source year and explicit time convention. The existing year-relative seconds do not establish a timezone. Never infer timezone from country alone.
4. Audit the ten model disturbances and document each mapping. Reuse upstream conversion equations where appropriate: radiation, temperature, humidity-to-vapor-pressure, CO2-to-density, wind, sky temperature, soil temperature, daily radiation sum and daylight transitions.
5. Resolve outdoor CO2 and soil temperature explicitly. The current recorded-weather loader uses 400 ppm and a Netherlands soil-temperature estimate. For custom runs, offer explicit compatibility assumptions first; add user-supplied soil temperature/CO2 through a versioned extension. Display chosen assumptions before running. Do not reinterpret the undocumented ?? column as soil temperature.
6. Define resampling on exact model timestamps, initially 900-second steps. Validate raw coverage first; never extrapolate beyond it. Verify transformation order, radiation/daylight boundaries and daily radiation sums against the upstream implementation. Document deliberate differences rather than silently changing them.

### Backend and UI

7. Extend parsing to provide validated records internally without returning all records in API responses. Keep uploads in bounded memory; return an opaque dataset ID and coverage metadata. Do not persist uploaded files by default.
8. Add an in-memory weather repository accepted by the adapter. Compile/initialize a candidate environment and validate it before replacing a healthy active run. Failed selection must preserve the previous run or clearly mark a failed run if an atomic replacement is impossible.
9. Add a **Use this weather** action after validation. Uploading alone must not reset the simulator. Confirm readiness, initialization progress and active weather identity visibly.
10. Bound retained uploads by count, bytes and lifetime. Preserve the currently active dataset while it is needed; explain expired IDs and re-upload recovery. Keep dataset selection and reset under existing revision/concurrency controls.
11. Record uploaded-data fingerprint, converter version, assumptions and model provenance in each run. Reconnect must retain the active weather identity.

### Acceptance tests

- Two synthetic weather files with different outdoor temperatures produce the expected different forcing values; compare deterministic simulated trajectories under identical controls.
- Selected radiation, RH, CO2 and sky-temperature values reach the correct model channels with verified units.
- Malformed files, gaps, missing inputs, out-of-range times and expired IDs produce actionable errors without corrupting a healthy run.
- Upload preview does not reset the run; explicit weather activation creates a new run ID.
- All simulation values still come from GreenLight; no approximation fallback occurs.
- Verify no uploaded bytes or bytecode are written to protected repositories.

## M2 — Select simulation start and end

Implemented on 2026-09-12 for uploaded Amsterdam-format weather. Source year and UTC/fixed local-standard clock are explicit. Both endpoints align to 900 seconds. Coverage reserves full-day radiation context and 12 hours of look-ahead. Initialization uses model defaults with zero warm-up. The existing 36-hour upload minimum is retained. Built-in scenarios retain preset dates; warm-up controls and replay/scrubbing are not part of M2.

1. After upload, display actual available coverage and distinguish source timestamps from elapsed simulation time.
2. Provide start/end selectors with validation and a displayed duration and step count. For the initial Amsterdam schema, require the source year/time convention before displaying calendar dates. Preserve ambiguous or unknown timezone metadata rather than inventing UTC.
3. Adopt half-open simulation intervals [start, end). Both boundaries must align with the supported 15-minute model grid; reject or explicitly offer aligned choices rather than silently round.
4. Distinguish simulation coverage, initialization/warm-up coverage and controller look-ahead. Reserve all required samples before enabling Start. Start with a validated bounded horizon; do not assume the upstream 60-day default fits an uploaded file.
5. Check how the upstream environment uses season length, N, Np, clock and initial time. Implement arbitrary selected start hours consistently in the state, controller clock, daylight processing and displayed timestamps.
6. Define warm-up as a separate visible interval if introduced. Exclude it from reported evaluation metrics. Do not fabricate preceding weather when warm-up data are absent.
7. Run in bounded step batches, show progress and stop exactly at the requested endpoint. Pause stops new batches; a current solver step may finish. Reset starts a new run; changing inputs requires explicit reinitialization.
8. Explain that playback speed changes wall-clock pacing, not the physical solver timestep. Add replay/scrubbing only after retaining complete results; a replay slider must not pretend to reverse model integration.

Acceptance: correct first/last forcing row and exact step count for one step, one day, non-midnight starts and final coverage boundary; leap-year and timezone tests where supported; no hidden next-year file reads; no stepping beyond the selected interval; short uploads receive a clear coverage explanation.

## M3 — Editable greenhouse, equipment and crop initialization

First bounded release implemented on 2026-09-15. See GREENHOUSE_CONFIGURATION.md for all 22 mapped inputs, dependencies, units, bounds and remaining inherited assumptions. Default reproduction, proportional-area scaling, zero-capacity resources, initialization, rollback and bilingual browser interaction are tested. Named material presets, editable screens/lamp efficiency, additional thermal states and recipe import/export are still future increments; measured-data calibration is M5.

### Parameter mapping first

1. Audit exact upstream default_params.py, greenlight_parameters.py, parameter-provider interfaces and init_state. Build a verified mapping table: UI field -> upstream name -> physical unit -> accepted range -> dependent values -> default source.
2. Expose only mapped parameters supported by this model version. Prefer named registry/provider overrides; avoid scattered numeric parameter indices. Recompute dependent quantities through verified upstream logic or a documented local adapter.
3. Keep all overrides in run-local configuration. Never edit upstream defaults on disk. Hash the actual effective parameter vector and initial state, not merely the unmodified defaults.

### UI sections, implemented in small increments

4. **Geometry:** floor area, air volumes/heights, cover area and ventilation geometry supported by the model. Label per-square-metre and whole-greenhouse outputs clearly. Verify that area changes do not incorrectly scale intensive quantities.
5. **Cover and screens:** expose optical/thermal properties with model defaults. Material labels such as glass/polycarbonate may be introduced only when a documented parameter set exists; a label alone is insufficient.
6. **Equipment:** heating capacity, lamp electric power/efficiency, CO2 injection capacity and ventilation limits where supported. Distinguish installed capacity from the existing 0-1 actuator commands. Equipment-disabled configurations must set physically consistent capacities/controls.
7. **Initial indoor conditions:** air temperature, humidity and CO2 first; then additional thermal states as supported. Convert RH/ppm to internal states using consistent temperatures. Clearly show which states remain model defaults.
8. **Initial crop:** keep tomato as the first supported crop. Expose verified leaf/stem/fruit dry biomass and supported temperature-history states. LAI is derived in the current model; map leaf biomass to LAI or provide one controlled conversion, avoiding contradictory independent inputs.
9. Offer **Use model defaults**, a units/help view, and a review screen showing user overrides and inherited defaults. Apply changes only on a new run. Add recipe import/export after schema validation.

Acceptance: default configuration reproduces the baseline within declared numerical tolerance; every exposed field changes the actual parameter/state it claims; invalid combinations are rejected; changed initial states refresh observations and caches; geometry/unit conversion tests pass; run provenance distinguishes different configurations.

## M4 — Reproducible results and public demonstration

1. Retain complete output series for the selected bounded horizon, separately from the existing short live-chart history. Limit memory use and support cancellation.
2. Provide explicit CSV result download and JSON recipe download. Include timestamps, units, model/converter versions, seed, effective configuration, weather fingerprint, time window and assumptions. A fingerprint alone does not reproduce weather: require the matching input file, or let the user explicitly export a bundle containing it.
3. Keep strategy comparisons compatible with changed configurations: control-only comparison requires the same weather, initial state, greenhouse configuration and time window. Label equipment/configuration scenario comparisons separately with visible differences.
4. Add a synthetic, redistributable example with expected outputs/tolerances and a walkthrough. Never publish protected weather or research results as examples.
5. Verify installation on a clean environment without the author's D-drive layout. Pin/document the approved model source and dependencies, review redistribution/license requirements and provide a model-unavailable explanation. License selection remains an owner decision.
6. Update README, model card, screenshots/tutorial and stale strategy/setup references. Run bilingual desktop/mobile browser checks.

Acceptance: a second user can install, upload the public example, choose a window/configuration, run, export and reproduce results with documented tolerances. Record actual runtime/memory measurements on a stated machine; do not invent performance claims.

## M5 — Greenhouse-specific parameter calibration

### Required evidence and input design

1. Require synchronized outdoor weather, indoor air temperature/RH/CO2 observations, known equipment/geometry, and actual historical actuator inputs. Request crop measurements when fitting crop parameters. Explicitly authorize any private research file before access.
2. Validate timestamp alignment, sampling intervals, units, sensor quality and missing-data policy. Historical actuator inputs should drive calibration runs; do not substitute the simulator's automatic controller for unknown historical actions.
3. Define separate contiguous calibration and held-out validation periods before fitting. Include any warm-up rule; prevent overlap/data leakage. Keep validation observations out of parameter selection.

### Fitting and validation

4. Start with a small physically defensible parameter subset selected after sensitivity/identifiability analysis. Keep directly measured geometry fixed. Do not fit all 208 parameters simultaneously.
5. Define an explicit weighted loss with residuals normalized by declared units/scales or sensor uncertainty. Handle solver failures and physical bounds. Use a free local optimizer, fixed seeds where applicable, and strict evaluation/runtime limits.
6. Show progress and allow cancellation. Save candidate parameter sets locally only through the intended project output workflow; never update protected source defaults.
7. Compare default and fitted parameters on both calibration and held-out periods. Report per-variable RMSE/MAE/bias, residual plots, fitted bounds and sensitivity/uncertainty evidence where available. Do not guarantee held-out improvement.
8. Publish a calibration report with dataset identity, parameter bounds, loss definition, optimizer settings, time splits and failures. Label insufficient data or non-identifiability honestly. Applying a fitted set to future runs must be explicit and versioned.

Acceptance: synthetic known-parameter cases test the fitting workflow without claiming real-world accuracy; held-out measurements are never used by the optimizer; failed fits preserve previous configurations; any real predictive claim is supported by independent data. This is calibration for a greenhouse and observation period, not universal country calibration.

## Proposed implementation touchpoints

Paths below are relative to this simulator repository and are proposals unless already present.

| Area | Existing or proposed files |
| --- | --- |
| XLSX validation and internal records | backend/weather_upload.py, tests/test_weather_upload.py |
| Weather transformation and memory repository | backend/custom_weather.py (new), backend/weather_source.py |
| Dataset lifecycle, schemas and API validation | backend/application.py, backend/server.py, backend/run_config.py (new) |
| Actual model parameters, state, clock and run bounds | backend/greenlight_adapter.py |
| Upload, settings forms and runtime UI | frontend/climate-upload.js, frontend/greenhouse-settings.js, frontend/app.js, index.html, styles.css |
| Reproduction and result exports | backend/run_results.py (new), public synthetic examples |
| Calibration | backend/calibration.py (new, M5 only) |
| Verification and documentation | tests/, README.md, MODEL_CARD.md, worklogs/ |

API evolution should retain existing revision checks. An upload returns a dataset ID; reset accepts a validated dataset/window/configuration; step operates on that immutable initialized run. Exact endpoint names and field names should be finalized in M0, rather than advertised as implemented now.

## Review and completion workflow

For each non-trivial increment: primary implementation -> one read-only review -> evaluate/apply justified recommendations -> at most one follow-up review -> relevant tests and an English HTML work log. Keep unit, real-model integration and UI tests proportional to changed behavior. Use synthetic fixtures wherever possible.

Every milestone log must distinguish implemented behavior, tested evidence, remaining limitations and Git status. The original planning task created no simulator feature. Subsequent milestone logs record the actual implementation and verification of M1 and M2; later milestone descriptions remain proposals.
