# Tasks: Autenticação e gerenciamento do perfil do usuário

**Input**: `specs/SDB-81-user-auth-profile/spec.md`, [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contrato HTTP](contracts/auth-profile.md) e [quickstart.md](quickstart.md).

**Tests**: obrigatórios pela constituição do projeto e pelos cenários de aceite da especificação. Em cada história, escrever primeiro os testes indicados e confirmar que falham pelo comportamento ainda ausente.

**Organization**: tarefas agrupadas por história; caminhos relativos à raiz do repositório. `[P]` indica arquivos independentes e nenhuma dependência de tarefa ainda incompleta. Manter `routers -> services -> repositories -> models`; `core` não importa camadas de negócio.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: disponibilizar bibliotecas e configuração sem criar ainda os endpoints.

- [X] T001 Adicionar `pwdlib[argon2]`, `PyJWT` e `email-validator` às dependências e atualizar o lock com `uv sync` em `pyproject.toml` e `uv.lock`.
- [X] T002 Configurar `JWT_SECRET_KEY` obrigatório, sem valor padrão versionado, expiração fixa de 60 minutos, algoritmo HS256 fixo e Redis de autenticação no banco lógico `/2` em `src/sidebrain_back/core/constants.py` e `.env.example`; preparar segredo apenas de teste antes do import de `main` em `tests/conftest.py`.

**Checkpoint**: dependências resolvidas e aplicação inicializável com configuração explícita.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: migração, segurança, erros e infraestrutura compartilhada por todas as histórias.

**CRITICAL**: concluir esta fase antes de iniciar uma história.

- [X] T003 [P] Escrever testes de upgrade/downgrade, colisão legada por `lower(btrim(usr_email))`, unicidade sob concorrência e preservação de contas/relacionamentos em `tests/integration/test_user_auth_migration.py`.
- [X] T004 [P] Escrever testes de hash Argon2id, JWT HS256 com `sub` UUID, `iat`, `exp` de 60 minutos e `ver` inteiro obrigatório, e recusa de UUID puro/assinatura adulterada/expiração em `tests/unit/test_auth_security.py`.
- [X] T005 [P] Escrever testes de `application/problem+json`, `WWW-Authenticate: Bearer`, `Retry-After` e corpo sem segredos nos handlers em `tests/contract/test_auth_error_contract.py`.
- [X] T006 [P] Escrever testes do limitador Redis para janela móvel de 15 minutos, quinta falha `401`, sexta `429` por 15 minutos, reset no sucesso, isolamento login/troca, concorrência, `422` sem contagem e falha fechada `503` em `tests/unit/test_auth_rate_limit.py`.
- [X] T007 Criar migração Alembic `migrations/versions/f81a1b2c3d4_user_auth.py` após `e5f6a7b8c9d0`: auditar duplicatas normalizadas de todas as contas (inclusive excluídas), adicionar `usr_token_version integer NOT NULL DEFAULT 0`, criar `uq_user_usr_email_normalized` único em `lower(btrim(usr_email))` com criação concorrente/autocommit e downgrade reversível; documentar limpeza de índice `INVALID` se a criação falhar.
- [X] T008 Atualizar `src/sidebrain_back/models/user_model.py` com `usr_token_version` inteiro não nulo e default `0`, mapear o índice funcional da migração e preservar `usr_email String(255) NOT NULL`, `usr_password_hash String(255) NOT NULL`, `usr_is_deleted=false`, `usr_deleted_at` anulável e relacionamentos sem cascata física no soft delete.
- [X] T009 Implementar `hash_password`/`verify_password` Argon2id fora do event loop, hash fictício para falhas indistinguíveis e `create_access_token`/`decode_access_token` com claims e algoritmo fixos em `src/sidebrain_back/core/security.py`; não registrar senha, hash, token ou segredo.
- [X] T010 Ampliar `src/sidebrain_back/core/errors.py` para repassar headers de `HTTPException` e de `ProblemDetailError`, emitir `application/problem+json` e manter `type`, `title`, `status`, `detail` e `errors` sem nomes físicos ou credenciais.
- [X] T011 Implementar cliente `redis.asyncio` compartilhado no banco `/2`, encerramento no lifespan e scripts Lua atômicos de janela móvel/bloqueio, usando `TIME` do Redis e chaves digest sem e-mail em claro, em `src/sidebrain_back/core/rate_limit.py` e `src/main.py`; receber a origem como string, sem depender de `Request` em `core`.
- [X] T012 Criar `UserRepository` e `get_user_repository` em `src/sidebrain_back/repositories/user_repository.py` com leitura ativa por `usr_id`, leitura sob lock e sessão `AsyncSession`, deixando regras de negócio no service.
- [X] T013 Criar `AuthService.authenticate_user_token` e `get_auth_service` em `src/sidebrain_back/services/auth_service.py`: decodificar JWT, exigir conta ativa, comparar `ver` com `usr_token_version` em nova consulta e sinalizar falha de autenticação sem conhecer `HTTPException`.
- [X] T014 Mover o provider HTTP `get_current_user` para `src/sidebrain_back/routers/v1/auth_router.py`, deixando `src/sidebrain_back/core/auth.py` apenas com extração Bearer transversal; mapear falha do service para `401` Problem Details com `WWW-Authenticate: Bearer`, preservando `User` como retorno e a assinatura dos endpoints.
- [X] T015 Atualizar imports de `get_current_user` para o novo provider em `src/sidebrain_back/routers/v1/track_router.py`, `src/sidebrain_back/routers/v1/step_router.py`, `src/sidebrain_back/routers/v1/lesson_router.py`, `src/sidebrain_back/routers/v1/quiz_router.py`, `src/sidebrain_back/routers/v1/feedback_router.py`, `src/sidebrain_back/routers/v1/knowledge_assessment_router.py`, `tests/conftest.py`, `tests/integration/test_lesson_hierarchy_queries.py` e `tests/integration/test_quiz_hierarchy_queries.py`; não mudar o contrato funcional dessas rotas.

