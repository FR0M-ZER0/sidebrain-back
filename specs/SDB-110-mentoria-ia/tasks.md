---
description: "Tarefas de implementação da mentoria de aprendizagem por IA"
---

# Tasks: Mentoria de aprendizagem por IA

**Input**: `specs/SDB-110-mentoria-ia/plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/mentoria.md` e `quickstart.md`.

**Testes**: incluídos por exigência da constituição e dos critérios verificáveis da especificação. Escrever os testes de cada história antes da respectiva implementação e confirmar que falham pelo motivo esperado.

**Formato**: `[ID] [P?] [Story?] Descrição e caminho`. `[P]` indica tarefas que podem ser feitas em paralelo após suas dependências e sem editar os mesmos arquivos.

## Phase 1: Setup

- [X] T001 Conferir ambiente e infraestrutura existentes, executar `uv sync` e registrar comandos de API, worker e banco de testes em `specs/SDB-110-mentoria-ia/quickstart.md`, preservando instruções válidas.
- [X] T002 Conferir a revisão Alembic atual e os padrões de autenticação, providers e testes em `migrations/env.py`, `src/sidebrain_back/routers/v1/track_router.py` e `tests/conftest.py` antes de criar a migração.

## Phase 2: Foundational

**Objetivo**: preparar persistência, controle de acesso, autorização e coordenação para as três histórias.

- [X] T003 [P] Criar testes de migração e integridade para entidades de mentoria, unicidade e upgrade/downgrade em `tests/integration/test_mentor_migration.py`.
- [X] T004 [P] Criar testes de contrato para consulta, aceite específico, versão obsoleta, revogação e autenticação do aviso em `tests/contract/test_mentor_consent_contract.py`.
- [ ] T005 [P] Criar testes de concorrência de lock e reserva durável por usuário em `tests/integration/test_mentor_lock.py`, `tests/integration/test_mentor_processing_service.py` e `tests/integration/test_mentor_http_lifecycle.py`, incluindo perda de conexão após reserva com worker ativo, revogação/exclusão `503` e bloqueio mantido até comprovação de encerramento. Há testes de perda de conexão e reserva simulada; falta reproduzir a perda com worker ativo e operação concorrente.
- [X] T006 Criar modelo de autorização em `src/sidebrain_back/models/mentor_consent_model.py`: `user_id` dono autenticado, **“uma autorização corrente por usuário e finalidade”**, `notice_version`, `granted_at` e `revoked_at` opcional; não armazenar conteúdo ou credenciais.
- [X] T007 Criar modelo de conversa em `src/sidebrain_back/models/mentor_conversation_model.py` com `id`, `user_id`, `track_id`, `created_at`, `updated_at`; **“trilha fixa e de propriedade do usuário na criação e no uso”** e múltiplas conversas por trilha.
- [X] T008 Criar modelo de mensagem em `src/sidebrain_back/models/mentor_message_model.py` com `id`, `conversation_id`, `sequence`, `role` **“`student` ou `mentor`”**, `content`, `created_at`; **“`(conversation_id, sequence)` é único”** e cada geração admite no máximo uma resposta.
- [X] T009 Criar modelos de geração, despacho, reserva durável e bloqueio de privacidade em `src/sidebrain_back/models/mentor_generation_model.py` com IDs, prazo e identificador de tentativa, timestamps, erro sanitizado e chave por conversa; estados **“`queued → processing → completed | failed`”**, no máximo uma geração não terminal, reserva `in_flight|finished` sem conteúdo e despacho apenas com identificadores e estado.
- [X] T010 Registrar os modelos em `src/sidebrain_back/models/__init__.py` e `migrations/env.py`; criar `migrations/versions/sdb110_cria_mentoria.py` com revisão única e `down_revision` atual, FKs, índices, constraints e downgrade estrutural reversível, sem prometer restaurar conteúdo apagado.
- [X] T011 Implementar lock consultivo de sessão por usuário em `src/sidebrain_back/core/mentor_lock.py`, com conexão dedicada, timeout, liberação em `finally` e invalidação em perda da conexão, sem transação aberta durante chamada externa.
- [X] T012 Criar schemas de autorização em `src/sidebrain_back/schemas/mentor_consent_schema.py`: aviso versionado, destinatário, finalidade e categorias; aceite apenas de versão corrente com `accepted=true`, schemas configurados conforme convenções do projeto.
- [X] T013 Criar operações de persistência por usuário em `src/sidebrain_back/repositories/mentor_consent_repository.py` e estados ausente, ativa, revogada e desatualizada, sem conteúdo de conversa.
- [X] T014 Implementar aviso, aceite e revogação em `src/sidebrain_back/services/mentor_consent_service.py`; bloquear novas reservas transacionalmente, aguardar chamadas em curso e, diante de reserva inconclusiva, manter bloqueio e retornar erro traduzido para `503`, sem confirmar revogação ou apagar histórico.
- [X] T015 Criar `GET`, `PUT` e `DELETE /api/v1/mentor-consent` em `src/sidebrain_back/routers/v1/mentor_consent_router.py`, com `get_current_user`, `Depends` e Problem Details; registrar em `src/sidebrain_back/routers/router.py`.
- [ ] T016 Validar que os testes de `tests/integration/test_mentor_migration.py`, `tests/integration/test_mentor_lock.py` e `tests/contract/test_mentor_consent_contract.py` passam; os testes existentes passam, mas a cobertura concorrente de T005 ainda está incompleta.

