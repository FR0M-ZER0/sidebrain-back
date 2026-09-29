---

description: "Lista de tarefas para implementar o gerenciamento de lições"
---

# Tasks: Gerenciamento de Lições

**Input**: Design documents from `specs/SDB-57-lesson-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/lessons.md`, `quickstart.md`

**Tests**: Obrigatórios porque a especificação define cenários de aceite, atomicidade, contratos públicos, hierarquia sem N+1 e metas mensuráveis de desempenho, e a constituição exige cobertura unitária, de contrato e de integração.

**Organization**: As tarefas estão agrupadas por história de usuário para permitir implementação e validação independente de cada incremento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo quando atua em arquivos diferentes e não depende de tarefa incompleta.
- **[Story]**: História de usuário correspondente (`US1`, `US2` ou `US3`).
- Toda tarefa possui caminho de arquivo explícito.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar a base persistente existente e preparar fixtures PostgreSQL reutilizáveis sem alterar o schema.

- [X] T001 Auditar versões, relacionamentos, enums, soft delete e a constraint existente `UNIQUE (lsn_step_id, lsn_position)` em `pyproject.toml`, `src/sidebrain_back/models/lesson_model.py`, `src/sidebrain_back/models/step_model.py`, `src/sidebrain_back/models/track_model.py`, `src/sidebrain_back/models/feedback_model.py`, `src/sidebrain_back/models/lesson_file_model.py`, `src/sidebrain_back/models/quiz_model.py`, `src/sidebrain_back/models/answer_model.py` e `migrations/versions/16fd0aac0bc2_cria_as_tabelas_iniciais_do_projeto.py`, registrando no changeset que a SDB-57 não requer migration
- [X] T002 [P] Ampliar `tests/conftest.py` com factories assíncronas para múltiplos Steps e Lessons, Feedback/LessonFile/Quiz ativos ou removidos e Answer, mantendo overrides de `get_db`/`get_current_user`, isolamento transacional e suporte a criação em lote sem um `flush` por filho

**Checkpoint**: Modelo, dependências e infraestrutura de teste estão confirmados sem migration especulativa.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implementar contratos, autorização hierárquica e pontos de extensão compartilhados pelas três histórias.

**CRITICAL**: Nenhuma história deve ser implementada antes desta fase.

- [X] T003 [P] Criar testes falhando dos schemas em `tests/unit/test_lesson_schema.py`, cobrindo literalmente `title: trim antes da validação; 1–255`, `text: trim antes da validação; não vazio`, `position: >= 1`, criação somente com `title/text/position`, PUT completo com `title/text/status/position`, estados `idle|in_progress|done`, `extra="forbid"`, aliases públicos e coleções com `default_factory=list`
- [X] T004 Implementar `LessonCreateRequest`, `LessonUpdateRequest`, `LessonResponse`, `LessonFeedbackResponse`, `LessonFileResponse`, `LessonQuizResponse` e `LessonAnswerResponse` em `src/sidebrain_back/schemas/lesson_schema.py`, satisfazendo T003 com `ConfigDict(from_attributes=True, populate_by_name=True)`, coleção pública `files` mapeada de `lesson_files` e nenhum nome físico, relacionamento, timestamp controlável ou flag de exclusão nos requests
- [X] T005 [P] Criar `LessonRepository` e `get_lesson_repository` em `src/sidebrain_back/repositories/lesson_repository.py`, com `get_accessible_step`, `get`, `position_exists` e `_hierarchy_options` compartilhados: ownership por `Step -> Track`, pais/Lesson ativos, conflito incluindo Lessons removidas, exclusão da própria Lesson no update e `selectinload` filtrado para Feedback, LessonFile e Quiz com Answers aninhadas
- [X] T006 Criar `LessonService` e `get_lesson_service` em `src/sidebrain_back/services/lesson_service.py`, injetando `LessonRepository` e `AsyncSession` por `Depends`, centralizando `_require_step`, `_require_lesson`, conflito `409`, `404` uniforme e rollback de `ProblemDetailError`, `IntegrityError` e falhas inesperadas sem expor SQL
- [X] T007 Criar o router base em `src/sidebrain_back/routers/v1/lesson_router.py` e registrá-lo em `src/sidebrain_back/routers/router.py`, preservando o prefixo efetivo `/api/v1`, `Depends(get_current_user)`, `Depends(get_lesson_service)` e os handlers globais de Problem Details

