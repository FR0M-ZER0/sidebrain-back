# Implementation Plan: Avaliacao de Conhecimento para Trilhas

**Branch**: `SDB-53-knowledge-assessment` | **Date**: 2026-09-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/SDB-53-knowledge-assessment/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A feature prepara uma avaliacao inicial de conhecimento antes da criacao de uma
trilha. O fluxo sera executado por uma task Celery que recebe o contexto do
chamador, retorna imediatamente um resultado `skipped` com nivel `beginner`
quando solicitado, ou delega a geracao ao adapter Groq. Schemas Pydantic
validarao o resultado completo antes da disponibilizacao, exigindo exatamente
cinco perguntas estruturadas. O resultado permanecera transitorio no backend de
resultados do Celery; nao havera endpoint, persistencia ou alteracao de
entidades de trilha nesta feature.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python >= 3.11

**Primary Dependencies**: Celery 5.6, Pydantic 2, Groq Python SDK 1.7, Redis

**Storage**: N/A para dominio; resultado transitorio no backend Redis do Celery

**Testing**: Pytest com fakes do service/provider e testes da task em modo eager

**Target Platform**: Worker Celery em servidor Linux/containerizado

**Project Type**: Servico web FastAPI com processamento assincrono Celery

**Performance Goals**: 95% das avaliacoes validas concluidas em ate 30 segundos,
excluindo indisponibilidade externa com retry

**Constraints**: Cinco perguntas exatas; sem resultado parcial; timeout de 30s
por chamada ao provider; no maximo 3 retries com backoff; sem logs de prompt,
resposta, credenciais ou contexto textual completo

**Scale/Scope**: Uma task, um service, um adapter e schemas/testes associados;
sem endpoint, migration, model, repository ou classificacao definitiva de nivel

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidencia |
|------|--------|-----------|
| I. Qualidade de codigo e Clean Code | PASS | Responsabilidades separadas entre schemas, service, adapter e task; nomes explicitos e testes isolados. |
| II. Responsabilidade unica e coesao | PASS | O service decide skip/validacao, o adapter chama Groq e a task orquestra retry/serializacao. |
| III. Separacao clara de camadas | PASS | Nao ha endpoint; a task nao acessa models/repositories e o provider fica fora da regra de negocio. |
| IV. Testes e contratos verificaveis | PASS | Testes unitarios cobrem regras e falhas; contrato de resultado e quickstart documentam o consumo. |
| V. Simplicidade e evolucao segura | PASS | Sem persistencia ou endpoint especulativo; resultado versionavel por schemas e backend Celery existente. |
| Padroes tecnicos do projeto | PASS | Python, Pydantic, Celery, Groq, Pytest e uv ja sao dependencias/padroes do repositorio. |
| Fluxo de desenvolvimento e gates | PASS | Plano preve `uv run ruff check .` e `uv run pytest`, alem de testes especificos da task. |

Nao ha violacoes que exijam registro em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-53-knowledge-assessment/
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
  │   ├── celery_app.py
  │   └── groq_client.py
  ├── schemas/
  │   └── knowledge_assessment_schema.py
  ├── services/
  │   ├── knowledge_assessment_generator.py
  │   └── knowledge_assessment_service.py
  └── tasks/
    ├── __init__.py
    └── knowledge_assessment_task.py

tests/
├── contract/
│   └── test_knowledge_assessment_contract.py
├── integration/
│   └── test_knowledge_assessment_task.py
└── unit/
  ├── test_knowledge_assessment_schema.py
  └── test_knowledge_assessment_service.py
```

**Structure Decision**: Manter o projeto unico existente. Schemas ficam em
`src/sidebrain_back/schemas`, regras em `services`, integracao com Groq em
adapter dedicado e orquestracao Celery em `tasks`; os testes seguem as tres
camadas ja usadas no repositorio. Nenhum model, repository ou migration sera
criado porque o resultado e transitorio.

## Constitution Check Post-Design

*GATE: aprovado apos a geracao de research.md, data-model.md, contratos e quickstart.md.*

- **Separacao de responsabilidades:** PASS. O modelo nao introduz persistencia;
  a task orquestra, o service decide e valida, e o adapter encapsula o Groq.
- **Contratos e testes:** PASS. O contrato documenta entrada e dois estados de
  saida; o quickstart aponta testes unitarios, de integracao e de contrato.
- **Observabilidade e evolucao segura:** PASS. Retry e falha definitiva sao
  distintos, sem dados sensiveis nos logs; nao ha mudanca de API existente.
- **Escopo:** PASS. A classificacao definitiva, respostas do usuario e
  criacao da trilha permanecem explicitamente fora desta feature.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
