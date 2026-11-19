# Tarefas da SDB-109 — Acompanhamento de jobs por WebSocket

**Origem** · [Plano](plan.md), [especificação](spec.md), [pesquisa](research.md), [dados](data-model.md), [contrato](contracts/job-updates.md) e [quickstart](quickstart.md).

**Organização** · Cinco histórias, em ordem de prioridade, precedidas pela preparação e pela infraestrutura compartilhada. Os testes atendem aos cenários obrigatórios da especificação e ao princípio IV da constituição. Escrever cada teste de história antes da implementação correspondente e confirmar que detecta a ausência do comportamento.

**Formato** · Cada tarefa contém ID sequencial e caminho relativo à raiz. `[P]` indica trabalho em arquivos distintos que pode ocorrer em paralelo depois dos pré-requisitos da fase. `[USn]` liga a tarefa à história. Arquivos novos têm nomes propostos concretos. Providers ficam junto às respectivas classes, com composição por `Depends` e sessões curtas de banco. Tasks Celery delegam regras de negócio a serviços.

## Fase 1 — Preparação

**Objetivo** · Preparar a validação usando a instalação e os serviços existentes.

- [X] T001 Conferir as dependências instaladas por `uv sync`, os comandos de API/worker e as configurações de PostgreSQL/Redis em `pyproject.toml`, `uv.lock`, `docker-compose.yml` e `.env.example`, registrando no `specs/SDB-109-websocket-job-updates/quickstart.md` qualquer ajuste necessário para executar os ensaios locais.
- [ ] T002 Preparar fixtures reutilizáveis em `tests/conftest.py` para dois usuários, recursos próprios/alheios, Redis com prefixo exclusivo por teste, banco descartável, provedor determinístico e barreiras de execução entre API e worker, com limpeza após cada cenário.

## Fase 2 — Fundamentos compartilhados

**Objetivo** · Disponibilizar dados que permitem autorizar os quatro canais e infraestrutura para observar commits. Esta fase bloqueia a implementação das histórias.

- [X] T003 [P] Criar `src/sidebrain_back/models/step_preparation_model.py` com “`task_id` chave primária”, “`user_id`, `track_id`, `source_step_id`, `target_step_id` com referências às entidades”, estados `pending | completed | failed`, “`created_at` e `finished_at` UTC com fuso” e “a presença de `finished_at` exatamente nos estados terminais”, permitindo várias tarefas por etapa e indexando o instante terminal conforme `data-model.md`.
- [X] T004 [P] Criar `src/sidebrain_back/models/step_summary_generation_model.py` com “Uma linha por `step_id` (PK/FK)”, “`generation` inteiro crescente positivo” e “`status` restrito a `pending | completed | failed`”, derivando dono/trilha da etapa e usando `Step.stp_summary` como texto canônico conforme `data-model.md`.
- [X] T005 Registrar os modelos em `src/sidebrain_back/models/__init__.py` e criar `migrations/versions/sdb109_job_updates.py`, ligada ao head vigente, com as duas tabelas, constraints, índices e gatilhos de `pg_notify` para inserções/mudanças observáveis nas duas tabelas novas, em `generation_request` e em `knowledge_assessment`; emitir só canal/chave e fornecer downgrade completo da revisão.
- [X] T006 Criar `src/sidebrain_back/repositories/step_preparation_repository.py` e `src/sidebrain_back/repositories/step_summary_generation_repository.py` com providers, consultas por posse, reserva e transições condicionais; aplicar a disponibilidade “`finished_at IS NULL`” ou instante estritamente anterior a “`finished_at + 24 horas`”, preservar o primeiro instante terminal e implementar incremento atômico e bloqueio da revisão de sumário.
- [X] T007 Implementar o listener técnico em `src/sidebrain_back/core/job_notifications.py` e seu ciclo de vida em `src/main.py`, com uma conexão PostgreSQL por processo, confirmação de LISTEN, registro/remoção de consumidores por canal/chave, sinal de releitura coalescido, sinalização de perda da escuta e fechamento no lifespan; manter o módulo core independente dos schemas e serviços de domínio.
- [ ] T008 Validar em `tests/integration/test_job_update_migration.py` e `tests/integration/test_job_notifications.py` as constraints, upgrade/downgrade com dados anteriores, sumário legado, notificações só após commit, ausência após rollback, distribuição entre conexões e remoção dos consumidores; executar os testes desta fase antes de iniciar US1.

