---

description: "Task list for feature implementation"
---

# Tasks: Filas RabbitMQ para Notificações

**Input**: Design documents from `/specs/SDB-101-rabbitmq-notification-queues/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/)

**Tests**: Incluídos porque a especificação exige testes de configuração,
roteamento, publicação e consumo, sem RabbitMQ externo nos testes unitários.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar dependência e estrutura inicial sem alterar o transporte
Celery/Redis existente.

- [X] T001 Adicionar `aio-pika` às dependências de produção em `pyproject.toml` e atualizar `uv.lock` com `uv lock`, sem remover ou alterar `celery` e `redis`
- [X] T002 [P] Criar os pacotes `src/sidebrain_back/notifications/__init__.py`, `tests/unit/notifications/__init__.py` e `tests/integration/notifications/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implementar a configuração e a topologia compartilhadas que
bloqueiam publisher e consumer.

- [X] T003 Adicionar ao `src/sidebrain_back/core/constants.py` configurações externas tipadas para host, porta, usuário, senha, vhost, exchange, routing key, fila principal, DLX, DLQ, máximo padrão de 5 tentativas, atraso inicial e fator de backoff; valores inválidos devem falhar e segredos não podem ser registrados
- [X] T004 [P] Adicionar ao `.env.example` somente nomes e defaults locais não sensíveis para as variáveis RabbitMQ, mantendo credenciais reais fora do repositório
- [X] T005 [P] Adicionar o serviço `rabbitmq` ao `docker-compose.yml` com volume persistente, credenciais vindas do ambiente, portas configuráveis e healthcheck de `rabbitmq-diagnostics`
- [X] T006 Criar `src/sidebrain_back/notifications/schemas.py` com `NotificationPayload`, exigindo os campos `event_id`, `type` e `data`, rejeitando strings vazias e JSON não serializável sem incluir o payload em logs
- [X] T007 Criar `src/sidebrain_back/notifications/broker.py` para conexão `aio-pika`, declaração idempotente da exchange, fila principal, binding, DLX e DLQ; exchange e filas devem ser duráveis e a topologia deve usar nomes configuráveis
- [X] T008 [P] Criar `tests/unit/notifications/test_config.py` e `tests/unit/notifications/test_broker.py` cobrindo validação das configurações, durabilidade, binding, DLQ e isolamento da configuração Celery/Redis

**Checkpoint**: A configuração e a topologia podem ser testadas sem broker
externo; publisher e consumer podem iniciar sobre os mesmos nomes e argumentos.

---

## Phase 3: User Story 1 - Enfileirar notificações sem interromper a operação (Priority: P1) ðŸŽ¯ MVP

**Goal**: Publicar payloads válidos na fila dedicada sem executar o handler no
fluxo produtor, preservando conteúdo e roteamento mesmo quando o consumer está
indisponível.

**Independent Test**: Publicar um `NotificationPayload` válido com publisher
confirmado e verificar que a mensagem chega à fila com conteúdo preservado, sem
invocar o handler.

### Tests for User Story 1

- [X] T009 [P] [US1] Criar `tests/unit/notifications/test_publisher.py` com broker mockado para validar serialização JSON UTF-8, `DeliveryMode.PERSISTENT`, `mandatory=True`, publisher confirm e rejeição de payload inválido ou não serializável sem publicação
- [X] T010 [P] [US1] Criar `tests/contract/notifications/test_publisher_contract.py` verificando que o publisher usa a exchange e routing key do contrato e registra publicação com `event_id`, tipo, tentativa, erro e timestamp sem payload completo

### Implementation for User Story 1

- [X] T011 [US1] Criar `src/sidebrain_back/notifications/publisher.py` com API assíncrona de publicação de `NotificationPayload`, validação antes do envio, mensagem persistente e espera de publisher confirm
- [X] T012 [US1] Implementar em `src/sidebrain_back/notifications/publisher.py` tratamento explícito de erro de conexão, timeout, mensagem não roteável e falha de confirmação, emitindo logs estruturados sem credenciais ou payload completo
- [X] T013 [US1] Integrar o publisher com a topologia de `src/sidebrain_back/notifications/broker.py` e expor apenas a função de publicação necessária ao produtor, sem importar ou modificar `sidebrain_back.core.celery_app`

