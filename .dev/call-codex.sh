#!/usr/bin/env bash
set -euo pipefail

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8123/api/webhook/ia-tool-usage}"

curl \
  --silent \
  --show-error \
  --write-out "\nHTTP %{http_code}\n" \
  --request POST \
  --header "Content-Type: application/json" \
  --data '{
    "schema_version": "1.0",
    "source": "manual_test",
    "source_version": "0.1.0",
    "collected_at": "2026-06-03T18:30:00.000Z",
    "provider": "codex",
    "status": "ok",
    "account_data": {
      "user_id": "user-manual-codex",
      "account_id": "acct-manual-codex",
      "email": "codex.manual@example.com"
    },
    "plan_data": {
      "type": "plus"
    },
    "provider_data": {
      "rate_limit": {
        "allowed": true,
        "limit_reached": false,
        "primary_window": {
          "used_percent": 12.5,
          "limit_window_seconds": 18000,
          "reset_after_seconds": 14400,
          "reset_at": 1780434415
        },
        "secondary_window": {
          "used_percent": 37.2,
          "limit_window_seconds": 604800,
          "reset_after_seconds": 428946,
          "reset_at": 1780846229
        }
      }
    },
    "error": null
  }' \
  "$WEBHOOK_URL"
