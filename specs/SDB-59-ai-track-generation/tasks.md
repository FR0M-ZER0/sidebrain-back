---

description: "Task list for AI track generation"
---

# Tasks: Geração de Trilhas com IA

**Input**: Design documents from `/specs/SDB-59-ai-track-generation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/generation-task.md, quickstart.md

**Tests**: Incluídos porque o plano, a constituição e o quickstart exigem testes unitários, de integração e de contrato.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar os pontos de extensão para o worker e a persistência da geração sem criar endpoint HTTP.

- [X] T001 [P] Registrar o módulo de tasks da geração no ciclo de inicialização do worker em `src/sidebrain_back/core/celery_app.py`, preservando serialização JSON e o broker/backend Redis existentes
- [X] T002 [P] Criar os módulos de geração previstos na estrutura do plano em `src/sidebrain_back/schemas/`, `src/sidebrain_back/services/`, `src/sidebrain_back/repositories/` e `src/sidebrain_back/tasks/`, mantendo as dependências `tasks -> services -> repositories -> models`
- [X] T003 [P] Adicionar fixtures e helpers compartilhados para contexto, resposta estruturada, sessão assíncrona e cliente Groq mockado em `tests/conftest.py`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estabelecer a chave idempotente e os contratos internos que todas as histórias utilizam.

- [X] T004 Adicionar `trk_generation_request_id` opcional e único ao modelo `Track` em `src/sidebrain_back/models/track_model.py`, sem expor o campo nos schemas públicos
- [X] T005 Criar migration reversível para adicionar/remover `track.trk_generation_request_id` e sua restrição `UNIQUE` em `migrations/versions/adiciona_idempotencia_da_geracao_de_trilhas.py`, incluindo downgrade sem erro
- [X] T006 [P] Definir `LearningContext`, `GenerationInput`, `GeneratedTrack`, `GeneratedStep`, `GeneratedLesson`, `GeneratedQuiz`, `GeneratedMission` e payloads de sucesso/falha em `src/sidebrain_back/schemas/generation_schema.py`; aplicar `goal`/`topic` obrigatórios, `knowledge_level`/`assessment_answers` opcionais, títulos com “1-255 caracteres”, posições “inteiro positivo, único e contíguo”, enums de domínio e valores positivos
- [X] T007 [P] Definir códigos de erro e exceções tratáveis da geração em `src/sidebrain_back/core/errors.py` ou módulo dedicado `src/sidebrain_back/services/generation_errors.py`, sem expor SQL, stack trace, prompt, token ou resposta bruta do provedor
- [X] T008 Criar teste de contrato do payload da task, incluindo campos obrigatórios `request_id`, `user_id`, `goal` e `topic`, opcionais omitidos, saída `succeeded`/`failed` e códigos de erro em `tests/contract/test_generation_task_contract.py`

**Checkpoint**: Migration, modelos internos e contrato serializável prontos; as histórias podem ser implementadas nos limites definidos abaixo.

## Phase 3: User Story 1 - Gerar a estrutura de uma trilha personalizada (Priority: P1) MVP

**Goal**: Receber o contexto de aprendizagem, chamar a IA, validar a estrutura completa e criar a trilha com todas as etapas na ordem da estratégia.

**Independent Test**: Fornecer contexto válido com e sem nível/respostas, executar a task assíncrona com Groq mockado e confirmar título, descrição, etapas ordenadas e níveis válidos; fornecer resposta inválida e confirmar erro sem registros.

### Tests for User Story 1

- [X] T009 [P] [US1] Testar validação de contexto, enums, limites textuais, posições únicas/contíguas e rejeição de conteúdo inválido nas etapas posteriores em `tests/unit/test_generation_schema.py`
- [X] T010 [P] [US1] Testar montagem do prompt com objetivo, tópico, nível e respostas disponíveis, exigindo todas as etapas e conteúdo detalhado somente na posição 1, em `tests/unit/test_generation_prompt.py`
- [X] T011 [P] [US1] Testar task com resposta válida, resposta vazia/malformada, campos ausentes, enum inválido e falha de validação antes de qualquer `session.add`/flush em `tests/unit/test_generation_task.py`
- [X] T012 [US1] Testar integração da geração de estrutura com todas as etapas na ordem e níveis esperados em `tests/integration/test_generation_structure.py`

### Implementation for User Story 1

- [X] T013 [P] [US1] Implementar serialização do contexto e prompt JSON estruturado usando `sidebrain_back.core.groq_client.get_groq_client` em `src/sidebrain_back/services/generation_service.py`, sem enviar IDs físicos ao provedor
- [X] T014 [US1] Implementar validação completa de `GeneratedTrack` em `src/sidebrain_back/schemas/generation_schema.py`, rejeitando etapas fora de ordem, níveis duplicados indevidos, posições inválidas, campos ausentes, valores fora do domínio e conteúdo posterior à primeira etapa
- [X] T015 [US1] Implementar orquestração do contexto, chamada única ao Groq, validação antes da persistência e payload serializável de sucesso/falha em `src/sidebrain_back/services/generation_service.py`
- [X] T016 [US1] Implementar task Celery de geração com entrada `request_id`, `user_id`, `goal`, `topic`, `knowledge_level` e `assessment_answers` em `src/sidebrain_back/tasks/generate_track_task.py`, classificando conexão/timeout/rate limit como transitórios e limitando a três tentativas totais com backoff/jitter
- [X] T017 [US1] Implementar criação transacional de Track e Steps em `src/sidebrain_back/repositories/generation_repository.py`, preservando `status=idle`, todas as posições contíguas e o `trk_generation_request_id` único
- [X] T018 [US1] Registrar logs estruturados com `request_id`, task id e categoria do erro, sem prompt completo, credenciais ou detalhes internos, em `src/sidebrain_back/tasks/generate_track_task.py`

**Checkpoint**: US1 deve gerar uma estrutura completa válida ou falhar de forma tratável sem registros parciais.

## Phase 4: User Story 2 - Disponibilizar o conteúdo inicial da trilha (Priority: P1)

**Goal**: Materializar somente a primeira etapa com lições ordenadas, um quiz por lição e missão opcional.

**Independent Test**: Executar uma geração válida e confirmar que a primeira etapa contém lições com título/texto/posição, quiz relacionado e missão quando aplicável, incluindo o caso sem missão.

### Tests for User Story 2

- [X] T019 [P] [US2] Testar validação de lições com posições únicas/contíguas, título “1-255 caracteres”, texto não vazio, exatamente um quiz por lição e missão opcional compatível em `tests/unit/test_generation_initial_content.py`
- [X] T020 [P] [US2] Testar persistência da primeira etapa com lições ordenadas, quiz associado a cada lição e missão com título, dificuldade, `xp_reward`, critério e `criteria_value` em `tests/integration/test_generation_initial_content.py`
- [X] T021 [US2] Testar criação válida sem missão na primeira etapa quando a estratégia não a prevê em `tests/integration/test_generation_without_mission.py`

### Implementation for User Story 2

- [X] T022 [US2] Completar a validação de conteúdo inicial em `src/sidebrain_back/schemas/generation_schema.py`, garantindo quiz obrigatório por lição, `GeneratedMission` no máximo uma e campos numéricos positivos compatíveis com os enums do domínio
- [X] T023 [US2] Implementar montagem de Lesson, Quiz e Mission somente para a etapa de `position == 1` em `src/sidebrain_back/repositories/generation_repository.py`, respeitando `lsn_position` e `status=idle`
- [X] T024 [US2] Integrar a materialização do conteúdo inicial ao fluxo transacional de `src/sidebrain_back/services/generation_service.py`, sem gerar ou persistir respostas, feedbacks, progresso de missão ou arquivos de lição
- [X] T025 [US2] Atualizar o contrato de resultado e asserções de task em `tests/contract/test_generation_task_contract.py` para retornar `track_id` somente em sucesso e mensagem pública estável em falha

**Checkpoint**: US2 deve entregar a primeira etapa pronta para estudo, com missão opcional, sem depender de endpoint novo.

## Phase 5: User Story 3 - Preservar etapas futuras para geração posterior (Priority: P1)

**Goal**: Persistir etapas futuras apenas como estrutura, garantir idempotência e manter rollback integral em falhas.

**Independent Test**: Gerar uma trilha com pelo menos duas etapas e confirmar que apenas a primeira possui lições/quizzes/missão; repetir o mesmo `request_id` sem duplicar e provocar falha de persistência para confirmar rollback.

### Tests for User Story 3

- [X] T026 [P] [US3] Testar rejeição de lição, quiz ou missão não vazios em etapa posterior e confirmação de que a instrução enviada à IA delimita conteúdo detalhado à primeira etapa em `tests/unit/test_generation_future_steps.py`
- [X] T027 [P] [US3] Testar reexecução com o mesmo `request_id`, retorno da trilha existente, conflito de unicidade e novo pedido com identificador diferente em `tests/integration/test_generation_idempotency.py`
- [X] T028 [P] [US3] Testar rollback de Track, Steps, Lessons, Quizzes e Mission quando a persistência falhar, e ausência de `Answer`, `Feedback`, `MissionProgress` e `LessonFile`, em `tests/integration/test_generation_transaction.py`

### Implementation for User Story 3

- [X] T029 [US3] Implementar busca por `request_id` e retorno da trilha associada antes da chamada à IA em `src/sidebrain_back/repositories/generation_repository.py`, tratando conflito de unicidade sem duplicar registros
- [X] T030 [US3] Garantir em `src/sidebrain_back/repositories/generation_repository.py` que etapas com `position > 1` sejam persistidas sem lições, quizzes ou missões e que somente relações da etapa 1 sejam montadas
- [X] T031 [US3] Envolver a gravação completa em `async with session.begin()` e mapear falhas de persistência/idempotência para erro tratável em `src/sidebrain_back/services/generation_service.py`
- [X] T032 [US3] Ajustar reexecução, retry e resultado final da task em `src/sidebrain_back/tasks/generate_track_task.py` para reutilizar trilha concluída, preservar task pendente do fluxo existente e não repetir falhas permanentes/validação

**Checkpoint**: US3 deve preservar a geração futura, impedir duplicatas e garantir zero registros parciais em qualquer falha.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validar migração, qualidade e o quickstart completo.

- [X] T033 [P] Adicionar teste de aplicação e reversão da migration de idempotência em `tests/integration/test_generation_migration.py`
- [X] T034 [P] Atualizar documentação do fluxo interno, limites de retry e ausência de endpoint em `specs/SDB-59-ai-track-generation/quickstart.md`
- [X] T035 Executar `uv run pytest tests/unit tests/integration tests/contract` e corrigir regressões da feature mantendo os contratos em `tests/contract/`, `tests/integration/` e `tests/unit/`
- [X] T036 Executar `uv run ruff check .` e corrigir somente problemas introduzidos pela geração de trilhas

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001-T003 podem iniciar em paralelo; não depende de outras fases.
- **Foundational (Phase 2)**: depende da Phase 1; T004-T008 são pré-requisitos das histórias.
- **User Stories (Phases 3-5)**: dependem da Phase 2. A implementação de US2 usa a validação, task e repositório de US1; US3 usa a materialização transacional de US1/US2, apesar de cada história ter teste independente.
- **Polish (Phase 6)**: depende das três histórias e da migration implementadas.

### User Story Dependencies

- **US1 (P1)**: inicia após Phase 2 e é o MVP; não depende de outra história.
- **US2 (P1)**: inicia após Phase 2, mas integra os componentes de geração criados em US1 para materializar o primeiro conteúdo.
- **US3 (P1)**: inicia após Phase 2; suas garantias de etapas futuras e rollback completam o fluxo transacional de US1/US2.

### Parallel Opportunities

- T001, T002 e T003 podem ser feitos em paralelo.
- T004 e T006-T008 podem ser feitos em paralelo; T005 depende do nome final da coluna/modelo.
- Em US1, T009-T011 podem ser escritos em paralelo; T013 e a preparação da persistência T017 podem avançar em arquivos distintos.
- Em US2, T019-T021 podem ser escritos em paralelo; a validação T022 e a montagem ORM T023 são separáveis antes da integração T024.
- Em US3, T026-T028 podem ser escritos em paralelo; a busca idempotente T029 e a regra de conteúdo futuro T030 são separáveis.
- T033 e T034 podem ser feitos em paralelo após o fluxo estabilizar.

## Parallel Example: User Story 1

```text
T009 tests/unit/test_generation_schema.py
T010 tests/unit/test_generation_prompt.py
T011 tests/unit/test_generation_task.py

