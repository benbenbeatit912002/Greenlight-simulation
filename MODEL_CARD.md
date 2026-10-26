# Model notes: GreenLight Simulation

Documentation updated: 2026-10-26. This is a learning and research tool, not a production climate computer or a system for controlling real equipment.

## Model and scope

The dashboard runs only GreenLight-Gym2, installed as **gl-gym 0.3.2**. It uses the 28-state `gl_gym/GreenLightTomato-v0` environment with six actuator controls. The standard installation includes Amsterdam/2010 weather; an advanced source-checkout override is described in [installation](docs/installation.md).

All simulated climate, crop and resource values come from the full model. A missing connection or solver error stops playback and hides results. There is no simplified-model fallback.

This project adds the interface and adapter. It has software and full-model integration tests, but predictions have not been independently validated here against a real greenhouse. Validation of the original GreenLight model does not automatically validate this package, controller or a user's configuration. Upstream authors and publications are credited in [CITATION.md](CITATION.md).

## Weather, settings and initialization

Weather uploads follow the nine-column Amsterdam format. They provide outdoor inputs; they do not identify the properties of a greenhouse or calibrate the model to a country.

- Uploaded CO₂ is used as outdoor concentration. Built-in Amsterdam loading retains the upstream 400 ppm assumption.
- Soil temperature uses the upstream Netherlands `soilTempNl(time)` approximation with source-year seconds, even for other locations.
- The undocumented `??` column and uploaded day-number column are retained for compatibility, not interpreted as additional model inputs.
- Uploaded runs need an explicit source year and fixed clock convention: UTC or local standard time without daylight saving.
- Start and end must align to 15-minute boundaries. Each simulated day needs full midnight-to-midnight weather plus at least 12 hours after the selected end.
- No missing weather is filled and no next-year file is read. The interval is `[start, end)`; the run stops at its exact endpoint.
- Initialization uses the applied greenhouse and crop settings with zero warm-up. Unspecified compartments and states keep upstream defaults, including an established tomato crop. Startup transients remain in the results.

See [weather input](docs/weather-input.md) for file limits and [greenhouse configuration](GREENHOUSE_CONFIGURATION.md) for the 22 supported parameter/state inputs, units and bounds. Geometry-dependent air/CO₂ capacities and installed equipment totals are recalculated. Blank settings retain reference values; applying a configuration does not rewrite model source defaults. Accepting a combination of settings does not establish that it represents a real greenhouse.

## Controls and outputs

Automatic control uses the upstream rule-based controller. Manual and scheduled modes supply six absolute control values between 0 and 1: heating, CO₂ injection, thermal screen, roof ventilation, lamps and blackout screen. Scheduled controls repeat daily according to the weather clock; they do not react to indoor conditions. See [the schedule guide](docs/controller-schedules.md).

The physical timestep is 900 seconds. Playback speed changes request batching, not model time. The API accepts integer batches of 1–192 steps.

Outputs include indoor/outdoor climate, crop states, actuator positions, heating, lamp electricity, CO₂ use, estimated cost and climate-limit warnings. The live chart is a short rolling history, not a complete result archive.

Radiation and resource values use the upstream auxiliary equations evaluated at the just-completed step's forcing:

| Output | Upstream value | Unit or interpretation |
| --- | --- | --- |
| Above-canopy global radiation | `a[42] + a[43]` | W/m² from sun and top lamps; excludes interlighting |
| Canopy-absorbed PAR | `a[191]` | µmol/m²/s |
| Leaf area index | `a[31]` | LAI |
| Heating, lamp electricity and CO₂ use | Integrals of `a[220]`, `a[37]` and `a[222]` | Cumulative resources |

Resources are reported per m²; whole-greenhouse totals use the applied floor area and unrounded values. Fruit dry mass is not a validated forecast of marketable yield.

The greenhouse drawing, plant animation and warning colours are visual aids, not spatial predictions or extra measurements. Cloud amount is unavailable rather than reported as a measured zero.

### Target limits

