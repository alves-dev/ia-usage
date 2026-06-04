"""Sensor platform for AI Usage."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    INGEST_STATUSES,
    INTEGRATION_NAME,
    INTEGRATION_VERSION,
    KNOWN_SOURCES,
    PLAN_TYPES,
    PROVIDER_NAMES,
    PROVIDER_SENSOR_KEYS,
    PROVIDER_STATUSES,
    account_update_signal,
    integration_update_signal,
)
from .models import AccountState, IntegrationState
from .providers.base import parse_datetime
from .runtime import AIUsageRuntime


@dataclass(frozen=True, kw_only=True)
class AIUsageIntegrationSensorDescription(SensorEntityDescription):
    """Describes an integration-level AI Usage sensor."""

    value_fn: Callable[[IntegrationState], Any]
    attributes_fn: Callable[[IntegrationState], dict[str, Any]] = lambda _state: {}


@dataclass(frozen=True, kw_only=True)
class AIUsageAccountSensorDescription(SensorEntityDescription):
    """Describes an account-level AI Usage sensor."""

    value_fn: Callable[[AccountState], Any]
    attributes_fn: Callable[[AccountState], dict[str, Any]] = lambda _state: {}


INTEGRATION_SENSOR_DESCRIPTIONS: tuple[AIUsageIntegrationSensorDescription, ...] = (
    AIUsageIntegrationSensorDescription(
        key="last_ingest_status",
        name="Last ingest status",
        icon="mdi:check-network-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=list(INGEST_STATUSES),
        value_fn=lambda state: state.last_ingest_status,
        attributes_fn=lambda state: _drop_none(
            {
                "last_received_at": _iso(state.last_webhook_received_at),
                "last_error_message": state.last_ingest_error_message,
            }
        ),
    ),
    AIUsageIntegrationSensorDescription(
        key="last_webhook_received_at",
        name="Last webhook received at",
        icon="mdi:webhook",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: state.last_webhook_received_at,
        attributes_fn=lambda state: {
            "last_ingest_status": state.last_ingest_status,
        },
    ),
    AIUsageIntegrationSensorDescription(
        key="last_source",
        name="Last source",
        icon="mdi:source-branch",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=list(KNOWN_SOURCES),
        value_fn=lambda state: state.last_source,
        attributes_fn=lambda state: _drop_none(
            {
                "source_version": state.last_source_version,
                "schema_version": state.last_schema_version,
                "provider": state.last_provider,
                "account_key": state.last_account_key,
            }
        ),
    ),
    AIUsageIntegrationSensorDescription(
        key="known_accounts",
        name="Known accounts",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:account-multiple",
        native_unit_of_measurement="accounts",
        value_fn=lambda state: state.known_accounts,
        attributes_fn=lambda state: {
            "providers": dict(state.known_accounts_by_provider),
        },
    ),
    AIUsageIntegrationSensorDescription(
        key="last_unscoped_error",
        name="Last unscoped error",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.last_unscoped_error,
        attributes_fn=lambda state: _drop_none(
            {
                "provider": state.last_unscoped_error_provider,
                "message": state.last_unscoped_error_message,
                "received_at": _iso(state.last_unscoped_error_received_at),
                "source": state.last_unscoped_error_source,
                "source_version": state.last_unscoped_error_source_version,
                "collected_at": _iso(state.last_unscoped_error_collected_at),
            }
        ),
    ),
)


COMMON_ACCOUNT_SENSOR_DESCRIPTIONS: tuple[AIUsageAccountSensorDescription, ...] = (
    AIUsageAccountSensorDescription(
        key="account",
        name="Account",
        icon="mdi:account-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: _account_value(state),  # noqa: PLW0108
        attributes_fn=lambda state: _account_attributes(state),  # noqa: PLW0108
    ),
    AIUsageAccountSensorDescription(
        key="plan",
        name="Plan",
        icon="mdi:card-account-details-outline",
        device_class=SensorDeviceClass.ENUM,
        options=list(PLAN_TYPES),
        value_fn=lambda state: _mapping_str(state.plan_data, "type"),
        attributes_fn=lambda state: {"plan_data": dict(state.plan_data)},
    ),
    AIUsageAccountSensorDescription(
        key="status",
        name="Status",
        icon="mdi:list-status",
        device_class=SensorDeviceClass.ENUM,
        options=list(PROVIDER_STATUSES),
        value_fn=lambda state: state.status,
        attributes_fn=lambda state: _drop_none(
            {
                "provider": state.provider,
                "collected_at": _iso(state.collected_at),
                "last_received_at": _iso(state.last_received_at),
            }
        ),
    ),
    AIUsageAccountSensorDescription(
        key="last_error",
        name="Last error",
        icon="mdi:alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: (
            state.error.code
            if state.error is not None
            else ("none" if state.has_sample else None)
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "message": state.error.message if state.error is not None else None,
                "status": state.status,
            }
        ),
    ),
    AIUsageAccountSensorDescription(
        key="collected_at",
        name="Collected at",
        icon="mdi:clock-edit-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: state.collected_at,
        attributes_fn=lambda state: _drop_none({"source": state.source}),
    ),
    AIUsageAccountSensorDescription(
        key="last_received_at",
        name="Last received at",
        icon="mdi:clock-in",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: state.last_received_at,
        attributes_fn=lambda state: _drop_none(
            {"collected_at": _iso(state.collected_at)}
        ),
    ),
    AIUsageAccountSensorDescription(
        key="source",
        name="Source",
        icon="mdi:cloud-upload-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=list(KNOWN_SOURCES),
        value_fn=lambda state: state.source,
        attributes_fn=lambda state: _drop_none(
            {
                "source_version": state.source_version,
                "schema_version": state.schema_version,
            }
        ),
    ),
    AIUsageAccountSensorDescription(
        key="request_count",
        name="Request count",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
        native_unit_of_measurement="requests",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda state: state.request_count if state.request_count > 0 else None,
        attributes_fn=lambda state: {"provider": state.provider},
    ),
)


CODEX_SENSOR_DESCRIPTIONS: tuple[AIUsageAccountSensorDescription, ...] = (
    AIUsageAccountSensorDescription(
        key="primary_window_used_percent",
        name="Primary window used",
        icon="mdi:gauge",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda state: _codex_window_number(
            state,
            "primary_window",
            "used_percent",
        ),
        attributes_fn=lambda state: _codex_used_attributes(state, "primary_window"),
    ),
    AIUsageAccountSensorDescription(
        key="primary_window_reset_at",
        name="Primary window reset at",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: _codex_window_datetime(
            state,
            "primary_window",
            "reset_at",
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "raw_reset_at": _codex_window_number(
                    state,
                    "primary_window",
                    "reset_at",
                ),
                "reset_after_seconds": _codex_window_number(
                    state,
                    "primary_window",
                    "reset_after_seconds",
                ),
            }
        ),
    ),
    AIUsageAccountSensorDescription(
        key="primary_window_reset_after",
        name="Primary window reset after",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda state: _codex_window_number(
            state,
            "primary_window",
            "reset_after_seconds",
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "reset_at": _iso(
                    _codex_window_datetime(state, "primary_window", "reset_at")
                )
            }
        ),
    ),
    AIUsageAccountSensorDescription(
        key="secondary_window_used_percent",
        name="Secondary window used",
        icon="mdi:gauge-low",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda state: _codex_window_number(
            state,
            "secondary_window",
            "used_percent",
        ),
        attributes_fn=lambda state: _codex_used_attributes(state, "secondary_window"),
    ),
    AIUsageAccountSensorDescription(
        key="secondary_window_reset_at",
        name="Secondary window reset at",
        icon="mdi:calendar-refresh-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: _codex_window_datetime(
            state,
            "secondary_window",
            "reset_at",
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "raw_reset_at": _codex_window_number(
                    state,
                    "secondary_window",
                    "reset_at",
                ),
                "reset_after_seconds": _codex_window_number(
                    state,
                    "secondary_window",
                    "reset_after_seconds",
                ),
            }
        ),
    ),
    AIUsageAccountSensorDescription(
        key="secondary_window_reset_after",
        name="Secondary window reset after",
        icon="mdi:timer-sand-complete",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=lambda state: _codex_window_number(
            state,
            "secondary_window",
            "reset_after_seconds",
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "reset_at": _iso(
                    _codex_window_datetime(state, "secondary_window", "reset_at")
                )
            }
        ),
    ),
)


OLLAMA_CLOUD_SENSOR_DESCRIPTIONS: tuple[AIUsageAccountSensorDescription, ...] = (
    AIUsageAccountSensorDescription(
        key="session_usage_used_percent",
        name="Session usage used",
        icon="mdi:speedometer",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda state: _ollama_usage_number(
            state,
            "session_usage",
            "used_percent",
        ),
        attributes_fn=lambda state: _ollama_used_attributes(state, "session_usage"),
    ),
    AIUsageAccountSensorDescription(
        key="session_usage_reset_at",
        name="Session usage reset at",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: _ollama_usage_datetime(
            state,
            "session_usage",
            "reset_at",
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "window": "session",
                "used_percent": _ollama_usage_number(
                    state,
                    "session_usage",
                    "used_percent",
                ),
            }
        ),
    ),
    AIUsageAccountSensorDescription(
        key="weekly_usage_used_percent",
        name="Weekly usage used",
        icon="mdi:chart-donut",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda state: _ollama_usage_number(
            state,
            "weekly_usage",
            "used_percent",
        ),
        attributes_fn=lambda state: _ollama_used_attributes(state, "weekly_usage"),
    ),
    AIUsageAccountSensorDescription(
        key="weekly_usage_reset_at",
        name="Weekly usage reset at",
        icon="mdi:calendar-week",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state: _ollama_usage_datetime(
            state,
            "weekly_usage",
            "reset_at",
        ),
        attributes_fn=lambda state: _drop_none(
            {
                "window": "weekly",
                "used_percent": _ollama_usage_number(
                    state,
                    "weekly_usage",
                    "used_percent",
                ),
            }
        ),
    ),
)

PROVIDER_SENSOR_DESCRIPTIONS = {
    "codex": CODEX_SENSOR_DESCRIPTIONS,
    "ollama_cloud": OLLAMA_CLOUD_SENSOR_DESCRIPTIONS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AI Usage sensors."""
    runtime: AIUsageRuntime = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            AIUsageIntegrationSensor(entry, runtime, description)
            for description in INTEGRATION_SENSOR_DESCRIPTIONS
        ]
    )

    added_accounts: set[tuple[str, str]] = set()

    @callback
    def _add_account_sensors(account: AccountState) -> None:
        key = (account.provider, account.account_key)
        if key in added_accounts:
            return
        added_accounts.add(key)
        async_add_entities(
            [
                AIUsageAccountSensor(entry, runtime, account, description)
                for description in _account_sensor_descriptions(account.provider)
            ]
        )

    entry.async_on_unload(
        runtime.async_register_account_sensor_callback(_add_account_sensors)
    )

    for account in runtime.account_states:
        _add_account_sensors(account)


