---

description: "Lista de tarefas para validação, cobertura de testes e documentação da estratégia síncrona de XP e ranking (SDB-105)"
---

# Tasks: Consistência e Estratégia Síncrona de XP e Ranking (SDB-105)

**Input**: Design documents from `/specs/SDB-105-xp-ranking-consistency/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/xp-ranking-consistency.md`, `quickstart.md`

**Tests**: Incluídos conforme exigido em `spec.md` (`FR-010`, `SC-005`), `plan.md` e na constituição do projeto (`constitution.md`), cobrindo fluxo HTTP ponta a ponta em PostgreSQL real, idempotência, exclusões lógicas e consistência entre perfil e ranking.

**Organization**: As tarefas estão organizadas por história de usuário para permitir implementação, teste e validação independentes de cada incremento, respeitando rigorosamente a restrição de **zero filas, workers ou contadores persistidos** para XP/ranking.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo (arquivos diferentes, sem dependências em tarefas incompletas)
- **[Story]**: História de usuário à qual a tarefa pertence (`US1`, `US2`, `US3`, `US4`)
- Caminhos exatos de arquivos incluídos em todas as descrições

## Path Conventions

- **Código-fonte da aplicação**: `src/sidebrain_back/`
- **Suíte de testes**: `tests/integration/`, `tests/contract/`, `tests/unit/`
- **Documentação**: `README.md` e `specs/SDB-105-xp-ranking-consistency/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Auditar os fluxos síncronos já existentes no código e estruturar o arquivo de testes de integração HTTP ponta a ponta sem alterar schema de banco nem criar filas.

- [X] T001 Auditar o fluxo síncrono existente entre conclusão de missão, perfil e ranking em `src/sidebrain_back/repositories/ranking_repository.py`, `src/sidebrain_back/services/ranking_service.py`, `src/sidebrain_back/services/user_service.py`, `src/sidebrain_back/services/quiz_service.py`, `src/sidebrain_back/services/mission_progress_service.py` e `src/sidebrain_back/tasks/`, confirmando ausência de filas de XP/ranking e que nenhuma migração Alembic será criada
- [X] T002 [P] Criar o esqueleto inicial e helpers/fixtures autenticadas HTTP (reaproveitando `test_app`, `db_session`, `learning_hierarchy_factory`, `mission_factory`, `quiz_factory`, `user_factory` e `mission_progress_factory` de `tests/conftest.py`, com stubs apenas em `QuizEvaluationService.evaluate` e `TrackService.enqueue_next_step_preparation`, sem mockar cálculo de XP ou ranking) em `tests/integration/test_xp_ranking_consistency.py`

**Checkpoint**: Escopo auditado e estrutura base de testes HTTP pronta.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Garantir ambiente de testes funcional e confirmar integridade da baseline existente antes de adicionar novos testes e documentação.

**⚠️ CRITICAL**: Nenhuma validação das histórias de usuário deve prosseguir sem o PostgreSQL de testes ativo e a baseline passando.

- [ ] T003 Subir o banco de testes (`docker compose --profile test up -d --wait postgres_test`) e executar a baseline existente em `tests/integration/test_ranking_lifecycle.py`, `tests/integration/test_mission_progress.py`, `tests/integration/test_user_profile_read.py` e `tests/contract/test_ranking_contract.py` *(Pendente de ambiente: sem Docker/PostgreSQL local e `.env` requer atualização conforme `.env.example`)*
- [X] T004 Confirmar no código existente que as invariantes de `data-model.md` permanecem íntegras sem necessidade de alteração lógica: `xp = COALESCE(SUM(Mission.msn_xp_reward), 0)`, `missionsCompleted = COUNT(Mission.msn_id)`, filtros `usr_is_deleted = False`, `mpg_status = DONE` e `msn_is_deleted = False` (sem filtrar `Step`/`Track` pai), ordenação `xp DESC, usr_created_at ASC, usr_id ASC` e guarda idempotente de `DONE` em `src/sidebrain_back/repositories/ranking_repository.py` e `src/sidebrain_back/services/mission_progress_service.py`

**Checkpoint**: Baseline verde e invariantes verificadas — implementação dos cenários por história liberada.

---

## Phase 3: User Story 1 - Refletir XP e posição imediatamente após concluir uma missão (Priority: P1) 🎯 MVP

**Goal**: Comprovar ponta a ponta que a conclusão de uma missão via submissão de resposta de quiz é persistida sincronamente antes da resposta HTTP e refletida imediatamente em `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me` sem depender de worker ou fila.

**Independent Test**: Submeter resposta via `POST /api/v1/quizzes/{quiz_id}/answers` (`201`), chamar `db_session.expire_all()` e consultar imediatamente `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me`, validando a atualização instantânea de `xp`, `missionsCompleted` e `position`.

### Tests for User Story 1

- [X] T005 [US1] Implementar teste de integração HTTP de atualização imediata pós-commit (`POST /api/v1/quizzes/{quiz_id}/answers` → `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me`, com `db_session.expire_all()` e múltiplos usuários para comprovar mudança imediata de `position`, `xp` e `missionsCompleted` sem worker/fila) em `tests/integration/test_xp_ranking_consistency.py`
- [X] T006 [US1] Implementar teste de integração HTTP de atomicidade em falha e submissão parcial (resposta que ainda não conclui a missão e falha com rollback antes do `commit` mantendo `xp`, `missionsCompleted` e `position` inalterados) em `tests/integration/test_xp_ranking_consistency.py`

### Documentation for User Story 1

- [X] T007 [P] [US1] Adicionar docstrings concisas registrando a atualização síncrona e atômica na mesma transação pós-commit (sem envio de XP/ranking para fila) em `QuizService.submit_quiz_answer` (`src/sidebrain_back/services/quiz_service.py`) e `MissionProgressService.recalculate_missions_by_step_id` (`src/sidebrain_back/services/mission_progress_service.py`)

**Checkpoint**: User Story 1 validada de forma independente — MVP comprova consistência síncrona pós-commit sem fila.

---

## Phase 4: User Story 2 - Garantir regra única entre perfil do usuário e ranking (Priority: P1)

**Goal**: Comprovar que `GET /api/v1/users/me`, `PUT /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me` compartilham exatamente a mesma regra derivada de XP e missões concluídas em todos os cenários (0 XP, progresso em andamento e múltiplas missões concluídas).

**Independent Test**: Consultar `GET /api/v1/users/me`, `PUT /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me` sobre o mesmo conjunto de usuários e missões em estados `idle`, `in_progress` e `done`, confirmando valores idênticos de `xp`, `missionsCompleted` e `position`.

### Tests for User Story 2

- [X] T008 [US2] Implementar teste de integração HTTP de consistência estrita entre perfil e ranking (`GET /api/v1/users/me`, `PUT /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me`, cobrindo usuários com 0 XP, missões `idle`/`in_progress` e múltiplas missões `done`, além da preservação de quantidade constante de queries em `tests/integration/test_ranking_lifecycle.py`) em `tests/integration/test_xp_ranking_consistency.py`

### Documentation for User Story 2

- [X] T009 [P] [US2] Adicionar docstrings concisas documentando a fonte única de verdade derivada (fórmula `xp = COALESCE(SUM(msn_xp_reward), 0)` / `missionsCompleted = COUNT(msn_id)` sem contador persistido nem projeção materializada) em `RankingRepository._ranking_summary` (`src/sidebrain_back/repositories/ranking_repository.py`), `RankingService` (`src/sidebrain_back/services/ranking_service.py`) e `UserService._build_user_me_response` (`src/sidebrain_back/services/user_service.py`)

**Checkpoint**: User Story 2 validada — igualdade estrita entre perfil e ranking comprovada e documentada nos serviços/repositório.

---

## Phase 5: User Story 3 - Assegurar idempotência no recálculo e exclusão de missões removidas (Priority: P2)

**Goal**: Comprovar que recálculos e submissões repetidas sobre missões já concluídas são idempotentes e que missões excluídas logicamente deixam de somar XP imediatamente (enquanto exclusão lógica apenas de `Step` ou `Track` pai preserva o XP de missões ativas concluídas, alinhado à `SDB-90`).

**Independent Test**: Executar múltiplas vezes `POST /api/v1/steps/{step_id}/missions/recalculate-progress` e novas submissões em `POST /api/v1/quizzes/{quiz_id}/answers` confirmando XP constante; excluir missão via `DELETE /api/v1/missions/{mission_id}` confirmando redução imediata para `0` (ou soma restante) e ajuste de `position`; e excluir apenas `Step`/`Track` pai confirmando preservação de XP de missão ativa.

### Tests for User Story 3

- [X] T010 [US3] Implementar teste de integração HTTP de idempotência (`POST /api/v1/steps/{step_id}/missions/recalculate-progress` repetido + nova submissão em `POST /api/v1/quizzes/{quiz_id}/answers` após missão já `done`, validando `xp` e `missionsCompleted` constantes em `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me`) em `tests/integration/test_xp_ranking_consistency.py`
- [X] T011 [US3] Implementar testes de integração HTTP de exclusão lógica em `tests/integration/test_xp_ranking_consistency.py`: (1) `DELETE /api/v1/missions/{mission_id}` (`204`) removendo imediatamente XP/contagem e ajustando `position` (incluindo retorno a `0 XP` quando todas as missões concluídas são removidas) e (2) exclusão lógica de `Step` (`DELETE /api/v1/tracks/{track_id}/steps/{step_id}`) e `Track` (`DELETE /api/v1/tracks/{track_id}`) mantendo o XP da missão ativa concluída, alinhado à `SDB-90`

### Documentation for User Story 3

- [ ] T012 [P] [US3] Refinar a docstring concisa de `MissionProgressService.update_missions_by_track_id` em `src/sidebrain_back/services/mission_progress_service.py` explicitando a guarda idempotente de progresso `DONE` e executar `uv run --no-sync pytest tests/integration/test_xp_ranking_consistency.py` para validar todos os cenários das histórias US1–US3 *(Docstring aplicada; execução do `pytest` pendente de PostgreSQL + `.env`)*

**Checkpoint**: User Stories 1, 2 e 3 integradas, isoladamente testáveis e passando em PostgreSQL real.

---

## Phase 6: User Story 4 - Formalizar a decisão síncrona sem filas e critérios de reavaliação (Priority: P2)

**Goal**: Documentar no `README.md` (junto às demais seções de fluxo/rotas do sistema) a fórmula oficial de XP, a decisão arquitetural síncrona sem filas/contadores e os critérios objetivos para eventual reavaliação futura, mantendo total coerência com as docstrings do código.

**Independent Test**: Ler a seção de XP e Ranking no `README.md` e as docstrings dos cinco arquivos do fluxo, confirmando presença da fórmula de XP, consistência imediata pós-commit entre perfil e ranking, exclusão de filas/workers/contadores redundantes e pré-requisitos mensuráveis para reavaliação futura.

- [X] T013 [US4] Adicionar a seção `## XP e Ranking` em `README.md` documentando: fórmula oficial (`xp = soma de msn_xp_reward` e `missionsCompleted = contagem` de missões ativas com `MissionProgress.status == done` para usuários ativos, preservando XP se apenas `Step`/`Track` pai for excluído), atualização síncrona pós-commit entre `POST /api/v1/quizzes/{quiz_id}/answers`, `GET /api/v1/users/me`, `GET /api/v1/rankings` e `GET /api/v1/rankings/me`, justificativa da não introdução de filas/workers/contadores redundantes e critérios objetivos de reavaliação futura (evidência de gargalo medida, SLA de atraso aceitável, publicação transacional/outbox, idempotência, ordenação/concorrência e reconciliação)
- [X] T014 [US4] Revisar e alinhar `README.md` e as docstrings em `src/sidebrain_back/repositories/ranking_repository.py`, `src/sidebrain_back/services/ranking_service.py`, `src/sidebrain_back/services/user_service.py`, `src/sidebrain_back/services/quiz_service.py` e `src/sidebrain_back/services/mission_progress_service.py` para garantir consistência terminológica e aderência integral à `spec.md`