## Phase 3: User Story 1 — Receber orientação para estudar (P1)

**Objetivo**: permitir solicitação autenticada de mentoria para uma trilha própria, com orientação assíncrona, independente e segura.

**Teste independente**: criar trilha e conversa próprias, aceitar o aviso e enviar objetivo e dificuldade; conferir orientação completa com prioridade, justificativa e ação prática, sem solução integral. Sem autorização, nenhuma chamada externa ocorre.

### Testes

- [X] T017 [P] [US1] Criar testes de contrato de criação de conversa, submissão, consulta de geração e leitura individual da resposta concluída, incluindo 404 de terceiros, retry, validação, autenticação, idempotência e Problem Details em `tests/contract/test_mentor_generation_contract.py` e `tests/integration/test_mentor_http_lifecycle.py`.
- [X] T018 [P] [US1] Criar testes unitários de prompt, redirecionamento de pedidos fora do estudo para mentoria, contexto insuficiente, rejeição de saída vazia/inválida, segurança e timeout em `tests/unit/test_mentor_generator_service.py`.
- [ ] T019 [P] [US1] Criar testes de integração de consentimento, entrega repetida, falha de despacho e de worker em `processing`, recuperação por tentativa, bloqueio de envio inconclusivo, retry e ausência de resposta parcial em `tests/integration/test_mentor_generation_repository.py`, `tests/integration/test_mentor_processing_service.py`, `tests/integration/test_mentor_dispatch_service.py`, `tests/integration/test_mentor_http_lifecycle.py` e `tests/unit/test_mentor_dispatch_task.py`. Falta o ensaio com worker e broker reais.

### Implementação

