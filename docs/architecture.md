# Architecture and reading guide

Start with `server.py`, then `backend/server.py`, `backend/application.py`, and `backend/greenlight_adapter.py`. Browser startup is in `frontend/app.js`; the script order is explicit in `index.html`.

```text
index.html + styles.css
  frontend/app.js                UI state, playback, API requests and comparisons
  frontend/translations.js       English / Traditional Chinese text
  frontend/charts.js             Trend chart drawing
  frontend/climate-upload.js     Workbook upload and time-window controls
  frontend/greenhouse-settings.js Greenhouse form and validation feedback
  frontend/run-window.js         Source-clock calculations
            |
  backend/server.py              HTTP transport, origin checks and public asset allowlist
  backend/application.py         Revision checks, request validation and serialized operations
  backend/greenlight_adapter.py  Scientific environment lifecycle, controls and snapshots
    model_defaults.py            Presets and control names
    model_source.py              Pinned-package discovery or explicit source override
    provenance.py                Read-only source and array identity
    weather_upload.py            Bounded workbook parsing, independent of the model
    weather_conversion.py        Weather conversion using upstream physical functions
    weather_source.py            Single-year source guard
    run_window.py                Simulation bounds and clock
    greenhouse_config.py         Parameter and initial-state mapping
            |
  installed gl-gym 0.3.2 package (or explicit read-only source override)
```

## Reset transaction

1. Capture the current run and validate the requested settings.
2. Select a candidate weather environment and apply targets.
3. Reset the candidate with effective parameters.
4. Apply the source clock and initial states; refresh reward limits.
5. Record configuration identity and start the run history.
6. Create a valid snapshot before closing the previous environment.

Failure restores the previous environment when it was preserved. `PreservedRunResetError` tells the application layer whether the previous run is still available.

## Runtime behavior

- HTTP handlers parse transport; application methods manage revisions and locks; adapters own model state.
- Upload validation never starts a model or persists workbook bytes.
- Browser code displays model results; it does not calculate greenhouse climate.
- One server process owns one shared simulation. Browser tabs are protected against stale writes, but users are not given independent sessions. Run separate local server processes/ports for independent simulations. Internet hosting, authentication and multi-user isolation are outside the current design.

See [scientific validation](scientific-validation.md) for what the checks do and do not establish.