**Checkpoint**: User Story 4 concluída — documentação oficial e docstrings alinhadas à decisão arquitetural da `SDB-105`.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validar a restrição negativa (nenhuma fila/dependência de XP adicionada) e executar toda a suíte de lint, formatação e testes do projeto conforme `quickstart.md`.

- [X] T015 Auditar `git status`, `git diff`, `pyproject.toml` e `src/sidebrain_back/tasks/` para confirmar que nenhuma fila, task Celery de XP/ranking, dependência de RabbitMQ ou migração/coluna persistida de XP foi adicionada
- [ ] T016 Executar a validação completa descrita em `specs/SDB-105-xp-ranking-consistency/quickstart.md` (`uv run --no-sync ruff check .`, `uv run --no-sync ruff format --check .`, `uv run --no-sync pytest tests/integration/test_xp_ranking_consistency.py tests/integration/test_ranking_lifecycle.py tests/integration/test_mission_progress.py tests/integration/test_user_profile_read.py` e `uv run --no-sync pytest`) confirmando 100% de aprovação *(`ruff check .` e `ruff format --check .` aprovados após edição final; execução do `pytest` pendente de PostgreSQL + `.env`)*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — iniciar imediatamente (`T001`, `T002`).
- **Foundational (Phase 2)**: Depende da conclusão da Phase 1 — bloqueia a validação das histórias (`T003`, `T004`).
- **User Story 1 (Phase 3 - P1)**: Depende da Phase 2 (`T005`, `T006`, `T007`) — constitui o **MVP**.
- **User Story 2 (Phase 4 - P1)**: Depende da Phase 2 (`T008`, `T009`); como `T008` edita `tests/integration/test_xp_ranking_consistency.py`, executar após `T006` (ou coordenar edições sequenciais no mesmo arquivo), enquanto `T009` pode rodar em paralelo.
- **User Story 3 (Phase 5 - P2)**: Depende da Phase 2 (`T010`, `T011`, `T012`); `T010` e `T011` compartilham `tests/integration/test_xp_ranking_consistency.py`, enquanto `T012` atualiza `mission_progress_service.py` e executa a suíte.
- **User Story 4 (Phase 6 - P2)**: Depende das docstrings de `T007`, `T009` e `T012` para a revisão final em `T014`; `T013` (`README.md`) pode começar após a Phase 2.
- **Polish (Phase 7)**: Depende da conclusão de todas as fases anteriores (`T015`, `T016`).

