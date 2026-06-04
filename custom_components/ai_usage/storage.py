"""Storage helpers for dynamic AI Usage accounts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SUPPORTED_PROVIDERS
from .models import AccountState
from .providers.base import parse_datetime

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}.accounts"


class AIUsageStorage:
    """Persist known provider accounts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize storage for one config entry."""
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{entry_id}",
        )

    async def async_load_accounts(self) -> list[AccountState]:
        """Load persisted account metadata."""
        data = await self._store.async_load()
        if not isinstance(data, Mapping):
            return []

        accounts_raw = data.get("accounts")
        if not isinstance(accounts_raw, list):
            return []

        accounts: list[AccountState] = []
        for item in accounts_raw:
            account = _account_from_storage_item(item)
            if account is not None:
                accounts.append(account)
        return accounts

    async def async_save_accounts(self, accounts: Iterable[AccountState]) -> None:
        """Persist known account metadata."""
        payload = {
            "version": STORAGE_VERSION,
            "accounts": [
                account.persisted_metadata()
                for account in sorted(
                    accounts,
                    key=lambda account: (account.provider, account.account_key),
                )
            ],
        }
        await self._store.async_save(payload)


def _account_from_storage_item(item: object) -> AccountState | None:
    """Convert one storage item into account state."""
    if not isinstance(item, Mapping):
        return None

    provider = _string_or_none(item.get("provider"))
    account_key = _string_or_none(item.get("account_key"))
    if provider not in SUPPORTED_PROVIDERS or account_key is None:
        return None

    account_key_quality = _string_or_none(item.get("account_key_quality"))
    account_label = _string_or_none(item.get("account_label"))
    account_data = item.get("account_data")
    plan_data = item.get("plan_data")

    state = AccountState(
        provider=provider,
        account_key=account_key,
        account_key_quality=account_key_quality or "stable",
        account_label=account_label or account_key,
        account_data=dict(account_data) if isinstance(account_data, Mapping) else {},
        plan_data=dict(plan_data) if isinstance(plan_data, Mapping) else {},
        request_count=_int_or_zero(item.get("request_count")),
    )

    last_seen_at = _string_or_none(item.get("last_seen_at"))
    if last_seen_at is not None:
        try:
            state.last_received_at = parse_datetime(last_seen_at)
        except ValueError:
            state.last_received_at = None

    return state


def _string_or_none(value: object) -> str | None:
    """Return a non-empty string or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _int_or_zero(value: object) -> int:
    """Return a non-negative int or zero."""
    if isinstance(value, bool):
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(number, 0)