class AIUsageIntegrationSensor(SensorEntity):
    """Representation of an integration-level AI Usage sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    entity_description: AIUsageIntegrationSensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        runtime: AIUsageRuntime,
        description: AIUsageIntegrationSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}:{description.key}"
        self._attr_device_info = _integration_device_info(entry)

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self._runtime.integration_state)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for the sensor."""
        attributes = self.entity_description.attributes_fn(
            self._runtime.integration_state
        )
        if self.entity_description.key == "last_ingest_status":
            attributes = dict(attributes)
            attributes["webhook_id"] = self._entry.data.get("webhook_id")
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


class AIUsageAccountSensor(SensorEntity, RestoreEntity):
    """Representation of a dynamic provider account sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    entity_description: AIUsageAccountSensorDescription

    def __init__(
        self,
        entry: ConfigEntry,
        runtime: AIUsageRuntime,
        account: AccountState,
        description: AIUsageAccountSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._entry = entry
        self._runtime = runtime
        self._provider = account.provider
        self._account_key = account.account_key
        self._restored_native_value: Any = None
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
    def entity_picture(self) -> str | None:
        """Return provider image for the account sensor."""
        if self.entity_description.key != "account":
            return None
        return self._runtime.get_provider_entity_picture(self._provider)

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        value = self.entity_description.value_fn(self._state)
        if value is None and not self._state.has_sample:
            return self._restored_native_value
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for the sensor."""
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
                self._restored_native_value = _restore_native_value(
                    self.entity_description,
                    last_state.state,
                )
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