- [X] T020 [P] [US1] Criar schemas em `src/sidebrain_back/schemas/mentor_schema.py` com campos de conversa, mensagem, geração e retry; mensagem **“Conteúdo não vazio e limitado a 4.000 caracteres por mensagem do estudante”**, `extra` proibido, chave UUID e paginação padrão.
- [X] T021 [P] [US1] Implementar acesso a conversas próprias e trilhas ativas em `src/sidebrain_back/repositories/mentor_conversation_repository.py`; `track_id` imutável, listagens por `updated_at` e `id`, com filtros de proprietário.
- [X] T022 [US1] Implementar mensagens, geração, despacho, reserva durável e bloqueio de privacidade transacionais em `src/sidebrain_back/repositories/mentor_generation_repository.py`: sequência monotônica, tentativas identificadas, prazo, estados e unicidade de resposta; serializar nova reserva com revogação/exclusão e impedir publicação de tentativa obsoleta; chave repetida com mesmo payload retorna operação existente e payload diferente gera conflito.
- [X] T023 [US1] Implementar gerador em `src/sidebrain_back/services/mentor_generator_service.py`, usando `core/llm_client.py` por injeção, timeout inicial configurável de 30 segundos, instruções separadas de dados não confiáveis e validação estrutural da resposta completa; orientar autonomia, redirecionar solicitações sem relação com estudo à mentoria, respeitar limites de segurança e reconhecer contexto insuficiente sem inventar fatos.
- [X] T024 [US1] Implementar criação de conversa, submissão e consulta em `src/sidebrain_back/services/mentor_service.py`: verificar trilha própria, autorização atual, uma geração ativa por conversa, mensagem e despacho atômicos; retornar conflito ou erro apropriado sem chamar provedor no serviço HTTP.
- [X] T025 [US1] Implementar processamento e retry limitado em `src/sidebrain_back/tasks/mentor_generation_task.py`: apenas IDs no broker, lock de T011 e reserva durável confirmada antes do envio; revalidar autorização e tentativa antes de publicar, encerrar reserva apenas quando o processo não puder mais enviar, descartar resultados obsoletos e não publicar resposta parcial; registrar task em `src/sidebrain_back/core/celery_app.py`.
- [X] T026 [US1] Implementar recuperação periódica em `src/sidebrain_back/tasks/mentor_dispatch_task.py` e agendamento em `src/sidebrain_back/core/celery_app.py`: recuperar despachos `queued` e detectar `processing` expirado por tentativa; reenfileirar apenas sem reserva inconclusiva e com limite de retries, ou marcar `failed` mantendo bloqueio até comprovação operacional de encerramento; impedir publicação por tentativa antiga.
- [X] T027 [US1] Implementar nova tentativa explícita idempotente para geração `failed` em `src/sidebrain_back/services/mentor_service.py`, associando nova geração à mesma mensagem, recusando se outra estiver ativa e retornando erro traduzido para `503` enquanto persistir reserva inconclusiva.
- [X] T028 [US1] Expor criação de conversa, envio, consulta de geração, consulta individual da mensagem concluída e retry em `src/sidebrain_back/routers/v1/mentor_router.py`, com consulta autorizada no `src/sidebrain_back/services/mentor_service.py` e `src/sidebrain_back/repositories/mentor_conversation_repository.py`; registrar em `src/sidebrain_back/routers/router.py` e aplicar os contratos de `specs/SDB-110-mentoria-ia/contracts/mentoria.md`.
- [X] T029 [US1] Executar os testes `tests/contract/test_mentor_generation_contract.py`, `tests/unit/test_mentor_generator_service.py` e `tests/integration/test_mentor_http_lifecycle.py`; corrigir falhas e demonstrar orientação com provedor de teste.

**Checkpoint**: fluxo básico demonstrável; ainda faltam o contexto enriquecido e o ciclo completo de histórico/exclusão exigidos pela feature.

## Phase 4: User Story 2 — Usar o contexto do aprendizado (P2)

**Objetivo**: fundamentar a orientação em dados pertinentes e comprovadamente ligados à trilha escolhida.

**Teste independente**: montar duas trilhas do mesmo usuário e uma de outro usuário, com e sem avaliação ligada; capturar o contexto enviado e verificar que só a trilha escolhida e os dados autorizados são usados, reconhecendo ausência e incertezas.

### Testes

- [X] T030 [P] [US2] Criar testes de projeção mínima, orçamento de contexto, avaliação pulada/antiga e dados conflitantes em `tests/unit/test_mentor_context_service.py`, `tests/integration/test_mentor_context_isolation.py` e `specs/SDB-110-mentoria-ia/quickstart.md`.
- [X] T031 [P] [US2] Criar testes de integração com dois usuários, duas trilhas, respostas de terceiros e avaliações ligadas ou não em `tests/integration/test_mentor_context_isolation.py` e `tests/integration/test_mentor_processing_service.py`; inspecionar o payload do provedor.
- [X] T032 [P] [US2] Criar testes de contrato para aviso, bloqueio por autorização ausente ou revogada e resposta a trilha de terceiro em `tests/contract/test_mentor_consent_contract.py` e `tests/integration/test_mentor_http_lifecycle.py`.

### Implementação

