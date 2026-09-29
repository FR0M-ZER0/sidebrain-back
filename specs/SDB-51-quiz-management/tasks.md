---

description: "Task list for quiz management"
---

# Tasks: Gerenciamento de Quizzes

**Input**: Design documents from `specs/SDB-51-quiz-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/quizzes.md`, `quickstart.md`

**Tests**: Os testes são obrigatórios porque a especificação define cenários de aceite, critérios mensuráveis de desempenho e composição hierárquica, e a constituição exige testes unitários, de integração e de contrato.

**Organization**: As tarefas estão agrupadas por história de usuário para permitir implementação e validação independente de cada incremento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo quando atua em arquivos diferentes e não depende de tarefa incompleta
- **[Story]**: História de usuário correspondente (`US1`, `US2` ou `US3`)
- Toda tarefa possui caminho de arquivo explícito

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar a base existente e preparar fixtures reais para a feature sem alterar o schema do banco.

- [X] T001 Confirmar as versões de FastAPI, Pydantic v2, SQLAlchemy async, asyncpg, Alembic, pytest e httpx em `pyproject.toml`, e verificar as tabelas/relacionamentos existentes em `src/sidebrain_back/models/quiz_model.py`, `src/sidebrain_back/models/answer_model.py`, `src/sidebrain_back/models/lesson_model.py` e `migrations/versions/16fd0aac0bc2_cria_as_tabelas_iniciais_do_projeto.py`, sem criar migration de colunas ou enums
- [X] T002 [P] Preparar em `tests/conftest.py` fixtures PostgreSQL assíncronas e factories para User, Track, Step, Lesson nos estados `idle`/`in_progress`/`done`, Quiz ativo/excluído e Answer, incluindo overrides de `get_db` e `get_current_user` e limpeza transacional entre testes

**Checkpoint**: Dependências, modelo persistente e infraestrutura de teste estão prontos.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implementar contratos e filtros compartilhados que bloqueiam as três histórias.

**CRITICAL**: Nenhuma história deve ser implementada antes desta fase.

- [X] T003 [P] Criar em `tests/unit/test_quiz_schema.py` testes falhando para `QuizCreateRequest` e `QuizUpdateRequest` com somente `question`, `strip()` antes do limite final de 1–1.000 caracteres e `extra="forbid"`, e para `QuizResponse`/`AnswerResponse` com aliases públicos, `AnswerRateEnum` restrito a `good`, `perfect`, `wrong`, `almost_got_it` e `answers=[]` por padrão
- [X] T004 Implementar em `src/sidebrain_back/schemas/quiz_schema.py` `QuizCreateRequest`, `QuizUpdateRequest`, `QuizResponse` e `AnswerResponse` conforme T003, usando `ConfigDict(from_attributes=True, populate_by_name=True)`, `Field(default_factory=list)` e sem expor `qui_*`, `ans_*`, timestamps no response direto ou flags de exclusão
- [X] T005 [P] Configurar a ordenação determinística das relações ORM em `src/sidebrain_back/models/lesson_model.py` e `src/sidebrain_back/models/quiz_model.py`: `Lesson.quizzes` por `qui_updated_at DESC, qui_id DESC` e `Quiz.answers` por `ans_created_at ASC, ans_id ASC`, sem alterar colunas nem cascatas
- [X] T006 [P] Criar `QuizRepository` e `get_quiz_repository` em `src/sidebrain_back/repositories/quiz_repository.py`, incluindo consultas compartilhadas de Lesson e Quiz acessíveis que atravessem `Lesson -> Step -> Track`, filtrem `Track.trk_user_id` pelo usuário atual, exijam `trk_is_deleted=false`, `stp_is_deleted=false`, `lsn_is_deleted=false` e, para Quiz, `qui_is_deleted=false`, e carreguem `Quiz.answers` com `selectinload`
- [X] T007 Criar `QuizService` e `get_quiz_service` em `src/sidebrain_back/services/quiz_service.py`, injetando `QuizRepository` e `AsyncSession` por `Depends` e centralizando respostas `404` que não diferenciem inexistência, exclusão ou ownership
- [X] T008 Criar o router base em `src/sidebrain_back/routers/v1/quiz_router.py` e registrá-lo em `src/sidebrain_back/routers/router.py` sob `/api/v1`, preservando `Depends(get_current_user)`, `Depends(get_quiz_service)` e os handlers globais de Problem Details

**Checkpoint**: Schemas, ordenação, autorização hierárquica, DI e roteamento estão disponíveis para todas as histórias.

---

## Phase 3: User Story 1 - Criar quiz em uma aula (Priority: P1) MVP

