# Device And Sensor Contract

Este documento define os devices e sensores que a integracao Home Assistant
`ai_usage` deve criar a partir dos payloads descritos em
[`docs/payload-contract.md`](payload-contract.md).

A integracao deve tratar cada payload recebido pelo webhook como uma nova
amostra do estado de uso de IA para um provider e, quando possivel, para uma
conta especifica daquele provider.

## Referencias Home Assistant

Este contrato segue estes pontos dos developer docs do Home Assistant:

- Um device pode representar um dispositivo fisico ou um servico.
- Um device e representado por uma ou mais entidades.
- `DeviceInfo` so e usado para registrar device automaticamente quando a
  entidade foi carregada por uma config entry e tem `unique_id`.
- Novas integracoes devem usar `has_entity_name = True`.
- `unique_id` nao deve depender de dados alteraveis pelo usuario, como email,
  username, nome do device, hostname, URL ou IP.
- Sensores numericos que devem participar de estatisticas precisam definir
  `state_class` corretamente.
- Atributos que mudam com frequencia devem ser evitados; quando um dado muda e
  e util por si so, ele deve preferencialmente virar outra entidade.

Links:

- https://developers.home-assistant.io/docs/device_registry_index/
- https://developers.home-assistant.io/docs/entity_registry_index/
- https://developers.home-assistant.io/docs/core/entity/
- https://developers.home-assistant.io/docs/core/entity/sensor/
- https://developers.home-assistant.io/docs/core/entity/binary-sensor/
- https://developers.home-assistant.io/docs/core/entity/image/

## Objetivos

- Criar devices dinamicamente quando uma nova conta de provider for observada
  em uma request do webhook.
- Permitir mais de uma conta por provider.
- Manter sensores comuns entre providers com nomes, estados e atributos
  consistentes.
- Isolar sensores especificos em cada provider sem misturar semanticas
  diferentes.
- Expor dados uteis para dashboards e automacoes sem gravar payload bruto no
  recorder do Home Assistant.
- Separar erro de ingestao do webhook de erro reportado pelo provider.

## Modelo De Devices

A integracao deve criar dois niveis de devices.

### Device Da Integracao

Representa a instancia configurada da integracao `AI Usage` no Home Assistant.
Ele serve como device pai para debug, controle da fonte e erros que nao podem
ser associados a uma conta especifica.

Exemplo de `DeviceInfo`:

```json
{
  "identifiers": [["ai_usage", "<config_entry_id>"]],
  "entry_type": "service",
  "manufacturer": "AI Usage",
  "model": "Webhook collector",
  "name": "AI Usage Webhook",
  "sw_version": "0.1.0"
}
```

Entidades associadas:

| Entidade | Estado | Categoria | Exemplo de estado | Observacoes |
| --- | --- | --- | --- | --- |
| `sensor.last_ingest_status` | `ok` ou codigo de erro de ingestao | diagnostic | `ok` | Resultado da ultima request recebida pelo webhook, independente do status do provider. |
| `binary_sensor.webhook_problem` | `on` quando a ultima ingestao falhou | diagnostic | `off` | `device_class: problem`. Use para alertas de webhook quebrado. |
| `sensor.last_webhook_received_at` | timestamp | diagnostic | `2026-06-02T15:40:01+00:00` | Data/hora em que o HA recebeu a ultima request. |
| `sensor.last_source` | source do ultimo payload valido | diagnostic | `browser_extension` | Desabilitado por padrao. Atributos devem incluir `source_version`, `schema_version`, `provider` e `account_key` quando disponiveis. |
| `sensor.known_accounts` | numero inteiro | diagnostic | `2` | Total de contas dinamicas conhecidas pela integracao. |
| `sensor.last_unscoped_error` | `none` ou codigo de erro | diagnostic | `not_authenticated` | Desabilitado por padrao. Usado quando o payload tem erro mas nao tem dados suficientes para identificar a conta. |

Exemplo de entidade `sensor.last_ingest_status`:

