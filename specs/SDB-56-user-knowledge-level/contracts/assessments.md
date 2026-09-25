# Contrato HTTP — Avaliações de Conhecimento

Base autenticada: `/api/v1/assessments`

Todos os endpoints usam a identidade fornecida por `get_current_user`. Nenhum
request aceita `user_id`, nível, pontuação, estado ou gabarito. Schemas de
entrada usam `extra="forbid"`.

## Tipos públicos

### AssessmentStatus

`pending | generated | skipped | completed | failed`

### AssessmentQuestion

```json
{
  "id": "0f477e98-c8a9-4bc1-9d76-66fc0672e216",
  "statement": "Qual construção permite aguardar uma coroutine?",
  "alternatives": [
    {
      "id": "11b936df-7b65-44e6-a4de-03cbd4c14d91",
      "text": "await"
    },
    {
      "id": "92143e0d-e60d-448a-96b4-d73b610603a7",
      "text": "yield"
    },
    {
      "id": "34129758-6c81-43bd-9ae0-01a240a98d20",
      "text": "pass"
    },
    {
      "id": "e744a79a-4fc2-4990-9283-9f80dc73d697",
      "text": "break"
    }
  ]
}
```

O schema público jamais possui `is_correct`,
`correct_alternative_id`, correção individual ou metadados do provider.

### AssessmentDetail

```json
{
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "subject": "Python assíncrono",
  "objective": "Criar APIs com FastAPI",
  "skip": false,
  "status": "pending",
  "questions": [],
  "score": null,
  "level": null,
  "error_code": null,
  "created_at": "2026-09-23T22:00:00",
  "updated_at": "2026-09-23T22:00:00",
  "completed_at": null
}
```

Invariantes por estado:

| Estado | Questions | Score | Level | Error code | Completed at |
|---|---|---|---|---|---|
| `pending` | `[]` | `null` | `null` | `null` | `null` |
| `generated` | 5 perguntas × 4 alternativas | `null` | `null` | `null` | `null` |
| `skipped` | `[]` | `null` | `beginner` | `null` | preenchido |
| `completed` | 5 perguntas × 4 alternativas | 0..5 | corte correspondente | `null` | preenchido |
| `failed` | `[]` | `null` | `null` | `assessment_preparation_failed` | `null` |

`error_code` é estável e sanitizado. Prompt, resposta bruta, exceção, tentativa
e credenciais nunca são públicos.

## Iniciar avaliação

`POST /api/v1/assessments`

### Request

```json
{
  "subject": "Python assíncrono",
  "objective": "Criar APIs com FastAPI",
  "skip": false
}
```

Regras:

- `subject`: obrigatório sempre, trim, 1..255;
- `objective`: opcional; quando enviado, trim, 1..1000; string vazia ou só
  espaços é inválida;
- `skip`: boolean, default `false`;
- campos extras são rejeitados.

### Nova avaliação ou ativa em pending — 202 Accepted

Headers:

```http
Location: /api/v1/assessments/36e29823-e41f-4212-8c28-c3de41beb183
```

Body:

```json
{
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "status": "pending"
}
```

O ID é criado e persistido antes do enqueue. Uma repetição com o mesmo usuário,
subject/objective/skip normalizados e uma avaliação `pending` retorna o mesmo
ID, não publica outra task e também responde `202`.

### Ativa já generated — 200 OK

```json
{
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "status": "generated"
}
```

`skipped`, `completed` e `failed` são terminais e não são reutilizados;
uma nova solicitação cria outro ID. Uma nova avaliação com `skip=true` também
responde `202 pending`: a task oficial executa o ramo sem provider e a
consulta passa a mostrar `skipped`.

### Erros

- `401`: autenticação ausente ou inválida;
- `422`: campo ausente, vazio, fora do limite, tipo inválido ou campo extra;
- `503`: registro criado, mas não foi possível publicar a task; o registro é
  marcado `failed`;
- `500`: falha interna/persistência não classificada.

## Consultar avaliação

`GET /api/v1/assessments/{assessment_id}`

### Resposta — 200 OK

Retorna `AssessmentDetail` coerente com o estado atual. `pending` e
`failed` são estados consultáveis e não transformam o GET em erro HTTP. O
cliente usa este endpoint para polling até `generated`, `skipped` ou
`failed`, e para consultar um resultado `completed`.

### Erros

- `401`: autenticação ausente ou inválida;
- `404`: ID inexistente ou avaliação de outro usuário, com a mesma resposta;
- `422`: UUID de path inválido;
- `500`: falha interna.

Exemplo uniforme de `404`:

```json
{
  "type": "https://sidebrain.api/errors/404",
  "title": "Não encontrado",
  "status": 404,
  "detail": "Avaliação não encontrada."
}
```

## Submeter respostas

`POST /api/v1/assessments/{assessment_id}/answers`

### Request

