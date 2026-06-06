# Generic Provider Contract Hypothesis

Este documento descreve uma hipotese de contrato para permitir providers
genericos na integracao `ai_usage`.

Ele nao substitui os contratos atuais de `codex` e `ollama_cloud`. A ideia aqui
e responder: se a integracao aceitasse um provider desconhecido previamente,
quais dados o source teria que enviar para que o Home Assistant conseguisse
criar devices e sensores de forma consistente?

## Principio Principal

Um provider generico nao deve ser um JSON livre.

Mesmo no modo generico, a integracao precisa receber dados em formato
padronizado para criar entidades estaveis no Home Assistant. A flexibilidade
deve estar na lista de entidades enviadas pelo source, nao na interpretacao de
campos arbitrarios pela integracao.

Recomendacao importante:

```text
Nao usar provider = "generic" como identificador do provider real.
```

O campo top-level `provider` deve continuar representando o provider real, em
formato estavel e seguro para automacoes:

```json
"provider": "anthropic_console"
```

O modo generico deve ser indicado dentro de `provider_data`:

```json
"provider_data": {
  "contract": "generic_provider.v1"
}
```

Isso evita criar todos os providers genericos em um unico device chamado
`generic` e mantem `unique_id`, devices e dashboards organizados por provider
real.

## Quando Usar

Usar provider generico quando:

- O provider ainda nao tem parser especifico na integracao.
- O source ja consegue normalizar os dados para sensores do Home Assistant.
- O conjunto de sensores pode variar por provider ou por conta.
- O objetivo e aceitar novos providers sem alterar o codigo da integracao.

Nao usar provider generico quando:

- A integracao precisa interpretar regras especificas do provider.
- O payload bruto precisa ser parseado dentro do Home Assistant.
- A semantica dos campos nao e estavel.
- O source nao consegue fornecer identificadores estaveis.

## Responsabilidades

### Responsabilidades Do Source

O source deve:

- Enviar o identificador estavel do provider em `provider`.
- Enviar o nome exibivel do provider em `provider_data.provider.name`.
- Enviar metadados do provider, como fabricante, URL de configuracao e imagem.
- Enviar um identificador estavel da conta em `account_data.stable_id`.
- Normalizar todos os sensores em uma lista padronizada.
- Garantir que cada entidade tenha `key` estavel.
- Converter timestamps para ISO 8601 UTC.
- Nao enviar cookies, tokens, HTML bruto, API keys ou segredos.
- Nao depender de email, username ou nome visual para `key`, `provider` ou
  `stable_id`.

### Responsabilidades Da Integracao

A integracao deve:

- Validar o envelope base.
- Validar que `provider_data.contract` e `generic_provider.v1`.
- Validar `provider`, `account_data.stable_id` e as chaves de entidades.
- Criar ou atualizar o device da conta dinamicamente.
- Criar ou atualizar entidades comuns da conta.
- Criar ou atualizar entidades genericas declaradas em
  `provider_data.entities`.
- Ignorar entidades invalidas sem derrubar o webhook inteiro, quando possivel.
- Registrar erro de contrato quando o payload nao puder ser usado.

## Envelope

O envelope base continua parecido com `docs/payload-contract.md`.

Exemplo minimo:

```json
{
  "schema_version": "1.0",
  "source": "browser_extension",
  "source_version": "0.1.0",
  "collected_at": "2026-06-02T15:40:00.000Z",
  "provider": "anthropic_console",
  "status": "ok",
  "account_data": {
    "stable_id": "anthropic-user-123",
    "email": "user@example.com"
  },
  "plan_data": {
    "type": "pro"
  },
  "provider_data": {
    "contract": "generic_provider.v1",
    "provider": {
      "name": "Anthropic Console"
    },
    "entities": []
  },
  "error": null
}
```

## Campos Obrigatorios

### `provider`

Identificador estavel do provider real.

Regras:

