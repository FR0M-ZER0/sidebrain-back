# Feature Specification: Filas RabbitMQ para Notificações

**Feature Branch**: `SDB-101-rabbitmq-notification-queues`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "SDB-101 — adicionar filas RabbitMQ para gerenciar notificações"

## Clarifications

### Session 2026-11-11

- Q: Qual política de retry deve ser usada para falhas transitórias no worker de notificações? → A: Backoff exponencial, até 5 tentativas
- Q: Após uma mensagem falhar nas 5 tentativas, onde ela deve ser isolada para investigação? → A: Dead-letter queue durável e separada
- Q: Quais campos mínimos devem existir em todo payload de notificação válido? → A: event_id, type, data
- Q: A fila principal e a dead-letter queue devem preservar mensagens após reinicialização do broker? → A: Filas duráveis e mensagens persistentes
- Q: Quais informações mínimas devem aparecer nos logs de publicação, retry e falha definitiva? → A: event_id, tipo, tentativa, erro, timestamp

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enfileirar notificações sem interromper a operação (Priority: P1)

Como uma integração da plataforma, quero publicar uma notificação para processamento assíncrono, para que a operação que originou o evento não precise esperar por sua entrega.

**Why this priority**: O fluxo de notificações precisa ser desacoplado das operações existentes sem alterar o processamento assíncrono já utilizado pela aplicação.

**Independent Test**: Publicar um payload válido e verificar que ele é aceito na fila dedicada sem executar o envio de uma notificação no mesmo fluxo.

**Acceptance Scenarios**:

1. **Given** um payload JSON válido, **When** ele é publicado pelo ponto de integração, **Then** ele é encaminhado à fila dedicada de notificações com seu conteúdo preservado.
2. **Given** uma indisponibilidade temporária do consumidor, **When** um payload é publicado, **Then** a mensagem permanece disponível para processamento posterior e não é descartada silenciosamente.

### User Story 2 - Processar notificações com recuperação de falhas (Priority: P1)

Como responsável pela operação, quero que um worker consuma a fila dedicada e tente novamente falhas transitórias, para reduzir a perda de notificações e facilitar o diagnóstico.

**Why this priority**: O consumo confiável é o valor principal da infraestrutura solicitada e deve isolar falhas individuais das demais mensagens.

**Independent Test**: Consumir uma mensagem com um handler controlado, simular uma falha transitória e verificar novas tentativas, registro do erro e confirmação somente após sucesso.

**Acceptance Scenarios**:

1. **Given** uma mensagem disponível, **When** o worker a processa com sucesso, **Then** o processamento é confirmado e a mensagem deixa de estar disponível para consumo.
2. **Given** uma falha transitória no processamento, **When** o worker termina a tentativa, **Then** a mensagem volta a ser elegível conforme o limite e o intervalo configurados.
3. **Given** uma mensagem que excedeu o limite de tentativas, **When** uma nova falha ocorre, **Then** ela é encaminhada para uma dead-letter queue durável e separada, e as demais mensagens continuam sendo processadas.

### User Story 3 - Operar a infraestrutura de notificações (Priority: P2)

Como responsável pelo desenvolvimento e operação, quero iniciar o broker e o worker com configurações documentadas, para reproduzir o fluxo localmente sem expor credenciais.

**Why this priority**: Configuração reproduzível e observável reduz o tempo necessário para validar integrações futuras e investigar falhas.

**Independent Test**: Iniciar o ambiente local com variáveis fornecidas externamente, verificar a saúde do broker e executar uma publicação e um consumo de teste.

**Acceptance Scenarios**:

1. **Given** as variáveis de ambiente documentadas, **When** o ambiente local é iniciado, **Then** o broker fica disponível e informa sua condição de saúde.
2. **Given** uma mensagem inválida, **When** o worker a recebe, **Then** ela é rejeitada e registrada sem interromper o consumo de mensagens válidas.
3. **Given** as tasks Celery existentes, **When** o novo worker é executado, **Then** elas continuam usando o Redis e seu comportamento não é alterado.

### Edge Cases

