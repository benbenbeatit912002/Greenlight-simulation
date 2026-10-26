# Public synthetic example

Run from the repository root after installing the Python dependencies:

```sh
uv run --no-sync python -B examples/validate_weather.py
```

The example reads `templates/greenlight-weather-template.xlsx`, which contains invented weather, and checks its parsed summary against `expected-weather-summary.json`. It expects 433 records at five-minute intervals covering 36 hours. Exit status is zero and the final line is:

```text
Synthetic weather validation passed. No scientific simulation was run.
```

The example runs offline without the full model. It checks installation and workbook compatibility, not greenhouse predictions. The JSON describes the parsed weather, not simulated crop or climate values.

To try the same example in the interface, start `server.py --engine browser`, open the local URL, and upload the workbook. Validation succeeds; the full model remains unavailable. Follow [installation](../docs/installation.md) to configure a compatible model before running a scientific simulation.