```yaml
platform: sensor
unique_id: "<config_entry_id>:last_ingest_status"
device: "AI Usage Webhook"
has_entity_name: true
name: "Last ingest status"
device_class: enum
options:
  - ok
  - invalid_json
  - payload_must_be_object
  - missing_provider
  - unsupported_provider
  - invalid_contract
  - account_unidentified
  - unknown_error
native_value: ok
attributes:
  last_received_at: "2026-06-02T15:40:01+00:00"
  webhook_id: "ai_usage_webhook"
```

Exemplo de entidade `binary_sensor.webhook_problem`:

```yaml
platform: binary_sensor
unique_id: "<config_entry_id>:webhook_problem"
device: "AI Usage Webhook"
has_entity_name: true
name: "Webhook problem"
device_class: problem
is_on: false
attributes:
  last_ingest_status: ok
  last_error_message: null
```

Exemplo de entidade `sensor.last_source`:

```yaml
platform: sensor
unique_id: "<config_entry_id>:last_source"
device: "AI Usage Webhook"
has_entity_name: true
name: "Last source"
native_value: browser_extension
attributes:
  source_version: "0.1.0"
  schema_version: "1.0"
  provider: codex
  account_key: "acct_4f8b2d9a5e7c1031"
```

Exemplo de entidade `sensor.last_webhook_received_at`:

```yaml
platform: sensor
unique_id: "<config_entry_id>:last_webhook_received_at"
device: "AI Usage Webhook"
has_entity_name: true
name: "Last webhook received at"
device_class: timestamp
native_value: "2026-06-02T15:40:01+00:00"
attributes:
  last_ingest_status: ok
```

Exemplo de entidade `sensor.known_accounts`:

```yaml
platform: sensor
unique_id: "<config_entry_id>:known_accounts"
device: "AI Usage Webhook"
has_entity_name: true
name: "Known accounts"
icon: "mdi:account-multiple"
native_value: 2
attributes:
  providers:
    codex: 1
    ollama_cloud: 1
```

Exemplo de entidade `sensor.last_unscoped_error`:

```yaml
platform: sensor
unique_id: "<config_entry_id>:last_unscoped_error"
device: "AI Usage Webhook"
has_entity_name: true
name: "Last unscoped error"
native_value: none
attributes:
  provider: null
  message: null
```

### Device De Conta Do Provider

Representa uma conta observada em um provider. Deve ser criado dinamicamente na
primeira request valida que permita identificar a conta.

Um provider pode ter N devices, um para cada conta:

```text
codex + conta A        -> device AI Usage Codex user@example.com
codex + conta B        -> device AI Usage Codex work@example.com
ollama_cloud + conta C -> device AI Usage Ollama Cloud alves-dev
```

Exemplo de `DeviceInfo` para Codex:

```json
{
  "identifiers": [["ai_usage", "<config_entry_id>:codex:acct_4f8b2d9a5e7c1031"]],
  "entry_type": "service",
  "manufacturer": "OpenAI",
  "model": "Codex account",
  "name": "AI Usage Codex user@example.com",
  "via_device": ["ai_usage", "<config_entry_id>"],
  "configuration_url": "https://chatgpt.com/"
}
```

Exemplo de `DeviceInfo` para Ollama Cloud:

```json
{
  "identifiers": [["ai_usage", "<config_entry_id>:ollama_cloud:acct_91b9b51ec7f03220"]],
  "entry_type": "service",
  "manufacturer": "Ollama",
  "model": "Ollama Cloud account",
  "name": "AI Usage Ollama Cloud alves-dev",
  "via_device": ["ai_usage", "<config_entry_id>"],
  "configuration_url": "https://ollama.com/settings"
}
```

## Identificacao De Conta

O `account_key` e a chave interna usada para montar `unique_id`,
`DeviceInfo.identifiers` e o cache de contas conhecidas. Ele deve ser estavel e
nao deve expor email ou username diretamente.

Ordem recomendada para resolver a identidade da conta:

