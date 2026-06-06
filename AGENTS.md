# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Home Assistant custom integration for AI usage telemetry.
Source code lives in `custom_components/ai_usage/`. Provider-specific logic is in
`custom_components/ai_usage/providers/`, while shared ingestion, validation,
identity, storage, runtime, and entity setup code lives beside it. Integration
assets are stored under `custom_components/ai_usage/brand/` and
`custom_components/ai_usage/provider_images/`.

Tests live in `tests/` and documentation lives in `docs/`. Keep payload and
sensor contract changes aligned with the relevant files in `docs/`.

Keep `CHANGELOG.md` updated for every user-visible behavior change, entity
contract change, provider change, compatibility change, or release preparation.
When changing the integration version, update every version source in the same
change, including `custom_components/ai_usage/const.py`,
`custom_components/ai_usage/manifest.json`, docs, badges, and changelog entries
when applicable.

## Build, Test, and Development Commands

- `uv sync` installs the pinned runtime and development dependencies.
- `uv run pytest` runs the full test suite configured by `pyproject.toml`.
- `uv run pytest tests/test_validation.py` runs one focused test module.
- `uv run ruff check .` runs linting and import-order checks.
- `uv run ruff format .` formats Python files using the repository style.
- `scripts/validate-homeassistant-version.sh` checks the declared Home Assistant
  compatibility metadata.

## Coding Style & Naming Conventions

Python targets 3.14 and uses Ruff with an 88-character line length. Prefer
explicit type hints, small pure helpers for payload parsing, and `from __future__
import annotations` in Python modules. Use `snake_case` for functions, variables,
fixtures, and module names; use `PascalCase` for classes.

Keep provider identifiers stable and lowercase, such as `codex` and
`ollama_cloud`. Avoid raw email values in unique IDs; follow the identity helpers
and decisions documented in `docs/account-stable-id-decision.md`.

## Testing Guidelines

Tests use `pytest` with `pytest-asyncio` in auto mode. Name test files
`test_*.py`, and prefer descriptive test names that state the expected behavior.
Use shared payload fixtures from `tests/conftest.py` and clone mutable payloads
before modifying them in a test.

Add or update tests for validation rules, provider payload handling, identity
behavior, and ingestion state changes. Run `uv run pytest` before opening a pull
request.

## Commit & Pull Request Guidelines

Recent commits use short imperative subjects, for example `Add version validation
script and update compatibility documentation`. Keep subjects specific and under
about 72 characters when practical.

Pull requests should include a concise summary, affected provider or integration
areas, test results, and links to related issues. Include screenshots only when
the change affects Home Assistant UI entities, icons, or displayed strings.

## Security & Configuration Tips

Treat webhook IDs as secrets. Do not commit real account identifiers, email
addresses, tokens, or Home Assistant instance URLs. Use synthetic payload data in
tests and documentation examples.