**Checkpoint**: Schemas, DI, autorização, regra compartilhada de posição e roteamento estão disponíveis para todas as histórias.

---

## Phase 3: User Story 1 - Criar lição em uma etapa própria (Priority: P1) MVP

**Goal**: Permitir que um usuário autenticado crie uma Lesson válida somente em um Step ativo de uma Track própria, com estado inicial `idle` e posição não reservada.

**Independent Test**: Com um Step ativo próprio, `POST /api/v1/steps/{step_id}/lessons` com título, texto e posição válidos retorna `201`, vínculo derivado da URL, status `idle` e `feedbacks/files/quizzes=[]`; Step/pai indisponível retorna `404`, posição ocupada retorna `409` e payload ou autenticação inválida retorna `422`/`401` sem persistência parcial.

### Tests for User Story 1

> Escrever e executar estes testes primeiro, confirmando que falham antes da implementação.

- [X] T008 [P] [US1] Criar testes de contrato do `POST /api/v1/steps/{step_id}/lessons` em `tests/contract/test_lesson_contract.py`, cobrindo `201`, `401`, UUID inválido, Problem Details `404`/`409`/`422`, status inicial `idle`, listas vazias e rejeição de `step_id`, `status`, IDs, filhos, timestamps e flags no body
- [X] T009 [P] [US1] Criar testes unitários de `LessonService.create_lesson` em `tests/unit/test_lesson_service.py`, comprovando uso do Step da URL, normalização de título/texto, validação de ownership, pré-checagem de posição, mapeamento concorrente de `IntegrityError`/SQLSTATE `23505` para `409`, resposta antes do commit e rollback sem alteração parcial
- [X] T010 [P] [US1] Criar testes PostgreSQL da criação em `tests/integration/test_lesson_lifecycle.py`, validando FK para Step, defaults `lsn_status=idle`, `lsn_is_deleted=false`, `lsn_deleted_at=null`, mesma posição permitida em Steps diferentes, constraint concorrente no mesmo Step e recusa quando Track ou Step está removido ou pertence a outro usuário

### Implementation for User Story 1

- [X] T011 [US1] Implementar `LessonRepository.create` em `src/sidebrain_back/repositories/lesson_repository.py`, recebendo `step_id` autorizado e `title/text/position`, inicializando status `idle`, soft delete falso e coleções vazias, adicionando e fazendo `flush()` sem commit nem criação de filhos
- [X] T012 [US1] Implementar `LessonService.create_lesson` em `src/sidebrain_back/services/lesson_service.py`, exigindo Step acessível, verificando posição inclusive entre removidas, criando/materializando `LessonResponse` antes do commit, convertendo violação única concorrente em `409` e demais falhas em `500` sanitizado após rollback
- [X] T013 [US1] Implementar `POST /v1/steps/{step_id}/lessons` com `status.HTTP_201_CREATED` e `response_model=LessonResponse` em `src/sidebrain_back/routers/v1/lesson_router.py`, obtendo `step_id` somente do path e exigindo usuário autenticado
- [X] T014 [US1] Executar os testes focados de criação em `tests/unit/test_lesson_schema.py`, `tests/unit/test_lesson_service.py`, `tests/contract/test_lesson_contract.py` e `tests/integration/test_lesson_lifecycle.py`, confirmando que US1 passa isoladamente

**Checkpoint**: A criação autenticada funciona como MVP, preserva a atomicidade e não permite controlar o relacionamento ou campos internos.

---

## Phase 4: User Story 2 - Consultar lições e conteúdo relacionado (Priority: P1)

