# Quickstart de Validação

## Pré-requisitos

- Python >= 3.11, `uv` e Docker instalados.
- `.env` configurado e PostgreSQL disponível pelo compose.

## Preparação

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
```

## Validação automatizada

```bash
uv run pytest tests/unit tests/integration tests/contract
uv run ruff check .
```

Testes de contrato devem sobrescrever `get_current_user` e `get_db`. Testes de
integração devem usar PostgreSQL porque UUID, FKs e tipos do schema são
específicos do banco configurado.

## Cenários mínimos

1. Criar feedback em aula ativa; confirmar `201`, `lesson_id`, `author_id` do
   contexto e ausência de campos internos no request.
2. Tentar criar sem autenticação, com aula inexistente/excluída, texto vazio e
   campo extra; confirmar `401`, `404` ou `422` sem persistência.
3. Listar aula com feedbacks ativos e excluídos; confirmar paginação e somente
   ativos.
4. Consultar feedback ativo; confirmar `id`, aula, autor, texto e timestamps.
5. Atualizar o próprio feedback; confirmar texto e `updated_at`; tentar outro
   autor e confirmar `404` sem alteração.
6. Remover logicamente; confirmar `204`, `deleted_at` no banco e ausência em
   detalhe, listagem e composição da aula.
7. Consultar uma trilha com uma aula contendo pelo menos 50 feedbacks;
   instrumentar o engine e confirmar que não existe uma query por feedback.

Os endpoints e payloads completos estão em [contracts/feedbacks.md](contracts/feedbacks.md),
e as regras de persistência em [data-model.md](data-model.md).
