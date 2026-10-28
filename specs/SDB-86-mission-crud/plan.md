# Implementation Plan: Gerenciamento de Missões

**Branch**: `feat/sdb-86-cria-endpoints-gerenciar-missoes` | **Date**: 2026-10-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-86-mission-crud/spec.md`

## Summary

Implementar o CRUD de `Mission` como recurso filho de `Step`, preservando a
autorização pela cadeia `Track -> Step -> Mission`, a exclusão lógica e a
composição de progresso do usuário autenticado. A solução adicionará schemas,
repository, service e router próprios, reutilizará o carregamento `selectinload`
já usado na hierarquia de Steps e registrará testes de contrato, unidade e
integração.

## Technical Context

**Language/Version**: Python 3.12 (projeto configurado via `pyproject.toml`)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy async, Alembic

**Storage**: PostgreSQL existente; tabelas `mission`, `mission_progress`,
`step` e `track`, sem nova tabela prevista

**Testing**: Pytest, TestClient para contratos HTTP e fixtures assíncronas para
integração

**Target Platform**: Serviço web FastAPI executado em Linux/container e
desenvolvimento local via `uv`

**Project Type**: Web service/API

**Performance Goals**: Listagens de até 100 missões em até 1 segundo em
condições normais, sem consultas adicionais por missão

**Constraints**: paginação `page=1`, `page_size=20`, máximo 100; respostas sem
nomes físicos; `404` uniforme para recursos inexistentes, deletados ou sem
ownership; `PUT` parcial conforme contrato da task

**Scale/Scope**: Escopo restrito ao CRUD de Mission e à leitura filtrada de
MissionProgress; não inclui CRUD nem mutações de progresso

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Os gates passam:

- **Princípios I e II**: cada camada terá responsabilidade única e seguirá os
  nomes e helpers já usados por Step.
- **Princípio III**: fluxo `router -> service -> repository -> models`, com
  schemas públicos separados dos modelos SQLAlchemy e `Depends` na composição.
- **Princípio IV**: serão incluídos testes de contrato para payload/status,
  unitários para validação/serviço e integração para persistência, soft delete,
  ownership e carregamento agrupado.
- **Princípio V**: `PUT` parcial é mantido por compatibilidade com a task e com
  o padrão de mutação existente; erros usam Problem Details e não haverá
  alteração incompatível nos endpoints existentes.

**Resultado pré-pesquisa**: PASS. Não há violação a justificar.

**Reavaliação pós-design**: PASS. A pesquisa confirmou o uso de
`selectinload` filtrado, a autorização contextual no repository, o `PUT`
parcial exigido pela task e a manutenção das camadas existentes; não há
clarificação pendente nem exceção constitucional.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-86-mission-crud/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── mission-api.md
├── quickstart.md
└── tasks.md
```

### Source Code

```text
src/
└── sidebrain_back/
    ├── models/mission_model.py
    ├── repositories/mission_repository.py
    ├── routers/v1/mission_router.py
    ├── schemas/mission_schema.py
    ├── services/mission_service.py
    ├── schemas/step_schema.py
    ├── repositories/step_repository.py
    └── routers/router.py
tests/
├── contract/test_mission_contract.py
├── integration/test_mission_lifecycle.py
├── unit/test_mission_schema.py
└── unit/test_mission_service.py
```

**Structure Decision**: Manter o monólito modular FastAPI existente. O novo
domínio seguirá os mesmos diretórios de `Step`, e alterações de hierarquia
ficarão em `step_schema.py`/`step_repository.py` apenas quando necessárias para
preservar a resposta existente.

## Complexity Tracking

Nenhuma violação constitucional ou projeto adicional foi identificado.