**Checkpoint**: US1 permite publicar sem consumer e deixa mensagens persistentes
disponíveis para consumo posterior.

---

## Phase 4: User Story 2 - Processar notificações com recuperação de falhas (Priority: P1)

**Goal**: Consumir mensagens, delegar ao handler, confirmar apenas sucessos,
repetir falhas transitórias com backoff exponencial até 5 tentativas e enviar
falhas definitivas ou inválidas para a DLQ.

**Independent Test**: Consumir uma mensagem com handler controlado, verificar
`ack` após sucesso, retries observáveis após falha transitória e DLQ após a
quinta falha, sem bloquear mensagens independentes.

### Tests for User Story 2

- [X] T014 [P] [US2] Criar `tests/unit/notifications/test_consumer.py` com mensagens e handler mockados para validar ack somente após sucesso, rejeição de payload inválido, isolamento de falha e continuidade do consumo
- [X] T015 [P] [US2] Criar `tests/unit/notifications/test_retry.py` verificando backoff exponencial configurável, limite padrão de cinco tentativas, logs por tentativa e rejeição final com `requeue=False`
- [X] T016 [US2] Criar `tests/integration/notifications/test_notification_flow.py` usando broker local opcional para verificar publicação, consumo, persistência, confirmação e encaminhamento à DLQ

### Implementation for User Story 2

- [X] T017 [P] [US2] Criar `src/sidebrain_back/notifications/handler.py` com protocolo assíncrono `handle(payload)` e erro explícito para falhas transitórias ou definitivas, sem implementar canais externos de entrega
- [X] T018 [US2] Criar `src/sidebrain_back/notifications/consumer.py` para consumir a fila, validar `NotificationPayload`, delegar cada mensagem ao handler e enviar `ack` somente após conclusão bem-sucedida
- [X] T019 [US2] Implementar em `src/sidebrain_back/notifications/consumer.py` retry com atraso exponencial configurável e cabeçalho de tentativa, limitado a 5 tentativas por mensagem; payload inválido deve ir diretamente à DLQ
- [X] T020 [US2] Implementar em `src/sidebrain_back/notifications/consumer.py` rejeição final sem requeue, tratamento de reconexão e logs estruturados com `event_id`, tipo, tentativa, erro e timestamp, sem payload completo ou segredos
- [X] T021 [US2] Criar `src/sidebrain_back/notifications/worker.py` com entrypoint do worker RabbitMQ separado do worker Celery, encerramento limpo e processamento concorrente sem bloquear mensagens independentes

**Checkpoint**: US2 processa sucessos, recupera falhas transitórias e isola
falhas definitivas na DLQ sem alterar o fluxo Celery.

---

## Phase 5: User Story 3 - Operar a infraestrutura de notificações (Priority: P2)

**Goal**: Permitir iniciar broker e worker com variáveis externas, healthcheck e
comandos documentados, preservando o funcionamento das tasks Celery em Redis.

**Independent Test**: Iniciar RabbitMQ pelo Compose, verificar healthcheck,
executar o worker, publicar uma mensagem de teste e confirmar que o worker
Celery continua usando Redis.

### Tests for User Story 3

- [X] T022 [P] [US3] Criar `tests/integration/notifications/test_operational_flow.py` para validar healthcheck, reconexão após indisponibilidade temporária e publicação/consumo com configurações fornecidas pelo ambiente
- [X] T023 [P] [US3] Criar `tests/unit/notifications/test_celery_isolation.py` verificando que `sidebrain_back.core.celery_app` mantém broker Redis, backend Redis, imports, agendamento e nomes de tasks existentes

### Implementation for User Story 3

- [X] T024 [US3] Documentar no `README.md` as variáveis RabbitMQ, o comando `docker compose up -d rabbitmq`, o healthcheck, o comando de execução do worker de notificações e um exemplo de publicação sem credenciais
- [X] T025 [US3] Adicionar ao `src/sidebrain_back/notifications/cli.py` comando executável para iniciar o worker usando configuração externa e retornar erro explícito quando credenciais ou parâmetros obrigatórios estiverem ausentes
- [X] T026 [US3] Integrar o comando do worker ao entrypoint documentado no `pyproject.toml` ou ao comando `uv run`, sem registrar segredos e sem alterar `src/sidebrain_back/core/celery_app.py`

