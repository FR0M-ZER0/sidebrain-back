---

description: "Task list for track management"
---

# Tasks: Gerenciamento de Trilhas

**Input**: Design documents from `specs/SDB-49-track-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/tracks.md`, `quickstart.md`

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Automated tests are included because the feature specification defines independent tests, acceptance scenarios, contract behavior, and measurable success criteria.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar a estrutura de implementação e validação da feature sem alterar a migration inicial existente.

- [X] T001 Confirmar as dependências FastAPI, Pydantic, SQLAlchemy async, asyncpg, Alembic, pytest e httpx em `pyproject.toml`, adicionando somente as que estiverem ausentes
- [X] T002 [P] Criar os diretórios `src/sidebrain_back/repositories/`, `src/sidebrain_back/schemas/`, `src/sidebrain_back/services/`, `tests/unit/`, `tests/integration/` e `tests/contract/` com seus arquivos `__init__.py` quando aplicável
- [X] T003 [P] Criar fixtures compartilhadas para `AsyncSession`, usuário autenticado, override de `get_db` e override de `get_current_user` em `tests/conftest.py`

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estabelecer os providers e contratos transversais que bloqueiam todos os endpoints de trilha.

**CRITICAL**: Nenhuma história deve ser implementada antes desta fase.

- [X] T004 Implementar ou integrar o provider `get_current_user` em `src/sidebrain_back/core/auth.py`, retornando `401` sem credencial válida e mantendo a identidade fora do body das requisições
- [X] T005 [P] Implementar exceções e handlers de Problem Details para `400`, `401`, `404`, `422` e `500` em `src/sidebrain_back/core/errors.py`, sem expor SQL, stack trace, credenciais ou ownership
- [X] T006 [P] Implementar o schema reutilizável de paginação em `src/sidebrain_back/schemas/pagination_schema.py` com `page=1`, `page_size=20`, `page >= 1`, `1 <= page_size <= 100`, envelope `data/page/page_size/total_items/total_pages` e `total_pages=0` quando `total_items=0`
- [X] T007 Registrar os handlers, providers e o router versionado na composição da aplicação em `src/main.py` e `src/sidebrain_back/routers/router.py`, preservando o agrupamento `/api/v1`
- [X] T008 [P] Validar a configuração de banco assíncrono e transações em `src/sidebrain_back/core/database.py`, garantindo rollback para falhas de persistência antes da implementação dos serviços

## Phase 3: User Story 1 - Criar uma trilha de aprendizagem (Priority: P1) MVP

**Goal**: Permitir que um usuário autenticado crie uma trilha própria com título obrigatório e descrição opcional.

**Independent Test**: Enviar criação válida com e sem descrição e confirmar `201`, vínculo com o usuário autenticado, identificador e timestamps; enviar título ausente, vazio e acima de 255 caracteres e confirmar `422` sem persistência.

### Tests for User Story 1

- [X] T009 [P] [US1] Criar testes de contrato para `POST /api/v1/tracks` em `tests/contract/test_track_create_contract.py`, cobrindo `201`, `401`, título obrigatório, título vazio, título acima de 255 caracteres e rejeição de `userId`, IDs, auditoria e exclusão lógica no request
- [X] T010 [P] [US1] Criar testes unitários do serviço de criação em `tests/unit/test_track_service_create.py`, verificando ownership derivado do usuário autenticado, normalização do título, descrição nula e rollback em falha de persistência

### Implementation for User Story 1

