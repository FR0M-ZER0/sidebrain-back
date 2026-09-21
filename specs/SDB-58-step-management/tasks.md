---

description: "Lista de tarefas para implementar o gerenciamento de etapas"
---

# Tasks: Gerenciamento de Etapas

**Input**: Design documents from `/specs/SDB-58-step-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/steps.md` e `quickstart.md`

**Organization**: As tarefas estão agrupadas por história de usuário para permitir implementação e validação independentes.

**Tests**: Incluídos porque a especificação e a constituição exigem testes unitários, de integração e de contrato.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar os pontos de extensão da feature no serviço FastAPI existente.

- [X] T001 [P] Confirmar as convenções de camadas, paginação, Problem Details e `Depends` em `docs/architecture.md` e `docs/code_conventions.md`
- [X] T002 [P] Mapear os modelos, enums e schemas de conteúdo já existentes que serão reutilizados em `src/sidebrain_back/models/step_model.py`, `src/sidebrain_back/models/lesson_model.py`, `src/sidebrain_back/models/mission_model.py` e `src/sidebrain_back/schemas/`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implementar a infraestrutura compartilhada que bloqueia os endpoints das três histórias.

**Critical**: Nenhuma história de usuário deve começar antes desta fase.

- [X] T003 Criar o schema público base de Step em `src/sidebrain_back/schemas/step_schema.py`, configurando `from_attributes=True`, expondo apenas `id`, `level`, `title`, `status`, `updated_at`, `lessons` e `missions` nas respostas e ocultando colunas físicas, auditoria e soft delete
- [X] T004 Criar os schemas de entrada `StepCreate` e `StepUpdate` em `src/sidebrain_back/schemas/step_schema.py`, exigindo `level` e `title`, usando `extra="forbid"`, restringindo `level` a `beginner`, `intermediate`, `advanced` ou `pro` e validando `title` com 1 a 255 caracteres após trim
- [X] T005 Criar a base de consultas hierárquicas e filtros de ownership/soft delete em `src/sidebrain_back/repositories/step_repository.py`, usando `selectinload` aninhado para Lessons, Quizzes, Answers, Feedbacks, LessonFiles, Missions e MissionProgress filtrado pelo usuário atual
- [X] T006 Criar os providers de dependência e o esqueleto do serviço em `src/sidebrain_back/services/step_service.py`, mantendo o fluxo `router -> service -> repository -> model` e erros uniformes de recurso não encontrado e persistência
- [X] T007 Registrar o router de Steps no agregador em `src/sidebrain_back/routers/router.py`, preservando o prefixo público efetivo `/api/v1/tracks/{track_id}/steps`

**Checkpoint**: schemas, filtros de segurança, carregamento da árvore, providers e registro de rota estão disponíveis para as histórias.

## Phase 3: User Story 1 - Criar uma etapa em uma trilha própria (Priority: P1) MVP

**Goal**: Permitir que um usuário autenticado crie um Step válido somente em um Track ativo de sua propriedade.

**Independent Test**: Com um Track ativo próprio, enviar `POST /api/v1/tracks/{track_id}/steps` com `level` e `title` válidos e verificar `201`, vínculo pela URL, status `idle` e listas `lessons`/`missions` vazias; repetir com payloads inválidos e Track inexistente, excluído ou de outro usuário.

### Tests for User Story 1

- [X] T008 [P] [US1] Criar testes unitários dos schemas de criação e resposta em `tests/unit/test_step_schema.py`, cobrindo enum de `level`, título obrigatório com limite de 1 a 255 caracteres, `extra="forbid"` e ausência de campos internos
- [X] T009 [P] [US1] Criar testes unitários da criação e autorização no serviço em `tests/unit/test_step_service.py`, cobrindo Track próprio ativo, Track inexistente/excluído/de outro usuário e retorno inicial sem filhos
- [X] T010 [P] [US1] Criar testes de contrato do endpoint POST em `tests/contract/test_step_contract.py`, cobrindo `201`, payload público, `401`, erros de validação e `404` uniforme

### Implementation for User Story 1

- [X] T011 [US1] Implementar a criação de Step em `src/sidebrain_back/repositories/step_repository.py`, derivando `stp_track_id` exclusivamente de `track_id` da URL, inicializando `is_deleted=false` e preservando o status inicial `idle`
- [X] T012 [US1] Implementar `create_step` em `src/sidebrain_back/services/step_service.py`, validando ownership do Track antes da persistência e convertendo falhas de persistência para Problem Details sem detalhes internos
- [X] T013 [US1] Implementar `POST /tracks/{track_id}/steps` em `src/sidebrain_back/routers/v1/step_router.py`, exigindo autenticação, retornando `StepResponse` com `201` e sem aceitar Track ou campos gerenciados no corpo
- [X] T014 [US1] Executar e ajustar o fluxo de criação para satisfazer `tests/unit/test_step_schema.py`, `tests/unit/test_step_service.py` e `tests/contract/test_step_contract.py`, garantindo que a história seja demonstrável isoladamente

**Checkpoint**: a criação de Step próprio funciona sem expor dados de outro usuário e sem criar filhos.

