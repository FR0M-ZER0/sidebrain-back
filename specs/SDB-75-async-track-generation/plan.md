# Implementation Plan: Geração assíncrona de Trilhas e preparação de Steps

**Branch**: `SDB-75-async-track-generation` | **Date**: 2026-09-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/SDB-75-async-track-generation/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Alterar a criação de Trilhas para aceitar um contexto de aprendizagem, registrar uma solicitação idempotente e enfileirar `tasks.generate_track` sem aguardar o provedor de IA. A solicitação retornará `202 Accepted` com `request_id`; o worker atualizará o estado e persistirá a Trilha completa em transação, ou uma falha observável com `error_code`. A mesma camada de serviço será exposta por `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next`, preservando a regra existente de elegibilidade, o threshold de 80% e a task incremental.

## Technical Context

**Language/Version**: Python >=3.11

**Primary Dependencies**: FastAPI 0.141+, Pydantic 2.11+, SQLAlchemy 2.0+, Celery 5.6+, PostgreSQL/asyncpg, Alembic

**Storage**: PostgreSQL; tabelas existentes de Track/Step/Lesson/Quiz/Mission e nova persistência de solicitação de geração

**Testing**: pytest, testes de contrato, unitários e de integração; `uv run ruff check .`; `uv run pytest`

**Target Platform**: Serviço Linux executado via FastAPI e worker Celery

**Project Type**: Web service HTTP versionado

**Performance Goals**: Responder as solicitações aceitas sem aguardar Groq; o tempo do endpoint deve ser limitado à validação, persistência do pedido e publicação da mensagem Celery

**Constraints**: Não executar geração de IA no ciclo HTTP; manter idempotência por `request_id`, retry limitado existente, transação atômica e Problem Details RFC 9457; não alterar threshold, paginação ou domínios fora do escopo

**Scale/Scope**: Fluxos de criação de Track e preparação incremental, seus schemas, repositories, services, tasks, migração e testes associados; sem frontend ou endpoint de consulta de progresso novo

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Qualidade e Clean Code**: PASS. O plano reutiliza schemas/tasks/services existentes e limita mudanças às responsabilidades afetadas.
- **II. Responsabilidade única**: PASS. Router compõe HTTP/Depends, service decide idempotência e enfileiramento, repository persiste, task executa background.
- **III. Separação de camadas**: PASS. O router não importará task/repository diretamente; tasks manterão sessão própria.
- **IV. Testes e contratos verificáveis**: PASS condicionado à implementação. Serão atualizados contratos, testes de endpoint, unitários e integração para 202, conflito, falhas e ownership.
- **V. Simplicidade e evolução segura**: PASS. A API v1 mantém a rota e altera explicitamente seu contrato de criação; erros serão Problem Details e estados estruturados.

Não há violação constitucional que exija justificativa.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-75-async-track-generation/
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
├── sidebrain_back/
│   ├── models/
│   ├── repositories/
│   ├── routers/v1/
│   ├── schemas/
│   ├── services/
│   └── tasks/
└── main.py

tests/
├── contract/
├── integration/
└── unit/

```

**Structure Decision**: Projeto único FastAPI em `src/sidebrain_back`, organizado pelas camadas normativas. A nova entidade/estado de solicitação será modelada em `models`, acessada por `repositories`, orquestrada por `services` e atualizada pela task; contratos e testes permanecem no diretório da feature e em `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Persistência própria de solicitação de geração | É necessário representar `pending`, `succeeded` e `failed` antes da criação da Track e guardar fingerprint/erro sem sobrecarregar `Track` | Usar apenas `Track.trk_generation_request_id` não representa falha ou pedido pendente e não permite detectar contexto divergente antes da geração |

## Phase 0: Research Summary

As decisões e evidências estão em [research.md](research.md). FastAPI permite declarar o contrato Pydantic e o status 202 no endpoint, enquanto Celery `delay()` publica a task e retorna um `AsyncResult`; retry continuará restrito às exceções transitórias já configuradas.

## Phase 1: Design Summary

- [data-model.md](data-model.md) define a solicitação, estados, fingerprint e relações com Track.
- [contracts/track-generation.md](contracts/track-generation.md) define os contratos HTTP de criação e preparação.
- [quickstart.md](quickstart.md) define a validação executável e os cenários de aceite.

## Constitution Check: pós-design

- **I. Qualidade e Clean Code**: PASS. O design separa estado de solicitação, domínio de Track e conteúdo incremental sem duplicar a regra de geração.
- **II. Responsabilidade única**: PASS. Fingerprint e transições ficam no service/repository; publicação e retry ficam na task; contratos ficam nos schemas/routers.
- **III. Separação de camadas**: PASS. O contrato exige `Depends` no router e impede acesso HTTP direto em services/tasks.
- **IV. Testes e contratos verificáveis**: PASS. O quickstart mapeia os cenários aos testes de contrato, unidade e integração, incluindo concorrência.
- **V. Simplicidade e evolução segura**: PASS. A solução reutiliza as tasks existentes e adiciona apenas a persistência necessária para estado e conflito.

O gate pós-design passa; não há violação constitucional aberta nem clarificação pendente.
