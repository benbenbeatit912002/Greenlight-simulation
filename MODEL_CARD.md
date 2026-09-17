# Model Card: GreenLight Simulation

Status: pre-deployment research and education prototype
Last reviewed: 2026-09-15

## Decision-support claim

This project helps a user compare simulated greenhouse climate-control choices before trying them in a physical greenhouse. It is a local, explainable decision-support workbench, not a production climate computer, a safety alarm, or an autonomous controller.

The current public interface runs only GreenLight-Gym2. Missing connections or solver errors hide simulation values and stop running. The legacy JavaScript approximation remains in the repository for historical regression tests but is not loaded by the interface.

| Engine | What it is | Appropriate use | Evidence status |
| --- | --- | --- | --- |
| GreenLight-Gym2 | A read-only adapter to the external `gl_gym/GreenLightTomato-v0` environment, using its 28-state GreenLight model, recorded Amsterdam weather, and six absolute controls. | Local scientific-model exploration and integration testing. | The adapter has reset/step integration tests. It has not yet been validated here against an independent greenhouse dataset. |
| Legacy browser approximation (not active) | Historical deterministic JavaScript model retained for regression tests. | Historical software testing only. | Not calibrated; not loaded by the public UI. |

The active engine is visible in the interface and returned by `GET /api/status`. A saved comparison records the engine, model identifier, weather fingerprint, cost-assumption identifier, scenario, horizon, targets, controls, resources, crop result, and alert count. The full-model identifier combines the installed package version (or a `source-checkout` label), adapter version, parameter fingerprint, and either an exact 40-character source Git revision or a SHA-256 fingerprint of the exact `gl_gym` Python modules loaded by the adapter. The selected weather array is fingerprinted separately. Comparisons are blocked when either side has sentinel provenance such as `unknown`, `unversioned`, or `local-source`; runs using the same scenario also require an identical weather fingerprint.

## Intended uses

- Learn how heating, ventilation, screens, CO2 dosing, and supplemental lighting interact in a greenhouse simulation.
- Compare a baseline and a candidate strategy at the same simulated horizon.
- Discuss climate, crop, resource, and cost trade-offs with students, researchers, advisers, or growers.
- Demonstrate a safe architecture for connecting a browser interface to a local scientific model.
- Develop reproducible validation cases before adding real greenhouse data.

## Uses that are not supported

- Sending commands to physical greenhouse actuators.
- Supervising crop safety, worker safety, or equipment safety.
- Claiming guaranteed yield, energy savings, profit, or crop health.
- Treating the browser approximation as a calibrated model.
- Calling this a live digital twin before greenhouse-specific sensor synchronization and calibration exist.
- Comparing runs made with different engines, model versions, cost assumptions, or horizons as if they were controlled experiments.
- Using the output as agronomic or investment advice without independent expert review.

## Inputs and outputs

Radiation is now evaluated directly from the same upstream `aux_states.update` equations as the ODE: above-canopy global radiation from sun and top lamps is `a[42]+a[43]` (W/m2, not including interlighting), and canopy-absorbed PAR is `a[191]` (umol/m2/s). LAI is `a[31]`; heat, lamp electricity and CO2 use integrate `a[220]`, `a[37]` and `a[222]`. Auxiliary values use the forcing row of the just-completed step, matching the upstream observation timing. This replaces the adapter's earlier approximate indoor-radiation formula.

Greenhouse parameters are in upstream `gl_gym/configs/default_params.py`; initial climate and crop state are in `gl_gym/environments/utils.py::init_state`. These parameters have not been calibrated for an arbitrary visitor's greenhouse. Recorded forcing is limited to the explicitly enabled `Amsterdam/2010.csv`, with cross-year reads blocked. Amsterdam-format uploads can be converted in memory for a full-model run after at least 36 hours of coverage. The converter consumes uploaded outdoor CO2, estimates soil temperature with upstream `soilTempNl(time)` using source-year seconds, and retains the undocumented `??` and uploaded day-number columns without interpreting them. Uploaded weather compatibility does not establish accuracy or greenhouse-specific calibration.

Custom uploaded runs require an explicit source year and fixed clock convention (UTC or source-local standard time without DST). The model clock and time state begin at the selected source timestamp, including non-midnight starts. Windows are half-open and aligned to the fixed 900-second model step. Coverage includes each simulated day's complete midnight-to-midnight radiation context and a 0.5-day prediction horizon after the chosen end. The adapter stops at exactly the requested number of steps without filling missing weather. Initial states use the applied run configuration; unspecified states inherit GreenLight defaults, with zero warm-up. Startup transients are part of the reported run. The Netherlands soil-temperature approximation remains an assumption, not a site-calibrated soil model.

The first greenhouse-settings release exposes 22 audited parameter/state inputs, described in [GREENHOUSE_CONFIGURATION.md](GREENHOUSE_CONFIGURATION.md). Height-dependent capacities and area-dependent total equipment capacities are recomputed. Empty overrides exactly preserve upstream parameter/state arrays. Only named initial states are changed; other compartments/surfaces keep defaults. The reward's equipment-dependent normalization is refreshed and observations are recomputed before reporting results. All edits remain in a run-local candidate environment.

