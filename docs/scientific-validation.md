# Scientific validation and reproducibility

Three kinds of evidence must remain distinct:

| Evidence | Default checks? | Meaning |
| --- | --- | --- |
| Software contracts | Yes | Request validation, clocks, configuration mapping, upload boundaries, UI assets and regression behavior |
| Full-model integration | No; explicit opt-in | A compatible upstream model initializes and steps correctly through this adapter |
| Independent predictive validation | Not yet completed here | Agreement with held-out greenhouse observations under documented conditions |

The public synthetic workbook demonstrates software compatibility. It is not measured weather and cannot establish predictive accuracy.

## Record a scientific run

Record the application commit and uncommitted changes, upstream source commit and loaded-source fingerprint, dependency lock, parameters, initial states, weather file identity, requested time window, source clock, seed and solver configuration. Retain the exact authorized input file; a hash alone cannot reconstruct it. Preserve full output series when available instead of relying on a screenshot or the short live chart.

The current adapter reports much of this identity in status/snapshots. A complete export/replay bundle is not yet available; see the [roadmap](roadmap.md).

## Before reporting predictive performance

Define calibration and held-out periods before fitting. Keep held-out observations out of parameter selection. Align timestamps, units, initial states and historical actuator inputs. Report error metrics, failed runs, assumptions and uncertainty; distinguish default-parameter runs from calibrated runs. Real-data fitting is not enabled in the dashboard. The [synthetic fitting example](calibration.md) tests the optimizer with generated targets only.

## Optional integration suite

After installing the pinned public model with `uv sync --locked --extra greenlight --python 3.12`:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUN_GREENLIGHT_INTEGRATION = '1'
uv run --no-sync python -B server.py --check-model
uv run --no-sync python -B -m unittest discover -s tests -p 'test_greenlight_integration.py' -v
```

On Linux/macOS, set those environment variables with `export`. Leave `GREENLIGHT_GYM_PATH` unset to test the installed package. The default `scripts/check.py` disables these tests; CI runs them separately against the pinned dependency. Custom model revisions need their own compatibility checks. Read [the model notes](../MODEL_CARD.md) for assumptions and limitations.