**Checkpoint**: token e migração funcionam; os testes T003–T006 e a autenticação dos routers existentes identificam as falhas antes dos endpoints novos.

---

## Phase 3: User Story 1 - Criar conta e entrar imediatamente (Priority: P1) 🎯 MVP

**Goal**: cadastrar um único titular por e-mail e devolver token e perfil público.

**Independent Test**: registrar conta, acessar rota protegida com o token, confirmar hash armazenado e nenhuma senha/hash na resposta; caixa diferente e concorrência recebem `409`.

### Tests for User Story 1

- [X] T016 [P] [US1] Escrever contrato de `POST /api/v1/auth/register`: `201` com apenas `accessToken`, `tokenType: "Bearer"`, `user{id,name,email}`; `409` para e-mail reservado; `422` para campos ausentes/extras/proibidos, em `tests/contract/test_user_registration_contract.py`.
- [X] T017 [P] [US1] Escrever integração de cadastro com hash Argon2id, e-mail normalizado, conta excluída reservando endereço e dois cadastros simultâneos resultando em um `201` e um `409`, sem escrita parcial, em `tests/integration/test_user_registration.py`.
- [X] T018 [P] [US1] Escrever testes de schemas para nome com trim e 1–255 caracteres após normalização, e-mail válido com trim/lower e máximo 255, senha mínima de 8, `extra="forbid"` e serialização pública sem `usr_*` em `tests/unit/test_user_auth_schema.py`.

### Implementation for User Story 1

- [X] T019 [US1] Criar `UserRegisterRequest` e `UserResponse` em `src/sidebrain_back/schemas/user_schema.py` com `ConfigDict(from_attributes=True, populate_by_name=True)`, `validation_alias` dos campos físicos `usr_id/usr_name/usr_email` e `serialization_alias` para `id/name/email`, sem hash/timestamps/flags.
- [X] T020 [US1] Criar `AuthResponse` em `src/sidebrain_back/schemas/auth_schema.py` com somente `accessToken`, `tokenType: "Bearer"` e `user: UserResponse`, sem campos físicos do banco.
- [X] T021 [US1] Implementar consulta de e-mail reservado por `lower(btrim(usr_email))`, incluindo excluídos, e `create` em `src/sidebrain_back/repositories/user_repository.py`; deixar o índice único como garantia final contra corrida.
- [X] T022 [US1] Implementar `AuthService.register_user` em `src/sidebrain_back/services/auth_service.py`: normalizar e validar, gerar hash em thread, criar e commitar usuário ativo com versão `0`, converter somente SQLSTATE `23505` da unicidade do e-mail em erro de domínio após rollback e emitir JWT após persistência.
- [X] T023 [US1] Expor `POST /auth/register` público com status `201` e `AuthResponse` em `src/sidebrain_back/routers/v1/auth_router.py` e registrar o router em `src/sidebrain_back/routers/router.py`, usando `Depends(get_auth_service)` e mapeando conflito de domínio em `409` Problem Details sem acessar repository/model no endpoint.

