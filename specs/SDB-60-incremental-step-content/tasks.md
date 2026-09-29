---

description: "Task list for incremental step content generation"
---

# Tasks: Geração incremental de conteúdo de Steps

**Input**: Design documents from `/specs/SDB-60-incremental-step-content/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/incremental-step-content.md`, `quickstart.md`

**Tests**: Os testes são obrigatórios porque a feature define limiar de progresso, concorrência, idempotência, rollback e retry, e a constituição exige cobertura unitária, de integração e de contrato.

**Organization**: As tarefas estão agrupadas por história de usuário para permitir implementação e validação independentes do incremento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo quando atua em arquivos diferentes e não depende de tarefa incompleta
- **[Story]**: História de usuário correspondente (`US1`, `US2`, `US3`)
- Toda tarefa possui caminho de arquivo explícito

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Revisar o contexto existente e preparar a extensão assíncrona sem alterar a API pública.

- [X] T001 Auditar `src/sidebrain_back/models/track_model.py`, `src/sidebrain_back/models/step_model.py`, `src/sidebrain_back/models/lesson_model.py`, `src/sidebrain_back/models/mission_model.py`, `src/sidebrain_back/models/quiz_model.py` e `src/sidebrain_back/repositories/track_repository.py` para confirmar o contrato atual de progressão, soft delete e relacionamento `Track -> Step -> Lesson` antes da implementação.
- [ ] T002 [P] Definir fixtures para `Track`, `Step`, `Lesson`, `Quiz` e `Mission` em `tests/conftest.py`, `tests/unit/` e `tests/integration/` para cobrir threshold de 80%, ausência de conteúdo, conteúdo ativo/inativo e cenários de concorrência.
- [X] T003 [P] Registrar e revisar a task assíncrona no stack Celery em `src/sidebrain_back/core/celery_app.py` e `src/sidebrain_back/tasks/__init__.py` para garantir o nome `tasks.prepare_next_step_content` sem criar novo endpoint HTTP.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implementar os blocos compartilhados de cálculo de progresso, identificação do próximo Step e execução assíncrona antes do desenvolvimento pelas histórias.

**CRITICAL**: Nenhuma história deve iniciar antes desta fase.

- [X] T004 Implementar helpers de cálculo de progresso e determinação do próximo Step elegível em `src/sidebrain_back/services/track_service.py`, validando critérios `>= 80%`, somente `Lesson` ativas, `Step` da mesma `Track` e ausência de conteúdo gerado.
- [X] T005 [P] Adicionar consultas de contexto e contagem em `src/sidebrain_back/repositories/track_repository.py` para obter `active_lessons_total`, `active_lessons_completed`, `completion_ratio` e o próximo `Step` elegível sem bloquear a requisição.
- [X] T006 Criar a task assíncrona base em `src/sidebrain_back/tasks/prepare_next_step_content_task.py` com entrada `step_id`, validação do `Step` existente/ativo e contexto mínimo da `Track`/Steps anteriores sem exigir `userId`.
- [X] T007 [P] Implementar a guarda de idempotência e concorrência em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, ignorando execução quando o `Step` já tem conteúdo ativo completo ou uma geração equivalente em andamento.
- [X] T008 Implementar logging, retry controlado e política de falha em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, garantindo que erros transitórios repitam até o limite e falhas permanentes encerrem sem loop infinito.

**Checkpoint**: O cálculo de progresso, a seleção do próximo Step e a task assíncrona base já estão prontos para as histórias.

---

## Phase 3: User Story 1 - Preparar o próximo Step antes da conclusão (Priority: P1) 🎯 MVP

**Goal**: Enfileirar a preparação assíncrona do próximo `Step` quando o progresso atual atingir o threshold, sem bloquear a operação principal.

**Independent Test**: Simular um `Step` com 80% ou mais de `Lesson`s ativas concluídas e verificar que a operação original conclui sem chamar provedor externo na requisição e que a tarefa de preparação é enfileirada apenas quando elegível.

### Tests for User Story 1

> Escrever e executar estes testes primeiro, confirmando que falham antes da implementação.

