"""Base provider contract helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from ..models import ProviderMetadata


class ProviderContractError(ValueError):
    """Raised when provider-specific data violates the contract."""


class ProviderPayloadHandler(ABC):
    """Validate provider-specific payload sections and expose metadata."""

    provider: str
    metadata: ProviderMetadata

    @abstractmethod
    def validate_provider_data(
        self,
        provider_data: Mapping[str, Any],
        *,
        status: str,
    ) -> None:
        """Validate provider-specific data."""


def require_mapping(
    data: Mapping[str, Any],
    key: str,
    *,
    path: str = "provider_data",
) -> Mapping[str, Any]:
    """Return a nested mapping or raise a provider contract error."""
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ProviderContractError(f"{path}.{key} must be an object")
    return value


def require_bool(
    data: Mapping[str, Any],
    key: str,
    *,
    path: str,
) -> bool:
    """Return a boolean value or raise a provider contract error."""
    value = data.get(key)
    if not isinstance(value, bool):
        raise ProviderContractError(f"{path}.{key} must be a boolean")
    return value


def require_number(
    data: Mapping[str, Any],
    key: str,
    *,
    path: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> int | float:
    """Return a numeric value or raise a provider contract error."""
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderContractError(f"{path}.{key} must be numeric")
    if minimum is not None and value < minimum:
        raise ProviderContractError(f"{path}.{key} must be >= {minimum:g}")
    if maximum is not None and value > maximum:
        raise ProviderContractError(f"{path}.{key} must be <= {maximum:g}")
    return value


def require_iso_datetime(
    data: Mapping[str, Any],
    key: str,
    *,
    path: str,
) -> datetime:
    """Return an ISO 8601 datetime converted to UTC."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProviderContractError(f"{path}.{key} must be an ISO 8601 string")
    try:
        return parse_datetime(value)
    except ValueError as err:
        raise ProviderContractError(
            f"{path}.{key} must be an ISO 8601 datetime"
        ) from err


def parse_datetime(value: str) -> datetime:
    """Parse a contract ISO 8601 datetime and normalize it to UTC."""
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("datetime must include timezone")
    return parsed.astimezone(UTC)
