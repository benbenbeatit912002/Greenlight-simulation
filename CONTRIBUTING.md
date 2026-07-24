# Contributing

Thank you for helping make GreenLight Simulation more reproducible, understandable, and useful. Contributions are welcome as reviewable GitHub pull requests.

## Before you start

- Read `README.md`, `MODEL_CARD.md`, `PRODUCT_STRATEGY.md`, and `AGENTS.md`.
- Search existing issues and pull requests before opening a duplicate.
- Keep the product positioned as pre-deployment decision support, not a production controller.
- Do not submit private greenhouse data, thesis material, credentials, unpublished results, or source copied from a repository whose license does not permit redistribution.
- This repository does not yet have a software license. Public visibility alone does not grant reuse rights; the owner must choose and add a license before broad redistribution is invited.

## Local setup

The browser-only development environment has no third-party runtime dependency:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync --locked --python 3.12
```

Start the local browser model:

```powershell
& '.\.venv\Scripts\python.exe' -B .\server.py --engine browser
```

Open <http://127.0.0.1:4173/>.

The optional full GreenLight-Gym2 setup is documented in `README.md`. Treat the external source checkout as read-only. Keep virtual environments, caches, logs, and generated outputs inside this repository, set `PYTHONDONTWRITEBYTECODE=1`, and invoke Python with `-B`.

## Make a focused change

1. Create a short branch from the current default branch.
2. Keep one pull request focused on one user problem or model-quality question.
3. Explain the intended user, expected behavior, assumptions, and limitations.
4. Add or update tests for behavior that changed.
5. Update documentation and `MODEL_CARD.md` when model meaning, provenance, economics, or validation status changes.
6. Add a standalone English HTML entry in `worklogs/` and place its link first in `worklogs/index.html`.

Avoid committing `.venv`, `.uv-cache`, `.runtime`, logs, local data, Python bytecode, editor files, or secrets.

## Model-change requirements

A model change needs more evidence than a visual UI change. Include:

- the process or decision-support need being changed;
- the engine affected (`greenlight-gym2`, browser approximation, or both);
- units, valid ranges, timestep, initialization, and cost assumptions;
- a deterministic reproduction case;
- at least one normal case and one boundary or failure case;
- a test of the expected response direction or a comparison against observations;
- limitations and possible counterexamples; and
- a statement saying whether the change is calibrated, validated, or only software-tested.

Do not tune a parameter on validation data and then report the same data as independent evidence. Separate calibration and held-out evaluation periods and record dataset provenance.

## Run the checks

JavaScript syntax and browser-model contracts:

```powershell
node --check .\simulator-engine.js
node --check .\app.js
node --test .\tests\browser_model_contract.test.js
```

Default Python suite:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_*.py' -v
```

Optional full-model integration:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUN_GREENLIGHT_INTEGRATION = '1'
& '.\.venv\Scripts\python.exe' -B -m unittest tests.test_greenlight_integration -v
```

Only run the optional test when the open-source dependencies are installed locally and the external GreenLight-Gym2 source can remain read-only.

## Pull request expectations

The pull request should contain:

- a concise problem statement and outcome;
- screenshots for visible UI changes;
- model and safety impact;
- exact validation commands and results;
- documentation/work-log updates;
- known limitations and follow-up work; and
- confirmation that no protected research material or secret was included.

Maintainers may ask for a smaller scope, stronger validation, clearer model labels, or an independent review before merging.

## Reporting problems

Use the structured GitHub issue forms for software bugs, model-validation evidence, and feature proposals. Follow `SECURITY.md` for vulnerabilities or sensitive reports.