**Goal**: Listar e consultar Lessons ativas com paginação, ordem por posição e árvore filtrada de Feedbacks, Files, Quizzes e Answers sem N+1.

**Independent Test**: Com um Step próprio contendo Lessons ativas/removidas e filhos ativos/removidos, a lista e o detalhe retornam somente recursos visíveis, árvore correta e listas vazias quando aplicável; página além do total é vazia, pais/ownership inválidos retornam `404`, e a contagem SQL permanece constante entre 1 e 50 Lessons.

### Tests for User Story 2

> Escrever e executar estes testes primeiro, confirmando que falham antes da implementação.

- [X] T015 [P] [US2] Ampliar `tests/contract/test_lesson_contract.py` com contratos para `GET /api/v1/steps/{step_id}/lessons` e `GET /api/v1/lessons/{lesson_id}`, cobrindo `401`, UUID/paginação inválidos, `page=1`, `page_size=20`, limite 1–100, envelope `data/page/page_size/total_items/total_pages`, `files` sem `lesson_files` e ausência de nomes físicos/campos internos
- [X] T016 [P] [US2] Ampliar `tests/unit/test_lesson_service.py` com `list_lessons_by_step_id` e `get_lesson`, cobrindo cálculo de offset, `total_pages`, coleção/página vazia, conversão hierárquica para `LessonResponse` e `404` uniforme para Step/Lesson inexistente, removido, sob pai removido ou alheio
- [X] T017 [P] [US2] Criar testes PostgreSQL de leitura em `tests/integration/test_lesson_lifecycle.py`, cobrindo ordem `lsn_position ASC`, paginação da raiz, filtros de Track/Step/Lesson, omissão de Feedback/LessonFile/Quiz removido, inclusão de todas as Answers do Quiz ativo, associação sem duplicações e coleções vazias
- [X] T018 [P] [US2] Criar `test_lesson_list_sc007_latency_and_sc008_constant_query_count` em `tests/integration/test_lesson_hierarchy_queries.py`, com banco PostgreSQL dedicado, Bearer real, sessão nova por request, carga em lote de 50 Lessons × 5 Feedbacks × 3 Files × 5 Quizzes × 10 Answers, validação do payload, 5 aquecimentos, 100 requests sequenciais, p95 <= 2 s e statements `> 0` e iguais entre 1 e 50 Lessons
- [X] T019 [P] [US2] Ampliar `tests/contract/test_track_read_contract.py` e `tests/contract/test_step_contract.py` para provar que hierarquias superiores continuam ocultando Lesson/filhos removidos e preservam o nome histórico `lesson_files`, enquanto o novo contrato direto em `tests/contract/test_lesson_contract.py` usa `files`

### Implementation for User Story 2

- [X] T020 [US2] Implementar `LessonRepository.list_by_step_id` e completar `LessonRepository.get` em `src/sidebrain_back/repositories/lesson_repository.py`, usando count separado, `offset`/`limit`, `lsn_is_deleted=false`, ordem `lsn_position ASC`, filtros de ownership/pais e eager loading agrupado de Feedback, LessonFile, Quiz e Answer sem paginação dos filhos
- [X] T021 [US2] Implementar `LessonService.list_lessons_by_step_id` e `LessonService.get_lesson` em `src/sidebrain_back/services/lesson_service.py`, validando o Step antes da lista vazia, reutilizando `PaginatedResponse.build`, materializando toda a árvore e retornando `404` sem revelar existência, exclusão ou ownership
- [X] T022 [US2] Implementar `GET /v1/steps/{step_id}/lessons` e `GET /v1/lessons/{lesson_id}` em `src/sidebrain_back/routers/v1/lesson_router.py`, com `page >= 1`, `1 <= page_size <= 100`, `PaginatedResponse[LessonResponse]` e autenticação obrigatória
- [X] T023 [US2] Executar os testes focados de leitura em `tests/unit/test_lesson_service.py`, `tests/contract/test_lesson_contract.py`, `tests/contract/test_track_read_contract.py`, `tests/contract/test_step_contract.py`, `tests/integration/test_lesson_lifecycle.py` e `tests/integration/test_lesson_hierarchy_queries.py`, confirmando US2 isoladamente com PostgreSQL e sem N+1

