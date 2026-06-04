"""AI Usage custom integration."""

from __future__ import annotations

import logging

from aiohttp.hdrs import METH_POST
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_WEBHOOK_ID, DOMAIN, PLATFORMS
from .runtime import AIUsageRuntime

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI Usage from a config entry."""
    runtime = AIUsageRuntime(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    webhook_id = entry.data[CONF_WEBHOOK_ID]
    webhook_registered = False

    try:
        await runtime.async_setup()
        webhook.async_register(
            hass,
            DOMAIN,
            entry.title,
            webhook_id,
            runtime.async_handle_webhook,
            allowed_methods=(METH_POST,),
        )
        webhook_registered = True
        _LOGGER.debug("Registered AI Usage webhook %s", webhook_id)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        if webhook_registered:
            webhook.async_unregister(hass, webhook_id)
        hass.data[DOMAIN].pop(entry.entry_id, None)
        raise

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload AI Usage."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        webhook.async_unregister(hass, entry.data[CONF_WEBHOOK_ID])
        runtime = hass.data[DOMAIN].pop(entry.entry_id, None)
        if runtime is not None:
            await runtime.async_unload()

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when config entry data changes."""
    await hass.config_entries.async_reload(entry.entry_id)
