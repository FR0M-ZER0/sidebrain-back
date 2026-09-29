# Implementation Plan: Gerenciamento de Lições

**Branch**: `feat/sdb-57-criar-endpoint-para-gerenciamento-das-licoes` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-57-lesson-management/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Implementar o CRUD autenticado de `Lesson`, com criação e listagem subordinadas
a `Step`, detalhe e mutações por `lesson_id`, atualização completa, exclusão
lógica e conflito de posição protegido também contra concorrência. O desenho
mantém o fluxo `router -> service -> repository -> model`, valida ownership por
`Lesson -> Step -> Track -> User` e carrega os filhos visíveis com
`selectinload`, sem consultas por item filho.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: FastAPI >= 0.141.1, Pydantic >= 2.11, SQLAlchemy async >= 2.0.52, asyncpg, Alembic e `uv`

**Storage**: PostgreSQL 16; tabelas, enums, FKs, campos de soft delete e constraint única de `lesson` já existem na migration inicial

**Testing**: Pytest >= 9.1.1, HTTPX/ASGITransport, testes unitários, de contrato e de integração com PostgreSQL; Ruff para lint

**Target Platform**: Serviço HTTP ASGI executado em Linux/container e no ambiente local suportado pelo Docker Compose

**Project Type**: Web service/API REST versionada

**Performance Goals**: No protocolo de SC-007, p95 end-to-end <= 2 segundos para 100 leituras sequenciais da primeira página com 50 Lessons e a cardinalidade de filhos especificada; quantidade de comandos SQL idêntica nos cenários equivalentes de 1 e 50 Lessons

**Constraints**: `AsyncSession`; Bearer resolvido por `get_current_user`; pais ativos e Track pertencente ao usuário; `PUT` completo; posição inteira >= 1, única por Step inclusive após soft delete; filhos somente leitura; respostas Problem Details; nenhuma remoção física ou cascata lógica

**Scale/Scope**: Cinco operações HTTP sobre uma entidade gerenciada e composição de quatro tipos de filhos existentes; CRUD de Feedback, LessonFile, Quiz e Answer permanece fora do escopo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate inicial: PASS

- Princípios I e II: validação de payload, autorização, regra de conflito,
  persistência e transporte HTTP permanecem em unidades pequenas e coesas.
- Princípio III: a dependência segue `routers -> services -> repositories ->
  models`; os providers de repository e service ficam junto às classes e usam
  `Depends`.
- Princípio IV: o plano inclui testes unitários, de contrato e de integração
  PostgreSQL para ownership, transações, soft delete, unicidade, hierarquia e
  contagem de queries.
- Princípio V: a API v1 recebe endpoints aditivos; contratos hierárquicos já
  publicados por Track/Step são preservados, e erros seguem Problem Details.
- Padrões técnicos: FastAPI, Pydantic, SQLAlchemy async, Alembic, Pytest, `uv`,
  paginação e aliases públicos seguem os documentos normativos do projeto.

Não há violação constitucional nem `NEEDS CLARIFICATION` pendente.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-57-lesson-management/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── lessons.md
└── tasks.md                 # Phase 2; não criado por /speckit-plan
```

### Source Code (repository root)

```text
src/
└── sidebrain_back/
    ├── core/
    │   ├── auth.py
    │   ├── database.py
    │   └── errors.py
    ├── enums/lesson_status_enum.py
    ├── models/
    │   ├── answer_model.py
    │   ├── feedback_model.py
    │   ├── lesson_file_model.py
    │   ├── lesson_model.py
    │   ├── quiz_model.py
    │   ├── step_model.py
    │   └── track_model.py
    ├── repositories/lesson_repository.py
    ├── routers/
    │   ├── router.py
    │   └── v1/lesson_router.py
    ├── schemas/
    │   ├── lesson_schema.py
    │   └── pagination_schema.py
    └── services/lesson_service.py

tests/
├── contract/test_lesson_contract.py
├── integration/
│   ├── test_lesson_hierarchy_queries.py
│   └── test_lesson_lifecycle.py
└── unit/
    ├── test_lesson_schema.py
    └── test_lesson_service.py
```

**Structure Decision**: Manter o projeto FastAPI único no layout `src`. Criar
os quatro módulos próprios de Lesson nas camadas existentes e registrar o novo
router no agregador. Reutilizar autenticação, paginação, enums e schemas
públicos de filhos quando compatíveis; o response direto de Lesson mantém
`files`, enquanto os contratos anteriores de Track/Step não são renomeados
nesta feature. O modelo e a migration inicial já satisfazem persistência,
inclusive a reserva de posição após soft delete, portanto não há migration
planejada.

## Complexity Tracking

Não se aplica: o design não viola a constituição nem introduz nova camada,
serviço externo ou abstração transversal.

## Phase 0: Research Summary

As decisões e alternativas estão em [research.md](./research.md). Foram
resolvidos contrato HTTP, aliases públicos, autorização, concorrência da
posição, estratégia de eager loading, unidade transacional, compatibilidade e
protocolo de desempenho. Não restam clarificações abertas.

## Phase 1: Design Outputs

- [data-model.md](./data-model.md): entidades, campos, relacionamentos,
  validações, visibilidade e transições.
- [contracts/lessons.md](./contracts/lessons.md): cinco endpoints, payloads,
  responses, paginação e erros.
- [quickstart.md](./quickstart.md): preparação e cenários executáveis de
  validação funcional, transacional e de desempenho.

## Constitution Check (pós-design): PASS

O design final mantém autorização e filtros no acesso a dados, regras e
transações no service, contratos no schema e HTTP no router. A constraint do
banco é a autoridade final contra corridas de posição; os erros de domínio são
mapeados sem expor SQL. O carregamento agrupado é verificável por contagem de
statements, e a cobertura proposta inclui todos os riscos materiais. Nenhuma
exceção constitucional precisa ser registrada.