**Marco verificável** · Migração reversível e listener entregando avisos apenas de alterações confirmadas. Os registros novos permitem criar fixtures autorizáveis dos quatro canais.

## Fase 3 — US1 · Autorizar o acompanhamento (P1)

**Objetivo** · Emitir ticket temporário restrito ao dono/recurso e aceitar uma inscrição correspondente.

**Teste independente** · Com estados persistidos por fixtures, emitir tickets para os quatro canais, abrir sockets, receber o snapshot e disputar o mesmo ticket entre duas instâncias. Recursos alheios, removidos e inexistentes produzem a mesma resposta pública.

### Testes

- [ ] T009 [P] [US1] Criar `tests/contract/test_ws_ticket_contract.py` cobrindo 200 com `ticket` e `Cache-Control: no-store`, 401, 422, 404 indistinguível e 503 em Problem Details, inclusive UUIDs, chave composta, canal desconhecido, ID vazio e credencial inválida.
- [ ] T010 [P] [US1] Criar `tests/integration/test_ws_ticket_consumption.py` cobrindo TTL de 60 segundos, consumo atômico concorrente por duas instâncias, ticket ausente/inválido/reutilizado, falha do Redis e conexão já autorizada que continua após a expiração do ticket.
- [ ] T011 [P] [US1] Criar `tests/contract/test_job_subscription_contract.py` cobrindo inscrição válida, snapshot dos quatro canais por fixtures, repetição idêntica, divergência de escopo, mensagens binárias/malformadas/tipo desconhecido e erro correlacionado ao par autorizado seguido de fechamento.

### Implementação

- [X] T012 [US1] Criar os schemas em `src/sidebrain_back/schemas/job_update_schema.py` para ticket, subscribe, escopo e envelopes públicos, com `ConfigDict(from_attributes=True, populate_by_name=True)`; validar UUID de solicitação/diagnóstico, preparação como “string opaca não vazia” e sumário como “Dois UUIDs unidos por um único `:`, na ordem trilha e etapa”; definir os quatro payloads e sua nulabilidade conforme `contracts/job-updates.md`.
- [X] T013 [US1] Implementar armazenamento de ticket em `src/sidebrain_back/core/ws_tickets.py`, usando segredo aleatório de 32 bytes, hash na chave com prefixo de ambiente, escopo completo, SET NX EX 60 e GETDEL; fornecer cliente pelo provider e fechar seu pool em `src/main.py`, preservando o significado “Emissão inicia TTL de 60 s. Consumo atômico ou expiração removem a chave.”.
- [X] T014 [US1] Criar `src/sidebrain_back/repositories/job_update_repository.py` e `src/sidebrain_back/services/job_update_service.py` para obter snapshots e autorizar todos os canais, consultando conta, dono, trilha ativa, vínculo exato da etapa, origem/destino da preparação e expiração; projetar schemas públicos, tratar sumário legado e usar `Recurso indisponível.` para ausência/falta de acesso, com sessão nova por leitura e sem objetos WebSocket no serviço.
- [X] T015 [US1] Adicionar emissão de ticket em `src/sidebrain_back/routers/v1/auth_router.py`, usando `get_current_user` e serviço injetado; registrar `src/sidebrain_back/routers/v1/job_update_router.py` em `src/sidebrain_back/routers/router.py`, consumir o ticket antes do upgrade, comparar a inscrição canônica, revalidar acesso e enviar snapshot, com um único emissor e liberação básica em finally.
- [ ] T016 [US1] Integrar em `src/sidebrain_back/services/job_update_service.py` e `src/sidebrain_back/routers/v1/job_update_router.py` os erros de domínio/infraestrutura e os códigos de fechamento 1008/1011 previstos no contrato, deduplicar inscrições e garantir que erro de inscrição use o escopo autorizado; executar T009–T011 e corrigir falhas até todos os cenários passarem.

