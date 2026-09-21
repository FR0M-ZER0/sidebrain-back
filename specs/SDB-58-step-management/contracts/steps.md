# Contrato HTTP: Steps

Base da API: `/api/v1`.

Todos os endpoints exigem autenticação. O `track_id` vem da URL. A inexistência,
soft delete ou ownership incompatível deve ser respondida como 404 uniforme.
Erros de validação, autenticação e persistência seguem Problem Details (RFC 9457)
no formato adotado pelo backend.

## POST `/tracks/{track_id}/steps`

Cria uma etapa no Track ativo pertencente ao usuário autenticado.

Request `application/json`:

```json
{
  "level": "beginner",
  "title": "Introduction"
}
```

Response `201`:

```json
{
  "id": "uuid",
  "level": "beginner",
  "title": "Introduction",
  "status": "idle",
  "updated_at": "2026-09-19T12:00:00",
  "lessons": [],
  "missions": []
}
```

## GET `/tracks/{track_id}/steps`

Lista Steps ativos do Track, com a árvore de leitura de cada Step.

Query: `page` (inteiro >= 1, padrão 1), `page_size` (inteiro 1..100, padrão 20).

A ordenação é estável por `updated_at` decrescente e, em caso de empate, `id`
decrescente. Não existe campo persistente de posição nesta feature.

Response `200`:

```json
{
  "data": [
    {
      "id": "uuid",
      "level": "beginner",
      "title": "Introduction",
      "status": "idle",
      "updated_at": "2026-09-19T12:00:00",
      "lessons": [],
      "missions": []
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_items": 1,
  "total_pages": 1
}
```

## GET `/tracks/{track_id}/steps/{step_id}`

Retorna um Step ativo pertencente ao Track da URL, incluindo Lessons com
`quizzes.answers`, `feedbacks`, `lesson_files` e Missions com `mission_progresses`
do usuário atual. Filhos excluídos são omitidos.

Response `200`: `StepResponse` conforme o POST.

## PUT `/tracks/{track_id}/steps/{step_id}`

Atualiza completamente os campos editáveis de um Step ativo.

Request `application/json`:

```json
{
  "level": "intermediate",
  "title": "Foundations"
}
```

Response `200`: `StepResponse` atualizado. Campos desconhecidos ou tentativas de
enviar campos gerenciados devem falhar na validação. A atualização mantém os
filhos existentes e retorna a árvore carregada com os mesmos filtros de leitura.

## DELETE `/tracks/{track_id}/steps/{step_id}`

Marca o Step como excluído logicamente, preserva o registro físico e não altera
os filhos.

Response `204`: sem corpo.

## Respostas de erro

- `400`/`422`: identificador ou payload inválido, conforme o handler vigente.
- `401`: autenticação ausente ou inválida.
- `404`: Track/Step inexistente, excluído, fora da hierarquia ou de outro usuário.
- `500`: falha de persistência encapsulada em Problem Details, sem detalhes internos.
