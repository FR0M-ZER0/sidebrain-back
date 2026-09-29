# Implementation Plan: Gerenciamento de Quizzes

**Branch**: `feat/sdb-51-criar-endpoint-para-gerenciamento-dos-quizzes` | **Date**: 2026-09-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/SDB-51-quiz-management/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Adicionar o CRUD autenticado de quizzes associados a aulas, com pergunta
normalizada, exclusão lógica, paginação e respostas existentes carregadas como
filhas. A implementação seguirá `router -> service -> repository -> model`,
aplicará ownership pela hierarquia `Quiz -> Lesson -> Step -> Track` e usará
`selectinload` e ordenação determinística para compor quizzes e respostas sem
N+1, inclusive nas respostas hierárquicas de trilhas.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: FastAPI >= 0.141.1, Pydantic v2, SQLAlchemy 2 async >= 2.0.52, asyncpg, Alembic e uv

**Storage**: PostgreSQL 16 no ambiente de desenvolvimento; tabelas `quiz` e `answer` já existem na migration inicial

**Testing**: Pytest >= 9.1.1, HTTPX/TestClient, testes unitários, de integração e de contrato

**Target Platform**: Serviço HTTP ASGI executado em Linux/container via Docker Compose

**Project Type**: Web service/API

**Performance Goals**: Em `MODE=test`, com PostgreSQL 16 via Docker Compose e sem concorrência, executar 5 requisições de aquecimento e medir 100 requisições autenticadas sequenciais a `GET /api/v1/lessons/{lesson_id}/quizzes?page=1&page_size=50`; o p95 end-to-end deve ser <= 2 segundos para 50 quizzes ativos com 10 respostas cada, e a quantidade de statements SQL deve permanecer constante entre cenários com 1 e 50 quizzes

**Constraints**: `AsyncSession`; autenticação por `get_current_user`; ownership herdado da trilha; pais e quiz não excluídos; pergunta com 1–1.000 caracteres após `strip()`; soft delete; contratos sem nomes físicos; respostas em Problem Details

**Scale/Scope**: Uma entidade gerenciada em cinco operações HTTP, leitura de `Answer[]` existente e atualização das hierarquias de aula/trilha; CRUD de Answer fora do escopo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate inicial: PASS

- Princípios I e II: validação, regra de negócio, persistência e HTTP ficam em módulos coesos e separados.
- Princípio III: o fluxo permanece `routers -> services -> repositories -> models`, com composição por `Depends`.
- Princípio IV: o plano inclui testes unitários, integração PostgreSQL, contrato público, soft delete, ownership e contagem de queries.
- Princípio V: a mudança é aditiva na API v1; a hierarquia existente ganha campos sem remover os já publicados e não há abstração ou migration especulativa.
- Padrões técnicos: FastAPI, Pydantic, SQLAlchemy async, Alembic, Pytest, `uv`, paginação padrão e Problem Details são preservados.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-51-quiz-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── quizzes.md
└── tasks.md                 # Phase 2; não criado por /speckit-plan
```

### Source Code (repository root)

```text
src/
├── main.py
└── sidebrain_back/
    ├── core/
    │   ├── auth.py
    │   ├── database.py
    │   └── errors.py
    ├── models/
    │   ├── answer_model.py
    │   ├── lesson_model.py
    │   └── quiz_model.py
    ├── repositories/
    │   ├── quiz_repository.py
    │   └── track_repository.py
    ├── routers/
    │   ├── router.py
    │   └── v1/quiz_router.py
    ├── schemas/
    │   ├── pagination_schema.py
    │   ├── quiz_schema.py
    │   └── track_schema.py
    └── services/quiz_service.py

tests/
├── contract/
│   ├── test_quiz_contract.py
│   └── test_track_read_contract.py
├── integration/
│   ├── test_quiz_hierarchy_queries.py
│   └── test_quiz_lifecycle.py
└── unit/
    ├── test_quiz_schema.py
    └── test_quiz_service.py
```

**Structure Decision**: Manter o serviço único com layout `src`, criar os
módulos próprios de quiz nas camadas existentes e ajustar somente modelos,
schema e repository da hierarquia que já expõem `Lesson -> Quiz -> Answer`.
As tabelas e colunas necessárias já existem; nenhuma migration será criada sem
evidência de plano de execução que justifique índices adicionais.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0: Research Summary

As decisões, fundamentos e alternativas estão em [research.md](research.md).
Não restam `NEEDS CLARIFICATION`: contrato, acesso, paginação, ordenação,
transações, composição hierárquica e estratégia de consultas foram resolvidos.

## Phase 1: Design Outputs

- [data-model.md](data-model.md): campos, relações, validações, acesso e transições de estado.
- [contracts/quizzes.md](contracts/quizzes.md): endpoints, payloads, respostas e erros.
- [quickstart.md](quickstart.md): preparação e cenários executáveis de validação.

## Constitution Check (pós-design): PASS

O design continua aditivo, preserva campos já publicados pela resposta de
trilhas, centraliza autorização e persistência no repository/service, não expõe
colunas físicas e define cobertura proporcional aos riscos de ownership,
exclusão lógica, hierarquia e N+1. Não há violação a registrar em Complexity
Tracking.