Parameter fingerprints now hash the effective model vector; initial-state fingerprints hash the actual 28-state initial array. The configuration fingerprint also includes selected-window metadata. Numeric comparisons require matching configuration evidence, including initial state, so old baselines without that evidence are blocked. Whole-greenhouse resource totals use actual floor area and unrounded cumulative per-area values. These software checks do not establish realistic behavior for every accepted parameter combination.

Cutaway geometry, cloud/sun placement, plant animation, threshold warnings and rounded displays are presentation choices, not additional GreenLight measurements or spatial predictions. Cloud amount is unavailable rather than falsely reported as a measured zero.

The common user inputs are:

- weather scenario;
- automatic or manual control mode;
- day and night temperature targets;
- CO2 and relative-humidity targets; and
- six normalized actuator controls in the interval 0 to 1.

The common outputs include indoor and outdoor climate, crop-state indicators, actuator positions, cumulative heating, lamp electricity, CO2 use, estimated cost, climate-limit warnings, and a short rolling history.

Historical regression context: the retained (inactive) browser model rejects non-finite targets and controls, and requires each step request to be an integer from 1 through 192. Target limits match the interface:

| Target | Accepted range |
| --- | --- |
| Day temperature | 16 to 30 degrees C |
| Night temperature | 12 to 24 degrees C |
| CO2 | 400 to 1500 ppm |
| Maximum relative humidity | 60% to 90% |

These are software input bounds, not universal agronomic recommendations.

The inactive approximation applies the following historical software clamps. They are **not applied to GreenLight-Gym2 scientific state**:

| State or record | Software bound |
| --- | --- |
| Indoor air temperature | -5 to 48 degrees C |
| Relative humidity | 28% to 100% |
| Indoor CO2 | 250 to 1800 ppm |
| Leaf area index | 0.4 to 4.6 |
| Rolling history | 1 to 97 records, ending at the current horizon |

These clamps prevent runaway software state. They are not evidence that every value inside the interval is physically realistic.

## Economic assumptions

Cost is an explanatory output, not a live quotation.

The inactive browser approximation used the versioned assumption set `browser-fixed-eur-2026-07` (not used by the current UI):

| Resource | Fixed illustrative value |
| --- | ---: |
| Heat | EUR 0.09/kWh |
| Lamp electricity | EUR 0.30/kWh |
| CO2 | EUR 0.30/kg |

The full engine accumulates the `variable_costs` value returned by GreenLight-Gym2 and identifies that calculation as `greenlight-gym2-variable-costs`. Neither engine currently receives a live tariff, time-varying carbon intensity, contract price, tax, or demand charge. Results from different cost-assumption identifiers are blocked from comparison.

## Current verification evidence

### Software and diagnostic checks

- The Python API tests cover status, reset, stepping, stale-revision protection, request validation, and loopback-only operation.
- The JavaScript model tests run all four weather scenarios for 192 steps, require finite bounded state and monotonic cumulative resources, and verify deterministic repeatability.
- Manual response tests require heating to raise winter temperature, ventilation to lower summer temperature, CO2 dosing to raise concentration and use, and lighting to raise inside radiation and electricity use.
- Reset tests require the horizon and cumulative resources to return to zero while model provenance remains stable.
- The UI contract requires a scenario change to perform a reset before a new run is compared.
- Calendar-window tests cover non-midnight starts, one-step and one-day windows, the last valid endpoint, batch overshoot, source-year/leap-day validation, unchanged runs after invalid selections, and candidate reset rollback. JavaScript date arithmetic does not depend on the viewer's timezone or daylight saving.
- An opt-in integration test constructs the real GreenLight-Gym2 adapter, resolves Git provenance when available or hashes the exact loaded source modules when it is not, fingerprints parameters and selected weather without modifying the checkout, advances one model step, and checks finite output and immutable provenance.

These tests show that the software behaves consistently with its declared contract. They do not establish predictive accuracy for a commercial greenhouse.

### Evaluation status

The project adapts the US EPA model-evaluation distinction between operational, diagnostic, dynamic, and uncertainty evaluation as a useful general credibility framework:

| Evaluation layer | Question for this project | Status |
| --- | --- | --- |
| Software contract | Does the implementation remain deterministic, finite, bounded, and reproducible? | Automated for the browser model and API. |
| Diagnostic | Do controlled input changes produce physically plausible response directions? | Initial automated actuator-response checks exist; deeper process tests are still needed. |
| Operational | How closely do climate, resource, and crop outputs match held-out observations? | Not yet performed in this repository. |
| Dynamic | Does the model reproduce observed changes across seasons, sites, cultivars, and strategies? | Not yet performed. |
| Uncertainty | How sensitive are decisions to parameters, weather, initialization, and measurement error? | Not yet performed. |

