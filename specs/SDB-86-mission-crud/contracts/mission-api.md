# Contrato HTTP — Mission

Prefixo da API: `/api/v1`.

Todos os endpoints exigem autenticação. Um Step ou Mission inexistente,
excluído logicamente ou pertencente a outro usuário produz o mesmo Problem
Details `404`.

## Criar

`POST /steps/{step_id}/missions`

Request:

```json
{
  "title": "Complete 3 lessons",
  "difficulty": "medium",
  "xpReward": 100,
  "criteria": "number_of_lessons_completed",
  "criteriaValue": 3
}
```

Resposta `201`:

```json
{
  "id": "uuid",
  "stepId": "uuid",
  "title": "Complete 3 lessons",
  "difficulty": "medium",
  "xpReward": 100,
  "criteria": "number_of_lessons_completed",
  "criteriaValue": 3,
  "updatedAt": "2026-10-14T21:00:00",
  "missionProgresses": []
}
```

## Listar

`GET /steps/{step_id}/missions?page=1&page_size=20`

Resposta `200`: `PaginatedResponse[MissionResponse]`, com no máximo 100
itens por página e somente os progressos do usuário autenticado.

## Consultar

`GET /missions/{mission_id}`

Resposta `200`: `MissionResponse`.

## Atualizar

`PUT /missions/{mission_id}`

Request parcial:

```json
{
  "title": "Complete 5 lessons",
  "xpReward": 200,
  "criteriaValue": 5
}
```

Resposta `200`: `MissionResponse`. `stepId` não pode ser alterado.

## Excluir

`DELETE /missions/{mission_id}`

Resposta `204` sem corpo. A missão permanece persistida, mas não aparece em
consultas posteriores.

## Erros

- `401`: usuário não autenticado.
- `404`: recurso não encontrado ou não autorizado.
- `422`: UUID, paginação, enum, título ou valores numéricos inválidos.
- `500`: falha interna tratada pelo contrato Problem Details existente.
