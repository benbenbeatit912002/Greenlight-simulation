# GreenLight 2 Greenhouse Simulator

An interactive greenhouse simulation and decision-support workbench connecting a bilingual browser interface to the GreenLight-Gym2 scientific model. Explore greenhouse settings, weather, control strategies, climate and resource use.

[![CI](https://github.com/benbenbeatit912002/Greenlight-simulation/actions/workflows/ci.yml/badge.svg)](https://github.com/benbenbeatit912002/Greenlight-simulation/actions/workflows/ci.yml)

**Status:** research/education prototype. The public interface uses the full scientific model or hides results when it is unavailable. Independent predictive validation, full-series result export and parameter calibration are not yet complete.

## Acknowledgements and citation

This work builds on **GreenLight**, developed by **David Katzin and collaborators**, and uses the **GreenLight-Gym2** implementation by **Bart van Laatum and contributors**. We gratefully acknowledge their scientific and software contributions.

- **Original GreenLight model:** David Katzin, Simon van Mourik, Frank Kempkes, and Eldert J. van Henten (2020). *GreenLight – An open source model for greenhouses with supplemental lighting: Evaluation of heat requirements under LED and HPS lamps*. Biosystems Engineering, 194, 61–81. [Paper](https://doi.org/10.1016/j.biosystemseng.2020.03.010) · [Original repository](https://github.com/davkat1/GreenLight).
- **GreenLight-Gym / GreenLight-Gym2:** Bart van Laatum, Eldert J. van Henten, and Sjoerd Boersma (2025). *GreenLight-Gym: Reinforcement learning benchmark environment for control of greenhouse production systems*. IFAC-PapersOnLine, 59(23), 437–442. [Paper](https://doi.org/10.1016/j.ifacol.2025.11.827) · [Upstream repository](https://github.com/BartvLaatum/GreenLight-Gym2).

This repository contributes the browser interface and local integration layer; the underlying greenhouse model and upstream environment are credited to their original authors. Please cite the relevant upstream publications when using this work in research. See [CITATION.md](CITATION.md) for BibTeX and attribution details.

## Quick start

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```sh
git clone https://github.com/benbenbeatit912002/Greenlight-simulation.git
cd Greenlight-simulation
uv sync --locked --python 3.12 --cache-dir .uv-cache
uv run --no-sync python -B examples/validate_weather.py
uv run --no-sync python -B server.py --engine browser
```

Open <http://127.0.0.1:4173/>. This setup displays the interface and validates the bundled synthetic weather without accessing a model checkout or private research data. No Node.js installation is needed to use the app. The example expects 433 records covering 36 hours and reports a successful validation.

To run actual simulations, install the `greenlight` extra and explicitly set `GREENLIGHT_GYM_PATH` to a compatible source checkout. Follow [the full Windows/Linux/macOS installation guide](docs/installation.md). The model source is read-only and is not bundled here; its exact compatible version remains a separate setup requirement.

## What you can do

- Use English or Traditional Chinese controls and explanations.
- Validate an Excel weather workbook, select source-clock simulation dates and review supported ranges.
- Configure supported greenhouse dimensions, equipment and initial conditions.
- Run the full model with automatic or manual controls at fixed 15-minute steps.
- Compare compatible baseline/candidate runs at matching horizons.

Each server process owns one shared simulation. For independent work, different users run separate local instances. This release is not a hosted multi-user service or production greenhouse controller.

## Find the right guide

| Goal | Read |
| --- | --- |
| Install on another computer | [Installation and troubleshooting](docs/installation.md) |
| Operate the interface | [User guide](docs/user-guide.md) |
| Run the public example | [Synthetic example](examples/README.md) |
| Prepare weather or settings | [Weather input](docs/weather-input.md), [greenhouse configuration](GREENHOUSE_CONFIGURATION.md) |
| Understand or modify code | [Architecture](docs/architecture.md), [contributing](CONTRIBUTING.md) |
| Call the local API | [API contract](docs/api.md) |
| Interpret scientific results | [Model card](MODEL_CARD.md), [validation](docs/scientific-validation.md) |
| See planned capabilities | [Implementation plan](IMPLEMENTATION_PLAN.md), [product direction](PRODUCT_STRATEGY.md) |

## Repository map

```text
server.py           Stable local startup entry point
backend/            HTTP, application operations and scientific adapter
frontend/           Browser controls, translations, charts and upload UI
frontend/legacy/    Inactive approximation retained for regression tests
index.html          Public page and explicit browser-script load order
styles.css          Interface styling
docs/               Installation, user, architecture and scientific guides
examples/           Public validation example and expected summary
templates/          Synthetic Excel weather template
tests/              Software contracts and opt-in full-model integration
scripts/check.py    Shared local/CI quality-check entry point
worklogs/           English project change records
```

## Contributing and checks

After the Python setup, install Node.js 22+ for development:

```sh
npm ci --ignore-scripts --cache .npm-cache
uv run --no-sync python -B scripts/check.py
```

Checks include Ruff formatting/lint/complexity, Prettier formatting, JavaScript syntax, Python and JavaScript contracts, and the public example. Default checks do not run external-model integration or establish scientific accuracy. See [CONTRIBUTING](CONTRIBUTING.md) before submitting a focused pull request. Report sensitive issues through [SECURITY](SECURITY.md).

## Model provenance and license status

GreenLight-Gym2 supplies the scientific model; this repository supplies the local interface and adapter. Model attribution and references are in [CITATION.md](CITATION.md) and [MODEL_CARD](MODEL_CARD.md). Source, parameter and weather fingerprints help explain which model/configuration produced a run.

No software license has been selected for this wrapper yet. Public visibility does not grant broad reuse rights. The owner must confirm the license and citation authors before those metadata can be finalized; upstream model and data permissions remain separate.

## Change records

[Worklog index](worklogs/index.html) records implementation and verification. Existing root startup remains supported; browser assets moved to `frontend/`, and full-model startup now requires explicit `GREENLIGHT_GYM_PATH` instead of automatic sibling discovery.
