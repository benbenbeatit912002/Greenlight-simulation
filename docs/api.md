# Local API

The same-origin API is available only from the local server. CORS is disabled and the server binds to `127.0.0.1` by default:

- `GET /api/status` reports engine availability, model provenance, economic assumptions, and the current revision.
- `POST /api/reset` starts a new run for the selected weather scenario.
- `POST /api/step` advances the simulation with rule-based or manual control.
- `POST /api/weather/preview` validates a raw `.xlsx` body with its standard XLSX MIME type and `X-GreenLight-Upload: 1`. It accepts local same-origin requests, retains at most two converted datasets in memory (the active dataset and one pending dataset), and returns an opaque `weather.weatherId` only when the full model can prepare the Amsterdam-format dataset. Datasets remain in memory until they are replaced or the server process ends; no workbook is persisted. The response sets `conversionReady: true` and `modelReady: false` until `POST /api/reset` succeeds. `POST /api/reset` accepts `scenario: "uploaded"` with that `weatherId` to explicitly start a new run. Invalid data returns HTTP 422 with structured `error.issues`; other failures include 403 (origin), 410 (expired upload), 413 (size), 415 (media type), and 429 (busy).

Every mutation carries a monotonically increasing `revision`. Clients send `expectedRevision` so stale tabs and duplicate requests cannot overwrite newer simulation state. The backend serializes access to the CasADi environment.

Uploaded resets require `runWindow` with exactly four fields: `sourceYear` (integer), `timeConvention` (`UTC` or `source-local-standard`), `startSeconds` and `endSeconds` (integer source-year seconds aligned to 900). Example: `{"sourceYear":2010,"timeConvention":"source-local-standard","startSeconds":33300,"endSeconds":36000}`. Upload responses include `coverage`; snapshots include `runWindow` and `runProgress`. Invalid windows return HTTP 400 `INVALID_WINDOW` before changing the active model or revision. A failed candidate with confirmed rollback returns HTTP 422 `RESET_REJECTED` and preserves the previous accessible run.

| Control | Actuator |
| --- | --- |
| `uBoil` | Boiler heating |
| `uCO2` | CO₂ injection |
| `uThScr` | Thermal screen |
| `uVent` | Roof ventilation |
| `uLamp` | Supplemental lighting |
| `uBlScr` | Blackout screen |

Example manual step:

```json
{
  "steps": 1,
  "mode": "manual",
  "controls": {
    "uBoil": 0.35,
    "uCO2": 0.15,
    "uThScr": 0.4,
    "uVent": 0.05,
    "uLamp": 0.25,
    "uBlScr": 0.0
  },
  "targets": {
    "dayTemp": 21.5,
    "nightTemp": 17.5,
    "co2": 900,
    "maxRh": 82
  },
  "expectedRevision": 1
}
```