**Checkpoint**: Lista, detalhe e hierarquias superiores exibem somente conteúdo autorizado e visível, com contrato compatível e custo SQL constante.

---

## Phase 5: User Story 3 - Atualizar ou remover uma lição (Priority: P2)

**Goal**: Substituir todos os campos editáveis de uma Lesson própria e aplicar soft delete terminal sem reordenação nem alteração dos filhos.

**Independent Test**: `PUT /api/v1/lessons/{lesson_id}` exige os quatro campos, permite qualquer transição de status e rejeita posição reservada sem alterar outras Lessons; `DELETE` retorna `204`, preserva fisicamente Lesson/filhos, mantém a posição reservada e torna o recurso indisponível em leituras e mutações posteriores.

### Tests for User Story 3

> Escrever e executar estes testes primeiro, confirmando que falham antes da implementação.

- [X] T024 [P] [US3] Ampliar `tests/contract/test_lesson_contract.py` com contratos para `PUT /api/v1/lessons/{lesson_id}` e `DELETE /api/v1/lessons/{lesson_id}`, cobrindo `200`, `204` sem body, `401`, `404`, `409`, `422`, PUT obrigatoriamente com `title/text/status/position` e rejeição de Step, IDs, filhos, timestamps, flags e campos extras
- [X] T025 [P] [US3] Ampliar `tests/unit/test_lesson_service.py` com update/delete, cobrindo qualquer transição entre `idle|in_progress|done`, posição atual permitida, posição de outra Lesson rejeitada, ausência de reordenação, preservação do Step/filhos, resposta antes do commit, mesmo instante em `updated_at/deleted_at` e rollback em falhas
- [X] T026 [P] [US3] Ampliar `tests/integration/test_lesson_lifecycle.py` para provar PUT completo e atômico, posição reservada por Lesson removida, soft delete terminal, linha de Lesson e filhos fisicamente preservados, ausência de `ON DELETE CASCADE`, invisibilidade imediata em lista/detalhe/hierarquias superiores e `404` nas operações repetidas

### Implementation for User Story 3

- [X] T027 [US3] Implementar `LessonRepository.update` e `LessonRepository.delete` em `src/sidebrain_back/repositories/lesson_repository.py`, substituindo somente `lsn_title/lsn_text/lsn_status/lsn_position`, atualizando `lsn_updated_at` em UTC sem timezone e, no delete, definindo `lsn_is_deleted=true` com `lsn_deleted_at=lsn_updated_at`, sem `session.delete()` nem mutação de filhos
- [X] T028 [US3] Implementar `LessonService.update_lesson` e `LessonService.delete_lesson` em `src/sidebrain_back/services/lesson_service.py`, reutilizando o get autorizado, verificando posição com exclusão da própria Lesson, mapeando conflito preventivo/concorrente para `409`, materializando o response antes do commit no PUT e fazendo rollback com `500` sanitizado
- [X] T029 [US3] Implementar `PUT /v1/lessons/{lesson_id}` com `LessonUpdateRequest`/`LessonResponse` e `DELETE /v1/lessons/{lesson_id}` com `status.HTTP_204_NO_CONTENT` em `src/sidebrain_back/routers/v1/lesson_router.py`, sempre exigindo autenticação e sem corpo no DELETE
- [X] T030 [US3] Executar os testes focados de mutação em `tests/unit/test_lesson_schema.py`, `tests/unit/test_lesson_service.py`, `tests/contract/test_lesson_contract.py` e `tests/integration/test_lesson_lifecycle.py`, confirmando US3 isoladamente e a preservação física dos filhos

**Checkpoint**: O CRUD completo de Lesson está funcional, com PUT integral, posição protegida e soft delete terminal sem perda de dados.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidar documentação, compatibilidade, desempenho e gates de qualidade da feature completa.

