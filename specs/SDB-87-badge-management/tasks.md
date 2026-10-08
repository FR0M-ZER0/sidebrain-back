---

description: "Task list for badge catalog management"
---

# Tasks: Gerenciamento de Badges

**Input**: Design documents from `specs/SDB-87-badge-management/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Organization**: As tarefas estão agrupadas por história de usuário para permitir implementação e validação independentes. A implementação segue `routers -> services -> repositories -> models` e os contratos públicos não expõem `bdg_*` nem `bpg_*`.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar a base de testes e os contratos para a feature sem alterar regras de domínio.

- [X] T001 [P] Revisar os fixtures de autenticação e payloads de badge em `tests/conftest.py` e `tests/contract/`, garantindo usuário autenticado válido e dados de criação consistentes com `spec.md`.
- [X] T002 [P] Registrar os cenários de contrato de `POST`, `GET`, `PATCH` e `DELETE /api/v1/badges` em `tests/contract/test_badge_contract.py`, cobrindo `401`, `404`, `409`, `422`, `201`, `200` e `204`.
- [X] T003 [P] Documentar os comandos de execução e validação da feature em `specs/SDB-87-badge-management/quickstart.md` e `README.md`, incluindo `uv run pytest ...` e `uv run ruff check .`.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Criar os contratos e operações compartilhadas que bloqueiam as três histórias.

- [X] T004 [P] Confirmar os enums de raridade e critério em `src/sidebrain_back/enums/badge_rarity_enum.py`, `src/sidebrain_back/enums/badge_criteria_enum.py` e `src/sidebrain_back/enums/badge_progress_status_enum.py`, alinhando `common|rare|epic|legendary`, `xp_gained|tracks_completed|lessons_completed|right_answers|day_streak|tracks_created|missions_completed` e `idle|in_progress|done`.
- [X] T005 [P] Definir schemas públicos de criação, atualização e resposta em `src/sidebrain_back/schemas/badge_schema.py`, com `name`, `description`, `rarity`, `criteria`, `criteria_value`, `updated_at`, `progress` e `from_attributes=True`, sem expor campos físicos ou flags internas.
- [X] T006 [P] Definir os modelos de erro e problemas públicos em `src/sidebrain_back/core/errors.py`, padronizando `Problem Details` para `401`, `404`, `409`, `422` e `500` e preservando mensagens sem stack trace.
- [X] T007 Criar ou alinhar o repositório de badge em `src/sidebrain_back/repositories/badge_repository.py` para criar, consultar ativos, listar paginado, atualizar e soft delete sem `delete()` físico, validando unicidade ativa por `lower(trim(name))`.
- [X] T008 Criar o service de badge em `src/sidebrain_back/services/badge_service.py` com normalização de nome, `criteria_value > 0`, validação de raridade/critério, paginação com `page >= 1` e `page_size <= 100`, carregamento de progresso do usuário autenticado e soft delete.

**Checkpoint**: schemas, erros e persistência de badge estão disponíveis; as histórias podem ser implementadas sem expor colunas físicas nem quebrar a arquitetura de camadas.

## Phase 3: User Story 1 - Criar um badge no catálogo (Priority: P1) 🎯 MVP

**Goal**: Cadastrar um badge global autenticado, normalizar o nome e devolver o badge com `progress: []` sem expor campos internos.

**Independent Test**: Enviar um payload válido para `POST /api/v1/badges` e verificar `201`, `name` normalizado e `progress` vazio, além de `401` sem autenticação e `422` em dados inválidos.

### Tests for User Story 1

- [X] T009 [P] [US1] Adicionar testes unitários de normalização e validação em `tests/unit/test_badge_schema.py`, cobrindo `strip()`, tamanho de `name`, enum de `rarity`, enum de `criteria` e `criteria_value > 0`.
- [X] T010 [P] [US1] Adicionar testes unitários do service em `tests/unit/test_badge_service.py` para criação com nome duplicado ativo, nome em caixa diferente, payload inválido e ausência de histórico de progresso.
- [X] T011 [P] [US1] Adicionar teste de integração em `tests/integration/test_badge_lifecycle.py` para criar um badge autenticado e confirmar `201` com `progress: []` e persistência do registro.

### Implementation for User Story 1

- [X] T012 [US1] Ajustar o modelo de `Badge` em `src/sidebrain_back/models/badge_model.py` para refletir `name`, `description`, `rarity`, `criteria`, `criteria_value`, `updated_at` e a regra de soft delete sem expor internals na resposta.
- [X] T013 [US1] Implementar a criação no repositório em `src/sidebrain_back/repositories/badge_repository.py`, incluindo consulta de conflito por nome ativo e criação transacional do badge.
- [X] T014 [US1] Implementar a criação no service em `src/sidebrain_back/services/badge_service.py`, normalizando `name`, validando payload e retornando badge com `progress: []`.
- [X] T015 [US1] Implementar `POST /api/v1/badges` em `src/sidebrain_back/routers/v1/badge_router.py` e registrar a rota no `src/sidebrain_back/routers/router.py`, usando `Depends(get_current_user)` e `Depends(get_badge_service)`.
- [X] T016 [US1] Finalizar os schemas e respostas públicas em `src/sidebrain_back/schemas/badge_schema.py`, incluindo `BadgeCreate`, `BadgeUpdate`, `BadgeResponse` e a composição do `progress` para o usuário autenticado.

**Checkpoint**: US1 entrega o MVP de criação do badge e é validável isoladamente.

## Phase 4: User Story 2 - Consultar badges e progresso pessoal (Priority: P1)

**Goal**: Listar badges ativos de forma paginada e consultar um badge específico, retornando somente o progresso do usuário autenticado.

**Independent Test**: Preparar badge ativo, badge removido e progressos de vários usuários; consultar a lista e um detalhe e verificar que somente o progresso do usuário atual aparece, com paginação consistente e `404` para removido/inexistente.

### Tests for User Story 2

- [X] T017 [P] [US2] Adicionar testes de contrato em `tests/contract/test_badge_contract.py` para `GET /api/v1/badges` e `GET /api/v1/badges/{badge_id}` com `200`, `401`, `404`, paginação e `progress` filtrado.
- [X] T018 [P] [US2] Adicionar testes unitários em `tests/unit/test_badge_service.py` para paginação, badge removido ignorado, `page_size` fora do intervalo e composição do progresso por usuário.
- [X] T019 [P] [US2] Adicionar teste de integração em `tests/integration/test_badge_lifecycle.py` para verificar isolamento de progressos de usuários diferentes e página além do total.

### Implementation for User Story 2

- [X] T020 [US2] Ajustar a query de listagem e detalhe em `src/sidebrain_back/repositories/badge_repository.py` para filtrar apenas itens ativos, ordenar estavelmente e carregar `BadgeProgress` somente para `bpg_user_id == user_id` via `selectinload` filtrado.
- [X] T021 [US2] Implementar `list_badges` e `get_badge_by_id` em `src/sidebrain_back/services/badge_service.py`, preservando paginação, escondendo badges removidos e montando `progress` somente do usuário autenticado.
- [X] T022 [US2] Ajustar os endpoints de consulta em `src/sidebrain_back/routers/v1/badge_router.py` para usar os serviços de listagem e detalhe sem expor campos internos e sem aceitar filtros físicos.

**Checkpoint**: US2 entrega a leitura filtrada do catálogo e garante isolamento de progresso por usuário.

## Phase 5: User Story 3 - Atualizar ou remover um badge (Priority: P2)

**Goal**: Atualizar parcialmente um badge ativo e remover logicamente sem apagar o histórico de progresso.

**Independent Test**: Atualizar apenas um campo válido, confirmar persistência parcial, depois remover o badge e verificar `204`, `404` em consultas e ausência de exclusão física em cascata.

### Tests for User Story 3

- [X] T023 [P] [US3] Adicionar testes de contrato em `tests/contract/test_badge_contract.py` para `PATCH /api/v1/badges/{badge_id}` e `DELETE /api/v1/badges/{badge_id}` com `200`, `204`, `401`, `404`, `409` e `422`.
- [X] T024 [P] [US3] Adicionar testes unitários em `tests/unit/test_badge_service.py` para atualização parcial, payload vazio, nome duplicado em outro badge ativo, e `soft delete` com preservação do registro e do progresso.
- [X] T025 [P] [US3] Adicionar teste de integração em `tests/integration/test_badge_lifecycle.py` para verificar `PATCH` parcial, `DELETE` lógico, `404` em nova atualização/remoção e ausência de exclusão física em cascata.

### Implementation for User Story 3

- [X] T026 [US3] Implementar a atualização e remoção de badge em `src/sidebrain_back/repositories/badge_repository.py`, preservando campos omitidos, aplicando soft delete em `bdg_is_deleted` e registrando `bdg_deleted_at` sem apagar o registro.
- [X] T027 [US3] Implementar `update_badge` e `delete_badge` em `src/sidebrain_back/services/badge_service.py`, exigindo ao menos um campo em atualização, rejeitando conflito de nome em badges ativos e respondendo `404` para item removido/inexistente.
- [X] T028 [US3] Alterar os endpoints de atualização e remoção em `src/sidebrain_back/routers/v1/badge_router.py` para `PATCH` parcial e `DELETE` lógico, sem expor campos internos nem aceitar client-side identifiers.

**Checkpoint**: US3 conclui o ciclo de vida do badge e preserva o histórico e o progresso do usuário.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Garantir qualidade, compatibilidade e validação final da feature.

- [X] T029 [P] Revisar a cobertura de regressão em `tests/unit/`, `tests/integration/` e `tests/contract/` para ajustar as acões de criação, consulta, atualização e remoção do catálogo de badges sem afetar outros recursos.
- [X] T030 [P] Executar `uv run ruff check .` e confirmar que a nova feature segue as convenções de `docs/code_conventions.md`, incluindo `Depends`, `selectinload`, paginação e schemas públicos sem `bdg_*`/`bpg_*`.
- [X] T031 Executar `uv run pytest` conforme `specs/SDB-87-badge-management/quickstart.md` e revisar falhas relacionadas a autenticação, paginação, soft delete e isolamento de progresso.
- [X] T032 Revisar os contratos públicos em `specs/SDB-87-badge-management/contracts/badges.md` e `README.md`, garantindo que descrições, exemplos e status `401/404/409/422/201/200/204` reflitam a implementação final.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001-T003 podem iniciar imediatamente e são independentes.
- **Foundational (Phase 2)**: T004-T008 dependem do setup e bloqueiam as histórias; T004, T005 e T006 podem evoluir em paralelo, e T007-T008 dependem das regras compartilhadas.
- **User Story 1 (Phase 3)**: T009-T011 podem ser escritos em paralelo; T012-T016 dependem do setup/fundação e da criação do badge.
- **User Story 2 (Phase 4)**: depende da US1; T017-T019 podem ser escritos em paralelo; T020-T022 dependem dos contratos e da estrutura da leitura.
- **User Story 3 (Phase 5)**: pode iniciar após a fundação, mas a integração final depende da US1 e da leitura; T023-T025 podem ser feitos em paralelo; T026-T028 dependem da validação de atualização e remoção.
- **Polish (Phase 6)**: depende das três histórias concluídas.

### User Story Dependencies

- **US1 (P1)**: é o MVP da feature; cria o catálogo de badges autenticado e valida unicidade ativa.
- **US2 (P1)**: depende da US1 porque reutiliza a criação e a composição do `BadgeResponse` com progresso isolado.
- **US3 (P2)**: depende da fundação, da US1 e da US2 para manter o ciclo de vida completo do badge sem quebrar a leitura.

### Parallel Opportunities

- Setup: T001, T002 e T003.
- Fundação: T004, T005 e T006; a persistência em T007 e o service em T008 seguem após essas regras.
- US1: T009, T010 e T011; depois, T012-T016 podem ser implementados em paralelo por área de responsabilidade.
- US2: T017, T018 e T019; a implementação do repositório e do service pode seguir em paralelo à validação.
- US3: T023-T025; depois, T026-T028 podem ser desenvolvidos por operação de repositório e router.
- Polish: T029 e T030 podem rodar em paralelo, enquanto T031 e T032 fecham a validação final.

## Parallel Example: User Story 1

```text
Task A: T009 [US1] validação de schema em tests/unit/test_badge_schema.py
Task B: T010 [US1] regras de negócio do service em tests/unit/test_badge_service.py
Task C: T011 [US1] integração de criação em tests/integration/test_badge_lifecycle.py
Task D: T012 [US1] modelo Badge em src/sidebrain_back/models/badge_model.py
Task E: T013 [US1] repositório de criação em src/sidebrain_back/repositories/badge_repository.py
```

## Parallel Example: User Story 2

```text
Task A: T017 [US2] testes de contrato de listagem/detalhe
Task B: T018 [US2] testes unitários de paginação e filtragem
Task C: T019 [US2] integração de isolamento de progresso
Task D: T020 [US2] query de listagem e detalhe no repository
Task E: T021 [US2] composição do service para resposta paginada
```

## Parallel Example: User Story 3

```text
Task A: T023 [US3] testes de contrato para PATCH/DELETE
Task B: T024 [US3] unit tests de atualização parcial
Task C: T025 [US3] integração de soft delete e preservação
Task D: T026 [US3] repositório de patch/delete
Task E: T027 [US3] service de patch/delete
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Setup e Foundational.
2. Implementar US1 para criar o badge e devolver `201` com nome normalizado e `progress: []`.
3. Executar os testes independentes de US1 e verificar `401`, `409`, `422` e resposta pública correta.
4. Parar no checkpoint antes de evoluir para US2 e US3.

### Incremental Delivery

1. Entregar US1 como MVP de catálogo global com criação autenticada e unicidade de nomes ativos.
2. Entregar US2 com listagem paginada, detalhe e isolamento do progresso do usuário atual.
3. Entregar US3 com atualização parcial e remoção lógica preservando o histórico.
4. Executar a fase de Polish e a suíte completa antes da liberação.

### Scope Protection

Não alterar autenticação, paginação global, modelos ou regras de outros agregados; limitar a feature ao CRUD de Badge e ao carregamento de `BadgeProgress` já existente.

## Completion Criteria

- Todas as tarefas seguem `- [ ] T###`, usam `[P]` apenas quando paralelizáveis e incluem `[US1]`, `[US2]` ou `[US3]` nas fases de história.
- Cada história tem critério de teste independente e cobertura para contrato público.
- MVP sugerido: Setup + Foundational + US1.
- `uv run ruff check .` e `uv run pytest` passam após a implementação.