**Checkpoint**: cadastro testável sozinho com JWT aceito por rota protegida preexistente; este é o MVP sugerido.

---

## Phase 4: User Story 2 - Entrar com credenciais existentes (Priority: P1)

**Goal**: autenticar conta ativa por e-mail e senha sem revelar se um endereço existe.

**Independent Test**: criar usuário no fixture, entrar e acessar rota protegida; endereço desconhecido, excluído e senha errada têm o mesmo `401`; UUID puro falha; após cinco falhas o próximo pedido recebe `429`.

### Tests for User Story 2

- [X] T024 [P] [US2] Escrever contrato de `POST /api/v1/auth/login` com `200 AuthResponse`, mesmo `401` para desconhecido/excluído/senha errada, `429 Retry-After`, `422` sem contagem e `503` com Redis indisponível em `tests/contract/test_user_login_contract.py`.
- [X] T025 [P] [US2] Escrever integração de login com e-mail em caixa/espaços diferentes, token válido nos routers existentes, reset do contador no sucesso, cinco falhas em 15 minutos e bloqueio da sexta tentativa inclusive para e-mail desconhecido em `tests/integration/test_user_login.py`.
- [X] T026 [P] [US2] Escrever testes de service para verificação com hash fictício, ausência de diferença pública entre conta inexistente/deletada e senha errada, origem separada e nenhuma senha/token nos logs em `tests/unit/test_auth_service_login.py`.

### Implementation for User Story 2

- [X] T027 [US2] Adicionar `UserLoginRequest` com `email` e `password` obrigatórios, e-mail normalizado e `extra="forbid"` em `src/sidebrain_back/schemas/auth_schema.py`.
- [X] T028 [US2] Implementar `get_by_email` para conta ativa por `lower(btrim(usr_email))` em `src/sidebrain_back/repositories/user_repository.py`, sem usar a consulta de e-mail reservado como prova de login.
- [X] T029 [US2] Implementar `AuthService.login_user` em `src/sidebrain_back/services/auth_service.py`: verificar bloqueio antes do hash, usar hash fictício para conta ausente/deletada, registrar somente falhas de credencial por e-mail normalizado+origem, revalidar bloqueio atomicamente ao finalizar, sinalizar erros de domínio para credencial inválida/bloqueio/Redis indisponível, zerar bucket no sucesso e emitir JWT.
- [X] T030 [US2] Expor `POST /auth/login` público com `200 AuthResponse` em `src/sidebrain_back/routers/v1/auth_router.py`; passar apenas `request.client.host` ao service e mapear erros de domínio para `401` uniforme, `429` com `Retry-After` ou `503` em Problem Details.

**Checkpoint**: login testável com usuário de fixture independentemente do cadastro; token substitui UUID puro em todos os recursos.

---

## Phase 5: User Story 3 - Consultar o próprio perfil (Priority: P1)

**Goal**: consultar somente `id`, `name` e `email` da conta autenticada.

**Independent Test**: GET com token válido retorna seu perfil; Bearer ausente, inválido, expirado, antigo ou de conta excluída retorna `401`; conta indisponível após autenticação retorna `404`.

### Tests for User Story 3

- [X] T031 [P] [US3] Escrever contrato de `GET /api/v1/users/me` com somente `id/name/email`, `401` Problem Details+`WWW-Authenticate: Bearer` e `404` após indisponibilidade tardia em `tests/contract/test_user_profile_read_contract.py`.
- [X] T032 [P] [US3] Escrever integração com JWT real para `GET /users/me` e rota protegida preexistente, recusando UUID puro e conta excluída, em `tests/integration/test_user_profile_read.py`.

### Implementation for User Story 3