| Ordem | Campo | Qualidade | Observacao |
| --- | --- | --- | --- |
| 1 | `account_data.account_id` | `stable` | Melhor identificador quando existir. |
| 2 | `account_data.user_id` | `stable` | Aceitavel quando `account_id` nao existir. |
| 3 | hash de `provider + email normalizado` | `email_hash` | Fallback aprovado para providers que nao retornam ID de conta, como `ollama_cloud`. Nao usar o email cru no `unique_id`. |

Formato recomendado:

```text
account_key = "acct_" + sha256("<provider>:<id_kind>:<id_value>")[0:16]
device_key = "<config_entry_id>:<provider>:<account_key>"
entity_unique_id = "<device_key>:<entity_key>"
```

Exemplo:

```text
provider = "codex"
account_data.account_id = "acct-123"
account_key = "acct_4f8b2d9a5e7c1031"
unique_id do sensor de status = "<config_entry_id>:codex:acct_4f8b2d9a5e7c1031:status"
```

Para `ollama_cloud`, o payload atual so tem `username` e `email`, e nao ha um ID
visivel ou oculto confiavel na pagina para extrair. Portanto, a identidade da
conta deve usar o hash de `provider + email normalizado`.

Exemplo para `ollama_cloud`:

```text
provider = "ollama_cloud"
account_data.email = "User@Example.com"
email normalizado = "user@example.com"
account_key = "acct_91b9b51ec7f03220"
unique_id do sensor de status = "<config_entry_id>:ollama_cloud:acct_91b9b51ec7f03220:status"
```

Se um provider nao fornecer `account_id`, `user_id` ou `email`, a integracao nao
deve criar device de conta para aquele payload. Nesse caso, deve atualizar
`sensor.last_unscoped_error` no device da integracao.

## Ciclo De Vida Dinamico

Ao receber uma request do webhook:

1. Validar o envelope base do payload.
2. Atualizar o device da integracao com o status de ingestao.
3. Resolver `provider` e `account_key`.
4. Se a conta for nova, registrar o estado interno da conta e adicionar as
   entidades desse provider dinamicamente.
5. Se a conta ja existir, atualizar as entidades existentes.
6. Se o payload estiver valido mas nao tiver dados suficientes para resolver a
   conta, atualizar `sensor.last_unscoped_error` no device da integracao.
7. Emitir escrita de estado apenas com dados em memoria; propriedades de
   entidades nao devem fazer I/O.

A integracao deve persistir a lista de contas conhecidas em storage local ou
restaurar sensores no startup. Sem isso, devices dinamicos so reaparecem apos a
proxima request do webhook.

## Regras Gerais De Entidades

- Este contrato usa entidades `sensor` e `binary_sensor`. `ImageEntity` e
  opcional e so deve ser usada se a imagem do provider precisar existir como
  entidade separada.
- Todas as entidades devem ter `unique_id`.
- Todas as entidades devem ter `has_entity_name = True`.
- O `name` da entidade deve descrever apenas o dado, por exemplo `Status`,
  `Plan`, `5-hour limit used`, e nao repetir o nome do device.
- `should_poll` deve ser `false`; atualizacoes acontecem somente quando o
  webhook recebe payload novo.
- Quando um campo estiver ausente, `native_value` deve ser `None`, deixando o HA
  representar o estado como `unknown`.
- Estados textuais devem usar `snake_case` e ser estaveis para automacoes.
- Percentuais devem ser numericos de `0` a `100`, unidade `%`,
  `state_class: measurement` e precisao sugerida de 0 casas decimais.
- Timestamps devem ser objetos `datetime` timezone-aware em UTC; exemplos neste
  documento estao em ISO 8601.
- Duracoes expostas como entidade devem usar minutos (`min`) ou horas (`h`) e
  `SensorDeviceClass.DURATION` quando disponivel. O payload pode continuar
  usando segundos quando esse for o contrato do provider.
- Nao gravar payload bruto como atributo por padrao. Se necessario para debug,
  criar uma entidade diagnostica desabilitada por padrao.
