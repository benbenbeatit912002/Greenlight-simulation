# Public weather examples for model robustness checks

The three new Excel examples use [NASA POWER hourly data](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/), a gridded satellite/reanalysis product—not measurements at a greenhouse. They follow the existing nine-column Amsterdam upload contract. Their provenance sidecars record the full query URL, units, source metadata, retrieval time, and raw-response SHA-256.

| Workbook | Coordinates | Source-clock range | Fixed UTC offset | Suggested 72-hour run |
| --- | --- | --- | --- | --- |
| [Amsterdam winter](../templates/weather-amsterdam-winter.xlsx) | 52.37, 4.90 | 2023-01-15 00:00 to 2023-01-19 00:00 | +01:00 | Jan 15 00:00 to Jan 18 00:00 |
| [Almería summer](../templates/weather-almeria-summer.xlsx) | 36.84, -2.46 | 2023-07-15 00:00 to 2023-07-19 00:00 | +01:00 | Jul 15 00:00 to Jul 18 00:00 |
| [Taipei summer](../templates/weather-taipei-summer.xlsx) | 25.03, 121.57 | 2023-07-15 00:00 to 2023-07-19 00:00 | +08:00 | Jul 15 00:00 to Jul 18 00:00 |

Select **source year 2023** and **source-local-standard** when applying one of these files. Almería uses standard time, not summer daylight-saving time. Each file contains 1,153 records spanning 96 hours, leaving 24 hours beyond the suggested run (more than the required 12-hour model look-ahead). No dates or missing weather are extrapolated.

## Conversion assumptions

- Explicitly request UTC from NASA, then convert to the stated fixed local-standard offset.
- Hourly source values are held on a five-minute grid; this is a formatting/resampling decision, not observed five-minute variability. Gaps and fill values are rejected.
- Convert downward shortwave and longwave radiation from NASA MJ/hr to W/m² by multiplying by 1,000,000/3,600.
- Derive an effective sky temperature from downward longwave irradiance with the Stefan–Boltzmann relationship and emissivity convention 1. This is a derived radiative temperature, not measured sky air temperature.
- Outdoor CO₂ is a fixed **400 ppm assumption**; NASA did not provide this measurement.
- Wind is NASA's 2 m wind speed; no height adjustment is made.
- The `??` column stores cloud fraction and is ignored by this simulator. The source year and seconds column determine the model clock.
- The existing adapter still uses upstream `soilTempNl` for soil temperature. Uploading tropical weather does not calibrate the soil model, structure, crop, or equipment for that location.

## Other candidate sources

| Source | Suitable use | Conversion caution |
| --- | --- | --- |
| [NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/) | Global reproducible example weather; also used by an upstream Gym2 weather helper | Explicit clock/units and derived sky temperature; not site observations |
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) | Historical reanalysis scenarios | Check variables, units, radiation interval convention, data-use terms, and fixed timezone; not downloaded in this task |
| [EnergyPlus weather / EPW](https://energyplus.net/weather) | Building/greenhouse weather scenarios; supported in GreenLight platform input tooling | Distinguish typical meteorological year from an actual recorded year; convert EPW hour-ending conventions; not downloaded in this task |

Sources were inspected on 2026-10-08. The reproducible fetch script is `examples/fetch_public_weather.py`; it uses a free public weather endpoint, no API key and no AI service. All download output stays inside this repository.

## Measured numerical test outcome, 2026-10-08

Each scenario used the same default greenhouse, seed 42, initial-state settings, weather, and limits (15–34 °C, 50–85% RH) for both strategies. Each run lasted 72 hours / 288 physical steps. Scheduled runs were repeated with batches of 48 steps and matched the one-step results exactly.

| Scenario | Automatic mean T (°C) | Scheduled mean T (°C) | Automatic heat (kWh/m²) | Scheduled heat (kWh/m²) | Automatic / scheduled time outside either limit (h) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Amsterdam winter | 18.84 | 8.53 | 7.936 | 2.886 | 19.25 / 72.00 |
| Almería summer | 27.73 | 32.54 | 0.302 | 2.886 | 43.50 / 65.25 |
| Taipei summer | 30.41 | 34.18 | 0.032 | 2.886 | 53.75 / 68.25 |

All nine runs completed with finite model states, no solver truncation, bounded applied controls, non-decreasing cumulative resources, and exact end times. **The example schedule is not a good operating strategy:** Taipei's scheduled maximum reached 44.64 °C and Amsterdam remained below the chosen temperature range. The automatic controller also exceeded limits in these scenarios. Default initialization transients are included; no spin-up was removed.

These results demonstrate numerical execution and comparison integrity for these specific inputs. They do not prove physical stability, controller optimality, model accuracy, regional calibration, energy savings, crop safety, or field readiness. Raw responses, converted CSV/JSON, and full result snapshots remain in `.runtime/controller-weather/` after running the scripts; that runtime directory is intentionally not published to Git.
