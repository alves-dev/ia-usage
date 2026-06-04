"""Provider payload handlers."""

from __future__ import annotations

from .base import ProviderContractError, ProviderPayloadHandler
from .codex import CodexPayloadHandler
from .ollama_cloud import OllamaCloudPayloadHandler

PROVIDER_HANDLERS: dict[str, ProviderPayloadHandler] = {
    "codex": CodexPayloadHandler(),
    "ollama_cloud": OllamaCloudPayloadHandler(),
}

__all__ = [
    "PROVIDER_HANDLERS",
    "ProviderContractError",
    "ProviderPayloadHandler",
]
