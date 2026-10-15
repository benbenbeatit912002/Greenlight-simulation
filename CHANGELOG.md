# Changelog

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