- O broker não deve iniciar com credenciais ausentes, inválidas ou embutidas em arquivos versionados.
- Falhas de conexão do worker devem produzir logs estruturados com `event_id`, tipo, tentativa, erro e timestamp, sem registrar o payload completo ou segredos, e permitir nova conexão conforme a política definida.
- A publicação deve rejeitar payloads não serializáveis ou sem os campos `event_id`, `type` e `data`, sem enviar mensagens incompletas.
- O processamento de uma mensagem com falha não deve impedir o processamento das demais mensagens disponíveis.
- A configuração da fila deve manter mensagens e roteamento durante reinicializações; a fila principal e a dead-letter queue são duráveis e as mensagens são persistentes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar um broker RabbitMQ no ambiente local com verificação de saúde.
- **FR-002**: O sistema MUST obter host, porta, usuário, senha e demais parâmetros do broker a partir de configuração externa, sem versionar segredos.
- **FR-003**: O sistema MUST manter uma configuração de processamento de notificações separada da configuração Celery existente, conectada ao RabbitMQ.
- **FR-004**: O sistema MUST declarar uma fila dedicada de notificações com exchange, routing key, fila durável e mensagens persistentes, além de uma dead-letter queue durável.
- **FR-005**: O sistema MUST disponibilizar um publicador que aceite payloads JSON serializáveis contendo os campos `event_id`, `type` e `data`, e os encaminhe para a fila dedicada.
- **FR-006**: O sistema MUST disponibilizar um consumidor que delegue cada mensagem a um handler de notificação e confirme a mensagem somente após processamento bem-sucedido.
- **FR-007**: O sistema MUST aplicar uma política configurável de retry com backoff exponencial para falhas transitórias, limitada a 5 tentativas por mensagem e com comportamento observável.
- **FR-008**: O sistema MUST registrar falhas de publicação, conexão, validação e processamento em logs estruturados contendo `event_id`, tipo, tentativa, erro e timestamp, sem registrar o payload completo ou segredos.
- **FR-009**: O sistema MUST encaminhar mensagens inválidas ou que excederam as tentativas para uma dead-letter queue durável e separada, para que não interrompam o consumo das demais mensagens.
- **FR-010**: O sistema MUST preservar o broker Redis, o agendamento, a execução e o backend de resultados das tasks Celery existentes.
- **FR-011**: O sistema MUST documentar as variáveis de ambiente, o comando de inicialização do broker e o comando de execução do worker de notificações.
- **FR-012**: O sistema MUST incluir testes para configuração e roteamento da fila, publicação e consumo, sem exigir um RabbitMQ externo nos testes unitários.

### Key Entities

- **Payload de Notificação**: Objeto JSON serializável com os campos `event_id`, `type` e `data`, representando uma notificação a processar sem credenciais ou outros segredos.
- **Fila de Notificações**: Canal durável e dedicado que mantém mensagens persistentes, regras de roteamento e parâmetros de durabilidade do fluxo.
- **Dead-letter queue**: Fila durável e separada que armazena mensagens persistentes inválidas ou que excederam as tentativas para investigação.
- **Worker de Notificações**: Consumidor responsável por executar o handler, confirmar sucessos, repetir falhas transitórias e isolar falhas definitivas.
- **Configuração do Broker**: Parâmetros externos necessários para conexão, autenticação e operação do RabbitMQ.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos testes de publicação com payload válido, a mensagem chega à fila dedicada com conteúdo e roteamento preservados.
- **SC-002**: Em 100% dos testes de falha transitória, o worker realiza novas tentativas até o limite configurado e registra o resultado de cada falha sem perder a mensagem.
- **SC-003**: Em 100% dos testes de processamento bem-sucedido, a mensagem é confirmada apenas após o handler concluir e não volta a ser entregue pelo fluxo normal.
- **SC-004**: Em um teste com pelo menos 1.000 mensagens válidas, nenhuma mensagem é descartada silenciosamente; cada uma termina como processada ou isolada como falha.
- **SC-005**: Uma pessoa desenvolvedora consegue iniciar o broker e o worker a partir da documentação e publicar uma mensagem de teste em até 10 minutos.
- **SC-006**: A suíte unitária do fluxo de notificações executa sem depender de um broker externo, e as tasks Celery existentes continuam passando seus testes sem alteração de configuração.

## Assumptions

- A integração de negócio que produzirá eventos e os canais de envio (e-mail, push ou outros) serão definidos em tarefas posteriores.
- O handler desta feature estabelece o ponto de consumo e o tratamento técnico da mensagem, mas não implementa entrega por canal externo.
- Os parâmetros de retry, incluindo o backoff exponencial e o limite padrão de 5 tentativas, durabilidade e conexão serão configuráveis por ambiente e terão valores padrão adequados ao desenvolvimento local.
- O Redis continuará sendo o broker e backend das tasks Celery já existentes.
- Os testes de integração que exigirem RabbitMQ poderão usar um ambiente local configurado, enquanto os testes unitários usarão substitutos controlados.

## Out of Scope

- Definir quais eventos de negócio geram notificações.
- Implementar envio por e-mail, push ou qualquer canal externo.
- Criar API, persistência de domínio ou interface de usuário para notificações.
- Migrar tasks Celery existentes do Redis para RabbitMQ.
- Definir autorização, preferências, templates ou regras de conteúdo das notificações.

