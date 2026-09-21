# Contrato HTTP: geração assíncrona de Trilhas

Base: `/api/v1`

## POST `/tracks`

### Request `202`

```json
{
  "request_id": "optional-uuid",
  "goal": "Aprender Python",
  "topic": "FastAPI",
  "knowledge_level": "beginner",
  "assessment_answers": [
    {"question": "Já usou APIs?", "answer": "Não", "rate": "wrong"}
  ]
}
```

`request_id` pode ser omitido. O servidor gera UUID. Campos desconhecidos, texto vazio, enum inválido ou respostas inválidas são rejeitados antes de persistir/enfileirar.

### Response `202 Accepted`

```json
{
  "status": "pending",
  "request_id": "uuid"
}
```

A resposta não contém Track e não espera o provedor externo. Repetição com o mesmo usuário, `request_id` e fingerprint retorna o mesmo identificador sem publicar uma segunda task.

### Conflito `409`

O mesmo `request_id` com usuário ou contexto diferente retorna Problem Details RFC 9457:

```json
{
  "type": "https://minha-api.com/errors/generation-request-conflict",
  "title": "Conflito de solicitação",
  "status": 409,
  "detail": "O request_id já foi usado para outro contexto.",
  "error_code": "generation_request_conflict"
}
```

### Validação `422`

Erros de entrada usam o Problem Details já padronizado pela API, com `status`, `title`, `detail` e lista de campos quando aplicável. Nomes físicos de banco não aparecem.

## POST `/tracks/{track_id}/steps/{step_id}/prepare-next`

### Response `202 Accepted`

Quando há próximo Step elegível:

```json
{
  "status": "accepted",
  "step_id": "uuid",
  "task_id": "celery-task-id"
}
```

O `step_id` identifica o Step que será preparado. O serviço chama `prepare_next_step_content_task.delay()` e o router não espera a task.

### Response `200 OK`

Quando o Step atual é autorizado, mas não há próximo Step elegível:

```json
{
  "status": "skipped",
  "reason": "no_eligible_next_step"
}
```

O threshold de 80% e as regras atuais de elegibilidade permanecem inalterados.

### Response `404 Not Found`

Step/Track inexistente, excluído logicamente ou pertencente a outro usuário produz exatamente o mesmo Problem Details genérico:

```json
{
  "type": "https://minha-api.com/errors/not-found",
  "title": "Não encontrado",
  "status": 404,
  "detail": "Step não encontrado"
}
```

Não é permitido distinguir existência, exclusão ou ownership. O router usa `Depends(get_current_user)` e `Depends(get_track_service)`; não acessa repositories/tasks diretamente.

## Resultado assíncrono interno

A task `tasks.generate_track` mantém o resultado serializado:

```json
{"status": "succeeded", "request_id": "uuid", "track_id": "uuid"}
```

ou:

```json
{"status": "failed", "request_id": "uuid", "error_code": "generation_persistence_failed"}
```

O resultado interno não altera a resposta HTTP inicial; a solicitação persistida é a fonte de estado de negócio.

## Execução

Após `uv run alembic upgrade head`, mantenha a API e o worker em processos
separados:

```bash
uv run dev
uv run celery -A sidebrain_back.core.celery_app worker --loglevel=INFO
```
