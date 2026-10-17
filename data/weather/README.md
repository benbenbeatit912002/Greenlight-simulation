# Weather collection

Hourly weather for eight example locations in 2023 and 2024. The source is [NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/). A location is a point query, not a country's entire climate and not a greenhouse weather station.

| Location | Country | Latitude | Longitude |
| --- | --- | ---: | ---: |
| Amsterdam | Netherlands | 52.37 | 4.90 |
| Almeria | Spain | 36.84 | -2.46 |
| Taipei | Taiwan | 25.03 | 121.57 |
| Tokyo | Japan | 35.68 | 139.69 |
| Davis, California | United States | 38.54 | -121.74 |
| Leamington, Ontario | Canada | 42.05 | -82.60 |
| Melbourne | Australia | -37.81 | 144.96 |
| Nairobi | Kenya | -1.29 | 36.82 |

## Download

From the repository root:

```sh
uv run --no-sync python -B examples/collect_weather.py
```

No account, API key or paid service is used. Requests are sequential, with a 45-second timeout and an 8 MiB response limit. A repeated run reuses checksum-verified downloads. It refuses to overwrite changed files. Use `--site taipei-tw --years 2024` for a smaller collection, or a new `--collection` name for a fresh download. Edit [sites.json](sites.json) to add a location and its fixed standard UTC offset.

All files stay together here:

```text
data/weather/
  sites.json
  downloads/nasa-power-2023-2024-v1/
    <site>/<year>/source.json    Unmodified NASA response
    <site>/<year>/request.json   Query URL, retrieval time and SHA-256
    <site>/<year>/hourly.csv     Standardized hourly values
    <site>/<year>/manifest.json Units, conversion, checks and provenance
    collection-<timestamp>.json Download successes and failures
  reports/                     Local model tests and experiment reports
```

Downloads and generated reports are ignored by Git. GitHub contains the collector, site list and documentation, so a clone stays small. These directories are not exposed by the simulator's HTTP server.

## What the records mean

Each CSV has one UTC hour per row: timestamp, air temperature (°C), relative humidity (%), 2 m wind speed (m/s), shortwave and longwave irradiance (W/m²), derived sky temperature (°C) and cloud fraction (0–1). These are hourly means from gridded satellite/reanalysis products. They are not five-minute observations. See NASA's [methodology](https://power.larc.nasa.gov/docs/methodology/) for spatial resolution and uncertainty.

- Radiation is converted from MJ/hr to W/m² using `1e6 / 3600`.
- Sky temperature is derived from longwave irradiance using the Stefan–Boltzmann relation with emissivity convention 1.
- No CO₂ measurements are downloaded. Model checks explicitly assume 400 ppm.
- No missing hours, sentinel values or non-finite values are filled. Incomplete years fail validation.
- Raw records use UTC. Model checks convert them to each site's fixed local-standard offset from `sites.json`, without daylight saving. Use `--clock UTC` to keep the model clock in UTC instead. Do not label UTC data as local time without conversion.
- Model checks still use the upstream Netherlands soil-temperature function and default greenhouse/crop parameters. A location change does not change or calibrate them.

The annual CSV is for analysis, not a direct dashboard upload. The dashboard expects a bounded, five-minute, nine-column Excel file. `backend.weather_archive.greenlight_window` prepares a 36-hour to 30-day window by holding hourly means on a five-minute grid, with an explicit fixed UTC offset. It rejects gaps and source-clock cross-year windows. This expansion adds no observed detail. The existing three ready-to-upload workbooks remain under `templates/`.

## Checks and first collection

The 2026-10-17 collection contains 16 complete site-years: 8,760 hours for 2023 and 8,784 for leap-year 2024, totaling **140,352 rows**. No values were imputed. The response reports NASA POWER Hourly API v2.10.3. Source queries, dates and hashes are recorded with each dataset.

After installing the `greenlight` extra, run:

```sh
uv run --no-sync python -B scripts/check_weather_archive.py
```

This checks January 15–18 and July 15–18 of each year, with an extra day of weather context. All 32 runs use the full model, default greenhouse, automatic controller and seed 42. **30 completed; Davis July 2023 and July 2024 failed integration**, after 11 and 61 hours respectively with local-standard time. Both also failed in a separate UTC-clock run. The solver reported non-finite Jacobian/convergence failures; their physical/numerical cause is not yet isolated. No source data or scientific equations were altered to hide these failures.

The command returns nonzero if any run fails. Completed runs may still exceed temperature or humidity limits. This is a numerical test, not evidence of accurate or safe greenhouse operation. A targeted rerun is `python -B scripts/check_weather_archive.py --site davis-us --months 7`.

Use the same `--collection <name>` for the collector, weather checks and synthetic calibration demo when working with a fresh collection. Reports record that selection. Missing or damaged datasets are reported as failed cases without discarding earlier results. Model failures after reset retain the model, configuration, weather and initial-state fingerprints, along with the number of completed steps.

For future modelling, keep whole periods separate, for example 2023 for development and 2024 for held-out evaluation. Weather alone supplies no indoor target values or historical actuator inputs. See [calibration requirements and experiments](../../docs/calibration.md).

## Attribution

Data source: NASA Langley Research Center's POWER project, funded by NASA's Earth Science Division. Service: POWER Hourly API v2.10.3, accessed 2026-10-17. Preserve the source metadata and follow NASA's [referencing and redistribution guidance](https://power.larc.nasa.gov/docs/referencing/). NASA requests acknowledgement and notification of published use or redistribution. No NASA endorsement is implied. This project does not assign a new license to the source data.
