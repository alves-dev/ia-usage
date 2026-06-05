# AI Usage - Implementation Spec

Este documento define o plano de implementacao real da integracao Home
Assistant `ai_usage`, apos a POC de webhook.

A POC validou o recebimento do webhook e o fluxo basico de atualizacao de
sensores. A implementacao real deve substituir o modelo atual por uma
arquitetura orientada aos contratos ja definidos em:

- `docs/payload-contract.md`
- `docs/device-and-sensor-contract.md`

O objetivo deste documento e deixar as tarefas divididas e suficientemente
claras para uma implementacao posterior, sem exigir novas decisoes tecnicas
durante a execucao.

## Decisoes Da V1

- Implementar suporte real apenas para os providers `codex` e `ollama_cloud`.
- Nao implementar provider generico na v1.
- Manter o provider generico como fase futura, usando
  `docs/generic-provider-contract.md` apenas como referencia.
- Manter a pasta `custom_components/ai_usage/brand/` para logos da integracao.
- Criar uma pasta separada para imagens dos providers.
- Usar `entity_picture` no `sensor.account` para expor a imagem do provider.
- Nao criar `ImageEntity` na v1.
- Nao gravar payload bruto como atributo das entidades por padrao.
- Nao criar entidade diagnostica desabilitada com payload resumido na v1.
- Nao migrar entidades antigas da POC.
- Usar Home Assistant `2026.5` como versao minima alvo.
- Usar `codex.png` e `ollama_cloud.png` como nomes finais das imagens dos
  providers.
- Aceitar imagens placeholders na primeira implementacao.
- Devices e entidades de conta devem ser criados dinamicamente quando o servico
  de ingestao processar uma conta nova.
- O processamento do payload nao deve ficar acoplado ao webhook. O webhook deve
  ser apenas um adapter de transporte que chama um servico interno de ingestao.

## Estado Atual Da POC

A implementacao atual esta organizada principalmente em:

- `custom_components/ai_usage/runtime.py`
- `custom_components/ai_usage/models.py`
- `custom_components/ai_usage/sensor.py`
- `custom_components/ai_usage/providers/`
- `custom_components/ai_usage/const.py`

O comportamento atual da POC:

- Registra um webhook configuravel via config flow.
- Aceita payload JSON via `POST`.
- Valida somente se o payload e objeto, se possui `provider` e se o provider e
  conhecido.
- Cria estados fixos por provider em `ProviderState`.
- Cria sensores fixos para cada provider listado em `SUPPORTED_PROVIDERS`.
- Trata payload como dados genericos de request/model/tokens/custo/duracao.
- Guarda `last_payload` e `normalized` como atributos.

O comportamento desejado para a implementacao real:

- Validar o contrato completo do payload.
- Separar erro de ingestao, erro de contrato e erro reportado pelo provider.
- Criar device pai da integracao.
- Criar devices dinamicos por conta de provider.
- Atualizar entidades comuns e especificas por conta.
- Persistir contas conhecidas para sobreviver a reload/restart.
- Expor imagens locais dos providers via `entity_picture`.
- Processar payloads por um servico reutilizavel, para permitir que no futuro a
  propria integracao gere payloads internamente sem passar pelo webhook.

## Escopo

### Dentro Do Escopo

- Webhook com validacao contratual.
- Estado interno por `provider + account_key`.
- Persistencia de contas conhecidas.
- Restore de entidades quando aplicavel.
- Device pai da integracao.
- Devices dinamicos de contas.
- Sensores comuns por conta.
- Binary sensors comuns por conta.
- Sensores especificos de `codex`.
- Sensores especificos de `ollama_cloud`.
- Imagens locais dos providers.
- Testes automatizados do webhook, identidade, devices e entidades.

### Fora Do Escopo Na V1

- Provider generico.
- `ImageEntity`.
- Entidades `number`, `switch`, `button` ou `select`.
- Debug entity com payload bruto.
- Migracao de entidades antigas da POC.
- Suporte a providers fora de `codex` e `ollama_cloud`.

## Estrutura De Arquivos Planejada

Manter:

```text
custom_components/ai_usage/brand/
```

Essa pasta continua sendo usada para logos da integracao. As imagens atuais
podem ser placeholders, mas a pasta deve continuar existindo.

Adicionar:

```text
custom_components/ai_usage/provider_images/
custom_components/ai_usage/provider_images/codex.png
custom_components/ai_usage/provider_images/ollama_cloud.png
```

Essa nova pasta sera usada para imagens dos providers exibidas nas entidades de
conta.

Atualizar ou criar modulos:

