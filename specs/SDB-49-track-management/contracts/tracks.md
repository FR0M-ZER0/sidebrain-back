# Contrato HTTP: Trilhas

Base path: `/api/v1/tracks`

Todos os endpoints exigem o contexto de usuário autenticado. Sem credencial válida: `401`. O proprietário nunca é aceito no body.

## Criar trilha

`POST /api/v1/tracks`

Request:

```json
{"title": "Python", "description": "Percurso inicial"}
```

`title` é obrigatório e tem 1-255 caracteres. `description` é opcional e pode ser `null`.

Response `201`: objeto de trilha com `id`, `title`, `description`, `created_at`, `updated_at` e a hierarquia de conteúdo.

## Listar trilhas

`GET /api/v1/tracks?page=1&page_size=20`

Response `200`:

```json
{"data": [], "page": 1, "page_size": 20, "total_items": 0, "total_pages": 0}
```

Somente trilhas ativas do usuário autenticado são retornadas. A cada item aplica-se a mesma hierarquia de leitura descrita em [data-model.md](../data-model.md).

## Consultar trilha

`GET /api/v1/tracks/{track_id}`

Response `200`: objeto de trilha completo, incluindo etapas, lições, arquivos, feedbacks, quizzes, respostas e missões com o progresso do usuário autenticado.

UUID malformado: `422`. UUID inexistente, excluído ou pertencente a outro usuário: `404`.

## Atualizar trilha

`PATCH /api/v1/tracks/{track_id}`

Request:

```json
{"title": "Python avançado", "description": null}
```

Ao menos um campo deve ser enviado. `title`, quando enviado, não pode ser vazio nem exceder 255 caracteres. Response `200`: trilha atualizada.

## Excluir trilha

`DELETE /api/v1/tracks/{track_id}`

Response `204` sem body. A operação marca `is_deleted` e `deleted_at`; novas leituras retornam `404` e a trilha não aparece em listagens.

## Problem Details

Formato mínimo:

```json
{"type": "...", "title": "...", "status": 404, "detail": "Trilha não encontrada"}
```

- `422`: body, UUID ou paginação inválidos; incluir `errors` quando houver campos.
- `401`: ausência ou invalidade da autenticação.
- `404`: inexistente, excluída ou de outro usuário, sem revelar ownership.
- `500`: falha de persistência/processamento, sem SQL, stack trace ou credenciais.
