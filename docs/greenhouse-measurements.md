# Three open greenhouse trials

Outdoor weather drives a scenario. To check a simulated room you also need something to compare it with: indoor measurements, the actual equipment in that compartment, and its control history on the same clock. A weather-only simulation is still useful for comparing schedules; it is not a calibration for the grower's site.

| Trial | Where to start | What it can support |
| --- | --- | --- |
| [WUR Autonomous Greenhouse Challenge, edition 2, v2](https://data.4tu.nl/datasets/8b35675d-7549-49cc-a8c3-dedec8d3f23e/2) | CC0 1.0. In the deposited archive use `Weather/Weather.csv`, `Reference/GreenhouseClimate.csv` and the README. | Same-compartment retrospective tomato climate replay. Observed indoor temperature and RH are targets. Pipe temperatures are measured circuit temperatures, not boiler power. See the [authors' greenhouse and equipment description](https://www.mdpi.com/1424-8220/20/22/6430). |
| [WUR LED/HPS trial, v2](https://doi.org/10.4121/78968e1b-eaea-4f37-89f9-2b98ba3ed865.v2) | CC BY-SA 4.0. Start with `Raw data.zip` and the depositor's methodology, not the simulation-output archive. | Two tomato compartments with weather, indoor climate, lamps, vents, screens and pipe temperatures. Useful for reproducing an original GreenLight evaluation; not an independent test of the original model. |
| [WUR Autonomous Greenhouse Challenge, edition 4, v1](https://doi.org/10.4121/fa102772-32db-4b30-bace-12f2016722ce.v1) | CC BY 4.0. The time-series ZIP separates observations from forecasts; inspect each compartment's channel metadata. | A separate 2024 trial with an explicit local time zone. Different equipment and dwarf potted tomatoes: do not reuse a high-wire tomato equipment/crop profile without checking it. |

### What we checked in the AGC2 Reference compartment

The official v2 archive has MD5 `2a0c7f3332881caef54ca8f4dc60c9a3` as listed by 4TU. The two local CSVs matched the corresponding archive members byte-for-byte by calculated SHA-256. Both have 47,809 unique, aligned five-minute timestamps, but 71 timestamps lack outdoor and indoor readings. Keep gaps and reject invalid measurements; the rows do not establish a UTC offset or the timing of each sensor within an interval.

Use measured `Tair` (°C) and `Rhair` (%) for scoring, not requested or realized setpoints. `VentLee`, `Ventwind`, `EnScr`, `BlackScr` and `AssimLight` are process-computer status channels. Independent position feedback is not established. The sign convention of `Pyrgeo`, screen endpoints and mixed-lamp heat partition remain unresolved. The documented and assumed CO₂ dose area units differ by a factor of 10,000. Do not infer five-minute boiler power from the two pipe temperatures or call a conditional retrospective replay a control forecast.

### What a one-parameter fit actually changed

A frozen, exploratory test used two six-hour episodes on January 25–26, 2020, to select one thermal-screen air-flux multiplier (kThScr, governing air exchange through the deployed screen) from five values. It compared the original and training-selected settings to measured indoor T/RH on separate episodes on February 24 and 26, excluding the first hour of each episode. There were 120 scored measurements per partition. These dates have **already been evaluated**; rerunning the protocol checks repeatability, not performance on unseen data.

| Held-out error | Baseline | Selected multiplier (0.5×) |
| --- | ---: | ---: |
| Temperature RMSE (°C) | 1.17924 | 1.17908 |
| Relative humidity RMSE (percentage points) | 7.55686 | 7.55269 |
| Temperature MAE (°C) | 0.98321 | 0.98366 |

The winner was on the grid boundary, neither RMSE improvement met the prespecified 5% criterion, and temperature MAE slightly worsened. **No parameter was adopted.** A separate sensitivity check with the blackout screen assumed open failed on one training episode; its April evaluation outcomes were not used in that test. Stronger evidence would require measured equipment mappings and predefined fit and evaluation periods with no shared samples, as well as a separate greenhouse before claiming transfer to another site. Links above identify the original sources and terms; no raw trial data is redistributed here.