- Entidades diagnosticas de auditoria/debug podem usar
  `entity_registry_enabled_default: false` para nao poluir novas instalacoes.

## Entidades Comuns Por Conta

Estas entidades devem existir para todo device de conta, independentemente do
provider.

| Entity key | Plataforma | Estado | Classe | Categoria | Exemplo |
| --- | --- | --- | --- | --- | --- |
| `account` | `sensor` | label da conta | nenhuma | diagnostic | `user@example.com` |
| `plan` | `sensor` | tipo do plano | enum quando houver opcoes conhecidas | nenhuma | `plus` |
| `status` | `sensor` | status do payload | enum | nenhuma | `ok` |
| `problem` | `binary_sensor` | erro ativo | problem | diagnostic | `off` |
| `last_error` | `sensor` | `none` ou codigo de erro | enum ou nenhuma | diagnostic | `none` |
| `collected_at` | `sensor` | timestamp da coleta | timestamp | diagnostic | `2026-06-02T15:40:00+00:00` |
| `last_received_at` | `sensor` | timestamp recebido pelo HA | timestamp | diagnostic | `2026-06-02T15:40:01+00:00` |
| `source` | `sensor` | source do payload | enum quando houver opcoes conhecidas | diagnostic | `browser_extension` |
| `request_count` | `sensor` | contador de payloads da conta | total_increasing | diagnostic | `42` |

Estas entidades comuns por conta devem ser desabilitadas por padrao no registro
de entidades: `last_error`, `collected_at`, `last_received_at`, `source` e
`request_count`.

### `sensor.account`

Entidade de perfil da conta. Ela deve ser o melhor lugar para mostrar imagem do
provider e metadados da conta.

Estado:

```text
account_data.email || account_data.username || account_data.account_id || account_data.user_id || account_key
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:account"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Account"
native_value: "user@example.com"
entity_picture: "/api/ai_usage/provider_image/codex"
attributes:
  provider: codex
  provider_name: Codex
  account_key: "acct_4f8b2d9a5e7c1031"
  account_key_quality: stable
  account_id: "acct-123"
  user_id: "user-123"
  username: null
  email: "user@example.com"
  plan_type: plus
```

Observacao: se for necessario uma entidade de imagem separada, usar `ImageEntity`
com `image_url` apontando para o logo do provider. Para o caso atual, o
`entity_picture` do sensor de conta e suficiente e mais simples.

### `sensor.plan`

Representa `plan_data.type`.

Este sensor nao e diagnostico. O plano e uma caracteristica da conta que pode
ser exibida em dashboards e usada em automacoes, mesmo quando muda pouco.

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:plan"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Plan"
device_class: enum
options:
  - free
  - plus
  - pro
  - team
  - enterprise
  - unknown
native_value: plus
attributes:
  provider: codex
  plan_data:
    type: plus
```

### `sensor.status`

Representa `status` do envelope.

Este status descreve a ultima amostra reportada pelo provider para a conta. Ele
nao substitui sensores especificos do provider, como `binary_sensor.allowed`,
que descrevem uma decisao de limite/uso dentro de um payload valido.

Estados aceitos:

```text
ok
not_authenticated
provider_unavailable
parse_error
rate_limited
ha_unavailable
unknown_error
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:status"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Status"
device_class: enum
options:
  - ok
  - not_authenticated
  - provider_unavailable
  - parse_error
  - rate_limited
  - ha_unavailable
  - unknown_error
native_value: ok
attributes:
  provider: codex
  collected_at: "2026-06-02T15:40:00+00:00"
  last_received_at: "2026-06-02T15:40:01+00:00"
```

### `binary_sensor.problem`

Representa se a ultima amostra da conta indica problema.

Regra:

```text
is_on = payload.status != "ok"
```

Exemplo:

```yaml
platform: binary_sensor
unique_id: "<device_key>:problem"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Problem"
device_class: problem
is_on: false
attributes:
  status: ok
  error_code: null
  error_message: null
