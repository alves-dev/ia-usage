"""Account identity resolution for AI Usage."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from .models import AccountIdentity, account_label_from_data


def resolve_account_identity(
    provider: str,
    account_data: Mapping[str, Any],
) -> AccountIdentity | None:
    """Resolve the stable account identity for a provider payload."""
    account_id = _normalize_identifier(account_data.get("account_id"))
    if account_id is not None:
        return _build_identity(
            provider,
            "account_id",
            account_id,
            "stable",
            account_data,
        )

    user_id = _normalize_identifier(account_data.get("user_id"))
    if user_id is not None:
        return _build_identity(provider, "user_id", user_id, "stable", account_data)

    email = normalize_email(account_data.get("email"))
    if email is not None:
        return _build_identity(provider, "email", email, "email_hash", account_data)

    return None


def normalize_email(value: object) -> str | None:
    """Normalize an email value for hashing."""
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _normalize_identifier(value: object) -> str | None:
    """Normalize a provider account identifier."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _build_identity(
    provider: str,
    id_kind: str,
    id_value: str,
    quality: str,
    account_data: Mapping[str, Any],
) -> AccountIdentity:
    """Build an account identity using the documented hash format."""
    digest = hashlib.sha256(f"{provider}:{id_kind}:{id_value}".encode()).hexdigest()
    account_key = f"acct_{digest[:16]}"
    return AccountIdentity(
        provider=provider,
        account_key=account_key,
        account_key_quality=quality,
        id_kind=id_kind,
        id_value=id_value,
        label=account_label_from_data(account_data, account_key),
    )
