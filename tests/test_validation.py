"""Tests for AI Usage payload contract validation."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from conftest import clone_payload
import pytest

from custom_components.ai_usage.const import (
    INGEST_STATUS_INVALID_CONTRACT,
    INGEST_STATUS_MISSING_PROVIDER,
    INGEST_STATUS_PAYLOAD_MUST_BE_OBJECT,
    INGEST_STATUS_UNSUPPORTED_PROVIDER,
)
from custom_components.ai_usage.validation import (
    PayloadValidationError,
    validate_payload,
)

OLLAMA_WEEKLY_USED_PERCENT = 44.4


def _assert_validation_error(
    payload: object,
    ingest_status: str,
    message_fragment: str,
) -> None:
    with pytest.raises(PayloadValidationError) as exc_info:
        validate_payload(payload)

    assert exc_info.value.ingest_status == ingest_status
    assert exc_info.value.http_status == HTTPStatus.BAD_REQUEST
    assert message_fragment in exc_info.value.message


def test_valid_codex_payload(codex_payload: dict[str, Any]) -> None:
    """A valid Codex payload should produce a payload envelope."""
    envelope = validate_payload(codex_payload)

    assert envelope.provider == "codex"
    assert envelope.status == "ok"
    assert envelope.error is None
    assert envelope.account_data["account_id"] == "acct-manual-codex"
    assert envelope.collected_at.isoformat() == "2026-06-03T18:30:00+00:00"


def test_valid_ollama_payload(ollama_payload: dict[str, Any]) -> None:
    """A valid Ollama Cloud payload should produce a payload envelope."""
    envelope = validate_payload(ollama_payload)

    assert envelope.provider == "ollama_cloud"
    assert envelope.status == "ok"
    assert (
        envelope.provider_data["weekly_usage"]["used_percent"]
        == OLLAMA_WEEKLY_USED_PERCENT
    )


def test_payload_must_be_object() -> None:
    """Payload must be a JSON object."""
    _assert_validation_error(
        [],
        INGEST_STATUS_PAYLOAD_MUST_BE_OBJECT,
        "payload must be an object",
    )


def test_missing_provider(codex_payload: dict[str, Any]) -> None:
    """provider is required."""
    payload = clone_payload(codex_payload)
    payload.pop("provider")

    _assert_validation_error(
        payload,
        INGEST_STATUS_MISSING_PROVIDER,
        "provider must be a non-empty string",
    )


def test_provider_must_be_string(codex_payload: dict[str, Any]) -> None:
    """provider must be a string."""
    payload = clone_payload(codex_payload)
    payload["provider"] = 42

    _assert_validation_error(
        payload,
        INGEST_STATUS_MISSING_PROVIDER,
        "provider must be a non-empty string",
    )


def test_unsupported_provider(codex_payload: dict[str, Any]) -> None:
    """Unsupported providers should be rejected."""
    payload = clone_payload(codex_payload)
    payload["provider"] = "unknown"

    _assert_validation_error(
        payload,
        INGEST_STATUS_UNSUPPORTED_PROVIDER,
        "provider is not supported",
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "2.0", "schema_version must be 1.0"),
        ("source", "unknown_source", "source is not supported"),
        ("account_data", [], "account_data must be an object"),
        ("plan_data", [], "plan_data must be an object"),
        ("provider_data", [], "provider_data must be an object"),
    ],
)
def test_invalid_envelope_fields(
    codex_payload: dict[str, Any],
    field: str,
    value: object,
    message: str,
) -> None:
    """Envelope field validation should return invalid_contract."""
    payload = clone_payload(codex_payload)
    payload[field] = value

    _assert_validation_error(payload, INGEST_STATUS_INVALID_CONTRACT, message)


def test_status_ok_rejects_error(codex_payload: dict[str, Any]) -> None:
    """Successful payloads must not include error."""
    payload = clone_payload(codex_payload)
    payload["error"] = {"code": "unexpected", "message": "Unexpected"}

    _assert_validation_error(
        payload,
        INGEST_STATUS_INVALID_CONTRACT,
        "error must be null",
    )


def test_error_status_requires_error(codex_payload: dict[str, Any]) -> None:
    """Error payloads must include structured error."""
    payload = clone_payload(codex_payload)
    payload["status"] = "rate_limited"
    payload["error"] = None

    _assert_validation_error(
        payload,
        INGEST_STATUS_INVALID_CONTRACT,
        "error must be an object",
    )


def test_codex_requires_rate_limit(codex_payload: dict[str, Any]) -> None:
    """Codex success payloads must include rate_limit."""
    payload = clone_payload(codex_payload)
    payload["provider_data"] = {}

    _assert_validation_error(
        payload,
        INGEST_STATUS_INVALID_CONTRACT,
        "provider_data.rate_limit must be an object",
    )


def test_codex_rejects_invalid_percent(codex_payload: dict[str, Any]) -> None:
    """Codex percentages must be within 0-100."""
    payload = clone_payload(codex_payload)
    payload["provider_data"]["rate_limit"]["primary_window"]["used_percent"] = 101

    _assert_validation_error(
        payload,
        INGEST_STATUS_INVALID_CONTRACT,
        "used_percent must be <= 100",
    )


def test_ollama_rejects_invalid_reset_at(ollama_payload: dict[str, Any]) -> None:
    """Ollama reset_at must be ISO 8601."""
    payload = clone_payload(ollama_payload)
    payload["provider_data"]["weekly_usage"]["reset_at"] = "not-a-date"

    _assert_validation_error(
        payload,
        INGEST_STATUS_INVALID_CONTRACT,
        "provider_data.weekly_usage.reset_at must be an ISO 8601 datetime",
    )
