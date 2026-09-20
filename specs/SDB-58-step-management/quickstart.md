# Quickstart de Validação: SDB-58

## Pré-requisitos

- Python >= 3.11, `uv` e dependências sincronizadas.
- PostgreSQL configurado conforme o ambiente do projeto.
- Banco migrado e usuário autenticado disponível para os testes.

```powershell
uv sync
uv run alembic upgrade head
```

## Validação automatizada

Execute a suíte específica durante a implementação:

```powershell
uv run pytest tests/unit/test_step_schema.py tests/unit/test_step_service.py
uv run pytest tests/contract/test_step_contract.py tests/integration/test_step_hierarchy_queries.py
uv run ruff check .
```

## Cenários end-to-end

1. Criar um Track ativo do usuário e enviar `POST /api/v1/tracks/{track_id}/steps`
   com `level=beginner` e título válido. Esperar `201`, status `idle` e listas
   `lessons`/`missions` vazias.
2. Listar com `GET /api/v1/tracks/{track_id}/steps?page=1&page_size=20`. Esperar
   envelope paginado e somente Steps ativos do Track.
3. Consultar `GET /api/v1/tracks/{track_id}/steps/{step_id}` com Lessons, Quizzes,
   Answers, Feedbacks, LessonFiles, Missions e MissionProgress previamente
   associados. Esperar a árvore sem campos físicos e sem filhos excluídos.
4. Atualizar via `PUT /api/v1/tracks/{track_id}/steps/{step_id}` enviando `level` e `title`. Esperar `200`; enviar campo
   extra ou omitir um dos campos e esperar erro de validação.
5. Remover via `DELETE /api/v1/tracks/{track_id}/steps/{step_id}`. Esperar `204`; repetir GET/PUT/DELETE e esperar `404`.
6. Repetir leitura e mutação usando Track de outro usuário, `track_id` incorreto
   ou Step de outro Track. Esperar `404` sem vazamento de dados.
7. Após a remoção, verificar no banco que o Step continua presente com
   `stp_is_deleted=true` e `stp_deleted_at` preenchido, enquanto Lessons/Missions
   e demais filhos permanecem inalterados.

O formato detalhado de payloads e status está em [contracts/steps.md](./contracts/steps.md);
os campos e filtros da árvore estão em [data-model.md](./data-model.md).
