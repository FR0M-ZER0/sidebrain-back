# Implementation Plan: Geração incremental de conteúdo de Steps

**Branch**: `SDB-60-incremental-step-content` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/SDB-60-incremental-step-content/spec.md`

## Summary

Implementar a preparação assíncrona do próximo Step quando o progresso do atual ultrapassa o threshold de 80%, sem bloquear a operação principal. A solução reutiliza a arquitetura atual do backend em `router -> service -> repository -> model`, e cria uma task Celery dedicada para validar o contexto da Track, gerar as entidades de Lesson/Quiz/Mission e persistir tudo em uma transação atômica, com idempotência e retry controlado.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy async, Alembic, Celery, Groq, pytest, uv

**Storage**: PostgreSQL existente, via `AsyncSession`, usando as tabelas de `track`, `step`, `lesson`, `quiz` e `mission` já presentes no domínio

**Testing**: pytest; testes unitários, integração e contrato conforme já adotados pelo projeto

**Target Platform**: Serviço ASGI em Linux/container com Celery worker em background

**Project Type**: Web service/API backend

**Performance Goals**: Atualização do progresso deve permanecer responsiva; a geração do próximo Step não deve bloquear a requisição; a task assíncrona deve evitar N+1 e manter as consultas de contexto limitadas ao domínio necessário

**Constraints**: sem novos endpoints HTTP; soft delete aplicado a Tracks/Steps/Lessons/Quizzes/Missions; ownership e relacionamento pela mesma Track; provisionamento do provedor externo fora do escopo; logs com observabilidade sem exposição de credenciais

**Scale/Scope**: Feature incremental para preparar conteúdo do próximo Step, sem abrir novos contratos públicos nem criar Answers, Feedbacks, LessonFiles ou MissionProgress

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate inicial: PASS

- Princípio I e II: a lógica de negócio fica em services/tasks, persistência em repository/models e HTTP em routers; as regras de progresso e geração seguem responsabilidade única.
- Princípio III: a estrutura continua `routers -> services -> repositories -> models`, com a task em `tasks/` orquestrando o processamento assíncrono sem expor detalhes HTTP.
- Princípio IV: a feature exige testes unitários, integração e contrato na mesma linha das outras features do projeto; o risco de concorrência, retry e persistência atômica exige cobertura específica.
- Princípio V: não há abstração especulativa nem mudança incompatível de API; a feature é aditiva e preserva contratos públicos já existentes.
- Padrões técnicos: FastAPI, Pydantic, SQLAlchemy async, Alembic, Celery, `uv`, Problem Details e paginação compatível com o código existente são mantidos.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-60-incremental-step-content/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── incremental-step-content.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── main.py
└── sidebrain_back/
    ├── core/
    │   ├── auth.py
    │   ├── celery_app.py
    │   ├── database.py
    │   └── errors.py
    ├── models/
    │   ├── lesson_model.py
    │   ├── mission_model.py
    │   ├── quiz_model.py
    │   ├── step_model.py
    │   └── track_model.py
    ├── repositories/
    │   ├── track_repository.py
    │   └── ...
    ├── routers/
    │   └── v1/
    ├── schemas/
    │   ├── track_schema.py
    │   └── ...
    ├── services/
    │   ├── track_service.py
    │   └── ...
    └── tasks/
        ├── knowledge_assessment_task.py
        └── ...

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Manter a arquitetura monolítica em um único backend com separação por camada e adicionar a task e service necessários na mesma estrutura já usada por `track`, `quiz` e `knowledge assessment`. A feature reusa `Track`, `Step`, `Lesson`, `Quiz` e `Mission` já existentes e evita criar novas rotas ou schemas públicos; qualquer funcionalidade nova fica em task/service + repository de apoio, sem ampliar a API HTTP.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0: Research Summary

As decisões principais foram consolidadas em [research.md](research.md) e resolvem os pontos de incerteza sobre:
- threshold inclusivo e cálculo do progresso;
- filtro de Lessons ativas e exclusão lógica;
- seleção do próximo Step dentro da mesma Track;
- tarefa assíncrona com idempotência e retry controlado;
- transação atômica e rollback em falha; e
- observabilidade sem expor credenciais.

## Phase 1: Design Outputs

- [data-model.md](data-model.md): entidades, validações e relacionamento de contexto de geração.
- [contracts/incremental-step-content.md](contracts/incremental-step-content.md): contrato interno da task assíncrona.
- [quickstart.md](quickstart.md): cenários executáveis de validação para progress threshold, geração, idempotência e retry.

## Constitution Check (pós-design): PASS

O design preserva a separação de camadas, usa persistência e transações conforme as convenções do backend, mantém a API pública inalterada e adiciona cobertura de testes para o comportamento crítico: threshold, concorrência, rollback e retry. Não há violação a registrar em Complexity Tracking.
