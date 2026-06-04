"""Constants for the IA Usage integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ia_usage"
INTEGRATION_NAME = "IA Usage"
INTEGRATION_VERSION = "0.0.1"

CONF_WEBHOOK_ID = "webhook_id"

PROVIDER_CODEX = "codex"
PROVIDER_OLLAMA_CLOUD = "ollama_cloud"
SUPPORTED_PROVIDERS = (PROVIDER_CODEX, PROVIDER_OLLAMA_CLOUD)

PROVIDER_NAMES = {
    PROVIDER_CODEX: "Codex",
    PROVIDER_OLLAMA_CLOUD: "Ollama Cloud",
}

PAYLOAD_SCHEMA_VERSION = "1.0"
KNOWN_SOURCES = (
    "browser_extension",
    "shell_script",
    "python_collector",
    "manual_test",
)

PROVIDER_STATUS_OK = "ok"
PROVIDER_STATUSES = (
    PROVIDER_STATUS_OK,
    "not_authenticated",
    "provider_unavailable",
    "parse_error",
    "rate_limited",
    "ha_unavailable",
    "unknown_error",
)

INGEST_STATUS_OK = "ok"
INGEST_STATUS_INVALID_JSON = "invalid_json"
INGEST_STATUS_PAYLOAD_MUST_BE_OBJECT = "payload_must_be_object"
INGEST_STATUS_MISSING_PROVIDER = "missing_provider"
INGEST_STATUS_UNSUPPORTED_PROVIDER = "unsupported_provider"
INGEST_STATUS_INVALID_CONTRACT = "invalid_contract"
INGEST_STATUS_ACCOUNT_UNIDENTIFIED = "account_unidentified"
INGEST_STATUS_UNKNOWN_ERROR = "unknown_error"
INGEST_STATUSES = (
    INGEST_STATUS_OK,
    INGEST_STATUS_INVALID_JSON,
    INGEST_STATUS_PAYLOAD_MUST_BE_OBJECT,
    INGEST_STATUS_MISSING_PROVIDER,
    INGEST_STATUS_UNSUPPORTED_PROVIDER,
    INGEST_STATUS_INVALID_CONTRACT,
    INGEST_STATUS_ACCOUNT_UNIDENTIFIED,
    INGEST_STATUS_UNKNOWN_ERROR,
)

PLAN_TYPES = ("free", "plus", "pro", "team", "enterprise", "unknown")

PARENT_SENSOR_KEYS = (
    "last_ingest_status",
    "last_webhook_received_at",
    "last_source",
    "known_accounts",
    "last_unscoped_error",
)
PARENT_BINARY_SENSOR_KEYS = ("webhook_problem",)

COMMON_ACCOUNT_SENSOR_KEYS = (
    "account",
    "plan",
    "status",
    "last_error",
    "collected_at",
    "last_received_at",
    "source",
    "request_count",
)
COMMON_ACCOUNT_BINARY_SENSOR_KEYS = ("problem",)

CODEX_SENSOR_KEYS = (
    "primary_window_used_percent",
    "primary_window_reset_at",
    "primary_window_reset_after",
    "secondary_window_used_percent",
    "secondary_window_reset_at",
    "secondary_window_reset_after",
)
CODEX_BINARY_SENSOR_KEYS = ("allowed", "limit_reached")

OLLAMA_CLOUD_SENSOR_KEYS = (
    "session_usage_used_percent",
    "session_usage_reset_at",
    "weekly_usage_used_percent",
    "weekly_usage_reset_at",
)
OLLAMA_CLOUD_BINARY_SENSOR_KEYS: tuple[str, ...] = ()

PROVIDER_SENSOR_KEYS = {
    PROVIDER_CODEX: CODEX_SENSOR_KEYS,
    PROVIDER_OLLAMA_CLOUD: OLLAMA_CLOUD_SENSOR_KEYS,
}
PROVIDER_BINARY_SENSOR_KEYS = {
    PROVIDER_CODEX: CODEX_BINARY_SENSOR_KEYS,
    PROVIDER_OLLAMA_CLOUD: OLLAMA_CLOUD_BINARY_SENSOR_KEYS,
}

PROVIDER_IMAGE_URL_BASE = f"/api/{DOMAIN}/provider_images"
PROVIDER_IMAGE_FILES = {
    PROVIDER_CODEX: "codex.png",
    PROVIDER_OLLAMA_CLOUD: "ollama_cloud.png",
}

PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR)

EVENT_WEBHOOK_RECEIVED = f"{DOMAIN}_webhook_received"


def integration_update_signal(entry_id: str) -> str:
    """Return the dispatcher signal for integration-level updates."""
    return f"{DOMAIN}_{entry_id}_integration_updated"


def account_update_signal(entry_id: str, provider: str, account_key: str) -> str:
    """Return the dispatcher signal for account state updates."""
    return f"{DOMAIN}_{entry_id}_{provider}_{account_key}_updated"


def accounts_changed_signal(entry_id: str) -> str:
    """Return the dispatcher signal emitted when dynamic accounts change."""
    return f"{DOMAIN}_{entry_id}_accounts_changed"


def provider_update_signal(entry_id: str, provider: str) -> str:
    """Return the legacy provider-level signal name."""
    return f"{DOMAIN}_{entry_id}_{provider}_updated"
