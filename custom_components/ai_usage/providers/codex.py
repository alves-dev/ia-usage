"""Codex provider contract handling."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..const import PROVIDER_CODEX, PROVIDER_STATUS_OK
from ..models import ProviderMetadata
from .base import (
    ProviderPayloadHandler,
    require_bool,
    require_mapping,
    require_number,
)


class CodexPayloadHandler(ProviderPayloadHandler):
    """Validate Codex usage payloads."""

    provider = PROVIDER_CODEX
    metadata = ProviderMetadata(
        provider=PROVIDER_CODEX,
        provider_name="Codex",
        manufacturer="OpenAI",
        model="Codex account",
        configuration_url="https://chatgpt.com/",
    )

    def validate_provider_data(
        self,
        provider_data: Mapping[str, Any],
        *,
        status: str,
    ) -> None:
        """Validate Codex rate limit data."""
        if status != PROVIDER_STATUS_OK and not provider_data:
            return

        rate_limit = require_mapping(provider_data, "rate_limit")
        require_bool(rate_limit, "allowed", path="provider_data.rate_limit")
        require_bool(rate_limit, "limit_reached", path="provider_data.rate_limit")

        for window_key in ("primary_window", "secondary_window"):
            window = require_mapping(
                rate_limit,
                window_key,
                path="provider_data.rate_limit",
            )
            window_path = f"provider_data.rate_limit.{window_key}"
            require_number(
                window,
                "used_percent",
                path=window_path,
                minimum=0,
                maximum=100,
            )
            require_number(
                window,
                "limit_window_seconds",
                path=window_path,
                minimum=0,
            )
            require_number(
                window,
                "reset_after_seconds",
                path=window_path,
                minimum=0,
            )
            require_number(window, "reset_at", path=window_path, minimum=0)
