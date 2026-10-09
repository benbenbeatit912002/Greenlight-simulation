# User guide

Use the top navigation to switch between four focused pages:

- **Live simulation**: greenhouse visualization, live charts, manual controls and model outputs.
- **Weather & dates**: upload and validate weather, then choose the simulation period.
- **Greenhouse settings**: edit geometry, equipment and initial-state drafts.
- **Controllers & comparison**: edit schedules, inspect equipment timelines, save a baseline and compare runs.

Switching pages does not restart the model or discard unsaved form edits. Start/pause and run progress stay available across pages. Browser Back/Forward and direct page links are supported. Reloading the browser is different from switching pages: unsaved drafts are not guaranteed to survive a reload.

1. Follow [installation](installation.md) and open the printed local URL.
2. Choose English or Traditional Chinese using the language button.
3. Check the model badge. Interface-only mode permits workbook validation but hides simulation results.
4. For your own weather, download the template, retain its headers and units, upload, and review validation feedback. The bundled records are synthetic examples.
5. With a configured full model, choose the source year and time convention, then select a valid start/end window. Steps are fixed at 15 minutes; provide full-day context and 12 hours of look-ahead.
6. Select **Set greenhouse dimensions** near the top of the page. Enter length and width in the optional rectangular-floor calculator, copy the area to the draft, and review cover area, main/mean height and roof vents. The space preview shows draft main/top/total air volumes. Review the remaining greenhouse defaults. Apply edits explicitly to initialize a new run; changing a draft field does not alter the current model.
7. Start/pause, choose automatic or manual control, or apply a daily schedule from **Controller schedules and comparison**. Inspect climate and resource outputs.
8. Save a baseline and compare a candidate at the same horizon. Incompatible model, weather, greenhouse configuration, initial state or scoring limits prevent numerical comparison. Follow the [schedule and comparison guide](controller-schedules.md) for automatic-versus-scheduled experiments.

The original blank-weather template contains synthetic examples. The three additional [public NASA weather workbooks](public-weather-examples.md) contain attributed gridded weather with explicit resampling assumptions; select year 2023 when uploading them.

Detailed workbook columns are in [weather input](weather-input.md). API requests are documented in [the API guide](api.md). Supported greenhouse values, units and limits are in [GREENHOUSE_CONFIGURATION](../GREENHOUSE_CONFIGURATION.md).

Playback speed changes the number of steps per request, not the physical timestep. Pausing allows the in-flight batch to finish. Reset starts a new run. A connection or solver error stops playback and hides values.

Each local server owns a shared run; opening another tab does not create a private session. Different people should use separate local instances for independent work. The default server binds only to the local computer.

The live chart is a short history, not a complete experiment archive. Full result export and parameter calibration remain planned. Predictions have not been independently validated in this wrapper; see [MODEL_CARD](../MODEL_CARD.md).
