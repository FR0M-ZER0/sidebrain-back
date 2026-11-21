---

description: "Task list for user avatar feature"
---

# Tasks: Avatar do perfil do usuÃ¡rio

**Input**: Design documents from `/specs/SDB-111-user-avatar/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/avatar-api.md](./contracts/avatar-api.md) e
[quickstart.md](./quickstart.md)

**Tests**: IncluÃ­dos porque FR-016 exige testes unitÃ¡rios, de contrato e de
integraÃ§Ã£o para catÃ¡logo, seleÃ§Ã£o, remoÃ§Ã£o, validaÃ§Ã£o, autenticaÃ§Ã£o, fallback e
regressÃµes do perfil.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar a estrutura de arquivos e a estratÃ©gia de recursos da
feature sem alterar os fluxos existentes.

- [X] T001 [P] Criar o pacote de recursos `src/sidebrain_back/static/avatars/` e registrar os arquivos `default.png`, `cat.png`, `dog.png`, `fox.png`, `bear.png`, `rabbit.png`, `panda.png`, `owl.png`, `penguin.png`, `lion.png` e `turtle.png`
- [X] T002 [P] Documentar a convenÃ§Ã£o de nomes e o mapeamento inicial de imagens em `docs/avatar_catalog.md`
- [X] T003 [P] Atualizar o manifesto de empacotamento para incluir `src/sidebrain_back/static/avatars/` na distribuiÃ§Ã£o em `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Criar o armazenamento e a infraestrutura HTTP compartilhados por
todas as histÃ³rias.

**âš ï¸ CRITICAL**: Nenhuma histÃ³ria pode ser concluÃ­da antes desta fase.

- [X] T004 Criar o modelo `Avatar` com `avt_slug VARCHAR(64)` como chave primÃ¡ria imutÃ¡vel, `avt_name VARCHAR(100)` obrigatÃ³rio, `avt_image_path VARCHAR(255)` obrigatÃ³rio, `avt_is_active BOOLEAN` obrigatÃ³rio com default `true` e `avt_created_at` em `src/sidebrain_back/models/avatar_model.py`
- [X] T005 Adicionar `usr_avatar_slug VARCHAR(64)` nullable ao modelo `User`, com relacionamento opcional para `Avatar`, em `src/sidebrain_back/models/user_model.py`
- [X] T006 Criar migraÃ§Ã£o Alembic aditiva em `migrations/versions/adiciona_avatar_ao_usuario.py` para criar `avatar`, adicionar `user.usr_avatar_slug` com `ON DELETE SET NULL`, inserir os dez slugs iniciais idempotentemente e preservar usuÃ¡rios existentes
- [X] T007 Registrar `Avatar` no metadata carregado por Alembic em `migrations/env.py` e validar que a migraÃ§Ã£o possui downgrade reversÃ­vel sem apagar referÃªncias de usuÃ¡rios
- [X] T008 Montar `StaticFiles` para `src/sidebrain_back/static/` em `/static` no app criado por `src/main.py`, mantendo a referÃªncia relativa `/static/avatars/{slug}.png`
- [X] T009 [P] Criar schemas base `AvatarResponse` e `AvatarListResponse` com `imageUrl` serializado e `ConfigDict(from_attributes=True, populate_by_name=True)` em `src/sidebrain_back/schemas/avatar_schema.py`
- [X] T010 [P] Criar `AvatarRepository` com consultas de catÃ¡logo ativo e slug por estado em `src/sidebrain_back/repositories/avatar_repository.py`, usando `Depends(get_db)` sem regra de negÃ³cio

**Checkpoint**: banco, arquivos estÃ¡ticos, schemas e acesso ao catÃ¡logo estÃ£o
prontos para as histÃ³rias.

---

## Phase 3: User Story 1 - Escolher um avatar (Priority: P1) ðŸŽ¯ MVP

**Goal**: UsuÃ¡rio autenticado consulta os dez avatares ativos, escolhe um slug
ativo e vÃª a imagem escolhida no prÃ³prio perfil; perfil sem seleÃ§Ã£o usa default.

