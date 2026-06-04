"""Reusable payload ingestion service for AI Usage."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from http import HTTPStatus
import logging
from typing import TYPE_CHECKING, Any

from .const import (
    INGEST_STATUS_ACCOUNT_UNIDENTIFIED,
    INGEST_STATUS_UNKNOWN_ERROR,
)
from .identity import resolve_account_identity
from .models import IngestContext, IngestResult
from .validation import PayloadValidationError, validate_payload

if TYPE_CHECKING:
    from .runtime import AIUsageRuntime

_LOGGER = logging.getLogger(__name__)


class AIUsageIngestionService:
    """Validate payloads and apply them to runtime state."""

    def __init__(self, runtime: AIUsageRuntime) -> None:
        """Initialize the ingestion service."""
        self._runtime = runtime

    async def async_ingest_payload(
        self,
        payload: object,
        *,
        received_at: datetime,
        transport: str,
        context: Mapping[str, Any] | None = None,
    ) -> IngestResult:
        """Ingest a raw payload delivered by any transport adapter."""
        ingest_context = IngestContext(
            transport=transport,
            received_at=received_at,
            webhook_id=_context_str(context, "webhook_id"),
            request_remote=_context_str(context, "request_remote"),
        )

        try:
            envelope = validate_payload(payload)
        except PayloadValidationError as err:
            result = IngestResult(
                ok=False,
                http_status=err.http_status,
                ingest_status=err.ingest_status,
                provider=err.provider,
                message=err.message,
            )
            await self._runtime.async_record_ingest_result(result, ingest_context)
            return result
        except Exception as err:
            _LOGGER.exception("Unexpected AI Usage payload validation failure")
            result = IngestResult(
                ok=False,
                http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
                ingest_status=INGEST_STATUS_UNKNOWN_ERROR,
                message=str(err),
            )
            await self._runtime.async_record_ingest_result(result, ingest_context)
            return result

        identity = resolve_account_identity(envelope.provider, envelope.account_data)
        if identity is None:
            message = "payload does not include account_id, user_id, or email"
            error_code = INGEST_STATUS_ACCOUNT_UNIDENTIFIED
            if envelope.error is not None:
                error_code = envelope.error.code
                message = envelope.error.message

            await self._runtime.async_record_unscoped_error(
                envelope,
                ingest_context,
                error_code=error_code,
                message=message,
            )
            result = IngestResult(
                ok=False,
                http_status=HTTPStatus.ACCEPTED,
                ingest_status=INGEST_STATUS_ACCOUNT_UNIDENTIFIED,
                provider=envelope.provider,
                message=message,
                provider_status=envelope.status,
            )
            await self._runtime.async_record_ingest_result(
                result,
                ingest_context,
                envelope,
            )
            return result

        try:
            created_account = await self._runtime.async_apply_account_sample(
                envelope,
                identity,
                ingest_context,
            )
        except Exception as err:
            _LOGGER.exception("Unexpected AI Usage account update failure")
            result = IngestResult(
                ok=False,
                http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
                ingest_status=INGEST_STATUS_UNKNOWN_ERROR,
                provider=envelope.provider,
                message=str(err),
                provider_status=envelope.status,
            )
            await self._runtime.async_record_ingest_result(
                result,
                ingest_context,
                envelope,
            )
            return result

        result = IngestResult.success(
            provider=envelope.provider,
            account_key=identity.account_key,
            created_account=created_account,
            provider_status=envelope.status,
        )
        await self._runtime.async_record_ingest_result(
            result,
            ingest_context,
            envelope,
        )
        return result


def _context_str(context: Mapping[str, Any] | None, key: str) -> str | None:
    """Return a string context value."""
    if context is None:
        return None
    value = context.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None