- [X] T009 [P] [US1] Criar testes unitários de `TrackService` em `tests/unit/test_track_service_create.py` e `tests/unit/test_track_service_mutation.py` cobrindo `>= 80%`, `completion_ratio` e ausência de conteúdo do próximo `Step`.
- [ ] T010 [P] [US1] Criar testes de integração em `tests/integration/test_track_lifecycle.py` para verificar o disparo assíncrono quando o threshold é alcançado e o não-disparo quando está abaixo de 80%.
- [ ] T011 [P] [US1] Criar testes de contrato em `tests/contract/test_track_read_contract.py` para confirmar que a atualização do progresso continua responsiva e que a API pública permanece inalterada.

### Implementation for User Story 1

- [X] T012 [US1] Implementar `should_prepare_next_step` e a seleção do próximo `Step` elegível em `src/sidebrain_back/services/track_service.py`, com validações de `Step` ativo, `Track` válida e `next_step_id` opcional.
- [X] T013 [US1] Implementar a consulta do contexto de progresso em `src/sidebrain_back/repositories/track_repository.py`, incluindo contagem somente de `Lesson`s ativas, cálculo do percentual e filtro de `Step`/`Track` excluídos.
- [X] T014 [US1] Enfileirar a tarefa assíncrona sem bloquear a operação principal em `src/sidebrain_back/services/track_service.py` ou no serviço de progresso correspondente, preservando a resposta atual da API.
- [ ] T015 [US1] Validar o fluxo de MVP em `tests/integration/test_track_lifecycle.py` e `tests/unit/test_track_service_mutation.py`, confirmando que o threshold inclusivo em 80% dispara preparação e valores abaixo não disparam.

**Checkpoint**: O usuário consegue avançar sem esperar geração síncrona quando o Step atual atinge o threshold definido.

---

## Phase 4: User Story 2 - Gerar conteúdo coerente para um Step (Priority: P1)

**Goal**: Gerar `Lesson`s, `Quiz`s e `Mission`s de forma coerente com a hierarquia da `Track` e persistir tudo em uma transação atômica.

**Independent Test**: Executar a task para um `Step` elegível e verificar que o conteúdo gerado é validado antes da persistência e que `Lesson`, `Quiz` e `Mission` são persistidos com os relacionamentos corretos.

### Tests for User Story 2

- [ ] T016 [P] [US2] Criar testes unitários em `tests/unit/test_knowledge_assessment_service.py` e `tests/unit/test_track_service_mutation.py` para validar o payload de contexto e rejeitar conteúdo gerado incompatível com enums/relacionamentos.
- [ ] T017 [P] [US2] Criar testes de integração em `tests/integration/test_track_hierarchy_queries.py` para confirmar que a geração produz `Lesson`s ordenadas por `position`, `Quiz`s vinculados à `Lesson` e `Mission`s vinculadas ao `Step`.
- [ ] T018 [P] [US2] Estender `tests/integration/test_knowledge_assessment_task.py` para verificar rollback completo em falha de persistência sem conteúdo parcial.

### Implementation for User Story 2

- [X] T019 [US2] Implementar a validação estrutural do payload recebido no provedor em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, rejeitando IDs, timestamps, flags de exclusão e estados definidos pelo conteúdo externo.
- [X] T020 [US2] Construir o `GenerationContext` e o payload de geração em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, incluindo `Track`, `Step` atual, `Step`s anteriores e o contexto necessário para evitar repetição incoerente.
- [X] T021 [US2] Implementar a persistência atômica em `src/sidebrain_back/tasks/prepare_next_step_content_task.py` e em repositórios auxiliares sob `src/sidebrain_back/repositories/` para criar `Lesson`s, `Quiz`s e `Mission`s em uma única transação com `rollback` completo em falha.
- [X] T022 [US2] Garantir que o conteúdo gerado não crie `Answer`, `Feedback`, `LessonFile` ou `MissionProgress` e que os nomes físicos `lsn_*`, `qui_*` e `msn_*` sejam mapeados conforme o domínio existente.
- [ ] T023 [US2] Executar os testes focados de geração em `tests/integration/test_track_hierarchy_queries.py`, `tests/integration/test_knowledge_assessment_task.py` e `tests/unit/test_track_service_mutation.py`, confirmando que o incremento da US2 passa isoladamente.

