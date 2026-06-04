"""Ollama Cloud provider contract handling."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..const import PROVIDER_OLLAMA_CLOUD, PROVIDER_STATUS_OK
from ..models import ProviderMetadata
from .base import (
    ProviderPayloadHandler,
    require_iso_datetime,
    require_mapping,
    require_number,
)


class OllamaCloudPayloadHandler(ProviderPayloadHandler):
    """Validate Ollama Cloud usage payloads."""

    provider = PROVIDER_OLLAMA_CLOUD
    metadata = ProviderMetadata(
        provider=PROVIDER_OLLAMA_CLOUD,
        provider_name="Ollama Cloud",
        manufacturer="Ollama",
        model="Ollama Cloud account",
        configuration_url="https://ollama.com/settings",
    )

    def validate_provider_data(
        self,
        provider_data: Mapping[str, Any],
        *,
        status: str,
    ) -> None:
        """Validate Ollama Cloud usage windows."""
        if status != PROVIDER_STATUS_OK and not provider_data:
            return

        for usage_key in ("session_usage", "weekly_usage"):
            usage = require_mapping(provider_data, usage_key)
            usage_path = f"provider_data.{usage_key}"
            require_number(
                usage,
                "used_percent",
                path=usage_path,
                minimum=0,
                maximum=100,
            )
            require_iso_datetime(usage, "reset_at", path=usage_path)