**Goal**: Permitir que um usuário autenticado crie um quiz em uma Lesson acessível e não excluída, usando somente a pergunta no body.

**Independent Test**: Com uma Lesson acessível em qualquer status, `POST /api/v1/lessons/{lesson_id}/quizzes` com pergunta válida retorna `201`, `lesson_id` derivado da URL e `answers=[]`; aula/pai ausente, excluído ou alheio retorna `404`, falta de autenticação retorna `401` e payload inválido retorna `422` sem persistência.

### Tests for User Story 1

> Escrever e executar estes testes primeiro, confirmando que falham antes da implementação.

- [X] T009 [P] [US1] Criar testes de contrato do `POST /api/v1/lessons/{lesson_id}/quizzes` na aplicação agregada em `tests/contract/test_quiz_contract.py`, cobrindo `201`, `401`, UUID inválido, Problem Details `404`/`422` e rejeição de `lesson_id`, `id`, `answers`, timestamps e flags no body
- [X] T010 [P] [US1] Criar testes unitários de `QuizService.create_quiz` em `tests/unit/test_quiz_service.py`, comprovando uso do `lesson_id` da URL, pergunta normalizada, aceitação de Lesson `idle`/`in_progress`/`done`, `404` para hierarquia inacessível e rollback sem persistência parcial
- [X] T011 [P] [US1] Criar teste de integração da criação em `tests/integration/test_quiz_lifecycle.py`, validando a FK para a Lesson, `qui_is_deleted=false`, `qui_deleted_at=null`, resposta sem nomes físicos e recusa quando Track, Step ou Lesson estiver excluída ou pertencer a outro usuário

### Implementation for User Story 1

- [X] T012 [US1] Implementar `QuizRepository.create` em `src/sidebrain_back/repositories/quiz_repository.py`, recebendo `lesson_id` validado e `question`, inicializando `qui_is_deleted=false`/`qui_deleted_at=null`, adicionando e fazendo `flush()` sem commit ou mutação de Answer
- [X] T013 [US1] Implementar `QuizService.create_quiz` em `src/sidebrain_back/services/quiz_service.py`, validando a Lesson acessível sem filtrar seu status, criando e materializando `QuizResponse` antes do commit, retornando `404` para pais indisponíveis e fazendo rollback com `500` sanitizado em falha inesperada
- [X] T014 [US1] Implementar `POST /v1/lessons/{lesson_id}/quizzes` com `status.HTTP_201_CREATED` e `response_model=QuizResponse` em `src/sidebrain_back/routers/v1/quiz_router.py`, obtendo `lesson_id` apenas do path e exigindo usuário autenticado
- [X] T015 [US1] Executar os testes focados de criação em `tests/unit/test_quiz_schema.py`, `tests/unit/test_quiz_service.py`, `tests/integration/test_quiz_lifecycle.py` e `tests/contract/test_quiz_contract.py`, confirmando que o incremento US1 passa isoladamente

**Checkpoint**: Criação autenticada funciona como MVP e não permite controlar relacionamento ou campos internos.

---

## Phase 4: User Story 2 - Consultar quizzes e respostas (Priority: P1)

**Goal**: Listar e consultar quizzes ativos com todas as Answers, paginação, ordenação determinística e composição hierárquica sem N+1.

**Independent Test**: Com uma Lesson contendo quizzes ativos, excluídos e Answers, os endpoints de lista e detalhe retornam somente quizzes acessíveis, cada Answer correta e ordenada; a hierarquia de Track contém `Lesson -> Quiz[] -> Answer[]`, e o número de queries não cresce por quiz ou Answer.

### Tests for User Story 2

> Escrever e executar estes testes primeiro, confirmando que falham antes da implementação.

