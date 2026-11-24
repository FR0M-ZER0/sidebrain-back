# Implementation Plan: Avatar do perfil do usuário

**Branch**: `SDB-111-user-avatar` | **Date**: 2026-11-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-111-user-avatar/spec.md`

## Summary

Adicionar ao perfil autenticado um avatar selecionável por slug, usando um catálogo
versionado no backend e imagens estáticas servidas pela API. A seleção será
persistida como uma referência opcional ao catálogo; o serviço validará apenas
avatares ativos e resolverá a imagem padrão para perfis sem seleção ou com
referência inativa. O contrato existente de `GET|PUT /api/v1/users/me` será
estendido sem criar um fluxo paralelo de perfil, e um novo endpoint autenticado
fornecerá somente o catálogo ativo.

## Technical Context

**Language/Version**: Python >=3.11

**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2 async, Alembic

**Storage**: PostgreSQL para catálogo e referência no usuário; arquivos PNG
versionados em `src/sidebrain_back/static/avatars/`

**Testing**: Pytest, testes de contrato e integração existentes

**Target Platform**: Serviço web FastAPI executado via `uv`/Uvicorn

**Project Type**: Web service/API

**Performance Goals**: Consulta de catálogo e perfil deve usar uma leitura
assíncrona simples; não há meta de throughput nova para esta feature

**Constraints**: Sem upload ou processamento de imagens; apenas slugs ativos podem
ser persistidos; migração backward-compatible e erros em Problem Details

**Scale/Scope**: Dez registros iniciais, um catálogo pequeno mantido por
migrações/arquivos versionados, todos os usuários existentes preservados

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Pass — antes da pesquisa**

- I/II: regras de seleção ficam no `UserService`; persistência fica em
  `UserRepository`/repositório de avatar; modelos não conterão lógica.
- III: o fluxo seguirá `routers -> services -> repositories -> models`, com
  schemas Pydantic e `Depends`.
- IV: o plano inclui testes unitários, de integração e de contrato para cada
  comportamento novo, além de regressão do perfil.
- V: o contrato existente será apenas ampliado; a migração será aditiva,
  reversível quando possível, e erros públicos continuarão em RFC 9457.

Não há violação constitucional que exija uma exceção.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-111-user-avatar/
├── plan.md
├── research.md
├── data-model.md
├── contracts/avatar-api.md
└── quickstart.md
```

### Source Code (repository root)

```text
src/
├── main.py
└── sidebrain_back/
    ├── models/user_model.py
    ├── models/avatar_model.py
    ├── repositories/user_repository.py
    ├── repositories/avatar_repository.py
    ├── schemas/user_schema.py
    ├── schemas/avatar_schema.py
    ├── services/user_service.py
    ├── services/avatar_service.py
    ├── routers/v1/user_router.py
    ├── routers/v1/avatar_router.py
    └── static/avatars/

migrations/versions/
└── <new_avatar_migration>.py

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Manter o único serviço FastAPI existente. O catálogo
receberá modelo/repositório/serviço/rota próprios para respeitar responsabilidade
única; a leitura e atualização do perfil continuarão no fluxo de usuário. As
imagens serão empacotadas junto ao módulo e montadas por `StaticFiles` em
`/static`, enquanto o catálogo protegido continuará sob `/api/v1`.

## Phase 0 — Research

Consolidar decisões em [research.md](./research.md), cobrindo persistência,
imagens estáticas, contratos protegidos e validação transacional.

## Phase 1 — Design & Contracts

Gerar [data-model.md](./data-model.md), [contracts/avatar-api.md](./contracts/avatar-api.md)
e [quickstart.md](./quickstart.md). A revisão pós-design mantém todos os gates
constitucionais aprovados: camadas separadas, contrato compatível, migração
aditiva, Problem Details e testes nos níveis apropriados.

## Complexity Tracking

Nenhuma violação constitucional.
