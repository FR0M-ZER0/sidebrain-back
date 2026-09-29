---

description: "Task list for asynchronous track generation and next-step preparation"
---

# Tasks: Geração assíncrona de Trilhas e preparação de Steps

**Input**: Design documents from `specs/SDB-75-async-track-generation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Organization**: As tarefas seguem as três histórias P1 da especificação. Cada tarefa informa o arquivo concreto afetado e mantém o fluxo `routers -> services -> repositories -> models`.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar a base de testes e os pontos de integração compartilhados sem alterar regras de domínio.

- [ ] T001 [P] Adicionar fixtures e doubles para publicação de tasks Celery em `tests/conftest.py`, permitindo testar `.delay()` sem broker real.
- [ ] T002 [P] Registrar os novos contratos de resposta assíncrona no conjunto de testes de contrato em `tests/contract/test_track_mutation_contract.py`.
- [X] T003 [P] Documentar os comandos de worker, API e migração usados pela feature em `specs/SDB-75-async-track-generation/quickstart.md`.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Criar os elementos compartilhados que bloqueiam as três histórias.

- [X] T004 [P] Definir o enum de estado `pending`, `succeeded` e `failed` em `src/sidebrain_back/enums/generation_status_enum.py`, alinhado às transições do `data-model.md`.
- [X] T005 [P] Definir os schemas públicos de aceitação e preparação em `src/sidebrain_back/schemas/generation_schema.py`, mantendo `LearningContext.extra="forbid"`, texto não vazio, enums válidos e sem campos físicos `trk_*`, `qui_*` ou `ans_*`.
- [X] T006 [P] Definir os schemas de resposta Problem Details e conflito em `src/sidebrain_back/core/errors.py`, preservando RFC 9457.
- [X] T007 Criar a migração reversível da tabela de solicitação de geração em `migrations/versions/adiciona_solicitacao_de_geracao.py`, com `request_id` único, fingerprint, contexto, estado, vínculo opcional de Track, `error_code` e timestamps.
- [X] T008 Executar `uv run alembic upgrade head` e verificar downgrade/upgrade da migração da solicitação em `tests/integration/test_generation_migration.py`.

**Checkpoint**: schemas, estados, erros e persistência de solicitação estão disponíveis; as histórias podem ser implementadas sem alterar Quiz, Feedback, Health, assessment ou paginação.

## Phase 3: User Story 1 - Solicitar uma Trilha sem bloquear a aplicação (Priority: P1) 🎯 MVP

**Goal**: Receber contexto de aprendizagem, registrar uma solicitação pendente, enfileirar `tasks.generate_track` e responder `202 Accepted` sem aguardar Groq.

**Independent Test**: Enviar contexto válido com o provedor lento, confirmar `202` com `request_id` antes do término do worker e depois confirmar que a task persiste todos os Steps, com conteúdo somente no Step 1.

### Tests for User Story 1

- [ ] T009 [P] [US1] Adicionar teste de contrato para `POST /api/v1/tracks` com `202`, `status=pending`, `request_id` e payload sem `request_id` em `tests/contract/test_track_mutation_contract.py`.
- [ ] T010 [P] [US1] Adicionar teste unitário de validação do contexto público, geração automática de UUID e conversão para `GenerationInput` em `tests/unit/test_generation_schema.py`.
- [ ] T011 [P] [US1] Adicionar teste unitário do service garantindo persistência `pending`, chamada de `generate_track_task.delay()` e ausência de chamada ao provedor em `tests/unit/test_track_service_create.py`.
- [ ] T012 [P] [US1] Adicionar integração do fluxo aceito até a conclusão do worker em `tests/integration/test_async_track_generation.py`, verificando uma Track, todos os Steps e conteúdo apenas no primeiro Step.

### Implementation for User Story 1

- [X] T013 [P] [US1] Criar o modelo `GenerationRequest` em `src/sidebrain_back/models/generation_request_model.py` com `request_id` único, `user_id`, fingerprint, contexto, estado, `track_id`, `error_code` e timestamps conforme `data-model.md`.
- [X] T014 [P] [US1] Criar o acesso de persistência da solicitação em `src/sidebrain_back/repositories/generation_request_repository.py`, incluindo criação pendente, busca por `request_id`, atualização de sucesso/falha e comparação de usuário/fingerprint.
- [X] T015 [US1] Implementar normalização e fingerprint determinístico do contexto em `src/sidebrain_back/services/generation_request_service.py`, sem dependência de HTTP e sem armazenar segredos.
- [X] T016 [US1] Refatorar `TrackService.create_track` em `src/sidebrain_back/services/track_service.py` para gerar `request_id` quando ausente, persistir `pending`, montar `GenerationInput` e publicar `generate_track_task.delay()` sem aguardar o `AsyncResult`.
- [X] T017 [US1] Alterar `TrackCreate` e adicionar o response model de aceitação em `src/sidebrain_back/schemas/track_schema.py`, mantendo nomes semânticos e `request_id` opcional na entrada.
- [X] T018 [US1] Alterar `POST /api/v1/tracks` em `src/sidebrain_back/routers/v1/track_router.py` para usar `202 Accepted`, o response model assíncrono e `Depends(get_track_service)`, sem importar task/repository diretamente.
- [X] T019 [US1] Atualizar `generate_track_task` em `src/sidebrain_back/tasks/generate_track_task.py` para associar a solicitação ao resultado, persistir `succeeded`/`failed` com `error_code`, manter retry transitório limitado e não deixar Track parcial.
- [X] T020 [US1] Atualizar `GenerationService` e `GenerationRepository` em `src/sidebrain_back/services/generation_service.py` e `src/sidebrain_back/repositories/generation_repository.py` para manter a transação atômica, o vínculo com `GenerationRequest` e conteúdo apenas no Step 1.

**Checkpoint**: US1 entrega o MVP completo e validável de criação assíncrona.

## Phase 4: User Story 2 - Repetir uma solicitação sem duplicar a Trilha (Priority: P1)

**Goal**: Reutilizar um `request_id` sem publicar geração duplicada e rejeitar reutilização com contexto diferente em Problem Details `409`.

**Independent Test**: Enviar duas solicitações equivalentes enquanto a primeira está pendente e após sua conclusão; confirmar uma única solicitação/task efetiva e no máximo uma Track. Reutilizar a chave com contexto diferente e confirmar `409` sem alterar o original.

### Tests for User Story 2

- [ ] T021 [P] [US2] Adicionar testes de contrato para repetição pendente/concluída e conflito `409` em `tests/contract/test_track_mutation_contract.py`.
- [ ] T022 [P] [US2] Adicionar testes unitários de fingerprint igual/diferente, usuário diferente e corrida de constraint única em `tests/unit/test_generation_request_service.py`.
- [ ] T023 [P] [US2] Adicionar integração de idempotência e concorrência do POST em `tests/integration/test_generation_idempotency.py`, verificando no máximo uma Track e uma publicação efetiva da task.
- [ ] T024 [P] [US2] Adicionar integração de falhas do worker em `tests/integration/test_generation_transaction.py`, verificando rollback, estado `failed`, `error_code` e ausência de 500 na resposta inicial.

### Implementation for User Story 2

- [X] T025 [US2] Completar a proteção transacional do repositório em `src/sidebrain_back/repositories/generation_request_repository.py` com lock/constraint handling para que pedidos equivalentes reutilizem o registro e pedidos divergentes retornem conflito.
- [X] T026 [US2] Mapear conflito de `request_id`, validação e falha de publicação para `ProblemDetailError` em `src/sidebrain_back/services/track_service.py`, sem modificar o registro original.
- [X] T027 [US2] Ajustar o tratamento de validação, falha permanente, retry esgotado e persistência em `src/sidebrain_back/tasks/generate_track_task.py` para sempre atualizar a solicitação com `error_code` e preservar a política de retry existente.
- [ ] T028 [US2] Atualizar testes de schema e resposta interna em `tests/unit/test_generation_task.py` e `tests/unit/test_generation_schema.py` para cobrir `GenerationSuccess`/`GenerationFailure` associados ao `request_id`.

**Checkpoint**: US1 e US2 passam independentemente nos contratos e integrações de criação, idempotência e falha.

## Phase 5: User Story 3 - Preparar manualmente o próximo Step (Priority: P1)

**Goal**: Expor `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next`, validar ownership/exclusão lógica e delegar o enfileiramento à regra existente.

**Independent Test**: Com um Step autorizado e elegível, confirmar `202` e `.delay()` imediato; repetir sem duplicar conteúdo; para inexistente, excluído ou de outro usuário, confirmar o mesmo `404`; sem próximo Step, confirmar `200` com `skipped`.

### Tests for User Story 3

- [ ] T029 [P] [US3] Adicionar testes de contrato para `202 accepted`, `200 skipped` e `404` genérico em `tests/contract/test_track_mutation_contract.py`.
- [ ] T030 [P] [US3] Adicionar testes unitários de ownership, exclusão lógica, threshold e delegação única em `tests/unit/test_track_service_prepare.py`.
- [ ] T031 [P] [US3] Adicionar integração da cadeia Track -> Step -> Lesson e do endpoint manual em `tests/integration/test_prepare_next_step_content.py`, cobrindo usuário autorizado e não autorizado.
- [ ] T032 [P] [US3] Adicionar integração concorrente para duas preparações do mesmo Step em `tests/integration/test_prepare_next_step_concurrency.py`, verificando no máximo um conjunto ativo de Lessons, Quiz e Mission.

### Implementation for User Story 3

- [X] T033 [P] [US3] Adicionar consulta de Step ativo pertencente à Track e usuário em `src/sidebrain_back/repositories/track_repository.py`, ocultando inexistência, exclusão lógica e ownership incompatível sob `None`.
- [X] T034 [US3] Implementar em `src/sidebrain_back/services/track_service.py` a operação de preparação manual, reutilizando `get_next_step_to_prepare`, o threshold de 80% e `prepare_next_step_content_task.delay()` sem duplicar regra no router.
- [X] T035 [US3] Criar schemas de resposta `accepted`/`skipped` em `src/sidebrain_back/schemas/generation_schema.py`, sem expor IDs físicos ou detalhes internos.
- [X] T036 [US3] Adicionar a rota `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next` em `src/sidebrain_back/routers/v1/track_router.py` usando `Depends(get_current_user)` e `Depends(get_track_service)`, com `404` uniforme e sem acesso direto a task.
- [X] T037 [US3] Reforçar a idempotência e a concorrência da task em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, mantendo lock de linha, conteúdo ativo único, transação atômica e retry limitado.

**Checkpoint**: US3 expõe a preparação manual sem alterar a preparação automática existente nem o threshold de 80%.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validar a feature completa e proteger os contratos existentes.

- [X] T038 [P] Atualizar a documentação de endpoint e exemplos em `specs/SDB-75-async-track-generation/contracts/track-generation.md` e `README.md`, refletindo `202`, `409`, `404` genérico e estados assíncronos.
- [X] T039 [P] Executar análise de imports e corrigir dependências indevidas entre router, service, repository, model e task nos arquivos alterados em `src/sidebrain_back/`.
- [X] T040 [P] Verificar regressão dos contratos de Track, Step, Quiz e Feedback em `tests/contract/` sem alterar suas regras fora do escopo.
- [X] T041 Executar `uv run alembic upgrade head`, `uv run ruff check .` e `uv run pytest` conforme `specs/SDB-75-async-track-generation/quickstart.md` e registrar qualquer falha bloqueadora.
- [ ] T042 Executar todos os cenários do `quickstart.md` com API, Redis e worker ativos e confirmar os critérios SC-001 a SC-008.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001-T003 podem iniciar imediatamente; T002 depende apenas dos contratos existentes.
- **Foundational (Phase 2)**: T004-T008 dependem do setup e bloqueiam as histórias; T004-T006 podem ser feitos em paralelo; T007 depende de T004; T008 depende de T007.
- **User Story 1 (Phase 3)**: T009-T012 podem ser escritos em paralelo; T013-T014 podem ser feitos em paralelo após T004/T007; T015 depende de T013/T014; T016-T020 dependem dos schemas e persistência.
- **User Story 2 (Phase 4)**: depende de US1 para reutilizar o fluxo assíncrono; T021-T024 podem ser escritos em paralelo; T025-T028 dependem dos testes/fluxo de US1.
- **User Story 3 (Phase 5)**: pode iniciar após a fundação, mas a integração final deve ocorrer depois de US1; T029-T032 podem ser escritos em paralelo; T033-T037 dependem dos testes e da API de serviço existente.
- **Polish (Phase 6)**: depende das três histórias e da migração concluídas.

### User Story Dependencies

- **US1 (P1)**: depende da fundação; é o MVP.
- **US2 (P1)**: depende de US1 porque endurece o mesmo fluxo de criação e persistência de solicitação, mas possui testes de conflito/idempotência independentes.
- **US3 (P1)**: depende da fundação e do `TrackService`; pode ser desenvolvida em paralelo com US2 quando não houver edição concorrente do mesmo arquivo.

### Parallel Opportunities

- Setup: T001, T002 e T003.
- Fundação: T004, T005 e T006; após T007, validações de migração podem ser isoladas.
- US1: T009-T014, respeitando dependências de modelo/repositório; testes de contrato, schema e integração podem ser preparados em paralelo.
- US2: T021-T024; implementação do conflito e da task pode ser separada quando os testes estiverem definidos.
- US3: T029-T033; testes de contrato, service e repository podem ser preparados em paralelo.
- Polish: T038-T040.

## Parallel Example: User Story 1

```text
Task A: T009 [US1] contrato de POST /tracks em tests/contract/test_track_mutation_contract.py
Task B: T010 [US1] validação de GenerationInput em tests/unit/test_generation_schema.py
Task C: T011 [US1] enqueue no TrackService em tests/unit/test_track_service_create.py
Task D: T013 [US1] modelo GenerationRequest em src/sidebrain_back/models/generation_request_model.py
Task E: T014 [US1] repository da solicitação em src/sidebrain_back/repositories/generation_request_repository.py
```

## Parallel Example: User Story 2

```text
Task A: T021 [US2] contratos de repetição e conflito
Task B: T022 [US2] testes de fingerprint e corrida
Task C: T023 [US2] integração de idempotência
Task D: T024 [US2] integração de falhas e rollback
```

## Parallel Example: User Story 3

```text
Task A: T029 [US3] contrato accepted/skipped/404
Task B: T030 [US3] regras de ownership e delegação
Task C: T031 [US3] integração do endpoint manual
Task D: T032 [US3] concorrência da preparação
Task E: T033 [US3] consulta autorizada no TrackRepository
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Setup e Foundational.
2. Implementar US1, incluindo migração, schema, request persistido, endpoint `202` e worker.
3. Executar os testes independentes de US1 e a validação de lint.
4. Parar no checkpoint para validar que a geração assíncrona funciona antes de adicionar conflito explícito e endpoint manual.

### Incremental Delivery

1. Entregar US1 como MVP de criação assíncrona.
2. Entregar US2 com idempotência, fingerprint, conflito `409` e falhas persistidas.
3. Entregar US3 com preparação manual, ownership e concorrência.
4. Executar Polish e a suíte completa antes da liberação.

### Scope Protection

Não alterar prompts, lógica do provedor de IA, threshold de 80%, paginação, Quiz, Feedback, Health, knowledge assessment, autenticação ou frontend.

## Completion Criteria

- Todas as tarefas seguem `- [ ] T###`, usam `[P]` apenas quando paralelizáveis e possuem `[US1]`, `[US2]` ou `[US3]` nas fases de história.
- Cada história tem critério de teste independente e cobertura para seu contrato público.
- MVP sugerido: Setup + Foundational + US1.
- `uv run ruff check .` e `uv run pytest` passam após a implementação.
