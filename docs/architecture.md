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
    provenance.py                Read-only source and array identity
    weather_upload.py            Bounded workbook parsing, independent of the model
    weather_conversion.py        Weather conversion using upstream physical functions
    weather_source.py            Single-year source guard
    run_window.py                Simulation bounds and clock
    greenhouse_config.py         Parameter and initial-state mapping
            |
  explicitly configured read-only GreenLight-Gym2 source
```

## Why keep `backend/`?

The project borrows Scientific Python's tooling and documentation conventions. It retains the existing `backend` package and root `server.py` because users and tests already import them, and the application serves assets from this checkout. Introducing a `src/` installable distribution requires separate packaging of those assets. Moving directories solely to match a template would not provide that capability.

`backend.server` continues to re-export `ApiError` and `SimulatorApplication`; their implementation now lives in `backend.application`. `backend.greenlight_adapter` retains the existing imported constants and fingerprint helpers for compatibility.

## Reset transaction

1. Capture the current run and validate the requested settings.
2. Select a candidate weather environment and apply targets.
3. Reset the candidate with effective parameters.
4. Apply the source clock and initial states; refresh reward limits.
5. Record configuration identity and start the run history.
6. Create a valid snapshot before closing the previous environment.

Failure restores the previous environment when it was preserved. `PreservedRunResetError` communicates this distinction to the application layer. Keep initialization order and numerical expressions stable during structural refactors.

## Boundaries for future changes

- HTTP handlers parse transport; application methods manage revisions and locks; adapters own model state.
- Upload validation never starts a model or persists workbook bytes.
- Formatting belongs to Ruff and Prettier. Scientific units, parameter indices, solver timing and behavior require human review and meaningful tests.
- Prefer named stages and explicit inputs. Avoid helper modules that only hide unrelated state behind generic `utils` names.
- The inactive approximation is isolated in `frontend/legacy/` and is not loaded by the page.
- One server process owns one shared simulation. Browser tabs are protected against stale writes, but users are not given independent sessions. Run separate local server processes/ports for independent simulations. Internet hosting, authentication and multi-user isolation are outside the current design.

See [scientific validation](scientific-validation.md) for what the checks do and do not establish.

## Template references

Project organization and contributor tooling are informed by the [Scientific Python development guide and template](https://github.com/scientific-python/cookie). Research metadata and citation planning are informed by [FAIR Python Cookiecutter](https://github.com/Materials-Data-Science-and-Informatics/fair-python-cookiecutter). These are references for conventions; the application was adapted in place and does not depend on either generator at runtime.