- Deve ser enviado pelo source.
- Deve usar `snake_case`.
- Deve conter apenas letras minusculas, numeros e underscore.
- Deve representar o provider ou produto real, nao o modo generico.
- Nao deve mudar quando o nome comercial mudar.

Exemplos validos:

```text
anthropic_console
openrouter
google_ai_studio
mistral_platform
perplexity
```

Exemplos invalidos:

```text
generic
Anthropic Console
anthropic-console
user@example.com
https://console.anthropic.com
```

### `provider_data.contract`

Identifica o contrato generico.

Valor atual:

```text
generic_provider.v1
```

### `provider_data.provider`

Metadados exibiveis do provider.

Formato:

```json
{
  "name": "Anthropic Console",
  "manufacturer": "Anthropic",
  "model": "AI usage account",
  "configuration_url": "https://console.anthropic.com/",
  "image_url": "https://example.com/anthropic.png",
  "icon": "mdi:brain"
}
```

Campos:

| Campo | Obrigatorio | Uso |
| --- | --- | --- |
| `name` | sim | Nome exibivel do provider no device. |
| `manufacturer` | nao | `DeviceInfo.manufacturer`. Se ausente, usar `name`. |
| `model` | nao | `DeviceInfo.model`. Se ausente, usar `Generic AI account`. |
| `configuration_url` | nao | Link de configuracao do provider. |
| `image_url` | nao | Imagem externa ou endpoint local para `entity_picture`. |
| `icon` | nao | Icone padrao para sensores sem icone especifico. |

Observacao: `image_url` so deve apontar para recurso publico e seguro. O source
nao deve enviar imagem base64 no payload.

### `account_data.stable_id`

Identificador estavel da conta no provider.

Para provider generico, este campo deve ser obrigatorio. Sem ele, a integracao
nao tem uma base confiavel para criar `unique_id` e `DeviceInfo.identifiers`.

Formato sugerido:

```json
{
  "stable_id": "anthropic-user-123",
  "account_id": "acct_123",
  "user_id": "user_123",
  "display_name": "Personal",
  "username": "alves-dev",
  "email": "user@example.com"
}
```

Regras:

- `stable_id` pode ser um ID do provider.
- Se o provider nao fornecer ID, o source pode gerar um ID local estavel.
- Nao usar email ou username como `stable_id` diretamente.
- Email e username podem ser atributos de exibicao.

## Dados Genericos

O bloco generico principal e `provider_data.entities`.

```json
{
  "provider_data": {
    "contract": "generic_provider.v1",
    "provider": {
      "name": "Anthropic Console"
    },
    "entities": []
  }
}
```

Cada item em `entities` descreve uma entidade que a integracao deve criar ou
atualizar.

Plataformas aceitas nesta hipotese:

```text
sensor
binary_sensor
```

Outras plataformas, como `image`, `number`, `switch` ou `button`, devem ficar
fora da primeira versao do provider generico.

## Entidade Generica: Sensor

Formato:

```json
{
  "platform": "sensor",
  "key": "daily_usage_percent",
  "name": "Daily usage used",
  "native_value": 42.5,
  "native_unit_of_measurement": "%",
  "device_class": null,
  "state_class": "measurement",
  "entity_category": null,
  "icon": "mdi:gauge",
  "suggested_display_precision": 0,
  "attributes": {
    "window": "daily"
  }
}
```

Campos:

| Campo | Obrigatorio | Uso |
| --- | --- | --- |
| `platform` | sim | Deve ser `sensor`. |
| `key` | sim | Chave estavel da entidade. |
| `name` | sim | Nome da entidade com `has_entity_name = True`. |
| `native_value` | sim | Estado nativo do sensor. Pode ser `null`. |
| `native_unit_of_measurement` | nao | Unidade nativa, como `%`, `s`, `requests`, `USD`. |
| `device_class` | nao | Classe HA quando aplicavel, como `timestamp`, `duration`, `enum`. |
| `state_class` | nao | `measurement`, `total` ou `total_increasing`. |
| `entity_category` | nao | `diagnostic` quando a entidade for tecnica/debug. |
| `icon` | nao | Icone MDI quando nao houver `device_class`. |
| `suggested_display_precision` | nao | Precisao sugerida para valores numericos. |
| `attributes` | nao | Atributos extras pequenos e estaveis. |