```

### `sensor.last_error`

Representa `error.code` quando existir.

Exemplo sem erro:

```yaml
platform: sensor
unique_id: "<device_key>:last_error"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Last error"
native_value: none
attributes:
  message: null
  status: ok
```

Exemplo com erro:

```yaml
platform: sensor
unique_id: "<device_key>:last_error"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Last error"
native_value: not_authenticated
attributes:
  message: "User is not logged in"
  status: not_authenticated
```

### `sensor.collected_at`

Representa `collected_at` do payload, ou seja, quando o coletor leu o estado no
provider.

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:collected_at"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Collected at"
device_class: timestamp
native_value: "2026-06-02T15:40:00+00:00"
attributes:
  source: browser_extension
```

### `sensor.last_received_at`

Representa a data/hora em que o Home Assistant recebeu a request. Pode ser igual
a `collected_at` quando o coletor envia imediatamente, mas deve ser mantido
separado para diagnosticar atraso, fila ou coletor travado.

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:last_received_at"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Last received at"
device_class: timestamp
native_value: "2026-06-02T15:40:01+00:00"
attributes:
  collected_at: "2026-06-02T15:40:00+00:00"
```

### `sensor.source`

Representa `source` do payload.

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:source"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Source"
device_class: enum
options:
  - browser_extension
  - shell_script
  - python_collector
  - manual_test
native_value: browser_extension
attributes:
  source_version: "0.1.0"
  schema_version: "1.0"
```

### `sensor.request_count`

Conta payloads aceitos para aquela conta.

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:request_count"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Request count"
icon: "mdi:counter"
native_unit_of_measurement: "requests"
state_class: total_increasing
native_value: 42
attributes:
  provider: codex
```

## Provider: Codex

O provider `codex` usa `provider_data.rate_limit`.

### Entidades Especificas

| Entity key | Plataforma | Estado | Classe | Unidade | Exemplo |
| --- | --- | --- | --- | --- | --- |
| `allowed` | `binary_sensor` | uso permitido | nenhuma | nenhuma | `on` |
| `limit_reached` | `binary_sensor` | limite atingido | problem | nenhuma | `off` |
| `five_hour_usage_used_percent` | `sensor` | percentual usado do limite de 5 horas | measurement | `%` | `1` |
| `five_hour_usage_available_percent` | `sensor` | percentual disponivel do limite de 5 horas | measurement | `%` | `99` |
| `five_hour_usage_reset_at` | `sensor` | reset do limite de 5 horas | timestamp | nenhuma | `2026-06-02T20:26:55+00:00` |
| `five_hour_usage_reset_after` | `sensor` | horas ate reset na amostra | duration | `h` | `5` |
| `weekly_usage_used_percent` | `sensor` | percentual usado do limite semanal | measurement | `%` | `18` |
| `weekly_usage_available_percent` | `sensor` | percentual disponivel do limite semanal | measurement | `%` | `82` |
| `weekly_usage_reset_at` | `sensor` | reset do limite semanal | timestamp | nenhuma | `2026-06-07T20:50:29+00:00` |
| `weekly_usage_reset_after` | `sensor` | horas ate reset na amostra | duration | `h` | `119.39` |

### `binary_sensor.allowed`

Mapeamento:

```text
provider_data.rate_limit.allowed -> is_on
```

`allowed` indica se o Codex permite novas requisicoes de uso neste momento,
conforme a resposta de rate limit. Ele pode ser lido junto com `status`: `status`
explica se a amostra da conta foi coletada corretamente; `allowed` explica se o
uso esta permitido dentro dessa amostra.

Exemplo:

```yaml
platform: binary_sensor
unique_id: "<device_key>:allowed"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Allowed"
is_on: true
attributes:
  limit_reached: false
  five_hour_usage_used_percent: 1
  five_hour_usage_available_percent: 99
  weekly_usage_used_percent: 18
  weekly_usage_available_percent: 82
