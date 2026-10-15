# Roadmap

This project helps people try local weather and equipment settings in the GreenLight greenhouse model. It is for learning and research, not for controlling a real greenhouse.

## Available now

- Upload weather in the supported Excel format and check its contents before running.
- Choose simulation dates within the available weather coverage.
- Set greenhouse dimensions, equipment capacities and starting conditions.
- Run the full GreenLight-Gym2 model with automatic, manual or daily scheduled controls.
- Compare runs with matching weather, greenhouse settings and duration.
- Use the dashboard in English or Traditional Chinese.
- Install the pinned public model and example weather with the `greenlight` extra; no separate source checkout is needed.

The simulator stops if the full model is unavailable. It does not switch to a simplified model.

## Next

### Save and repeat a simulation

Export the complete results and the settings used to produce them. A repeatable run needs the weather file as well as the model version, parameters, initial conditions and control settings. Full time-series export and recipe import are not available yet.

### Make installation easier

The model dependency is now pinned and has a command-line startup check. Next, improve first-run error messages and consider a desktop launcher. A project software license still needs to be selected before broad redistribution is invited.

### Expand greenhouse settings

Add more equipment and cover options only when they can be mapped to documented model parameters. Material names such as glass or polycarbonate should refer to tested parameter sets, not just labels.

## Later: calibration against measurements

Uploading a country's weather does not calibrate a greenhouse. Calibration needs indoor measurements, known greenhouse geometry, equipment details and the controls actually used during the measurement period.

A future calibration workflow should fit a small, justified set of parameters and check the results against a separate period of measurements. It should report errors and uncertainty, not promise better results for every location.

## Limits

There is no live sensor connection, hardware control, automatic regional calibration or validated prediction guarantee. Independent predictive validation remains unfinished. See the [model card](../MODEL_CARD.md) and [validation guide](scientific-validation.md) for the current evidence and assumptions.