No accuracy threshold or commercial fitness claim should be added until the intended greenhouse, variables, horizon, data quality, calibration split, and decision context are specified.

## Known limitations and risks

- The browser equations and synthetic scenarios are intentionally simplified and can reach unrealistic combinations under extreme manual controls.
- The browser model has no greenhouse geometry, cultivar calibration, equipment capacity calibration, water or nutrient accounting, disease model, uncertainty interval, or sensor assimilation.
- Fixed economic assumptions can reverse the apparent preference between strategies when real tariffs differ.
- End-state fruit dry mass is not a validated marketable-yield forecast.
- The full adapter's successful software integration does not transfer the validation evidence of the original GreenLight publication to this particular package version, weather configuration, controller, or user experiment.
- The active model may depend on an external local GreenLight-Gym2 source checkout. Its package label, Git revision or loaded-source fingerprint, parameter fingerprint, weather fingerprint, adapter version, and repository commit must be retained with any result intended for review. A source that cannot produce either a Git identity or a loaded-source fingerprint is intentionally not comparable in the UI.
- Baseline-versus-candidate deltas are descriptive. A lower resource value can accompany an unacceptable climate or crop outcome.

## Reproducibility

Browser-model contract tests require only Node.js:

```powershell
node --check .\frontend\legacy\simulator-engine.js
node --check .\frontend\app.js
node --test .\tests\browser_model_contract.test.js
```

Default Python checks do not import the protected external model:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_*.py' -v
```

The optional full-model integration check must run with bytecode disabled and an explicit read-only GreenLight-Gym2 source path, as described in `README.md`.

For a publishable validation case, retain at minimum:

1. repository commit and branch;
2. engine, package label, source Git revision or fingerprint, parameter fingerprint, weather fingerprint, and adapter version;
3. cost-assumption identifier;
4. source dataset identifier and license;
5. calibration and held-out validation periods;
6. greenhouse/crop configuration and initialization;
7. scenario, seed, controls, targets, timestep, and horizon;
8. metric definitions, units, missing-data handling, and uncertainty method; and
9. generated plots/tables plus the command that recreates them.

Do not place private greenhouse data, thesis material, credentials, or protected research outputs in this public repository.

## Validation roadmap

1. Add a machine-readable experiment recipe and exportable comparison report.
2. Add time-varying tariff, carbon-intensity, and resource-price inputs with explicit provenance.
3. Select an openly licensed greenhouse dataset and define a calibration/validation split before tuning parameters.
4. Report climate MAE, RMSE, and bias; resource error; crop error; missing-data coverage; and naive-baseline comparisons.
5. Add parameter sensitivity and bounded uncertainty ensembles so decisions show ranges, not only point estimates.
6. Repeat evaluation across a second period or greenhouse before making broader claims.
7. Consider live read-only sensor synchronization only after the offline evaluation protocol is stable.

## Scientific and software-quality references

Full upstream author attribution and BibTeX are provided in [CITATION.md](CITATION.md). The underlying GreenLight model is credited to Katzin and collaborators; the GreenLight-Gym2 environment is credited to van Laatum and contributors. This repository supplies the interface and adapter.

- van Laatum, Bart; van Henten, Eldert J.; and Boersma, Sjoerd (2025), [GreenLight-Gym: Reinforcement learning benchmark environment for control of greenhouse production systems](https://doi.org/10.1016/j.ifacol.2025.11.827). IFAC-PapersOnLine, 59(23), 437–442. This is the citation requested by the [GreenLight-Gym2 upstream repository](https://github.com/BartvLaatum/GreenLight-Gym2#citation).

- Katzin et al. (2020), [GreenLight - An open source model for greenhouses with supplemental lighting](https://doi.org/10.1016/j.biosystemseng.2020.03.010). This is provenance for the underlying GreenLight model, not validation of this project's browser approximation or adapter configuration.
- de Visser et al. (2025), [Towards optimization of tomato cultivation using a digital twin](https://research.wur.nl/en/publications/towards-optimization-of-tomato-cultivation-using-a-digital-twin/). The study describes calibration using sensor data and manual plant observations, followed by scenario-oriented decision support.
- Gong et al. (2023), [Boosting the prediction accuracy of a process-based greenhouse climate-tomato production model by particle filtering and deep learning](https://research.wur.nl/en/publications/boosting-the-prediction-accuracy-of-a-process-based-greenhouse-cl/). The results show why calibration and held-out validation evidence matter.
- US EPA, [CMAQ Model Evaluation Framework](https://www.epa.gov/cmaq/cmaq-model-evaluation-framework). The operational, diagnostic, dynamic, and uncertainty categories are adapted here as a general model-credibility structure.
- FAIR4RS Working Group (2022), [FAIR Principles for Research Software](https://doi.org/10.15497/RDA00068). Versioning, executability, and transparent reuse motivate the repository's provenance and reproducibility records.