```text
custom_components/ai_usage/binary_sensor.py
custom_components/ai_usage/models.py
custom_components/ai_usage/runtime.py
custom_components/ai_usage/sensor.py
custom_components/ai_usage/const.py
custom_components/ai_usage/providers/base.py
custom_components/ai_usage/providers/codex.py
custom_components/ai_usage/providers/ollama_cloud.py
```

Possiveis novos modulos, se a implementacao ficar mais clara:

```text
custom_components/ai_usage/identity.py
custom_components/ai_usage/storage.py
custom_components/ai_usage/validation.py
custom_components/ai_usage/images.py
custom_components/ai_usage/ingestion.py
```

A criacao desses modulos e recomendada se evitar concentrar validacao,
persistencia e runtime em um unico arquivo.

## Constantes E Plataformas

Atualizar `custom_components/ai_usage/const.py`:

- Manter `DOMAIN = "ai_usage"`.
- Manter `CONF_WEBHOOK_ID = "webhook_id"`.
- Manter providers conhecidos:
  - `codex`
  - `ollama_cloud`
- Atualizar `PLATFORMS` para incluir:
  - `Platform.SENSOR`
  - `Platform.BINARY_SENSOR`
- Adicionar constantes para:
  - versao do schema aceito: `1.0`
  - sources conhecidos
  - statuses conhecidos
  - erros de ingestao
  - chaves das entidades comuns
  - chaves das entidades especificas
  - caminhos das imagens dos providers

## Registro De Imagens Dos Providers

Durante `async_setup_entry`, registrar um caminho estatico local para imagens
dos providers.

Endpoint recomendado:

```text
/api/ai_usage/provider_images/<provider>.png
```

Mapeamento esperado:

```text
codex        -> /api/ai_usage/provider_images/codex.png
ollama_cloud -> /api/ai_usage/provider_images/ollama_cloud.png
```

O `sensor.account` deve usar esse endpoint em `entity_picture`.

Tarefa de implementacao:

- Criar helper para registrar static path uma unica vez por instancia do HA.
- Usar API moderna do Home Assistant para static paths.
- Garantir que a ausencia de uma imagem nao quebre a ingestao do webhook.
- Se a imagem do provider estiver ausente, deixar `entity_picture = None`.

Decisao:

- A versao minima alvo e Home Assistant `2026.5`; usar a API atual de static
  paths sem fallback para versoes antigas.

## Arquitetura De Ingestao

A implementacao real deve separar transporte de processamento.

O webhook nao deve conter a regra de negocio da ingestao. Ele deve apenas:

1. Ler a request HTTP.
2. Converter a request em payload Python.
3. Chamar um servico interno de ingestao.
4. Converter `IngestResult` em resposta HTTP.

O processamento deve ficar em um servico reutilizavel, por exemplo
`AIUsageIngestionService`.

Interface recomendada:

```text
async_ingest_payload(
    payload: object,
    *,
    received_at: datetime,
    transport: str,
    context: Mapping[str, Any] | None = None,
) -> IngestResult
```

Valores esperados para `transport` na v1:

```text
webhook
```

Valores futuros possiveis:

```text
integration_collector
manual_service
test
```

Responsabilidades do servico de ingestao:

- Validar se o payload e objeto.
- Validar o envelope contratual.
- Validar provider e dados especificos.
- Resolver identidade da conta.
- Atualizar estado do device pai.
- Criar ou atualizar estado de conta.
- Persistir contas conhecidas.
- Disparar signals de atualizacao.
- Retornar `IngestResult`.

Responsabilidades do webhook:

- Tratar erro de JSON invalido.
- Chamar o servico de ingestao com `transport = "webhook"`.
- Mapear `IngestResult.http_status` para a resposta HTTP.
- Nao conhecer detalhes de sensores, devices, storage ou providers alem do
  necessario para log basico.

Beneficio esperado:

- No futuro, se a propria integracao coletar dados diretamente, ela podera
  chamar `async_ingest_payload()` com `transport = "integration_collector"` sem
  criar uma request HTTP artificial e sem duplicar regras de validacao.

## Modelos Internos

Substituir os modelos orientados a POC por modelos alinhados ao contrato.

Modelos recomendados:

```text
PayloadEnvelope
ProviderError
AccountIdentity
ProviderMetadata
AccountState
IntegrationState
IngestResult
IngestContext
```

### PayloadEnvelope

Representa o envelope validado do payload.

Campos:

- `schema_version`
- `source`
- `source_version`
- `collected_at`
- `provider`
- `status`
- `account_data`
- `plan_data`
- `provider_data`
- `error`

### ProviderError

Representa `error` do payload.

Campos:

- `code`
- `message`

