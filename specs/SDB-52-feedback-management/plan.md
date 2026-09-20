# Implementation Plan: Gerenciamento de Feedback

**Branch**: `feat/sdb-52-adiciona-endpoints-de-feedback` | **Date**: 2026-09-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/SDB-52-feedback-management/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Adicionar o ciclo de vida de feedbacks associados a aulas, preservando autoria,
exclusão lógica e isolamento das operações de escrita. A implementação seguirá
schemas, repository, service e router versionado. A consulta da hierarquia de
trilhas continuará carregando apenas feedbacks ativos com `selectinload`, sem
N+1.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python >= 3.11

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, Alembic, uv

**Storage**: PostgreSQL; tabela `feedback` já existe na migration inicial

**Testing**: Pytest, testes unitários, de integração e de contrato

**Target Platform**: Serviço HTTP executado em Linux/container via Docker Compose

**Project Type**: Web service/API

**Performance Goals**: Consultas devem carregar feedbacks em lote, sem uma query por feedback; o cenário de 50 feedbacks deve permanecer constante por relação carregada

**Constraints**: AsyncSession, `get_current_user`, exclusão lógica, requests sem IDs/autoria/timestamps/flags internos e erros em Problem Details

**Scale/Scope**: Uma entidade e cinco operações HTTP, integrada à leitura de aulas/trilhas; sem CRUD de usuários ou aulas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate inicial: PASS

- Princípios I e II: schemas, services, repositories e models mantêm responsabilidades únicas.
- Princípio III: fluxo `routers -> services -> repositories -> models`, com `Depends`.
- Princípio IV: o plano inclui testes unitários, de integração, contrato e contagem de queries.
- Princípio V: reutiliza a API v1, a tabela existente e a exclusão lógica, sem abstrações especulativas.
- Padrões técnicos: FastAPI, Pydantic, SQLAlchemy, Alembic, Pytest e `uv` são preservados.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/
├── main.py
└── sidebrain_back/
  ├── core/
  ├── models/feedback_model.py, lesson_model.py, user_model.py
  ├── repositories/feedback_repository.py
  ├── routers/v1/feedback_router.py
  ├── schemas/feedback_schema.py, track_schema.py
  └── services/feedback_service.py

tests/
├── contract/test_feedback_contract.py
├── integration/test_feedback_lifecycle.py, test_feedback_hierarchy_queries.py
└── unit/test_feedback_service.py
```

**Structure Decision**: Manter o serviço único existente e adicionar módulos de
feedback nas camadas correspondentes. O modelo e as relações já existem; não
será criada migration, salvo se a validação identificar necessidade real de
índice.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0: Research Summary

As decisões e alternativas estão registradas em [research.md](research.md). Não
restam incógnitas técnicas no contexto do plano.

## Phase 1: Design Outputs

- [data-model.md](data-model.md): entidade, relações, filtros e transições.
- [contracts/feedbacks.md](contracts/feedbacks.md): endpoints e payloads.
- [quickstart.md](quickstart.md): setup e cenários de validação executáveis.

## Constitution Check (pós-design): PASS

O design mantém a separação de camadas, usa contratos Pydantic com aliases,
define cobertura para os cenários de aceite e mantém a leitura eager carregada
em lote. Não há violação que exija entrada em Complexity Tracking.
