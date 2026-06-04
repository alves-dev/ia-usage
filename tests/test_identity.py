"""Tests for AI Usage account identity resolution."""

from __future__ import annotations

import hashlib

from custom_components.ai_usage.identity import (
    normalize_email,
    resolve_account_identity,
)


def _expected_account_key(provider: str, id_kind: str, id_value: str) -> str:
    digest = hashlib.sha256(f"{provider}:{id_kind}:{id_value}".encode()).hexdigest()
    return f"acct_{digest[:16]}"


def test_account_id_has_priority() -> None:
    """account_id should be preferred over user_id and email."""
    identity = resolve_account_identity(
        "codex",
        {
            "account_id": "acct-123",
            "user_id": "user-123",
            "email": "user@example.com",
        },
    )

    assert identity is not None
    assert identity.id_kind == "account_id"
    assert identity.id_value == "acct-123"
    assert identity.account_key_quality == "stable"
    assert identity.account_key == _expected_account_key(
        "codex",
        "account_id",
        "acct-123",
    )
    assert identity.label == "user@example.com"


def test_user_id_used_when_account_id_absent() -> None:
    """user_id should be used when account_id is absent."""
    identity = resolve_account_identity(
        "codex",
        {
            "user_id": "user-123",
            "email": "user@example.com",
        },
    )

    assert identity is not None
    assert identity.id_kind == "user_id"
    assert identity.account_key == _expected_account_key(
        "codex",
        "user_id",
        "user-123",
    )


def test_email_hash_fallback_is_normalized() -> None:
    """Email fallback should normalize case and whitespace."""
    upper = resolve_account_identity("ollama_cloud", {"email": " User@Example.COM "})
    lower = resolve_account_identity("ollama_cloud", {"email": "user@example.com"})

    assert upper is not None
    assert lower is not None
    assert upper.id_kind == "email"
    assert upper.account_key_quality == "email_hash"
    assert upper.account_key == lower.account_key
    assert upper.account_key == _expected_account_key(
        "ollama_cloud",
        "email",
        "user@example.com",
    )


def test_username_without_email_does_not_identify_account() -> None:
    """Username alone must not create a stable account identity."""
    assert resolve_account_identity("ollama_cloud", {"username": "igor"}) is None


def test_normalize_email_rejects_empty_values() -> None:
    """Empty email values should be rejected."""
    assert normalize_email(None) is None
    assert normalize_email("   ") is None