- [X] T033 [P] [US2] Implementar projeção específica em `src/sidebrain_back/repositories/mentor_context_repository.py`, filtrando dono e exclusões em `Answer → Quiz → Lesson → Step → Track`, sem carregar feedback ou respostas de terceiros.
- [X] T034 [US2] Implementar consulta de avaliação vinculada em `src/sidebrain_back/repositories/mentor_context_repository.py` pelo caminho `Track.trk_generation_request_id → GenerationRequest.assessment_id → KnowledgeAssessment`, verificando ambos os donos; omitir avaliação sem vínculo confiável.
- [X] T035 [US2] Criar montagem transitória em `src/sidebrain_back/services/mentor_context_service.py`, com orçamento configurável, progresso, datas e proveniência; avaliação `skipped` não é medição e dados antigos ou ausentes não são fatos atuais.
- [X] T036 [US2] Integrar projeção ao gerador e à task em `src/sidebrain_back/services/mentor_generator_service.py` e `src/sidebrain_back/tasks/mentor_generation_task.py`, sem cache global, RAG, dados de outras trilhas ou modificações no progresso.
- [X] T037 [US2] Executar `tests/unit/test_mentor_context_service.py`, `tests/integration/test_mentor_context_isolation.py`, `tests/contract/test_mentor_consent_contract.py` e `tests/integration/test_mentor_http_lifecycle.py`, validando a fundamentação e o isolamento.

**Checkpoint**: recomendações utilizam apenas contexto comprovadamente pertinente, inclusive no caso de trilhas legadas sem avaliação.

## Phase 5: User Story 3 — Aprofundar uma orientação (P2)

**Objetivo**: continuar e consultar conversas, excluir uma conversa ou todo o histórico e impedir republicação após exclusão.

**Teste independente**: criar conversas na mesma trilha, continuar uma com uma restrição e verificar histórico ordenado; excluir uma e depois todas, confirmando remoção física, isolamento entre usuários e ausência de recriação por tarefa tardia.

### Testes

- [X] T038 [P] [US3] Criar testes de contrato para listagem paginada, histórico ordenado, exclusão individual/em massa e 404 indistinto em `tests/contract/test_mentor_conversation_contract.py`.
- [ ] T039 [P] [US3] Criar testes de integração para histórico independente, exclusão física, exclusão de trilha/conta, concorrência com worker e revogação em `tests/integration/test_mentor_service.py`, `tests/integration/test_mentor_http_lifecycle.py`, `tests/integration/test_mentor_parent_deletion.py` e `tests/integration/test_mentor_lock.py`. Falta reproduzir concorrência com worker ativo.
- [X] T040 [P] [US3] Criar testes unitários de seleção limitada do histórico da própria conversa e adaptação a mensagem posterior em `tests/unit/test_mentor_conversation_service.py`.

### Implementação

- [X] T041 [US3] Implementar listagem paginada e consulta das mensagens por sequência em `src/sidebrain_back/repositories/mentor_conversation_repository.py`; retornar somente histórico da conversa própria, com página e tamanho conforme `src/sidebrain_back/schemas/pagination_schema.py`.
- [X] T042 [US3] Integrar mensagens anteriores pertinentes da mesma conversa ao contexto em `src/sidebrain_back/services/mentor_context_service.py`; respeitar orçamento e priorizar mensagem atual sem incluir outras conversas.
- [X] T043 [US3] Implementar exclusão física individual e em massa em `src/sidebrain_back/repositories/mentor_conversation_repository.py` e `src/sidebrain_back/services/mentor_service.py`: bloquear novas reservas transacionalmente; retornar `503` mantendo bloqueio se houver envio inconclusivo; após término comprovado, remover mensagens, gerações e despachos sem afetar trilhas ou outros usuários.
- [X] T044 [US3] Integrar a remoção do conteúdo de mentoria aos fluxos de exclusão lógica em `src/sidebrain_back/services/track_service.py` e `src/sidebrain_back/services/user_service.py`, coordenando lock e tarefas pendentes para impedir órfãos ou republicação.
- [X] T045 [US3] Expor listagem e consulta de conversas, listagem de mensagens e exclusões individual/em massa em `src/sidebrain_back/routers/v1/mentor_router.py`, respeitando paginação, autenticação e Problem Details.
- [ ] T046 [US3] Executar `tests/contract/test_mentor_conversation_contract.py`, `tests/integration/test_mentor_http_lifecycle.py`, `tests/integration/test_mentor_parent_deletion.py`, `tests/integration/test_mentor_lock.py` e `tests/unit/test_mentor_conversation_service.py`; validar exclusão após chamada em andamento e falha de conexão do lock. Os testes existentes passam; falta o ensaio concorrente com worker ativo descrito em T005.