```json
{
  "answers": [
    {
      "question_id": "0f477e98-c8a9-4bc1-9d76-66fc0672e216",
      "alternative_id": "11b936df-7b65-44e6-a4de-03cbd4c14d91"
    },
    {
      "question_id": "ca190697-f771-48a6-b98e-e63b28fdc391",
      "alternative_id": "62457db4-bd59-4180-93ae-c6f66f793aca"
    },
    {
      "question_id": "cd8337aa-78bb-42ac-aac9-164f44fb088d",
      "alternative_id": "76fe6ce3-f54a-42cf-8c47-579225a55a4f"
    },
    {
      "question_id": "36ee8ac1-89cb-49e1-8313-9d2ff6ea3953",
      "alternative_id": "bf1b4219-f7fa-4b23-8f34-3c4399e152a5"
    },
    {
      "question_id": "b1b1a910-f3a7-483e-b5f5-919808530c55",
      "alternative_id": "568a63e2-b65f-428f-8871-992bbf9cfeac"
    }
  ]
}
```

Regras:

- exatamente cinco itens;
- `question_id` sem repetição;
- o conjunto deve corresponder exatamente às perguntas da avaliação;
- cada alternativa deve pertencer à pergunta indicada;
- root e itens rejeitam campos extras;
- `level`, `score`, `is_correct`, `user_id`, `status` e gabarito nunca
  são aceitos.

### Resposta — 200 OK

Retorna `AssessmentDetail` em `completed`. O trecho abaixo destaca os
campos calculados; a resposta completa também contém as cinco perguntas
públicas, nos mesmos formatos da consulta em `generated`.

```json
{
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "subject": "Python assíncrono",
  "objective": "Criar APIs com FastAPI",
  "skip": false,
  "status": "completed",
  "score": 4,
  "level": "advanced",
  "error_code": null,
  "created_at": "2026-09-23T22:00:00",
  "updated_at": "2026-09-23T22:03:00",
  "completed_at": "2026-09-23T22:03:00"
}
```

A resposta não inclui gabarito nem indicação de acerto por item.

Tabela de corte:

| Acertos | Level |
|---:|---|
| 0–1 | `beginner` |
| 2–3 | `intermediate` |
| 4 | `advanced` |
| 5 | `pro` |

### Erros

- `401`: autenticação ausente ou inválida;
- `404`: avaliação inexistente ou de outro usuário;
- `409`: avaliação própria não está em `generated` (inclui pending,
  skipped, completed, failed e segunda submissão);
- `422`: cardinalidade, duplicidade, UUID, pergunta, alternativa, vínculo ou
  campo extra inválido;
- `500`: falha interna; a transação é revertida por inteiro.

Exemplo de conflito:

```json
{
  "type": "https://sidebrain.api/errors/409",
  "title": "Conflito",
  "status": 409,
  "detail": "A avaliação não está disponível para submissão.",
  "error_code": "assessment_not_generated"
}
```

Exemplo de vínculo inválido:

```json
{
  "type": "https://sidebrain.api/errors/422",
  "title": "Erro de validação",
  "status": 422,
  "detail": "Requisição inválida.",
  "errors": [
    {
      "field": "body.answers.2.alternative_id",
      "message": "Alternativa inválida para a pergunta informada."
    }
  ]
}
```

## Contrato interno da task oficial

Nome Celery: `tasks.prepare_knowledge_assessment`

Argumentos JSON:

```json
{
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "user_id": "8d4e1d4b-3b0e-4f2d-a5f4-123456789abc",
  "subject": "Python assíncrono",
  "objective": "Criar APIs com FastAPI",
  "skip": false
}
```

Regras:

- os cinco valores são definidos pelo backend; nenhum vem diretamente de
  campos controlados pelo cliente além do contexto já validado;
- `assessment_id` identifica o registro `pending` criado antes do enqueue;
- a task compara o contexto recebido com o registro e nunca substitui o ID;
- `skip=true` não chama o provider e persiste `skipped/beginner`;
- `skip=false` usa exclusivamente o generator/service da SDB-53;
- o payload interno do provider contém `correct_alternative_id`, mas a task
  persiste o gabarito e retorna ao result backend apenas
  `assessment_id/status`, nunca perguntas ou gabarito;
- falhas transitórias mantêm `pending` durante o retry;
- falha definitiva ou retry esgotado persiste `failed` sem conteúdo parcial;
- uma entrega repetida que encontra estado diferente de `pending` não
  sobrescreve a avaliação.

Resultado mínimo:

```json
{
  "assessment_id": "36e29823-e41f-4212-8c28-c3de41beb183",
  "status": "generated"
}
```

## Segurança e privacidade

- Nunca responder `403` para ownership; usar o mesmo `404` de inexistência.
- Nunca expor `user_id`, task id, retry count, nomes físicos de colunas,
  `is_correct`, `correct_alternative_id`, prompt, resposta bruta, credencial
  ou detalhe da exceção.
- Logs estruturados podem conter assessment id, task id, tentativa, evento e
  tipo da exceção; não podem conter subject, objective, alternativas ou
  gabarito.
- Todos os erros públicos seguem o formato Problem Details já registrado em
  `sidebrain_back.core.errors`.