## Phase 4: User Story 2 - Consultar etapas e seu conteúdo (Priority: P1)

**Goal**: Listar e consultar Steps ativos do Track próprio com a hierarquia filtrada de conteúdo relacionado, sem N+1 por filho.

**Independent Test**: Preparar um Track com Steps, Lessons, Quizzes, Answers, Feedbacks, LessonFiles, Missions e MissionProgress; verificar listagem paginada, consulta individual, filtros de soft delete/ownership e carregamento agrupado.

### Tests for User Story 2

- [X] T015 [P] [US2] Criar testes de contrato dos endpoints GET em `tests/contract/test_step_contract.py`, cobrindo paginação `page >= 1`, `page_size` entre 1 e 100, ordenação estável, envelopes públicos e `404` por hierarquia incompatível
- [X] T016 [P] [US2] Criar testes de integração da árvore de Steps em `tests/integration/test_step_hierarchy_queries.py`, cobrindo Lessons, Quizzes com Answers, Feedbacks, LessonFiles, Missions com progressos do usuário, omissão de filhos excluídos e ausência de duplicações/N+1
- [X] T017 [P] [US2] Criar testes unitários de leitura em `tests/unit/test_step_service.py`, cobrindo coleção vazia, Track/Step excluído, Step fora do Track e Track pertencente a outro usuário

### Implementation for User Story 2

- [X] T018 [US2] Implementar a consulta hierárquica agrupada em `src/sidebrain_back/repositories/step_repository.py`, aplicando `selectinload`, filtros de soft delete, filtro de `MissionProgress` pelo usuário e `.unique()` quando necessário
- [X] T019 [US2] Implementar listagem paginada em `src/sidebrain_back/repositories/step_repository.py`, ordenando por `stp_updated_at DESC` e `stp_id DESC` e retornando somente Steps ativos do Track autorizado
- [X] T020 [US2] Implementar `list_steps` e `get_step` em `src/sidebrain_back/services/step_service.py`, validando Track e Step simultaneamente por URL, ownership e flags de exclusão e convertendo ausência em `404` uniforme
- [X] T021 [US2] Implementar `GET /tracks/{track_id}/steps` e `GET /tracks/{track_id}/steps/{step_id}` em `src/sidebrain_back/routers/v1/step_router.py`, usando o envelope `PaginatedResponse` e `StepResponse` conforme o contrato
- [X] T022 [US2] Ajustar a composição dos schemas filhos em `src/sidebrain_back/schemas/step_schema.py` para reutilizar os schemas públicos compatíveis de Lesson, Quiz, Answer, Feedback, LessonFile, Mission e MissionProgress sem expor nomes físicos
- [X] T023 [US2] Executar e ajustar `tests/contract/test_step_contract.py`, `tests/integration/test_step_hierarchy_queries.py` e `tests/unit/test_step_service.py` para confirmar filtros, paginação, hierarquia completa e ausência de carregamento individual por filho

**Checkpoint**: listagem e consulta individual retornam somente a árvore autorizada, sem filhos excluídos e sem N+1 evitável.

## Phase 5: User Story 3 - Atualizar e remover uma etapa (Priority: P1)

**Goal**: Atualizar `level` e `title` por PUT completo e remover logicamente um Step próprio sem alterar seus filhos.

**Independent Test**: Criar um Step, atualizá-lo com os dois campos obrigatórios, rejeitar campos gerenciados ou payload incompleto, removê-lo com `204`, confirmar `404` nas operações seguintes e verificar que filhos permanecem inalterados.

### Tests for User Story 3

- [X] T024 [P] [US3] Estender os testes unitários de atualização e remoção em `tests/unit/test_step_service.py`, cobrindo PUT completo, preservação de status/auditoria, soft delete terminal, ownership e idempotência negativa com `404`
- [X] T025 [P] [US3] Estender os testes de contrato de mutação em `tests/contract/test_step_contract.py`, cobrindo `200` no PUT, `204` no DELETE, campos extras/gerenciados rejeitados e erros `401`/`404`/`422`
- [X] T026 [P] [US3] Criar testes de integração do ciclo de vida em `tests/integration/test_step_lifecycle.py`, cobrindo atualização, persistência de `stp_is_deleted=true` e `stp_deleted_at`, exclusão física ausente e filhos inalterados

### Implementation for User Story 3

- [X] T027 [US3] Implementar atualização completa e soft delete em `src/sidebrain_back/repositories/step_repository.py`, alterando apenas `stp_level` e `stp_title` no PUT e preenchendo `stp_deleted_at` sem cascata para filhos
- [X] T028 [US3] Implementar `update_step` e `delete_step` em `src/sidebrain_back/services/step_service.py`, recusando Steps excluídos ou fora da hierarquia e mantendo os campos gerenciados sob controle do sistema
- [X] T029 [US3] Implementar `PUT /tracks/{track_id}/steps/{step_id}` e `DELETE /tracks/{track_id}/steps/{step_id}` em `src/sidebrain_back/routers/v1/step_router.py`, retornando `200` com a árvore atualizada e `204` sem corpo, respectivamente
- [X] T030 [US3] Executar e ajustar `tests/unit/test_step_service.py`, `tests/contract/test_step_contract.py` e `tests/integration/test_step_lifecycle.py` para confirmar o ciclo completo e a preservação dos registros filhos

