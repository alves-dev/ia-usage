# AI Usage

<p align="center">
  <img src="https://raw.githubusercontent.com/alves-dev/ai-usage/main/custom_components/ai_usage/brand/ai_usage_v5_512.png" alt="AI Usage" width="128">
</p>

<p align="center">
  <strong>Track AI service usage inside Home Assistant.</strong>
</p>

<p align="center">
  <a href="/hacs/repository/1255408258">
    <img alt="Open in HACS" src="https://img.shields.io/badge/Open%20in%20HACS-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white">
  </a>
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=alves-dev&repository=ai-usage&category=integration">
    <img alt="Add as a custom repository" src="https://img.shields.io/badge/Add%20to%20HACS-18BC9C?style=for-the-badge&logo=github&logoColor=white">
  </a>
</p>

<p align="center">
  <img alt="Home Assistant" src="https://img.shields.io/badge/Home%20Assistant-2026.4%2B-41BDF5?style=flat-square">
  <img alt="HACS" src="https://img.shields.io/badge/HACS-Custom%20Integration-18BC9C?style=flat-square">
  <img alt="Providers" src="https://img.shields.io/badge/Providers-Codex%20%7C%20Ollama%20Cloud-7C3AED?style=flat-square">
</p>

<p align="center">
  <a href="https://sonar.alves-dev.com/dashboard?id=ai-usage">
    <img alt="Quality Gate Status" src="https://sonar.alves-dev.com/api/project_badges/measure?project=ai-usage&metric=alert_status&token=sqb_ebd6127a5ab8462ca0c48146a5f8ca2c10b90bb4">
  </a>
  <a href="https://sonar.alves-dev.com/dashboard?id=ai-usage">
    <img alt="Coverage" src="https://sonar.alves-dev.com/api/project_badges/measure?project=ai-usage&metric=coverage&token=sqb_ebd6127a5ab8462ca0c48146a5f8ca2c10b90bb4">
  </a>
  <a href="https://sonar.alves-dev.com/dashboard?id=ai-usage">
    <img alt="Reliability Issues" src="https://sonar.alves-dev.com/api/project_badges/measure?project=ai-usage&metric=software_quality_reliability_issues&token=sqb_ebd6127a5ab8462ca0c48146a5f8ca2c10b90bb4">
  </a>
  <a href="https://sonar.alves-dev.com/dashboard?id=ai-usage">
    <img alt="Security Rating" src="https://sonar.alves-dev.com/api/project_badges/measure?project=ai-usage&metric=software_quality_security_rating&token=sqb_ebd6127a5ab8462ca0c48146a5f8ca2c10b90bb4">
  </a>
</p>

## What It Is

AI Usage is a custom Home Assistant integration that receives AI tool usage data
and turns it into sensors.

It is designed for simple dashboard questions:

- Can my account still use the service?
- How much of the current limit has been used?
- When does the limit reset?
- Did a collector stop sending data?
- How many AI accounts does Home Assistant know about?

The integration currently supports data from:

- Codex
- Ollama Cloud

## How It Works

AI Usage does not access your AI account directly and does not log in to external
services. It works as an entry point inside Home Assistant.

An external collector sends data to a Home Assistant webhook. The integration
validates that data, identifies the account, and updates sensors that you can use
in dashboards, automations, and alerts.

```text
External collector -> Home Assistant webhook -> AI Usage -> Sensors
```

This makes it possible to use different sources in the future, such as browser
extensions, local scripts, or other small collectors.

## What You See In Home Assistant

The integration creates one main device for the webhook and separate devices for
each identified AI account.

The main device shows the overall collection state:

- last received status
- whether the webhook has a problem
- when the last data arrived
- last data source
- number of known accounts
- last error that was not tied to a specific account

Each AI account shows sensors such as:

- account
- plan
- status
- active problem
- last error
- collection time
- Home Assistant receive time
- data source
- number of accepted samples

Provider-specific sensors also appear depending on the provider. For Codex, the
integration shows rate-limit windows and reset times. For Ollama Cloud, it shows
session usage and weekly usage.

## HACS Installation

If you have already added this repository to HACS, use:

[![Open in HACS](https://img.shields.io/badge/Open%20AI%20Usage%20in%20HACS-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white)](/hacs/repository/1255408258)

To add it as a custom repository:

[![Add to HACS](https://img.shields.io/badge/Add%20Custom%20Repository-18BC9C?style=for-the-badge&logo=github&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alves-dev&repository=ai-usage&category=integration)

Manual HACS setup:

1. Open HACS.
2. Go to **Integrations**.
3. Open the three-dot menu.
4. Choose **Custom repositories**.
5. Add `https://github.com/alves-dev/ai-usage`.
6. Select **Integration** as the category.
7. Install **AI Usage**.
8. Restart Home Assistant.

## Configuration

After installing and restarting:

1. Open **Settings > Devices & services**.
2. Click **Add Integration**.
3. Search for **AI Usage**.
4. Choose a **Webhook endpoint ID**.

The ID becomes part of the webhook URL. If the ID is:

```text
ia-tool-usage
```

the URL will be:

```text
http://YOUR_HOME_ASSISTANT:8123/api/webhook/ia-tool-usage
```

Treat this ID as a secret. Use a long value that is hard to guess.

## After Configuration

The integration only creates account sensors after it receives the first valid
payload. If you just installed it and do not see Codex or Ollama Cloud sensors
yet, that usually means no collector has sent data yet.

When the first valid sample arrives:

- the account appears as a new device;
- sensors are created automatically;
- the account is saved so it comes back after restarting Home Assistant.

## Privacy

AI Usage is designed to avoid sensitive identifiers in internal sensor IDs.

- Real email addresses are not used directly in `unique_id`.
- Raw webhook payloads are not stored.
- The webhook ID should be treated as a secret.
- Examples and tests should use synthetic data.

## Technical Documentation

Technical details live outside the README so the HACS screen stays easier to
read:

- [Payload contract](docs/payload-contract.md)
- [Device and sensor contract](docs/device-and-sensor-contract.md)
- [Generic provider contract](docs/generic-provider-contract.md)
- [Stable account identity decision](docs/account-stable-id-decision.md)
- [Implementation specification](docs/implementation-spec.md)
- [Home Assistant compatibility](docs/compatibility.md)

## Development

Main commands for contributors:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
scripts/validate-homeassistant-version.sh
```

Changes to payloads, sensors, or provider behavior should update the matching
technical documentation in `docs/`.