Regras para `key`:

```text
^[a-z0-9_]{1,64}$
```

Chaves reservadas que o source nao deve usar em entidades genericas:

```text
account
plan
status
problem
last_error
collected_at
last_received_at
source
request_count
```

Essas chaves pertencem as entidades comuns da conta.

## Entidade Generica: Binary Sensor

Formato:

```json
{
  "platform": "binary_sensor",
  "key": "limit_reached",
  "name": "Limit reached",
  "is_on": false,
  "device_class": "problem",
  "entity_category": null,
  "icon": null,
  "attributes": {
    "reason": null
  }
}
```

Campos:

| Campo | Obrigatorio | Uso |
| --- | --- | --- |
| `platform` | sim | Deve ser `binary_sensor`. |
| `key` | sim | Chave estavel da entidade. |
| `name` | sim | Nome da entidade com `has_entity_name = True`. |
| `is_on` | sim | Booleano. |
| `device_class` | nao | Classe HA, como `problem` ou `connectivity`. |
| `entity_category` | nao | `diagnostic` quando for tecnico/debug. |
| `icon` | nao | Icone MDI quando nao houver `device_class`. |
| `attributes` | nao | Atributos extras pequenos e estaveis. |

## Tipos De Estado

### Numero

Usar para percentuais, contadores, custos, creditos e duracoes.

Exemplo:

```json
{
  "platform": "sensor",
  "key": "monthly_spend_usd",
  "name": "Monthly spend",
  "native_value": 12.34,
  "native_unit_of_measurement": "USD",
  "state_class": "measurement",
  "icon": "mdi:cash"
}
```

### Percentual

Regras:

- `native_value` numerico.
- Unidade `%`.
- Valor recomendado de `0` a `100`.
- `state_class` normalmente `measurement`.

Exemplo:

```json
{
  "platform": "sensor",
  "key": "daily_usage_percent",
  "name": "Daily usage used",
  "native_value": 42.5,
  "native_unit_of_measurement": "%",
  "state_class": "measurement",
  "suggested_display_precision": 1,
  "attributes": {
    "window": "daily"
  }
}
```

### Timestamp

Regras:

- `native_value` deve ser ISO 8601 UTC.
- `device_class` deve ser `timestamp`.

Exemplo:

```json
{
  "platform": "sensor",
  "key": "daily_reset_at",
  "name": "Daily reset at",
  "native_value": "2026-06-03T00:00:00.000Z",
  "device_class": "timestamp",
  "attributes": {
    "window": "daily"
  }
}
```

### Duracao

Regras:

- `native_value` numerico.
- Unidade recomendada: `s`.
- `device_class` deve ser `duration` quando suportado.

Exemplo:

```json
{
  "platform": "sensor",
  "key": "daily_reset_after",
  "name": "Daily reset after",
  "native_value": 3600,
  "native_unit_of_measurement": "s",
  "device_class": "duration",
  "attributes": {
    "reset_at": "2026-06-03T00:00:00.000Z"
  }
}
```

### Texto

Usar para estados textuais pequenos e estaveis.

Exemplo:

```json
{
  "platform": "sensor",
  "key": "active_model",
  "name": "Active model",
  "native_value": "claude-opus-4",
  "icon": "mdi:brain"
}
```

### Enum

Usar quando o conjunto de valores for conhecido.

Exemplo:

```json
{
  "platform": "sensor",
  "key": "quota_state",
  "name": "Quota state",
  "native_value": "available",
  "device_class": "enum",
  "options": [
    "available",
    "limited",
    "exhausted",
    "unknown"
  ],
  "icon": "mdi:list-status"
}
```

## Device Criado

Para cada `provider + account_data.stable_id`, a integracao cria um device de
conta.

Entrada:

```json
{
  "provider": "anthropic_console",
  "account_data": {
    "stable_id": "anthropic-user-123",
    "email": "user@example.com"
  },
  "provider_data": {
    "provider": {
      "name": "Anthropic Console",
      "manufacturer": "Anthropic",
      "model": "Console account",
      "configuration_url": "https://console.anthropic.com/"
    }
  }
}
```

`DeviceInfo` resultante:

```json
{
  "identifiers": [["ai_usage", "<config_entry_id>:anthropic_console:acct_43aeb78c10cc0172"]],
  "entry_type": "service",
  "manufacturer": "Anthropic",
  "model": "Console account",
  "name": "AI Usage Anthropic Console user@example.com",
  "via_device": ["ai_usage", "<config_entry_id>"],
  "configuration_url": "https://console.anthropic.com/"
}
```

Regras de nome:

```text
device_name = "AI Usage " + provider_data.provider.name + " " + account_label
```

`account_label` deve seguir esta ordem:

```text
account_data.display_name
account_data.email
account_data.username
account_data.account_id
account_data.user_id
account_data.stable_id
account_key
```

## Unique IDs

O `provider` e o `stable_id` devem ser usados apenas como entrada para gerar uma
chave opaca.

Formato recomendado:

```text
account_key = "acct_" + sha256("<provider>:stable_id:<stable_id>")[0:16]
device_key = "<config_entry_id>:<provider>:<account_key>"
common_entity_unique_id = "<device_key>:<common_key>"
generic_entity_unique_id = "<device_key>:generic:<entity.key>"
```

Exemplo:

```text
provider = "anthropic_console"
stable_id = "anthropic-user-123"
account_key = "acct_43aeb78c10cc0172"
unique_id daily_usage_percent = "<config_entry_id>:anthropic_console:acct_43aeb78c10cc0172:generic:daily_usage_percent"
```

## Sensores Comuns Criados

Mesmo no provider generico, a integracao deve criar os sensores comuns definidos
no contrato de devices e sensores.

Exemplo de `sensor.account`:

```yaml
platform: sensor
unique_id: "<device_key>:account"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Account"
native_value: "user@example.com"
entity_picture: "https://example.com/anthropic.png"
attributes:
  provider: anthropic_console
  provider_name: "Anthropic Console"
  account_key: "acct_43aeb78c10cc0172"
  account_key_quality: stable
  stable_id: "anthropic-user-123"
  email: "user@example.com"
  plan_type: pro
```

Exemplo de `sensor.plan`:

```yaml
platform: sensor
unique_id: "<device_key>:plan"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Plan"
device_class: enum
native_value: pro
attributes:
  provider: anthropic_console
```

Exemplo de `sensor.status`:

```yaml
platform: sensor
unique_id: "<device_key>:status"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Status"
device_class: enum
native_value: ok
attributes:
  provider: anthropic_console
  generic_contract: "generic_provider.v1"
```

Exemplo de `binary_sensor.problem`:

```yaml
platform: binary_sensor
unique_id: "<device_key>:problem"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Problem"
device_class: problem
is_on: false
attributes:
  status: ok
  error_code: null
```

## Sensores Genericos Criados

A integracao deve criar uma entidade para cada item valido em
`provider_data.entities`.

### Sensor Numerico

Payload:

```json
{
  "platform": "sensor",
  "key": "daily_usage_percent",
  "name": "Daily usage used",
  "native_value": 42.5,
  "native_unit_of_measurement": "%",
  "state_class": "measurement",
  "suggested_display_precision": 1,
  "attributes": {
    "window": "daily"
  }
}
```

Entidade criada:

```yaml
platform: sensor
unique_id: "<device_key>:generic:daily_usage_percent"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Daily usage used"
native_value: 42.5
native_unit_of_measurement: "%"
state_class: measurement
suggested_display_precision: 0
attributes:
  window: daily
```

### Sensor Timestamp

Payload:

```json
{
  "platform": "sensor",
  "key": "daily_reset_at",
  "name": "Daily reset at",
  "native_value": "2026-06-03T00:00:00.000Z",
  "device_class": "timestamp",
  "attributes": {
    "window": "daily"
  }
}
```

