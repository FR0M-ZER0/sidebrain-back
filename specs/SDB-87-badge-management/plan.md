# Implementation Plan: Gerenciamento de Badges

**Branch**: `SDB-87-badge-management` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/SDB-87-badge-management/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Adicionar o CRUD autenticado de badges do catálogo global, com paginação,
normalização e unicidade de nomes ativos, exclusão lógica e composição do
progresso do usuário autenticado. A implementação seguirá
`router -> service -> repository -> model`, usando schemas públicos, filtros de
soft delete e `selectinload` filtrado pelo usuário para evitar exposição de
progressos de terceiros.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: FastAPI >= 0.141.1, Pydantic v2, SQLAlchemy 2 async >= 2.0.52, asyncpg, Alembic e uv

**Storage**: PostgreSQL 16; tabelas `badge` e `badge_progress` já existem na migration inicial

**Testing**: Pytest >= 9.1.1, HTTPX/TestClient, testes unitários, de integração e de contrato

**Target Platform**: Serviço HTTP ASGI executado em Linux/container via Docker Compose

**Project Type**: Web service/API

**Performance Goals**: Listar 100 badges com quantidade constante de statements SQL entre 1 e 100 itens; manter p95 <= 2 s em 100 requisições autenticadas sequenciais no ambiente de teste

**Constraints**: `AsyncSession`; autenticação por `get_current_user`; todos os badges são globais; soft delete; nomes e enums validados; contratos sem nomes físicos; erros em Problem Details

**Scale/Scope**: Uma entidade gerenciada em cinco operações HTTP, leitura filtrada de `BadgeProgress` existente; evolução do progresso e CRUD de `BadgeProgress` fora do escopo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate inicial: PASS

- Princípios I e II: normalização, unicidade, transação e composição ficam divididas entre schemas, service e repository.
- Princípio III: os endpoints usarão `routers -> services -> repositories -> models`, com providers via `Depends`.
- Princípio IV: o design prevê testes unitários, de integração PostgreSQL e de contrato para autenticação, paginação, soft delete e isolamento de progresso.
- Princípio V: a mudança é aditiva na API v1, usa os modelos existentes e mantém erros públicos no formato Problem Details.
- Padrões técnicos: FastAPI, Pydantic, SQLAlchemy async, Alembic, Pytest, `uv`, paginação normativa e schemas com `from_attributes=True`.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-87-badge-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── badges.md
└── tasks.md             # criado posteriormente pelo fluxo speckit-tasks
```

### Source Code (repository root)
```text
src/
├── main.py
└── sidebrain_back/
  ├── models/badge_model.py, badge_progress_model.py
  ├── repositories/badge_repository.py
  ├── routers/v1/badge_router.py
  ├── schemas/badge_schema.py
  └── services/badge_service.py

tests/
├── contract/test_badge_contract.py
├── integration/test_badge_lifecycle.py
└── unit/test_badge_schema.py, test_badge_service.py

```

**Structure Decision**: Manter o serviço único com layout `src`, criar os
módulos próprios de Badge nas camadas existentes e registrar o router em
`routers/router.py`. Os modelos e enums já existem; não será criada migration
porque a feature apenas expõe o CRUD e carrega progressos existentes.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0: Research Summary

As decisões, fundamentos e alternativas estão em [research.md](research.md).
Todas as dúvidas técnicas foram resolvidas: os contratos, regras de validação,
persistência, filtros de acesso e estratégia de carregamento foram resolvidos.

## Phase 1: Design Outputs

- [data-model.md](data-model.md): entidades, campos, relações, validações e ciclo de soft delete.
- [contracts/badges.md](contracts/badges.md): endpoints, payloads, respostas e erros públicos.
- [quickstart.md](quickstart.md): cenários executáveis de validação da feature.

## Constitution Check (pós-design): PASS

O design mantém as camadas existentes, não altera a estrutura de banco, não
expõe colunas físicas ou relacionamentos internos e define cobertura para os
riscos de unicidade normalizada, isolamento por usuário, paginação além do
total e exclusão lógica. Não há violação a registrar em Complexity Tracking.