### User Story Dependencies

- **US1 (P1)**: Independente após Foundational.
- **US2 (P1)**: Independente após Foundational (compartilha apenas o arquivo de testes `tests/integration/test_xp_ranking_consistency.py` com US1).
- **US3 (P2)**: Independente após Foundational (compartilha apenas o arquivo de testes `tests/integration/test_xp_ranking_consistency.py` com US1/US2).
- **US4 (P2)**: Depende da consolidação das docstrings de US1–US3 apenas para a revisão cruzada final (`T014`).

### Parallel Opportunities

- **Phase 1**: `T001` (auditoria de código) e `T002` (esqueleto do arquivo de testes) em paralelo.
- **Phase 3 (US1)**: `T007` (docstrings em `quiz_service.py` e `mission_progress_service.py`) em paralelo com `T005`/`T006` (`test_xp_ranking_consistency.py`).
- **Phase 4 (US2)**: `T009` (docstrings em `ranking_repository.py`, `ranking_service.py`, `user_service.py`) em paralelo com `T008` (`test_xp_ranking_consistency.py`).
- **Phase 5 (US3)**: `T012` (refinamento em `mission_progress_service.py`, antes da execução final da suíte) pode ser preparado em paralelo às alterações em `test_xp_ranking_consistency.py`.
- **Phase 6 (US4)**: `T013` (`README.md`) pode ser redigido em paralelo aos testes de US2/US3.