- [X] T016 [P] [US2] Ampliar `tests/contract/test_quiz_contract.py` com contratos para `GET /api/v1/lessons/{lesson_id}/quizzes` e `GET /api/v1/quizzes/{quiz_id}`, validando autenticação, UUID/paginação, envelope `data/page/page_size/total_items/total_pages` e SC-007: Quiz identificável por `lesson_id/question/answers` e cada Answer por `user_id/text/rate`, sem nomes físicos ou campos internos
- [X] T017 [P] [US2] Criar em `tests/unit/test_quiz_service.py` testes de `list_quizzes_by_lesson` e `get_quiz`, cobrindo cálculo de offset, página além do total com `data=[]`, `total_pages=0` para coleção vazia e `404` para Lesson/Quiz indisponível
- [X] T018 [P] [US2] Criar testes PostgreSQL de leitura em `tests/integration/test_quiz_lifecycle.py`, cobrindo filtros de ownership e soft delete em Track, Step, Lesson e Quiz, ordem de quizzes `updated_at DESC, id DESC`, ordem de Answers `created_at ASC, id ASC`, empates por UUID e correspondência sem duplicações
- [X] T019 [P] [US2] Criar em `tests/integration/test_quiz_hierarchy_queries.py` o benchmark end-to-end de SC-005 com API em `MODE=test`, PostgreSQL 16 via Docker Compose, sem concorrência, 5 requisições de aquecimento e 100 requisições autenticadas sequenciais a `GET /api/v1/lessons/{lesson_id}/quizzes?page=1&page_size=50`, calculando p95 <= 2 segundos para 50 quizzes ativos com 10 Answers cada e instrumentando statements para provar contagem constante entre cenários com 1 e 50 quizzes
- [X] T020 [P] [US2] Ampliar `tests/contract/test_track_read_contract.py` para exigir `lesson_id` no Quiz e `user_id`/`AnswerRateEnum` em Answer, preservando todos os campos e aliases já publicados pelo contrato hierárquico de Track

### Implementation for User Story 2

- [X] T021 [US2] Implementar `QuizRepository.list_by_lesson_id` em `src/sidebrain_back/repositories/quiz_repository.py`, com count separado, `offset`/`limit`, `qui_is_deleted=false`, ordem `qui_updated_at DESC, qui_id DESC` e `selectinload(Quiz.answers)` em uma consulta agrupada; completar `get` compartilhado sem lazy loading
- [X] T022 [US2] Implementar `QuizService.list_quizzes_by_lesson` e `QuizService.get_quiz` em `src/sidebrain_back/services/quiz_service.py`, reutilizando `PaginatedResponse.build`, validando acesso da Lesson antes da lista e retornando `404` sem revelar ownership ou estado de exclusão
- [X] T023 [US2] Implementar `GET /v1/lessons/{lesson_id}/quizzes` e `GET /v1/quizzes/{quiz_id}` em `src/sidebrain_back/routers/v1/quiz_router.py`, usando `page=1`, `page_size=20`, `page >= 1`, `1 <= page_size <= 100` e os response models públicos
- [X] T024 [P] [US2] Refatorar `src/sidebrain_back/schemas/track_schema.py` para reutilizar o núcleo canônico de `src/sidebrain_back/schemas/quiz_schema.py`, adicionando `lesson_id` ao Quiz e `user_id`/`AnswerRateEnum` à Answer sem remover os timestamps anteriormente publicados pela API v1
- [X] T025 [P] [US2] Revisar `TrackRepository._hierarchy_options` em `src/sidebrain_back/repositories/track_repository.py` para manter `Lesson.quizzes` filtrado por `Quiz.qui_is_deleted=false`, carregar `Quiz.answers` com `selectinload` e respeitar a ordenação ORM sem queries por filho
- [X] T026 [US2] Executar os testes focados de leitura em `tests/unit/test_quiz_service.py`, `tests/integration/test_quiz_lifecycle.py`, `tests/integration/test_quiz_hierarchy_queries.py`, `tests/contract/test_quiz_contract.py` e `tests/contract/test_track_read_contract.py`, confirmando US2 isoladamente com fixtures persistidas

**Checkpoint**: Lista, detalhe e hierarquia exibem somente quizzes ativos com Answers corretas, ordenadas e carregadas em lote.

---

## Phase 5: User Story 3 - Atualizar ou remover um quiz (Priority: P2)

**Goal**: Permitir atualização exclusiva da pergunta e soft delete terminal, preservando Lesson e Answers.

**Independent Test**: `PUT /api/v1/quizzes/{quiz_id}` atualiza somente a pergunta e retorna o Quiz com Answers; `DELETE` retorna `204`, mantém Quiz/Answers fisicamente e torna o Quiz indisponível em detalhe, lista, hierarquia e mutações posteriores.

### Tests for User Story 3

> Escrever e executar estes testes primeiro, confirmando que falham antes da implementação.

- [X] T027 [P] [US3] Ampliar `tests/contract/test_quiz_contract.py` com contratos para `PUT /api/v1/quizzes/{quiz_id}` e `DELETE /api/v1/quizzes/{quiz_id}`, cobrindo `200`, `204` sem body, `401`, `404`, `422`, pergunta obrigatória com 1–1.000 caracteres após `strip()` e rejeição de alteração de `lesson_id`, Answers, IDs, timestamps e flags
- [X] T028 [P] [US3] Ampliar `tests/unit/test_quiz_service.py` com atualização e exclusão, verificando preservação da Lesson/Answers, `404` para Quiz excluído/alheio ou sob pai excluído, mesmo timestamp em `qui_updated_at`/`qui_deleted_at`, commit somente após composição válida e rollback em falha
- [X] T029 [P] [US3] Ampliar `tests/integration/test_quiz_lifecycle.py` para provar que soft delete mantém as linhas de Quiz e Answer, não aciona `ON DELETE CASCADE`, torna a exclusão terminal e remove imediatamente o Quiz de detalhe, listagem e hierarquia