T013 src/sidebrain_back/services/generation_service.py
T017 src/sidebrain_back/repositories/generation_repository.py
```

## Parallel Example: User Story 2

```text
T019 tests/unit/test_generation_initial_content.py
T020 tests/integration/test_generation_initial_content.py
T021 tests/integration/test_generation_without_mission.py
```

## Parallel Example: User Story 3

```text
T026 tests/unit/test_generation_future_steps.py
T027 tests/integration/test_generation_idempotency.py
T028 tests/integration/test_generation_transaction.py
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Setup e Foundational.
2. Implementar US1: contexto, prompt estruturado, validação, task e Track/Steps transacionais.
3. Executar os testes independentes de US1 e confirmar que respostas inválidas não gravam registros.
4. Parar para validação antes de adicionar conteúdo detalhado.

### Incremental Delivery

1. Entregar US1 com estrutura completa e falha tratável.
2. Entregar US2 com conteúdo inicial da primeira etapa e missão opcional.
3. Entregar US3 com etapas futuras, idempotência e rollback comprovados.
4. Executar Phase 6 e os comandos do quickstart.

### Suggested MVP Scope

O MVP recomendado é a **User Story 1**, pois entrega a estrutura personalizada e estabelece o contrato assíncrono; US2 e US3 devem ser adicionadas antes de considerar a experiência completa da feature.

## Completion Criteria

- Todos os 36 tasks usam checkbox `- [ ]`, ID sequencial, marcador `[P]` somente quando aplicável, labels `[US1]`/`[US2]`/`[US3]` nas fases de história e caminho de arquivo explícito.
- Cada história possui objetivo, teste independente, testes direcionados e implementação rastreável aos requisitos.
- Não há endpoint novo previsto; o contrato é interno entre o fluxo de acompanhamento e a task Celery.