**Independent Test**: Consultar `GET /api/v1/avatars`, selecionar `cat` em
`PUT /api/v1/users/me` e confirmar em `GET /api/v1/users/me` que `imageUrl` Ã©
`/static/avatars/cat.png`; sem seleÃ§Ã£o, confirmar `default.png`.

### Tests for User Story 1

- [X] T011 [P] [US1] Criar testes de contrato para `GET /api/v1/avatars`, `GET /api/v1/users/me` e seleÃ§Ã£o por `PUT /api/v1/users/me` em `tests/contract/test_avatar_catalog_contract.py`
- [X] T012 [P] [US1] Criar teste unitÃ¡rio do catÃ¡logo ativo, resoluÃ§Ã£o do avatar selecionado e fallback default em `tests/unit/test_avatar_service.py`
- [X] T013 [P] [US1] Criar teste de integraÃ§Ã£o do catÃ¡logo autenticado, seleÃ§Ã£o de avatar e leitura do perfil em `tests/integration/test_avatar_catalog.py`

### Implementation for User Story 1

- [X] T014 [US1] Implementar `AvatarService` para listar somente registros ativos e construir `AvatarResponse` com URL relativa em `src/sidebrain_back/services/avatar_service.py`
- [X] T015 [US1] Implementar rota autenticada `GET /api/v1/avatars` usando `get_current_user` e `get_avatar_service` em `src/sidebrain_back/routers/v1/avatar_router.py`
- [X] T016 [US1] Adicionar `avatar: str | None` opcional ao `UserUpdateRequest`, preservando a distinÃ§Ã£o entre campo ausente e `null`, em `src/sidebrain_back/schemas/user_schema.py`
- [X] T017 [US1] Implementar no `UserService` a validaÃ§Ã£o de slug ativo, a persistÃªncia da seleÃ§Ã£o e a resoluÃ§Ã£o do avatar selecionado ou default na resposta de `GET /api/v1/users/me` em `src/sidebrain_back/services/user_service.py`
- [X] T018 [US1] Adicionar mÃ©todos de atualizaÃ§Ã£o e consulta da referÃªncia de avatar em `src/sidebrain_back/repositories/user_repository.py` e integrar `get_avatar_service` por `Depends` em `src/sidebrain_back/services/user_service.py`
- [X] T019 [US1] Incluir `UserMeResponse.avatar` e registrar `avatar_router` no roteador `/api` em `src/sidebrain_back/schemas/user_schema.py` e `src/sidebrain_back/routers/router.py`

**Checkpoint**: catÃ¡logo, seleÃ§Ã£o de slug ativo, perfil e fallback default
funcionam independentemente.

---

## Phase 4: User Story 2 - Alterar ou remover o avatar (Priority: P1)

**Goal**: UsuÃ¡rio troca o avatar, remove a seleÃ§Ã£o com `null` e mantÃ©m nome,
e-mail, senha e demais dados inalterados.

**Independent Test**: Selecionar `cat`, substituir por `fox`, enviar
`{"avatar": null}` e verificar a imagem apÃ³s cada operaÃ§Ã£o e a preservaÃ§Ã£o dos
demais campos.

### Tests for User Story 2

- [X] T020 [P] [US2] Estender os testes de contrato para campo ausente manter, `avatar: null` remover e troca retornar a nova referÃªncia em `tests/contract/test_user_profile_update_contract.py`
- [X] T021 [P] [US2] Criar testes unitÃ¡rios de transiÃ§Ãµes ativoâ†’ativo, ativoâ†’nulo e payload sem avatar em `tests/unit/test_user_service.py`
- [X] T022 [P] [US2] Estender testes de integraÃ§Ã£o de atualizaÃ§Ã£o para troca, remoÃ§Ã£o e preservaÃ§Ã£o de nome/e-mail/gamificaÃ§Ã£o em `tests/integration/test_user_profile_update.py`

### Implementation for User Story 2