def _account_sensor_descriptions(
    provider: str,
) -> tuple[AIUsageAccountSensorDescription, ...]:
    """Return all sensor descriptions for a provider account."""
    provider_keys = set(PROVIDER_SENSOR_KEYS.get(provider, ()))
    provider_descriptions = tuple(
        description
        for description in PROVIDER_SENSOR_DESCRIPTIONS.get(provider, ())
        if description.key in provider_keys
    )
    return COMMON_ACCOUNT_SENSOR_DESCRIPTIONS + provider_descriptions


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


def _account_value(state: AccountState) -> str:
    """Return the display value for sensor.account."""
    for key in ("email", "username", "account_id", "user_id"):
        value = _mapping_str(state.account_data, key)
        if value is not None:
            return value
    return state.account_key


def _account_attributes(state: AccountState) -> dict[str, Any]:
    """Return account sensor attributes."""
    return {
        "provider": state.provider,
        "provider_name": PROVIDER_NAMES.get(state.provider, state.provider),
        "account_key": state.account_key,
        "account_key_quality": state.account_key_quality,
        "account_id": _mapping_str(state.account_data, "account_id"),
        "user_id": _mapping_str(state.account_data, "user_id"),
        "username": _mapping_str(state.account_data, "username"),
        "email": _mapping_str(state.account_data, "email"),
        "plan_type": _mapping_str(state.plan_data, "type"),
    }