**Checkpoint**: Uma pessoa desenvolvedora consegue iniciar broker e worker em
até 10 minutos e validar o fluxo local sem modificar Celery/Redis.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidar documentação, qualidade, segurança e validação final.

- [X] T027 [P] Atualizar `docs/architecture.md` e `docs/code_conventions.md` para documentar o pacote de notificações, a separação de Celery/Redis e a convenção do worker não-Celery
- [X] T028 [P] Revisar `src/sidebrain_back/notifications/` para garantir type hints, logs estruturados, ausência de payload/segredos em mensagens e compatibilidade com Ruff
- [X] T029 Executar `uv run ruff check .` no repositório e corrigir somente problemas introduzidos nos arquivos da feature
- [X] T030 Executar `uv run pytest` para `tests/unit/notifications/`, `tests/integration/notifications/` e a suíte existente, confirmando os critérios SC-001 a SC-006, incluindo teste com pelo menos 1.000 mensagens válidas no ambiente de integração
- [X] T031 Executar os cenários de [quickstart.md](./quickstart.md) e registrar no resultado da implementação os comandos e resultados de broker, publisher, worker, DLQ e regressão Celery

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências; T002 pode executar em paralelo com T001.
- **Foundational (Phase 2)**: Depende de T001 e T002; T004, T005 e T008 podem
  executar em paralelo após a estrutura inicial, enquanto T006 e T007 definem
  os contratos usados pelas histórias.
- **User Stories (Phases 3-5)**: Dependem da conclusão da Phase 2. US1 e US2
  compartilham a topologia, mas podem ser desenvolvidas em paralelo depois de
  T007; US3 depende dos entrypoints de US1/US2 para sua validação operacional.
- **Polish (Phase 6)**: Depende das três histórias e de seus testes.

### User Story Dependencies

- **US1 (P1)**: Depende da Phase 2; é o MVP e não depende de outra história.
- **US2 (P1)**: Depende da Phase 2 e do contrato de payload; pode ser testada com
  handler mockado, sem depender do publisher real.
- **US3 (P2)**: Depende de T011, T018 e T021 para validar os comandos, mas mantém
  a regressão Celery independente.

### Dependency Graph

```text
T001 -> T003 -> T006 -> T007 -> T011 -> T013
  â””-> T002 -> T004/T005/T008
T007 -> T014/T015/T017 -> T018 -> T019/T020 -> T021
T011/T018/T021 -> T022/T023/T024/T025/T026
US1 + US2 + US3 -> T027/T028/T029/T030/T031
```

### Parallel Opportunities

- Setup: T001 e T002.
- Foundation: T004, T005 e T008 após T003; T006 e T007 podem ser separados
  somente se o contrato de schema for acordado antes da topologia.
- US1: T009 e T010; após os testes, T011 e T012 podem ser separados por arquivo.
- US2: T014, T015 e T017; T018 e T019/T020 permanecem sequenciais no consumer.
- US3: T022, T023 e T024; não executar T026 antes de T021.
- Polish: T027 e T028; validações T029-T031 devem ocorrer após as alterações.

## Parallel Example: User Story 1

```text
Task T009: testes unitários do publisher em tests/unit/notifications/test_publisher.py
Task T010: teste de contrato em tests/contract/notifications/test_publisher_contract.py
Task T011: implementação do publisher em src/sidebrain_back/notifications/publisher.py
```

T011 só deve ser finalizada após os testes T009/T010 demonstrarem as falhas
esperadas; T012 e T013 dependem da implementação do publisher.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Setup e Foundational.
2. Implementar US1 com schema, topologia, publisher confirmado e testes mockados.
3. Executar a validação independente de publicação e confirmar persistência sem
   consumer.
4. Parar para revisão antes de iniciar o worker.

### Incremental Delivery

1. Adicionar US2 com consumer, handler, retry, ack e DLQ; validar falhas isoladas.
2. Adicionar US3 com Compose, CLI, documentação, healthcheck e regressão Celery.
3. Executar Polish, lint, suíte completa e teste de carga de 1.000 mensagens.

### Format Validation

Todos os 31 itens de execução usam `- [ ]`, ID sequencial `T###`, marcador
`[P]` somente quando aplicável, rótulo `[USn]` em todas as tarefas de história
e caminho de arquivo explícito na descrição.


