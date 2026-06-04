"""Tests for AI Usage ingestion service."""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from conftest import clone_payload
import pytest

from custom_components.ai_usage.const import (
    INGEST_STATUS_ACCOUNT_UNIDENTIFIED,
    INGEST_STATUS_INVALID_CONTRACT,
    INGEST_STATUS_OK,
)
from custom_components.ai_usage.ingestion import AIUsageIngestionService
from custom_components.ai_usage.models import (
    AccountIdentity,
    IngestContext,
    IngestResult,
    PayloadEnvelope,
)


class FakeRuntime:
    """Runtime test double for the ingestion service."""

    def __init__(self) -> None:
        """Initialize captured calls."""
        self.applied_samples: list[
            tuple[PayloadEnvelope, AccountIdentity, IngestContext]
        ] = []
        self.recorded_results: list[
            tuple[IngestResult, IngestContext, PayloadEnvelope | None]
        ] = []
        self.unscoped_errors: list[tuple[PayloadEnvelope, IngestContext, str, str]] = []
        self.created_account = True

    async def async_apply_account_sample(
        self,
        envelope: PayloadEnvelope,
        identity: AccountIdentity,
        context: IngestContext,
    ) -> bool:
        """Capture account samples."""
        self.applied_samples.append((envelope, identity, context))
        return self.created_account

    async def async_record_ingest_result(
        self,
        result: IngestResult,
        context: IngestContext,
        envelope: PayloadEnvelope | None = None,
    ) -> None:
        """Capture ingest results."""
        self.recorded_results.append((result, context, envelope))

    async def async_record_unscoped_error(
        self,
        envelope: PayloadEnvelope,
        context: IngestContext,
        *,
        error_code: str,
        message: str,
    ) -> None:
        """Capture unscoped errors."""
        self.unscoped_errors.append((envelope, context, error_code, message))


@pytest.fixture
def received_at() -> datetime:
    """Return a stable received_at timestamp."""
    return datetime(2026, 6, 3, 18, 31, tzinfo=UTC)


async def test_ingest_valid_codex_payload(
    codex_payload: dict[str, Any],
    received_at: datetime,
) -> None:
    """A valid account payload should be applied and recorded as ok."""
    runtime = FakeRuntime()
    service = AIUsageIngestionService(runtime)  # type: ignore[arg-type]

    result = await service.async_ingest_payload(
        codex_payload,
        received_at=received_at,
        transport="test",
    )

    assert result.ok is True
    assert result.http_status == HTTPStatus.OK
    assert result.ingest_status == INGEST_STATUS_OK
    assert result.provider == "codex"
    assert result.account_key is not None
    assert result.created_account is True
    assert result.provider_status == "ok"

    assert len(runtime.applied_samples) == 1
    envelope, identity, context = runtime.applied_samples[0]
    assert envelope.provider == "codex"
    assert identity.id_kind == "account_id"
    assert context.transport == "test"
    assert context.webhook_id is None

    assert len(runtime.recorded_results) == 1
    recorded_result, recorded_context, recorded_envelope = runtime.recorded_results[0]
    assert recorded_result is result
    assert recorded_context.transport == "test"
    assert recorded_envelope is envelope


async def test_ingest_valid_payload_with_webhook_context(
    ollama_payload: dict[str, Any],
    received_at: datetime,
) -> None:
    """Webhook-specific context should be captured without being required."""
    runtime = FakeRuntime()
    service = AIUsageIngestionService(runtime)  # type: ignore[arg-type]

    result = await service.async_ingest_payload(
        ollama_payload,
        received_at=received_at,
        transport="webhook",
        context={"webhook_id": "ia-tool-usage", "request_remote": "127.0.0.1"},
    )

    assert result.ok is True
    assert len(runtime.applied_samples) == 1
    _envelope, identity, context = runtime.applied_samples[0]
    assert identity.id_kind == "email"
    assert context.transport == "webhook"
    assert context.webhook_id == "ia-tool-usage"
    assert context.request_remote == "127.0.0.1"


async def test_invalid_contract_is_recorded(
    codex_payload: dict[str, Any],
    received_at: datetime,
) -> None:
    """Invalid contracts should not apply account samples."""
    runtime = FakeRuntime()
    service = AIUsageIngestionService(runtime)  # type: ignore[arg-type]
    payload = clone_payload(codex_payload)
    payload["account_data"] = []

    result = await service.async_ingest_payload(
        payload,
        received_at=received_at,
        transport="test",
    )

    assert result.ok is False
    assert result.http_status == HTTPStatus.BAD_REQUEST
    assert result.ingest_status == INGEST_STATUS_INVALID_CONTRACT
    assert result.provider == "codex"
    assert result.message == "account_data must be an object"
    assert runtime.applied_samples == []
    assert len(runtime.recorded_results) == 1
    assert runtime.recorded_results[0][2] is None


async def test_payload_without_identity_updates_unscoped_error(
    error_payload: dict[str, Any],
    received_at: datetime,
) -> None:
    """Valid payloads without identity should update unscoped error state."""
    runtime = FakeRuntime()
    service = AIUsageIngestionService(runtime)  # type: ignore[arg-type]

    result = await service.async_ingest_payload(
        error_payload,
        received_at=received_at,
        transport="test",
    )

    assert result.ok is False
    assert result.http_status == HTTPStatus.ACCEPTED
    assert result.ingest_status == INGEST_STATUS_ACCOUNT_UNIDENTIFIED
    assert result.provider == "codex"
    assert result.provider_status == "not_authenticated"
    assert result.message == "Manual test: user is not logged in"

    assert runtime.applied_samples == []
    assert len(runtime.unscoped_errors) == 1
    envelope, context, error_code, message = runtime.unscoped_errors[0]
    assert envelope.provider == "codex"
    assert context.transport == "test"
    assert error_code == "not_authenticated"
    assert message == "Manual test: user is not logged in"

    assert len(runtime.recorded_results) == 1
    assert runtime.recorded_results[0][2] is envelope
