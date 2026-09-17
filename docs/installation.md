# Installation

## Choose a setup

| Setup | Requirements | What works |
| --- | --- | --- |
| Interface and public example | Git, uv, Python 3.12 (uv can provision it) | UI, weather validation, synthetic example |
| Contributor | Above plus Node.js 22+ and npm | Formatting, lint, software regression tests |
| Scientific simulation | Above plus compatible GreenLight-Gym2 source and `greenlight` dependencies | Full-model simulations; separate scientific validation is still required |

This is a source application: run it from its checkout. The existing `python server.py` entry point is retained. A standalone wheel containing the frontend and model is not currently published.

## Windows PowerShell

```powershell
git clone https://github.com/benbenbeatit912002/Greenlight-simulation.git
Set-Location Greenlight-simulation
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --locked --python 3.12
uv run --no-sync python -B examples/validate_weather.py
uv run --no-sync python -B server.py --engine browser
```

## Linux or macOS

```sh
git clone https://github.com/benbenbeatit912002/Greenlight-simulation.git
cd Greenlight-simulation
export PYTHONDONTWRITEBYTECODE=1
export UV_CACHE_DIR="$PWD/.uv-cache"
uv sync --locked --python 3.12
uv run --no-sync python -B examples/validate_weather.py
uv run --no-sync python -B server.py --engine browser
```

Open <http://127.0.0.1:4173/>. Stop with Ctrl+C. If the port is busy, add `--port 4174`. The historical `browser` option means interface-only: it never substitutes approximate simulation values.

For end users who do not need Ruff, `uv sync --locked --no-dev --python 3.12` is sufficient. No Node installation is needed to use the interface.

## Scientific model setup

Set `GREENLIGHT_GYM_PATH` to a compatible source checkout containing `gl_gym/__init__.py`. The application no longer assumes a personal sibling-directory layout. If this variable is absent, full-model startup returns a clear configuration error. Existing users who relied on automatic sibling discovery must set it explicitly.

```powershell
$env:GREENLIGHT_GYM_PATH = 'C:\path\to\GreenLight-Gym2'
uv sync --locked --extra greenlight --python 3.12
uv run --no-sync python -B server.py --engine glgym
```

On Linux/macOS, use `export GREENLIGHT_GYM_PATH="/path/to/GreenLight-Gym2"` with the same remaining commands. The variable is not loaded from `.env` automatically.

The adapter requires the `gl_gym/GreenLightTomato-v0` environment, a 28-state model, six controls, the component API, and the auxiliary equations documented in [MODEL_CARD](../MODEL_CARD.md). A repository with a similar name is not sufficient evidence of compatibility. The current project does not yet distribute a pinned, universally installable upstream source revision. Obtain the exact compatible revision from the maintainer and record its commit and local changes; do not guess a different GreenLight repository.

Built-in runs require the upstream Amsterdam/2010 weather file. Use only data you are authorized to access. The synthetic validation example above does not require that file. Full-model integration tests are opt-in and are not part of the default checks.

## Contributor setup

After Python setup, install the locked frontend development tool:

```sh
npm ci --ignore-scripts --cache .npm-cache
uv run --no-sync python -B scripts/check.py
```

`scripts/check.py` runs the same checks as CI. Dependencies and caches stay in this checkout. See [CONTRIBUTING](../CONTRIBUTING.md) for the formatting commands and review expectations.

## Troubleshooting

- **Model path missing:** set `GREENLIGHT_GYM_PATH` explicitly, or use `--engine browser` for the tutorial and upload validation.
- **Optional dependencies missing:** rerun `uv sync --locked --extra greenlight --python 3.12`. A later sync without this extra can remove optional packages.
- **Import/API mismatch:** confirm the exact upstream revision; do not edit the external model to silence an import error.
- **Asset 404 after updating:** restart the server and reload the page. Browser scripts now live under `frontend/`.
- **Different results between users:** compare source revision, loaded-source hash, configuration, weather, initialization and solver versions before comparing outputs.