### AccountIdentity

Representa a identidade resolvida da conta.

Campos:

- `provider`
- `account_key`
- `account_key_quality`
- `id_kind`
- `id_value`
- `label`

Valores esperados para `account_key_quality`:

- `stable`
- `email_hash`

### ProviderMetadata

Representa metadados exibiveis do provider.

Campos:

- `provider`
- `provider_name`
- `manufacturer`
- `model`
- `configuration_url`
- `entity_picture`

### AccountState

Representa o estado mutavel de uma conta.

Campos minimos:

- `provider`
- `account_key`
- `account_key_quality`
- `account_label`
- `account_data`
- `plan_data`
- `provider_data`
- `status`
- `error`
- `source`
- `source_version`
- `schema_version`
- `collected_at`
- `last_received_at`
- `request_count`

### IntegrationState

Representa o estado do device pai.

Campos minimos:

- `last_ingest_status`
- `last_ingest_error_message`
- `last_webhook_received_at`
- `last_source`
- `last_source_version`
- `last_schema_version`
- `last_provider`
- `last_account_key`
- `known_accounts`
- `known_accounts_by_provider`
- `last_unscoped_error`
- `last_unscoped_error_message`

### IngestResult

Representa o resultado de uma ingestao de payload, independentemente do
transporte usado para entregar esse payload.

Campos:

- `ok`
- `http_status`
- `ingest_status`
- `provider`
- `account_key`
- `created_account`
- `message`

### IngestContext

Representa metadados da origem que chamou o servico de ingestao.

Campos:

- `transport`
- `received_at`
- `webhook_id`
- `request_remote`

Regras:

- `webhook_id` e `request_remote` sao opcionais e especificos do webhook.
- O servico de ingestao nao deve depender desses campos para validar provider,
  conta ou entidades.
- Chamadas internas futuras devem conseguir criar `IngestContext` sem dados de
  webhook.

## Validacao Do Webhook

O webhook deve seguir o contrato de `docs/payload-contract.md`, mas a validacao
de contrato deve ficar no servico de ingestao, nao no handler HTTP.

Fluxo:

1. Ler JSON da request.
2. Se JSON invalido, responder `400` com `invalid_json`.
3. Chamar `AIUsageIngestionService.async_ingest_payload()`.
4. O servico valida se o payload e objeto.
5. O servico valida envelope base.
6. O servico valida `provider`.
7. O servico valida `status`.
8. O servico valida coerencia de `error`.
9. O servico valida campos especificos do provider.
10. O servico resolve identidade da conta.
11. O servico atualiza device pai.
12. O servico atualiza ou cria conta.
13. O servico dispara atualizacao das entidades.
14. O webhook responde JSON com o `IngestResult`.

### Erros De Ingestao

Estados aceitos para `sensor.last_ingest_status`:

```text
ok
invalid_json
payload_must_be_object
missing_provider
unsupported_provider
invalid_contract
account_unidentified
unknown_error
```

Regras:

- Erro de ingestao representa problema do webhook ou contrato.
- Erro do provider representa `payload.status != "ok"`.
- Um payload com `status = not_authenticated` pode ser contratualmente valido.
- Um payload valido sem conta identificavel deve atualizar
  `last_unscoped_error`.

### Erros Do Provider

Estados aceitos no payload:

```text
ok
not_authenticated
provider_unavailable
parse_error
rate_limited
ha_unavailable
unknown_error
```

Regras:

- Se `status = ok`, `error` deve ser `null`.
- Se `status != ok`, `error.code` e `error.message` devem existir.
- Se `status != ok` mas a conta for identificavel, atualizar o device da conta.
- Se `status != ok` e a conta nao for identificavel, atualizar
  `sensor.last_unscoped_error` no device pai.

## Identificacao De Conta

Usar a ordem definida em `docs/device-and-sensor-contract.md`.

Ordem:

1. `account_data.account_id`
2. `account_data.user_id`
3. hash de `provider + email normalizado`

Formato:

```text
account_key = "acct_" + sha256("<provider>:<id_kind>:<id_value>")[0:16]
device_key = "<config_entry_id>:<provider>:<account_key>"
entity_unique_id = "<device_key>:<entity_key>"
```

Normalizacao de email:

- Converter para string.
- Aplicar `strip()`.
- Aplicar lowercase.
- Rejeitar string vazia.

Regras:

- Nunca usar email cru, username ou nome visual em `unique_id`.
- Email e username podem aparecer como atributos de exibicao.
- Se nao houver `account_id`, `user_id` ou email, a conta nao deve ser criada.
- Para `ollama_cloud`, usar hash do email normalizado, pois o contrato atual nao
  fornece ID estavel de conta.