- [X] T023 [US2] Ajustar a validaÃ§Ã£o de `UserUpdateRequest` para permitir `avatar: null`, rejeitar `null` explÃ­cito em `name`/`email` e manter o comportamento de campos ausentes em `src/sidebrain_back/schemas/user_schema.py`
- [X] T024 [US2] Atualizar `UserService.update_user` para aplicar somente a transiÃ§Ã£o de avatar solicitada, persistir `NULL` na remoÃ§Ã£o e executar um Ãºnico commit/rollback transacional em `src/sidebrain_back/services/user_service.py`
- [X] T025 [US2] Atualizar `UserRepository.update` para aceitar a referÃªncia opcional de avatar sem modificar campos pÃºblicos nÃ£o enviados em `src/sidebrain_back/repositories/user_repository.py`
- [X] T026 [US2] Garantir que o response de perfil apÃ³s troca ou remoÃ§Ã£o preserve `id`, `name`, `email`, `createdAt`, `xp` e `missionsCompleted` em `src/sidebrain_back/schemas/user_schema.py` e `src/sidebrain_back/services/user_service.py`

**Checkpoint**: seleÃ§Ã£o, alteraÃ§Ã£o, remoÃ§Ã£o e atualizaÃ§Ã£o parcial do perfil
funcionam sem regressÃ£o.

---

## Phase 5: User Story 3 - Manter o catÃ¡logo seguro e administrÃ¡vel (Priority: P2)

**Goal**: Rejeitar slugs inexistentes/inativos, ocultar opÃ§Ãµes desativadas,
resolver default para referÃªncias inativas e documentar manutenÃ§Ã£o segura.

**Independent Test**: Desativar um avatar, confirmar que ele desaparece do
catÃ¡logo e que perfis existentes retornam default; tentar selecionÃ¡-lo e tentar
alterar sem autenticaÃ§Ã£o, confirmando Problem Details e ausÃªncia de mutaÃ§Ã£o.

### Tests for User Story 3

- [X] T027 [P] [US3] Criar testes de contrato para slug inexistente/inativo, ausÃªncia de autenticaÃ§Ã£o e formato Problem Details em `tests/contract/test_avatar_catalog_contract.py`
- [X] T028 [P] [US3] Criar testes unitÃ¡rios para rejeiÃ§Ã£o sem mutaÃ§Ã£o e fallback de referÃªncia inativa em `tests/unit/test_avatar_service.py`
- [X] T029 [P] [US3] Criar testes de integraÃ§Ã£o para desativaÃ§Ã£o, seleÃ§Ã£o invÃ¡lida, catÃ¡logo filtrado, autenticaÃ§Ã£o e preservaÃ§Ã£o de usuÃ¡rios existentes em `tests/integration/test_avatar_catalog.py`

### Implementation for User Story 3

- [X] T030 [US3] Mapear erros de avatar inexistente/inativo para `ProblemDetailError` sem alterar o usuÃ¡rio em `src/sidebrain_back/routers/v1/user_router.py` e `src/sidebrain_back/services/auth_errors.py`
- [X] T031 [US3] Garantir que consultas de perfil tratem avatar inativo como default, enquanto novas seleÃ§Ãµes consultam `avt_is_active = true`, em `src/sidebrain_back/services/avatar_service.py` e `src/sidebrain_back/services/user_service.py`
- [X] T032 [US3] Atualizar `docs/avatar_catalog.md` com procedimento para adicionar imagem/slug via migraÃ§Ã£o idempotente, desativar `avt_is_active` e preservar referÃªncias histÃ³ricas
- [X] T033 [US3] Atualizar `specs/SDB-111-user-avatar/contracts/avatar-api.md` e `README.md` para refletir endpoints efetivos `/api/v1`, autenticaÃ§Ã£o, fallback e Problem Details

**Checkpoint**: catÃ¡logo administrÃ¡vel por cÃ³digo, seguro contra seleÃ§Ãµes
invÃ¡lidas e compatÃ­vel com usuÃ¡rios antigos.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validar integraÃ§Ã£o completa, documentaÃ§Ã£o e ausÃªncia de regressÃµes.