**Checkpoint**: O conteúdo do próximo Step é gerado, validado e persistido de forma coerente e atômica.

---

## Phase 5: User Story 3 - Evitar duplicidade e recuperar falhas transitórias (Priority: P1)

**Goal**: Manter a integridade da trilha em execuções concorrentes e falhas temporárias, sem duplicar conteúdo nem deixar dados parciais persistidos.

**Independent Test**: Submeter duas execuções para o mesmo `Step`, simular timeout ou indisponibilidade do provedor e verificar que apenas uma geração persiste, que não há duplicação e que retries seguem limite configurado.

### Tests for User Story 3

- [ ] T024 [P] [US3] Criar testes de concorrência em `tests/integration/test_track_lifecycle.py` e `tests/integration/test_knowledge_assessment_task.py` para assegurar idempotência quando duas tasks disparadas para o mesmo `Step` entram em execução simultânea.
- [ ] T025 [P] [US3] Criar testes de retry em `tests/unit/test_knowledge_assessment_service.py` para simular falhas transitórias do provedor e validar limite finito sem loop infinito.

### Implementation for User Story 3

- [X] T026 [US3] Implementar a checagem de `Step` com conteúdo ativo completo ou geração em andamento em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, encerrando sem chamar o provedor externo quando o guard já estiver ativo.
- [X] T027 [US3] Adicionar deduplicação por `Step` em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, bloqueando novas tentativas e garantindo que apenas uma execução persista a coleção do próximo conteúdo.
- [X] T028 [US3] Implementar tratamento confiável de retry e falha permanente em `src/sidebrain_back/tasks/prepare_next_step_content_task.py`, incluindo logs observáveis sem expor segredos ou credenciais.
- [ ] T029 [US3] Executar os testes focados de concorrência e retry em `tests/integration/test_track_lifecycle.py`, `tests/integration/test_knowledge_assessment_task.py` e `tests/unit/test_knowledge_assessment_service.py`, confirmando que o incremento de US3 está estável e sem duplicação.

**Checkpoint**: Execuções repetidas e concorrentes não duplicam conteúdo e falhas transitórias são repetidas apenas dentro do limite definido.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidar documentação, validação operacional e gatilho final da feature.

- [X] T030 [P] Atualizar `README.md` e `docs/architecture.md` para documentar a geração incremental de conteúdo, o threshold de 80%, a task assíncrona e a separação `router -> service -> repository -> model` aplicada nesta feature.
- [ ] T031 [P] Executar os cenários de `specs/SDB-60-incremental-step-content/quickstart.md`, validando threshold, geração bem-sucedida, idempotência, concorrência e retry sem conteúdo parcial.
- [X] T032 Executar `uv run ruff check .` e `uv run pytest` no projeto, corrigindo regressões apenas na área de `src/sidebrain_back/`, `tests/` e `specs/SDB-60-incremental-step-content/` para validar a feature completa.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: inicia imediatamente.
- **Foundational (Phase 2)**: depende da Setup e bloqueia todas as histórias.
- **US1, US2 e US3 (Phases 3–5)**: dependem da fase foundational e devem ser testáveis independentemente, mas compartilham os mesmos arquivos críticos de task/service/repository.
- **Polish (Phase 6)**: depende de todas as histórias concluídas e do cenário de quickstart.

### User Story Dependencies

- **US1 (P1)**: depende da Phase 2 e constitui o MVP recomendado.
- **US2 (P1)**: depende da Phase 2 e do contexto do `Step` atual e da `Track`.
- **US3 (P1)**: depende da Phase 2 e dos guardas de idempotência introduzidos com a task.
- **Ordem recomendada**: US1 → US2 → US3, com validação por checkpoint após cada história.

### Within Each User Story

