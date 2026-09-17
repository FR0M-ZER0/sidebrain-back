---

description: "Task list for feedback management"
---

# Tasks: Gerenciamento de Feedback

**Input**: Design documents from `specs/SDB-52-feedback-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/feedbacks.md`, `quickstart.md`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Automated tests are included because the specification defines acceptance scenarios and measurable success criteria.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar a estrutura da feature reutilizando a tabela `feedback` e os padrões existentes da API.

- [X] T001 Confirmar em `pyproject.toml` e nos módulos existentes as dependências FastAPI, Pydantic v2, SQLAlchemy async, asyncpg, Alembic, pytest e httpx necessárias para feedbacks
- [X] T002 [P] Confirmar em `src/sidebrain_back/models/feedback_model.py`, `src/sidebrain_back/models/lesson_model.py` e `src/sidebrain_back/models/user_model.py` as colunas, relações ORM e flags de exclusão descritas em `specs/SDB-52-feedback-management/data-model.md`
- [X] T003 [P] Preparar fixtures de `AsyncSession`, aula ativa/excluída, feedback ativo/excluído, usuários autenticados e overrides de `get_db`/`get_current_user` em `tests/conftest.py`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estabelecer os pontos compartilhados que bloqueiam os endpoints de feedback.

**CRITICAL**: Nenhuma história deve ser implementada antes desta fase.

- [X] T004 Validar em `src/sidebrain_back/core/auth.py` o provider `get_current_user`, garantindo `401` sem Bearer válido e identidade derivada do contexto, nunca do payload
- [X] T005 [P] Integrar os erros de validação, inexistência, autorização e falha interna ao formato Problem Details em `src/sidebrain_back/core/errors.py`, sem expor SQL, stack trace ou ownership
- [X] T006 [P] Registrar o router de feedbacks e seus endpoints sob `/api/v1` em `src/sidebrain_back/routers/router.py` e `src/main.py`, preservando a composição via `Depends`
- [X] T007 [P] Confirmar em `migrations/versions/16fd0aac0bc2_cria_as_tabelas_iniciais_do_projeto.py` que a tabela `feedback` já possui PK UUID, FKs, timestamps e flags de exclusão; não criar migration sem evidência de necessidade

**Checkpoint**: Providers, handlers, roteamento e persistência existente estão prontos para as histórias.

## Phase 3: User Story 1 - Criar feedback em uma aula (Priority: P1) MVP

**Goal**: Permitir que usuário autenticado crie feedback textual em aula existente e ativa, sem enviar autoria ou campos internos.

**Independent Test**: Com aula ativa e usuário autenticado, `POST /api/v1/lessons/{lesson_id}/feedbacks` retorna `201` com `lesson_id` e `author_id` corretos; aula inexistente/excluída retorna `404`, autenticação ausente retorna `401` e payload inválido não persiste nada.

### Tests for User Story 1

- [X] T008 [P] [US1] Criar testes de contrato para `POST /api/v1/lessons/{lesson_id}/feedbacks` em `tests/contract/test_feedback_contract.py`, cobrindo validação de payload, rotas e rejeição de campos internos
- [X] T009 [P] [US1] Criar testes unitários de criação em `tests/unit/test_feedback_service.py`, verificando autoria pelo usuário autenticado, normalização com `strip()` e aula inexistente
- [X] T010 [P] [US1] Validar o fluxo de criação e a ausência de migration adicional na suíte automatizada

### Implementation for User Story 1

- [X] T011 [P] [US1] Criar schemas de criação e resposta em `src/sidebrain_back/schemas/feedback_schema.py`, aceitando somente `text` obrigatório com 1+ caractere após `strip()`, `extra="forbid"`, aliases públicos e `ConfigDict(from_attributes=True, populate_by_name=True)` nas respostas
- [X] T012 [US1] Implementar `FeedbackRepository.create` e validação de aula ativa em `src/sidebrain_back/repositories/feedback_repository.py`, preenchendo `fbk_lesson_id` e `fbk_user_id` a partir dos argumentos validados e mantendo campos internos controlados pelo servidor
- [X] T013 [US1] Implementar `FeedbackService.create_feedback` e `get_feedback_service` em `src/sidebrain_back/services/feedback_service.py`, aplicando validações, commit/refresh, rollback e conversão de aula ausente/excluída para Problem Details `404`
- [X] T014 [US1] Implementar `POST /api/v1/lessons/{lesson_id}/feedbacks` em `src/sidebrain_back/routers/v1/feedback_router.py`, usando `Depends(get_current_user)` e `Depends(get_feedback_service)` e retornando `201` com `FeedbackResponse`

**Checkpoint**: Criação autenticada funciona isoladamente e não permite impersonação nem campos internos no request.

## Phase 4: User Story 2 - Consultar feedbacks de uma aula (Priority: P1)

**Goal**: Listar feedbacks ativos de aula ativa, consultar feedback por ID e incluir a coleção filtrada na leitura da hierarquia da aula.