- [X] T034 [P] Atualizar as asserÃ§Ãµes de chaves de resposta nos testes existentes em `tests/contract/test_user_profile_read_contract.py` e doubles de `UserMeResponse` para incluir `avatar`
- [X] T035 [P] Adicionar verificaÃ§Ã£o HTTP dos onze arquivos estÃ¡ticos e da existÃªncia de `default.png` em `tests/integration/test_avatar_catalog.py`
- [X] T036 Executar `uv run ruff check .` e corrigir somente problemas introduzidos pela feature
- [X] T037 Executar `uv run pytest tests/unit tests/contract` e corrigir falhas de contrato ou regressÃµes do perfil
- [X] T038 Executar `uv run pytest tests/integration/test_user_profile_read.py tests/integration/test_user_profile_update.py tests/integration/test_avatar_catalog.py` apÃ³s aplicar `uv run alembic upgrade head`
- [X] T039 Executar os cenÃ¡rios de [quickstart.md](./quickstart.md) e registrar o resultado da validaÃ§Ã£o de catÃ¡logo, seleÃ§Ã£o, remoÃ§Ã£o, fallback e autenticaÃ§Ã£o

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001â€“T003 sÃ£o independentes e podem iniciar imediatamente.
- **Foundational (Phase 2)**: depende de T001â€“T003; T004â€“T010 bloqueiam as
  histÃ³rias.
- **User Story 1 (Phase 3)**: depende da fundaÃ§Ã£o; Ã© o MVP.
- **User Story 2 (Phase 4)**: depende de US1 porque estende o mesmo contrato e
  serviÃ§o de seleÃ§Ã£o, mas seus testes sÃ£o independentes apÃ³s a fundaÃ§Ã£o.
- **User Story 3 (Phase 5)**: depende de US1 e US2 para validar todas as
  transiÃ§Ãµes e a manutenÃ§Ã£o do catÃ¡logo.
- **Polish (Phase 6)**: depende das histÃ³rias desejadas e da migraÃ§Ã£o aplicada.

### Parallel Opportunities

- T001, T002 e T003 podem executar em paralelo.
- T009 e T010 podem executar em paralelo apÃ³s os modelos; T011â€“T013, T020â€“T022
  e T027â€“T029 podem executar em paralelo dentro de suas histÃ³rias.
- T034 e T035 podem executar em paralelo com a documentaÃ§Ã£o T033.

### User Story Completion Order

```text
Phase 1 â†’ Phase 2 â†’ US1 (P1/MVP) â†’ US2 (P1) â†’ US3 (P2) â†’ Polish
```

## Implementation Strategy

### MVP First

1. Concluir Setup e Foundational.
2. Implementar US1: catÃ¡logo autenticado, seleÃ§Ã£o ativa, perfil e default.
3. Executar os testes de US1 e parar para validaÃ§Ã£o independente.

### Incremental Delivery

1. Adicionar US2 para troca, remoÃ§Ã£o e atualizaÃ§Ã£o parcial.
2. Adicionar US3 para inativaÃ§Ã£o, rejeiÃ§Ãµes, autenticaÃ§Ã£o e manutenÃ§Ã£o.
3. Executar Polish com lint, testes unitÃ¡rios, contratos, integraÃ§Ã£o e quickstart.

### Validation Criteria by Story

- **US1**: dez avatares ativos com slug/nome/URL, seleÃ§Ã£o persistida e default
  para perfil sem avatar.
- **US2**: troca e remoÃ§Ã£o refletem na primeira consulta posterior, enquanto
  campos existentes permanecem iguais.
- **US3**: 100% dos slugs invÃ¡lidos/inativos sÃ£o rejeitados sem mutaÃ§Ã£o,
  catÃ¡logo oculta inativos, fallback funciona e requisiÃ§Ãµes sem autenticaÃ§Ã£o
  falham em Problem Details.