**Marco verificável** · Autorização e snapshot funcionam com dados de teste dos quatro canais. Este é o primeiro incremento demonstrável.

## Fase 4 — US2 · Resultado da geração de trilha (P1)

**Objetivo** · Entregar pending, succeeded e failed de uma geração real, inclusive quando concluída antes da conexão.

**Teste independente** · Iniciar trilha pelo HTTP existente, conectar pelo request_id e observar sucesso/falha com worker em outro processo, conferindo que o conteúdo está disponível após o sucesso.

- [ ] T017 [P] [US2] Criar `tests/contract/test_track_job_updates.py` para request_id correlacionado, estados pending/succeeded/failed, track_id nulo fora de sucesso, error_code nulo fora de falha e resultado terminal anterior à inscrição.
- [ ] T018 [P] [US2] Criar `tests/integration/test_track_job_producer.py` para commit do conteúdo antes da entrega, retry seguido de sucesso, esgotamento, exceção definitiva inesperada, reentrega e tentativa tardia de sobrescrever um terminal, incluindo worker separado da API.
- [ ] T019 [US2] Proteger a transição `pending → succeeded / failed` em `src/sidebrain_back/repositories/generation_request_repository.py` e a confirmação conjunta de trilha/estado em `src/sidebrain_back/services/generation_service.py`; adaptar `src/sidebrain_back/tasks/generate_track_task.py` para delegar persistência de falha ao serviço, tratar esgotamento real de retry e exceções definitivas após rollback e manter retries transitórios pendentes.
- [ ] T020 [US2] Integrar o acompanhamento contínuo em `src/sidebrain_back/services/job_update_service.py` e `src/sidebrain_back/routers/v1/job_update_router.py`, aguardando LISTEN e registrando consumidor antes do snapshot, limpando o sinal antes de ler, relendo após avisos e reautorizando antes de cada envio; suprimir duplicatas/regressões da mesma execução e executar T017–T018 e a regressão de `tests/unit/test_track_sse.py`.

**Marco verificável** · Uma trilha iniciada pelo contrato vigente chega ao terminal pelo socket com posse verificada.

## Fase 5 — US3 · Diagnóstico, preparação e sumário (P1)

**Objetivo** · Completar os canais restantes, com expiração verificável e precedência da geração mais recente de sumário.

**Teste independente** · Para cada canal, iniciar pelo endpoint vigente, observar sucesso/falha e reconectar. Disputar dois sumários da mesma etapa e verificar a preparação imediatamente antes e no instante de completar 24 horas.

### Testes

- [ ] T021 [P] [US3] Criar `tests/contract/test_assessment_job_updates.py` cobrindo pending, generated/skipped/completed como completed, failed, perguntas vazias nas situações previstas, ordem pública de perguntas/alternativas e ausência de gabarito; restringir códigos de falha a generation_failed/invalid_generation_result.
- [ ] T022 [P] [US3] Criar `tests/integration/test_step_preparation_job.py` para despacho por prepare-next e por progresso do quiz, vínculo reservado antes do worker, conteúdo já existente, alvo removido, retries, falha definitiva, despacho incerto/reentrega e limite de 24 horas tanto no ticket quanto na inscrição, mantendo o instante terminal original.
- [ ] T023 [P] [US3] Criar `tests/integration/test_step_summary_job.py` para gerações A/B concluídas fora de ordem, falha tardia de A, combinações POST/quiz, revisão pendente antes do cálculo, rollback do quiz após cálculo, texto legado e coincidência do resultado vigente no socket, reconexão e GET do sumário.

### Implementação

