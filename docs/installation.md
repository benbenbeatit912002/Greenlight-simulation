# Installation

## Choose a setup

| Setup | Requirements | What works |
| --- | --- | --- |
| Full simulator (recommended) | Git, uv, Python 3.12 | Full-model simulations using the pinned `gl-gym` package and its example weather |
| Interface only | Same tools, without the `greenlight` extra | UI, weather validation, synthetic example; no simulation values |
| Contributor | Above plus Node.js 22+ and npm | Formatting, lint, software and model integration tests |

Run the application from the cloned project folder. Setup installs the model automatically; no second repository is needed. There is no standalone installer yet. Installation needs internet access, but normal simulation and bundled examples run offline.

## Windows PowerShell

```powershell
git clone https://github.com/benbenbeatit912002/Greenlight-simulation.git
Set-Location Greenlight-simulation
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$PWD\.runtime\python"
New-Item -ItemType Directory -Force .runtime\tmp | Out-Null
$env:TEMP = "$PWD\.runtime\tmp"
$env:TMP = $env:TEMP
uv sync --locked --extra greenlight --python 3.12
uv run --no-sync python -B server.py --check-model
uv run --no-sync python -B server.py
```

## Linux or macOS

```sh
git clone https://github.com/benbenbeatit912002/Greenlight-simulation.git
cd Greenlight-simulation
export PYTHONDONTWRITEBYTECODE=1
export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python"
mkdir -p .runtime/tmp
export TMPDIR="$PWD/.runtime/tmp"
uv sync --locked --extra greenlight --python 3.12
uv run --no-sync python -B server.py --check-model
uv run --no-sync python -B server.py
```

Open <http://127.0.0.1:4173/>. Stop with Ctrl+C. If the port is busy, add `--port 4174`. The check command must print **Full GreenLight model check passed**; it does not leave a server running. A failed check exits with code 2. The regular server also refuses to start if the full model cannot initialize.

For end users who do not need Ruff, add `--no-dev` to the sync command. Keep `--extra greenlight` on later syncs or uv can remove the optional model. No Node installation is needed to use the simulator.

## What is installed?

The `greenlight` extra pins [gl-gym 0.3.2](https://pypi.org/project/gl-gym/0.3.2/). `uv.lock` records its artifact hashes and supporting dependency versions. Everything is installed in this checkout's `.venv`; the commands above also keep downloads, temporary files and any uv-provisioned Python inside this checkout. Existing system Python can be reused.

The package includes `gl_gym/data/weather/Amsterdam/2010.csv` for the built-in scenarios. You can use it immediately or upload your own Excel weather. Uploads remain in memory. Reinforcement-learning training tools are not needed or installed.

The dependency declares AGPL-3.0-or-later and includes its license. Attribution is in [CITATION.md](../CITATION.md). The wrapper's software license remains undecided; separate installation does not waive upstream license terms.

## Advanced: use a source checkout

Normally leave `GREENLIGHT_GYM_PATH` unset. If it is set, it takes precedence over the installed package and must point to a compatible checkout containing `gl_gym/__init__.py`. An invalid override fails explicitly; it does not silently select another model. Source imports are read-only and bytecode writing is disabled.

```powershell
$env:GREENLIGHT_GYM_PATH = 'C:\path\to\GreenLight-Gym2'
uv sync --locked --extra greenlight --python 3.12
uv run --no-sync python -B server.py --check-model
uv run --no-sync python -B server.py
```

On Linux/macOS, use `export GREENLIGHT_GYM_PATH="/path/to/GreenLight-Gym2"` with the same remaining commands. The variable is not loaded from `.env` automatically.

The adapter requires the `gl_gym/GreenLightTomato-v0` environment, a 28-state model, six controls, 208 parameters, the component API and the auxiliary equations documented in [MODEL_CARD](../MODEL_CARD.md). Custom source revisions are not covered by the pinned-package guarantee. Their provenance is labeled as a source checkout, not as the installed package. Restart Python when changing model sources.

To return to the packaged model, run `Remove-Item Env:GREENLIGHT_GYM_PATH -ErrorAction SilentlyContinue` in PowerShell, `set GREENLIGHT_GYM_PATH=` in CMD, or `unset GREENLIGHT_GYM_PATH` in a POSIX shell. This clears the variable only for that terminal; it does not remove any files.

## Interface-only use

Omit the extra with `uv sync --locked --python 3.12`, then run `uv run --no-sync python -B server.py --engine browser`. The historical `browser` name means interface-only: simulation results are unavailable and there is no approximation fallback. Run `uv run --no-sync python -B examples/validate_weather.py` to validate the 433-row synthetic workbook without loading a model.

## Contributor setup

After Python setup, install the locked frontend development tool:

```sh
npm ci --ignore-scripts --cache .npm-cache
uv run --no-sync python -B scripts/check.py
```

`scripts/check.py` runs the same software checks as CI; full-model integration is separate. See [CONTRIBUTING](../CONTRIBUTING.md) for formatting and test commands.

## Troubleshooting

- **Model not installed or wrong version:** run the locked sync command with `--extra greenlight`, then repeat `--check-model`.
- **Optional dependencies missing:** rerun `uv sync --locked --extra greenlight --python 3.12`. A later sync without this extra can remove optional packages.
- **Import/API mismatch or unexpected source:** unset an old `GREENLIGHT_GYM_PATH` to use the tested package. A custom model revision may not provide the API this adapter needs.
- **Asset 404 after updating:** restart the server and reload the page. Browser scripts now live under `frontend/`.
- **Different results between users:** compare source revision, loaded-source hash, configuration, weather, initialization and solver versions before comparing outputs.
