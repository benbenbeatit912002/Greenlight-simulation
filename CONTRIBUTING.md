# Contributing

Open an issue to discuss a change, or send a focused pull request with tests.

## Before you start

- Read [README.md](README.md), [MODEL_CARD.md](MODEL_CARD.md), and the [roadmap](docs/roadmap.md).
- Search existing issues and pull requests before opening a duplicate.
- Describe the project as a simulation for learning and research, not a production controller.
- Do not submit private greenhouse data, thesis material, credentials, unpublished results, or source copied from a repository whose license does not permit redistribution.
- This repository does not yet have a software license. Public visibility alone does not grant reuse rights; the owner must choose and add a license before broad redistribution is invited.

## Local setup

Follow [installation](docs/installation.md), including the contributor setup. Python dependencies are locked in `uv.lock`; Prettier is locked in `package-lock.json`. Node.js is only a development dependency.

```sh
uv sync --locked --python 3.12 --cache-dir .uv-cache
npm ci --ignore-scripts --cache .npm-cache
uv run --no-sync python -B server.py --engine browser
```

This minimal setup serves the interface and upload validation. For simulation, sync with `--extra greenlight` and run `server.py --check-model`, then `server.py`. The pinned public package supplies the model and default weather. `GREENLIGHT_GYM_PATH` is an optional advanced source override; never edit a collaborator's model or research files while working on this wrapper.

## Make a focused change

1. Create a short branch from the current default branch.
2. Keep one pull request focused on one user problem or model-quality question.
3. Explain the intended user, expected behavior, assumptions, and limitations.
4. Add or update tests for behavior that changed.
5. Update documentation and `MODEL_CARD.md` when model meaning, provenance, economics, or validation status changes.
6. Add a short entry to `CHANGELOG.md` for user-facing changes.

Avoid committing `.venv`, `.uv-cache`, `.runtime`, logs, local data, Python bytecode, editor files, or secrets.

## Model-change requirements

A model change needs more evidence than a visual UI change. Include:

- the process or decision-support need being changed;
- the affected GreenLight equations or adapter behavior;
- units, valid ranges, timestep, initialization, and cost assumptions;
- a deterministic reproduction case;
- at least one normal case and one boundary or failure case;
- a test of the expected response direction or a comparison against observations;
- limitations and possible counterexamples; and
- a statement saying whether the change is calibrated, validated, or only software-tested.

Do not tune a parameter on validation data and then report the same data as independent evidence. Separate calibration and held-out evaluation periods and record dataset provenance.

## Run the checks

```sh
uv run --no-sync python -B scripts/check.py
```

The shared runner disables external-model integration, keeps temporary files inside this repository, and fails on the first failed check. CI runs it on Windows, Linux and macOS. Cross-platform CI results are established only after the workflow runs on GitHub.

Apply formatting explicitly:

```sh
uv run --no-sync ruff format backend tests scripts examples server.py
uv run --no-sync ruff check backend tests scripts examples server.py --fix
npm run format
```

The Python cyclomatic-complexity limit is 20. New code should use focused functions with explicit inputs and documented units. A score below the limit does not by itself make code understandable. Keep source readable; generated/minified distribution assets should not replace the maintained source.

For model execution checks, follow [the opt-in integration instructions](docs/scientific-validation.md). CI runs these separately with the pinned public package and its weather on Windows, Linux and macOS. Custom external sources still require explicit authorization. Passing software checks is not evidence of greenhouse prediction accuracy.

## Pull request expectations

The pull request should contain:

- a concise problem statement and outcome;
- screenshots for visible UI changes;
- model and safety impact;
- exact validation commands and results;
- documentation and changelog updates;
- known limitations and follow-up work; and
- confirmation that no protected research material or secret was included.

Maintainers may ask for a smaller scope, stronger validation, clearer model labels, or an independent review before merging.

## Reporting problems

Use the structured GitHub issue forms for software bugs, model-validation evidence, and feature proposals. Follow `SECURITY.md` for vulnerabilities or sensitive reports.