- [ ] T024 [US3] Integrar `src/sidebrain_back/services/knowledge_assessment_service.py` e `src/sidebrain_back/tasks/knowledge_assessment_task.py` à confirmação de perguntas/estado e às falhas definitivas após rollback; ajustar a projeção em `src/sidebrain_back/services/job_update_service.py` para generated/skipped/completed, preservando o contrato legado da task e a representação pública de `src/sidebrain_back/schemas/knowledge_assessment_schema.py`.
- [ ] T025 [US3] Criar `src/sidebrain_back/services/step_preparation_service.py` e integrar ambos os despachos de `src/sidebrain_back/services/track_service.py`, reservando task_id e vínculo persistido antes de `apply_async(task_id=...)`; preservar accepted/skipped e o ID da etapa de destino, tratar falha confirmada e entrega incerta com repetição limitada pelo mesmo ID e consumo idempotente.
- [ ] T026 [US3] Integrar `src/sidebrain_back/tasks/prepare_next_step_content_task.py` ao serviço de `src/sidebrain_back/services/step_preparation_service.py`, movendo para o serviço a persistência/orquestração de domínio necessária para confirmar conteúdo e terminal na mesma transação; usar bloqueio e guarda terminal por task_id, considerar conteúdo já existente como sucesso, deixar retry transitório pendente e persistir failed após rollback definitivo, preservando execução de mensagens antigas.
- [X] T027 [US3] Integrar a revisão em `src/sidebrain_back/services/step_summary_service.py` e `src/sidebrain_back/repositories/step_summary_repository.py`, reservando geração em transação curta e condicionando à revisão vigente a gravação de `stp_summary` e o terminal; confirmar texto/estado juntos, descartar escrita obsoleta e marcar failed após rollback somente para a revisão ainda vigente.
- [X] T028 [US3] Integrar a reserva e confirmação de sumário em `src/sidebrain_back/services/step_service.py` e `src/sidebrain_back/services/quiz_service.py`, reservando em sessão independente antes de bloqueios conflitantes, calculando com a resposta ainda não confirmada visível à transação do quiz e confirmando sucesso junto de resposta/progresso/XP; preservar resultado HTTP de cada chamada e persistir falha da revisão vigente se o commit do quiz falhar.
- [X] T029 [US3] Completar snapshots e validação da revisão imediatamente antes do envio em `src/sidebrain_back/services/job_update_service.py` e `src/sidebrain_back/repositories/job_update_repository.py`, incluindo TTL da preparação calculado pelo banco, sumário legado, pendência sem exposição do texto anterior e supressão de resultados de gerações substituídas; conferir os payloads em `src/sidebrain_back/schemas/job_update_schema.py`.
- [ ] T030 [US3] Executar T021–T023 e ampliar `tests/integration/test_learning_job_producers.py` para sucesso/falha de diagnóstico, preparação e sumário atravessando processos reais, incluindo transição durante a inscrição, resultado anterior à conexão e compatibilidade das mensagens Celery anteriores à ativação.

**Marco verificável** · Os quatro canais entregam resultados públicos, a preparação expira no limite exato e o sumário vigente resiste a conclusões antigas.

## Fase 6 — US4 · Retomar e encerrar (P2)

**Objetivo** · Garantir retomada coerente, isolamento, revogação e liberação completa dos recursos da conexão.

**Teste independente** · Concluir jobs durante cada janela da inscrição e durante desconexão, reconectar com outro ticket, revogar acesso antes do envio e medir consumidores/tarefas remanescentes após cada encerramento.

