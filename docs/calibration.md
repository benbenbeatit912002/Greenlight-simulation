# Fitting a greenhouse model to local measurements

Changing weather changes the model's input. Calibration changes uncertain model parameters to reduce disagreement with measured greenhouse outputs. A country label is not a parameter set.

## Relevant work

| Reference | Approach | What fits this project |
| --- | --- | --- |
| [Guzman-Cruz et al. (2009), Calibration of a greenhouse climate model using evolutionary algorithms](https://doi.org/10.1016/j.biosystemseng.2009.06.006) | Compared evolutionary and local-search methods against measured indoor temperature and humidity, after sensitivity analysis. | Fit a small, sensitive subset of parameters and compare with held-out measurements. The best method in that study is not automatically best here. |
| [Zhou et al. (2023), GreenLight/TOMSIM, particle filtering and deep learning](https://doi.org/10.1016/j.compag.2023.107980) | Estimated greenhouse parameters with a particle filter, then tested a neural correction trained on measured data. Parameter fitting improved vapor-pressure predictions but did not improve temperature by itself. | Start with the physical model and parameter estimation. A neural correction needs real targets and changes what an output represents; it is not included here. |
| [de Visser et al. (2025), tomato digital twin](https://doi.org/10.17660/ActaHortic.2025.1425.28) | Calibrated crop growth using early sensor and manual plant measurements, then evaluated later months and updated plant state from sensors. | Separate calibration from later evaluation, and distinguish state updating from parameter fitting. |
| [LetsGrow Strategy Manager configuration](https://support.letsgrow.com/portal/en/kb/articles/configuring-your-greenhouse-location-and-crop-compartments-7-5-2024) | Requires compartment geometry, greenhouse type, insulation and heating information. | Keep weather and greenhouse configuration separate. This product guide does not disclose an automatic fitting algorithm. |

These sources support a measurement-based workflow. They do not establish that outdoor weather alone can identify greenhouse parameters.

## A tested first step

`examples/calibration_demo.py` tests bounded least squares using [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html). It runs the full GreenLight model to generate synthetic indoor temperature/RH, hides one boiler-capacity value, and tries to recover it. This is a small implementation test, not a reproduction of those papers or a fit to a real greenhouse.

```sh
uv run --no-sync python -B examples/collect_weather.py --site amsterdam-nl
uv run --no-sync python -B examples/calibration_demo.py
```

The experiment uses fixed open-loop controls, a known initial state, a 48-hour Amsterdam January window from 2023 for fitting, and a separate 2024 window for evaluation. It excludes the first 12 hours of each run. Synthetic noise standard deviations are 0.1 °C and 0.5 RH percentage points. The residual scales are 0.2 °C and 1 RH point. The soft-L1 loss and bounds of 80–320 W/m² are experiment choices, not recommendations for every greenhouse.

On 2026-10-17, 25 model runs recovered **179.98 W/m²** from a synthetic value of **180 W/m²**, starting from 260 W/m². Held-out synthetic temperature RMSE changed from 1.927 to 0.101 °C, and RH RMSE from 4.577 to 0.493 percentage points. The same simulator creates and fits the targets, so this is an intentionally easy inverse problem. It tests units, replay, optimizer wiring and separation of years; it says nothing about field accuracy. No value is applied to the dashboard or saved into upstream model files.

## Before fitting real measurements

1. Record location, UTC offset, timestamps, units, sensor quality and the exact greenhouse/crop specification. Fix measured geometry instead of letting an optimizer invent it.
2. Supply synchronized outdoor forcing, indoor temperature/RH (and CO₂ if fitted), and the **actual applied** heating, vent, screen, lamp and CO₂ commands. Controller setpoints alone are not actuator histories.
3. Check gaps and sensor delays. Define a warm-up interval and chronological calibration/validation periods before tuning anything. Do not randomly mix neighboring rows across the split.
4. Screen candidate parameters for sensitivity and identifiability. Fit a few uncertain parameters within justified physical bounds. Use weighted residuals so different units do not dominate solely by scale.
5. Evaluate the untouched period. Report temperature/RH MAE, RMSE and bias, failed simulations, parameter bounds and uncertainty. Reject a fit that only improves training error or produces implausible settings.
6. Repeat on another period or facility before claiming regional transfer. Keep the original defaults and require an explicit user action to apply any candidate.

The weather archive lacks the indoor and actuator measurements required by steps 2–5. Automatic real-greenhouse calibration is therefore not enabled in the dashboard. Particle filtering, neural residual correction and online adaptation remain future work.