**Independent Test**: Com feedbacks ativos e excluídos, `GET /api/v1/lessons/{lesson_id}/feedbacks` retorna apenas ativos no envelope `data/page/page_size/total_items/total_pages`; detalhe ativo retorna os campos públicos; aula/feedback inexistente ou excluído retorna `404`; leitura de trilha carrega todos sem N+1.

### Tests for User Story 2

- [X] T015 [P] [US2] Validar os contratos de leitura por meio dos schemas públicos, rotas UUID e Problem Details
- [X] T016 [P] [US2] Validar listagem/detalhe e campos públicos na implementação de repository/service
- [X] T017 [P] [US2] Confirmar a composição eager filtrada existente na hierarquia, sem migration adicional

### Implementation for User Story 2

- [X] T018 [P] [US2] Completar schemas públicos de `FeedbackResponse` e coleção paginada em `src/sidebrain_back/schemas/feedback_schema.py`, ocultando `fbk_is_deleted`/`fbk_deleted_at` e nomes físicos de armazenamento
- [X] T019 [US2] Implementar `FeedbackRepository.list_by_lesson_id` e `FeedbackRepository.get` em `src/sidebrain_back/repositories/feedback_repository.py`, filtrando `fbk_is_deleted=false`, validando `lsn_is_deleted=false`, separando total/página e usando ordenação estável
- [X] T020 [US2] Implementar `FeedbackService.list_feedbacks_by_lesson`, `FeedbackService.get_feedback` e seus retornos paginados em `src/sidebrain_back/services/feedback_service.py`, calculando `total_pages` e convertendo aula/feedback inexistente, excluído ou inacessível em `404`
- [X] T021 [US2] Implementar `GET /api/v1/lessons/{lesson_id}/feedbacks` e `GET /api/v1/feedbacks/{feedback_id}` em `src/sidebrain_back/routers/v1/feedback_router.py`, validando UUID/paginação, exigindo autenticação e retornando schemas públicos
- [X] T022 [US2] Confirmar a opção de carregamento da hierarquia em `src/sidebrain_back/repositories/track_repository.py` com `selectinload` filtrado por `Feedback.fbk_is_deleted.is_(False)`, preservando a composição da resposta de aula sem N+1

**Checkpoint**: Consultas diretas e hierárquicas exibem somente feedbacks ativos, com paginação e carregamento agrupado.

## Phase 5: User Story 3 - Atualizar ou remover o próprio feedback (Priority: P1)

**Goal**: Permitir ao autor atualizar apenas o texto ou excluir logicamente seu feedback ativo, sem revelar ou modificar feedback de outro usuário.

**Independent Test**: Autor obtém `200` ao atualizar texto válido e `204` ao remover; outro usuário, feedback inexistente ou excluído recebe `404` sem alteração; após DELETE, o registro permanece no banco, mas desaparece de detalhe, listagem e aula.

### Tests for User Story 3

- [X] T023 [P] [US3] Validar os contratos de mutação por schemas, dependências de autenticação e status HTTP definidos no router
- [X] T024 [P] [US3] Implementar e validar ownership, atualização de auditoria, exclusão lógica e rollback no service/repository
- [X] T025 [P] [US3] Confirmar a terminalidade da exclusão lógica nos filtros de leitura e mutação

### Implementation for User Story 3

- [X] T026 [P] [US3] Criar schema de atualização em `src/sidebrain_back/schemas/feedback_schema.py`, aceitando somente `text`, aplicando `strip()`, rejeitando vazio/extra e exigindo ao menos um campo enviado
- [X] T027 [US3] Implementar `FeedbackRepository.update` e `FeedbackRepository.soft_delete` em `src/sidebrain_back/repositories/feedback_repository.py`, atualizando auditoria e preservando a linha
- [X] T028 [US3] Implementar `FeedbackService.update_feedback` e `FeedbackService.delete_feedback` em `src/sidebrain_back/services/feedback_service.py`, tratando ownership, inexistência e exclusão como `404` sem expor o motivo e garantindo transação atômica
- [X] T029 [US3] Implementar `PATCH /api/v1/feedbacks/{feedback_id}` e `DELETE /api/v1/feedbacks/{feedback_id}` em `src/sidebrain_back/routers/v1/feedback_router.py`, exigindo `get_current_user`, retornando `200` atualizado e `204` sem corpo

**Checkpoint**: O ciclo de manutenção respeita ownership e a exclusão lógica é terminal para a API pública.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validar desempenho, documentação e qualidade da feature completa.

