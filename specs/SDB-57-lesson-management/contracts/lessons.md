# Contrato HTTP: Lessons

Base da API: `/api/v1`.

Todos os endpoints exigem Bearer válido. Na implementação atual, o token é o
UUID do usuário resolvido por `get_current_user`. JSON público usa `snake_case`.

## Representação

### LessonResponse

```json
{
  "id": "00000000-0000-0000-0000-000000000101",
  "title": "Variables",
  "text": "Variables are used to store data.",
  "status": "idle",
  "position": 1,
  "updated_at": "2026-09-21T12:00:00",
  "feedbacks": [
    {
      "id": "00000000-0000-0000-0000-000000000201",
      "user_id": "00000000-0000-0000-0000-000000000301",
      "text": "Very useful lesson.",
      "created_at": "2026-09-21T11:00:00",
      "updated_at": "2026-09-21T11:30:00"
    }
  ],
  "files": [
    {
      "id": "00000000-0000-0000-0000-000000000401",
      "path": "/lessons/variables.png",
      "file_type": "image",
      "updated_at": "2026-09-21T11:00:00"
    }
  ],
  "quizzes": [
    {
      "id": "00000000-0000-0000-0000-000000000501",
      "question": "What is a variable?",
      "updated_at": "2026-09-21T11:00:00",
      "answers": [
        {
          "id": "00000000-0000-0000-0000-000000000601",
          "user_id": "00000000-0000-0000-0000-000000000301",
          "text": "A named storage location.",
          "rate": "perfect",
          "created_at": "2026-09-21T11:30:00",
          "updated_at": "2026-09-21T11:30:00"
        }
      ]
    }
  ]
}
```

`status` aceita `idle`, `in_progress` e `done`; `file_type` aceita `audio`,
`gif` e `image`; `rate` aceita `good`, `perfect`, `wrong` e `almost_got_it`.
Coleções sem itens são sempre `[]`.

O novo contrato direto usa `files`. Responses históricos de Track/Step que já
publicam `lesson_files` não são renomeados pela SDB-57.

## POST `/steps/{step_id}/lessons`

Cria uma Lesson no Step ativo pertencente a uma Track do usuário autenticado.

Request:

```json
{
  "title": "Variables",
  "text": "Variables are used to store data.",
  "position": 1
}
```

Response `201`: `LessonResponse` com `status="idle"`, `step_id` derivado da URL
e as três coleções vazias.

- `step_id` malformado: `422`.
- Step inexistente, excluído, sob Track excluída ou de outro usuário: `404`.
- Posição já reservada no Step, inclusive por Lesson removida: `409`.
- Campo ausente, extra, nulo ou inválido: `422`.

## GET `/steps/{step_id}/lessons`

Query:

- `page`: inteiro >= 1, padrão `1`;
- `page_size`: inteiro entre 1 e 100, padrão `20`.

Response `200`:

```json
{
  "data": [],
  "page": 1,
  "page_size": 20,
  "total_items": 0,
  "total_pages": 0
}
```

Retorna somente Lessons ativas, ordenadas por `position` crescente. Cada item
é um `LessonResponse` com Feedbacks, Files e Quizzes ativos; cada Quiz contém
suas Answers. Página além do total retorna `data: []` e mantém os metadados
coerentes. Step indisponível ou inacessível retorna `404`.

## GET `/lessons/{lesson_id}`

Response `200`: `LessonResponse` completo.

UUID malformado retorna `422`. Lesson inexistente, removida, sob Step/Track
removido ou pertencente a outro usuário retorna `404` sem revelar a causa.

## PUT `/lessons/{lesson_id}`

Substitui todos os campos editáveis da Lesson.

Request:

```json
{
  "title": "Python Variables",
  "text": "Variables store values in Python.",
  "status": "in_progress",
  "position": 2
}
```

Response `200`: `LessonResponse` atualizado, incluindo os filhos visíveis.

- Os quatro campos são obrigatórios; payload parcial retorna `422` sem mutação.
- Qualquer transição entre os três estados é válida.
- `step_id`, ID, timestamps, filhos e flags de exclusão não são aceitos.
- A posição pode permanecer igual à atual. Posição reservada por outra Lesson
  do mesmo Step retorna `409`; nenhuma Lesson é reordenada automaticamente.
- Lesson/pai inacessível retorna `404`.

## DELETE `/lessons/{lesson_id}`

Response `204`, sem corpo.

A operação marca a Lesson como removida, preenche `deleted_at`, atualiza
`updated_at` e preserva fisicamente a Lesson e todos os filhos. GET/PUT/DELETE
posteriores retornam `404`; a posição permanece reservada.

## Erros

- `401`: credencial ausente/inválida ou usuário removido.
- `404`: Step/Lesson inexistente, removido, contido em pai removido ou alheio.
- `409`: posição já reservada no Step.
- `422`: UUID, paginação ou payload inválido.
- `500`: falha inesperada sanitizada, após rollback.

Formato Problem Details:

```json
{
  "type": "https://sidebrain.api/errors/409",
  "title": "Conflito",
  "status": 409,
  "detail": "Já existe uma lição nesta posição para a etapa."
}
```

Falhas de validação também incluem `errors` com campo e mensagem. Nenhuma
resposta expõe nomes físicos, SQL, stack trace, existência de recurso alheio ou
estado parcial.
