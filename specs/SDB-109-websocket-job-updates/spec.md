# Feature Specification — Acompanhamento de jobs assíncronos por WebSocket

**Feature Branch** `feat/sdb-109-Criar-endpoints-WebSocket-para-atualizacao-de-jobs-assíncronos`

**Created** 2026-11-11

**Status** Draft

**Input** SDB-109 — Criar endpoints WebSocket para atualização de jobs assíncronos.

A pessoa que aguarda a geração de uma trilha, perguntas de diagnóstico, preparação da próxima etapa ou sumário do quiz precisa conhecer o andamento e o resultado da operação pela conexão de acompanhamento. A entrega abrange a emissão de credenciais temporárias, inscrição autorizada, comunicação dos quatro fluxos e documentação para integração do cliente. A descrição e os critérios de aceite da tarefa orientam esta especificação. [SDB-109](https://fromzero-api.atlassian.net/browse/SDB-109)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autorizar o acompanhamento de uma operação (Priority P1)

Como usuário autenticado, quero obter uma credencial temporária para acompanhar uma operação minha, para receber suas atualizações com acesso restrito ao recurso solicitado.

**Why this priority** A autorização por usuário e recurso é necessária em todos os fluxos de acompanhamento.

**Independent Test** Solicitar tickets para recursos próprios, alheios e indisponíveis, abrir conexões com tickets válidos e inválidos e tentar inscrever recursos diferentes do autorizado.

**Acceptance Scenarios**

1. **Given** um usuário autenticado com permissão para acompanhar um recurso, **When** solicita um ticket informando canal e identificador válidos, **Then** recebe um ticket temporário vinculado ao próprio usuário e àquela combinação de canal e recurso.
2. **Given** um ticket válido e ainda disponível, **When** o cliente o apresenta na abertura da conexão e envia a inscrição correspondente, **Then** o sistema consome o ticket, autoriza o acompanhamento e envia o estado atual do recurso.
3. **Given** um ticket ausente, inválido, expirado ou consumido, **When** o cliente tenta abrir a conexão, **Then** o sistema recusa o acesso aos dados de acompanhamento.
4. **Given** um recurso alheio, inexistente ou removido logicamente, **When** o usuário solicita um ticket, **Then** recebe a mesma resposta genérica de recurso indisponível.
5. **Given** uma conexão autorizada para determinado canal e recurso, **When** o cliente envia uma inscrição divergente, **Then** recebe um erro correlacionado ao escopo autorizado e a conexão é encerrada.
6. **Given** duas tentativas simultâneas de abertura com o mesmo ticket, **When** ambas são processadas, **Then** exatamente uma pode obter autorização.
7. **Given** uma solicitação de ticket com autenticação inválida, canal desconhecido ou identificador malformado, **When** o sistema valida o pedido, **Then** devolve o erro correspondente no formato padronizado de detalhes de problema do produto.

---

### User Story 2 - Receber o resultado da geração de uma trilha (Priority P1)

Como usuário que solicitou uma trilha, quero acompanhar a solicitação pelo seu identificador e receber a confirmação de sucesso ou falha, para acessar o conteúdo gerado ou compreender que a geração falhou.

**Why this priority** A geração de trilhas é uma jornada central que já possui identificação da solicitação e estados públicos de acompanhamento.

**Independent Test** Iniciar uma geração, inscrever seu identificador e conduzir execuções separadas até sucesso e falha, verificando o estado inicial e os resultados recebidos.

**Acceptance Scenarios**

1. **Given** uma geração pendente, **When** o cliente se inscreve em `track_generation` com o `request_id` autorizado, **Then** recebe uma atualização inicial com estado `pending` e passa a acompanhar aquela solicitação.
2. **Given** uma inscrição ativa, **When** a trilha fica disponível, **Then** o cliente recebe uma atualização com o mesmo `request_id`, estado `succeeded`, `track_id` do resultado e `error_code` vazio.
3. **Given** uma inscrição ativa, **When** a geração termina em falha, **Then** o cliente recebe uma atualização com o mesmo `request_id`, estado `failed`, `track_id` vazio e `error_code` público.
4. **Given** uma geração que já terminou antes da inscrição, **When** o cliente se inscreve com um ticket válido, **Then** o primeiro estado recebido contém o resultado terminal atual.

---

### User Story 3 - Acompanhar diagnóstico, preparação e sumário (Priority P1)

Como usuário que aguarda uma operação de aprendizagem, quero receber as perguntas de diagnóstico, a confirmação de preparação da próxima etapa e o sumário do quiz nos seus respectivos canais, para continuar minha jornada quando o resultado estiver disponível.

**Why this priority** Os três fluxos completam o contrato de acompanhamento necessário ao cliente da aplicação.

**Independent Test** Executar sucesso e falha de cada fluxo com recursos conhecidos, comparar os dados recebidos aos resultados públicos da operação e verificar a correlação entre canal e identificador.

**Acceptance Scenarios**

1. **Given** um diagnóstico autorizado em preparação, **When** o cliente se inscreve em `assessment` com o `assessment_id`, **Then** recebe o estado atual e, quando a geração termina com sucesso, recebe `completed` com as perguntas públicas e respectivas alternativas.
2. **Given** um diagnóstico cuja geração falhou, **When** o estado é enviado ao inscrito, **Then** a atualização contém o mesmo `assessment_id`, estado `failed`, perguntas vazias e `error_code` público.
3. **Given** um diagnóstico dispensado pelo fluxo existente, **When** o usuário acompanha seu resultado, **Then** recebe `completed` com perguntas vazias.
4. **Given** uma preparação de próxima etapa aceita com `task_id`, **When** o cliente acompanha esse identificador em `step_preparation`, **Then** recebe o estado atual e o resultado terminal `completed` ou `failed` da tarefa correspondente.
5. **Given** uma geração de sumário para uma etapa acessível, **When** o cliente acompanha `step_summary` com a chave `{track_id}:{step_id}`, **Then** recebe o estado atual e uma atualização terminal com `step_id`, estado `completed` e `summary`, ou estado `failed` e `error` público.
6. **Given** um resultado desses três fluxos disponível antes da conexão, **When** o cliente realiza a inscrição autorizada, **Then** o primeiro estado recebido já permite reconhecer sua conclusão ou falha.
7. **Given** um diagnóstico cujas perguntas possuem gabarito privado e uma operação com detalhes internos de falha, **When** as atualizações são enviadas, **Then** o cliente recebe somente perguntas, alternativas, códigos e mensagens públicos previstos para seu recurso.

---

### User Story 4 - Recuperar o estado e encerrar o acompanhamento (Priority P2)

Como usuário que pode perder a conexão ou sair de uma tela, quero retomar o acompanhamento pelo estado atual e encerrar a conexão ao terminar, para reconhecer o resultado da operação e liberar os recursos de acompanhamento.

**Why this priority** Quedas de conexão e transições de tela fazem parte do uso normal da aplicação e precisam ter comportamento previsível.

**Independent Test** Concluir operações durante a inscrição e durante uma desconexão, reconectar com novo ticket e verificar isolamento e liberação de recursos após fechamentos normais e inesperados.

**Acceptance Scenarios**

1. **Given** uma operação que avança enquanto a inscrição está sendo estabelecida, **When** o acompanhamento fica ativo, **Then** o cliente recebe uma sequência coerente que alcança o estado atual, incluindo eventual resultado terminal.
2. **Given** uma conexão interrompida enquanto a operação continua, **When** o usuário solicita um novo ticket e se inscreve novamente, **Then** recebe o estado atual e acompanha as atualizações posteriores até o resultado terminal.
3. **Given** uma conexão ativa, **When** o cliente a fecha por conclusão, falha, tempo limite, cancelamento do acompanhamento ou saída da tela, **Then** o sistema remove a inscrição e libera os consumidores e recursos associados à conexão.
4. **Given** usuários acompanhando recursos diferentes, inclusive no mesmo canal, **When** qualquer operação muda de estado, **Then** cada conexão recebe exclusivamente os eventos do usuário, canal e recurso autorizados.
5. **Given** uma indisponibilidade que impede obter o estado atual ou continuar o acompanhamento, **When** o sistema identifica a falha, **Then** informa um erro público correlacionado ao escopo autorizado, encerra a conexão e libera seus recursos.

---

### User Story 5 - Integrar o cliente aos quatro fluxos (Priority P2)

Como responsável pela integração do cliente, quero consultar o contrato de acompanhamento e os requisitos de publicação, para conectar as telas aos resultados das operações de aprendizagem.

**Why this priority** A documentação e a compatibilidade das operações de início permitem que o cliente adote o acompanhamento com comportamento verificável.

**Independent Test** Seguir a documentação para iniciar e acompanhar cada operação em um ambiente de integração, comparando suas chamadas de início aos contratos públicos vigentes.

**Acceptance Scenarios**

1. **Given** os contratos públicos vigentes das quatro operações de início, **When** o cliente inicia cada operação com os pedidos já aceitos, **Then** recebe os identificadores, códigos de resposta e resultados previstos nesses contratos e consegue usar os recursos correspondentes no acompanhamento.
2. **Given** a documentação de integração e um ambiente com as configurações descritas, **When** o integrador executa os quatro fluxos, **Then** consegue obter tickets, conectar, inscrever, reconhecer os estados terminais de sucesso e falha e retomar o acompanhamento com novo ticket.

### Edge Cases

- Credenciais de sessão ausentes ou inválidas na emissão de ticket resultam em recusa de autenticação.
- Canal desconhecido, identificador vazio e chave composta de sumário malformada resultam em erro de validação.
- Uma etapa indicada em `step_summary` deve pertencer à trilha da chave e ao usuário autorizado.
- Um identificador de tarefa de preparação precisa estar associado a uma operação acompanhável daquele usuário. Uma tarefa desconhecida recebe a resposta genérica de recurso indisponível.
- Um recurso removido ou uma permissão perdida entre a emissão do ticket e a inscrição deve resultar em recusa do acompanhamento.
- A expiração do ticket é avaliada no consumo para abrir a conexão. Uma conexão já autorizada pode acompanhar a operação até seu encerramento.
- Uma atualização emitida entre a leitura do estado inicial e a ativação do acompanhamento deve chegar ao cliente ou estar refletida no estado entregue. Um estado terminal deve prevalecer sobre atualizações anteriores recebidas com atraso.
- Uma nova tentativa transitória de processamento mantém o acompanhamento em andamento. O estado `failed` representa o encerramento efetivo daquela execução.
- Mensagem de inscrição malformada ou tipo de mensagem desconhecido resulta em erro público no escopo autorizado e encerramento da conexão.
- Repetir a mesma inscrição na mesma conexão deve resultar em um único acompanhamento lógico do recurso.
- Desconexão durante o envio ou falha no produtor de eventos deve acionar a liberação dos recursos da conexão afetada.
- Resultados emitidos por processamentos em execução separada precisam alcançar as conexões autorizadas da aplicação.
- O sumário pode estar pronto na própria resposta da chamada de geração. A inscrição posterior deve reconhecer esse resultado concluído.
- Uma preparação dispensada pelo fluxo de início, cuja resposta possui `status` igual a `skipped` e carece de `task_id`, é concluída pelo próprio retorno dessa operação. O canal de preparação acompanha as tarefas efetivamente aceitas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** O sistema MUST disponibilizar `POST /api/v1/auth/ws-ticket` com autenticação Bearer vigente, receber `channel` e `resource_id` e devolver a credencial temporária no campo `ticket` ao usuário autorizado a acompanhar o recurso.
- **FR-002** Cada ticket MUST estar vinculado ao usuário autenticado e a uma única combinação de canal e recurso, com validade de 60 segundos a partir da emissão e consumo de uso único na autorização da conexão.
- **FR-003** O sistema MUST verificar a permissão de acompanhamento na emissão do ticket e na inscrição, respeitando o vínculo do recurso ao usuário e a disponibilidade dos recursos relacionados. Recursos alheios, inexistentes e removidos MUST produzir a mesma resposta genérica de indisponibilidade.
- **FR-004** O sistema MUST disponibilizar a abertura de WebSocket em `GET /api/v1/ws?ticket={ticket}`, autorizar a conexão pelo ticket temporário e recusar tickets ausentes, inválidos, expirados ou consumidos. O uso simultâneo do mesmo ticket MUST autorizar no máximo uma conexão.
- **FR-005** A credencial de sessão de longa duração MUST ser utilizada somente na autenticação da emissão do ticket. A URL de acompanhamento MUST transportar exclusivamente a credencial temporária exigida pelo contrato de conexão.
- **FR-006** Após abrir a conexão, o cliente MUST poder enviar uma inscrição com `type` igual a `subscribe`, `channel` e `resource_id`. O sistema MUST aceitar o par autorizado pelo ticket e rejeitar inscrições divergentes ou mensagens inválidas com erro no escopo autorizado e encerramento da conexão.
- **FR-007** O sistema MUST enviar o estado atual ao aceitar a inscrição, incluindo resultados já concluídos, e acompanhar as atualizações seguintes até o estado terminal. O estabelecimento da inscrição MUST cobrir as mudanças ocorridas durante a obtenção e o envio do estado inicial.
- **FR-008** Toda atualização MUST usar o envelope público com `type` igual a `job.updated`, `channel`, `resource_id` e `payload`, mantendo a correlação com a inscrição autorizada.
- **FR-009** Uma falha que impeça processar a inscrição ou continuar o acompanhamento MUST ser comunicada pelo envelope com `type` igual a `job.error`, `channel`, `resource_id` e `message` pública, seguida de encerramento da conexão. A falha do job MUST ser representada pelo estado terminal `failed` no payload de atualização do canal correspondente.
- **FR-010** O canal `track_generation` MUST usar `request_id` como `resource_id` e entregar `request_id`, `status`, `track_id` e `error_code`. Os estados MUST ser `pending`, `succeeded` e `failed`, sendo os dois últimos terminais. `track_id` MUST identificar a trilha no sucesso e assumir valor nulo nos demais estados. `error_code` MUST conter o código público na falha e assumir valor nulo nos demais estados.
- **FR-011** O canal `assessment` MUST usar `assessment_id` como `resource_id` e entregar `assessment_id`, `status` e `questions`, incluindo `error_code` na falha. Os estados de acompanhamento MUST ser `pending`, `completed` e `failed`, sendo os dois últimos terminais para a geração das perguntas. As perguntas MUST corresponder à representação pública vigente do diagnóstico, com alternativas públicas e proteção do gabarito.
- **FR-012** Para `assessment`, o estado de domínio `pending` MUST corresponder a `pending`, os estados `generated`, `skipped` e `completed` MUST corresponder a `completed`, e `failed` MUST corresponder a `failed`. `questions` MUST ser uma lista vazia enquanto pendente, em caso de dispensa ou falha, e conter as perguntas disponíveis nos demais casos de sucesso.
- **FR-013** O canal `step_preparation` MUST usar `task_id` como `resource_id` e entregar `task_id` e `status`. O acompanhamento MUST representar processamento em andamento como `pending` e resultado terminal como `completed` ou `failed`, conforme o resultado efetivo da preparação.
- **FR-014** O canal `step_summary` MUST usar a chave `{track_id}:{step_id}` como `resource_id`, validar toda a relação entre usuário, trilha e etapa e entregar `step_id` e `status`. O estado MUST ser `pending` durante o processamento, `completed` com `summary` no sucesso ou `failed` com `error` público na falha.
- **FR-015** O sistema MUST publicar resultados dos quatro fluxos a partir das operações existentes, incluindo sucesso anterior à inscrição, falha definitiva e processamento concluído em execução separada. O estado terminal de sucesso MUST indicar um resultado já disponível para uso pelo usuário.
- **FR-016** Cada conexão MUST receber exclusivamente dados do seu usuário, canal e recurso autorizados. A repetição da mesma inscrição MUST manter um único acompanhamento lógico naquela conexão.
- **FR-017** O sistema MUST permitir retomar o acompanhamento com um novo ticket e o mesmo canal e recurso, fornecendo o estado atual. Um estado terminal MUST prevalecer sobre estados anteriores da mesma execução.
- **FR-018** O fechamento normal ou inesperado da conexão e as falhas de envio ou acompanhamento MUST remover a inscrição e liberar seus consumidores e recursos associados. O encerramento do acompanhamento MUST permitir que a operação de aprendizagem continue até o resultado previsto pelo seu fluxo.
- **FR-019** As operações de início de geração de trilha, diagnóstico, preparação de etapa e sumário MUST manter compatibilidade com os pedidos, identificadores, códigos de resposta e resultados públicos vigentes. O acompanhamento MUST funcionar a partir desses identificadores e resultados.
- **FR-020** As mensagens públicas MUST utilizar campos semânticos de domínio e mensagens de falha compreensíveis, protegendo credenciais, gabaritos, dados de outros usuários e detalhes internos de processamento.
- **FR-021** As falhas da operação de emissão do ticket MUST usar o formato padronizado de detalhes de problema do produto, com tratamento verificável para autenticação, validação e recurso indisponível.
- **FR-022** A documentação de integração MUST descrever a emissão e validade do ticket, abertura da conexão, inscrição, envelopes, payloads dos quatro canais, estados terminais, falhas e retomada com novo ticket. Ela MUST registrar os endereços de acesso acordados nas tarefas de origem e as configurações de publicação necessárias para conexão segura em produção e distribuição das atualizações entre os processamentos e as conexões.

### Key Entities

- **Ticket de acompanhamento** — Credencial temporária emitida para um usuário autenticado, limitada ao canal e recurso autorizados, com expiração e informação de consumo.
- **Inscrição** — Vínculo de uma conexão com o usuário, canal e identificador de uma operação acompanhada, durante o tempo em que recebe atualizações.
- **Operação acompanhada** — Geração de trilha, geração de perguntas de diagnóstico, tarefa de preparação de etapa ou geração de sumário, com identificação pública, usuário autorizado e estado atual.
- **Atualização de job** — Comunicação correlacionada à inscrição, contendo o estado atual e os dados públicos de resultado ou falha definidos para o canal.
- **Erro de acompanhamento** — Comunicação de impossibilidade de aceitar ou continuar uma inscrição, com identificação do escopo autorizado e mensagem pública.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** Em 100% dos cenários de aceite dos quatro fluxos, o usuário recebe o resultado de sucesso ou falha pela conexão de acompanhamento e reconhece se pode continuar a jornada, dispensando consultas periódicas de estado pelo cliente.
- **SC-002** Em 100% dos cenários em que a operação avança antes ou durante a inscrição, o primeiro estado e as atualizações seguintes permitem conhecer o resultado atual, incluindo conclusões ocorridas antes da conexão.
- **SC-003** Em 100% das tentativas de acesso com credenciais inválidas, expiradas, consumidas ou direcionadas a recurso sem permissão, o acesso é recusado. A reutilização concorrente da mesma credencial autoriza no máximo uma conexão, e a quantidade de mensagens entregues fora do escopo autorizado é zero.
- **SC-004** Em 100% dos cenários de retomada com nova credencial válida, o usuário consegue identificar o estado atual da mesma operação, inclusive quando ela terminou durante a desconexão.
- **SC-005** Após cada cenário de fechamento normal, fechamento inesperado e falha de acompanhamento, a quantidade de inscrições, consumidores e recursos de acompanhamento associados à conexão encerrada é zero.
- **SC-006** Em condições controladas de validação, pelo menos 95% dos estados iniciais e resultados terminais ficam disponíveis ao cliente em até 2 segundos da aceitação da inscrição ou da disponibilização do resultado, respectivamente.
- **SC-007** Todos os cenários de compatibilidade das quatro operações de início continuam aprovados, cobrindo seus resultados imediatos e os identificadores usados no acompanhamento.
- **SC-008** Uma pessoa responsável pela integração consegue executar os quatro fluxos seguindo a documentação publicada, incluindo conexão segura, sucesso, falha, encerramento e retomada.

## Assumptions

- O escopo funcional e o contrato de integração são fornecidos pela SDB-109 e pela tarefa consumidora SDB-104, incluindo os endereços de emissão de ticket e de conexão e o envio da inscrição após a abertura. [SDB-109](https://fromzero-api.atlassian.net/browse/SDB-109) · [SDB-104](https://fromzero-api.atlassian.net/browse/SDB-104)
- A validade de 60 segundos do ticket é uma premissa adotada para tornar verificável a exigência de curta duração. Sua expiração limita a abertura da conexão.
- Cada conexão acompanha o único par de canal e recurso autorizado pelo ticket. Retomadas usam um novo ticket para esse mesmo par.
- Os valores `completed` e `failed` descritos para preparação e sumário são interpretados como estados terminais, conforme a SDB-104. O estado `pending` completa o snapshot obrigatório enquanto essas operações estão em andamento.
- O canal `assessment` acompanha a disponibilidade das perguntas. O estado de domínio `generated` já representa sucesso dessa geração, e a dispensa `skipped` também encerra a espera. Esses estados e o diagnóstico já respondido `completed` são representados como `completed` no acompanhamento, em alinhamento com o exemplo público das tarefas.
- A autenticação, a identificação do usuário e as regras atuais de acesso a trilhas, etapas e diagnósticos fornecem a base da autorização. O acompanhamento da preparação depende de vincular cada `task_id` aceito ao usuário e à operação correspondente.
- O fluxo atual de geração do sumário pode devolver o conteúdo na própria chamada de início. Essa entrega é coberta pelo estado terminal disponível na inscrição posterior.
- Fechar a conexão representa cancelar a espera do cliente. O processamento da operação segue seu ciclo normal.
- A entrega desta tarefa é o acompanhamento no backend e sua documentação. A integração das telas e a configuração cliente de `VITE_WS_URL` são dependências da SDB-104. A documentação desta entrega deve permitir publicação com `wss://` em produção.
- O alvo de 2 segundos para comunicação em condições controladas é uma premissa de experiência de uso, a ser verificada para os quatro fluxos no planejamento da validação.
