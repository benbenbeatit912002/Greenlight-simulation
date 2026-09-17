# Greenhouse configuration reference

Implemented 2026-09-15 for the GreenLight-Gym2 208-parameter, 28-state adapter. This is a bounded software interface, not greenhouse-specific calibration.

## Using the panel

Open **Step 3 · Greenhouse and initial state** below the weather panel. Expand a group, review the displayed upstream defaults and enter overrides. Blank fields inherit defaults. The review table shows every effective input and whether it is inherited or user-supplied. **Apply settings and initialize** stops playback and starts a new run with the currently active weather/window. Editing alone does not change the model.

**Use model defaults** clears only the draft. Apply it to return the model to defaults. The top reset button and weather selection preserve already applied settings; they do not apply an unfinished draft. Drafts are not saved across page reloads. Applied settings are returned by the server on reconnect/reload.

All values are validated by the backend. A rejected candidate preserves the existing environment, state, configuration and revision. Each reset creates a candidate environment; overrides live in its parameter provider, never in an upstream source file.

## Parameter mapping

Indices below refer to the exact vector in `gl_gym/configs/default_params.py`. Existing upstream named-registry entries include floor area, boiler power, CO₂ dosing and lamp power. Other verified indices are consolidated in `backend/greenhouse_config.py` because the upstream registry does not yet name them. The fixed provider receives a copied, effective vector; the source registry/default vectors are not patched.

| API key | Upstream parameter | Input unit | Supported range |
| --- | --- | --- | --- |
| floorArea | aFlr, p[46] | m² | 1–2000 |
| coverArea | aCov, p[47] | m² including walls | 1–10000; at least floorArea |
| mainHeight | hAir, p[48] | m | 1–15 |
| totalHeight | hGh, p[49] | m, mean height | 1.1–20; at least mainHeight + 0.1 |
| roofVentArea | aRoof, p[55] | m² maximum roof aperture | 0–2000; no larger than floorArea |
| ventHeight | hVent, p[56] | m | 0.1–3 |
| boilerPower | pBoil, p[108] | W/m² floor | 0–500; multiply by aFlr for model W |
| co2Capacity | phiExtCo2, p[109] | mg/m²/s | 0–20; multiply by aFlr for model mg/s |
| lampPower | thetaLampMax, p[172] | W/m² | 0–400 |
| roofParTransmission | tauRfPar, p[69] | fraction | 0–0.87; transmission + inherited reflection ≤ 1 |
| roofNirTransmission | tauRfNir, p[68] | fraction | 0–0.87; transmission + inherited reflection ≤ 1 |
| roofThickness | hRf, p[73] | mm | 0.5–30; divide by 1000 for model m |
| roofConductivity | lambdaRf, p[71] | W/m/K | 0.05–5 |

These bounds are conservative supported input limits, not construction or growing advice. Zero electrical/heating/CO₂ capacity is an explicit output-disable case tested by this adapter; it extends the registry's lamp sampling lower bound. It does not remove equipment thermal mass or leakage. Side ventilation is not exposed because this model implementation fixes side apertures to zero.

Geometry fields are independent. To scale the same design, scale floor, cover and roof-aperture areas together. Floor-area changes retain per-area boiler/CO₂ capacities and recompute their total capacities. Height changes recompute the upstream dependent equations:

- capAir, p[112] = hAir × rhoAir × cPAir;
- capTop, p[120] = (hGh − hAir) × rhoAir × cPAir;
- capCo2Air, p[122] = hAir;
- capCo2Top, p[123] = hGh − hAir.

Other cover properties, emissivities, screen properties and lamp efficiencies remain defaults. A selection of four cover properties is not a complete glass/polycarbonate material preset. The schematic remains illustrative, not a spatial geometry calculation.

## Initial state mapping

Defaults are read from the upstream `init_state` result for the selected weather. No overrides reproduce that original state exactly. State indices refer to `gl_gym/environments/utils.py::init_state`.

| API key | State | Input unit/range |
| --- | --- | --- |
| initialAirTemp | tAir, x[2] | °C, 5–40 |
| initialRh | vpAir, x[15] via upstream satVp(tAir) | %, 10–100 |
| initialCo2 | co2Air, x[0] via upstream co2ppm2dens(tAir) × 10⁶ | ppm, 100–3000 |
| initialLeaf | cLeaf, x[23] | g/m² × 1000 to model mg/m²; 1 through cLeafMax/1000 (about 112.78) |
| initialStem | cStem, x[24] | g/m², 1–3000; ×1000 internally |
| initialFruit | cFruit, x[25] | g/m², 0–3000; ×1000 internally |
| initialCanopyTemp | tCan, x[4] | °C, 5–45 |
| initialCanopy24h | tCan24, x[21] | °C, 5–45 |
| initialTempSum | tCanSum, x[26] | °C day, 0–5000 |

Changing main-air temperature without RH/CO₂ overrides preserves the upstream default main-air RH and ppm, not the original densities. Top air, cover, pipes, screens, soil, carbohydrate buffer and all other unexposed states remain upstream defaults. Canopy temperature and its 24-hour state are separate inputs. LAI is derived as p[142] × x[23]; there is no contradictory independent LAI input. The inherited tomato biomass/temperature-sum defaults represent an established crop rather than a seedling.

After overrides, x_prev and observations are refreshed before the first snapshot. The reward's cached maximum/minimum profit normalization is recomputed from the actual equipment vector. Warm-up remains zero; this does not assert equilibrium or physical consistency with measured indoor history.

## API and provenance

`POST /api/reset` accepts:

```json
{"greenhouseConfig":{"schemaVersion":1,"overrides":{"initialAirTemp":22,"initialRh":70,"initialCo2":800,"boilerPower":150}},"expectedRevision":0}
```

Include the usual scenario/weatherId/runWindow fields when selecting weather. Omitted greenhouseConfig retains the applied configuration. An explicit empty overrides object restores defaults. Numeric strings, booleans, nulls, non-finite numbers, unknown keys and incompatible geometry are rejected.

Snapshots contain the request, inherited defaults, effective inputs, volumes, total installed capacities and initial LAI under `greenhouse`. `resources` remains per m²; `wholeGreenhouseResources` multiplies unrounded cumulative values by actual floor area. Neither is a measured resource saving or calibrated yield forecast.

Parameter and initial-state fingerprints hash the actual effective arrays. The configuration fingerprint also includes the selected time-window metadata. Fingerprints remain immutable while stepping. Numeric comparisons require identical model/configuration fingerprints; old saved baselines lacking configuration evidence are intentionally not comparable. Broader equipment-scenario comparisons remain a later product feature.

## Evidence and limits

Tests cover every exposed mapping, dependent capacities, exact default-state/parameter reproduction, deterministic default trajectories, zero-output capacities, invalid settings preserving a run and proportional area scaling. Browser checks exercise draft versus applied state and reset/reconnect behavior. These are software compatibility checks, not validation against a real greenhouse.

Named material presets, editable screens, lamp efficiency, unexposed thermal states, seedling presets and configuration import/export remain future increments. Measured-data calibration and independent prediction validation remain separate milestones.
