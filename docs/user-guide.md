# User guide

You can use the simulator with outdoor weather only. Indoor measurements are not required for the main workflow. The results describe a modelled greenhouse under your chosen assumptions; uploading weather does not calibrate the model to that location.

Follow [installation](installation.md), open the printed local URL and choose English or Traditional Chinese. The full-model badge must be connected to run a simulation. Interface-only mode permits workbook checks but hides simulation results.

## 1. Weather and dates

Use the bundled Amsterdam/2010 weather to explore, or upload your own outdoor weather workbook.

1. Download the template and keep its headers, units and five-minute row spacing. Its example rows are synthetic, not local measurements.
2. Upload the workbook and select **Check weather data**. This checks the file; it does not change the active run.
3. Choose the source year and fixed clock convention (UTC or source-local standard time without daylight saving).
4. Select a valid start and end. The model uses 15-minute steps and needs full-day radiation context plus 12 hours of look-ahead. Missing weather is not filled in.
5. Select **Apply weather and dates**. This initializes a new run but does not start stepping.
6. Continue to **Greenhouse settings**.

The three [public NASA weather workbooks](public-weather-examples.md) contain attributed gridded weather with explicit resampling assumptions. Select source year 2023 for these examples. They are not five-minute on-site measurements. See [weather input](weather-input.md) for all columns and limits.

## 2. Greenhouse settings

Enter the dimensions, equipment capacities and initial climate/crop conditions you know. You may leave fields blank: each field displays the **reference default** it will use. These defaults are not automatically adjusted by country.

- The optional length/width calculator copies floor area into the draft. It does not resize cover area or roof vents. Review those independently.
- The space preview and review table describe your draft, not necessarily the active run.
- **Clear draft to reference defaults** clears the form. It does not change the running simulation until you apply.
- **Apply settings and initialize** creates a new run with the edited settings. Applying configuration does not change the model's stored defaults.
- Continue to **Run & compare**, or open **Live simulation**.

The three-step guide reports applied server state: bundled/uploaded weather, reference defaults versus explicit user overrides, and whether a baseline is saved. Editing a form or checking a workbook does not update these applied-state labels. An override may equal a default numerically; the count describes how a value was supplied, not proof that it differs. Independent parameters without overrides retain reference values. Dependent heat and CO₂ capacities and total equipment capacities are recalculated from the applied geometry and equipment settings.

Unknown properties still matter. Unspecified initial states use the reference established tomato crop; there is no warm-up period. Uploaded-weather soil temperature uses the upstream Netherlands approximation. Results are estimates under these assumptions, not local measurements, verified savings or production advice. See [GREENHOUSE_CONFIGURATION](../GREENHOUSE_CONFIGURATION.md) for values, units and bounds.

## 3. Run and compare control plans

Use **Controllers & comparison** to compare automatic control with a daily schedule. Keep the applied weather, greenhouse, initial state and evaluation limits fixed.

1. Set the comparison limits and select **Initialize automatic baseline**.
2. Select **Start simulation**. Pause at the duration you want to compare and let the in-flight batch finish.
3. Save the current result as the baseline.
4. Edit the daily equipment schedule and select **Apply schedule and initialize**. This starts a separate run using the same applied weather and greenhouse configuration.
5. Select **Run to saved baseline duration**.
6. Review temperature, humidity, heating and time outside limits together. Lower energy alone does not establish a better growing strategy.

A saved baseline is not automatically comparable. The existing checks require matching model, weather, greenhouse configuration, initial state, scoring limits and horizon, plus separate runs with unchanged strategies. Changing weather, greenhouse settings or limits means you must create a new matching baseline. This workflow compares control plans, not different greenhouse designs against one fixed baseline.

See the [schedule and comparison guide](controller-schedules.md) for details. Measured validation and parameter fitting remain separate research tasks, not prerequisites or steps in this workflow.

## Navigation and run behaviour

Four pages are available: **Weather & dates**, **Greenhouse settings**, **Controllers & comparison**, and **Live simulation**. The guide and next-step links only navigate; they never apply drafts, change model settings or start a run. You can skip uploading weather or editing settings and use the active reference example.

Switching pages does not restart the model or discard unsaved form edits. Start/pause and progress stay available across pages. Browser Back/Forward and direct page links are supported. Reloading is different: unsaved drafts are not guaranteed to survive a reload.

Playback speed changes the number of steps per request, not the physical timestep. Pausing allows the current batch to finish. Reset initializes a new run. A connection or solver error stops playback and hides values; there is no browser approximation fallback.

Each local server owns a shared run. Another tab is not a private session; different people should use separate local instances. The default server binds only to the local computer.

The live chart is a short history, not a complete experiment archive. Full result export remains planned. Predictions have not been independently validated in this wrapper; see [MODEL_CARD](../MODEL_CARD.md). API requests are documented in [the API guide](api.md).
