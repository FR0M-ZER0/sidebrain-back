# Tasks: Geração de Missões por IA para Steps

**Input**: Documentos de design em `specs/SDB-93-generate-step-missions/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md` e `contracts/`

**External prerequisite**: A task SDB-93 depende da entrega do CRUD de Mission. O código atual ainda não contém `src/sidebrain_back/routers/v1/mission_router.py`, `src/sidebrain_back/services/mission_service.py` nem `src/sidebrain_back/repositories/mission_repository.py`. Complete a task correspondente de gerenciamento de missões antes de iniciar as fases de usuário; não replique essas camadas aqui.

**Tests**: Incluídos porque a especificação exige testes verificáveis e a constituição do repositório os torna obrigatórios para mudanças de comportamento e contrato.

**Organization**: Tasks agrupadas pelas três jornadas da especificação para preservar incrementos verificáveis. US2 e US3 reutilizam o validador central definido na fase Foundational.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode ser executada em paralelo com tarefas de arquivos diferentes, sem dependências incompletas.
- **[Story]**: identifica a User Story da especificação (`US1`, `US2`, `US3`).
- Todas as tarefas incluem caminhos de arquivos exatos.

## Phase 1: Setup (Prerequisite Gate)

**Purpose**: Confirmar que a dependência de CRUD está pronta antes de implementar a geração.

- [X] T001 Verificar a entrega do CRUD reutilizável: `src/sidebrain_back/routers/v1/mission_router.py`, `src/sidebrain_back/services/mission_service.py`, `src/sidebrain_back/repositories/mission_repository.py` e `src/sidebrain_back/schemas/mission_schema.py` estão ausentes; implementação SDB-93 bloqueada até a conclusão da task externa de gerenciamento de missões, sem criar duplicatas nesta feature.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Disponibilizar um único contrato validado de missão para todas as histórias.

**⚠️ CRITICAL**: T001 e esta fase devem ser concluídas antes das User Stories.

- [ ] T002 Atualizar `tests/unit/test_generation_schema.py` para cobrir `GeneratedMission`: título aparado com 1–255 caracteres; dificuldade `easy`, `medium`, `hard` ou `very_hard`; critério `number_of_lessons_completed`, `get_all_answer_right_in_a_lesson`, `complete_a_step`, `complete_a_track`, `number_of_steps_completed` ou `get_all_answers_right`; `xp_reward > 0`; `criteria_value > 0`; campos extras rejeitados.
- [ ] T003 Centralizar `GeneratedMission` em `src/sidebrain_back/schemas/generation_schema.py`, impondo literalmente as restrições de T002 e mantendo um único schema para a geração inicial, sob demanda e incremental.

**Checkpoint**: Schema central implementado e coberto; as histórias podem prosseguir sem regras divergentes de missão.

---

## Phase 3: User Story 1 - Solicitar missões para um Step (Priority: P1) 🎯 MVP

**Goal**: Solicitar missões de forma autenticada e assíncrona, obter o estado pelo `taskId` e não duplicar solicitações ou missões.

**Independent Test**: Para um Step ativo sem missões pertencente ao usuário, o POST responde rapidamente com `202`, `stepId` e `taskId`; a consulta autenticada transita por `pending`/`running` até `succeeded` ou `failed`, e as missões concluídas aparecem na leitura existente do Step. Repetir durante execução retorna o mesmo `taskId`; Step sem acesso e tarefa de outro usuário retornam `404` indistinguível.

### Tests for User Story 1

- [ ] T004 [P] [US1] Criar testes de contrato para request, responses, autenticação, status HTTP, Problem Details e consulta protegida em `tests/contract/test_mission_generation_contract.py`, conforme `specs/SDB-93-generate-step-missions/contracts/mission-generation.openapi.yaml`.
- [ ] T005 [P] [US1] Criar testes unitários em `tests/unit/test_mission_generation_service.py` para ownership Step→Track, exclusão lógica, missão ativa (skipped), reutilização de geração `pending`/`running`, criação de task única e falha de publicação.
- [ ] T006 [P] [US1] Criar testes de integração em `tests/integration/test_mission_generation.py` para geração bem-sucedida, lote atômico, concorrência no mesmo Step, consulta de estado por proprietário e `404` idêntico para recurso inexistente ou alheio.

