# Changelog

## 2026-10-25

- Made the weather file button and empty-file message follow the interface language without clearing the selected workbook.
- Added a soft light workspace, white cards and dark-green controls, with matching chart colours.
- Added a three-step guide for weather, greenhouse settings and control-plan comparison, showing applied inputs separately from drafts.
- Improved navigation, keyboard focus, numbered headings and greenhouse disclosure alignment in both languages.
- Refreshed the README screenshots and weather-only user guide.
- Kept full-model calculations and comparison safety checks unchanged, including rejection of baselines from a different model version.

## 2026-10-17

- Removed the unused browser climate model and outdated fallback descriptions from the public project.
- Added an hourly NASA POWER collector for eight locations, with source hashes, units, gap checks and leap-year coverage.
- Added fixed-offset weather windows and full-model seasonal checks. Raw downloads and generated reports remain local.
- Tested a bounded, one-parameter fitting example with synthetic data and a separate evaluation year. Real-greenhouse calibration is not yet enabled.
- Added research references and a check that prevents local-only files from entering a release.

## 2026-10-15

- Pinned gl-gym 0.3.2 so the full model and its example weather install with the `greenlight` extra, without a separate source checkout.
- Added `server.py --check-model` to verify installation before opening the dashboard.
- Kept package and custom-source provenance separate and rejected mixed model imports.
- Fixed Excel download content types on Windows and added a regression test.
- Added pinned-package integration checks to cross-platform CI.
- Simplified the public documentation and added a short roadmap.
- Kept local development notes out of the published project and blocked access to them through the simulator server.

## 2026-10-14

- Added dashboard screenshots showing weather uploads, greenhouse settings and equipment schedules.
- Shortened the project introduction and English/Chinese interface descriptions.

## 2026-10-09

- Split the dashboard into simulation, weather, greenhouse settings and controller pages.
- Used 24-hour schedule inputs for the English interface.

## 2026-10-08

- Added daily equipment schedules and comparison with automatic control.
- Added public weather examples for Amsterdam, Almería and Taipei, with source and conversion notes.
