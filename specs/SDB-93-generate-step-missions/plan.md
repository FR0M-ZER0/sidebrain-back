# Implementation Plan: Geração de Missões por IA para Steps

**Branch**: `SDB-93-generate-step-missions` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/SDB-93-generate-step-missions/spec.md`

## Summary

Adicionar solicitação autenticada e assíncrona para gerar missões de um Step sem missões, com consulta de estado protegida por ownership e idempotência enquanto a geração estiver ativa. Persistir o ciclo de vida em registro próprio associado a Step, usuário e ID da task; revalidar autorização/conteúdo no worker; validar toda resposta com um único schema de missão e gravar o lote atomicamente pelo caminho de serviço/repositório de Mission. Aplicar a mesma validação à geração inicial e incremental, preservando seus contratos atuais.

## Technical Context

- **Language/Version**: Python >=3.11
- **Primary Dependencies**: FastAPI, Pydantic 2, SQLAlchemy 2 async, Celery 5.6, Groq
- **Storage**: PostgreSQL via SQLAlchemy AsyncSession e asyncpg
- **Testing**: Pytest, HTTPX e Ruff; suites unitária, de integração e de contrato
- **Target Platform**: API e worker Celery do backend SideBrain
- **Project Type**: Serviço web/API
- **Performance Goals**: Pelo menos 95% das solicitações válidas respondem em até 1 segundo; a requisição não aguarda o provedor de IA
- **Constraints**: Gerar exatamente a quantidade solicitada (1–3) por solicitação; autenticação e ownership ocultados sob 404; saída da IA contém somente cinco campos; transação atômica por lote; erros públicos em Problem Details; não duplicar CRUD de Mission
- **Scale/Scope**: Uma geração sob demanda por Step ativo de cada vez; até três missões por solicitação; escalar conforme infraestrutura existente de API, PostgreSQL e Celery

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio/gate | Avaliação | Evidência / tratamento |
|---|---|---|
| Clean Code e responsabilidade única | PASS | Prompt/validação e regra de domínio ficam em serviços; a task orquestra; repositórios encapsulam acesso aos dados. |
| Separação de camadas | PASS | Fluxo planejado: router → service → repository/model; serviço agenda task; o worker constrói suas dependências fora do ciclo FastAPI. |
| Contratos e testes verificáveis | PASS | O contrato OpenAPI descreve status, autenticação, erros, request e responses; testes cobrem schemas, ownership, concorrência, transação e os fluxos existentes. |
| Evolução segura | PASS | O endpoint é aditivo em `/v1`; os contratos HTTP existentes de geração de Trilha e preparação incremental permanecem estáveis. |
| Simplicidade e uso das abstrações existentes | PASS COM PRÉ-REQUISITO | Reutilizar Mission CRUD e padrões de geração já existentes. A task depende da entrega das camadas de gerenciamento de Mission, atualmente indicada como pré-requisito na especificação. Não duplicar essas camadas. |
| Observabilidade e segurança | PASS | Persistir estado e código de erro sanitizado; autorizar consulta pelo dono; logs estruturados sem prompt ou resposta bruta. |
| Migração e testes de banco | PASS | Um registro persistente de geração requer migração versionada e testes de integração da constraint de ownership/estado e rollback. |

Não há violações constitucionais que precisem ser justificadas.

## Phase 0: Research

Conclusões, referências e alternativas estão em [research.md](research.md). Não restam decisões bloqueantes.

## Phase 1: Design & Contracts

O modelo e estados estão em [data-model.md](data-model.md), as interfaces públicas em [contracts/mission-generation.openapi.yaml](contracts/mission-generation.openapi.yaml) e a validação operacional em [quickstart.md](quickstart.md).

### Constitution Check pós-design

| Gate | Resultado | Verificação do desenho |
|---|---|---|
| Uma responsabilidade por camada | PASS | Router traduz HTTP; service autoriza, deduplica e agenda; worker coordena; gerador valida regras de domínio; repository persiste. |
| Dependências e injeção | PASS | Providers `get_*` permanecem junto a seus serviços/repositórios; task cria dependências com sua própria sessão conforme a arquitetura. |
| Persistência atômica | PASS | Todo lote de missões e a transição para `succeeded` compartilham uma transação; exceção causa rollback do lote. |
| Compatibilidade | PASS | Novo endpoint e consulta de estado são aditivos; endpoints anteriores conservam status e shape. |
| Observabilidade sem vazamento | PASS | Estado de falha contém código estável e logs contêm IDs/categoria, sem payload do provedor. |
| Testes e migração | PASS | Plano de validação inclui testes de contrato, unitários, integração transacional e migração. |

### Project Structure

#### Documentation (this feature)

```text
specs/SDB-93-generate-step-missions/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── mission-generation.openapi.yaml
└── tasks.md
```

#### Source Code (repository root)

```text
src/sidebrain_back/
├── models/
│   └── mission_generation_request_model.py
├── repositories/
│   ├── mission_repository.py                 # prerequisite Mission CRUD; reuse
│   └── mission_generation_request_repository.py
├── routers/v1/
│   └── mission_router.py                     # prerequisite router; add endpoint/status route
├── schemas/
│   ├── generation_schema.py                  # canonical GeneratedMission
│   └── mission_schema.py                     # HTTP request/response schemas
├── services/
│   ├── generation_service.py                 # initial prompt/validated mission
│   ├── mission_generator.py                  # reusable AI generation/domain validation
│   └── mission_service.py                    # prerequisite service; request/status/persistence
└── tasks/
    ├── generate_step_missions_task.py
    └── prepare_next_step_content_task.py     # use canonical validator

migrations/versions/
└── migration for MissionGenerationRequest

tests/
├── contract/
│   └── test_mission_generation_contract.py
├── integration/
│   └── test_mission_generation.py
└── unit/
    ├── test_mission_generation_service.py
    ├── test_mission_generator.py
    └── test_prepare_next_step_content_task.py
```

**Structure Decision**: Serviço FastAPI existente, sem novo projeto. Os diretórios acima são os caminhos planejados para a funcionalidade; arquivos de CRUD de Mission são pré-requisito a reutilizar, não duplicações desta entrega. Manter o router sob `routers/v1` conforme versionamento adotado pelo repositório.

## Complexity Tracking

Sem violações. O registro persistente de geração é a menor extensão que atende simultaneamente consulta de estado, ownership, idempotência em andamento e falhas observáveis sem depender da retenção do backend de resultados Celery.
