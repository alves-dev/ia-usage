# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added available percentage sensors for Codex and Ollama Cloud usage windows.
- Added `sensor.last_sample_age` for account staleness tracking.
- Added README tables explaining Home Assistant entities and status/limit
  signals.

### Changed

- Changed Codex reset-after duration sensors to show hours instead of raw
  seconds.
- Renamed Codex primary/secondary window entities to 5-hour and weekly usage
  limit entities.
- Changed percentage sensors to use zero decimal places by default.
- Changed low-level diagnostic entities to be disabled by default.
- Documented the beta status before `v1.0.0` and clarified entity contract
  stability expectations.

## [0.0.1] - 2026-06-03

### Added

- Initial HACS-ready release of AI Usage.
- Added Home Assistant webhook ingestion for normalized AI usage payloads.
- Added support for Codex usage payloads.
- Added support for Ollama Cloud usage payloads.
