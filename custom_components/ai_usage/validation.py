"""Payload contract validation for AI Usage."""

from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from .const import (
    INGEST_STATUS_INVALID_CONTRACT,
    INGEST_STATUS_MISSING_PROVIDER,
    INGEST_STATUS_PAYLOAD_MUST_BE_OBJECT,
    INGEST_STATUS_UNSUPPORTED_PROVIDER,
    KNOWN_SOURCES,
    PAYLOAD_SCHEMA_VERSION,
    PROVIDER_STATUS_OK,
    PROVIDER_STATUSES,
    SUPPORTED_PROVIDERS,
)
from .models import PayloadEnvelope, ProviderError
from .providers import PROVIDER_HANDLERS, ProviderContractError
from .providers.base import parse_datetime


class PayloadValidationError(ValueError):
    """Raised when a payload cannot be ingested."""

    def __init__(
        self,
        ingest_status: str,
        message: str,
        *,
        provider: str | None = None,
        http_status: int = HTTPStatus.BAD_REQUEST,
    ) -> None:
        """Initialize the validation error."""
        super().__init__(message)
        self.ingest_status = ingest_status
        self.message = message
        self.provider = provider
        self.http_status = http_status


def validate_payload(payload: object) -> PayloadEnvelope:
    """Validate a raw payload object against the v1 contract."""
    if not isinstance(payload, Mapping):
        raise PayloadValidationError(
            INGEST_STATUS_PAYLOAD_MUST_BE_OBJECT,
            "payload must be an object",
        )

    provider = _validate_provider(payload)
    schema_version = _required_string(payload, "schema_version", provider=provider)
    if schema_version != PAYLOAD_SCHEMA_VERSION:
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            f"schema_version must be {PAYLOAD_SCHEMA_VERSION}",
            provider=provider,
        )

    source = _required_string(payload, "source", provider=provider)
    if source not in KNOWN_SOURCES:
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            "source is not supported",
            provider=provider,
        )

    source_version = _required_string(payload, "source_version", provider=provider)
    collected_at_raw = _required_string(payload, "collected_at", provider=provider)
    try:
        collected_at = parse_datetime(collected_at_raw)
    except ValueError as err:
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            "collected_at must be an ISO 8601 datetime with timezone",
            provider=provider,
        ) from err

    status = _required_string(payload, "status", provider=provider)
    if status not in PROVIDER_STATUSES:
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            "status is not supported",
            provider=provider,
        )

    account_data = _required_dict(payload, "account_data", provider=provider)
    plan_data = _required_dict(payload, "plan_data", provider=provider)
    provider_data = _required_dict(payload, "provider_data", provider=provider)
    error = _validate_error(payload.get("error"), status, provider=provider)

    handler = PROVIDER_HANDLERS[provider]
    try:
        handler.validate_provider_data(provider_data, status=status)
    except ProviderContractError as err:
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            str(err),
            provider=provider,
        ) from err

    return PayloadEnvelope(
        schema_version=schema_version,
        source=source,
        source_version=source_version,
        collected_at=collected_at,
        provider=provider,
        status=status,
        account_data=account_data,
        plan_data=plan_data,
        provider_data=provider_data,
        error=error,
    )


def _validate_provider(payload: Mapping[str, Any]) -> str:
    """Validate and normalize the provider field."""
    provider_raw = payload.get("provider")
    if not isinstance(provider_raw, str) or not provider_raw.strip():
        raise PayloadValidationError(
            INGEST_STATUS_MISSING_PROVIDER,
            "provider must be a non-empty string",
        )

    provider = provider_raw.strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise PayloadValidationError(
            INGEST_STATUS_UNSUPPORTED_PROVIDER,
            "provider is not supported",
            provider=provider,
        )
    return provider


def _required_string(
    payload: Mapping[str, Any],
    key: str,
    *,
    provider: str,
) -> str:
    """Return a required non-empty string field."""
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            f"{key} must be a non-empty string",
            provider=provider,
        )
    return value.strip()


def _required_dict(
    payload: Mapping[str, Any],
    key: str,
    *,
    provider: str,
) -> dict[str, Any]:
    """Return a required object field as a dict."""
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            f"{key} must be an object",
            provider=provider,
        )
    return dict(value)


def _validate_error(
    value: object,
    status: str,
    *,
    provider: str,
) -> ProviderError | None:
    """Validate the structured provider error."""
    if status == PROVIDER_STATUS_OK:
        if value is not None:
            raise PayloadValidationError(
                INGEST_STATUS_INVALID_CONTRACT,
                "error must be null when status is ok",
                provider=provider,
            )
        return None

    if not isinstance(value, Mapping):
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            "error must be an object when status is not ok",
            provider=provider,
        )

    code = value.get("code")
    message = value.get("message")
    if not isinstance(code, str) or not code.strip():
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            "error.code must be a non-empty string",
            provider=provider,
        )
    if not isinstance(message, str) or not message.strip():
        raise PayloadValidationError(
            INGEST_STATUS_INVALID_CONTRACT,
            "error.message must be a non-empty string",
            provider=provider,
        )

    return ProviderError(code=code.strip(), message=message.strip())