- [X] T011 [P] [US1] Criar schemas de criação e resposta em `src/sidebrain_back/schemas/track_schema.py`, expondo apenas `title` e `description` no request e aplicando `title` obrigatório com 1 a 255 caracteres após normalização, descrição opcional com `null` permitido e `ConfigDict(from_attributes=True, populate_by_name=True)` nas respostas
- [X] T012 [US1] Implementar `TrackRepository.create` e seu provider com `AsyncSession` em `src/sidebrain_back/repositories/track_repository.py`, preenchendo `trk_user_id` exclusivamente pelo contexto autenticado e iniciando `trk_is_deleted=false` e `trk_deleted_at=null`
- [X] T013 [US1] Implementar `TrackService.create_track` e seu provider em `src/sidebrain_back/services/track_service.py`, aplicando validações, commit/refresh, timestamps e tradução de falhas de persistência para Problem Details sem detalhes internos
- [X] T014 [US1] Implementar `POST /api/v1/tracks` em `src/sidebrain_back/routers/v1/track_router.py`, usando `Depends(get_current_user)` e `Depends(get_track_service)`, retornando `201` com o schema público da trilha

**Checkpoint**: A criação autenticada funciona isoladamente e não permite atribuir a trilha a outro usuário pelo payload.

## Phase 4: User Story 2 - Consultar trilhas próprias (Priority: P1)

**Goal**: Listar trilhas ativas próprias com paginação e consultar uma trilha com toda a hierarquia de conteúdo filtrada.

**Independent Test**: Preparar trilhas para dois usuários, incluindo filhos ativos e excluídos, listar e consultar como cada usuário e confirmar ownership, paginação, `404` para UUID inexistente/excluído/alheio, hierarquia correta e ausência de N+1.

### Tests for User Story 2

- [X] T015 [P] [US2] Criar testes de contrato para `GET /api/v1/tracks` e `GET /api/v1/tracks/{track_id}` em `tests/contract/test_track_read_contract.py`, cobrindo envelope paginado, parâmetros inválidos, UUID malformado `422`, recurso ausente/alheio/excluído `404` e Problem Details
- [X] T016 [P] [US2] Criar testes de integração da listagem e detalhe em `tests/integration/test_track_read.py`, verificando somente trilhas próprias ativas, `total_items`, `total_pages`, ordenação por `trk_created_at DESC, trk_id DESC` e resposta vazia consistente
- [X] T017 [P] [US2] Criar teste de integração da árvore completa e contagem de queries em `tests/integration/test_track_hierarchy_queries.py`, verificando Step -> Lesson/Mission -> LessonFile/Feedback/Quiz/Answer/MissionProgress, filtros de exclusão e progresso apenas do usuário atual, com consultas agrupadas e não proporcionais a cada filho

### Implementation for User Story 2

- [X] T018 [P] [US2] Completar schemas públicos da hierarquia em `src/sidebrain_back/schemas/track_schema.py` para `Track`, `Step`, `Lesson`, `LessonFile`, `Feedback`, `Quiz`, `Answer`, `Mission` e `MissionProgress`, ocultando `is_deleted`/`deleted_at` dos filhos e usando nomes públicos sem prefixos físicos
- [X] T019 [US2] Implementar `TrackRepository.list` e `TrackRepository.get` em `src/sidebrain_back/repositories/track_repository.py` com filtros `track.user_id = current_user.id` e `track.is_deleted = false`, `count` separado, `limit/offset`, ordenação estável e `selectinload` aninhado com critérios de exclusão em cada relação e `progress.user_id = current_user.id`
- [X] T020 [US2] Implementar `TrackService.list_tracks` e `TrackService.get_track` em `src/sidebrain_back/services/track_service.py`, calculando `ceil(total_items / page_size)`, preservando metadados para coleção vazia e convertendo trilha inexistente, excluída ou de outro usuário em `404`
- [X] T021 [US2] Implementar `GET /api/v1/tracks` e `GET /api/v1/tracks/{track_id}` em `src/sidebrain_back/routers/v1/track_router.py`, validando UUID e paginação antes da consulta e retornando os schemas da árvore sem acessar models/repositories diretamente

**Checkpoint**: A consulta isolada entrega apenas dados do usuário autenticado, carrega a árvore sem N+1 e não revela a existência de recursos de terceiros.

## Phase 5: User Story 3 - Atualizar e excluir uma trilha (Priority: P1)

**Goal**: Permitir atualização parcial e exclusão lógica de trilhas ativas próprias.

