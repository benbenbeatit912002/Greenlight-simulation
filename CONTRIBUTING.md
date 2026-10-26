# Contributing

Bug reports, documentation fixes and small improvements are welcome. For a larger feature, open an issue first so we can discuss what it should do.

## Setup and checks

Follow the [installation guide](docs/installation.md), then install Node.js 22+ for the frontend checks:

```sh
npm ci --ignore-scripts --cache .npm-cache
uv run --no-sync python -B scripts/check.py
```

This runs formatting, Python and JavaScript tests, and the example workbook check. Full-model integration runs separately; see [the test instructions](docs/scientific-validation.md#optional-integration-suite).

To format changed code:

```sh
uv run --no-sync ruff format backend tests scripts examples server.py
npm run format
```

## Sending a change

- Explain the problem and what you changed. Keep unrelated work in another pull request.
- Add a regression test for changed behavior and include the test results.
- Add a screenshot for a visible UI change. Update the relevant guide and changelog when needed.

If model results change, include a reproducible example with the weather, greenhouse settings, controls, units and time window. Explain which assumptions changed and update the [model notes](MODEL_CARD.md). Keep calibration and evaluation periods separate: passing software tests is not validation against a real greenhouse.

Only share code and data you have permission to publish, and remove credentials or confidential information. This dashboard does not yet have a software license; see the [license status](README.md#model-provenance-and-license-status). The upstream model and weather data have their own terms.

For sensitive security reports, follow [SECURITY.md](SECURITY.md) instead of posting the details in an issue.