- [ ] T031 [P] [US4] Criar `tests/integration/test_job_subscription_races.py` com barreiras antes/depois do LISTEN, entre registro/leitura, durante leitura/envio e durante reconexão, parametrizando os quatro canais, avisos repetidos, revisão de sumário e eventos atrasados; exigir chegada ao estado atual sem regressão.
- [ ] T032 [P] [US4] Criar `tests/integration/test_job_subscription_lifecycle.py` para isolamento por usuário/canal/recurso, revogação após ticket e após snapshot, desconexão ociosa, falha de envio, fechamento normal, erro de consulta e perda do listener, exigindo zero recursos pertencentes ao socket e continuidade do job.
- [X] T033 [US4] Completar em `src/sidebrain_back/routers/v1/job_update_router.py` a recepção concorrente de mensagens/desconexão e emissão serial, cancelando/aguardando tarefas auxiliares em finally e removendo inscrição ao terminal/erro/fechamento; permitir que a task de aprendizagem continue e impedir segundo consumidor na inscrição repetida.
- [X] T034 [US4] Completar em `src/sidebrain_back/services/job_update_service.py` a revalidação de conta/posse/exclusão/revisão antes de cada atualização, convertendo perda de acesso em job.error genérico e supressão do payload; consolidar o ciclo de releitura para cobrir mudanças durante snapshot/envio e retomada com novo ticket.
- [ ] T035 [US4] Completar em `src/sidebrain_back/core/job_notifications.py` e `src/main.py` o tratamento de perda do listener, notificando consumidores afetados e restabelecendo escuta para novas inscrições, com encerramento de recursos no shutdown; registrar contexto e tempos sem credenciais ou conteúdo e executar T031–T032.
- [ ] T036 [US4] Criar e executar `tests/performance/test_job_update_latency.py` com worker separado e provedor determinístico, pelo menos 100 amostras por canal/tipo de entrega, mesmo relógio de referência e p95 de até 2 segundos para snapshots e terminais, registrando condições e resultado no `specs/SDB-109-websocket-job-updates/quickstart.md`.

**Marco verificável** · Recuperação, isolamento, liberação e latência atendem SC-002 a SC-006 nos cenários controlados.

## Fase 7 — US5 · Integrar o cliente (P2)

**Objetivo** · Permitir a integração dos quatro fluxos a partir das chamadas vigentes e de documentação reproduzível.

**Teste independente** · Executar as quatro chamadas e o protocolo completo seguindo o guia, comparar códigos/corpos anteriores e verificar conexão segura através do proxy em homologação.

- [ ] T037 [P] [US5] Ampliar `tests/contract/test_job_start_compatibility.py` com os quatro contratos de início, incluindo reutilização de request_id, diagnóstico 200/202 e Location, preparação 202 accepted/200 skipped, sumário 200 com texto imediato e identificação correta do canal/recurso a partir de cada resposta.
- [X] T038 [P] [US5] Publicar no `README.md` e atualizar `specs/SDB-109-websocket-job-updates/contracts/job-updates.md` o fluxo ticket/upgrade/subscribe, payloads, erros, retenção, reconexão, endereços e `VITE_WS_URL`, além de TLS, upgrade/timeout do proxy, PostgreSQL compartilhado com conexão de escuta por sessão e Redis de tickets compartilhado.
- [X] T039 [US5] Implementar a proteção dos logs de acesso do socket em `src/sidebrain_back/core/logging.py` e `src/main.py`, documentar a omissão da query também no proxy em `README.md` e testar em `tests/unit/test_ws_access_logging.py` que ticket/Bearer não aparecem nos logs; documentar a ordem migração/produtores/cliente e a janela de IDs legados de preparação.
- [ ] T040 [US5] Executar o guia local e em homologação de `specs/SDB-109-websocket-job-updates/quickstart.md`, cobrindo sucesso/falha e retomada nos quatro canais, duas réplicas, worker separado, wss pelo proxy e ausência de tickets nos logs; executar T037 e registrar evidências e eventuais bloqueios de ambiente no próprio guia antes de marcar a tarefa concluída.

**Marco verificável** · Contratos de início aprovados e integração reproduzível usando a documentação publicada.

## Fase 8 — Revisão e validação transversal

- [X] T041 Revisar as dependências e nomenclaturas nos arquivos novos de `src/sidebrain_back/services/job_update_service.py`, `src/sidebrain_back/repositories/job_update_repository.py` e `src/sidebrain_back/routers/v1/job_update_router.py`, junto aos produtores modificados, contra `docs/architecture.md` e `docs/code_conventions.md`; verificar providers, domínio em serviços, sessões curtas e mensagens públicas.
- [X] T042 Executar `uv run ruff check .` e `uv run pytest` conforme `pyproject.toml`, cobrindo regressões HTTP/SSE, migração e tarefas antigas, corrigir falhas introduzidas e registrar comandos/resultados no `specs/SDB-109-websocket-job-updates/quickstart.md`.
- [ ] T043 Auditar os 22 requisitos e oito critérios de sucesso de `specs/SDB-109-websocket-job-updates/spec.md` contra a implementação e evidências, atualizar os estados desta lista em `specs/SDB-109-websocket-job-updates/tasks.md` e conferir coerência final de `plan.md`, `data-model.md` e `contracts/job-updates.md` no mesmo diretório.