### Implementation for User Story 1

- [ ] T007 [P] [US1] Criar `src/sidebrain_back/enums/mission_generation_status_enum.py` com os estados públicos `pending`, `running`, `succeeded` e `failed`, mantendo `RETRY` interno do Celery como `running`.
- [ ] T008 [US1] Criar `src/sidebrain_back/models/mission_generation_request_model.py` com `id` UUID, `task_id` string único, `step_id` UUID, `user_id` UUID, `status`, `error_code` curto nullable, `created_at`, `started_at` nullable e `finished_at` nullable, conforme `specs/SDB-93-generate-step-missions/data-model.md`.
- [ ] T009 [US1] Criar `migrations/versions/sdb93_create_mission_generation_requests.py` para a tabela de geração, chaves estrangeiras de Step e User, unicidade de `task_id`, estados documentados e timestamps.
- [ ] T010 [US1] Criar `src/sidebrain_back/repositories/mission_generation_request_repository.py` para criar/atualizar solicitações e consultar por `task_id` + `user_id`; serializar solicitações concorrentes bloqueando brevemente o Step ativo e retornar solicitação `pending`/`running` existente.
- [ ] T011 [US1] Adicionar a `src/sidebrain_back/schemas/mission_schema.py` `MissionGenerateRequest` com apenas `count` (inteiro de 1–3, padrão 1), `difficulty` opcional nos quatro enums permitidos e `focus` opcional aparado de 1–500 caracteres, rejeitando campos extras; adicionar responses `MissionGenerateAccepted`, `MissionGenerateSkipped` e `MissionGenerationStatus` conforme o contrato OpenAPI.
- [ ] T012 [US1] Criar `src/sidebrain_back/services/mission_generator.py` para montar contexto com título/descrição da Trilha, título/nível do Step, Steps anteriores e missões existentes, sem dados sensíveis; pedir somente os cinco campos de missão, exigir exatamente `count` resultados e não repetir erros de parsing ou validação.
- [ ] T013 [US1] Estender `src/sidebrain_back/services/mission_service.py` com `request_mission_generation` e consulta de estado: validar Step ativo e ownership Step→Track, ocultar acesso inválido em 404, retornar skipped quando houver missões ativas, devolver o mesmo `taskId` para pedido ativo, persistir o estado pendente e publicar a task sem aguardar; mapear falha de publicação para estado `failed` sanitizado e Problem Details.
- [ ] T014 [US1] Criar `src/sidebrain_back/tasks/generate_step_missions_task.py` para abrir sessão própria, marcar `running`, revalidar Step ativo/sem missões, chamar o gerador sem lock durante a chamada externa, validar o lote inteiro com `GeneratedMission`, definir o Step pai pelo servidor, persistir pelo `MissionService`/`MissionRepository` numa transação atômica e marcar `succeeded` na mesma transação; iniciar sem progresso ou entidades relacionadas, reverter lote em falha, registrar task/Step/categoria sem payload e aplicar retry limitado com backoff somente para erros transitórios do provedor.
- [ ] T015 [US1] Estender `src/sidebrain_back/routers/v1/mission_router.py` com `POST /v1/steps/{step_id}/missions/generate` e `GET /v1/missions/generations/{task_id}`, protegidos por `Depends(get_current_user)` e delegados ao service; retornar `202` accepted, `200` skipped, e nunca importar task ou repository no router.

**Checkpoint**: US1 completa quando os testes T004–T006 passam e o cliente pode solicitar, acompanhar, repetir e consultar uma geração sem acesso cruzado.

---

## Phase 4: User Story 2 - Receber missão na geração inicial da Trilha (Priority: P1)

