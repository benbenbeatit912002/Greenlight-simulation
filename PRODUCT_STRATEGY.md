# Product Strategy: Explainable Greenhouse Decision Support

Last reviewed: 2026-07-25

## Product decision

Build this project as an **explainable, pre-deployment greenhouse decision-support workbench**. Its job is to help someone compare control strategies and weather scenarios before trying them in a physical greenhouse.

The project should not present itself as a production climate computer, an autonomous grower, or a source of agronomic advice. Those products require greenhouse-specific calibration, live sensor validation, hardware integration, operational safeguards, and accountable expert supervision. A local simulation workbench is a credible and useful side-project-sized entry point.

## What the greenhouse sector needs

| Need | Evidence | Product implication |
| --- | --- | --- |
| Lower energy and resource cost without losing crop performance | The USDA ARS controlled-environment plan identifies energy efficiency, resource-use modelling, profitability, and testing facility upgrades before implementation as explicit needs. | Put energy, CO₂, estimated cost, crop state, and climate limits in the same comparison instead of optimizing one metric in isolation. |
| More labour productivity and better decision support | WUR describes autonomous cultivation as a response to a tight labour market, combining continuous monitoring, control, and data-driven grower support. | Assist human decisions first. Automating explanations and comparisons is safer and more achievable than automating actuators. |
| Scenario testing before real-world changes | USDA ARS calls for decision tools that model crop growth, energy, and resource use, including options for upgrades before implementation. WUR's digital-twin work describes scenario generators that show the consequences of greenhouse and crop settings. | Make controlled A/B experiments the core workflow: establish a baseline, change one strategy, use an equal horizon, and inspect trade-offs. |
| Trustworthy and explainable automation | WUR's LEAP-AI project links explainability to eventual adoption of resource-efficient intelligent control. | Always expose the active engine, assumptions, horizon, scenario, and reasons a comparison is or is not valid. Do not output an unexplained “best strategy.” |
| Calibration and data quality | WUR's tomato digital-twin study calibrated the crop model with sensor data and manual plant observations before using it for predictions and decision support. | Call the current system a simulation, not a live digital twin. Treat sensor ingestion and greenhouse-specific calibration as a later research phase. |

## Initial user and job to be done

The best first user is a greenhouse-control student, researcher, technical adviser, or technically curious grower who wants to answer:

> “Under the same model and simulated duration, what changes when I alter this weather scenario, target, or actuator strategy?”

In less than five minutes, that user should be able to:

1. run a baseline strategy;
2. save its result with model provenance;
3. reset and run a candidate strategy to the same horizon;
4. compare heating, lighting, CO₂, estimated cost, end-state alerts, and fruit dry mass; and
5. understand that the result is a simulated trade-off, not production advice.

This user group is reachable without installing greenhouse hardware or obtaining commercial farm data, which makes it appropriate for a side project. Growers can still review and critique the workflow, but commercial control claims should wait for a calibrated pilot.

## Product promise

**Compare greenhouse control choices before they reach the greenhouse, with visible assumptions and no hidden model substitution.**

The differentiator is not “AI.” It is disciplined experimentation:

- same-horizon comparison;
- explicit engine provenance;
- crop, climate, and resource trade-offs together;
- local-first operation;
- a clearly labelled browser approximation when the scientific model is unavailable; and
- reproducible settings instead of an unexplained recommendation score.

## Scope boundaries

### In scope

- Weather and control scenario exploration.
- Baseline-versus-candidate comparisons.
- Climate-limit visibility.
- Resource, cost, and crop-state summaries.
- Experiment provenance and reproducibility.
- Education, research communication, and pre-deployment discussion.

### Out of scope for now

- Writing commands to real greenhouse actuators.
- Safety-critical alarms or production supervision.
- Crop-health, yield, profit, or energy-saving guarantees.
- Calling the browser approximation a scientific result.
- Calling the simulation a live digital twin before sensor synchronization and greenhouse-specific calibration exist.
- Black-box autonomous optimization without constraints and human-readable explanations.

## Prioritized roadmap

| Priority | Increment | Why it belongs here | Exit condition |
| --- | --- | --- | --- |
| Now | Experiment comparison workbench | Creates immediate decision-support value from the model already present. | A baseline and candidate can be compared only when engine, immutable model provenance, cost assumptions, and horizon are compatible; all provenance remains visible. |
| Now | Model credibility and public collaboration foundation | A public scientific-software project needs explicit evidence boundaries, deterministic tests, review structure, and reproducible automation before adding more features. | A model card separates the two engines and their evidence; comparisons also require matching model/cost versions; CI runs software and diagnostic contracts; issue and pull-request templates request model evidence. |
| Next | Reproducible experiment recipe and report | Makes results reviewable by a supervisor, grower, or collaborator. | Settings, seed, engine, model version, horizon, metrics, and caveats can be reproduced from one saved recipe. |
| Next | Tariff, carbon-intensity, and resource-price scenarios | Energy cost and environmental impact vary over time; fixed assumptions hide the real trade-off. | Every calculated cost or footprint identifies its source, unit, and time basis. |
| Later | Sensitivity and uncertainty analysis | A single deterministic run can create false confidence. | Key parameters can be varied in bounded ensembles and outputs show ranges rather than only point values. |
| Later | Read-only weather and sensor import plus calibration workflow | This is the bridge from simulator to a genuine greenhouse digital twin. | Imported data are validated, provenance is recorded, and calibration quality is reported against held-out observations. |
| Pilot only | Human-approved recommendations or controller integration | Operational value is possible, but safety and accountability dominate. | Greenhouse partner, domain expert, fail-safe design, audit trail, and explicit authorization are in place before any write path exists. |

## Success measures

- A new visitor can state the project's purpose and model limitations after the walkthrough.
- A user cannot mistake the browser approximation for the full GreenLight model.
- A user cannot see numeric A/B deltas when the two runs use different engines or different horizons.
- A user can explain which setting changed and which resource/crop trade-off resulted.
- The same experiment can eventually be reproduced from recorded settings and model provenance.
- Domain reviewers find the workflow useful even when they disagree with the model assumptions.

## Public-project readiness gaps

- The repository owner still needs to choose a software license before broad reuse is invited.
- Scientific claims still need observed-data validation cases with a declared calibration/validation split; the current model card and diagnostic contracts deliberately stop short of predictive-accuracy claims.
- Public deployment should default to the clearly labelled browser approximation unless a managed scientific backend is available.
- A calibrated commercial-greenhouse case study would be stronger evidence than additional interface polish.

The current public foundation now includes a model card, deterministic browser-model contracts, default Python contracts, public-repository CI, contribution and security guidance, issue forms, and a pull-request evidence checklist.

## Sources

- [Wageningen University & Research — Autonomous cultivation in greenhouse horticulture](https://www.wur.nl/en/research/plant/autonomous-cultivation-greenhouse-horticulture)
- [Wageningen University & Research — Towards optimization of tomato cultivation using a digital twin (2025)](https://research.wur.nl/en/publications/towards-optimization-of-tomato-cultivation-using-a-digital-twin/)
- [Wageningen University & Research — A Layered, Explainable Approach to Intelligent Greenhouse Horticulture](https://research.wur.nl/en/projects/a-layered-explainable-approach-to-intelligent-greenhouse-horticul/)
- [USDA Agricultural Research Service — National Program 305 Action Plan 2024–2029](https://www.ars.usda.gov/ARSUserFiles/np305/NP%20305%20Action%20Plan%202024-2029_Finalv2.pdf)

These sources establish sector needs and research direction. The product positioning and roadmap above are project-level inferences, not claims made by the cited organizations.
