"""Provider image static path registration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PROVIDER_IMAGE_FILES, PROVIDER_IMAGE_URL_BASE

_IMAGES_REGISTERED = "_provider_images_registered"
_IMAGE_URLS = "_provider_image_urls"


async def async_register_provider_static_paths(hass: HomeAssistant) -> None:
    """Register local provider image paths once per Home Assistant instance."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_IMAGES_REGISTERED):
        return

    image_dir = Path(__file__).parent / "provider_images"
    urls: dict[str, str | None] = {}
    configs: list[StaticPathConfig] = []

    for provider, filename in PROVIDER_IMAGE_FILES.items():
        path = image_dir / filename
        if not path.is_file():
            urls[provider] = None
            continue

        url_path = f"{PROVIDER_IMAGE_URL_BASE}/{filename}"
        urls[provider] = url_path
        configs.append(StaticPathConfig(url_path, str(path), True))

    if configs:
        await hass.http.async_register_static_paths(configs)

    domain_data[_IMAGE_URLS] = urls
    domain_data[_IMAGES_REGISTERED] = True


def provider_entity_picture(hass: HomeAssistant, provider: str) -> str | None:
    """Return the registered local entity picture URL for a provider."""
    domain_data = hass.data.get(DOMAIN, {})
    urls = domain_data.get(_IMAGE_URLS)
    if not isinstance(urls, dict):
        return None
    value = urls.get(provider)
    return value if isinstance(value, str) else None
