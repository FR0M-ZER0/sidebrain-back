# Implementation Plan: Gerenciamento de Etapas

**Branch**: `SDB-58-step-management` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-58-step-management/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Implementar o CRUD de `Step` sob um `Track` do usuário autenticado, mantendo
autorização por ownership, soft delete e respostas hierárquicas de leitura.
O desenho seguirá o fluxo existente `router -> service -> repository -> model`,
com schemas públicos Pydantic e carregamento agrupado da árvore por
`selectinload`.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python >=3.11

**Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2 async ORM, Alembic, `uv`

**Storage**: PostgreSQL via `AsyncSession`; modelo `step` já existente

**Testing**: Pytest unitário, integração e contratos HTTP; Ruff para lint

**Target Platform**: Serviço web FastAPI executado no ambiente do backend

**Project Type**: Web service REST versionado em `/v1`

**Performance Goals**: Operações válidas em até 2 segundos sob a carga esperada; consultas hierárquicas sem N+1 por filho

**Constraints**: `track_id` somente na URL; somente `level` e `title` são editáveis; filhos apenas leitura; soft delete sem cascata lógica

**Scale/Scope**: Cinco operações de Step: criar, listar, consultar, atualizar e remover; composição de Lesson/Mission e seus filhos existentes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Princípios I-II: responsabilidades pequenas e coesas serão distribuídas entre schemas, router, service e repository.
- [x] Princípio III: dependências seguirão `routers -> services -> repositories -> models`, com `Depends` nos providers.
- [x] Princípio IV: o plano inclui testes unitários, de integração e de contrato para o novo recurso.
- [x] Princípio V: será reutilizado o padrão existente de paginação, Problem Details e carregamento hierárquico, sem abstrações especulativas.
- [x] Padrões técnicos: FastAPI/Pydantic/SQLAlchemy/Alembic/Pytest/uv e schemas com `from_attributes=True`.

**Gate pré-pesquisa**: PASS. Não há violação constitucional nem clarificação pendente na especificação.

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
    ├── models/step_model.py
    ├── repositories/step_repository.py
    ├── schemas/step_schema.py
    ├── services/step_service.py
    └── routers/v1/step_router.py

tests/
├── contract/
│   └── test_step_contract.py
├── integration/
│   └── test_step_hierarchy_queries.py
└── unit/
    ├── test_step_schema.py
    └── test_step_service.py
```
**Structure Decision**: Projeto único FastAPI já existente. A feature adiciona
os módulos específicos de Step nas camadas existentes e testes correspondentes;
o modelo, os enums e os schemas de conteúdo já presentes serão reutilizados.
O novo `step_router` também será incluído em `src/sidebrain_back/routers/router.py`,
preservando o caminho público efetivo `/api/v1/tracks/{track_id}/steps`. Não há
alteração de estrutura de banco prevista.

**Design pós-pesquisa**: PASS. O carregamento aninhado usa `selectinload` com
filtros de exclusão lógica e ownership de progresso, e os contratos públicos
ocultam nomes físicos e campos de auditoria. A listagem de Steps terá ordenação
estável por `stp_updated_at DESC, stp_id DESC`; a criação retorna o Step recém-
persistido com `lessons` e `missions` vazios, pois não há filhos criados nessa
operação.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma | N/A | A solução permanece dentro das camadas e abstrações existentes. |