Entidade criada:

```yaml
platform: sensor
unique_id: "<device_key>:generic:daily_reset_at"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Daily reset at"
device_class: timestamp
native_value: "2026-06-03T00:00:00+00:00"
attributes:
  window: daily
```

### Sensor Enum

Payload:

```json
{
  "platform": "sensor",
  "key": "quota_state",
  "name": "Quota state",
  "native_value": "available",
  "device_class": "enum",
  "options": [
    "available",
    "limited",
    "exhausted",
    "unknown"
  ]
}
```

Entidade criada:

```yaml
platform: sensor
unique_id: "<device_key>:generic:quota_state"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Quota state"
device_class: enum
options:
  - available
  - limited
  - exhausted
  - unknown
native_value: available
```

### Binary Sensor

Payload:

```json
{
  "platform": "binary_sensor",
  "key": "limit_reached",
  "name": "Limit reached",
  "is_on": false,
  "device_class": "problem",
  "attributes": {
    "reason": null
  }
}
```

Entidade criada:

```yaml
platform: binary_sensor
unique_id: "<device_key>:generic:limit_reached"
device: "AI Usage Anthropic Console user@example.com"
has_entity_name: true
name: "Limit reached"
device_class: problem
is_on: false
attributes:
  reason: null
```

## Payload Completo De Exemplo

```json
{
  "schema_version": "1.0",
  "source": "browser_extension",
  "source_version": "0.1.0",
  "collected_at": "2026-06-02T15:40:00.000Z",
  "provider": "anthropic_console",
  "status": "ok",
  "account_data": {
    "stable_id": "anthropic-user-123",
    "account_id": "acct_123",
    "display_name": "Personal",
    "email": "user@example.com"
  },
  "plan_data": {
    "type": "pro",
    "display_name": "Pro"
  },
  "provider_data": {
    "contract": "generic_provider.v1",
    "provider": {
      "name": "Anthropic Console",
      "manufacturer": "Anthropic",
      "model": "Console account",
      "configuration_url": "https://console.anthropic.com/",
      "image_url": "https://example.com/anthropic.png",
      "icon": "mdi:brain"
    },
    "entities": [
      {
        "platform": "sensor",
        "key": "daily_usage_percent",
        "name": "Daily usage used",
        "native_value": 42.5,
        "native_unit_of_measurement": "%",
        "state_class": "measurement",
        "suggested_display_precision": 1,
        "attributes": {
          "window": "daily"
        }
      },
      {
        "platform": "sensor",
        "key": "daily_reset_at",
        "name": "Daily reset at",
        "native_value": "2026-06-03T00:00:00.000Z",
        "device_class": "timestamp",
        "attributes": {
          "window": "daily"
        }
      },
      {
        "platform": "sensor",
        "key": "quota_state",
        "name": "Quota state",
        "native_value": "available",
        "device_class": "enum",
        "options": [
          "available",
          "limited",
          "exhausted",
          "unknown"
        ]
      },
      {
        "platform": "binary_sensor",
        "key": "limit_reached",
        "name": "Limit reached",
        "is_on": false,
        "device_class": "problem",
        "attributes": {
          "reason": null
        }
      }
    ]
  },
  "error": null
}
```

## Exemplo De Erro

Quando o source consegue identificar provider e conta, o erro pertence ao device
da conta.

```json
{
  "schema_version": "1.0",
  "source": "browser_extension",
  "source_version": "0.1.0",
  "collected_at": "2026-06-02T15:40:00.000Z",
  "provider": "anthropic_console",
  "status": "not_authenticated",
  "account_data": {
    "stable_id": "anthropic-user-123",
    "email": "user@example.com"
  },
  "plan_data": {},
  "provider_data": {
    "contract": "generic_provider.v1",
    "provider": {
      "name": "Anthropic Console"
    },
    "entities": []
  },
  "error": {
    "code": "not_authenticated",
    "message": "User is not logged in"
  }
}
```