**Checkpoint**: histórico, continuação e exclusão atendem à especificação e preservam o isolamento.

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T047 [P] Revisar configuração e ausência de texto privado em logs, fila, resultados e erros em `src/sidebrain_back/tasks/mentor_generation_task.py`, `src/sidebrain_back/services/mentor_service.py`, `tests/integration/test_mentor_processing_service.py` e `tests/integration/test_mentor_privacy_logging.py`.
- [X] T048 [P] Documentar o provedor efetivamente configurado, sua retenção e processo de exclusão em `docs/mentor_privacy.md`; incluir procedimento autorizado de comprovação de encerramento de worker e resolução de reserva inconclusiva, e registrar que produção depende de validação operacional e jurídica.
- [X] T049 Preparar rubrica e executar avaliação conforme SC-001 a SC-006 em `specs/SDB-110-mentoria-ia/quickstart.md`: 20 solicitações, 20 pedidos de resolução, 10 conversas e 10 cenários sintéticos; registrar amostragem, resultados e limitações sem afirmar que mocks comprovam qualidade ou que a avaliação equivale a um teste com estudantes reais.
- [ ] T050 Executar os cenários de `specs/SDB-110-mentoria-ia/quickstart.md`, upgrade/downgrade em banco descartável, `uv run pytest` e `uv run ruff check .`; registrar resultados e impedimentos em `specs/SDB-110-mentoria-ia/quickstart.md`.

## Dependencies & Execution Order

### Phase Dependencies

- Setup → Foundational → US1 → US2 e US3 → Polish.
- US1 fornece a geração e o contrato usados pelas demais. US2 e US3 podem ter **testes** preparados em paralelo após a base; sua implementação deve integrar sobre US1. US2 e US3 compartilham `mentor_context_service.py` e outros arquivos: coordenar integrações, não editar os mesmos arquivos simultaneamente.
- Consentimento e lock são fundamentais ao MVP; não adiar sua verificação até US2. A exclusão completa e o isolamento de contexto são requisitos da feature, não melhorias opcionais.
- T049 depende de serviço integrado e de cenários sintéticos avaliados; T050 depende da integração e dos ambientes necessários. Não declarar as metas como cumpridas sem medições.

### User Story Dependencies

- **US1**: depende de T001–T016; testa envio e orientação usando dados mínimos informados pelo estudante.
- **US2**: depende da base e da geração de US1; pode ser validada com chamadas controladas e dados de teste.
- **US3**: depende da base e da geração de US1; pode ser validada com históricos e provedor controlado, sem exigir conclusão de US2.

### Parallel Opportunities

- Preparar T003–T005 em arquivos de teste distintos; preparar T017–T019, T030–T032 e T038–T040 em paralelo dentro de cada história, após suas dependências.
- T020 e T021 podem ser desenvolvidas em paralelo após a base; T033 pode avançar enquanto os testes de US3 são preparados.
- T047 e T048 podem ocorrer em paralelo após a integração das histórias; T049 e T050 devem ser coordenadas porque ambas atualizam o quickstart.

## Parallel Examples

- **US1**: T017 testa o contrato HTTP enquanto T018 testa o gerador e T019 cobre falhas transacionais, em arquivos separados.
- **US2**: T030 testa a montagem do contexto enquanto T031 verifica isolamento em banco e T032 cobre o contrato de autorização.
- **US3**: T038 testa o contrato enquanto T039 verifica concorrência/exclusão e T040 exercita o histórico.

## Implementation Strategy

1. Concluir setup e base, incluindo autorização e coordenação segura.
2. Entregar US1 como **MVP de demonstração controlada**, com validação independente.
3. Acrescentar US2 e US3, respeitando dependências e evitando alterações simultâneas nos mesmos arquivos.
4. Antes de liberar a feature a usuários reais, concluir todas as histórias, testes de privacidade/exclusão, validação da política do provedor e medições aplicáveis; a demonstração de US1 sozinha não satisfaz a spec completa.
