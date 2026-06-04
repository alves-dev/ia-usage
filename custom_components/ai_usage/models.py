"""Models used by the AI Usage integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from typing import Any

from .const import (
    INGEST_STATUS_OK,
    PROVIDER_NAMES,
    PROVIDER_STATUS_OK,
)


@dataclass(frozen=True, slots=True)
class ProviderError:
    """Structured provider error from a payload."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PayloadEnvelope:
    """Validated payload envelope."""

    schema_version: str
    source: str
    source_version: str
    collected_at: datetime
    provider: str
    status: str
    account_data: dict[str, Any]
    plan_data: dict[str, Any]
    provider_data: dict[str, Any]
    error: ProviderError | None


@dataclass(frozen=True, slots=True)
class AccountIdentity:
    """Resolved account identity."""

    provider: str
    account_key: str
    account_key_quality: str
    id_kind: str
    id_value: str
    label: str


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    """Display metadata for a provider account device."""

    provider: str
    provider_name: str
    manufacturer: str
    model: str
    configuration_url: str
    entity_picture: str | None = None


@dataclass(slots=True)
class AccountState:
    """Mutable state for one provider account."""

    provider: str
    account_key: str
    account_key_quality: str
    account_label: str
    account_data: dict[str, Any] = field(default_factory=dict)
    plan_data: dict[str, Any] = field(default_factory=dict)
    provider_data: dict[str, Any] = field(default_factory=dict)
    status: str | None = None
    error: ProviderError | None = None
    source: str | None = None
    source_version: str | None = None
    schema_version: str | None = None
    collected_at: datetime | None = None
    last_received_at: datetime | None = None
    request_count: int = 0

    @property
    def has_sample(self) -> bool:
        """Return whether this account has an in-memory payload sample."""
        return self.status is not None and self.last_received_at is not None

    @property
    def device_key(self) -> str:
        """Return the stable account device key suffix."""
        return f"{self.provider}:{self.account_key}"

    def apply(
        self,
        envelope: PayloadEnvelope,
        identity: AccountIdentity,
        received_at: datetime,
    ) -> None:
        """Apply a validated envelope sample."""
        self.account_key_quality = identity.account_key_quality
        self.account_label = identity.label
        self.account_data = dict(envelope.account_data)
        self.plan_data = dict(envelope.plan_data)
        self.provider_data = dict(envelope.provider_data)
        self.status = envelope.status
        self.error = envelope.error
        self.source = envelope.source
        self.source_version = envelope.source_version
        self.schema_version = envelope.schema_version
        self.collected_at = envelope.collected_at
        self.last_received_at = received_at
        self.request_count += 1

    def persisted_metadata(self) -> dict[str, Any]:
        """Return small metadata safe to persist in Home Assistant storage."""
        data: dict[str, Any] = {
            "provider": self.provider,
            "account_key": self.account_key,
            "account_key_quality": self.account_key_quality,
            "account_label": self.account_label,
            "account_data": dict(self.account_data),
            "plan_data": dict(self.plan_data),
            "provider_name": PROVIDER_NAMES.get(self.provider, self.provider),
            "request_count": self.request_count,
        }
        if self.last_received_at is not None:
            data["last_seen_at"] = self.last_received_at.isoformat()
        return data


@dataclass(slots=True)
class IntegrationState:
    """Mutable integration-level state for the parent device."""

    last_ingest_status: str = INGEST_STATUS_OK
    last_ingest_error_message: str | None = None
    last_webhook_received_at: datetime | None = None
    last_source: str | None = None
    last_source_version: str | None = None
    last_schema_version: str | None = None
    last_provider: str | None = None
    last_account_key: str | None = None
    known_accounts: int = 0
    known_accounts_by_provider: dict[str, int] = field(default_factory=dict)
    last_unscoped_error: str = "none"
    last_unscoped_error_message: str | None = None
    last_unscoped_error_provider: str | None = None
    last_unscoped_error_received_at: datetime | None = None
    last_unscoped_error_source: str | None = None
    last_unscoped_error_source_version: str | None = None
    last_unscoped_error_collected_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Result of ingesting one payload."""

    ok: bool
    http_status: int
    ingest_status: str
    provider: str | None = None
    account_key: str | None = None
    created_account: bool = False
    message: str | None = None
    provider_status: str | None = None

    @classmethod
    def success(
        cls,
        *,
        provider: str,
        account_key: str,
        created_account: bool,
        provider_status: str = PROVIDER_STATUS_OK,
    ) -> IngestResult:
        """Build a successful ingest result."""
        return cls(
            ok=True,
            http_status=HTTPStatus.OK,
            ingest_status=INGEST_STATUS_OK,
            provider=provider,
            account_key=account_key,
            created_account=created_account,
            provider_status=provider_status,
        )

    def as_response(self) -> dict[str, Any]:
        """Return the JSON response payload for a webhook request."""
        response: dict[str, Any] = {
            "ok": self.ok,
            "ingest_status": self.ingest_status,
            "provider": self.provider,
            "account_key": self.account_key,
            "created_account": self.created_account,
        }
        if self.message is not None:
            response["message"] = self.message
        if self.provider_status is not None:
            response["provider_status"] = self.provider_status
        return response


@dataclass(frozen=True, slots=True)
class IngestContext:
    """Metadata about the transport that initiated ingestion."""

    transport: str
    received_at: datetime
    webhook_id: str | None = None
    request_remote: str | None = None


def account_label_from_data(
    account_data: Mapping[str, Any],
    fallback: str,
) -> str:
    """Return the preferred human-readable account label."""
    for key in ("email", "username", "account_id", "user_id"):
        value = account_data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return fallback