### Implementation for User Story 3

- [X] T030 [US3] Implementar `QuizRepository.update` e `QuizRepository.soft_delete` em `src/sidebrain_back/repositories/quiz_repository.py`, alterando somente `qui_question`/`qui_updated_at` no PUT e definindo `qui_is_deleted=true` com `qui_deleted_at=qui_updated_at` em UTC no DELETE, sem `session.delete()` ou mutação de Answers
- [X] T031 [US3] Implementar `QuizService.update_quiz` e `QuizService.delete_quiz` em `src/sidebrain_back/services/quiz_service.py`, reutilizando o `get` autorizado, materializando a resposta antes do commit no PUT, retornando `404` para recursos indisponíveis e fazendo rollback com erro `500` sanitizado
- [X] T032 [US3] Implementar `PUT /v1/quizzes/{quiz_id}` com `QuizUpdateRequest`/`QuizResponse` e `DELETE /v1/quizzes/{quiz_id}` com `status.HTTP_204_NO_CONTENT` em `src/sidebrain_back/routers/v1/quiz_router.py`, sempre exigindo usuário autenticado e sem corpo no DELETE
- [X] T033 [US3] Executar os testes focados de mutação em `tests/unit/test_quiz_schema.py`, `tests/unit/test_quiz_service.py`, `tests/integration/test_quiz_lifecycle.py` e `tests/contract/test_quiz_contract.py`, confirmando US3 isoladamente com fixtures persistidas

**Checkpoint**: Atualização preserva o relacionamento e o soft delete é terminal sem perda física de Answers.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidar documentação, desempenho, regressão e qualidade da feature completa.

- [X] T034 [P] Documentar os cinco endpoints, paginação, aliases públicos, `404` para ownership oculto e fluxo `router -> service -> repository -> model` em `README.md` e `docs/architecture.md`, referenciando `specs/SDB-51-quiz-management/contracts/quizzes.md`
- [X] T035 [P] Executar integralmente `specs/SDB-51-quiz-management/quickstart.md` e registrar em `tests/integration/test_quiz_hierarchy_queries.py` as 5 requisições de aquecimento, as 100 amostras end-to-end, o p95 <= 2 segundos e a contagem constante de statements para 1 versus 50 quizzes, sem criar índice ou migration sem `EXPLAIN ANALYZE` que demonstre necessidade
- [X] T036 Executar os gates finais definidos em `pyproject.toml` com `uv run ruff check .` e `uv run pytest`, corrigindo apenas regressões relacionadas a Quiz nos arquivos de `src/sidebrain_back/`, `tests/` e `specs/SDB-51-quiz-management/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: inicia imediatamente.
- **Foundational (Phase 2)**: depende da Setup e bloqueia todas as histórias.
- **US1, US2 e US3 (Phases 3–5)**: dependem da Foundational. São testáveis com fixtures persistidas sem depender dos endpoints de outra história, mas alterações simultâneas em `quiz_repository.py`, `quiz_service.py` e `quiz_router.py` exigem coordenação.
- **Polish (Phase 6)**: depende das histórias incluídas no release e de PostgreSQL disponível.

### User Story Dependencies

- **US1 (P1)**: depende somente da Phase 2 e constitui o MVP recomendado.
- **US2 (P1)**: depende somente da Phase 2; suas fixtures criam Quiz/Answer diretamente, portanto não depende do POST da US1.
- **US3 (P2)**: depende dos métodos compartilhados de acesso da Phase 2; suas fixtures persistem Quiz/Answer diretamente, portanto não depende funcionalmente da US1 ou US2.
- **Ordem de integração recomendada**: US1 -> US2 -> US3, para reduzir conflitos nos quatro módulos compartilhados.

### Within Each User Story

- Testes devem ser escritos e observados falhando antes da implementação correspondente.
- Repository precede Service; Service precede Router.
- O response deve ser materializado antes do commit em mutações com body.
- O checkpoint da história deve passar antes de integrar o próximo incremento.

### Dependency Graph

```text
Phase 1 Setup
    -> Phase 2 Foundational
        -> US1 Create (MVP)
        -> US2 Read + hierarchy
        -> US3 Update + soft delete
