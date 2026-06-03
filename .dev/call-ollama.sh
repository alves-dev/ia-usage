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
    "provider": "ollama_cloud",
    "status": "ok",
    "account_data": {
      "username": "ollama-manual",
      "email": "ollama.manual@example.com"
    },
    "plan_data": {
      "type": "free"
    },
    "provider_data": {
      "session_usage": {
        "used_percent": 8.0,
        "reset_at": "2026-06-03T22:00:00.000Z"
      },
      "weekly_usage": {
        "used_percent": 44.4,
        "reset_at": "2026-06-08T00:00:00.000Z"
      }
    },
    "error": null
  }' \
  "$WEBHOOK_URL"