Entidades atualizadas:

```yaml
device: "AI Usage Anthropic Console user@example.com"
entity: "sensor.status"
native_value: not_authenticated
```

```yaml
device: "AI Usage Anthropic Console user@example.com"
entity: "binary_sensor.problem"
is_on: true
attributes:
  error_code: not_authenticated
  error_message: "User is not logged in"
```

```yaml
device: "AI Usage Anthropic Console user@example.com"
entity: "sensor.last_error"
native_value: not_authenticated
attributes:
  message: "User is not logged in"
```

## Validacao

A integracao deve rejeitar o payload inteiro quando:

- `provider` estiver ausente, vazio ou invalido.
- `provider_data.contract` nao for `generic_provider.v1`.
- `provider_data.provider.name` estiver ausente.
- `account_data.stable_id` estiver ausente.
- `provider_data.entities` nao for uma lista.

A integracao pode aceitar o payload e ignorar apenas uma entidade quando:

- `entity.key` for invalido.
- `entity.key` colidir com chave reservada.
- `entity.platform` nao for suportado.
- `native_value` tiver tipo incompativel com `device_class`.
- `options` de enum nao contiver `native_value`.
- `attributes` nao for objeto.

Quando uma entidade for ignorada, o device da integracao deve registrar um erro
diagnostico, por exemplo:

```yaml
entity: "sensor.last_ingest_status"
native_value: invalid_contract
attributes:
  ignored_entities:
    - key: "bad key"
      reason: "invalid_key"
```

## Atributos

Atributos devem ser pequenos, estaveis e uteis para automacoes ou dashboards.

Permitido:

```json
{
  "window": "daily",
  "limit": 100,
  "reset_at": "2026-06-03T00:00:00.000Z"
}
```

Evitar:

```json
{
  "raw_payload": {},
  "html": "<html>...</html>",
  "token": "secret",
  "events": []
}
```

Regra pratica: se um atributo muda sempre e e importante, ele provavelmente
deve ser uma entidade propria.

## Diferenca Entre Provider Especifico E Generico

Provider especifico:

```text
provider = codex
provider_data.rate_limit.primary_window.used_percent
```

Vantagem:

- A integracao conhece a semantica.
- Pode criar sensores nomeados e otimizados.
- Pode validar regras especificas do provider.

Provider generico:

```text
provider = anthropic_console
provider_data.contract = generic_provider.v1
provider_data.entities[0].key = daily_usage_percent
```

Vantagem:

- A integracao nao precisa conhecer o provider antes.
- O source controla quais sensores fazem sentido.
- Novos providers podem ser adicionados sem mudar codigo.

Custo:

- O source precisa fazer mais trabalho.
- A integracao confia menos na semantica.
- Erros de nomenclatura no source podem gerar sensores ruins ou inconsistentes.

## Decisao Recomendada

Se essa hipotese virar contrato real, a recomendacao e:

1. Manter `provider` como identificador real do provider.
2. Usar `provider_data.contract = "generic_provider.v1"` para ativar o modo
   generico.
3. Tornar `account_data.stable_id` obrigatorio para provider generico.
4. Aceitar apenas `sensor` e `binary_sensor` na primeira versao.
5. Usar `provider_data.entities` como lista declarativa de entidades.
6. Criar `unique_id` opaco com hash de `provider + stable_id`.
7. Tratar provider generico como caminho de extensibilidade, nao como substituto
   dos providers especificos quando a integracao precisar conhecer a semantica.

## Perguntas Em Aberto

- A integracao deve permitir `image_url` externa ou servir apenas imagens locais
  cadastradas pelo provider?
- Entidades genericas devem ser removidas quando somem do payload, ou apenas
  ficar `unknown`?
- O source pode mudar `name` de uma entidade sem quebrar dashboards?
- Deve existir uma allowlist de `device_class`, `state_class` e unidades?
- O contrato deve aceitar uma entidade desabilitada por padrao com payload bruto
  sanitizado para debug?
