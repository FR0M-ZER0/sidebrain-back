# Implementation Plan: Consistência e Estratégia Síncrona de XP e Ranking (SDB-105)

**Branch**: `feat/sdb-105-adiciona-filas-gerenciar-xp-ranking` | **Date**: 2026-11-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/SDB-105-xp-ranking-consistency/spec.md`

## Summary

Validar, consolidar com testes de integração HTTP ponta a ponta e documentar formalmente a estratégia síncrona de cálculo de XP e ranking mantendo `MissionProgress` (com missões ativas) como fonte única de verdade compartilhada entre perfil (`UserService`) e ranking (`RankingService`) via `RankingRepository`. Conforme decisão arquitetural explícita da `SDB-105`, **nenhuma fila, worker Celery, dependência de RabbitMQ, coluna de contador de XP ou materialized view será introduzida nesta etapa**; as entregas consistem em (1) suíte de integração HTTP ponta a ponta comprovando visibilidade imediata pós-commit, consistência entre `/users/me`, `/rankings` e `/rankings/me`, idempotência no recálculo/resubmissão e comportamento diante de exclusões lógicas, e (2) documentação da fórmula oficial de XP, da decisão síncrona e dos critérios de reavaliação no `README.md` e em docstrings concisas dos módulos do fluxo.

## Technical Context

**Language/Version**: Python 3.11+ (`3.11.16` no `.venv` local, `pyproject.toml` `requires-python = ">=3.11"`)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.0 (`AsyncSession`), `uv` (sem inclusão de novas dependências; Celery/Redis já existentes no projeto não são usados para XP/ranking)

**Storage**: PostgreSQL 16 (`pgvector/pgvector:pg16` nos testes); leitura agregada sob demanda sobre `user`, `mission` e `mission_progress` existentes (nenhuma migração Alembic ou alteração de schema)

**Testing**: Pytest (`tests/integration`, `tests/contract`, `tests/unit`) + Ruff (`ruff check .`, `ruff format --check .`)

**Target Platform**: Serviço web FastAPI em container Linux e ambiente local Windows/Linux via `uv`

**Project Type**: Web service / REST API

**Performance Goals**: Preservar orçamento constante de consultas SQL nas leituras de ranking (2 queries na listagem paginada e 1 query na consulta individual) sem N+1 e sem adicionar novo benchmark de carga nesta issue

**Constraints**: Proibido adicionar filas, workers assíncronos, barramento de eventos, RabbitMQ, contadores persistidos de XP ou projeções materializadas; manter contratos HTTP e regras de conclusão/desempate inalterados; documentação obrigatória no `README.md` e em docstrings concisas do fluxo

**Scale/Scope**: Sem novos endpoints ou alterações de regra de negócio; alteração focal em documentação (`README.md`), docstrings em até 5 arquivos existentes do fluxo (`ranking_repository.py`, `ranking_service.py`, `user_service.py`, `quiz_service.py`, `mission_progress_service.py`) e cobertura de integração HTTP ponta a ponta em `tests/integration/test_xp_ranking_consistency.py`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Qualidade de Código e Clean Code**: PASS — Nenhuma lógica duplicada de cálculo de XP será criada; `UserService` e `RankingService` continuam compartilhando `RankingRepository._ranking_summary()`. Docstrings serão concisas e testes seguirão as fixtures compartilhadas de `tests/conftest.py`.
- **II. Responsabilidade Única e Coesão**: PASS — As responsabilidades existentes em `routers`, `services` (`QuizService`, `MissionProgressService`, `RankingService`, `UserService`) e `repositories` (`RankingRepository`) permanecem intactas e coesas.
- **III. Separação Clara de Camadas**: PASS — O fluxo preserva `routers -> services -> repositories -> models` e injeção via `Depends`, sem introduzir `tasks/` para XP ou ranking.
- **IV. Testes e Contratos Verificáveis**: PASS — Adiciona teste de integração HTTP ponta a ponta validando os contratos reais de conclusão de missão, perfil, ranking geral/individual, recálculo idempotente, rollback em falha e exclusão lógica, mantendo contratos existentes estáveis.
- **V. Simplicidade e Evolução Segura**: PASS — Adere estritamente ao princípio da solução mais simples que satisfaz o requisito, evitando abstrações especulativas (filas/outbox/contadores) até que haja evidência medida de gargalo.

**Resultado pré-pesquisa**: PASS. Nenhuma violação constitucional identificada.

**Reavaliação pós-design**: PASS. Os artefatos `research.md`, `data-model.md`, `contracts/xp-ranking-consistency.md` e `quickstart.md` confirmam zero alterações de schema, zero novas dependências/filas e cobertura integral dos requisitos funcionais e critérios de aceite da `SDB-105`.

## Project Structure

### Documentation (this feature)

```text
specs/SDB-105-xp-ranking-consistency/
├── spec.md                              # Especificação funcional e clarificações (/speckit-specify + /speckit-clarify)
├── plan.md                              # Este plano de implementação (/speckit-plan)
├── research.md                          # Decisões técnicas e alternativas avaliadas (Phase 0)
├── data-model.md                        # Fórmula oficial, projeções e invariantes (Phase 1)
├── quickstart.md                        # Roteiro de validação ponta a ponta (Phase 1)
├── checklists/
│   └── requirements.md                  # Checklist de qualidade da especificação
├── contracts/
│   └── xp-ranking-consistency.md        # Contrato de consistência entre rotas HTTP existentes (Phase 1)
└── tasks.md                             # Tarefas ordenadas (/speckit-tasks - Phase 2)
```

### Source Code (repository root)

```text
README.md                                                    # Atualizar: seção de XP e Ranking (fórmula, decisão síncrona sem filas e critérios de reavaliação)
src/
└── sidebrain_back/
    ├── repositories/
    │   └── ranking_repository.py                            # Atualizar: docstring concisa da fonte única de verdade e fórmula de XP
    └── services/
        ├── mission_progress_service.py                      # Atualizar: docstring concisa da idempotência e commit transacional no recálculo
        ├── quiz_service.py                                  # Atualizar: docstring concisa da consistência síncrona pós-commit (sem fila de XP)
        ├── ranking_service.py                               # Atualizar: docstring concisa da consulta sob demanda sem fila/projeção
        └── user_service.py                                  # Atualizar: docstring concisa do reuso da mesma regra de XP do ranking no perfil

tests/
└── integration/
    ├── test_mission_progress.py                             # Existente (referência, validar execução)
    ├── test_ranking_lifecycle.py                            # Existente (referência, validar execução)
    ├── test_user_profile_read.py                            # Existente (referência, validar execução)
    └── test_xp_ranking_consistency.py                       # Novo: fluxo HTTP completo (conclusão -> perfil + ranking -> idempotência -> soft delete -> rollback)
```

**Structure Decision**: Manter integralmente a estrutura em camadas existente em `src/sidebrain_back/` e `tests/`. Não criar módulos em `tasks/`, novos `models/`, novos `schemas/`, novos `routers/` ou migrações em `migrations/`.

## Complexity Tracking

Nenhuma violação constitucional ou complexidade adicional precisa de justificativa.