**Independent Test**: Criar uma trilha, atualizar título e/ou descrição, confirmar `200` e auditoria, excluir, confirmar `204`, `deleted_at` preenchido e ausência posterior; validar `422` para payload inválido e `404` para recurso inexistente, excluído ou alheio.

### Tests for User Story 3

- [X] T022 [P] [US3] Criar testes de contrato para `PATCH /api/v1/tracks/{track_id}` e `DELETE /api/v1/tracks/{track_id}` em `tests/contract/test_track_mutation_contract.py`, cobrindo ao menos um campo no PATCH, título vazio/acima de 255, `404`, `200`, `204` sem body e Problem Details
- [X] T023 [P] [US3] Criar testes unitários de atualização e exclusão em `tests/unit/test_track_service_mutation.py`, verificando preservação de valores quando campos não são enviados, `trk_updated_at`, transição `is_deleted=false -> true`, `deleted_at=now()` e rollback
- [X] T024 [P] [US3] Criar teste de integração do ciclo de vida em `tests/integration/test_track_lifecycle.py`, confirmando que a trilha excluída permanece no banco, mas não aparece em listagem/detalhe e não pode ser atualizada ou excluída novamente

### Implementation for User Story 3

- [X] T025 [US3] Completar o schema PATCH em `src/sidebrain_back/schemas/track_schema.py`, aceitando somente `title` e `description`, exigindo ao menos um campo, rejeitando título vazio quando enviado e preservando o valor anterior quando omitido
- [X] T026 [US3] Implementar `TrackRepository.update` e `TrackRepository.soft_delete` em `src/sidebrain_back/repositories/track_repository.py`, filtrando por ownership e estado ativo, atualizando auditoria e marcando exclusão lógica sem apagar fisicamente o registro
- [X] T027 [US3] Implementar `TrackService.update_track` e `TrackService.delete_track` em `src/sidebrain_back/services/track_service.py`, traduzindo ausência para `404`, validando payload antes da alteração e convertendo falhas para Problem Details com rollback
- [X] T028 [US3] Implementar `PATCH /api/v1/tracks/{track_id}` e `DELETE /api/v1/tracks/{track_id}` em `src/sidebrain_back/routers/v1/track_router.py`, usando autenticação central, retornando `200` atualizado e `204` sem corpo respectivamente

**Checkpoint**: O ciclo de manutenção funciona isoladamente e a exclusão lógica é terminal para esta API.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validar desempenho, documentação e qualidade da implementação completa.

- [X] T029 [P] Medir a consulta da árvore e revisar o plano de execução em `tests/integration/test_track_hierarchy_queries.py`; criar migration adicional em `migrations/versions/<revision>_add_track_read_indexes.py` somente se a medição justificar índices para `(trk_user_id, trk_is_deleted, trk_created_at)` ou FKs da árvore
- [X] T030 [P] Atualizar a documentação de endpoints e exemplos de Problem Details em `README.md` e `docs/architecture.md`, mantendo a separação `router -> service -> repository -> model`
- [X] T031 Executar os cenários do quickstart em `specs/SDB-49-track-management/quickstart.md` com PostgreSQL, registrando qualquer ajuste necessário nos testes da feature
- [X] T032 Executar `uv run ruff check .` e `uv run pytest tests/unit tests/integration tests/contract` e corrigir somente problemas relacionados à feature em `src/`, `tests/` e `migrations/`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: pode iniciar imediatamente.
- **Foundational (Phase 2)**: depende da Setup e bloqueia todas as histórias.
- **User Stories (Phases 3-5)**: dependem da Foundational; podem ser paralelizadas depois dela, embora compartilhem `track_schema.py`, `track_repository.py`, `track_service.py` e `track_router.py`, que devem ser integrados sem sobrescrita.
- **Polish (Phase 6)**: depende das três histórias desejadas e da disponibilidade do PostgreSQL.

### User Story Dependencies

