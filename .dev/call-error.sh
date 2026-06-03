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
    "status": "not_authenticated",
    "account_data": {},
    "plan_data": {},
    "provider_data": {},
    "error": {
      "code": "not_authenticated",
      "message": "Manual test: user is not logged in"
    }
  }' \
  "$WEBHOOK_URL"
