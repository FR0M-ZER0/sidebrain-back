# Contrato HTTP: Quizzes

Base path: `/api/v1`. Todos os endpoints exigem Bearer válido. Nesta versão, a
credencial é o UUID do usuário reconhecido por `get_current_user`.

## Representações

### QuizResponse

```json
{
  "id": "00000000-0000-0000-0000-000000000101",
  "lesson_id": "00000000-0000-0000-0000-000000000201",
  "question": "What is a variable in Python?",
  "answers": [
    {
      "id": "00000000-0000-0000-0000-000000000301",
      "user_id": "00000000-0000-0000-0000-000000000401",
      "text": "A named reference to a value",
      "rate": "perfect"
    }
  ]
}
```

Os valores de `rate` são `good`, `perfect`, `wrong` e `almost_got_it`. Quiz sem
respostas retorna `answers: []`.

### Lista paginada

```json
{
  "data": [],
  "page": 1,
  "page_size": 20,
  "total_items": 0,
  "total_pages": 0
}
```

## Criar quiz

`POST /lessons/{lesson_id}/quizzes`

Request:

```json
{"question": "What is a variable in Python?"}
```

Response `201`: `QuizResponse` com `lesson_id` obtido da URL e `answers: []`.
A Lesson pode estar em qualquer status, mas deve existir, estar ativa e
pertencer à hierarquia do usuário autenticado.

## Listar quizzes de uma aula

`GET /lessons/{lesson_id}/quizzes?page=1&page_size=20`

Response `200`: envelope paginado de `QuizResponse`. Retorna somente quizzes
ativos, ordenados por `updated_at` decrescente e `id` decrescente. As Answers de
cada item são carregadas em lote e ordenadas por criação crescente e ID
crescente.

Aula inexistente, excluída, contida em pai excluído ou inacessível retorna
`404`. Página além do total retorna `data: []`.

## Consultar quiz

`GET /quizzes/{quiz_id}`

Response `200`: `QuizResponse`, incluindo todas as Answers associadas na ordem
definida. UUID malformado retorna `422`; Quiz inexistente, excluído, com pai
excluído ou de outra Track retorna `404`.

## Atualizar quiz

`PUT /quizzes/{quiz_id}`

Request:

```json
{"question": "How does a Python variable reference a value?"}
```

Response `200`: `QuizResponse` atualizado com suas Answers. O request substitui
somente a pergunta; `lesson_id`, IDs, Answers, timestamps e flags não são
aceitos. Pergunta vazia, somente com espaços, maior que 1.000 caracteres após
normalização ou campo extra retorna `422` sem persistência.

## Remover quiz

`DELETE /quizzes/{quiz_id}`

Response `204` sem body. A linha de Quiz permanece com `is_deleted=true` e
`deleted_at` preenchido; Answers não são alteradas e o `ON DELETE CASCADE` não é
acionado. Repetir a operação retorna `404`.

## Autorização e erros

- `401`: credencial ausente, inválida ou usuário excluído.
- `404`: Lesson/Quiz inexistente, excluído, sob pai excluído ou pertencente a
  outra Track; a API não distingue esses casos para não revelar ownership.
- `422`: UUID, paginação ou payload inválido.
- `500`: falha interna sem SQL, stack trace ou credenciais.

Formato mínimo de Problem Details:

```json
{
  "type": "https://sidebrain.api/errors/404",
  "title": "Não encontrado",
  "status": 404,
  "detail": "Quiz não encontrado"
}
```

Erros de validação também incluem `errors` com campo e mensagem.

## Composição hierárquica

Responses de Track que já incluem aulas continuam apresentando
`Lesson -> Quiz[] -> Answer[]`. Quizzes excluídos são omitidos; os campos
preexistentes da API v1 são preservados, e `lesson_id`/`user_id` são adicionados
às representações aninhadas para satisfazer o contrato sem quebra.
