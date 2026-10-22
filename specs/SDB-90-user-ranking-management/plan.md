# Implementation Plan: Gerenciamento do Ranking de Usuários por XP

**Branch**: `feat/sdb-90-criar-endpoints-para-gerenciamento-do-ranking-dos-usuarios` | **Date**: 2026-10-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-90-user-ranking-management/spec.md`

## Summary

Implementar os endpoints somente de leitura do ranking de usuários por XP (`GET /api/v1/rankings` e `GET /api/v1/rankings/me`). O XP e a contagem de missões concluídas serão calculados de forma derivada via agregação SQL sobre `User`, `MissionProgress` e `Mission` (considerando apenas usuários ativos, missões ativas e progressos com status `done`), com ordenação determinística (`xp DESC, usr_created_at ASC, usr_id ASC`), posição global sequencial (`1-based`) e contrato público `RankingEntryResponse` / `PaginatedResponse[RankingEntryResponse]`.

## Technical Context

**Language/Version**: Python >= 3.11 (ambiente do projeto em Python 3.12 via `pyproject.toml`)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.0 (`AsyncSession`)

**Storage**: PostgreSQL existente; leitura agregada sobre as tabelas `user`, `mission` e `mission_progress` (nenhuma nova tabela, coluna ou migração Alembic necessária)

**Testing**: Pytest (`tests/unit`, `tests/contract`, `tests/integration`)

**Target Platform**: Serviço web FastAPI executado em container Linux e ambiente local via `uv`

**Project Type**: Web service / REST API

**Performance Goals**: Quantidade constante de consultas SQL por requisição (2 queries na listagem paginada: contagem + agregação da página; 1 query na posição individual via CTE com `ROW_NUMBER()`), sem N+1 independentemente do número de usuários ou missões

**Constraints**: Somente leitura (`GET`); paginação normativa (`page=1`, `page_size=20`, máximo `100`); `position` global `1-based` sem divisão em empate; ocultação total de `usr_email`, `usr_password_hash` e nomes físicos (`usr_*`, `msn_*`, `mpg_*`); erros em Problem Details (RFC 9457)

**Scale/Scope**: 2 endpoints HTTP (`GET /api/v1/rankings` e `GET /api/v1/rankings/me`), 4 novos módulos de aplicação (`ranking_schema.py`, `ranking_repository.py`, `ranking_service.py`, `ranking_router.py`), registro em `routers/router.py` e suíte de testes dedicada

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Qualidade de Código e Clean Code**: PASS — Nomes seguem estritamente `docs/code_conventions.md` (`RankingRepository`, `RankingService`, `list_rankings`, `get_my_ranking`, `get_user_ranking`, `count_ranked_users`), sem duplicação de regras de cálculo.
- **II. Responsabilidade Única e Coesão**: PASS — `ranking_router.py` trata apenas HTTP/query params/autenticação; `ranking_service.py` orquestra paginação, construção dos schemas e erro `404`; `ranking_repository.py` encapsula toda a agregação SQL.
- **III. Separação Clara de Camadas**: PASS — Fluxo estrito `routers -> services -> repositories -> models`, com injeção via `Depends` (`get_ranking_repository`, `get_ranking_service`) e schemas desacoplados dos modelos ORM.
- **IV. Testes e Contratos Verificáveis**: PASS — Planejados testes unitários para schema e service, testes de contrato para ambos os endpoints HTTP e testes de integração em PostgreSQL cobrindo agregação, soft delete, desempate, paginação e ausência de N+1.
- **V. Simplicidade e Evolução Segura**: PASS — Nenhuma tabela/coluna desnormalizada adicionada; reutilização de `PaginatedResponse`, `get_current_user` e `ProblemDetailError`.

**Resultado pré-pesquisa**: PASS. Nenhuma violação constitucional identificada.

**Reavaliação pós-design**: PASS. Os artefatos `research.md`, `data-model.md`, `contracts/ranking-api.md` e `quickstart.md` mantêm separação estrita de camadas, consultas SQL constantes sem N+1 e contratos públicos aderentes às convenções do projeto.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-90-user-ranking-management/
├── plan.md              # Este arquivo (/speckit-plan)
├── research.md          # Decisões técnicas e alternativas (Phase 0)
├── data-model.md        # Projeção derivada e schemas públicos (Phase 1)
├── quickstart.md        # Guia de execução e validação (Phase 1)
├── contracts/
│   └── ranking-api.md   # Contrato HTTP dos endpoints de ranking (Phase 1)
└── tasks.md             # Tarefas de implementação (/speckit-tasks - Phase 2)
```

### Source Code (repository root)

```text
src/
└── sidebrain_back/
    ├── models/
    │   ├── user_model.py              # Existente (leitura)
    │   ├── mission_model.py           # Existente (leitura)
    │   └── mission_progress_model.py  # Existente (leitura)
    ├── repositories/
    │   └── ranking_repository.py      # Novo: list_rankings, count_ranked_users, get_user_ranking
    ├── schemas/
    │   └── ranking_schema.py          # Novo: RankingEntryResponse, RankingListResponse
    ├── services/
    │   └── ranking_service.py         # Novo: RankingService (list_rankings, get_my_ranking)
    └── routers/
        ├── router.py                  # Atualizado: inclui ranking_router
        └── v1/
            └── ranking_router.py      # Novo: GET /rankings, GET /rankings/me

tests/
├── contract/
│   └── test_ranking_contract.py       # Novo: testes de contrato HTTP (200, 401, 404, 422)
├── integration/
│   └── test_ranking_lifecycle.py      # Novo: testes de integração SQL (XP, empates, paginação, N+1)
└── unit/
    ├── test_ranking_schema.py         # Novo: testes unitários de serialização/aliases
    └── test_ranking_service.py        # Novo: testes unitários de serviço
```

**Structure Decision**: Manter a estrutura em camadas existente em `src/sidebrain_back/` e `tests/`, adicionando os quatro arquivos do domínio `ranking` (`ranking_schema.py`, `ranking_repository.py`, `ranking_service.py`, `ranking_router.py`) e registrando o router em `src/sidebrain_back/routers/router.py`.

## Complexity Tracking

Nenhuma violação constitucional ou complexidade adicional precisa de justificativa.
