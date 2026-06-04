"""Shared test fixtures for AI Usage."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))


@pytest.fixture
def codex_payload() -> dict[str, Any]:
    """Return a valid Codex payload."""
    return {
        "schema_version": "1.0",
        "source": "manual_test",
        "source_version": "0.1.0",
        "collected_at": "2026-06-03T18:30:00.000Z",
        "provider": "codex",
        "status": "ok",
        "account_data": {
            "user_id": "user-manual-codex",
            "account_id": "acct-manual-codex",
            "email": "codex.manual@example.com",
        },
        "plan_data": {
            "type": "plus",
        },
        "provider_data": {
            "rate_limit": {
                "allowed": True,
                "limit_reached": False,
                "primary_window": {
                    "used_percent": 12.5,
                    "limit_window_seconds": 18000,
                    "reset_after_seconds": 14400,
                    "reset_at": 1780434415,
                },
                "secondary_window": {
                    "used_percent": 37.2,
                    "limit_window_seconds": 604800,
                    "reset_after_seconds": 428946,
                    "reset_at": 1780846229,
                },
            },
        },
        "error": None,
    }


@pytest.fixture
def ollama_payload() -> dict[str, Any]:
    """Return a valid Ollama Cloud payload."""
    return {
        "schema_version": "1.0",
        "source": "manual_test",
        "source_version": "0.1.0",
        "collected_at": "2026-06-03T18:30:00.000Z",
        "provider": "ollama_cloud",
        "status": "ok",
        "account_data": {
            "username": "ollama-manual",
            "email": "ollama.manual@example.com",
        },
        "plan_data": {
            "type": "free",
        },
        "provider_data": {
            "session_usage": {
                "used_percent": 8.0,
                "reset_at": "2026-06-03T22:00:00.000Z",
            },
            "weekly_usage": {
                "used_percent": 44.4,
                "reset_at": "2026-06-08T00:00:00.000Z",
            },
        },
        "error": None,
    }


@pytest.fixture
def error_payload() -> dict[str, Any]:
    """Return a valid provider error payload without account identity."""
    return {
        "schema_version": "1.0",
        "source": "manual_test",
        "source_version": "0.1.0",
        "collected_at": "2026-06-03T18:30:00.000Z",
        "provider": "codex",
        "status": "not_authenticated",
        "account_data": {},
        "plan_data": {},
        "provider_data": {},
        "error": {
            "code": "not_authenticated",
            "message": "Manual test: user is not logged in",
        },
    }


def clone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of a payload fixture."""
    return deepcopy(payload)