- **US1 (P1)**: depende apenas da Phase 2; é o MVP recomendado.
- **US2 (P1)**: depende da Phase 2 e dos schemas/modelos ORM existentes; pode ser implementada sem depender funcionalmente do endpoint de criação usando fixtures de banco.
- **US3 (P1)**: depende da Phase 2 e do contrato/schema da trilha; pode ser testada com fixtures de banco sem depender do endpoint POST.

### Parallel Opportunities

- Phase 1: T002 e T003 podem executar em paralelo; T001 é uma verificação independente.
- Phase 2: T005, T006 e T008 podem executar em paralelo; T004 e T007 integram os providers na aplicação.
- US1: T009, T010 e T011 podem iniciar em paralelo; T012 depende do schema/modelo; T013 depende do repository; T014 depende do service.
- US2: T015, T016, T017 e T018 podem iniciar em paralelo; T019 depende dos schemas/modelos; T020 depende do repository; T021 depende do service.
- US3: T022, T023, T024 e T025 podem iniciar em paralelo; T026 depende do schema/modelo; T027 depende do repository; T028 depende do service.
- As três histórias podem ser atribuídas a implementadores diferentes após a Phase 2, coordenando os arquivos compartilhados.

## Parallel Example: User Story 1

```text
Task: T009 Contract tests in tests/contract/test_track_create_contract.py
Task: T010 Service unit tests in tests/unit/test_track_service_create.py
Task: T011 Schemas in src/sidebrain_back/schemas/track_schema.py
```

## Parallel Example: User Story 2

```text
Task: T015 Read contract tests in tests/contract/test_track_read_contract.py
Task: T016 Pagination integration tests in tests/integration/test_track_read.py
Task: T017 Hierarchy/query-count tests in tests/integration/test_track_hierarchy_queries.py
Task: T018 Hierarchy schemas in src/sidebrain_back/schemas/track_schema.py
```

## Parallel Example: User Story 3

```text
Task: T022 Mutation contract tests in tests/contract/test_track_mutation_contract.py
Task: T023 Mutation service tests in tests/unit/test_track_service_mutation.py
Task: T024 Lifecycle integration tests in tests/integration/test_track_lifecycle.py
Task: T025 PATCH schema in src/sidebrain_back/schemas/track_schema.py
```

## Implementation Strategy

### MVP First

1. Completar Phases 1 e 2.
2. Implementar US1 com T009-T014.
3. Executar os testes da US1 e validar o endpoint `POST /api/v1/tracks`.
4. Prosseguir para US2 e US3 somente após o checkpoint do MVP.

### Incremental Delivery

1. Setup + Foundational: autenticação, erros, paginação e composição da API.
2. US1: criação autenticada de trilhas.
3. US2: listagem e leitura da árvore hierárquica.
4. US3: atualização e exclusão lógica.
5. Polish: medição de queries, documentação e validação completa do quickstart.

## Independent Test Criteria

- **US1**: criação válida retorna `201` e ownership/timestamps; entradas inválidas retornam `422` sem persistência.
- **US2**: listagem retorna somente trilhas próprias ativas com metadados consistentes; detalhe retorna a hierarquia filtrada e `404` para inexistente/alheia/excluída; quantidade de queries não cresce por filho.
- **US3**: PATCH válido retorna `200` e preserva dados omitidos; PATCH inválido retorna `422`; DELETE retorna `204`, preenche `deleted_at` e remove a trilha de leituras posteriores.

## Format Validation

Todos os 32 itens de tarefa usam checkbox `- [ ]`, ID sequencial `T###`, marcador `[P]` somente quando aplicável, rótulo `[USn]` nas fases de histórias e caminho de arquivo explícito na descrição.

## Notes

- A migration inicial já contém a hierarquia necessária; não criar alteração especulativa.
- Filhos são somente leitura nesta feature.
- O PATCH usa `PATCH`, não `PUT`, para atualização parcial.
- Ownership falho retorna `404`, igual a recurso inexistente, para não revelar dados de outros usuários.