```

### `binary_sensor.limit_reached`

Mapeamento:

```text
provider_data.rate_limit.limit_reached -> is_on
```

Exemplo:

```yaml
platform: binary_sensor
unique_id: "<device_key>:limit_reached"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Limit reached"
device_class: problem
is_on: false
attributes:
  allowed: true
```

### `sensor.five_hour_usage_used_percent`

Mapeamento:

```text
provider_data.rate_limit.primary_window.used_percent -> native_value
provider_data.rate_limit.primary_window.limit_window_seconds -> attribute
provider_data.rate_limit.primary_window.reset_at -> attribute as UTC ISO 8601
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:five_hour_usage_used_percent"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "5-hour limit used"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 1
attributes:
  window: five_hour
  limit_window_seconds: 18000
  reset_after_seconds: 18000
  reset_at: "2026-06-02T20:26:55+00:00"
```

### `sensor.five_hour_usage_available_percent`

Mapeamento:

```text
100 - provider_data.rate_limit.primary_window.used_percent -> native_value
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:five_hour_usage_available_percent"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "5-hour limit available"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 99
attributes:
  window: five_hour
  used_percent: 1
  reset_at: "2026-06-02T20:26:55+00:00"
```

### `sensor.five_hour_usage_reset_at`

Mapeamento:

```text
provider_data.rate_limit.primary_window.reset_at -> datetime UTC
```

`reset_at` do Codex vem em Unix epoch seconds e deve ser convertido para
datetime UTC.

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:five_hour_usage_reset_at"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "5-hour limit reset at"
device_class: timestamp
native_value: "2026-06-02T20:26:55+00:00"
attributes:
  raw_reset_at: 1780434415
  reset_after_seconds: 18000
```

### `sensor.five_hour_usage_reset_after`

Mapeamento:

```text
provider_data.rate_limit.primary_window.reset_after_seconds -> native_value
```

O valor do payload esta em segundos, mas o estado da entidade deve ser convertido
para horas.

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:five_hour_usage_reset_after"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "5-hour limit reset after"
device_class: duration
native_unit_of_measurement: "h"
native_value: 5
attributes:
  reset_at: "2026-06-02T20:26:55+00:00"
  reset_after_seconds: 18000
```

### `sensor.weekly_usage_used_percent`

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:weekly_usage_used_percent"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Weekly limit used"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 18
attributes:
  window: weekly
  limit_window_seconds: 604800
  reset_after_seconds: 429815
  reset_at: "2026-06-07T20:50:29+00:00"
```

### `sensor.weekly_usage_available_percent`

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:weekly_usage_available_percent"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Weekly limit available"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 82
attributes:
  window: weekly
  used_percent: 18
  reset_at: "2026-06-07T20:50:29+00:00"
```

### `sensor.weekly_usage_reset_at`

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:weekly_usage_reset_at"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Weekly limit reset at"
device_class: timestamp
native_value: "2026-06-07T20:50:29+00:00"
attributes:
  raw_reset_at: 1780846229
  reset_after_seconds: 429815
```

### `sensor.weekly_usage_reset_after`

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:weekly_usage_reset_after"
device: "AI Usage Codex user@example.com"
has_entity_name: true
name: "Weekly limit reset after"
device_class: duration
native_unit_of_measurement: "h"
native_value: 119.39
attributes:
  reset_at: "2026-06-07T20:50:29+00:00"
  reset_after_seconds: 429815