**Goal**: Fazer a geração inicial reutilizar as regras comuns de missão sem tornar a missão obrigatória nem alterar o contrato atual da Trilha.

**Independent Test**: Gerar uma Trilha válida com primeiro Step sem missão e confirmar sucesso; para missão presente, validar os cinco campos estritos e a persistência ligada ao primeiro Step, sem conteúdo inicial nos Steps posteriores.

### Tests for User Story 2

- [ ] T016 [P] [US2] Atualizar `tests/unit/test_mission_generator.py` para verificar que o prompt da geração inicial exige somente os cinco campos de missão, valores positivos e enums permitidos e mantém missão opcional.
- [ ] T017 [P] [US2] Atualizar `tests/integration/test_generation_without_mission.py` e `tests/integration/test_generation_initial_content.py` para verificar sucesso sem missão, rejeição de missão inválida sem persistência parcial e conteúdo restrito ao primeiro Step.

### Implementation for User Story 2

- [ ] T018 [P] [US2] Atualizar `src/sidebrain_back/services/generation_service.py` para instruir o provedor a produzir, quando houver missão, apenas `title`, `difficulty`, `xp_reward`, `criteria` e `criteria_value`, com enums permitidos e valores positivos; reutilizar `GeneratedMission` sem exigir que a missão esteja presente.
- [ ] T019 [P] [US2] Atualizar `src/sidebrain_back/repositories/generation_repository.py` para persistir a missão inicial validada pelo fluxo comum, atribuir Step e campos operacionais pelo servidor e preservar atomicidade e estrutura atual da Trilha.

**Checkpoint**: US2 completa quando T016–T017 passam e criação de Trilha mantém contrato e opcionalidade da missão.

---

## Phase 5: User Story 3 - Receber missões na preparação incremental (Priority: P1)

**Goal**: Remover o validador divergente da task incremental e aplicar a regra central sem alterar elegibilidade, lock, retry ou contrato HTTP.

**Independent Test**: Preparar um Step elegível e confirmar validação central de cada missão, `xp_reward > 0` e `criteria_value > 0`, transação atômica, lock de Step e skip de conteúdo existente preservados.

### Tests for User Story 3

- [ ] T020 [P] [US3] Atualizar `tests/unit/test_prepare_next_step_content_task.py` para verificar reutilização do `GeneratedMission` central e rejeitar `xp_reward == 0` e `criteria_value == 0`, preservando retry de erros transitórios.
- [ ] T021 [P] [US3] Atualizar `tests/integration/test_generation_transaction.py` para verificar rollback integral do lote incremental com missão inválida e idempotência concorrente do Step.

### Implementation for User Story 3

- [ ] T022 [US3] Atualizar `src/sidebrain_back/tasks/prepare_next_step_content_task.py` para remover `GeneratedMission` local e importar o modelo central de `src/sidebrain_back/schemas/generation_schema.py`; alinhar `ge=0` para `gt=0` em `xp_reward` e `criteria_value`, mantendo lock, skip, política de retry e persistência incremental existentes.

**Checkpoint**: US3 completa quando T020–T021 passam e a task incremental não mantém regras duplicadas.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentar a decisão arquitetural e validar o incremento inteiro.

- [ ] T023 [P] Atualizar `docs/architecture.md` para documentar o endpoint e a consulta de estado, o ciclo do registro persistente e a persistência atômica; preservar as regras de dependência e responsabilidades das camadas.
- [ ] T024 Executar os cenários de `specs/SDB-93-generate-step-missions/quickstart.md`, `uv run ruff check .` e `uv run pytest`; corrigir falhas causadas pelas alterações SDB-93 e confirmar que os contratos preexistentes de geração de Trilha e preparação incremental continuam passando.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 verifica o pré-requisito externo de CRUD de Mission. Bloqueada enquanto a entrega de gerenciamento de missões não fornecer router, service, repository e schema.
- **Foundational (Phase 2)**: depende de T001; T002 (testes) precede T003 (schema central) e bloqueia as três histórias.
- **User Stories (Phases 3–5)**: dependem do CRUD externo e da fase Foundational. US1 implementa o fluxo sob demanda; US2 e US3 são independentes entre si após o schema central.
- **Polish (Phase 6)**: T024 depende da integração das histórias que se deseja liberar; documentação T023 pode ocorrer em paralelo com validações finais depois que o fluxo principal estabilizar.

