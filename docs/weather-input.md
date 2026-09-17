# Weather input

## Workbook workflow

The first custom-weather milestone is available in the **Import your outdoor weather** panel. Expand its bilingual **Excel tutorial**, download the [Excel template](../templates/greenlight-weather-template.xlsx), replace its synthetic example rows, choose the workbook, and select **Check and run**. The English template contains instructions and 433 invented 5-minute records spanning 36 hours; these are not research measurements. A full-model run needs at least 36 hours so the GreenLight model has a 24-hour simulation window plus its 0.5-day prediction horizon.

The Amsterdam-format upload now has two stages. The server validates the workbook in memory and, when the full model is available and at least 36 hours are covered, prepares a bounded in-memory dataset with the model's 0.5-day look-ahead. The response distinguishes `conversionReady` from `modelReady`: conversion readiness means the weather is staged and can be selected; model readiness is reported only after a successful reset. Selecting **Run with this weather** explicitly initializes a new GreenLight run; uploading alone does not reset the active run. A successful readiness check is evidence of software compatibility for this adapter path, not predictive accuracy for another greenhouse.

The `Weather` sheet uses schema `amsterdam-weather-xlsx-v2`, matching the exact header order of `Amsterdam/2010.csv`:

| Column | Meaning | Required for preview |
| --- | --- | --- |
| `time` | Numeric seconds since start of the source year | Yes |
| `global radiation` | Global solar irradiance, W/m2; not PAR or accumulated energy | Yes |
| `wind speed` | Outdoor wind speed, m/s | Yes |
| `air temperature` | Outdoor air temperature, degrees Celsius | Yes |
| `sky temperature` | Effective sky temperature, degrees Celsius | Yes |
| `??` | Undocumented placeholder, retained but not consumed by the upstream loader | Yes |
| `CO2 concentration` | Outdoor CO2 concentration, ppm; consumed by the uploaded-weather converter | Yes |
| `day number` | Source day field, retained but not consumed by the loader | Yes |
| `RH` | Outdoor RH, numeric 0–100 percent, not an Excel fraction | Yes |

Keep exact, unique column names in row 1, in the listed order. Only `Weather` and an optional `Instructions` sheet are accepted. All nine cells in each record must be finite numbers. Times must align to 300-second boundaries and increase by exactly 300 seconds. Selected windows can begin later in the year. The converter preserves source-year seconds for the model clock, daily radiation and the upstream `soilTempNl(time)` soil-temperature estimate. It consumes uploaded outdoor CO2 but does not interpret `??` as soil temperature. Earlier `weather-xlsx-v1` workbooks remain accepted for backward-compatible preview with their original UTC/1–60-minute contract.

### Custom simulation dates

1. Upload and check an Amsterdam-format workbook (at least 36 hours, within the existing upload limits).
2. In **Simulation dates**, enter its actual source year (1900–2100). Select **UTC** or **Local standard time** to match the file. Local standard time is a fixed clock without daylight-saving transitions. The app never infers or converts timezone from your computer or a country name.
3. Review uploaded weather coverage and the narrower selectable simulation range. Select start/end on 15-minute boundaries. The panel shows duration and step count; 09:15–10:00 is three steps.
4. **Run with this weather** initializes the selected window. Then start or pause the simulation. Progress shows completed/total steps and the source-clock timestamp. It stops exactly at the chosen end even when a requested batch would overshoot. Reset explicitly starts a new run; uploading alone does not reset one.

The interval is `[start, end)`. GreenLight uses the applied indoor/crop initial-state settings (unspecified states inherit model defaults) with **zero warm-up**; this is not equilibrium initialization or calibration. Each simulated date needs midnight-to-midnight weather for daily radiation totals, plus at least **12 hours after the selected end** for controller look-ahead. Both constraints affect the selectable range. No missing samples are filled and no next-year file is read. A partially covered first day cannot be used as a simulation date. Playback speed changes pacing/batch size, not the **900-second physical timestep**. Pause stops new batches; an in-flight batch can finish.

Custom dates currently apply to uploaded Amsterdam-format weather. Built-in scenarios retain preset windows. Advanced greenhouse settings, warm-up configuration, result-series export and location-specific calibration remain later milestones.

### Greenhouse and initial state

**Step 3 · Greenhouse and initial state** exposes 22 verified inputs: floor/cover area and heights, roof ventilation, boiler/CO₂/lamp capacities, four cover properties, main-air initial temperature/RH/CO₂, and tomato biomass/canopy-temperature history. Inputs change the full model, not only the drawing. Review the inherited defaults and the settings table, then select **Apply settings and initialize**. Draft edits do not change a running simulation. **Use model defaults** clears the draft; apply it to reset with defaults.

Area fields are independent. Air/CO₂ capacities are recalculated for changed heights; total boiler and CO₂ capacities scale with floor area. Existing resource cards remain per m², and the new panel separately reports whole-greenhouse totals. Parameter and initial-state fingerprints describe the actual arrays. Comparisons with different configurations or initial states are blocked.

See the [configuration mapping and limitations](../GREENHOUSE_CONFIGURATION.md) for exact units, supported ranges, inherited states, zero-capacity behavior and API examples. These inputs are not measured-data calibration or complete named material presets. Source defaults and protected model checkouts are never modified.

Input bounds are software-supported weather ranges, not agronomic recommendations: air temperature -80 to 65 C, RH 0–100%, radiation 0–1600 W/m2, wind 0–100 m/s, sky temperature -120 to 80 C, soil temperature -60 to 90 C, and CO2 100–5000 ppm. Numeric text, booleans, nonfinite values, formulas, macros, embedded objects and external workbook links are rejected.

Uploads are limited to 2 MiB, 10,000 records (about 34 days at 5-minute resolution), nine columns, 256 archive entries and 16 MiB uncompressed content. Do not upload the whole Amsterdam year. Use a plain XML-based `.xlsx` package without images or other binary attachments. Only one upload is processed at a time. The response includes the time range, interval, column ranges, first five records, SHA-256 fingerprint and up to 30 row/column errors. Uploaded bytes are checked in memory on the local server and are not persisted, logged as data, or sent to GitHub. Private runtime folders are excluded from Git and HTTP serving.

To try the preview without importing an external model, use [the interface-only installation](installation.md). Static-file-only hosting can show the panel and template but cannot process uploads; the Python backend is required.
