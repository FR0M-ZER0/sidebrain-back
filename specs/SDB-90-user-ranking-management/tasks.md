---

description: "Lista de tarefas para implementação do gerenciamento do ranking de usuários por XP (SDB-90)"
---

# Tasks: Gerenciamento do Ranking de Usuários por XP

**Input**: Design documents from `/specs/SDB-90-user-ranking-management/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/ranking-api.md`, `quickstart.md`

**Tests**: Incluídos conforme exigido pela constituição do projeto (`constitution.md`) e pelo plano de implementação (`plan.md`), cobrindo testes unitários, de contrato e de integração em PostgreSQL.

**Organization**: As tarefas estão organizadas por história de usuário para permitir implementação, teste e validação independentes de cada incremento.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode executar em paralelo (arquivos diferentes, sem dependências em tarefas incompletas)
- **[Story]**: História de usuário à qual a tarefa pertence (`US1`, `US2`, `US3`)
- Caminhos exatos de arquivos incluídos em todas as descrições

## Path Conventions

- **Código-fonte da aplicação**: `src/sidebrain_back/`
- **Suíte de testes**: `tests/unit/`, `tests/contract/`, `tests/integration/`
- **Documentação**: `docs/` e `specs/SDB-90-user-ranking-management/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Auditar os modelos existentes de leitura e preparar fixtures de teste reutilizáveis sem alterar o schema do banco de dados.

- [X] T001 Auditar os modelos existentes `User`, `Mission` e `MissionProgress`, o enum `MissionProgressStatusEnum` e o envelope `PaginatedResponse` em `src/sidebrain_back/models/user_model.py`, `src/sidebrain_back/models/mission_model.py`, `src/sidebrain_back/models/mission_progress_model.py`, `src/sidebrain_back/enums/mission_progress_status_enum.py` e `src/sidebrain_back/schemas/pagination_schema.py`, confirmando que nenhuma tabela, coluna ou migração Alembic deve ser criada
- [X] T002 [P] Ampliar `tests/conftest.py` com factories assíncronas reutilizáveis para usuários ranqueáveis (`user_factory` permitindo configurar `usr_id`, `usr_name`, `usr_created_at`, `usr_is_deleted`) e progressos de missão (`mission_progress_factory` permitindo configurar `mpg_status`, `mpg_score`, `mpg_finished_in`), mantendo o isolamento transacional de `db_session`

**Checkpoint**: Modelos de origem e infraestrutura de fixtures prontos para suportar os testes e camadas do ranking.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implementar os schemas públicos, a estrutura base de repositório/serviço com injeção de dependência e o registro de rotas que bloqueiam todas as histórias de usuário.

**⚠️ CRITICAL**: Nenhuma implementação de história de usuário deve começar antes da conclusão desta fase.

- [X] T003 [P] Criar testes unitários falhando para os schemas públicos em `tests/unit/test_ranking_schema.py`, validando literalmente as restrições de `data-model.md`: `position` (`int`, `Obrigatório, >= 1 (1-based, sequencial global)`), `userId` (`UUID`, `Obrigatório (alias="userId", serialization_alias="userId")`), `name` (`str`, `Obrigatório`), `xp` (`int`, `Obrigatório, >= 0`), `missionsCompleted` (`int`, `Obrigatório, >= 0 (alias="missionsCompleted", serialization_alias="missionsCompleted")`), ausência de `totalUsers` e ocultação de `usr_email`, `usr_password_hash`, `usr_updated_at`, `usr_deleted_at`, `mpg_score`, `mpg_finished_in` e `mpg_updated_at`
- [X] T004 Implementar `RankingEntryResponse` e `RankingListResponse` (reutilizando `PaginatedResponse[RankingEntryResponse]` com `data: list[RankingEntryResponse]`, `page: int (>= 1, padrão 1)`, `page_size: int (1..100, padrão 20)`, `total_items: int (>= 0, total de usuários ativos)` e `total_pages: int (>= 0)`) em `src/sidebrain_back/schemas/ranking_schema.py`, usando `model_config = ConfigDict(from_attributes=True, populate_by_name=True)` e satisfazendo os testes de T003
- [X] T005 [P] Criar a classe `RankingRepository`, o tipo/projeção de linha ranqueada e o provider `get_ranking_repository` em `src/sidebrain_back/repositories/ranking_repository.py`, definindo a base de agregação sobre `User` (`Filtro obrigatório usr_is_deleted.is_(False)`), `LEFT JOIN MissionProgress` (`Vínculo com User.usr_id` e `Condição de contabilização: mpg_status == 'done' (idle e in_progress são ignorados)`) e `LEFT JOIN Mission` (`Vínculo com Mission.msn_id` e `Filtro obrigatório msn_is_deleted.is_(False) para contabilização`), com fórmulas `xp = COALESCE(SUM(Mission.msn_xp_reward), 0)` e `missionsCompleted = COUNT(Mission.msn_id)` e ordenação `ORDER BY xp DESC, usr_created_at ASC, usr_id ASC`
- [X] T006 Criar a classe `RankingService` e o provider `get_ranking_service` em `src/sidebrain_back/services/ranking_service.py`, recebendo `RankingRepository` via `Depends(get_ranking_repository)`
- [X] T007 Criar o router `router = APIRouter(prefix="/v1/rankings", tags=["rankings"])` em `src/sidebrain_back/routers/v1/ranking_router.py` e registrá-lo em `src/sidebrain_back/routers/router.py`, preservando o prefixo `/api/v1/rankings`, autenticação com `Depends(get_current_user)` e tratamento padronizado em Problem Details (RFC 9457)

**Checkpoint**: Schemas públicos, injeção de dependências (`Depends`) e roteamento base configurados — implementação das histórias de usuário liberada.

---

## Phase 3: User Story 1 - Consultar o ranking geral de usuários por XP (Priority: P1) 🎯 MVP

**Goal**: Permitir que qualquer usuário autenticado consulte a classificação geral paginada de participantes ativos ordenada por XP decrescente (`GET /api/v1/rankings`), com posições globais sequenciais (`1-based`) contínuas entre páginas e inclusão de usuários ativos com `0 XP`.

**Independent Test**: Com um conjunto conhecido de usuários ativos e removidos logicamente e missões concluídas, em andamento, não iniciadas e removidas logicamente, consultar páginas de `GET /api/v1/rankings` e verificar que apenas usuários ativos são exibidos na ordem correta de XP e desempate, com posições globais sequenciais iniciando em 1 e metadados de paginação precisos.

### Tests for User Story 1 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO e confirmar que FALHAM antes da implementação**

- [X] T008 [P] [US1] Criar testes de contrato HTTP para `GET /api/v1/rankings` em `tests/contract/test_ranking_contract.py`, cobrindo `200 OK` com envelope `PaginatedResponse[RankingEntryResponse]` (`data`, `page`, `page_size`, `total_items`, `total_pages`), defaults `page=1` e `page_size=20`, continuidade de `position` na página 2, retorno `data=[]` para página além de `total_pages`, erro `401 Unauthorized` sem token válido e erro `422 Unprocessable Entity` para `page < 1`, `page_size < 1` ou `page_size > 100` em Problem Details
- [X] T009 [P] [US1] Criar testes unitários de `RankingService.list_rankings` em `tests/unit/test_ranking_service.py`, cobrindo cálculo de `offset` e `limit`, invocação de `count_ranked_users` e `list_rankings`, mapeamento para `RankingEntryResponse` e construção do envelope via `PaginatedResponse.build`
- [X] T010 [P] [US1] Criar testes de integração PostgreSQL para a listagem geral em `tests/integration/test_ranking_lifecycle.py`, validando soma de `msn_xp_reward` e contagem de `msn_id` para missões ativas com `mpg_status == 'done'`, inclusão de usuários ativos sem missões concluídas com `xp = 0` e `missionsCompleted = 0`, continuidade de `position` entre páginas consecutivas e quantidade constante de queries SQL por requisição (2 queries: contagem + página agregada, sem N+1)

### Implementation for User Story 1

- [X] T011 [US1] Implementar `RankingRepository.count_ranked_users` e `RankingRepository.list_rankings` em `src/sidebrain_back/repositories/ranking_repository.py`, filtrando `User.usr_is_deleted.is_(False)`, agrupando por `User.usr_id`, `User.usr_name` e `User.usr_created_at`, ordenando por `xp DESC, usr_created_at ASC, usr_id ASC`, aplicando `offset`/`limit` e atribuindo `position` global sequencial (`offset + index + 1`)
- [X] T012 [US1] Implementar `RankingService.list_rankings` em `src/sidebrain_back/services/ranking_service.py`, coordenando `count_ranked_users` e `list_rankings`, convertendo cada entrada para `RankingEntryResponse` e retornando `PaginatedResponse.build(data=..., page=page, page_size=page_size, total_items=total_items)`
- [X] T013 [US1] Implementar o endpoint `GET /v1/rankings` em `src/sidebrain_back/routers/v1/ranking_router.py`, recebendo `page: int = Query(default=1, ge=1)` e `page_size: int = Query(default=20, ge=1, le=100)`, exigindo `Depends(get_current_user)` e `Depends(get_ranking_service)` e retornando `PaginatedResponse[RankingEntryResponse]`
- [X] T014 [US1] Executar os testes focados da US1 em `tests/unit/test_ranking_schema.py`, `tests/unit/test_ranking_service.py`, `tests/contract/test_ranking_contract.py` e `tests/integration/test_ranking_lifecycle.py`, confirmando que a User Story 1 passa integralmente

**Checkpoint**: `GET /api/v1/rankings` está funcional, paginado, sem N+1 e validado independentemente como MVP.

---

## Phase 4: User Story 2 - Consultar a própria posição no ranking (Priority: P1)

**Goal**: Permitir que o usuário autenticado consulte diretamente sua posição atual, seu XP acumulado e seu total de missões concluídas (`GET /api/v1/rankings/me`) sem precisar paginar a listagem geral, mantendo consistência absoluta com o leaderboard global e retornando `404` se o usuário não for encontrado como ativo.

**Independent Test**: Autenticar-se com um usuário ativo em uma base com múltiplos participantes acima, empatados e abaixo de sua pontuação e verificar que `GET /api/v1/rankings/me` retorna exatamente a mesma posição global, XP e contagem de missões concluídas que esse usuário ocupa na classificação geral, e que um usuário inativo/inexistente no ranking recebe `404`.

### Tests for User Story 2 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO e confirmar que FALHAM antes da implementação**

- [X] T015 [P] [US2] Ampliar `tests/contract/test_ranking_contract.py` com testes de contrato para `GET /api/v1/rankings/me`, validando `200 OK` com exatamente os 5 campos de `RankingEntryResponse` (`position`, `userId`, `name`, `xp`, `missionsCompleted` e sem `totalUsers`), `401 Unauthorized` sem credenciais válidas e `404 Not Found` em Problem Details quando o usuário autenticado não é encontrado como ativo pelo serviço
- [X] T016 [P] [US2] Ampliar `tests/unit/test_ranking_service.py` com testes unitários de `RankingService.get_my_ranking`, cobrindo retorno de `RankingEntryResponse` para usuário ativo (com XP acumulado ou com `xp = 0` e `missionsCompleted = 0`) e lançamento de `ProblemDetailError` com status `404` quando `get_user_ranking` retorna `None`
- [X] T017 [P] [US2] Ampliar `tests/integration/test_ranking_lifecycle.py` com testes PostgreSQL para `GET /api/v1/rankings/me`, verificando igualdade exata de `position`, `userId`, `name`, `xp` e `missionsCompleted` com a entrada correspondente em `GET /api/v1/rankings`, retorno `404` para usuário com `usr_is_deleted = true` ou inexistente e execução em uma única query SQL via CTE com `ROW_NUMBER()`

### Implementation for User Story 2

- [X] T018 [US2] Implementar `RankingRepository.get_user_ranking` em `src/sidebrain_back/repositories/ranking_repository.py`, construindo CTE/subquery com `ROW_NUMBER() OVER (ORDER BY xp DESC, usr_created_at ASC, usr_id ASC)` sobre os usuários ativos (`User.usr_is_deleted.is_(False)`) e filtrando pelo `user_id` autenticado em uma única consulta SQL
- [X] T019 [US2] Implementar `RankingService.get_my_ranking` em `src/sidebrain_back/services/ranking_service.py`, consultando `self.repository.get_user_ranking(user.usr_id)`, lançando `ProblemDetailError(status=404, title="Não encontrado", detail="Usuário não encontrado.")` quando o retorno for `None` e convertendo o resultado para `RankingEntryResponse`
- [X] T020 [US2] Implementar o endpoint `GET /v1/rankings/me` em `src/sidebrain_back/routers/v1/ranking_router.py`, mantendo `Depends(get_current_user)` inalterado, `response_model=RankingEntryResponse` e delegando a execução para `RankingService.get_my_ranking`
- [X] T021 [US2] Executar os testes focados da US2 em `tests/unit/test_ranking_service.py`, `tests/contract/test_ranking_contract.py` e `tests/integration/test_ranking_lifecycle.py`, confirmando que a User Story 2 passa isoladamente e em conjunto com a US1

**Checkpoint**: `GET /api/v1/rankings` e `GET /api/v1/rankings/me` funcionam de forma independente e consistente.

---

## Phase 5: User Story 3 - Garantir elegibilidade, cálculo derivado de XP e desempate determinístico (Priority: P2)

**Goal**: Garantir que o ranking reflita exclusivamente usuários ativos (`usr_is_deleted = false`) e missões ativas concluídas (`msn_is_deleted = false` e `mpg_status = 'done'`), preserve o XP mesmo se `Step` ou `Track` pai for removido logicamente, aplique desempate determinístico (`usr_created_at ASC, usr_id ASC`) sem posições compartilhadas e oculte integralmente dados sensíveis ou internos.

**Independent Test**: Criar cenários de empate de XP entre múltiplos usuários ativos (incluindo 0 XP), progressos `idle`/`in_progress`, `mpg_score` diversos, missões removidas logicamente, `Step`/`Track` removidos logicamente e usuários removidos logicamente, verificando que as posições permanecem idênticas entre consultas repetidas, registros excluídos de usuário/missão não afetam o ranking e nenhum atributo interno vaza no contrato.

### Tests for User Story 3 ⚠️

> **NOTE: Escrever estes testes PRIMEIRO e confirmar que FALHAM ou validam integralmente as invariantes antes do fechamento da fase**

- [X] T022 [P] [US3] Ampliar `tests/integration/test_ranking_lifecycle.py` com testes de elegibilidade e cálculo derivado em banco PostgreSQL: exclusão de progressos `idle` e `in_progress`, ignorância de `mpg_score`, exclusão de missões com `msn_is_deleted = true`, preservação do XP e de `missionsCompleted` quando `Step` (`stp_is_deleted = true`) ou `Track` (`trk_is_deleted = true`) pai está removido logicamente, e exclusão total de usuários com `usr_is_deleted = true` da listagem, de `total_items` e do cálculo de posições dos demais usuários
- [X] T023 [P] [US3] Ampliar `tests/integration/test_ranking_lifecycle.py` com testes de desempate determinístico (`ORDER BY xp DESC, usr_created_at ASC, usr_id ASC`), cobrindo empates com XP positivo e com `0 XP`, desempate pelo `usr_created_at` mais antigo (`ASC`), segundo desempate por `usr_id` crescente (`ASC`) quando `usr_created_at` é idêntico, ausência de posição compartilhada e estabilidade entre chamadas repetidas em `GET /api/v1/rankings` e `GET /api/v1/rankings/me`
- [X] T024 [P] [US3] Ampliar `tests/contract/test_ranking_contract.py` e `tests/unit/test_ranking_schema.py` com asserções explícitas de não exposição de `usr_email`, `usr_password_hash`, `usr_created_at`, `usr_updated_at`, `usr_deleted_at`, `mpg_score`, `mpg_finished_in`, `mpg_updated_at` e quaisquer chaves iniciadas por `usr_`, `msn_` ou `mpg_` em ambas as rotas

### Implementation for User Story 3

- [X] T025 [US3] Revisar e consolidar a expressão de agregação e ordenação compartilhada em `src/sidebrain_back/repositories/ranking_repository.py` e os mapeamentos de `src/sidebrain_back/schemas/ranking_schema.py`, garantindo que `list_rankings` e `get_user_ranking` reutilizem exatamente os mesmos critérios de filtro (`User.usr_is_deleted.is_(False)`, `MissionProgress.mpg_status == MissionProgressStatusEnum.DONE`, `Mission.msn_is_deleted.is_(False)`) e a mesma cláusula `ORDER BY xp DESC, User.usr_created_at ASC, User.usr_id ASC` sem depender de `Step` ou `Track`
- [X] T026 [US3] Executar todos os testes unitários, de contrato e de integração de ranking em `tests/unit/test_ranking_schema.py`, `tests/unit/test_ranking_service.py`, `tests/contract/test_ranking_contract.py` e `tests/integration/test_ranking_lifecycle.py`, confirmando 100% de aprovação nas três histórias de usuário

**Checkpoint**: Todas as histórias de usuário (US1, US2 e US3) e regras de borda estão implementadas e verificadas de forma independente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentação arquitetural, revisão de conformidade com as convenções do projeto e validação final de qualidade.

- [X] T027 [P] Documentar a seção de gerenciamento do ranking de usuários em `docs/architecture.md`, descrevendo o fluxo `routers/v1/ranking_router.py -> services/ranking_service.py -> repositories/ranking_repository.py -> models`, o cálculo derivado de XP e `missionsCompleted` via agregação SQL sem N+1 e a referência ao contrato `specs/SDB-90-user-ranking-management/contracts/ranking-api.md`
- [X] T028 [P] Revisar `src/sidebrain_back/schemas/ranking_schema.py`, `src/sidebrain_back/repositories/ranking_repository.py`, `src/sidebrain_back/services/ranking_service.py` e `src/sidebrain_back/routers/v1/ranking_router.py` contra `docs/architecture.md` e `docs/code_conventions.md`, confirmando nomenclatura de arquivos/classes/métodos, `ConfigDict(from_attributes=True, populate_by_name=True)` e providers `get_*` junto às classes
- [X] T029 Executar a validação completa descrita em `specs/SDB-90-user-ranking-management/quickstart.md`, incluindo `uv run --no-sync ruff check .` e `uv run --no-sync pytest` na raiz do repositório

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Não possui dependências — pode iniciar imediatamente (T001 e T002 em paralelo).
- **Foundational (Phase 2)**: Depende da conclusão da Phase 1 — **BLOQUEIA** todas as histórias de usuário (T003 e T005 em paralelo; T004 depende de T003; T006 depende de T005; T007 depende de T004 e T006).
- **User Stories (Phases 3, 4 e 5)**: Todas dependem da conclusão da Phase 2 (Foundational).
  - **US1 (Phase 3 - P1)**: Pode iniciar imediatamente após a Phase 2; não depende de outras histórias.
  - **US2 (Phase 4 - P1)**: Pode iniciar após a Phase 2; compartilha os arquivos do domínio `ranking`, sendo recomendada execução sequencial logo após a US1 para evitar conflitos de edição em `ranking_repository.py`, `ranking_service.py` e `ranking_router.py`.
  - **US3 (Phase 5 - P2)**: Consolida e valida exaustivamente os casos de borda sobre os endpoints de US1 e US2.
- **Polish (Phase 6)**: Depende da conclusão das Phases 3, 4 e 5.

### User Story Dependencies

```text
Phase 1: Setup (T001–T002)
   │
   ▼