## Dependências e ordem de execução

A ordem principal é Preparação → Fundamentos → US1 → US2 → US3 → US4 → US5 → Revisão. US2 entrega o ciclo contínuo reutilizado pelos demais canais. US1 usa fixtures de estados persistidos para ser validada antes da integração dos produtores. US4 aprofunda garantias já presentes na inscrição e no envio das histórias anteriores.

| Grupo | Pré-requisitos e ordem interna |
|---|---|
| Preparação | T001 → T002. |
| Fundamentos | T003 e T004 após T002, depois T005 → T006 → T007 → T008. |
| US1 | Após T008, T009/T010/T011 podem ser escritos juntos, depois T012 → T013 → T014 → T015 → T016. |
| US2 | Após T016, T017/T018 podem ser escritos juntos, depois T019 → T020. |
| US3 | Após T020, T021/T022/T023 podem ser escritos juntos, depois T024 → T025 → T026 → T027 → T028 → T029 → T030. |
| US4 | Após T030, T031/T032 podem ser escritos juntos, depois T033 → T034 → T035 → T036. |
| US5 | Após T036, T037/T038 podem avançar juntos, depois T039 → T040. |
| Revisão | Após T040, T041 → T042 → T043. |

## Exemplos de execução paralela por história

| História | Trabalhos simultâneos após o pré-requisito da fase |
|---|---|
| US1 | T009 contrato HTTP, T010 disputa de ticket e T011 inscrição usam arquivos diferentes. |
| US2 | T017 verifica o contrato de mensagens enquanto T018 exercita o produtor e seus commits. |
| US3 | T021, T022 e T023 cobrem domínios diferentes com as fixtures prontas de T002. |
| US4 | T031 controla as janelas de corrida enquanto T032 verifica revogação, isolamento e recursos. |
| US5 | T037 verifica as chamadas de início enquanto T038 publica a documentação. |

Os modelos T003/T004 também podem ser escritos simultaneamente. Os arquivos compartilhados de serviço, router e migração seguem a ordem indicada para evitar edições conflitantes. A marcação paralela pressupõe que as fixtures e interfaces requeridas já estejam definidas.

## Estratégia de entrega

O primeiro incremento é a US1 com infraestrutura e fixtures dos quatro canais, permitindo demonstrar ticket, autorização e snapshot. A US2 acrescenta o primeiro fluxo completo com produtor real. Para o MVP utilizável de acompanhamento de trilhas, concluir US1 e US2 e validar também os cenários de revogação, reconexão e limpeza da US4 aplicáveis à trilha. A entrega completa da SDB-109 exige as cinco histórias e os gates finais.

Concluir cada fase pelos testes indicados e atualizar suas caixas após evidência de aprovação. A homologação depende de acesso ao ambiente e seu proxy. Se faltar esse acesso, registrar o bloqueio em T040 e manter a tarefa pendente.

## Cobertura dos requisitos

| Requisitos | Tarefas principais |
|---|---|
| FR-001, FR-002, FR-004, FR-005, FR-006, FR-021 | T009–T016 |
| FR-003, FR-016, FR-020 | T012–T016, T021, T029, T032–T035, T039 |
| FR-007, FR-008, FR-009, FR-017, FR-018 | T007, T011, T016, T020, T031–T035 |
| FR-010 | T017–T020 |
| FR-011, FR-012 | T021, T024, T030 |
| FR-013 | T003, T006, T022, T025, T026, T029, T030 |
| FR-014 | T004, T006, T023, T027–T030, T034 |
| FR-015 | T005, T008, T018–T020, T024–T030 |
| FR-019, FR-022 | T037–T040, T042 |
| SC-001, SC-002 | T017–T030, T031 |
| SC-003, SC-004, SC-005 | T009–T011, T022, T023, T031–T035 |
| SC-006 | T036 |
| SC-007, SC-008 | T037–T040, T042, T043 |