US1 + US2 + US3
    -> Phase 6 Polish
```

## Parallel Opportunities

- Setup: T002 pode avançar enquanto T001 audita dependências e modelo.
- Foundational: T003, T005 e T006 atuam em arquivos diferentes; T004 depende de T003, T007 depende de T006 e T008 depende de T007.
- US1: T009, T010 e T011 podem ser escritos em paralelo; depois T012 -> T013 -> T014 -> T015.
- US2: T016, T017, T018, T019 e T020 podem ser escritos em paralelo; T021, T024 e T025 podem avançar em arquivos diferentes, seguidos por T022 -> T023 -> T026.
- US3: T027, T028 e T029 podem ser escritos em paralelo; depois T030 -> T031 -> T032 -> T033.
- Polish: T034 e T035 podem executar em paralelo; T036 é o gate final.

## Parallel Example: User Story 1

```text
Task T009: Contract tests in tests/contract/test_quiz_contract.py
Task T010: Service tests in tests/unit/test_quiz_service.py
Task T011: Persistence tests in tests/integration/test_quiz_lifecycle.py
```

## Parallel Example: User Story 2

```text
Task T016: Read contracts in tests/contract/test_quiz_contract.py
Task T017: Read service tests in tests/unit/test_quiz_service.py
Task T018: Filtering and ordering in tests/integration/test_quiz_lifecycle.py
Task T019: Query count and performance in tests/integration/test_quiz_hierarchy_queries.py
Task T020: Hierarchy contract in tests/contract/test_track_read_contract.py
```

## Parallel Example: User Story 3

```text
Task T027: Mutation contracts in tests/contract/test_quiz_contract.py
Task T028: Mutation service tests in tests/unit/test_quiz_service.py
Task T029: Soft-delete persistence tests in tests/integration/test_quiz_lifecycle.py
```

## Implementation Strategy

### MVP First

1. Completar T001–T008 (Setup e Foundational).
2. Implementar T009–T015 (US1).
3. Parar e validar criação autenticada independentemente.
4. Demonstrar `POST /api/v1/lessons/{lesson_id}/quizzes` antes de ampliar o CRUD.

### Incremental Delivery

1. Setup + Foundational: contratos, ordem ORM, ownership, DI e router.
2. US1: criação autenticada de Quiz.
3. US2: lista, detalhe, Answers e hierarquia sem N+1.
4. US3: atualização e soft delete terminal.
5. Polish: documentação, meta de 2 segundos, regressão, lint e suíte completa.

### Independent Test Criteria

- **US1**: POST válido retorna `201`, usa a Lesson da URL e `answers=[]`; Lesson/pai ausente, excluído ou alheio retorna `404`; entrada/autenticação inválida retorna `422`/`401` sem persistência parcial.
- **US2**: lista retorna somente quizzes ativos no envelope paginado e na ordem definida; detalhe e hierarquia incluem todas as Answers correspondentes na ordem definida e com nomes públicos verificáveis; página além do total é vazia; no protocolo de SC-005, 50 × 10 permanece sem N+1 e com p95 end-to-end <= 2 segundos.
- **US3**: PUT altera somente a pergunta e preserva Lesson/Answers; DELETE retorna `204`, mantém Quiz/Answers no banco e torna o Quiz indisponível em todas as leituras e mutações posteriores.

## Summary

- **Total task count**: 36
- **Task count per user story**: US1 = 7, US2 = 11, US3 = 7
- **Setup/Foundational/Polish**: 11 tarefas compartilhadas
- **Parallel opportunities identified**: 19 tarefas marcadas `[P]`, com grupos paralelos em todas as fases
- **Suggested MVP scope**: T001–T015, encerrando após User Story 1
- **Format validation**: Todos os 36 itens usam checkbox `- [ ]`, ID sequencial `T###`, `[P]` somente quando aplicável, `[USn]` somente nas fases de histórias e caminho de arquivo explícito

## Notes

- A migration inicial já contém Quiz, Answer, FKs, enum e soft delete; não alterar seu histórico.
- O contrato público usa `lesson_id` e `user_id`, apesar dos nomes físicos `qui_*`/`ans_*`.
- Answer é somente leitura nesta feature e nunca é filtrada pelo usuário autenticado depois que o Quiz foi autorizado.
- Ownership falho retorna `404`, igual a recurso inexistente, para não revelar conteúdo de outra Track.
- A listagem usa o envelope genérico `PaginatedResponse[QuizResponse]`, não um envelope `items` separado.