- [X] T031 [P] Documentar os cinco endpoints, paginação, `files` no response direto, compatibilidade de `lesson_files` nas hierarquias existentes, conflito `409`, `404` de ownership e fluxo `router -> service -> repository -> model` em `README.md` e `docs/architecture.md`, referenciando `specs/SDB-57-lesson-management/contracts/lessons.md`
- [X] T032 [P] Revisar `src/sidebrain_back/repositories/lesson_repository.py`, `src/sidebrain_back/services/lesson_service.py`, `src/sidebrain_back/schemas/lesson_schema.py` e `src/sidebrain_back/routers/v1/lesson_router.py` contra `docs/architecture.md` e `docs/code_conventions.md`, removendo duplicação acidental e confirmando providers junto às classes e métodos `list_by_step_id/get/create/update/delete`
- [X] T033 Executar integralmente `specs/SDB-57-lesson-management/quickstart.md` e registrar `sc007_p95_seconds`, `sc008_query_count_one_lesson` e `sc008_query_count_fifty_lessons` em `.pytest_cache/lesson-benchmark.xml`, sem criar índice ou migration sem `EXPLAIN (ANALYZE, BUFFERS)` que demonstre necessidade
- [X] T034 Executar os gates finais de `pyproject.toml` com `uv run ruff check .` e `uv run pytest`, corrigindo somente regressões relacionadas à SDB-57 em `src/sidebrain_back/`, `tests/`, `README.md`, `docs/architecture.md` e `specs/SDB-57-lesson-management/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: inicia imediatamente; T001 e T002 podem avançar em paralelo.
- **Foundational (Phase 2)**: depende da Setup e bloqueia todas as histórias. T003 e T005 podem iniciar em paralelo; T004 depende de T003, T006 depende de T005 e T007 depende dos providers.
- **US1, US2 e US3 (Phases 3–5)**: dependem da Foundational. São testáveis com fixtures persistidas sem depender funcionalmente dos endpoints de outra história, mas alterações simultâneas nos quatro módulos de Lesson exigem coordenação.
- **Polish (Phase 6)**: depende das histórias incluídas no release e de PostgreSQL 16 dedicado disponível.

### User Story Dependencies

- **US1 (P1)**: depende somente da Phase 2 e constitui o MVP recomendado.
- **US2 (P1)**: depende somente da Phase 2; suas fixtures criam a árvore diretamente, portanto não depende do POST da US1.
- **US3 (P2)**: depende dos métodos compartilhados de acesso da Phase 2; suas fixtures persistem Lesson/filhos diretamente, portanto não depende funcionalmente da US1 ou US2.
- **Ordem de integração recomendada**: US1 -> US2 -> US3, reduzindo conflitos em `lesson_repository.py`, `lesson_service.py`, `lesson_schema.py` e `lesson_router.py`.

### Within Each User Story

- Os testes devem ser escritos e observados falhando antes da implementação correspondente.
- Repository precede Service; Service precede Router.
- A constraint do banco permanece a autoridade final sobre posição em operações concorrentes.
- Responses de mutação com body são materializados antes do commit.
- O checkpoint da história deve passar antes de integrar o incremento seguinte.

### Dependency Graph

```text
Phase 1 Setup
    -> Phase 2 Foundational
        -> US1 Create (MVP)
        -> US2 Read + hierarchy + performance
        -> US3 Update + soft delete
US1 + US2 + US3
    -> Phase 6 Polish
