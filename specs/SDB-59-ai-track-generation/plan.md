# Implementation Plan: Geração de Trilhas com IA

**Branch**: `SDB-59-ai-track-generation` | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/SDB-59-ai-track-generation/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Executar uma task Celery idempotente que envia o contexto de aprendizagem ao
cliente Groq, valida uma resposta estruturada completa e persiste, em uma única
transação, a trilha com todas as etapas e o conteúdo detalhado somente da
primeira etapa. A task usará schemas internos Pydantic, um serviço para
orquestração e um repositório para montar a hierarquia ORM; falhas transitórias
do provedor terão até três tentativas e falhas de validação ou persistência não
deixarão registros parciais.

## Technical Context

**Language/Version**: Python >= 3.11

**Primary Dependencies**: Celery 5.6, Groq SDK 1.7, Pydantic 2.11, SQLAlchemy 2.0, asyncpg, PostgreSQL

**Storage**: PostgreSQL via SQLAlchemy AsyncSession; Alembic para migration do identificador idempotente

**Testing**: pytest (unitário, integração e contrato), ruff

**Target Platform**: Worker Celery em servidor Linux, com Redis como broker/backend

**Project Type**: Serviço web FastAPI com processamento assíncrono de domínio

**Performance Goals**: A solicitação não bloqueia a API; uma geração usa uma chamada ao provedor e uma transação de persistência, sem gerar conteúdo futuro antecipadamente

**Constraints**: máximo de 3 tentativas para falhas transitórias; validação completa antes do primeiro flush persistente; rollback integral em qualquer falha; sem endpoint novo

**Scale/Scope**: Uma trilha por solicitação idempotente; etapas futuras somente como estrutura; sem respostas, feedbacks, progresso de missão ou arquivos de lição

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Resultado | Evidência |
|---|---|---|
| I. Qualidade e Clean Code | PASS | Schemas, task, serviço e repositório terão responsabilidades separadas e nomes semânticos. |
| II. Responsabilidade única | PASS | IA, validação, orquestração e persistência serão componentes distintos. |
| III. Camadas | PASS | A task usará o serviço; o serviço usará o repositório; nenhum router novo será criado. |
| IV. Testes e contratos | PASS | Serão previstos testes unitários para validação/retry/idempotência e integração para transação e hierarquia. |
| V. Simplicidade e evolução segura | PASS | Reutiliza Celery, Groq, modelos e sessão existentes; a nova coluna de idempotência terá migration reversível. |

## Project Structure

### Documentation (this feature)

```text
specs/SDB-59-ai-track-generation/
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
│   ├── core/                 # cliente Groq, sessão e Celery existentes
│   ├── models/               # Track, Step, Lesson, Quiz e Mission existentes
│   ├── repositories/         # persistência da geração
│   ├── schemas/              # schemas internos de entrada/saída da IA
│   ├── services/             # orquestração da geração
│   └── tasks/                # task Celery da geração
├── migrations/versions/      # coluna de idempotência da solicitação

tests/
├── contract/
├── integration/
└── unit/

```

**Structure Decision**: Manter a organização em camadas existente. A geração
assíncrona entra em `tasks/`, o contrato interno em `schemas/`, a regra de
orquestração em `services/` e a gravação em `repositories/`. Nenhum endpoint ou
router será adicionado, conforme FR-015.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nenhuma | N/A | O desenho segue os limites existentes e não cria projeto ou camada adicional. |

## Constitution Check (pós-design)

**Resultado: PASS.** O desenho mantém a direção `tasks/services/repositories/models`,
usa schemas Pydantic sem expor IDs físicos, prevê testes unitários e de integração,
e inclui migration reversível para a chave de idempotência. Não há endpoint novo,
nem violação não justificada da constituição.
