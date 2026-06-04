"""Binary sensor platform for AI Usage."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    INGEST_STATUS_OK,
    INTEGRATION_NAME,
    INTEGRATION_VERSION,
    PROVIDER_BINARY_SENSOR_KEYS,
    PROVIDER_STATUS_OK,
    account_update_signal,
    integration_update_signal,
)
from .models import AccountState, IntegrationState
from .runtime import AIUsageRuntime


@dataclass(frozen=True, kw_only=True)
class AIUsageIntegrationBinarySensorDescription(BinarySensorEntityDescription):
    """Describes an integration-level AI Usage binary sensor."""

    value_fn: Callable[[IntegrationState], bool | None]
    attributes_fn: Callable[[IntegrationState], dict[str, Any]] = lambda _state: {}


@dataclass(frozen=True, kw_only=True)
class AIUsageAccountBinarySensorDescription(BinarySensorEntityDescription):
    """Describes an account-level AI Usage binary sensor."""

    value_fn: Callable[[AccountState], bool | None]
    attributes_fn: Callable[[AccountState], dict[str, Any]] = lambda _state: {}


INTEGRATION_BINARY_SENSOR_DESCRIPTIONS: tuple[
    AIUsageIntegrationBinarySensorDescription, ...
] = (
    AIUsageIntegrationBinarySensorDescription(
        key="webhook_problem",
        name="Webhook problem",
        icon="mdi:webhook",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda state: state.last_ingest_status != INGEST_STATUS_OK,
        attributes_fn=lambda state: _drop_none(
            {
                "last_ingest_status": state.last_ingest_status,
                "last_error_message": state.last_ingest_error_message,
            }
        ),
    ),
)


COMMON_ACCOUNT_BINARY_SENSOR_DESCRIPTIONS: tuple[
    AIUsageAccountBinarySensorDescription, ...
] = (
    AIUsageAccountBinarySensorDescription(
        key="problem",
        name="Problem",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda state: (
            state.status != PROVIDER_STATUS_OK if state.has_sample else None
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "status": state.status,
                "error_code": state.error.code if state.error is not None else None,
                "error_message": (
                    state.error.message if state.error is not None else None
                ),
            }
        ),
    ),
)


CODEX_BINARY_SENSOR_DESCRIPTIONS: tuple[AIUsageAccountBinarySensorDescription, ...] = (
    AIUsageAccountBinarySensorDescription(
        key="allowed",
        name="Allowed",
        icon="mdi:check-decagram-outline",
        value_fn=lambda state: _codex_rate_limit_bool(state, "allowed"),
        attributes_fn=lambda state: _drop_none(
            {
                "limit_reached": _codex_rate_limit_bool(state, "limit_reached"),
                "primary_window_used_percent": _codex_window_number(
                    state,
                    "primary_window",
                    "used_percent",
                ),
                "secondary_window_used_percent": _codex_window_number(
                    state,
                    "secondary_window",
                    "used_percent",
                ),
            }
        ),
    ),
    AIUsageAccountBinarySensorDescription(
        key="limit_reached",
        name="Limit reached",
        icon="mdi:speedometer-slow",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda state: _codex_rate_limit_bool(state, "limit_reached"),
        attributes_fn=lambda state: _drop_none(
            {"allowed": _codex_rate_limit_bool(state, "allowed")}
        ),
    ),
)

PROVIDER_BINARY_SENSOR_DESCRIPTIONS = {
    "codex": CODEX_BINARY_SENSOR_DESCRIPTIONS,
    "ollama_cloud": (),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AI Usage binary sensors."""
    runtime: AIUsageRuntime = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            AIUsageIntegrationBinarySensor(entry, runtime, description)
            for description in INTEGRATION_BINARY_SENSOR_DESCRIPTIONS
        ]
    )

    added_accounts: set[tuple[str, str]] = set()

    @callback
    def _add_account_binary_sensors(account: AccountState) -> None:
        key = (account.provider, account.account_key)
        if key in added_accounts:
            return
        added_accounts.add(key)
        async_add_entities(
            [
                AIUsageAccountBinarySensor(entry, runtime, account, description)
                for description in _account_binary_sensor_descriptions(account.provider)
            ]
        )

    entry.async_on_unload(
        runtime.async_register_account_binary_sensor_callback(
            _add_account_binary_sensors
        )
    )

    for account in runtime.account_states:
        _add_account_binary_sensors(account)


