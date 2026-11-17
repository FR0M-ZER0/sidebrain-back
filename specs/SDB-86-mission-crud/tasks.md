---
description: "Tarefas de implementação do CRUD de Mission"
---

# Tasks: Gerenciamento de Missões

**Input**: Design documents from `/specs/SDB-86-mission-crud/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/mission-api.md](./contracts/mission-api.md) e
[quickstart.md](./quickstart.md)

**Organization**: As tarefas estão agrupadas por história de usuário. Os
testes são obrigatórios pela constituição do projeto e devem ser escritos antes
da implementação de cada incremento.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar o escopo de trabalho sem criar novas dependências ou
alterar o schema do banco, pois `Mission` e `MissionProgress` já existem.

- [X] T001 Confirmar a branch `feat/sdb-86-cria-endpoints-gerenciar-missoes` e revisar os artefatos de design em `specs/SDB-86-mission-crud/plan.md`, `specs/SDB-86-mission-crud/spec.md` e `specs/SDB-86-mission-crud/contracts/mission-api.md`
- [X] T002 [P] Mapear fixtures, autenticação e convenções de teste existentes para reutilização em `tests/conftest.py`, `tests/contract/` e `tests/integration/`
- [X] T003 [P] Confirmar que os enums e modelos persistidos necessários estão disponíveis em `src/sidebrain_back/enums/mission_difficulty_enum.py`, `src/sidebrain_back/enums/mission_criteria_enum.py`, `src/sidebrain_back/models/mission_model.py` e `src/sidebrain_back/models/mission_progress_model.py`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fixar os pontos de integração compartilhados antes das histórias,
sem alterar comportamento de endpoints existentes.

- [X] T004 Documentar a matriz de rotas, respostas e erros Problem Details em `specs/SDB-86-mission-crud/contracts/mission-api.md`, preservando `PUT` parcial e os nomes semânticos camelCase
- [X] T005 [P] Definir a estratégia de consulta contextual `user -> Track -> Step -> Mission` e carregamento filtrado de `MissionProgress` em `src/sidebrain_back/repositories/mission_repository.py`
- [ ] T006 [P] Preparar casos compartilhados de usuário autenticado, ownership, soft delete e progresso filtrado em `tests/conftest.py` ou fixtures específicas sob `tests/`

**Checkpoint**: Fundação pronta; as histórias podem ser implementadas em
sequência de prioridade ou em paralelo quando não houver conflito de arquivos.

## Phase 3: User Story 1 - Gerenciar missões de um step (Priority: P1) 🎯 MVP

**Goal**: Entregar o ciclo completo de criação, listagem, consulta, atualização
parcial e exclusão lógica de Mission para Steps autorizados.

**Independent Test**: Com um Track e um Step ativos pertencentes ao usuário,
executar `POST -> GET lista -> GET detalhe -> PUT -> DELETE` e confirmar
paginação, resposta sem nomes físicos, preservação de campos omitidos e
desaparecimento após soft delete, sem depender de CRUD de progresso.

### Tests for User Story 1

- [X] T007 [P] [US1] Criar testes de schema para payloads `MissionCreate` e `MissionUpdate` em `tests/unit/test_mission_schema.py`, cobrindo título de 1–255 caracteres após trim, título apenas com espaços, enums conhecidos, `xpReward` não negativo, `criteriaValue` positivo, campos extras e atualização vazia
- [X] T008 [P] [US1] Criar testes de contrato HTTP em `tests/contract/test_mission_contract.py` para autenticação, `POST /api/v1/steps/{step_id}/missions`, `GET` paginado, `GET /api/v1/missions/{mission_id}`, `PUT` parcial e `DELETE 204`
- [X] T009 [P] [US1] Criar teste de integração do ciclo de vida em `tests/integration/test_mission_lifecycle.py`, verificando criação, listagem vazia/paginada, consulta, atualização parcial, soft delete e retenção do registro

### Implementation for User Story 1

- [X] T010 [P] [US1] Criar schemas públicos `MissionCreate`, `MissionUpdate`, `MissionProgressResponse` e `MissionResponse` em `src/sidebrain_back/schemas/mission_schema.py`, usando `from_attributes=True`, `populate_by_name=True`, aliases `id`, `stepId`, `xpReward`, `criteriaValue` e `missionProgresses`, e sem aceitar `stepId` no body
- [X] T011 [US1] Implementar `MissionRepository` e `get_mission_repository` em `src/sidebrain_back/repositories/mission_repository.py`, com `create`, `list`, `get`, `update` e `soft_delete`, filtros de missão/step/track ativos e `selectinload` agrupado de progressos por `mpg_user_id`
- [X] T012 [US1] Implementar `MissionService` e `get_mission_service` em `src/sidebrain_back/services/mission_service.py`, mantendo regras fora do HTTP, convertendo entidades para schemas, aplicando commit/rollback e retornando `404` uniforme para recursos inacessíveis
- [X] T013 [US1] Implementar as rotas autenticadas em `src/sidebrain_back/routers/v1/mission_router.py` para `POST /steps/{step_id}/missions`, `GET /steps/{step_id}/missions`, `GET /missions/{mission_id}`, `PUT /missions/{mission_id}` e `DELETE /missions/{mission_id}`, com paginação `page=1`, `page_size=20`, máximo 100 e status `201`/`200`/`204`
- [X] T014 [US1] Registrar o router de Mission em `src/sidebrain_back/routers/router.py` e alinhar os imports públicos necessários em `src/sidebrain_back/schemas/__init__.py`, `src/sidebrain_back/repositories/__init__.py` e `src/sidebrain_back/services/__init__.py` apenas se esses módulos expuserem exports
- [X] T015 [US1] Completar os testes unitários de serviço em `tests/unit/test_mission_service.py`, cobrindo mapeamento de resposta, validação de Step, atualização sem alteração de Step, exclusão lógica, commit e rollback

**Checkpoint**: O MVP deve passar os testes de schema, contrato e ciclo de vida
da Mission isoladamente.

## Phase 4: User Story 3 - Proteger o acesso às missões (Priority: P1)

**Goal**: Garantir que Steps e Missions inexistentes, excluídos ou pertencentes
a outro usuário sejam indistinguíveis e nunca sejam revelados ou alterados.

**Independent Test**: Repetir criação, listagem, consulta, atualização e
exclusão usando Step/Mission de outro usuário, recurso soft-deleted ou UUID
inexistente; todas as operações devem retornar `404` uniforme, enquanto payloads
inválidos retornam `422` sem persistência parcial.

### Tests for User Story 3

- [ ] T016 [P] [US3] Adicionar casos de contrato de autorização em `tests/contract/test_mission_contract.py`, verificando `404` uniforme para Step/Mission inexistente, excluído ou de outro usuário e ausência de colunas físicas na resposta
- [ ] T017 [P] [US3] Adicionar casos de integração de isolamento em `tests/integration/test_mission_lifecycle.py`, verificando que usuário diferente não lê, atualiza, lista ou exclui a Mission e que payload inválido não cria dados
- [ ] T018 [P] [US3] Adicionar testes unitários de consultas contextualizadas em `tests/unit/test_mission_service.py` ou `tests/unit/test_mission_repository.py`, confirmando filtros de ownership, soft delete e progressos de outro usuário

### Implementation for User Story 3

- [X] T019 [US3] Fortalecer as consultas e mutações contextualizadas em `src/sidebrain_back/repositories/mission_repository.py`, aplicando na mesma operação os filtros `Track.trk_user_id`, `Track.trk_is_deleted`, `Step.stp_is_deleted`, `Mission.msn_is_deleted` e o vínculo correto entre IDs
- [X] T020 [US3] Garantir em `src/sidebrain_back/services/mission_service.py` que falhas de autorização, inexistência e estado excluído produzam o mesmo `ProblemDetailError(404, ...)`, sem detalhes que distingam a causa
- [X] T021 [US3] Garantir em `src/sidebrain_back/schemas/mission_schema.py` e `src/sidebrain_back/routers/v1/mission_router.py` que `stepId`, `msn_*`, `mpg_*`, payloads vazios e valores inválidos sejam rejeitados ou ocultados conforme o contrato `422`

**Checkpoint**: Todos os testes de isolamento devem passar sem alterar os
dados protegidos e sem expor informações de ownership.

## Phase 5: User Story 2 - Preservar a hierarquia de aprendizagem (Priority: P2)

**Goal**: Preservar a composição `Step -> Mission[] -> MissionProgress[]` nas
respostas de Step e Track, somente com missões ativas e progresso do usuário.

**Independent Test**: Criar um Track com Steps e Missions, registrar progresso
para dois usuários, consultar Step e Track e verificar que apenas as Missions
ativas e o progresso do usuário autenticado aparecem, sem N+1.

### Tests for User Story 2

- [ ] T022 [P] [US2] Estender o contrato de hierarquia em `tests/contract/test_step_contract.py` e `tests/contract/test_track_contract.py`, verificando `missionProgresses` filtrado, aliases semânticos e omissão de Missions excluídas
- [ ] T023 [P] [US2] Criar integração de hierarquia em `tests/integration/test_mission_hierarchy.py`, consultando Step e Track com múltiplas Missions, progressos de usuários diferentes e uma Mission soft-deleted
- [ ] T024 [P] [US2] Adicionar verificação de carregamento agrupado em `tests/integration/test_mission_hierarchy.py` ou `tests/performance/test_mission_performance.py`, confirmando que a quantidade de consultas não cresce uma por Mission em listagens de até 100 itens

### Implementation for User Story 2

- [X] T025 [US2] Ajustar `MissionResponse` e `MissionProgressResponse` em `src/sidebrain_back/schemas/mission_schema.py` ou nos schemas hierárquicos existentes para serializar `missionProgresses`, `finishedIn`, `score` e `updatedAt` sem nomes físicos
- [X] T026 [US2] Ajustar as opções de carregamento em `src/sidebrain_back/repositories/step_repository.py` e, se necessário, no repository de Track responsável pela hierarquia, mantendo `Mission.msn_is_deleted.is_(False)` e `MissionProgress.mpg_user_id == user_id` em `selectinload`
- [X] T027 [US2] Ajustar `StepResponse`/`TrackResponse` em `src/sidebrain_back/schemas/step_schema.py` e `src/sidebrain_back/schemas/track_schema.py` somente quando necessário para manter a composição existente e evitar defaults mutáveis

**Checkpoint**: Consultas de Step e Track mantêm a hierarquia completa para o
usuário atual e omitem missões/progressos indevidos.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validar a entrega completa, documentação e regressão.

- [X] T028 [P] Atualizar referências de validação e endpoints em `specs/SDB-86-mission-crud/quickstart.md` e `specs/SDB-86-mission-crud/contracts/mission-api.md` após qualquer ajuste de implementação
- [X] T029 [P] Revisar nomes, aliases, defaults de listas e responsabilidades de camada em `src/sidebrain_back/schemas/mission_schema.py`, `src/sidebrain_back/repositories/mission_repository.py`, `src/sidebrain_back/services/mission_service.py` e `src/sidebrain_back/routers/v1/mission_router.py`
- [X] T030 Executar `uv run ruff check .` e corrigir apenas problemas introduzidos pela feature nos arquivos alterados
- [X] T031 Executar `uv run pytest tests/contract/test_mission_contract.py tests/unit/test_mission_schema.py tests/unit/test_mission_service.py tests/integration/test_mission_lifecycle.py tests/integration/test_mission_hierarchy.py` e registrar o resultado em `specs/SDB-86-mission-crud/quickstart.md` se o fluxo de documentação exigir evidência
- [X] T032 Executar `uv run pytest` para regressão completa e confirmar que os endpoints existentes de Step e Track permanecem compatíveis

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências; T002 e T003 podem executar em paralelo.
- **Foundational (Phase 2)**: depende de T001; T005 e T006 podem executar em
  paralelo após a revisão inicial.
- **User Story 1 (Phase 3)**: depende de Phase 2; T007–T009 devem ser escritos
  e falhar antes de T010–T015.
- **User Story 3 (Phase 4)**: depende da base de Mission de US1, especialmente
  T011–T013; os testes T016–T018 devem orientar T019–T021.
- **User Story 2 (Phase 5)**: depende da resposta e carregamento de Mission
  entregues em US1; pode iniciar após os contratos de US1 estarem estáveis.
- **Polish (Phase 6)**: depende das histórias desejadas e executa a validação
  completa.

### User Story Dependencies

- **US1 (P1)**: independente após Phase 2; é o MVP.
- **US3 (P1)**: depende da infraestrutura de Mission de US1 para testar e
  fortalecer a autorização, mas não depende de US2.
- **US2 (P2)**: depende de MissionResponse/MissionProgressResponse de US1; não
  altera o escopo de mutação de MissionProgress.

### Parallel Opportunities

- Phase 1: T002 e T003.
- Phase 2: T005 e T006.
- US1: T007, T008 e T009 podem ser escritos em paralelo; T010 pode ser
  implementado em paralelo com T011 após os contratos dos schemas estarem
  definidos.
- US3: T016, T017 e T018 podem ser escritos em paralelo; T019 e T021 tocam
  arquivos diferentes e podem ser executados em paralelo após os testes.
- US2: T022, T023 e T024 podem ser escritos em paralelo; T025 e T026 tocam
  arquivos diferentes.
- Polish: T028 e T029 podem executar em paralelo; T030–T032 são sequenciais.

## Parallel Example: User Story 1

```text
Task T007: testes de schema em tests/unit/test_mission_schema.py
Task T008: testes HTTP em tests/contract/test_mission_contract.py
Task T009: ciclo de vida em tests/integration/test_mission_lifecycle.py
```

Após os testes falharem por ausência da implementação:

```text
Task T010: schemas em src/sidebrain_back/schemas/mission_schema.py
Task T011: repository em src/sidebrain_back/repositories/mission_repository.py
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Concluir Setup e Foundational.
2. Escrever T007–T009 e confirmar falhas esperadas.
3. Implementar T010–T015.
4. Validar o checkpoint da US1 com os testes direcionados.
5. Parar para demonstração do CRUD básico antes de ampliar a hierarquia.

### Incremental Delivery

1. Entregar US1 como MVP.
2. Entregar US3 com isolamento e `404` uniforme.
3. Entregar US2 preservando a hierarquia Step/Track.
4. Executar Polish e a suíte completa.

### Traceability

- **FR-001/002/005/006/007/008/009/010/011/012/017**:
  T007–T015.
- **FR-003/004/013/016/017**: T016–T021.
- **FR-014/015**: T022–T027.
- **SC-001/003/005/007**: US1.
- **SC-002**: US3.
- **SC-004/006**: US2.

## Notes

- Todas as tarefas seguem o formato `- [ ] Txxx [P?] [US?] descrição com caminho`.
- `[P]` só é usado quando os arquivos são distintos e não há dependência de
  uma tarefa incompleta.
- Não foi criada tarefa de migração porque o modelo e as tabelas de Mission já
  existem; qualquer alteração de banco futura deverá ganhar migração reversível
  e testes próprios.