## Persistencia

A integracao deve persistir contas conhecidas para que devices dinamicos
reaparecam apos reload/restart.

Usar storage local do Home Assistant.

Conteudo minimo do storage:

```json
{
  "version": 1,
  "accounts": [
    {
      "provider": "codex",
      "account_key": "acct_4f8b2d9a5e7c1031",
      "account_key_quality": "stable",
      "account_label": "user@example.com",
      "account_data": {},
      "plan_data": {},
      "provider_name": "Codex",
      "request_count": 42,
      "last_seen_at": "2026-06-02T15:40:01+00:00"
    }
  ]
}
```

Regras:

- Persistir somente dados pequenos e necessarios para recriar devices.
- Nao persistir payload bruto.
- Nao persistir segredos.
- Salvar storage quando uma conta nova for criada.
- Salvar storage quando metadados persistidos da conta mudarem.
- Evitar escrita em storage em toda request se nada persistivel mudou.

## Restore De Entidades

Usar `RestoreEntity` nas entidades dinamicas para recuperar ultimo estado quando
possivel.

Regras:

- O storage recria a entidade.
- O restore recupera o ultimo estado conhecido.
- O webhook continua sendo a fonte de verdade para novas atualizacoes.
- Se nao houver estado restaurado, usar `unknown` ate a primeira request
  aplicavel.

## Devices

### Device Pai Da Integracao

Representa a instancia configurada da integracao.

Identificador:

```text
("ai_usage", "<config_entry_id>")
```

DeviceInfo:

```text
entry_type: service
manufacturer: AI Usage
model: Webhook collector
name: AI Usage Webhook
sw_version: versao da integracao
```

Entidades associadas:

- `sensor.last_ingest_status`
- `binary_sensor.webhook_problem`
- `sensor.last_webhook_received_at`
- `sensor.last_source` desabilitado por padrao
- `sensor.known_accounts`
- `sensor.last_unscoped_error` desabilitado por padrao

### Device De Conta

Representa uma conta observada em um provider.

Identificador:

```text
("ai_usage", "<config_entry_id>:<provider>:<account_key>")
```

Regras:

- `entry_type = service`
- `via_device` aponta para o device pai.
- `name = "AI Usage " + provider_name + " " + account_label`
- `manufacturer`, `model` e `configuration_url` devem vir de metadados
  conhecidos do provider.

Metadados por provider:

```text
codex:
  provider_name: Codex
  manufacturer: OpenAI
  model: Codex account
  configuration_url: https://chatgpt.com/

ollama_cloud:
  provider_name: Ollama Cloud
  manufacturer: Ollama
  model: Ollama Cloud account
  configuration_url: https://ollama.com/settings
```

## Entidades Do Device Pai

Todas devem ter:

- `unique_id`
- `has_entity_name = True`
- `should_poll = False`
- device info do device pai

### sensor.last_ingest_status

Estado:

- ultimo status de ingestao do webhook.

Categoria:

- `diagnostic`

Device class:

- `enum`

Estados:

```text
ok
invalid_json
payload_must_be_object
missing_provider
unsupported_provider
invalid_contract
account_unidentified
unknown_error
```

Atributos:

- `last_received_at`
- `webhook_id`
- `last_error_message`

### binary_sensor.webhook_problem

Estado:

```text
is_on = last_ingest_status != "ok"
```

Categoria:

- `diagnostic`

Device class:

- `problem`

Atributos:

- `last_ingest_status`
- `last_error_message`

### sensor.last_webhook_received_at

Estado:

- timestamp em que o HA recebeu a ultima request.

Device class:

- `timestamp`

Categoria:

- `diagnostic`

### sensor.last_source

Estado:

- `source` do ultimo payload valido.

Categoria:

- `diagnostic`

Atributos:

- `source_version`
- `schema_version`
- `provider`
- `account_key`

### sensor.known_accounts

Estado:

- quantidade total de contas conhecidas.

Categoria:

- `diagnostic`

Unidade:

- `accounts`

Atributos:

- contagem por provider.

### sensor.last_unscoped_error

Estado:

- `none` ou codigo do ultimo erro sem conta identificavel.

Categoria:

- `diagnostic`

Atributos:

- `provider`
- `message`
- `received_at`

## Entidades Comuns Por Conta

Todas as entidades comuns devem existir para todo device de conta.

### sensor.account

Estado:

```text
account_data.email
account_data.username
account_data.account_id
account_data.user_id
account_key
```

Usar o primeiro valor disponivel nessa ordem.

Atributos:

- `provider`
- `provider_name`
- `account_key`
- `account_key_quality`
- `account_id`
- `user_id`
- `username`
- `email`
- `plan_type`

Imagem:

- `entity_picture` aponta para a imagem local do provider.

Categoria:

- `diagnostic`

### sensor.plan

Estado:

- `plan_data.type`

Device class:

- `enum`, quando as opcoes conhecidas forem configuradas.

Opcoes recomendadas:

```text
free
plus
pro
team
enterprise
unknown
```

### sensor.status

Estado:

- `status` do envelope.

Device class:

- `enum`

Estados:

```text
ok
not_authenticated
provider_unavailable
parse_error
rate_limited
ha_unavailable
unknown_error
```

### binary_sensor.problem

Estado:

```text
is_on = status != "ok"
```

Device class:

- `problem`

Atributos:

- `status`
- `error_code`
- `error_message`

### sensor.last_error

Desabilitado por padrao.

Estado:

- `none` quando nao houver erro.
- `error.code` quando houver erro.

Atributos:

- `message`
- `status`

### sensor.collected_at

Desabilitado por padrao.

Estado:

- `collected_at` do payload.

Device class:

- `timestamp`

Categoria:

- `diagnostic`

### sensor.last_received_at

Desabilitado por padrao.

Estado:

- timestamp em que o HA recebeu a request.

Device class:

- `timestamp`

Categoria:

- `diagnostic`

### sensor.source

Desabilitado por padrao.

Estado:

- `source` do payload.

Device class:

- `enum`, quando possivel.

Estados conhecidos:

```text
browser_extension
shell_script
python_collector
manual_test
```

Atributos:

- `source_version`
- `schema_version`

Categoria:

- `diagnostic`

### sensor.request_count

Desabilitado por padrao.

Estado:

- contador de payloads aceitos para a conta.

Unidade:

- `requests`

State class:

- `total_increasing`

Categoria:

- `diagnostic`

## Entidades Especificas Do Codex

Origem:

```text
provider_data.rate_limit
```

### binary_sensor.allowed

Mapeamento:

```text
provider_data.rate_limit.allowed -> is_on
```

Atributos:

- `limit_reached`
- `five_hour_usage_used_percent`
- `five_hour_usage_available_percent`
- `weekly_usage_used_percent`
- `weekly_usage_available_percent`

### binary_sensor.limit_reached

Mapeamento:

```text
provider_data.rate_limit.limit_reached -> is_on
```

Device class:

- `problem`

### sensor.five_hour_usage_used_percent

Mapeamento:

```text
provider_data.rate_limit.primary_window.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.five_hour_usage_available_percent

Mapeamento:

```text
100 - provider_data.rate_limit.primary_window.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.five_hour_usage_reset_at

Mapeamento:

```text
provider_data.rate_limit.primary_window.reset_at
```

Conversao:

- Unix epoch seconds para `datetime` timezone-aware em UTC.

Device class:

- `timestamp`

### sensor.five_hour_usage_reset_after

Mapeamento:

```text
provider_data.rate_limit.primary_window.reset_after_seconds
```

Conversao:

- segundos do payload para horas no estado da entidade.

Unidade:

- `h`

Device class:

- `duration`, quando disponivel.

### sensor.weekly_usage_used_percent

Mapeamento:

```text
provider_data.rate_limit.secondary_window.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.weekly_usage_available_percent

Mapeamento:

```text
100 - provider_data.rate_limit.secondary_window.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.weekly_usage_reset_at

Mapeamento:

```text
provider_data.rate_limit.secondary_window.reset_at
```

Conversao:

- Unix epoch seconds para `datetime` timezone-aware em UTC.

Device class:

- `timestamp`

### sensor.weekly_usage_reset_after

Mapeamento:

```text
provider_data.rate_limit.secondary_window.reset_after_seconds
```

Conversao:

- segundos do payload para horas no estado da entidade.

Unidade:

- `h`

Device class:

- `duration`, quando disponivel.

## Entidades Especificas Do Ollama Cloud

Origem:

```text
provider_data.session_usage
provider_data.weekly_usage
```

### sensor.session_usage_used_percent

Mapeamento:

```text
provider_data.session_usage.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.session_usage_available_percent

Mapeamento:

```text
100 - provider_data.session_usage.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.session_usage_reset_at

Mapeamento:

```text
provider_data.session_usage.reset_at
```

Conversao:

- ISO 8601 UTC para `datetime` timezone-aware em UTC.

Device class:

- `timestamp`

### sensor.weekly_usage_used_percent

Mapeamento:

```text
provider_data.weekly_usage.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.weekly_usage_available_percent

Mapeamento:

```text
100 - provider_data.weekly_usage.used_percent
```

Unidade:

- `%`

State class:

- `measurement`

Precisao sugerida:

- 0 casas decimais.

### sensor.weekly_usage_reset_at

Mapeamento:

```text
provider_data.weekly_usage.reset_at
```

Conversao:

- ISO 8601 UTC para `datetime` timezone-aware em UTC.

Device class:

- `timestamp`

## Atualizacao Dinamica De Entidades

O runtime deve permitir que plataformas adicionem entidades quando uma conta nova
for descoberta.

Fluxo recomendado:

1. `sensor.async_setup_entry` registra callback no runtime para adicionar
   sensores.
2. `binary_sensor.async_setup_entry` registra callback no runtime para adicionar
   binary sensors.
3. Ao carregar contas persistidas, o runtime solicita criacao das entidades.
4. Ao receber conta nova via webhook, o runtime persiste a conta e solicita
   criacao das entidades.
5. Ao receber nova amostra de conta existente, o runtime atualiza estado e
   dispara dispatcher signal.

Regras:

- Entidades nao devem fazer I/O em propriedades.
- Entidades devem ler estado em memoria.
- Entidades devem chamar `async_write_ha_state()` ao receber signal.
- Uma conta nova nao deve exigir reload da integracao para aparecer.

## Provider Handlers

Os handlers atuais em `custom_components/ai_usage/providers/` devem deixar de
normalizar tokens/custo/duracao da POC e passar a validar/mapear dados do
contrato real.

### Handler Base

Responsabilidades:

- Validar envelope comum, ou delegar para validador central.
- Fornecer interface comum para providers.
- Retornar metadados do provider.
- Retornar lista de entidades especificas do provider.
- Validar provider data especifico.

### Handler Codex

Responsabilidades:

- Validar `provider_data.rate_limit`.
- Validar campos booleanos `allowed` e `limit_reached`.
- Validar janelas `primary_window` e `secondary_window`.
- Validar percentuais numericos.
- Validar `reset_at` como Unix epoch seconds.
- Validar `reset_after_seconds` como numero.

### Handler Ollama Cloud

Responsabilidades:

- Validar `provider_data.session_usage`.
- Validar `provider_data.weekly_usage`.
- Validar percentuais numericos.
- Validar `reset_at` como ISO 8601 UTC.
- Aceitar `account_data.username` e `account_data.email`.
- Exigir email para criar conta na v1, pois e o fallback aprovado de identidade.

## Respostas Do Webhook

Resposta de sucesso com conta identificada:

```json
{
  "ok": true,
  "ingest_status": "ok",
  "provider": "codex",
  "account_key": "acct_4f8b2d9a5e7c1031",
  "created_account": false
}
```

Resposta de payload valido sem conta identificavel:

```json
{
  "ok": false,
  "ingest_status": "account_unidentified",
  "provider": "codex",
  "account_key": null
}
```

Resposta de contrato invalido:

```json
{
  "ok": false,
  "ingest_status": "invalid_contract",
  "message": "account_data must be an object"
}
```

Codigos HTTP recomendados:

- `200` para payload aceito e aplicado.
- `202` para payload contratualmente valido, mas sem conta identificavel.
- `400` para JSON invalido, payload nao objeto ou contrato invalido.
- `400` para provider nao suportado.

## Eventos E Dispatcher

Manter evento de webhook recebido, mas atualizar payload do evento.

Evento:

```text
ai_usage_webhook_received
```

Dados:

- `entry_id`
- `provider`
- `account_key`
- `ingest_status`
- `provider_status`
- `created_account`
- `known_accounts`

Dispatcher signals recomendados:

```text
ai_usage_<entry_id>_integration_updated
ai_usage_<entry_id>_<provider>_<account_key>_updated
ai_usage_<entry_id>_accounts_changed
```

## Config Flow

Manter config flow atual com webhook configuravel.

Tarefas:

- Verificar se `strings.json` cobre:
  - criacao da config entry
  - reconfigure do webhook
  - erro `invalid_webhook_id`
- Nao adicionar opcoes de provider na v1.
- Nao adicionar configuracao de imagem na v1.

## strings.json

Atualizar traducoes conforme entidades e mensagens finais.

Itens esperados:

- Nome da integracao.
- Descricao do webhook.
- Erro de webhook id invalido.
- Nomes de entidades quando aplicavel.
- Mensagens de diagnostico se usadas no config flow.

Observacao:

- Os nomes das entidades podem vir diretamente de descriptions em codigo, mas
  devem seguir a nomenclatura do contrato.

## Testes

Criar ou atualizar testes automatizados para cobrir a implementacao real.

### Testes De Webhook

Cenarios:

- JSON invalido.
- Payload nao objeto.
- Provider ausente.
- Provider nao string.
- Provider nao suportado.
- `schema_version` ausente.
- `schema_version` nao suportado.
- `account_data` nao objeto.
- `plan_data` nao objeto.
- `provider_data` nao objeto.
- `status = ok` com `error` preenchido.
- `status != ok` com `error` ausente.
- Payload valido de `codex`.
- Payload valido de `ollama_cloud`.

### Testes De Identidade

Cenarios:

- `account_id` gera `account_key` estavel.
- `user_id` e usado quando `account_id` ausente.
- Email normalizado gera hash estavel.
- Email com maiusculas gera o mesmo hash do lowercase.
- Username sem email nao cria conta para `ollama_cloud`.
- Payload sem identificador atualiza `last_unscoped_error`.

### Testes De Device Pai

Cenarios:

- Device pai e criado na setup.
- `last_ingest_status` inicia em estado adequado.
- `webhook_problem` liga em erro de ingestao.
- `known_accounts` atualiza ao criar conta.
- `last_source` atualiza em payload valido.
- `last_unscoped_error` atualiza quando nao ha conta.

### Testes De Device De Conta

Cenarios:

- Primeira request cria device de conta.
- Segunda request da mesma conta nao duplica device.
- Duas contas do mesmo provider criam dois devices.
- Contas de providers diferentes criam devices separados.
- Device usa `via_device`.
- Device usa manufacturer/model/configuration_url corretos.

### Testes De Entidades Comuns

Cenarios:

- `sensor.account` mostra label correta.
- `sensor.account` possui `entity_picture` correto.
- `sensor.plan` reflete `plan_data.type`.
- `sensor.status` reflete `payload.status`.
- `binary_sensor.problem` liga quando `status != ok`.
- `sensor.last_error` usa `none` sem erro.
- `sensor.last_error` usa `error.code` com erro.
- `sensor.collected_at` converte timestamp corretamente.
- `sensor.last_received_at` usa horario do HA.
- `sensor.source` inclui `source_version` e `schema_version`.
- `sensor.request_count` incrementa por conta.

### Testes Codex

Cenarios:

- `allowed` reflete `rate_limit.allowed`.
- `limit_reached` reflete `rate_limit.limit_reached`.
- Percentuais das janelas sao numericos.
- `reset_at` Unix epoch vira `datetime` UTC.
- `reset_after_seconds` vira duracao em horas.
- Campo ausente deixa entidade como `unknown`, sem quebrar webhook valido se o
  contrato permitir ausencia.

### Testes Ollama Cloud

Cenarios:

- `session_usage.used_percent` vira sensor percentual.
- `session_usage.reset_at` vira timestamp.
- `weekly_usage.used_percent` vira sensor percentual.
- `weekly_usage.reset_at` vira timestamp.
- Reset ISO invalido gera erro de contrato.

### Testes De Persistencia E Restore

Cenarios:

- Conta nova e salva em storage.
- Reload recria entidades da conta.
- Request count persistido nao volta para zero.
- Estado restaurado aparece antes de nova request quando HA tiver estado salvo.
- Payload bruto nao e salvo no storage.

### Testes Do Servico De Ingestao

Cenarios:

- Webhook chama `AIUsageIngestionService` e apenas converte resultado para HTTP.
- Servico processa payload valido sem depender de request HTTP.
- Servico aceita `transport = "webhook"`.
- Servico aceita um `transport` interno de teste sem exigir `webhook_id`.
- Erros de contrato sao produzidos pelo servico, nao pelo handler HTTP.
- Estado, storage e dispatcher sao atualizados pelo fluxo comum de ingestao.

### Testes De Imagens

Cenarios:

- Static path dos providers e registrado.
- `sensor.account.entity_picture` aponta para o provider correto.
- Provider sem imagem nao quebra entidade.

## Fases De Implementacao

### Fase 1 - Documento E Assets

Tarefas:

- Criar esta especificacao.
- Criar pasta `provider_images`.
- Adicionar placeholders de `codex.png` e `ollama_cloud.png`.
- Manter pasta `brand`.

Resultado esperado:

- Estrutura de assets pronta para a implementacao.

### Fase 2 - Modelos, Identidade E Validacao

Tarefas:

- Criar modelos internos.
- Criar `AIUsageIngestionService`.
- Implementar validador do envelope.
- Implementar resolver de identidade.
- Implementar metadados fixos dos providers v1.
- Implementar conversores de timestamp e percentuais.
- Fazer o webhook chamar o servico de ingestao, sem conter regra de negocio.

Resultado esperado:

- Servico de ingestao testavel isoladamente. O webhook ainda pode nao criar
  entidades novas, mas ja deve delegar validacao e processamento ao servico.

### Fase 3 - Runtime E Storage

Tarefas:

- Trocar estado por provider por estado por conta.
- Criar estado do device pai.
- Implementar storage de contas conhecidas.
- Carregar contas persistidas na setup.
- Definir signals de atualizacao.
- Integrar o servico de ingestao ao runtime e ao storage.

Resultado esperado:

- Runtime sabe criar, recuperar e atualizar contas em memoria, sempre chamado
  pelo servico de ingestao.

### Fase 4 - Devices E Sensores Comuns

Tarefas:

- Reescrever `sensor.py` para entidades comuns e device pai.
- Criar `binary_sensor.py`.
- Atualizar `PLATFORMS`.
- Implementar criacao dinamica de entidades.
- Implementar `RestoreEntity`.

Resultado esperado:

- Devices e entidades comuns funcionam com payloads validos.

### Fase 5 - Sensores Especificos

Tarefas:

- Implementar entidades especificas de `codex`.
- Implementar entidades especificas de `ollama_cloud`.
- Remover sensores de tokens/custo/duracao da POC.
- Remover atributos com payload bruto.

Resultado esperado:

- Sensores por provider seguem os contratos atuais.

### Fase 6 - Imagens E Polimento

Tarefas:

- Registrar static path de imagens.
- Aplicar `entity_picture` em `sensor.account`.
- Atualizar `strings.json`.
- Revisar nomes, categorias, device classes e state classes.

Resultado esperado:

- Entidades aparecem com nomes e imagens corretas no Home Assistant.

### Fase 7 - Testes E Ajustes Finais

Tarefas:

- Implementar testes listados neste documento.
- Rodar testes.
- Corrigir warnings de Home Assistant.
- Revisar recorder attributes para garantir que payload bruto nao esta sendo
  gravado.

Resultado esperado:

- Implementacao pronta para uso real.

## Checklist De Aceite

- [ ] Webhook aceita payloads validos de `codex`.
- [ ] Webhook aceita payloads validos de `ollama_cloud`.
- [ ] Webhook rejeita contrato invalido com erro claro.
- [ ] Device pai e criado.
- [ ] Devices de conta sao criados dinamicamente.
- [ ] Multiplas contas do mesmo provider sao suportadas.
- [ ] Contas conhecidas sobrevivem a reload/restart.
- [ ] Sensores comuns existem para todas as contas.
- [ ] Binary sensors comuns existem para todas as contas.
- [ ] Sensores especificos do Codex existem.
- [ ] Sensores especificos do Ollama Cloud existem.
- [ ] `sensor.account` usa imagem local do provider.
- [ ] Pasta `brand` continua existindo.
- [ ] Pasta de imagens dos providers existe.
- [ ] Payload bruto nao aparece como atributo por padrao.
- [ ] Webhook delega processamento para o servico de ingestao.
- [ ] Servico de ingestao processa payload sem depender de request HTTP.
- [ ] Testes automatizados cobrem validacao, identidade, devices e sensores.

## Decisoes Confirmadas Antes Da Implementacao

1. Versao minima do Home Assistant:
   - Usar Home Assistant `2026.5`.
   - Nao implementar fallback para APIs antigas.

2. Nome das imagens dos providers:
   - Usar `codex.png`.
   - Usar `ollama_cloud.png`.

3. Imagens placeholders:
   - Placeholders sao aceitos na primeira implementacao.

4. Entidade diagnostica com payload resumido:
   - Nao criar na v1.

5. Migracao dos sensores da POC:
   - Nao migrar na v1.
   - A POC nao representa o contrato final, entao as entidades finais podem usar
     novos `unique_id`.

6. Acoplamento ao webhook:
   - Nao acoplar processamento ao webhook.
   - Criar um servico de ingestao reutilizavel.
   - O webhook deve ser apenas o primeiro transporte desse servico.

## Fase Futura - Provider Generico

O provider generico deve ficar fora da v1.

Quando for implementado, usar `docs/generic-provider-contract.md` como base e
adicionar:

- validacao de `provider_data.contract = "generic_provider.v1"`
- suporte a `account_data.stable_id`
- criacao dinamica de entidades declaradas em `provider_data.entities`
- bloqueio de chaves reservadas
- validacao de plataformas aceitas
- testes de provider desconhecido com contrato generico

A arquitetura da v1 deve evitar acoplamento excessivo aos dois providers atuais,
mas nao precisa implementar comportamento generico antes da hora.