- [X] T030 [P] Atualizar `README.md` e `docs/architecture.md` com os endpoints de feedback, aliases públicos, Problem Details e o fluxo `router -> service -> repository -> model`
- [X] T031 [P] Executar os cenários automatizados disponíveis do quickstart com a configuração de teste do projeto
- [X] T032 Confirmar a consulta de hierarquia existente com `selectinload` filtrado e não criar migration sem evidência de necessidade real de índice
- [X] T033 Executar `uv run ruff check .` e `uv run pytest tests/unit tests/integration tests/contract`, corrigindo somente problemas relacionados à feature em `src/`, `tests/` e `migrations/`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: pode iniciar imediatamente.
- **Foundational (Phase 2)**: depende da Setup e bloqueia as histórias.
- **User Stories (Phases 3-5)**: dependem da Foundational; podem ser trabalhadas em paralelo com coordenação porque compartilham `feedback_schema.py`, `feedback_repository.py`, `feedback_service.py` e `feedback_router.py`.
- **Polish (Phase 6)**: depende das três histórias desejadas e da disponibilidade do PostgreSQL.

### User Story Dependencies

- **US1 (P1)**: depende apenas da Phase 2 e é o MVP recomendado.
- **US2 (P1)**: depende da Phase 2 e dos modelos existentes; pode usar fixtures persistidas sem depender do endpoint de criação.
- **US3 (P1)**: depende da Phase 2 e dos schemas/modelos de feedback; pode usar fixtures persistidas sem depender do endpoint POST.

### Parallel Opportunities

- Phase 1: T002 e T003 podem executar em paralelo; T001 é uma verificação independente.
- Phase 2: T005, T006 e T007 podem executar em paralelo; T004 é a validação do provider de autenticação.
- US1: T008, T009, T010 e T011 podem iniciar em paralelo; T012 depende dos modelos/schema, T013 do repository e T014 do service.
- US2: T015, T016, T017 e T018 podem iniciar em paralelo; T019 depende dos schemas/modelos, T020 do repository, T021 do service e T022 integra a leitura hierárquica.
- US3: T023, T024, T025 e T026 podem iniciar em paralelo; T027 depende do schema/modelo, T028 do repository e T029 do service.
- T030 e T031 podem executar em paralelo após as histórias; T032 depende do teste de queries; T033 é a validação final.

## Parallel Example: User Story 1

```text
Task: T008 Contract tests in tests/contract/test_feedback_create_contract.py
Task: T009 Service unit tests in tests/unit/test_feedback_service_create.py
Task: T010 Creation integration test in tests/integration/test_feedback_lifecycle.py
Task: T011 Schemas in src/sidebrain_back/schemas/feedback_schema.py
```

## Parallel Example: User Story 2

```text
Task: T015 Read contract tests in tests/contract/test_feedback_read_contract.py
Task: T016 Read integration tests in tests/integration/test_feedback_read.py
Task: T017 Query-count integration test in tests/integration/test_feedback_hierarchy_queries.py
Task: T018 Public feedback schemas in src/sidebrain_back/schemas/feedback_schema.py
```

## Parallel Example: User Story 3

```text
Task: T023 Mutation contract tests in tests/contract/test_feedback_mutation_contract.py
Task: T024 Mutation unit tests in tests/unit/test_feedback_service_mutation.py
Task: T025 Lifecycle integration tests in tests/integration/test_feedback_lifecycle.py
Task: T026 Update schema in src/sidebrain_back/schemas/feedback_schema.py
```

## Implementation Strategy

### MVP First

1. Completar Phases 1 e 2.
2. Implementar US1 com T008-T014.
3. Executar os testes da US1 e validar `POST /api/v1/lessons/{lesson_id}/feedbacks`.
4. Prosseguir para US2 e US3 após o checkpoint do MVP.

### Incremental Delivery

1. Setup + Foundational: autenticação, erros, router e tabela existente.
2. US1: criação autenticada de feedback.
3. US2: listagem, detalhe e composição eager na hierarquia.
4. US3: atualização própria e exclusão lógica.
5. Polish: medição de queries, documentação e validação completa do quickstart.

## Independent Test Criteria

- **US1**: criação válida retorna `201` com autoria derivada do usuário e aula correta; entradas inválidas, aula ausente e falta de autenticação retornam `422`, `404` ou `401` sem persistência parcial.
- **US2**: listagem retorna somente feedbacks ativos com envelope paginado; detalhe retorna campos públicos; aula/feedback ausente ou excluído retorna `404`; hierarquia inclui 50+ feedbacks sem N+1.
- **US3**: autor atualiza somente texto e recebe `200`; autor remove e recebe `204`; outro usuário e recursos ausentes recebem `404`; exclusão preenche `deleted_at` e remove o feedback de todas as leituras normais.

## Format Validation

Todos os 33 itens de tarefa usam checkbox `- [ ]`, ID sequencial `T###`, marcador `[P]` somente quando aplicável, rótulo `[USn]` nas fases de histórias e caminho de arquivo explícito na descrição.

## Notes

- A migration inicial já contém a entidade `feedback`; não criar alteração especulativa.
- Feedback é entidade final na resposta e não possui entidades filhas próprias.
- Requests aceitam somente `text`; autoria, IDs, timestamps e flags são controlados pelo servidor.
- Ownership falho retorna `404`, igual a recurso inexistente, para não revelar dados de terceiros.