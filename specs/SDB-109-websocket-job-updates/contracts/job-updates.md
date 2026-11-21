# Contrato de integração do cliente

## 1. Iniciar a operação

Todas as rotas abaixo usam Bearer e o prefixo `/api/v1`. Cada linha indica como obter o par de inscrição a partir da operação existente.

| Canal | POST relativo | Resultado que identifica o acompanhamento |
|---|---|---|
| `track_generation` | `/tracks`, com `goal` e `topic` | HTTP 202 com `request_id` e `status`. Usar o UUID retornado, inclusive na repetição idempotente. |
| `assessment` | `/assessments`, com `subject` e, opcionalmente, `objective` ou `skip` | HTTP 202 para preparação ou HTTP 200 para reutilização de perguntas já geradas. Preservar `Location` e usar `assessment_id`. |
| `step_preparation` | `/tracks/{track_id}/steps/{step_id}/prepare-next`, sem corpo | HTTP 202 com `status: accepted`, `step_id` da **próxima** etapa e `task_id`. Usar o `task_id`. HTTP 200 com `status: skipped` e `reason: no_eligible_next_step` encerra o fluxo na própria chamada. |
| `step_summary` | `/tracks/{track_id}/steps/{step_id}/summary`, sem corpo | HTTP 200 com `step_id` e `summary`. Formar a chave `{track_id}:{step_id}` com os UUIDs do caminho. A inscrição pode começar com resultado terminal. |

## 2. Emitir o ticket

`POST /api/v1/auth/ws-ticket` com `Authorization: Bearer <accessToken>` e `Content-Type: application/json`. O corpo usa um canal da tabela e uma chave string. Para trilha e diagnóstico, enviar um UUID. Para preparação, copiar o ID opaco recebido. Para sumário, enviar os dois UUIDs na ordem indicada.

```json
{"channel":"assessment","resource_id":"41ac2264-04fb-46a4-b404-6d30618534dd"}
```

Resposta HTTP 200, com `Cache-Control: no-store`.

```json
{"ticket":"<credencial-temporaria>"}
```

O ticket vale por 60 segundos desde a emissão e autoriza uma abertura. Duas tentativas simultâneas com o mesmo valor podem produzir somente um upgrade autorizado.

| HTTP | Significado |
|---|---|
| 401 | Bearer ausente ou inválido. |
| 404 | Recurso indisponível. Mesma resposta para falta de posse, exclusão, ausência, relação trilha/etapa inválida ou preparação expirada. |
| 422 | Canal inválido, parâmetro obrigatório ausente ou chave malformada. |
| 503 | Serviço de emissão temporariamente indisponível. |

Essas falhas usam `application/problem+json` com `type`, `title`, `status`, `detail` e, quando aplicável, `errors` por campo. Para o 404, o detalhe é `Recurso indisponível.`.

## 3. Abrir o socket e inscrever

Fazer upgrade em `GET /api/v1/ws?ticket={ticket}`. Enviar só o ticket temporário na query. Ticket ausente, inválido, expirado ou consumido resulta em recusa antes do upgrade. O navegador pode expor apenas um erro de conexão. Se a conexão cair após o consumo, solicitar outro ticket, ainda que nenhum evento tenha chegado. Um socket aberto continua válido quando o TTL do ticket termina.

Após `open`, enviar uma mensagem de texto JSON com o mesmo par autorizado.

```json
{"type":"subscribe","channel":"assessment","resource_id":"41ac2264-04fb-46a4-b404-6d30618534dd"}
```

Repetir a inscrição idêntica mantém um consumidor. Trocar o canal ou o recurso requer nova conexão. Mensagens inválidas, binárias ou de tipo desconhecido geram erro correlacionado ao escopo do ticket.

## 4. Processar o snapshot e os resultados

O primeiro `job.updated` representa o estado atual. Todos os frames de atualização têm `type`, `channel`, `resource_id` e `payload`. Os IDs no payload são os IDs públicos da operação. Exemplo de um diagnóstico dispensado:

```json
{"type":"job.updated","channel":"assessment","resource_id":"41ac2264-04fb-46a4-b404-6d30618534dd","payload":{"assessment_id":"41ac2264-04fb-46a4-b404-6d30618534dd","status":"completed","questions":[]}}
```

| Canal e ID sempre presente no payload | `pending` | Sucesso terminal | Falha terminal |
|---|---|---|---|
| `track_generation` · `request_id` | `track_id: null`, `error_code: null` | `succeeded` com `track_id` UUID e `error_code: null` | `failed` com `track_id: null` e `error_code` público da geração |
| `assessment` · `assessment_id` | `questions: []` | `completed` com `questions` de `generated` ou `completed`, ou `[]` para `skipped` | `failed`, `questions: []` e `error_code` igual a `generation_failed` ou `invalid_generation_result` |
| `step_preparation` · `task_id` | Apenas ID e `status` | `completed`, somente ID e `status` | `failed`, somente ID e `status` |
| `step_summary` · `step_id` | Apenas ID e `status` | `completed` e `summary` string | `failed` e `error` com mensagem pública |

Cada pergunta contém `id`, `statement` e `alternatives`, uma lista de objetos com `id` e `text`. Enviar perguntas e alternativas na ordem pública. O gabarito, as respostas do usuário e os detalhes de exceção ficam restritos ao backend. No sumário prevalece a geração iniciada mais recentemente, inclusive após reconexão. Na preparação, o resultado está disponível até imediatamente antes de completar 24 horas da transição terminal.

## 5. Encerrar e retomar

Um `job.updated` com estado terminal encerra a espera. O cliente pode fechar normalmente (1000) assim que processar o frame. Ao sair da tela, cancelar a espera ou atingir o timeout local, também deve fechar o socket. O processamento do job segue seu curso. Para retomar, emitir novo ticket e repetir a inscrição. O protocolo entrega o estado atual sem exigir histórico de eventos.

Se uma inscrição falhar ou perder permissão, o servidor envia `job.error` usando o **par autorizado**, mesmo que o cliente tenha enviado outro identificador. Em seguida fecha com 1008. Em indisponibilidade de infraestrutura após o upgrade, envia erro público e fecha com 1011 quando o transporte permitir. Para um socket já interrompido, o cliente trata o fechamento e pode reconectar.

```json
{"type":"job.error","channel":"assessment","resource_id":"41ac2264-04fb-46a4-b404-6d30618534dd","message":"Recurso indisponível."}
```

## Publicação

Em desenvolvimento, usar `ws://localhost:8080/api/v1/ws`. Em produção, configurar `VITE_WS_URL=wss://<host-publico>/api/v1/ws` no cliente da SDB-104 e terminar TLS no proxy que encaminha o upgrade ao servidor ASGI. Configurar timeout do proxy compatível com conexões ociosas e omitir a query de logs de acesso no proxy **e** no servidor. API e workers usam o mesmo PostgreSQL. A sessão de escuta requer conexão direta ou pooling por sessão. Todas as réplicas de API devem compartilhar a instância Redis de tickets. [Guia de validação](../quickstart.md) · [SDB-104](https://fromzero-api.atlassian.net/browse/SDB-104)