- [X] T033 [US3] Implementar `UserService.get_user` e `get_user_service` em `src/sidebrain_back/services/user_service.py` com nova leitura por ID ativo via repository e erro de domínio se a conta ficar indisponível depois da autenticação.
- [X] T034 [US3] Criar `GET /users/me` protegido com `UserResponse` em `src/sidebrain_back/routers/v1/user_router.py` e incluir o router em `src/sidebrain_back/routers/router.py`, usando `Depends(get_current_user)`, `Depends(get_user_service)` e mapeando indisponibilidade tardia em `404`, sem `user_id` do cliente.
- [X] T035 [US3] Substituir o header de teste `Bearer <usr_id>` por JWT real, mantendo a verificação de queries da hierarquia, em `tests/integration/test_lesson_hierarchy_queries.py`.

**Checkpoint**: consulta de perfil independente; identidade sempre deriva do token e é relida antes da resposta.

---

## Phase 6: User Story 4 - Atualizar nome ou e-mail (Priority: P2)

**Goal**: editar apenas nome e/ou e-mail da própria conta, sem afetar senha ou identidade.

**Independent Test**: atualizar cada campo isolado e ambos; corpo vazio/proibido recebe `422`; e-mail de outro titular recebe `409`; o próprio e-mail normalizado não conflita.

### Tests for User Story 4

- [X] T036 [P] [US4] Escrever contrato de `PUT /api/v1/users/me` para `200 UserResponse`, `401/404/409/422`, rejeição de `id`, `password`, hash e flags, em `tests/contract/test_user_profile_update_contract.py`.
- [X] T037 [P] [US4] Escrever integração de alteração de nome, e-mail e ambos, reserva de e-mail por conta excluída, conflito simultâneo entre contas e rollback sem mutação parcial em `tests/integration/test_user_profile_update.py`.

### Implementation for User Story 4

- [X] T038 [US4] Criar `UserUpdateRequest` em `src/sidebrain_back/schemas/user_schema.py` exigindo ao menos um campo não nulo, nome trim de 1–255 caracteres e e-mail válido trim/lower de até 255, com `extra="forbid"`.
- [X] T039 [US4] Implementar `update` de nome/e-mail apenas para usuário ativo em `src/sidebrain_back/repositories/user_repository.py`, sem modificar `usr_password_hash`, `usr_token_version`, `usr_id` ou flags.
- [X] T040 [US4] Implementar `UserService.update_user` em `src/sidebrain_back/services/user_service.py`: reler ativo, aceitar o próprio e-mail normalizado, verificar conflito reservado, commitar, fazer rollback em falha e sinalizar como erro de domínio somente unicidade de e-mail SQLSTATE `23505`.
- [X] T041 [US4] Expor `PUT /users/me` em `src/sidebrain_back/routers/v1/user_router.py` com `UserUpdateRequest`, `UserResponse`, `Depends`, identidade apenas do Bearer e mapeamento de conflito/indisponibilidade em `409/404`.

**Checkpoint**: atualização não permite escolher titular nem alterar credencial.

---

## Phase 7: User Story 5 - Trocar a própria senha (Priority: P2)

**Goal**: trocar senha com prova da atual, revogar tokens antigos e limitar tentativas.

**Independent Test**: trocar com senha atual correta, receber `204` vazio, recusar senha/token antigos e aceitar novo login; cinco erros da senha atual bloqueiam a sexta tentativa por 15 minutos.

### Tests for User Story 5

- [X] T042 [P] [US5] Escrever contrato de `PUT /api/v1/users/me/password` com `204` vazio, `401` por senha atual errada, `404` tardio, `422` para senha nova curta/igual/extra e `429 Retry-After` em `tests/contract/test_user_password_contract.py`.
- [X] T043 [P] [US5] Escrever integração de troca atômica com lock de linha, incremento de `usr_token_version`, recusa imediata de todos os JWT anteriores em `/users/me` e router antigo, login com senha nova e preservação da antiga se falhar em `tests/integration/test_user_password_change.py`.
- [X] T044 [P] [US5] Escrever testes de service/limitador para cinco falhas por conta+origem em 15 minutos, sexta `429` por 15 minutos, bucket separado do login, reset no sucesso, `422` sem contagem e Redis indisponível `503` em `tests/unit/test_user_password_service.py`.

### Implementation for User Story 5