class AIUsageIntegrationBinarySensor(BinarySensorEntity):
    """Representation of an integration-level AI Usage binary sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    entity_description: AIUsageIntegrationBinarySensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        runtime: AIUsageRuntime,
        description: AIUsageIntegrationBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        self.entity_description = description
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}:{description.key}"
        self._attr_device_info = _integration_device_info(entry)

    @property
    def is_on(self) -> bool | None:
        """Return the current binary sensor value."""
        return self.entity_description.value_fn(self._runtime.integration_state)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for the binary sensor."""
        attributes = self.entity_description.attributes_fn(
            self._runtime.integration_state
        )
        return attributes or None

    async def async_added_to_hass(self) -> None:
        """Subscribe to integration-level updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                integration_update_signal(self._entry.entry_id),
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Write updated state to Home Assistant."""
        self.async_write_ha_state()


class AIUsageAccountBinarySensor(BinarySensorEntity, RestoreEntity):
    """Representation of a dynamic provider account binary sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    entity_description: AIUsageAccountBinarySensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        runtime: AIUsageRuntime,
        account: AccountState,
        description: AIUsageAccountBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        self.entity_description = description
        self._entry = entry
        self._runtime = runtime
        self._provider = account.provider
        self._account_key = account.account_key
        self._restored_is_on: bool | None = None
        self._restored_attributes: dict[str, Any] | None = None
        self._attr_unique_id = (
            f"{entry.entry_id}:{account.provider}:{account.account_key}:"
            f"{description.key}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the provider account device info."""
        return _account_device_info(self._entry, self._runtime, self._state)

    @property
    def is_on(self) -> bool | None:
        """Return the current binary sensor value."""
        value = self.entity_description.value_fn(self._state)
        if value is None and not self._state.has_sample:
            return self._restored_is_on
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for the binary sensor."""
        attributes = self.entity_description.attributes_fn(self._state)
        if attributes:
            return attributes
        if not self._state.has_sample:
            return self._restored_attributes
        return None

    @property
    def _state(self) -> AccountState:
        """Return account state."""
        return self._runtime.get_account_state(self._provider, self._account_key)

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to account updates."""
        if not self._state.has_sample:
            last_state = await self.async_get_last_state()
            if last_state is not None:
                self._restored_is_on = _restore_binary_value(last_state.state)
                self._restored_attributes = dict(last_state.attributes)

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                account_update_signal(
                    self._entry.entry_id,
                    self._provider,
                    self._account_key,
                ),
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Write updated state to Home Assistant."""
        self.async_write_ha_state()


def _account_binary_sensor_descriptions(
    provider: str,
) -> tuple[AIUsageAccountBinarySensorDescription, ...]:
    """Return all binary sensor descriptions for a provider account."""
    provider_keys = set(PROVIDER_BINARY_SENSOR_KEYS.get(provider, ()))
    provider_descriptions = tuple(
        description
        for description in PROVIDER_BINARY_SENSOR_DESCRIPTIONS.get(provider, ())
        if description.key in provider_keys
    )
    return COMMON_ACCOUNT_BINARY_SENSOR_DESCRIPTIONS + provider_descriptions


def _integration_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return DeviceInfo for the parent integration device."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        entry_type=DeviceEntryType.SERVICE,
        manufacturer=INTEGRATION_NAME,
        model="Webhook collector",
        name="Source Webhook",
        sw_version=INTEGRATION_VERSION,
    )


def _account_device_info(
    entry: ConfigEntry,
    runtime: AIUsageRuntime,
    account: AccountState,
) -> DeviceInfo:
    """Return DeviceInfo for a provider account device."""
    metadata = runtime.get_provider_metadata(account.provider)
    return DeviceInfo(
        identifiers={
            (DOMAIN, f"{entry.entry_id}:{account.provider}:{account.account_key}")
        },
        entry_type=DeviceEntryType.SERVICE,
        manufacturer=metadata.manufacturer,
        model=metadata.model,
        name=f"{metadata.provider_name} {account.account_label}",
        via_device=(DOMAIN, entry.entry_id),
        configuration_url=metadata.configuration_url,
    )


def _codex_rate_limit_bool(state: AccountState, key: str) -> bool | None:
    """Return a Codex rate_limit boolean value."""
    value = _nested_value(state.provider_data, "rate_limit", key)
    return value if isinstance(value, bool) else None


def _codex_window_number(
    state: AccountState,
    window_key: str,
    value_key: str,
) -> int | float | None:
    """Return a Codex window numeric value."""
    value = _nested_value(
        state.provider_data,
        "rate_limit",
        window_key,
        value_key,
    )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _nested_value(data: dict[str, Any], *path: str) -> Any:
    """Return a nested mapping value."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    """Drop attributes with None values."""
    return {key: value for key, value in data.items() if value is not None}


def _restore_binary_value(state: str) -> bool | None:
    """Convert a restored HA state string into a binary native value."""
    if state == STATE_ON:
        return True
    if state == STATE_OFF:
        return False
    if state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None
    return None