| Target | Dashboard range | API range |
| --- | --- | --- |
| Day temperature | 16–30 °C | 10–35 °C |
| Night temperature | 12–24 °C | 8–30 °C |
| CO₂ | 400–1500 ppm | 300–1600 ppm |
| Maximum RH | 60–90% | 40–98% |

These are software input bounds, not recommended growing conditions. Non-finite targets and controls are rejected.

## Comparing runs

A control-plan comparison requires matching model identity, weather, greenhouse configuration, initial state, cost assumptions, scoring limits and duration. Runs must be separate and keep their strategies unchanged. Baselines from another model version or without enough identifying information are blocked.

The model identifier combines the package version or source-checkout label, adapter version, effective parameter fingerprint, and either an exact source Git revision or a SHA-256 fingerprint of the exact `gl_gym` Python modules loaded by the adapter. Weather and the actual 28-state initial array have separate fingerprints; configuration identity includes the selected time window. Installed-package runs do not use this dashboard repository's commit as the model's source revision.

These identifiers are visible in the interface and API. Keep them with any result you want to reproduce. Unknown or unversioned model identity is not accepted for comparison.

### Cost assumptions

The adapter accumulates GreenLight-Gym2's `variable_costs` under the identifier `greenlight-gym2-variable-costs`. It does not use live tariffs, time-varying carbon intensity, taxes or demand charges. Estimated cost is not a utility quote, and a lower resource total does not necessarily mean a better crop outcome.

## What has been checked

| Evidence | Current status |
| --- | --- |
| Software behavior | Automated tests cover requests, dates, configuration, uploads, translations, schedules and comparison checks. |
| Full-model integration | Tests initialize, reset and step the installed model, check resource accounting and exercise uploaded weather. |
| Diagnostic checks | Some configuration and auxiliary-output checks exist; broader tests of physical response are still needed. |
| Operational comparison with measurements | Independent predictive validation is not completed in this public version. |
| Dynamic validation across seasons or greenhouses | Not completed. |
| Uncertainty in parameters and predictions | No uncertainty intervals are available in the dashboard. |

Passing these checks is not proof of prediction accuracy.

The 2026-10-17 weather-archive test completed **30 of 32** default-controller runs. Davis summer cases for both 2023 and 2024 failed integration. The cause has not been isolated; valid weather input therefore does not guarantee numerical completion. See [the weather collection results](data/weather/README.md).

The separate [synthetic fitting example](docs/calibration.md) tests an optimizer using targets generated by the same simulator. It is not real-greenhouse calibration, and its fitted value is not adopted by the dashboard.

## Remaining limits

There is no live sensor connection, hardware control, disease model, automatic regional calibration or full time-series export. Results do not guarantee yield, energy savings, profit or safe growing conditions.

Calibration needs indoor measurements, greenhouse and equipment information, and actual control histories. Parameters should be fitted on one period and evaluated on another. Defaults are not automatically appropriate for every site.

For test commands and recording a repeatable experiment, see [scientific validation](docs/scientific-validation.md). Planned exports, additional settings and measurement-based calibration are listed in the [roadmap](docs/roadmap.md).

## Further reading

- [GreenLight (Katzin et al., 2020)](https://doi.org/10.1016/j.biosystemseng.2020.03.010) and [GreenLight-Gym (van Laatum et al., 2025)](https://doi.org/10.1016/j.ifacol.2025.11.827): the model and environment used here.
- [Tomato digital twin (de Visser et al., 2025)](https://research.wur.nl/en/publications/towards-optimization-of-tomato-cultivation-using-a-digital-twin/): calibration with sensor and plant observations.
- [Greenhouse model prediction (Zhou et al., 2023)](https://research.wur.nl/en/publications/boosting-the-prediction-accuracy-of-a-process-based-greenhouse-cl/): parameter estimation and a separate data-driven correction.
- [US EPA model evaluation framework](https://www.epa.gov/cmaq/cmaq-model-evaluation-framework): the distinction between operational, diagnostic, dynamic and uncertainty evaluation used above.
- [FAIR Principles for Research Software](https://doi.org/10.15497/RDA00068): reproducibility and reuse of research software.
