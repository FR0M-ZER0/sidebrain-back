# Implementation Plan: Gerenciamento de Trilhas

**Branch**: `SDB-49-track-management` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/SDB-49-track-management/spec.md`

## Summary

Implementar o CRUD autenticado de trilhas próprias, com exclusão lógica, paginação e leitura da hierarquia de etapas e conteúdos. A solução seguirá `router -> service -> repository -> model`, schemas Pydantic separados dos modelos ORM, uma dependência central de usuário autenticado e consultas SQLAlchemy assíncronas com `selectinload` encadeado e filtros de exclusão lógica para evitar N+1.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: FastAPI 0.141+, Pydantic, SQLAlchemy 2.0 async, asyncpg, Alembic, pytest/httpx

**Storage**: PostgreSQL existente, via `AsyncSession`; a migration inicial já contém a hierarquia de trilhas

**Testing**: pytest, testes unitários de service/repository e testes de integração HTTP com PostgreSQL

**Target Platform**: Serviço ASGI executado com Uvicorn em ambiente Linux/containerizado

**Project Type**: Web service REST versionado

**Performance Goals**: 95% das operações válidas em até 2 segundos sob carga esperada; leitura da árvore sem consultas por filho

**Constraints**: ownership obrigatório; somente trilhas ativas; Problem Details; paginação com limites; requests não aceitam IDs internos, proprietário ou auditoria

**Scale/Scope**: Endpoints de trilha em `/api/v1`; filhos somente leitura; sem CRUD de etapas, lições, missões ou recursos nesta feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

O arquivo de constituição ainda contém somente placeholders e não define princípios ratificados ou gates executáveis. Não há violação formal a avaliar; aplicam-se como requisitos normativos as convenções existentes em `docs/architecture.md` e `docs/code_conventions.md`. **PASS**, condicionado à validação dos contratos e testes descritos abaixo.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-49-track-management/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
```text
src/
├── main.py
└── sidebrain_back/
  ├── core/                 # sessão, autenticação e handlers de erro
  ├── models/               # modelos ORM existentes
  ├── repositories/         # track_repository.py
  ├── schemas/              # track_schema.py e paginação
  ├── services/             # track_service.py
  └── routers/v1/           # track_router.py

tests/
├── unit/                     # regras de serviço e consultas
├── integration/              # fluxo HTTP com PostgreSQL
└── contract/                 # respostas e status do contrato
```

**Structure Decision**: Web service único com separação explícita por camadas, mantendo os modelos existentes e adicionando `repositories`, `schemas`, `services`, o router versionado e testes focados na feature. A autenticação será consumida por provider central (`get_current_user`); login/token não será criado nesta feature.

## Implementation Phases

### Phase 0: Research

- Definir o boundary de autenticação como `get_current_user`, retornando `401` sem credencial válida e sem aceitar `userId` em requests.
- Usar `selectinload` encadeado para a árvore Track -> Step -> Lesson/Mission -> recursos, com critérios de exclusão lógica e progresso filtrado pelo usuário autenticado.
- Adotar `page=1` e `page_size=20`, com `page >= 1` e `1 <= page_size <= 100`; ordenar por `trk_created_at` e `trk_id` para paginação determinística.
- Manter a migration inicial; criar migration adicional somente se a medição justificar índices para ownership/exclusão lógica.

### Phase 1: Design and Contracts

- Criar schemas de entrada separados dos schemas de resposta, incluindo a árvore e o envelope paginado.
- Criar repository assíncrono com filtros de ownership/soft delete, contagem separada e eager loading agrupado.
- Criar service para CRUD, timestamps, exclusão lógica e tradução de ausência em recurso não encontrado.
- Criar router `/api/v1/tracks` e handlers Problem Details para validação, `404` e falhas de persistência.
- Cobrir contrato HTTP, ownership, paginação, validação, exclusão lógica, árvore completa e ausência de N+1.

## Requirement Mapping

| Requisitos | Decisão/artefato |
|---|---|
| FR-001 a FR-003, FR-006 a FR-009, FR-013, FR-014 | schemas, service e endpoints CRUD |
| FR-004, FR-010, FR-011 | repository com ownership/soft delete e Problem Details |
| FR-005 | contrato paginado e consulta `count` + `limit/offset` |
| FR-005a a FR-005d | `data-model.md`, contrato hierárquico e `selectinload` |
| FR-012 | router versionado `/api/v1/tracks` |
| SC-001 a SC-006 | `quickstart.md` e testes unitários, de integração e contrato |

## Constitution Check (post-design)

**PASS**: o desenho respeita as camadas documentadas, mantém dependências direcionadas, separa ORM de schemas, usa DI e inclui validação automatizada. A constituição placeholder não impõe gates adicionais.

## Complexity Tracking

Nenhuma violação de constituição foi identificada; não há complexidade excepcional a justificar.
