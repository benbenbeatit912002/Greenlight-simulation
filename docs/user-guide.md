# User guide

You can use the simulator with outdoor weather only. Indoor measurements are not required for the main workflow. The results describe a modelled greenhouse under your chosen assumptions; uploading weather does not calibrate the model to that location.

Follow [installation](installation.md), open the printed local URL and choose English or Traditional Chinese. The full-model badge must be connected to run a simulation. Interface-only mode permits workbook checks but hides simulation results.

## 1. Weather and dates

Use the bundled Amsterdam/2010 weather to explore, or upload your own outdoor weather workbook.

The **Choose file** button and empty-file message follow the interface language. Switching languages keeps your selected workbook. The file-selection dialog itself follows your browser or operating-system language.

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

Use **Run & compare** to compare automatic control with a daily schedule or with selected devices under MPC. Keep the applied weather, greenhouse, initial state and evaluation limits fixed.

To try MPC, check devices under **Model predictive control (MPC)**, click **Initialize with this selection**, then start the simulation. Unchecked devices stay on the usual rules. See [how the controller chooses its next move](controller-schedules.md#select-equipment-for-mpc).

1. Set the comparison limits and select **Initialize automatic baseline**.
2. Select **Start simulation**. Pause at the duration you want to compare and let the in-flight batch finish.
3. Save the current result as the baseline.
4. Choose the second controller. For a daily schedule, edit the equipment times and select **Apply schedule and initialize**. For MPC, check the devices and select **Initialize with this selection**. Either starts a new run with the same weather and greenhouse.
5. Select **Run to saved baseline duration**.
6. Review temperature, humidity, heating and time outside limits together. Lower energy alone does not establish a better growing strategy.

A saved baseline is not automatically comparable. The existing checks require matching model, weather, greenhouse configuration, initial state, scoring limits and horizon, plus separate runs with unchanged strategies. Changing weather, greenhouse settings or limits means you must create a new matching baseline. This workflow compares control plans, not different greenhouse designs against one fixed baseline.

See the [schedule and comparison guide](controller-schedules.md) for details. [Open greenhouse measurements](greenhouse-measurements.md) are useful for checking predictions against real rooms; they are not required for weather-driven scenarios.

## Navigation and run behaviour

### Save and reproduce a run

On the controller comparison page, pause the model and let the current batch finish. **Save baseline** and **Download run (ZIP)** then use the same displayed step. Download the first run before initializing the second one. Each ZIP contains `timeseries.csv` and `settings.json`. The CSV starts at initialization and includes every accepted 15-minute step, even when playback advances several steps at once. The six requested and applied commands describe the **preceding interval**; those cells are blank on the initial row. An unused schedule carried over from an earlier run is not included.

Give a colleague the ZIP, this simulator version and, for uploaded weather, the **same weather workbook**, if you are allowed to share them. The ZIP contains weather inputs for the simulated intervals as well as greenhouse settings and control history; it does not contain the workbook itself, private paths or a temporary session ID. From an installed checkout:

```console
uv run --locked --extra greenlight python -B scripts/replay_run.py RUN.zip --weather WEATHER.xlsx
```

Omit `--weather` for the built-in Amsterdam scenarios. The script starts its own model, not your live dashboard. It checks the model, effective weather including look-ahead, parameters, initial state, evaluation limits and cost assumptions. It reports exact reproduction only if the entire regenerated CSV has the same SHA-256. A different solver build or platform can produce small numerical differences; a mismatch is not reported as a verified replay.

The settings file dates the start, the planned end and the last exported step in the source clock. An Amsterdam preset uses the clock in its bundled weather file; no timezone offset is inferred. Paused slider edits take effect on the next step, not retroactively in a saved baseline. Unset `GREENLIGHT_GYM_PATH` before replay. Only for an archive recorded from a trusted custom checkout, also supply `--source-checkout PATH`; never select a checkout on someone else's instructions in a ZIP.

**Example:** run `uv run --locked --extra greenlight python -B examples/taipei_heating_replay.py`. The two 48-hour schedules use the included Taipei workbook and the same greenhouse. Only heating from 04:00 to 06:00 changes; both turn it off at 08:00, source local time. Compare heat per square metre, mean indoor temperature and hours outside 18–30°C. These are simulated effects, not a local calibration.

### Moving between pages

Four pages are available: **Weather & dates**, **Greenhouse settings**, **Run & compare**, and **Live simulation**. The guide and next-step links only navigate; they never apply drafts, change model settings or start a run. You can skip uploading weather or editing settings and use the active reference example.

Switching pages does not restart the model or discard unsaved form edits. Start/pause and progress stay available across pages. Browser Back/Forward and direct page links are supported. Reloading is different: unsaved drafts are not guaranteed to survive a reload.

Each step is 15 simulated minutes. Playback speed changes the batch size except in MPC mode, which takes one step per request. Pausing lets an in-flight request finish. Reset starts a new run. If MPC cannot find a command, the last confirmed values stay on screen; **Retry and resume** restarts playback. If the connection or the greenhouse model fails, playback stops and values are hidden.

Each local server owns a shared run. Another tab is not a private session; different people should use separate local instances. The default server binds only to the local computer.

The live chart keeps a short history. For every completed step, use [Download run](#save-and-reproduce-a-run). Replaying the file checks that the model produced the same series, not that it predicted a real greenhouse accurately. See the [model notes](../MODEL_CARD.md) and [API guide](api.md).