- [X] T045 [US5] Criar `PasswordUpdateRequest` em `src/sidebrain_back/schemas/user_schema.py` com `currentPassword` e `newPassword` obrigatórios, nova senha com mínimo de 8 caracteres e `extra="forbid"`; diferença da atual é validada pelo service após verificar a atual.
- [X] T046 [US5] Implementar leitura ativa sob `FOR UPDATE` e `update_password` em `src/sidebrain_back/repositories/user_repository.py`, persistindo novo `usr_password_hash` e incremento de `usr_token_version` na mesma transação.
- [X] T047 [US5] Implementar `UserService.update_password` em `src/sidebrain_back/services/user_service.py`: conferir senha atual em thread, validar nova diferente, aplicar bucket Redis por conta+origem e bloqueio antes/depois da verificação, commitar atomicamente, sinalizar erros de domínio para senha incorreta/igual/bloqueio/Redis indisponível e zerar apenas este bucket no sucesso.
- [X] T048 [US5] Expor `PUT /users/me/password` em `src/sidebrain_back/routers/v1/user_router.py`, passar origem já extraída, mapear erros de domínio em `401/404/422/429/503` Problem Details e retornar `Response(status_code=204)` sem corpo no sucesso.

**Checkpoint**: senha antiga e todos os tokens anteriores falham após commit; uma nova entrada é necessária.

---

## Phase 8: User Story 6 - Excluir a própria conta (Priority: P2)

**Goal**: encerrar acesso com soft delete sem perder registro ou agregados relacionados.

**Independent Test**: DELETE retorna `204` vazio, conserva usuário/relacionamentos, preenche `usr_deleted_at` e torna login e JWT anterior inválidos.

### Tests for User Story 6

- [X] T049 [P] [US6] Escrever contrato de `DELETE /api/v1/users/me` com `204` vazio, `401` por token inválido/conta já excluída e `404` se a conta ficar indisponível após autenticação em `tests/contract/test_user_delete_contract.py`.
- [X] T050 [P] [US6] Escrever integração de soft delete com `usr_is_deleted=true`, `usr_deleted_at` UTC preenchido, relacionamentos preservados, login/token antigo recusados e rollback sem mudança parcial em `tests/integration/test_user_delete.py`.

### Implementation for User Story 6

- [X] T051 [US6] Implementar `delete` lógico e terminal somente para usuário ativo em `src/sidebrain_back/repositories/user_repository.py`, preenchendo `usr_is_deleted=true` e `usr_deleted_at` no mesmo update, sem remoção física ou cascata.
- [X] T052 [US6] Implementar `UserService.delete_user` em `src/sidebrain_back/services/user_service.py` com nova leitura ativa, commit/rollback e erro de domínio quando a conta desaparecer entre autenticação e mutação.
- [X] T053 [US6] Expor `DELETE /users/me` em `src/sidebrain_back/routers/v1/user_router.py` com `Depends`, mapeamento da indisponibilidade tardia em `404` e `Response(status_code=204)` sem corpo.

**Checkpoint**: exclusão terminal preserva dados relacionados e impede acesso em todos os endpoints protegidos.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: migração de consumidores, documentação, desempenho e gates finais.

- [X] T054 [P] Substituir `usr_password_hash="hash_ana"` do usuário de desenvolvimento por hash Argon2id válido e documentar a credencial apenas para ambiente descartável em `seed.py`, sem executar o script em base com dados.
- [X] T055 [P] Documentar corte coordenado do Bearer UUID, obtenção de `accessToken` por cadastro/login, expiração, hashes legados e pré-auditoria de colisões em `docs/auth_migration.md` e atualizar instruções de autenticação em `README.md`.
- [X] T056 [P] Atualizar exemplos históricos de UUID Bearer para JWT em `specs/SDB-51-quiz-management/quickstart.md`, `specs/SDB-51-quiz-management/contracts/quizzes.md` e `specs/SDB-57-lesson-management/contracts/lessons.md`, preservando os demais contratos.
- [X] T057 Atualizar `docs/architecture.md` para refletir provider HTTP em `routers/v1/auth_router.py`, regras no `AuthService`, consultas no `UserRepository`, versão de credencial e Redis sem dependência de negócio em `core`.
- [X] T058 [P] Criar ensaio com 20 clientes simultâneos e dados válidos, medindo cadastro, login e GET de perfil com pelo menos 95% das respostas em até 2 segundos no ambiente alvo, em `tests/performance/test_auth_profile_performance.py`.
- [X] T059 Registrar validação do contrato com cinco consumidores da API, exigindo ao menos quatro jornadas de cadastro, entrada e consulta sem esclarecimentos adicionais, em `specs/SDB-81-user-auth-profile/consumer-validation.md`.
- [X] T060 Executar `uv run ruff check .`, `uv run pytest`, upgrade/downgrade em banco descartável e todos os cenários de `specs/SDB-81-user-auth-profile/quickstart.md`; registrar resultados e eventuais falhas em `specs/SDB-81-user-auth-profile/validation-results.md`.