Phase 2: Foundational (T003–T007)
   │
   ├──► Phase 3: US1 - GET /api/v1/rankings (T008–T014) 🎯 MVP
   │       │
   │       ▼
   ├──► Phase 4: US2 - GET /api/v1/rankings/me (T015–T021)
   │       │
   │       ▼
   └──► Phase 5: US3 - Elegibilidade, XP derivado e desempate (T022–T026)
           │
           ▼
Phase 6: Polish & Cross-Cutting Concerns (T027–T029)
```

### Within Each User Story

- Testes unitários, de contrato e de integração DEVEM ser escritos antes da implementação correspondente.
- Implementação segue a ordem de dependência das camadas: `repositories` → `services` → `routers`.
- O checkpoint de cada história deve passar antes de avançar para a fase seguinte.

### Parallel Opportunities

- **Phase 1**: `T002` pode rodar em paralelo com `T001`.
- **Phase 2**: `T003` (`tests/unit/test_ranking_schema.py`) e `T005` (`src/sidebrain_back/repositories/ranking_repository.py`) podem rodar em paralelo.
- **Phase 3 (US1)**: `T008`, `T009` e `T010` atuam em arquivos de teste distintos e podem ser desenvolvidos em paralelo.
- **Phase 4 (US2)**: `T015`, `T016` e `T017` atuam em arquivos de teste distintos e podem ser desenvolvidos em paralelo.
- **Phase 5 (US3)**: `T022`/`T023` (integração) e `T024` (contrato/schema) podem ser desenvolvidos em paralelo.
- **Phase 6 (Polish)**: `T027` (`docs/architecture.md`) e `T028` (revisão de código) podem rodar em paralelo antes de `T029`.

---

## Parallel Example: User Story 1

```bash
# Executar a criação dos testes da User Story 1 em paralelo:
Task T008: "Criar testes de contrato HTTP para GET /api/v1/rankings em tests/contract/test_ranking_contract.py"
Task T009: "Criar testes unitários de RankingService.list_rankings em tests/unit/test_ranking_service.py"
Task T010: "Criar testes de integração PostgreSQL para a listagem geral em tests/integration/test_ranking_lifecycle.py"
```

## Parallel Example: User Story 2

```bash
# Executar a criação dos testes da User Story 2 em paralelo:
Task T015: "Ampliar tests/contract/test_ranking_contract.py com testes de contrato para GET /api/v1/rankings/me"
Task T016: "Ampliar tests/unit/test_ranking_service.py com testes unitários de RankingService.get_my_ranking"
Task T017: "Ampliar tests/integration/test_ranking_lifecycle.py com testes PostgreSQL para GET /api/v1/rankings/me"
```

## Parallel Example: User Story 3

```bash
# Executar as verificações de regras de negócio/desempate e segurança de contrato em paralelo:
Task T022/T023: "Ampliar tests/integration/test_ranking_lifecycle.py com testes de elegibilidade, soft delete e desempate determinístico"
Task T024: "Ampliar tests/contract/test_ranking_contract.py e tests/unit/test_ranking_schema.py com asserções de não exposição de campos internos"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Concluir Phase 1: Setup (`T001`–`T002`)
2. Concluir Phase 2: Foundational (`T003`–`T007`)
3. Concluir Phase 3: User Story 1 (`T008`–`T014`)
4. **STOP and VALIDATE**: Executar os testes da User Story 1 e validar `GET /api/v1/rankings` independentemente
5. Demonstrar o leaderboard paginado funcional antes de avançar