---

## Parallel Example: User Story 1 & User Story 2

```text
# Em paralelo (arquivos distintos após Phase 2):
Task T005: "Implementar fluxo HTTP ponta a ponta de atualização imediata pós-commit em tests/integration/test_xp_ranking_consistency.py"
Task T007: "Adicionar docstrings síncronas em src/sidebrain_back/services/quiz_service.py e src/sidebrain_back/services/mission_progress_service.py"
Task T009: "Adicionar docstrings de fonte única de verdade em src/sidebrain_back/repositories/ranking_repository.py, src/sidebrain_back/services/ranking_service.py e src/sidebrain_back/services/user_service.py"
Task T013: "Adicionar seção ## XP e Ranking em README.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Concluir Phase 1 (`T001`–`T002`) e Phase 2 (`T003`–`T004`).
2. Concluir Phase 3 (`T005`–`T007` — User Story 1).
3. **STOP and VALIDATE**: Rodar `uv run --no-sync pytest tests/integration/test_xp_ranking_consistency.py` para comprovar atualização imediata pós-commit de perfil e ranking sem fila.

### Incremental Delivery

1. Setup + Foundational → baseline verde confirmada.
2. US1 (P1) → conclusão síncrona pós-commit comprovada ponta a ponta.
3. US2 (P1) → igualdade estrita entre perfil, ranking geral e posição individual comprovada e documentada nos serviços.
4. US3 (P2) → idempotência no recálculo e exclusões lógicas (`Mission` vs. `Step`/`Track`) comprovadas.
5. US4 (P2) → `README.md` atualizado e docstrings revisadas em alinhamento completo.
6. Polish → auditoria de zero filas + `ruff check .` + `ruff format --check .` + suíte completa `pytest`.

