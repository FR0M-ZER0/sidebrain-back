# Feature Specification: Geração assíncrona de Trilhas e preparação de Steps

**Feature Branch**: `SDB-75-async-track-generation`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "SDB-75 - Ajustar o fluxo de criação de Trilhas para geração assíncrona e expor a preparação do próximo Step"

## Clarifications

### Session 2026-09-21

- Q: O cliente deve poder enviar um `request_id` opcional no payload, com geração automática quando ausente? → A: Sim. `request_id` é opcional no payload; a API gera um quando ausente.
- Q: Qual rota HTTP deve disparar a preparação manual do próximo Step? → A: `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Solicitar uma Trilha sem bloquear a aplicação (Priority: P1)

Como usuário que deseja uma Trilha personalizada, quero enviar meu contexto de aprendizagem e receber uma confirmação imediata, para continuar usando a aplicação enquanto a Trilha é gerada em segundo plano.

**Why this priority**: A geração depende de um provedor externo e não deve manter a requisição aberta nem tornar a experiência do usuário dependente do tempo de resposta desse provedor.

**Independent Test**: Enviar um contexto válido, simular um provedor lento e verificar que a API responde imediatamente com uma identificação da solicitação, sem esperar a geração terminar.

**Acceptance Scenarios**:

1. **Given** um objetivo, tópico, nível de conhecimento e respostas de avaliação válidos, **When** o usuário solicita uma nova Trilha, **Then** o sistema valida o contexto, registra a solicitação pendente, inicia a geração em segundo plano e responde com `202 Accepted` e `request_id`.
2. **Given** uma solicitação aceita, **When** a geração em segundo plano é concluída, **Then** a Trilha é persistida com todas as etapas previstas, conteúdo detalhado apenas no primeiro Step e o resultado associado ao `request_id`.
3. **Given** uma solicitação aceita, **When** o provedor externo demora para responder, **Then** a resposta HTTP da solicitação não aguarda o provedor e não retorna erro por timeout da geração.

### User Story 2 - Repetir uma solicitação sem duplicar a Trilha (Priority: P1)

Como cliente da API, quero reutilizar um identificador de solicitação ao repetir uma chamada, para obter o mesmo resultado sem criar Trilhas duplicadas.

**Why this priority**: Clientes podem repetir chamadas após uma falha de rede ou receber a mesma mensagem mais de uma vez; a idempotência protege a integridade dos dados.

**Independent Test**: Enviar duas solicitações equivalentes com o mesmo `request_id`, inclusive enquanto a primeira ainda está pendente, e confirmar que ambas apontam para uma única solicitação e uma única Trilha quando a geração termina.

**Acceptance Scenarios**:

1. **Given** uma solicitação pendente ou concluída com determinado `request_id`, **When** o cliente envia novamente o mesmo contexto e identificador, **Then** o sistema não agenda uma nova geração nem cria uma segunda Trilha.
2. **Given** um `request_id` já associado a um contexto diferente, **When** o cliente tenta reutilizá-lo, **Then** o sistema rejeita a solicitação com erro de conflito em Problem Details e preserva o resultado original.

### User Story 3 - Preparar manualmente o próximo Step (Priority: P1)

Como usuário que avança em uma Trilha, quero solicitar a preparação do próximo Step elegível, para que seu conteúdo esteja disponível sem executar a regra de geração diretamente na camada HTTP.

**Why this priority**: O produto já possui a preparação automática por progresso; expor a mesma capacidade permite acionamento explícito e mantém uma única regra de negócio.

**Independent Test**: Solicitar a preparação para um Step pertencente ao usuário e verificar que a operação retorna imediatamente e agenda a preparação, enquanto Steps de outro usuário ou inexistentes retornam o mesmo `404` genérico.

**Acceptance Scenarios**:

1. **Given** um Step ativo pertencente ao usuário e um próximo Step elegível, **When** o cliente chama `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next`, **Then** o sistema valida a cadeia Trilha → Step, agenda a preparação em segundo plano e responde sem aguardar o provedor externo.
2. **Given** um Step já preparado ou com preparação equivalente em andamento, **When** o cliente solicita novamente a preparação, **Then** o sistema mantém comportamento idempotente e não cria conteúdo duplicado.
3. **Given** um Step inexistente, excluído ou pertencente a outro usuário, **When** o cliente solicita a preparação, **Then** o sistema responde com `404 Not Found` genérico, sem revelar se o recurso existe ou quem é seu proprietário.
4. **Given** não há próximo Step elegível, **When** o cliente solicita a preparação, **Then** o sistema não cria conteúdo e comunica o resultado conforme o contrato público da operação.

### Edge Cases

- Payload incompleto, inválido ou com valores fora dos limites do domínio deve ser rejeitado antes de qualquer solicitação em segundo plano e seguir Problem Details.
- Quando o `request_id` não for informado pelo cliente, o sistema deve gerar um identificador único; quando informado, deve usá-lo como chave de idempotência.
- Uma falha transitória do provedor durante a geração deve usar a política limitada de novas tentativas já existente, sem bloquear o endpoint nem criar registros parciais.
- Uma falha permanente, uma resposta inválida ou o esgotamento das tentativas deve produzir uma falha de geração persistida e observável, com `error_code`, sem retornar um `500` causado pela execução em segundo plano ao cliente que já recebeu `202`.
- Se a persistência falhar durante a geração, a Trilha não deve ficar parcialmente criada e a solicitação deve terminar em falha tratável.
- A preparação manual deve respeitar exclusão lógica e ownership em toda a cadeia Lesson → Step → Trilha.
- Solicitações concorrentes de preparação para o mesmo Step não devem duplicar Lessons, Quizzes ou Missions.
- O limiar de 80% e a paginação existentes não devem ser alterados por esta feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST aceitar uma solicitação de criação de Trilha contendo objetivo, tópico, nível de conhecimento e, quando disponíveis, respostas da avaliação de conhecimento.
- **FR-002**: O sistema MUST validar o payload antes de registrar ou iniciar a geração e MUST devolver erros de entrada em Problem Details, sem expor nomes físicos de persistência.
- **FR-003**: O sistema MUST aceitar um `request_id` opcional no payload, gerar um identificador quando ele não for fornecido e usar o valor informado pelo cliente como chave de idempotência.
- **FR-004**: O endpoint de criação MUST registrar a solicitação como pendente, iniciar a geração em segundo plano e responder imediatamente com `202 Accepted` e `request_id`.
- **FR-005**: O endpoint de criação MUST NOT aguardar o provedor externo nem executar a geração completa durante a requisição HTTP.
- **FR-006**: A geração em segundo plano MUST persistir a Trilha completa quando bem-sucedida, incluindo todas as etapas previstas, com conteúdo detalhado apenas no primeiro Step e as etapas posteriores representadas pela sua posição, nível e título.
- **FR-007**: A geração MUST preservar a idempotência por `request_id`: repetir o mesmo pedido enquanto pendente ou concluído MUST produzir o mesmo resultado lógico e não duplicar a Trilha.
- **FR-008**: O sistema MUST rejeitar a reutilização de um `request_id` com contexto diferente sem modificar a solicitação original.
- **FR-009**: Falhas de validação, geração, provedor ou persistência MUST ser representadas como falha de geração persistida e tratável, contendo ao menos `error_code`, sem propagar uma exceção de worker como erro `500` do endpoint já aceito.
- **FR-010**: O sistema MUST manter a política existente de retry limitado para falhas transitórias e MUST evitar retry indefinido para falhas permanentes ou respostas inválidas.
- **FR-011**: O sistema MUST disponibilizar `POST /api/v1/tracks/{track_id}/steps/{step_id}/prepare-next` para solicitar a preparação do próximo Step de uma Trilha, retornando antes da conclusão do provedor externo.
- **FR-012**: A operação de preparação MUST validar a cadeia Lesson → Step → Trilha, considerar apenas recursos ativos e exigir que a Trilha pertença ao usuário autenticado.
- **FR-013**: A operação de preparação MUST responder com `404 Not Found` genérico para recurso inexistente, excluído logicamente ou sem permissão, sem distinguir esses casos.
- **FR-014**: A operação de preparação MUST delegar a decisão e o enfileiramento ao serviço responsável, sem duplicar regra de negócio no endpoint.
- **FR-015**: A preparação manual MUST reutilizar a mesma task e as mesmas garantias de idempotência e concorrência do disparo automático existente.
- **FR-016**: As respostas públicas MUST usar nomes semânticos de domínio e MUST NOT expor identificadores físicos com prefixos `trk_`, `qui_` ou `ans_`.
- **FR-017**: A feature MUST preservar os endpoints, regras de Quiz, Feedback, Health e avaliação de conhecimento existentes, além do threshold de 80% e da paginação.
- **FR-018**: Erros públicos MUST seguir Problem Details conforme RFC 9457, incluindo status, título, detalhe e código ou lista de erros quando aplicável.

### Key Entities

- **Solicitação de geração**: Registro que identifica o pedido, seu contexto, estado pendente, concluído ou falho e o `request_id` usado para idempotência.
- **Trilha**: Percurso personalizado associado ao usuário, formado por Steps e pelo conteúdo gerado inicialmente.
- **Step**: Etapa ordenada da Trilha; o primeiro recebe conteúdo na geração inicial e os demais aguardam preparação posterior.
- **Conteúdo de Step**: Lessons, Quizzes e Mission associados a um Step quando sua preparação é concluída.
- **Falha de geração**: Resultado persistido de uma execução que não pôde concluir, com `error_code` e informação suficiente para acompanhamento sem expor detalhes sensíveis.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das solicitações válidas de criação respondem com `202 Accepted` e `request_id` sem aguardar a conclusão do provedor externo.
- **SC-002**: Em 100% dos testes de repetição com o mesmo `request_id`, existe no máximo uma Trilha persistida e nenhuma geração duplicada é iniciada.
- **SC-003**: 100% das gerações válidas concluídas persistem todas as etapas previstas, com conteúdo detalhado somente no primeiro Step.
- **SC-004**: 100% das falhas de validação ou execução são representadas por resultado tratável com `error_code`; nenhuma falha do worker aceita pelo endpoint aparece como `500` na resposta inicial.
- **SC-005**: Em 100% dos cenários de preparação manual sem permissão, inexistentes ou excluídos, a resposta observável é o mesmo `404` genérico e não revela ownership.
- **SC-006**: Em 100% dos cenários válidos de preparação manual, o endpoint delega o enfileiramento e permanece responsivo sem esperar o provedor externo.
- **SC-007**: Em testes concorrentes para o mesmo Step, no máximo um conjunto de conteúdo ativo é persistido.
- **SC-008**: 100% dos cenários de aceite das três jornadas prioritárias possuem testes automatizados passando antes da liberação.

## Assumptions

- A autenticação e a identificação do usuário atual já são fornecidas pelo fluxo existente da API.
- Quando o cliente não enviar `request_id`, a aplicação o gera; clientes que precisam repetir uma solicitação devem fornecer o mesmo identificador em cada tentativa.
- O armazenamento de estados de geração e falhas existente será reutilizado; esta feature não cria uma nova interface de acompanhamento além do contrato necessário para a solicitação e seus resultados.
- O mecanismo atual de execução assíncrona, retry limitado, idempotência e transação será preservado, sendo ajustado apenas para ser acionado pelo endpoint de criação e pela nova operação de preparação.
- O contrato da operação de preparação será um endpoint de disparo que retorna a aceitação da solicitação; consulta detalhada de progresso permanece dependente do mecanismo de acompanhamento já existente.
- O threshold de 80%, a lógica de IA, os prompts, a paginação e os domínios de Quiz, Feedback, Health e avaliação de conhecimento permanecem inalterados.
- A geração inicial continua criando conteúdo apenas para o primeiro Step; a preparação de Steps posteriores continua obedecendo às regras vigentes do domínio.
- Frontend, alteração de autenticação e migrações de dados fora do estado de geração não fazem parte desta feature.