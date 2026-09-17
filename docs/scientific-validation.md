# Scientific validation and reproducibility

Three kinds of evidence must remain distinct:

| Evidence | Default checks? | Meaning |
| --- | --- | --- |
| Software contracts | Yes | Request validation, clocks, configuration mapping, upload boundaries, UI assets and regression behavior |
| Full-model integration | No; explicit opt-in | A compatible upstream model initializes and steps correctly through this adapter |
| Independent predictive validation | Not yet completed here | Agreement with held-out greenhouse observations under documented conditions |

The public synthetic workbook demonstrates software compatibility. It is not measured weather and cannot establish predictive accuracy. Legacy browser-model tests do not validate the active scientific model.

## Record a scientific run

Record the application commit and uncommitted changes, upstream source commit and loaded-source fingerprint, dependency lock, parameters, initial states, weather file identity, requested time window, source clock, seed and solver configuration. Retain the exact authorized input file; a hash alone cannot reconstruct it. Preserve full output series when available instead of relying on a screenshot or the short live chart.

The current adapter reports much of this identity in status/snapshots. A complete export/replay bundle is still M4 in [IMPLEMENTATION_PLAN](../IMPLEMENTATION_PLAN.md); this structural refactor does not claim to implement it.

## Before reporting predictive performance

Define calibration and held-out periods before fitting. Keep held-out observations out of parameter selection. Align timestamps, units, initial states and historical actuator inputs. Report error metrics, failed runs, assumptions and uncertainty; distinguish default-parameter runs from calibrated runs. The current application does not implement the M5 fitting workflow.

## Optional integration suite

After configuring an explicitly authorized model/data source:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUN_GREENLIGHT_INTEGRATION = '1'
uv run --no-sync python -B -m unittest discover -s tests -p 'test_greenlight_integration.py' -v
```

On Linux/macOS, set those environment variables with `export`. The default `scripts/check.py` deliberately disables these tests and never assumes access to a contributor's external research data. Read [MODEL_CARD](../MODEL_CARD.md) for the authoritative model scope and limitations.
