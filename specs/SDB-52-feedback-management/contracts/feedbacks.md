# Contrato HTTP: Feedbacks

Base path: `/api/v1`. Todos os endpoints exigem Bearer válido quando indicado;
sem autenticação, a resposta é `401` em Problem Details.

## Criar feedback

`POST /lessons/{lesson_id}/feedbacks`

Request:

```json
{"text": "A explicação foi clara."}
```

Response `201`:

```json
{
  "id": "uuid",
  "lesson_id": "uuid",
  "author_id": "uuid",
  "text": "A explicação foi clara.",
  "created_at": "2026-09-16T12:00:00",
  "updated_at": "2026-09-16T12:00:00"
}
```

`lesson_id` deve apontar para aula ativa. A autoria é obtida do token; campos
extras são rejeitados com `422`.

## Listar feedbacks de uma aula

`GET /lessons/{lesson_id}/feedbacks?page=1&page_size=20`

Response `200` usa o envelope paginado padrão. Retorna somente feedbacks ativos
da aula ativa. Aula inexistente ou excluída retorna `404`.

## Consultar feedback

`GET /feedbacks/{feedback_id}`

Response `200`: o objeto público acima. UUID inválido retorna `422`; inexistente
ou excluído retorna `404`.

## Atualizar feedback próprio

`PATCH /feedbacks/{feedback_id}`

Request:

```json
{"text": "A explicação foi atualizada."}
```

O feedback deve estar ativo e pertencer ao usuário autenticado. Alteração por
outro usuário, inexistência ou exclusão retorna `404` sem alterar dados.

## Remover feedback próprio

`DELETE /feedbacks/{feedback_id}`

Response `204` sem body. A linha permanece no banco com exclusão lógica; novas
consultas retornam `404` e ela não aparece na aula.

## Problem Details

Formato mínimo:

```json
{"type": "...", "title": "Não encontrado", "status": 404, "detail": "Feedback não encontrado"}
```

`401` autenticação inválida, `404` recurso inexistente/excluído/inacessível,
`422` payload ou UUID inválido e `500` falha interna sem detalhes de banco.