### Incremental Delivery

1. **Setup + Foundational** (`T001`–`T007`) → Contratos, DI e base de repositório prontos
2. **User Story 1** (`T008`–`T014`) → `GET /api/v1/rankings` paginado e testado (MVP!)
3. **User Story 2** (`T015`–`T021`) → `GET /api/v1/rankings/me` direto via CTE e testado
4. **User Story 3** (`T022`–`T026`) → Garantia exaustiva de desempate, soft delete e segurança de contrato
5. **Polish** (`T027`–`T029`) → Documentação atualizada e suíte completa + lint aprovados

---

## Notes

- `[P]` indica tarefas em arquivos distintos e sem dependência de tarefas não concluídas.
- `[US1]`, `[US2]` e `[US3]` mapeiam cada tarefa diretamente às histórias de usuário de `spec.md`.
- Nenhuma tabela ou coluna nova deve ser adicionada ao banco de dados (todo cálculo de `xp`, `missionsCompleted` e `position` é derivado em tempo de consulta).
- `Step` ou `Track` com exclusão lógica **não** invalidam o XP de uma `Mission` ativa (`msn_is_deleted = false`) concluída (`mpg_status = 'done'`).
- A resposta de `GET /api/v1/rankings/me` retorna exclusivamente os 5 campos de `RankingEntryResponse` (`position`, `userId`, `name`, `xp`, `missionsCompleted`), sem `totalUsers`.
