"""Config flow for AI Usage."""

from __future__ import annotations

import re

from homeassistant import config_entries
from homeassistant.components import webhook
import voluptuous as vol

from .const import CONF_WEBHOOK_ID, DOMAIN

_WEBHOOK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


class AIUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an AI Usage config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._suggested_webhook_id: str | None = None

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            webhook_id = _clean_webhook_id(user_input[CONF_WEBHOOK_ID])
            if webhook_id is None:
                errors[CONF_WEBHOOK_ID] = "invalid_webhook_id"
            else:
                return self.async_create_entry(
                    title="AI Usage",
                    data={CONF_WEBHOOK_ID: webhook_id},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_webhook_schema(self._default_webhook_id()),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict | None = None):
        """Allow the webhook endpoint to be reconfigured."""
        entry = self._get_reconfigure_entry()
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_mismatch()

        errors: dict[str, str] = {}
        if user_input is not None:
            webhook_id = _clean_webhook_id(user_input[CONF_WEBHOOK_ID])
            if webhook_id is None:
                errors[CONF_WEBHOOK_ID] = "invalid_webhook_id"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_WEBHOOK_ID: webhook_id},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_webhook_schema(entry.data[CONF_WEBHOOK_ID]),
            errors=errors,
        )

    def _default_webhook_id(self) -> str:
        """Return a stable generated webhook ID for this flow instance."""
        if self._suggested_webhook_id is None:
            self._suggested_webhook_id = webhook.async_generate_id()
        return self._suggested_webhook_id


def _webhook_schema(default: str) -> vol.Schema:
    """Return the config flow schema."""
    return vol.Schema({vol.Required(CONF_WEBHOOK_ID, default=default): str})


def _clean_webhook_id(value: object) -> str | None:
    """Validate and normalize the configured webhook ID."""
    if not isinstance(value, str):
        return None

    webhook_id = value.strip()
    if not _WEBHOOK_ID_PATTERN.fullmatch(webhook_id):
        return None

    return webhook_id