- Testes devem ser escritos e falhar antes da implementação correspondente.
- Repositório precede service; service precede task; task precede validação.
- A transação deve ser atômica e qualquer falha deve causar rollback completo.
- O checkpoint da história deve ser validado antes de avançar para a próxima.

### Dependency Graph

```text
Phase 1 Setup
    -> Phase 2 Foundational
        -> US1 Prepare next step
        -> US2 Generate coherent content
        -> US3 Idempotency and retries
    -> Phase 6 Polish
```

## Parallel Opportunities

- Setup: T002 e T003 podem ser executados em paralelo.
- Foundational: T005 e T007 podem ser executados em paralelo, enquanto T004 e T006 fornecem a base das regras e da task.
- US1: T009, T010 e T011 podem ser escritos em paralelo; T012, T013 e T014 podem seguir em paralelo após a base, com T015 como validação final.
- US2: T016, T017 e T018 podem ser executados em paralelo; T019 e T020 podem evoluir em paralelo antes da persistência, seguida por T021, T022 e T023.
- US3: T024 e T025 podem ser executados em paralelo; T026, T027 e T028 podem avançar em paralelo antes da validação final em T029.
- Polish: T030 e T031 podem ser feitos em paralelo; T032 é o gate final de qualidade.

## Parallel Example: User Story 1

```text
T009: unit tests for threshold logic in tests/unit/
T010: integration tests for asynchronous trigger in tests/integration/
T011: contract validation for unchanged API behavior in tests/contract/
```

## Parallel Example: User Story 2

```text
T016: structural validation tests in tests/unit/
T017: generation and hierarchy verification in tests/integration/
T018: rollback safety tests in tests/integration/
```

## Parallel Example: User Story 3

```text
T024: concurrent execution tests in tests/integration/
T025: retry policy tests in tests/unit/
```

## Implementation Strategy

### MVP First

1. Completar T001–T008 (Setup + Foundational).
2. Implementar T009–T015 (US1).
3. Pausar e validar a preparação do próximo Step sem bloquear a operação principal.
4. Demonstrar o threshold de 80% antes de avançar para a geração do conteúdo.

### Incremental Delivery

1. Setup + Foundational: cálculo do progresso e task assíncrona base.
2. US1: preparar conteúdo do próximo Step antes da conclusão.
3. US2: gerar conteúdo coerente e persistir em transação atômica.
4. US3: idempotência e retry seguro para concorrência e falhas transitórias.
5. Polish: documentação, validação do quickstart e regressão final.

### Independent Test Criteria

- **US1**: `completion_ratio >= 0.80` dispara a preparação do próximo `Step` sem bloquear a resposta atual, e valores abaixo de 80% não disparam geração.
- **US2**: a task gera `Lesson`s, `Quiz`s e `Mission`s coerentes com a hierarquia e, em falha, nenhuma parte persiste no banco.
- **US3**: duas execuções concorrentes para o mesmo `Step` não duplicam conteúdo; falhas transitórias têm retry limitado e o sistema encerra sem loop infinito.

## Summary

- **Total task count**: 32
- **Task count per user story**: US1 = 7, US2 = 8, US3 = 6
- **Setup/Foundational/Polish**: 11 tarefas compartilhadas
- **Parallel opportunities identified**: 18 tarefas marcadas com `[P]` em grupos de testes, geração e documentação
- **Suggested MVP scope**: T001–T015, encerrando após a User Story 1
- **Format validation**: Todos os itens usam checkbox `- [ ]`, ID sequencial `T###`, `[P]` apenas quando aplicável, `[USn]` apenas nas fases de histórias e caminho de arquivo explícito em cada tarefa

## Notes

- A feature não cria novos endpoints HTTP; ela reforça o fluxo existente de progresso e geração assíncrona.
- A geração incremental deve preservar o modelo de domínio e a política de soft delete da aplicação.
- O threshold de 80% é inclusivo (`>= 80%`) e deve ser testado explicitamente.
- A transação deve ser atômica para `Lesson`, `Quiz` e `Mission` e qualquer falha deve produzir rollback completo.
- A observabilidade das tasks deve registrar contexto útil sem expor credenciais ou dados sensíveis.