```

## Provider: Ollama Cloud

O provider `ollama_cloud` usa `provider_data.session_usage` e
`provider_data.weekly_usage`.

### Entidades Especificas

| Entity key | Plataforma | Estado | Classe | Unidade | Exemplo |
| --- | --- | --- | --- | --- | --- |
| `session_usage_used_percent` | `sensor` | uso da sessao | measurement | `%` | `0` |
| `session_usage_available_percent` | `sensor` | uso disponivel da sessao | measurement | `%` | `100` |
| `session_usage_reset_at` | `sensor` | reset da sessao | timestamp | nenhuma | `2026-05-31T19:00:00+00:00` |
| `weekly_usage_used_percent` | `sensor` | uso semanal | measurement | `%` | `4` |
| `weekly_usage_available_percent` | `sensor` | uso semanal disponivel | measurement | `%` | `96` |
| `weekly_usage_reset_at` | `sensor` | reset semanal | timestamp | nenhuma | `2026-06-01T00:00:00+00:00` |

### `sensor.session_usage_used_percent`

Mapeamento:

```text
provider_data.session_usage.used_percent -> native_value
provider_data.session_usage.reset_at -> attribute
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:session_usage_used_percent"
device: "AI Usage Ollama Cloud alves-dev"
has_entity_name: true
name: "Session usage used"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 0
attributes:
  window: session
  reset_at: "2026-05-31T19:00:00+00:00"
```

### `sensor.session_usage_available_percent`

Mapeamento:

```text
100 - provider_data.session_usage.used_percent -> native_value
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:session_usage_available_percent"
device: "AI Usage Ollama Cloud alves-dev"
has_entity_name: true
name: "Session usage available"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 100
attributes:
  window: session
  used_percent: 0
  reset_at: "2026-05-31T19:00:00+00:00"
```

### `sensor.session_usage_reset_at`

Mapeamento:

```text
provider_data.session_usage.reset_at -> datetime UTC
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:session_usage_reset_at"
device: "AI Usage Ollama Cloud alves-dev"
has_entity_name: true
name: "Session usage reset at"
device_class: timestamp
native_value: "2026-05-31T19:00:00+00:00"
attributes:
  window: session
  used_percent: 0
```

### `sensor.weekly_usage_used_percent`

Mapeamento:

```text
provider_data.weekly_usage.used_percent -> native_value
provider_data.weekly_usage.reset_at -> attribute
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:weekly_usage_used_percent"
device: "AI Usage Ollama Cloud alves-dev"
has_entity_name: true
name: "Weekly usage used"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 4
attributes:
  window: weekly
  reset_at: "2026-06-01T00:00:00+00:00"
```

### `sensor.weekly_usage_available_percent`

Mapeamento:

```text
100 - provider_data.weekly_usage.used_percent -> native_value
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:weekly_usage_available_percent"
device: "AI Usage Ollama Cloud alves-dev"
has_entity_name: true
name: "Weekly usage available"
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
native_value: 96
attributes:
  window: weekly
  used_percent: 4
  reset_at: "2026-06-01T00:00:00+00:00"
```

### `sensor.weekly_usage_reset_at`

Mapeamento:

```text
provider_data.weekly_usage.reset_at -> datetime UTC
```

Exemplo:

```yaml
platform: sensor
unique_id: "<device_key>:weekly_usage_reset_at"
device: "AI Usage Ollama Cloud alves-dev"
has_entity_name: true
name: "Weekly usage reset at"
device_class: timestamp
native_value: "2026-06-01T00:00:00+00:00"
attributes:
  window: weekly
  used_percent: 4.4