### User Story Dependencies

- **US1 (P1)**: depende do CRUD de Mission e da fase Foundational; MVP recomendado porque cobre o fluxo assíncrono novo, ownership, status consultável e idempotência.
- **US2 (P1)**: depende do CRUD de Mission e da fase Foundational; independente de US1 em comportamento, mas ambos compartilham o validador.
- **US3 (P1)**: depende da fase Foundational; independente de US1/US2 para comportamento incremental e preserva a task existente.

### Critical Path within US1

T004–T006 (escrever testes) → T007–T011 (status, persistência e schemas) → T012 (gerador) → T013 (orquestração de negócio) → T014 (worker) → T015 (rotas) → executar T006 e T024.

## Parallel Opportunities

- **Setup**: T001 é um gate único; nenhuma implementação desta feature deve paralelizar enquanto estiver bloqueado.
- **Foundational**: T002 e T003 são sequenciais para manter desenvolvimento orientado por testes.
- **US1**: T004, T005 e T006 podem ser escritos em paralelo em arquivos distintos; depois, T007 e os testes de contrato/unidade podem prosseguir enquanto a modelagem é preparada. T008 precede T009/T010; T011 e T012 são independentes após T003; T013 depende de schemas/repositórios/gerador; T014 depende de T013; T015 integra após T013–T014.
- **US2**: T016 e T017 podem ser escritos em paralelo; T018 e T019 podem ser trabalhados em paralelo depois dos testes e do CRUD de Mission.
- **US3**: T020 e T021 podem ser escritos em paralelo; T022 segue os testes e T003.
- **Entre histórias**: US2 e US3 podem avançar em paralelo após T003 e a conclusão do CRUD de Mission; ambas não dependem do endpoint sob demanda de US1.
- **Polish**: T023 pode ser executada em paralelo com T024 após estabilização das mudanças.

## Parallel Example: User Story 1

```text
# Após concluir T001 e T003, escrever estes testes em paralelo:
T004: tests/contract/test_mission_generation_contract.py
T005: tests/unit/test_mission_generation_service.py
T006: tests/integration/test_mission_generation.py

# Após schemas, repository e gerador estarem prontos:
T013: src/sidebrain_back/services/mission_service.py
# A implementação da task e da rota só integra depois que o service define seu contrato:
T014: src/sidebrain_back/tasks/generate_step_missions_task.py
T015: src/sidebrain_back/routers/v1/mission_router.py
```

## Implementation Strategy

### MVP First (US1)

1. Concluir o pré-requisito CRUD de Mission verificado por T001.
2. Concluir T002–T003 para centralizar a validação.
3. Implementar e validar US1 com T004–T015.
4. Validar requisição rápida, consulta de estado, autorização, idempotência, persistência atômica e missões visíveis nas consultas existentes.
5. Liberar US1 como incremento independente antes de ampliar os fluxos existentes, se os critérios do produto permitirem.

### Incremental Delivery

1. Pré-requisito CRUD de Mission + Foundational.
2. US1: geração sob demanda e consulta do estado.
3. US2: convergência da geração inicial com a validação central.
4. US3: convergência incremental, sem regressão de lock/skip/retry.
5. Polish: documentação, lint e suíte completa.

### Parallel Team Strategy

1. Uma pessoa conclui T001 e T002–T003.
2. Após a fundação, frentes separadas implementam US1, US2 e US3; US1 continua condicionado ao CRUD de Mission.
3. Integrar e executar T024 somente depois das três frentes escolhidas estarem completas.