**Checkpoint**: o CRUD completo de Step está funcional, com PUT controlado, soft delete e isolamento por ownership.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validar o conjunto da feature e a conformidade com os contratos do repositório.

- [X] T031 [P] Atualizar a documentação de rotas e exemplos de gerenciamento de Steps em `README.md` ou na documentação de API existente, refletindo `/api/v1/tracks/{track_id}/steps`
- [X] T032 [P] Revisar os módulos da feature em `src/sidebrain_back/repositories/step_repository.py`, `src/sidebrain_back/services/step_service.py`, `src/sidebrain_back/schemas/step_schema.py` e `src/sidebrain_back/routers/v1/step_router.py` contra `docs/architecture.md` e `docs/code_conventions.md`
- [X] T033 Executar a validação específica do quickstart com `uv run pytest tests/unit/test_step_schema.py tests/unit/test_step_service.py` e `uv run pytest tests/contract/test_step_contract.py tests/integration/test_step_hierarchy_queries.py tests/integration/test_step_lifecycle.py`, conforme `specs/SDB-58-step-management/quickstart.md`
- [X] T034 Executar `uv run ruff check .` e `uv run pytest` para validar lint e regressão da suíte completa conforme `.specify/memory/constitution.md`

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: sem dependências; T001 e T002 podem executar em paralelo.
- **Phase 2 (Foundational)**: depende da Phase 1 e bloqueia todas as histórias; T003/T004, T005 e T006 podem iniciar em paralelo, enquanto T007 depende do router/provider disponíveis.
- **Phase 3 (US1)**: depende da Phase 2; é o MVP e habilita a criação usada pelos cenários seguintes.
- **Phase 4 (US2)**: depende da Phase 2 e dos dados/contratos de criação para cenários realistas; a leitura deve permanecer testável com fixtures próprias.
- **Phase 5 (US3)**: depende da Phase 2 e pode reutilizar os componentes de US1/US2; a validação do ciclo completo deve ocorrer após os endpoints compartilhados estarem integrados.
- **Phase 6 (Polish)**: depende das histórias desejadas estarem implementadas.

### User Story Dependencies

- **US1 (P1)**: pode começar após a fundação; MVP independente.
- **US2 (P1)**: pode começar após a fundação; depende apenas dos modelos/relacionamentos existentes e é independente de CRUD de filhos.
- **US3 (P1)**: pode começar após a fundação; reutiliza `StepResponse` e a autorização, sem depender de CRUD adicional.

### Parallel Opportunities

- T001/T002 podem executar em paralelo.
- T003/T004, T005 e T006 podem executar em paralelo por arquivo/responsabilidade, com T007 após a definição das dependências do router.
- Dentro de cada história, os testes unitários, de contrato e de integração marcados `[P]` podem ser escritos em paralelo antes da implementação.
- T008-T010, T015-T017 e T024-T026 podem ser distribuídos por tipo de teste.
- US1, US2 e US3 podem ser desenvolvidas em paralelo após a Phase 2 se houver equipe suficiente; a integração final permanece sequencial.

## Parallel Example: User Story 1

```text
T008: schema unit tests in tests/unit/test_step_schema.py
T009: service creation tests in tests/unit/test_step_service.py
T010: POST contract tests in tests/contract/test_step_contract.py
```

## Parallel Example: User Story 2

```text
T015: GET contract tests in tests/contract/test_step_contract.py
T016: hierarchy integration tests in tests/integration/test_step_hierarchy_queries.py
T017: read service tests in tests/unit/test_step_service.py
```

## Parallel Example: User Story 3

```text
T024: mutation service tests in tests/unit/test_step_service.py
T025: mutation contract tests in tests/contract/test_step_contract.py
T026: lifecycle integration tests in tests/integration/test_step_lifecycle.py
```

## Implementation Strategy

### MVP First (US1 Only)

1. Concluir Phases 1 e 2.
2. Implementar T008-T014.
3. Validar a criação com os testes unitários e de contrato da US1.
4. Parar no checkpoint para demonstrar criação autorizada, validação e resposta `201`.

### Incremental Delivery

1. Entregar US1 como MVP.
2. Entregar US2 para leitura paginada e hierárquica.
3. Entregar US3 para atualização e soft delete.
4. Executar a validação específica e a suíte completa na Phase 6.

### Test-First Rule

As tarefas de teste de cada história devem ser escritas e falhar antes da implementação correspondente, conforme a constituição e o quickstart.

## Completion Criteria

- [ ] Todas as 34 tarefas estão numeradas sequencialmente e seguem o formato `- [ ] T### [P?] [US?] descrição com caminho`
- [ ] Cada história possui objetivo, teste independente, testes de contrato/integração/unitários e implementação rastreável aos contratos
- [ ] Os requisitos de ownership, soft delete, hierarquia filtrada, paginação e campos públicos estão cobertos
- [ ] Os testes específicos, Ruff e suíte completa foram executados antes da conclusão da implementação