```

## Parallel Opportunities

- Setup: T002 pode avançar enquanto T001 audita dependências e persistência.
- Foundational: T003 e T005 atuam em arquivos diferentes; T004 depende de T003, T006 de T005 e T007 de T006.
- US1: T008, T009 e T010 podem ser escritos em paralelo; depois T011 -> T012 -> T013 -> T014.
- US2: T015, T016, T017, T018 e T019 podem ser escritos em paralelo; depois T020 -> T021 -> T022 -> T023.
- US3: T024, T025 e T026 podem ser escritos em paralelo; depois T027 -> T028 -> T029 -> T030.
- Polish: T031 e T032 podem avançar em paralelo; T033 precede T034.

## Parallel Example: User Story 1

```text
Task T008: POST contracts in tests/contract/test_lesson_contract.py
Task T009: Creation service tests in tests/unit/test_lesson_service.py
Task T010: Creation persistence tests in tests/integration/test_lesson_lifecycle.py
```

## Parallel Example: User Story 2

```text
Task T015: GET contracts in tests/contract/test_lesson_contract.py
Task T016: Read service tests in tests/unit/test_lesson_service.py
Task T017: Filtering and hierarchy tests in tests/integration/test_lesson_lifecycle.py
Task T018: Query count and p95 in tests/integration/test_lesson_hierarchy_queries.py
Task T019: Compatibility in tests/contract/test_track_read_contract.py and tests/contract/test_step_contract.py
```

## Parallel Example: User Story 3

```text
Task T024: Mutation contracts in tests/contract/test_lesson_contract.py
Task T025: Mutation service tests in tests/unit/test_lesson_service.py
Task T026: Atomicity and soft delete in tests/integration/test_lesson_lifecycle.py
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar T001–T007 (Setup e Foundational).
2. Implementar T008–T014 (US1).
3. Parar e validar a criação autenticada independentemente.
4. Demonstrar `POST /api/v1/steps/{step_id}/lessons` antes de ampliar o CRUD.

### Incremental Delivery

1. Setup + Foundational: fixtures, schemas, ownership, conflito, DI e router.
2. US1: criação autenticada e concorrência de posição.
3. US2: lista, detalhe, filhos filtrados, compatibilidade e ausência de N+1.
4. US3: PUT completo e soft delete terminal.
5. Polish: documentação, benchmark, lint e regressão completa.

### Independent Test Criteria

- **US1**: POST válido retorna `201`, usa o Step da URL, status `idle` e listas vazias; Step/pai indisponível ou alheio retorna `404`; posição ocupada retorna `409`; entrada/autenticação inválida retorna `422`/`401` sem persistência parcial.
- **US2**: lista paginada retorna somente Lessons ativas por posição crescente; detalhe e lista incluem exatamente Feedbacks/Files/Quizzes ativos e todas as Answers correspondentes; o response direto usa `files`, hierarquias anteriores preservam `lesson_files`, e o protocolo SC-007/SC-008 comprova p95 <= 2 s e contagem SQL constante.
- **US3**: PUT exige e substitui `title/text/status/position`, permite qualquer transição válida sem reordenar; DELETE retorna `204`, preserva Lesson/filhos, mantém a posição reservada e torna a Lesson indisponível em leituras e mutações posteriores.

## Summary

- **Total task count**: 34
- **Task count per user story**: US1 = 7, US2 = 9, US3 = 7
- **Setup/Foundational/Polish**: 11 tarefas compartilhadas
- **Parallel opportunities identified**: 16 tarefas marcadas `[P]`, com grupos paralelos em todas as fases
- **Suggested MVP scope**: T001–T014, encerrando após User Story 1
- **Format validation target**: todos os 34 itens usam checkbox `- [ ]`, ID sequencial `T###`, `[P]` somente quando aplicável, `[USn]` somente nas fases de histórias e pelo menos um caminho de arquivo explícito

## Notes

- A migration inicial já contém a constraint única que reserva a posição após soft delete; não alterar seu histórico.
- `position >= 1` e strings normalizadas/não vazias são garantidas pela aplicação, não por `CHECK` no banco.
- Answer não possui soft delete; depois que a Lesson é autorizada, todas as Answers dos Quizzes ativos são retornadas.
- O novo contrato direto usa `files`; `lesson_files` permanece nos contratos já publicados por Track/Step nesta versão.
- Ownership incompatível retorna `404`, igual a recurso inexistente ou removido, para não revelar conteúdo de outra Track.