def _codex_used_attributes(state: AccountState, window_key: str) -> dict[str, Any]:
    """Return attributes for Codex used-percent sensors."""
    window_label = "primary" if window_key == "primary_window" else "secondary"
    return _drop_none(
        {
            "window": window_label,
            "limit_window_seconds": _codex_window_number(
                state,
                window_key,
                "limit_window_seconds",
            ),
            "reset_after_seconds": _codex_window_number(
                state,
                window_key,
                "reset_after_seconds",
            ),
            "reset_at": _iso(_codex_window_datetime(state, window_key, "reset_at")),
        }
    )


def _ollama_used_attributes(state: AccountState, usage_key: str) -> dict[str, Any]:
    """Return attributes for Ollama Cloud used-percent sensors."""
    window_label = "session" if usage_key == "session_usage" else "weekly"
    return _drop_none(
        {
            "window": window_label,
            "reset_at": _iso(_ollama_usage_datetime(state, usage_key, "reset_at")),
        }
    )


def _codex_window_number(
    state: AccountState,
    window_key: str,
    value_key: str,
) -> int | float | None:
    """Return a numeric Codex window value."""
    value = _nested_value(
        state.provider_data,
        "rate_limit",
        window_key,
        value_key,
    )
    return _number_or_none(value)


def _codex_window_datetime(
    state: AccountState,
    window_key: str,
    value_key: str,
) -> datetime | None:
    """Return a Codex epoch field as UTC datetime."""
    value = _codex_window_number(state, window_key, value_key)
    if value is None:
        return None
    return datetime.fromtimestamp(float(value), UTC)


def _ollama_usage_number(
    state: AccountState,
    usage_key: str,
    value_key: str,
) -> int | float | None:
    """Return a numeric Ollama Cloud usage value."""
    value = _nested_value(state.provider_data, usage_key, value_key)
    return _number_or_none(value)


def _ollama_usage_datetime(
    state: AccountState,
    usage_key: str,
    value_key: str,
) -> datetime | None:
    """Return an Ollama Cloud ISO field as UTC datetime."""
    value = _nested_value(state.provider_data, usage_key, value_key)
    if not isinstance(value, str):
        return None
    try:
        return parse_datetime(value)
    except ValueError:
        return None


def _nested_value(data: dict[str, Any], *path: str) -> Any:
    """Return a nested mapping value."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _mapping_str(data: dict[str, Any], key: str) -> str | None:
    """Return a non-empty string value from a mapping."""
    value = data.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number_or_none(value: object) -> int | float | None:
    """Return a number while rejecting booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _iso(value: datetime | None) -> str | None:
    """Return a datetime as ISO text for attributes."""
    if value is None:
        return None
    return value.isoformat()


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    """Drop attributes with None values."""
    return {key: value for key, value in data.items() if value is not None}


def _restore_native_value(
    description: AIUsageAccountSensorDescription,
    state: str,
) -> Any:
    """Convert a restored HA state string into a sensor native value."""
    if state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None

    if description.device_class == SensorDeviceClass.TIMESTAMP:
        try:
            return parse_datetime(state)
        except ValueError:
            return None

    if description.state_class in (
        SensorStateClass.MEASUREMENT,
        SensorStateClass.TOTAL_INCREASING,
    ):
        try:
            number = float(state)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number

    return state
