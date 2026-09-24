# Quickstart de Validação: SDB-57

## Pré-requisitos

- Python >= 3.11, `uv`, Docker e Docker Compose.
- Variáveis obrigatórias de `.env` preenchidas.
- PostgreSQL 16 em um banco dedicado a testes. `MODE=test` não troca o banco;
  confirme `POSTGRES_DB` para não executar a suíte contra dados de desenvolvimento.

Se `.env` ainda não existir, copie o exemplo e edite-o antes de prosseguir:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Não remova volumes existentes para preparar o teste. Se o volume do Compose já
foi inicializado com outro banco, provisione explicitamente um banco de teste.

## Preparação

```powershell
docker compose up -d postgres
uv sync
uv run alembic upgrade head
```

As migrations são necessárias em banco vazio porque os enums PostgreSQL usados
pelos modelos são preexistentes (`create_type=False`). Redis não participa do
fluxo de Lesson, embora suas variáveis ainda precisem existir para carregar as
settings atuais.

## Validação automatizada

Durante a implementação, execute primeiro os grupos específicos:

```powershell
uv run pytest tests/unit/test_lesson_schema.py tests/unit/test_lesson_service.py -q
uv run pytest tests/contract/test_lesson_contract.py tests/contract/test_track_read_contract.py -q
uv run pytest tests/integration/test_lesson_lifecycle.py -q
uv run pytest tests/integration/test_lesson_hierarchy_queries.py::test_lesson_list_sc007_latency_and_sc008_constant_query_count -q
uv run ruff check .
```

Antes da entrega, execute a suíte completa:

```powershell
uv run pytest
```

Resultados esperados: todos os testes e o lint passam; os contratos anteriores
de Track/Step continuam estáveis; nenhum teste deixa dados persistidos fora de
sua transação.

## Cenários funcionais

1. Com uma Track e um Step ativos do usuário, criar Lesson em
   `POST /api/v1/steps/{step_id}/lessons`. Esperar `201`, status `idle`, posição
   informada e `feedbacks/files/quizzes` vazios.
2. Repetir a posição no mesmo Step e esperar Problem Details `409`. Repetir a
   posição em outro Step e esperar sucesso.
3. Listar `GET /api/v1/steps/{step_id}/lessons?page=1&page_size=20`. Esperar
   envelope paginado, somente Lessons ativas e ordem crescente de posição.
4. Consultar uma Lesson que possua Feedbacks, LessonFiles e Quizzes/Answers.
   Esperar somente filhos ativos, associação correta das Answers e listas vazias
   quando não houver filhos.
5. Atualizar via `PUT /api/v1/lessons/{lesson_id}` com os quatro campos. Esperar
   `200`, aceitar qualquer estado válido e não alterar o Step. Omitir um campo ou
   enviar campo interno/extra deve retornar `422` sem alteração parcial.
6. Remover via `DELETE /api/v1/lessons/{lesson_id}`. Esperar `204`; confirmar no
   banco que a Lesson permanece com soft delete e que todos os filhos permanecem
   inalterados. Repetir GET/PUT/DELETE deve retornar `404`.
7. Tentar todas as operações com recurso de outro usuário, Step/Track removido
   ou identificador inexistente. Esperar `404` uniforme, sem vazamento.
8. Após o soft delete, tentar criar outra Lesson na posição reservada. Esperar
   `409`.

Consulte [contracts/lessons.md](./contracts/lessons.md) para payloads e códigos,
e [data-model.md](./data-model.md) para filtros e transições.

## Protocolo de SC-007 e SC-008

Execute o benchmark isoladamente, sem concorrência ou carga externa. O teste usa
HTTPX `ASGITransport`, portanto mede FastAPI, autenticação, banco e serialização
no processo, não latência de rede/Uvicorn.

Dataset da página medida:

- 50 Lessons ativas;
- 5 Feedbacks ativos por Lesson;
- 3 LessonFiles ativos por Lesson;
- 5 Quizzes ativos por Lesson;
- 10 Answers por Quiz.

Procedimento:

1. Validar antes da medição que a resposta contém 50 Lessons e a cardinalidade
   completa de filhos.
2. Comparar a contagem de statements entre cenários equivalentes com 1 e 50
   Lessons. A contagem deve ser maior que zero e idêntica nos dois casos.
3. Usar uma sessão nova por request para evitar falso ganho pelo identity map.
4. Executar 5 requisições de aquecimento.
5. Medir 100 requisições autenticadas e estritamente sequenciais a
   `GET /api/v1/steps/{step_id}/lessons?page=1&page_size=50`.
6. Calcular o percentil 95; o resultado deve ser <= 2 segundos.

Para registrar as propriedades do benchmark em JUnit:

```powershell
uv run pytest tests/integration/test_lesson_hierarchy_queries.py::test_lesson_list_sc007_latency_and_sc008_constant_query_count --junitxml=.pytest_cache/lesson-benchmark.xml -o junit_family=legacy
```

Registrar `sc007_p95_seconds`, `sc008_query_count_one_lesson` e
`sc008_query_count_fifty_lessons`. Se a meta falhar por acesso ao banco, coletar
`EXPLAIN (ANALYZE, BUFFERS)` antes de propor índices ou migration.