## Dependencies & Execution Order

### Phase Dependencies

```text
Setup (T001–T002)
  └─ Foundational (T003–T015)
       ├─ US1 cadastro (T016–T023) ─┐
       ├─ US2 entrada (T024–T030) ──┤
       └─ US3 perfil (T031–T035) ───┼─ Polish (T054–T060)
            ├─ US4 edição (T036–T041)
            ├─ US5 senha (T042–T048)
            └─ US6 exclusão (T049–T053)
```

- **US1 (P1)**: começa após Foundation; o teste usa uma rota protegida já existente. É o MVP mínimo.
- **US2 (P1)**: começa após Foundation e usa usuário de fixture, sem depender do cadastro. Compartilha `auth_service.py` e `auth_router.py` com US1; implementar alterações nesses arquivos em sequência.
- **US3 (P1)**: começa após Foundation com JWT emitido por fixture. Abre `user_service.py` e `user_router.py` para as histórias de perfil.
- **US4, US5, US6 (P2)**: começam após US3 para reutilizar service/router de perfil. Podem ter testes preparados em paralelo, mas a implementação em `user_service.py`, `user_repository.py`, `user_schema.py` e `user_router.py` deve ser coordenada para evitar edições simultâneas.
- **Polish**: documentação e performance podem ser preparadas independentemente; validação final T060 depende de todas as histórias e do corte documentado. T059 depende dos contratos públicos implementados e de consumidores disponíveis.

### Within Each User Story

1. Escrever testes de contrato, unidade e integração da fase; confirmar falha por comportamento ausente.
2. Implementar schema/model/repository necessário, depois service e endpoint.
3. Executar os testes da história e verificar o critério independente antes de avançar.

## Parallel Execution Examples

- **US1**: T016 (`tests/contract/test_user_registration_contract.py`), T017 (`tests/integration/test_user_registration.py`) e T018 (`tests/unit/test_user_auth_schema.py`) podem ser escritos em paralelo; T019–T023 seguem a ordem de dependências.
- **US2**: T024 (`tests/contract/test_user_login_contract.py`), T025 (`tests/integration/test_user_login.py`) e T026 (`tests/unit/test_auth_service_login.py`) são independentes; T027–T030 seguem em sequência.
- **US3**: T031 (`tests/contract/test_user_profile_read_contract.py`) e T032 (`tests/integration/test_user_profile_read.py`) podem avançar juntos; T033–T035 dependem do provider comum.
- **US4**: T036 e T037 usam arquivos distintos e podem ser escritos juntos; T038–T041 compartilham o fluxo de perfil.
- **US5**: T042, T043 e T044 podem ser escritos juntos; T045–T048 dependem da mesma mutação de senha.
- **US6**: T049 e T050 podem ser escritos juntos; T051–T053 formam a cadeia de exclusão.
- **Cross-cutting**: T054, T055, T056 e T058 usam arquivos separados, desde que o contrato esteja estabilizado; T059 e T060 são gates de fechamento.

## Implementation Strategy

### MVP First

Concluir Setup, Foundation e US1; validar cadastro, unicidade case-insensitive, hash persistido, token de 60 minutos e acesso a uma rota protegida existente. Isso permite demonstrar a primeira jornada sem antecipar atualização ou exclusão de perfil.

### Incremental Delivery

Concluir US2 e US3 para formar o fluxo completo de entrada e consulta. Depois entregar US4, US5 e US6, validando cada história isoladamente. O corte de produção do Bearer UUID exige todos os clientes preparados, dados legados auditados e os gates finais T058–T060.

## Notes

- `[P]` indica tarefas sem sobreposição de arquivos nem dependência imediata; não indica que toda uma história possa modificar os mesmos módulos em paralelo.
- Não adicionar refresh token, recuperação por e-mail, OAuth, roles ou side effects de streak/login nesta feature.
- Todo erro público segue Problem Details; respostas `204` têm corpo vazio.