```

## Mapeamento Resumido

### Envelope Comum

| Payload | Entidade | Estado/Atributo |
| --- | --- | --- |
| `schema_version` | `sensor.source` | atributo `schema_version` |
| `source` | `sensor.source` | estado |
| `source_version` | `sensor.source` | atributo `source_version` |
| `collected_at` | `sensor.collected_at` | estado |
| `provider` | `sensor.account` e atributos comuns | atributo `provider` |
| `status` | `sensor.status` | estado |
| `status != "ok"` | `binary_sensor.problem` | `is_on` |
| `account_data` | `sensor.account` | atributos |
| `plan_data.type` | `sensor.plan` | estado |
| `error.code` | `sensor.last_error` | estado |
| `error.message` | `sensor.last_error` | atributo `message` |

### Codex

| Payload | Entidade |
| --- | --- |
| `provider_data.rate_limit.allowed` | `binary_sensor.allowed` |
| `provider_data.rate_limit.limit_reached` | `binary_sensor.limit_reached` |
| `provider_data.rate_limit.primary_window.used_percent` | `sensor.five_hour_usage_used_percent` |
| `provider_data.rate_limit.primary_window.used_percent` | `sensor.five_hour_usage_available_percent` |
| `provider_data.rate_limit.primary_window.reset_at` | `sensor.five_hour_usage_reset_at` |
| `provider_data.rate_limit.primary_window.reset_after_seconds` | `sensor.five_hour_usage_reset_after` |
| `provider_data.rate_limit.secondary_window.used_percent` | `sensor.weekly_usage_used_percent` |
| `provider_data.rate_limit.secondary_window.used_percent` | `sensor.weekly_usage_available_percent` |
| `provider_data.rate_limit.secondary_window.reset_at` | `sensor.weekly_usage_reset_at` |
| `provider_data.rate_limit.secondary_window.reset_after_seconds` | `sensor.weekly_usage_reset_after` |

### Ollama Cloud

| Payload | Entidade |
| --- | --- |
| `provider_data.session_usage.used_percent` | `sensor.session_usage_used_percent` |
| `provider_data.session_usage.used_percent` | `sensor.session_usage_available_percent` |
| `provider_data.session_usage.reset_at` | `sensor.session_usage_reset_at` |
| `provider_data.weekly_usage.used_percent` | `sensor.weekly_usage_used_percent` |
| `provider_data.weekly_usage.used_percent` | `sensor.weekly_usage_available_percent` |
| `provider_data.weekly_usage.reset_at` | `sensor.weekly_usage_reset_at` |

## Tratamento De Erros

Erros devem existir em dois niveis.

No device da integracao:

- JSON invalido.
- Payload fora do envelope.
- Provider ausente ou nao suportado.
- Payload valido com `status != "ok"` mas sem dados para resolver a conta.

No device da conta do provider:

- Payload valido e associado a uma conta.
- `status != "ok"` vindo do provider.
- `error.code` e `error.message` enviados pelo source.
- Limites atingidos ou indisponibilidade especifica do provider.

Exemplo de erro sem conta identificavel:

```yaml
device: "AI Usage Webhook"
entity: "sensor.last_unscoped_error"
native_value: not_authenticated
attributes:
  provider: codex
  source: browser_extension
  source_version: "0.1.0"
  collected_at: "2026-06-02T15:40:00+00:00"
  message: "User is not logged in"
```

Exemplo de erro com conta identificavel:

```yaml
device: "AI Usage Codex user@example.com"
entity: "sensor.last_error"
native_value: rate_limited
attributes:
  provider: codex
  message: "Usage limit reached"
  status: rate_limited
```

## Disponibilidade

As entidades representam a ultima amostra recebida. Portanto:

- Uma entidade nao deve ficar `unavailable` apenas porque nao houve webhook
  recente.
- A entidade deve ficar `unavailable` quando o estado interno da integracao nao
  puder ser carregado, quando a entidade depende de uma conta removida, ou
  quando o valor armazenado e invalido para a classe da entidade.
- Automacoes que precisam detectar ausencia de atualizacao devem usar
  `sensor.last_received_at` ou `sensor.collected_at`.

## Dados Sensiveis

- Nao armazenar cookies, tokens, HTML bruto ou API keys.
- Nao usar email ou username diretamente em `unique_id` ou
  `DeviceInfo.identifiers`.
- Email e username podem aparecer em atributos e no nome exibido do device, pois
  sao dados de conta esperados pelo payload, mas essa decisao deve ser
  configuravel no futuro se houver requisito de privacidade.
- Payload bruto deve ficar fora dos atributos por padrao.

## Decisoes Recomendadas Para Proxima Versao Do Payload

Tambem seria util adicionar `provider_data.provider_image_url` apenas se a
imagem vier do provider e puder mudar. Para logos estaticos conhecidos, a
integracao deve servir assets locais e nao exigir que o source envie imagem.
