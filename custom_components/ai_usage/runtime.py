"""Runtime state and webhook transport for AI Usage."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
import logging
from typing import Any

from aiohttp.web import Request, Response, json_response
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    EVENT_WEBHOOK_RECEIVED,
    INGEST_STATUS_INVALID_JSON,
    INGEST_STATUS_OK,
    account_update_signal,
    accounts_changed_signal,
    integration_update_signal,
    provider_update_signal,
)
from .images import async_register_provider_static_paths, provider_entity_picture
from .ingestion import AIUsageIngestionService
from .models import (
    AccountIdentity,
    AccountState,
    IngestContext,
    IngestResult,
    IntegrationState,
    PayloadEnvelope,
    ProviderMetadata,
)
from .providers import PROVIDER_HANDLERS
from .storage import AIUsageStorage

_LOGGER = logging.getLogger(__name__)

AccountCallback = Callable[[AccountState], None]


class AIUsageRuntime:
    """Hold runtime state and process webhook requests."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the runtime."""
        self.hass = hass
        self.entry = entry
        self.integration_state = IntegrationState()
        self.accounts: dict[tuple[str, str], AccountState] = {}
        self.ingestion_service = AIUsageIngestionService(self)
        self._storage = AIUsageStorage(hass, entry.entry_id)
        self._account_sensor_callbacks: list[AccountCallback] = []
        self._account_binary_sensor_callbacks: list[AccountCallback] = []

    async def async_setup(self) -> None:
        """Load runtime state required before platforms are set up."""
        await async_register_provider_static_paths(self.hass)

        for account in await self._storage.async_load_accounts():
            key = (account.provider, account.account_key)
            self.accounts[key] = account

        self._update_known_account_counts()

    async def async_unload(self) -> None:
        """Release runtime callbacks."""
        self._account_sensor_callbacks.clear()
        self._account_binary_sensor_callbacks.clear()

    @property
    def account_states(self) -> tuple[AccountState, ...]:
        """Return known account states."""
        return tuple(
            self.accounts[key]
            for key in sorted(self.accounts, key=lambda item: (item[0], item[1]))
        )

    def get_account_state(self, provider: str, account_key: str) -> AccountState:
        """Return state for a provider account."""
        return self.accounts[(provider, account_key)]

    def get_provider_metadata(self, provider: str) -> ProviderMetadata:
        """Return display metadata for a provider."""
        return PROVIDER_HANDLERS[provider].metadata

    def get_provider_entity_picture(self, provider: str) -> str | None:
        """Return the local provider image URL if the file is registered."""
        return provider_entity_picture(self.hass, provider)

    def async_register_account_sensor_callback(
        self,
        callback: AccountCallback,
    ) -> Callable[[], None]:
        """Register a callback used by the sensor platform for new accounts."""
        self._account_sensor_callbacks.append(callback)

        def _remove() -> None:
            self._account_sensor_callbacks.remove(callback)

        return _remove

    def async_register_account_binary_sensor_callback(
        self,
        callback: AccountCallback,
    ) -> Callable[[], None]:
        """Register a callback used by the binary sensor platform for accounts."""
        self._account_binary_sensor_callbacks.append(callback)

        def _remove() -> None:
            self._account_binary_sensor_callbacks.remove(callback)

        return _remove

    async def async_apply_account_sample(
        self,
        envelope: PayloadEnvelope,
        identity: AccountIdentity,
        context: IngestContext,
    ) -> bool:
        """Create or update the account state represented by a payload."""
        key = (identity.provider, identity.account_key)
        account = self.accounts.get(key)
        created_account = account is None
        before_metadata = _metadata_compare(account) if account is not None else None

        if account is None:
            account = AccountState(
                provider=identity.provider,
                account_key=identity.account_key,
                account_key_quality=identity.account_key_quality,
                account_label=identity.label,
            )
            self.accounts[key] = account

        account.apply(envelope, identity, context.received_at)
        self._update_known_account_counts()

        after_metadata = _metadata_compare(account)
        if created_account or before_metadata != after_metadata:
            await self._storage.async_save_accounts(self.account_states)

        if created_account:
            self._notify_new_account(account)
            async_dispatcher_send(
                self.hass,
                accounts_changed_signal(self.entry.entry_id),
            )

        async_dispatcher_send(
            self.hass,
            account_update_signal(
                self.entry.entry_id,
                identity.provider,
                identity.account_key,
            ),
        )
        async_dispatcher_send(
            self.hass,
            provider_update_signal(self.entry.entry_id, identity.provider),
        )
        return created_account

    async def async_record_unscoped_error(
        self,
        envelope: PayloadEnvelope,
        context: IngestContext,
        *,
        error_code: str,
        message: str,
    ) -> None:
        """Record a valid provider payload that cannot be tied to an account."""
        state = self.integration_state
        state.last_unscoped_error = error_code
        state.last_unscoped_error_message = message
        state.last_unscoped_error_provider = envelope.provider
        state.last_unscoped_error_received_at = context.received_at
        state.last_unscoped_error_source = envelope.source
        state.last_unscoped_error_source_version = envelope.source_version
        state.last_unscoped_error_collected_at = envelope.collected_at

    async def async_record_ingest_result(
        self,
        result: IngestResult,
        context: IngestContext,
        envelope: PayloadEnvelope | None = None,
    ) -> None:
        """Update parent device state after an ingestion attempt."""
        state = self.integration_state
        state.last_ingest_status = result.ingest_status
        state.last_ingest_error_message = (
            result.message if result.ingest_status != INGEST_STATUS_OK else None
        )
        if context.transport == "webhook":
            state.last_webhook_received_at = context.received_at

        if envelope is not None:
            state.last_source = envelope.source
            state.last_source_version = envelope.source_version
            state.last_schema_version = envelope.schema_version
            state.last_provider = envelope.provider
        elif result.provider is not None:
            state.last_provider = result.provider

        state.last_account_key = result.account_key
        self._update_known_account_counts()

        async_dispatcher_send(self.hass, integration_update_signal(self.entry.entry_id))
        if context.transport == "webhook":
            self.hass.bus.async_fire(
                EVENT_WEBHOOK_RECEIVED,
                {
                    "entry_id": self.entry.entry_id,
                    "provider": result.provider,
                    "account_key": result.account_key,
                    "ingest_status": result.ingest_status,
                    "provider_status": result.provider_status,
                    "created_account": result.created_account,
                    "known_accounts": state.known_accounts,
                },
            )

    async def async_handle_webhook(
        self,
        hass: HomeAssistant,
        webhook_id: str,
        request: Request,
    ) -> Response:
        """Handle an incoming webhook payload."""
        received_at = datetime.now(UTC)
        request_remote = request.remote

        try:
            payload: Any = await request.json()
        except Exception as err:
            _LOGGER.warning("Invalid AI Usage webhook JSON on %s: %s", webhook_id, err)
            result = IngestResult(
                ok=False,
                http_status=HTTPStatus.BAD_REQUEST,
                ingest_status=INGEST_STATUS_INVALID_JSON,
                message="invalid_json",
            )
            await self.async_record_ingest_result(
                result,
                IngestContext(
                    transport="webhook",
                    received_at=received_at,
                    webhook_id=webhook_id,
                    request_remote=request_remote,
                ),
            )
            return json_response(result.as_response(), status=result.http_status)

        result = await self.ingestion_service.async_ingest_payload(
            payload,
            received_at=received_at,
            transport="webhook",
            context={
                "webhook_id": webhook_id,
                "request_remote": request_remote,
            },
        )
        return json_response(result.as_response(), status=result.http_status)

    def _notify_new_account(self, account: AccountState) -> None:
        """Ask registered platforms to add entities for a new account."""
        for callback in tuple(self._account_sensor_callbacks):
            callback(account)
        for callback in tuple(self._account_binary_sensor_callbacks):
            callback(account)

    def _update_known_account_counts(self) -> None:
        """Update account count fields on the parent integration state."""
        counts: dict[str, int] = {}
        for provider, _account_key in self.accounts:
            counts[provider] = counts.get(provider, 0) + 1
        self.integration_state.known_accounts = len(self.accounts)
        self.integration_state.known_accounts_by_provider = counts


def _metadata_compare(account: AccountState | None) -> dict[str, Any] | None:
    """Return persisted fields that should trigger a storage save."""
    if account is None:
        return None

    data = account.persisted_metadata()
    data.pop("request_count", None)
    data.pop("last_seen_at", None)
    return data
