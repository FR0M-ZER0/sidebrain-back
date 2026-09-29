# Quickstart de Validação

## Pré-requisitos

- Python >= 3.11, `uv`, Docker e Docker Compose.
- `.env` criado a partir de `.env.example`.
- Um usuário, uma Track, uma Step e uma Lesson ativa relacionados no PostgreSQL.

## Preparação

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
uv run dev
```

A API deve responder em `http://localhost:8080`; os endpoints desta feature
ficam sob `http://localhost:8080/api/v1`.

## Validação automatizada

```bash
uv run pytest tests/unit/test_quiz_schema.py tests/unit/test_quiz_service.py
uv run pytest tests/integration/test_quiz_lifecycle.py tests/integration/test_quiz_hierarchy_queries.py
uv run pytest tests/contract/test_quiz_contract.py tests/contract/test_track_read_contract.py
uv run ruff check .
```

Resultado esperado: todos os testes e o lint passam. Os testes de integração
que exercitam UUID, FKs, enum e queries devem usar PostgreSQL.

## Validação manual do fluxo principal

Defina UUIDs existentes no ambiente:

```bash
export API_BASE="http://localhost:8080/api/v1"
export USER_ID="00000000-0000-0000-0000-000000000001"
export LESSON_ID="00000000-0000-0000-0000-000000000002"
```

Crie um quiz:

```bash
curl -i -X POST "$API_BASE/lessons/$LESSON_ID/quizzes" \
  -H "Authorization: Bearer $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"question":"  What is a variable in Python?  "}'
```

Espere `201`, pergunta sem espaços nas extremidades, `lesson_id` igual ao da
URL e `answers: []`. Guarde o `id` retornado em `QUIZ_ID`.

Liste e consulte:

```bash
curl -i "$API_BASE/lessons/$LESSON_ID/quizzes?page=1&page_size=20" \
  -H "Authorization: Bearer $USER_ID"

curl -i "$API_BASE/quizzes/$QUIZ_ID" \
  -H "Authorization: Bearer $USER_ID"
```

Espere `200`, envelope paginado na listagem e Answers ordenadas por
`created_at ASC, id ASC` quando existirem.

Atualize e remova:

```bash
curl -i -X PUT "$API_BASE/quizzes/$QUIZ_ID" \
  -H "Authorization: Bearer $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"question":"How does a Python variable reference a value?"}'

curl -i -X DELETE "$API_BASE/quizzes/$QUIZ_ID" \
  -H "Authorization: Bearer $USER_ID"
```

Espere `200` no PUT e `204` sem body no DELETE. Depois do DELETE, detalhe,
update e novo delete devem retornar `404`; a linha e suas Answers devem
permanecer fisicamente no banco.

## Cenários de segurança e borda

1. Repetir chamadas sem Authorization e confirmar `401` em Problem Details.
2. Usar Lesson/Quiz de outra Track e confirmar `404`, sem revelar ownership.
3. Usar Lesson, Step, Track ou Quiz excluído e confirmar `404`.
4. Criar/atualizar com pergunta vazia, somente espaços, 1.001 caracteres após
   `strip()` ou campo `lesson_id`/`id`/`answers`; confirmar `422` sem mutação.
5. Solicitar página além do total e confirmar `data: []` com metadados coerentes.
6. Consultar uma Track e confirmar `Lesson -> Quiz[] -> Answer[]`, sem quizzes
   excluídos e com `lesson_id`/`user_id` públicos.

## Validação de desempenho e N+1

Use a API em `MODE=test`, PostgreSQL 16 iniciado pelo Docker Compose, sem carga
concorrente, e prepare uma Lesson com exatamente 50 quizzes ativos e 10 Answers
por quiz. O teste executa 5 requisições autenticadas de aquecimento e depois 100
requisições sequenciais a
`GET /api/v1/lessons/{lesson_id}/quizzes?page=1&page_size=50`:

```bash
uv run pytest tests/integration/test_quiz_hierarchy_queries.py -q
```

O teste deve calcular o percentil 95 das 100 amostras end-to-end, incluindo
autenticação, acesso ao banco e serialização, e exigir p95 de no máximo 2
segundos. Também deve instrumentar o engine e comprovar que a quantidade de
statements SQL permanece constante ao comparar o mesmo endpoint com 1 e 50
quizzes. Se a meta falhar por acesso ao banco, use `EXPLAIN ANALYZE` para
fundamentar uma migration de índices em uma mudança separada.

Consulte [contracts/quizzes.md](contracts/quizzes.md) para o contrato completo e
[data-model.md](data-model.md) para filtros, relações e transições.
