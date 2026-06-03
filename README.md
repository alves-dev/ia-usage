# IA Usage

Home Assistant custom integration for tracking AI service usage from external
collectors.

The integration receives normalized payloads through a Home Assistant webhook,
validates the payload contract, identifies the provider account, and exposes
diagnostic and usage entities for dashboards and automations.

Supported providers in the current version:

- `codex`
- `ollama_cloud`

## What It Does

IA Usage is a webhook collector. It does not scrape provider pages by itself.
Another source, such as a browser extension, shell script, or manual test, sends
payloads to Home Assistant using the contract documented in
[docs/payload-contract.md](docs/payload-contract.md).

The integration then:

1. Validates the payload envelope and provider-specific data.
2. Separates ingestion errors from provider-reported errors.
3. Resolves a stable account identity without using raw email in `unique_id`.
4. Creates a parent diagnostic device for the webhook collector.
5. Creates dynamic account devices for each observed provider account.
6. Updates common account entities and provider-specific usage entities.
7. Persists known accounts so dynamic devices return after reload/restart.
8. Serves local provider images for `sensor.account.entity_picture`.

## Architecture

```text
Collector / script / extension
        |
        | POST /api/webhook/<webhook_id>
        v
Home Assistant webhook adapter
        |
        v
IAUsageIngestionService
        |
        +--> payload validation
        +--> provider validation
        +--> account identity
        +--> runtime state
        +--> storage
        +--> dispatcher updates
        |
        v
Sensors and binary sensors
```

The webhook is intentionally thin. Business logic lives in
`IAUsageIngestionService`, so future collectors can call the same ingestion
service without creating an artificial HTTP request.

## Devices

### Source Webhook

The parent device represents the configured IA Usage webhook source.

It contains integration-level diagnostics:

| Entity | Purpose |
| --- | --- |
| `sensor.last_ingest_status` | Result of the last ingest attempt. |
| `binary_sensor.webhook_problem` | On when the last ingest attempt failed. |
| `sensor.last_webhook_received_at` | Timestamp when HA received the last webhook. |
| `sensor.last_source` | Source of the last valid payload. |
| `sensor.known_accounts` | Number of dynamic provider accounts known. |
| `sensor.last_unscoped_error` | Last valid provider error that could not be tied to an account. |

### Provider Account Devices

Each identified account gets its own device:

```text
Codex codex.manual@example.com
Ollama Cloud ollama.manual@example.com
```

Account devices are created dynamically when the first valid payload for that
account arrives.

Common account entities:

| Entity | Purpose |
| --- | --- |
| `sensor.account` | Account label and provider image. |
| `sensor.plan` | Plan type from `plan_data.type`. |
| `sensor.status` | Provider status from the payload. |
| `binary_sensor.problem` | On when provider status is not `ok`. |
| `sensor.last_error` | Provider error code or `none`. |
| `sensor.collected_at` | Timestamp collected by the source. |
| `sensor.last_received_at` | Timestamp received by Home Assistant. |
| `sensor.source` | Source name and source/schema versions. |
| `sensor.request_count` | Count of accepted payloads for the account. |

Provider-specific entities:

| Provider | Entities |
| --- | --- |
| `codex` | Allowed, limit reached, primary/secondary window usage and reset sensors. |
| `ollama_cloud` | Session and weekly usage percent/reset sensors. |

## Installation

Copy `custom_components/ia_usage` into your Home Assistant config directory:

```text
config/custom_components/ia_usage
```

Restart Home Assistant, then add the integration:

```text
Settings > Devices & services > Add Integration > IA Usage
```

During setup, choose the `Webhook endpoint ID`.

If the ID is:

```text
ia-tool-usage
```

the webhook URL is:

```text
http://localhost:8123/api/webhook/ia-tool-usage
```

Treat the webhook ID like a secret. Use a long, non-obvious value for real
deployments.

## Payload Contract

Every payload uses the same envelope:

```json
{
  "schema_version": "1.0",
  "source": "manual_test",
  "source_version": "0.1.0",
  "collected_at": "2026-06-03T18:30:00.000Z",
  "provider": "codex",
  "status": "ok",
  "account_data": {},
  "plan_data": {},
  "provider_data": {},
  "error": null
}
```

See the full contract:

- [Payload contract](docs/payload-contract.md)
- [Device and sensor contract](docs/device-and-sensor-contract.md)
- [Implementation spec](docs/implementation-spec.md)

<details>
<summary>Codex example payload</summary>

```json
{
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
}
```

</details>

<details>
<summary>Ollama Cloud example payload</summary>

```json
{
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
}
```

</details>

<details>
<summary>Error payload without account identity</summary>

This is a valid provider error payload, but because it has no account identity,
it updates the parent device `sensor.last_unscoped_error` instead of creating an
account device.

```json
{
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
}
```

</details>

## Manual Webhook Calls

Development scripts are available in `.dev/`:

```bash
.dev/call-error.sh
.dev/call-codex.sh
.dev/call-ollama.sh
```

By default they call:

```text
http://localhost:8123/api/webhook/ia-tool-usage
```

Override the URL with:

```bash
WEBHOOK_URL="http://localhost:8123/api/webhook/my-webhook-id" .dev/call-codex.sh
```

## Account Identity

The integration never uses raw email, username, or display name in `unique_id`.

Identity resolution order:

1. `account_data.account_id`
2. `account_data.user_id`
3. hash of normalized provider email

Account key format:

```text
acct_<sha256(provider:id_kind:id_value)[0:16]>
```

For `ollama_cloud`, email hash is currently the expected identity fallback
because the source page does not expose a stable account ID.

## Storage And Restore

Known accounts are persisted with Home Assistant storage. The stored data is
small metadata used to recreate dynamic devices after reload/restart.

The integration does not persist raw payloads.

Dynamic entities also use `RestoreEntity` where applicable, so the last known
state can be shown before the next webhook sample arrives.

## Local Development

Install dependencies:

```bash
uv sync --all-groups
```

Run lint:

```bash
uv run ruff check custom_components/ia_usage tests
```

Run tests:

```bash
uv run pytest
```

Copy the integration to a local Home Assistant Core checkout:

```bash
.dev/copy-to-core.sh
```

More local notes are in [docs/development.md](docs/development.md).

## GitHub Actions

The workflow in `.github/workflows/tests.yml` runs on `main` pushes and pull
requests:

```bash
uv sync --all-groups --frozen
uv run ruff check custom_components/ia_usage tests
uv run pytest
```

## Version Target

The development environment pins:

```toml
homeassistant==2026.6.0
```

The integration manifest currently has no Python package requirements because
the runtime uses Home Assistant APIs and Python standard library modules only.
