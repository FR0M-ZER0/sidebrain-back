# Feature Specification: Geração de Missões por IA para Steps

**Feature Branch**: `SDB-93-generate-step-missions`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "SDB-93 — geração de missões por IA integrada à criação de trilhas, preparação incremental de Steps e solicitação assíncrona sob demanda."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Solicitar missões para um Step (Priority: P1)

Como usuário autenticado que possui uma Trilha, quero solicitar missões para um Step ainda sem missões, para receber atividades relevantes sem esperar a geração terminar.

**Why this priority**: Permite completar ou recuperar o conteúdo de um Step sob demanda, sem manter o cliente aguardando um serviço externo.

**Independent Test**: Solicitar a geração para um Step ativo e autorizado sem missões, com o serviço de IA deliberadamente lento, e confirmar que a API responde com aceitação e identificador da tarefa antes do término da geração.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado e um Step ativo de uma Trilha sua, sem missões ativas, **When** ele solicita a geração sem opções, **Then** a API responde `202 Accepted` com `status: accepted`, o identificador do Step e o identificador da tarefa, sem aguardar a IA.
2. **Given** um Step ativo do usuário sem missões, **When** ele solicita a geração com opções válidas, **Then** a solicitação é aceita e essas opções são consideradas na geração.
3. **Given** um Step que já possui missões ativas, **When** o usuário solicita novamente a geração, **Then** a API responde `200 OK` com `status: skipped` e `reason: missions_already_exist`, sem criar duplicatas.
4. **Given** um Step inexistente, excluído logicamente ou pertencente a outro usuário, **When** qualquer usuário tenta solicitar sua geração, **Then** a resposta é o mesmo `404 Not Found`, sem revelar a existência ou o proprietário do Step.
5. **Given** uma solicitação sem credencial válida, **When** o cliente solicita a geração, **Then** o sistema responde `401 Unauthorized`.
6. **Given** uma solicitação com `count` fora de 1 a 3, uma dificuldade não permitida ou foco fora do limite definido, **When** o cliente a envia, **Then** o sistema responde `422 Unprocessable Content` e não agenda geração alguma.
7. **Given** duas solicitações concorrentes para o mesmo Step ainda sem missões, **When** ambas são processadas, **Then** no máximo um conjunto de missões ativas é persistido.

### User Story 2 - Receber missões junto à geração inicial da Trilha (Priority: P1)

Como usuário que solicita uma Trilha personalizada, quero que a primeira etapa receba uma missão adequada ao seu conteúdo, para começar a aprender com uma atividade coerente desde o início.

**Why this priority**: A missão da etapa inicial faz parte do valor entregue pela Trilha recém-gerada e não deve depender de uma solicitação adicional.

**Independent Test**: Gerar uma Trilha válida e verificar que o primeiro Step pode conter uma missão validada, enquanto Steps posteriores permanecem sem conteúdo inicial, preservando o contrato atual de geração.

**Acceptance Scenarios**:

1. **Given** um pedido válido de criação de Trilha, **When** a geração inicial termina com sucesso, **Then** o primeiro Step pode conter uma missão gerada pela IA e os Steps futuros permanecem sem Lessons e sem missão até serem preparados.
2. **Given** uma resposta de IA válida para a missão inicial, **When** a Trilha é persistida, **Then** a missão respeita o Step ao qual pertence e suas regras de domínio.
3. **Given** uma resposta inválida para a missão, **When** a Trilha é processada, **Then** nenhum dado de missão inválido é persistido e o fluxo existente de geração trata a falha sem criar persistência parcial.

### User Story 3 - Receber missões durante a preparação incremental (Priority: P1)

Como usuário que avança em uma Trilha, quero que a preparação do próximo Step gere missões coerentes junto ao seu conteúdo, para ter atividades disponíveis quando a etapa for liberada.

**Why this priority**: Mantém a experiência de progressão completa e consistente com a geração inicial e com a solicitação sob demanda.

**Independent Test**: Preparar um Step elegível e verificar que Lessons e missões válidas são disponibilizadas em conjunto, sem duplicação em nova tentativa ou concorrência.

**Acceptance Scenarios**:

1. **Given** um Step elegível para preparação incremental, **When** seu conteúdo é gerado, **Then** as missões acompanham o conteúdo e obedecem às mesmas regras de validação e persistência da geração sob demanda.
2. **Given** um Step já preparado ou com conteúdo ativo, **When** uma nova preparação é solicitada, **Then** o comportamento de idempotência existente é mantido e conteúdo duplicado não é criado.
3. **Given** uma resposta inválida de missão durante a preparação, **When** o lote é persistido, **Then** o lote inteiro é rejeitado e não resta conteúdo parcialmente persistido.
4. **Given** uma falha transitória do provedor durante a preparação, **When** a política de tentativas é aplicada, **Then** novas tentativas permanecem limitadas e o endpoint que iniciou o fluxo não aguarda o provedor.

### Edge Cases

- Uma geração enfileirada pode ser iniciada depois que o Step foi excluído ou recebeu missões por outra operação; o processamento deve revalidar o estado e encerrar sem duplicar conteúdo.
- A IA pode retornar JSON inválido, campos ausentes ou extras, tipos incorretos, título vazio, enum desconhecido ou valores numéricos não positivos; nenhuma missão inválida deve ser persistida.
- Uma missão válida não pode referenciar um Step, progresso, resposta, feedback ou arquivo informado pela IA; o vínculo com o Step solicitado é determinado pelo sistema.
- Uma falha de persistência em qualquer missão do lote deve desfazer integralmente as alterações daquele lote.
- Erros transitórios do provedor podem ser repetidos de forma limitada; erros de parsing ou validação não devem ser repetidos automaticamente.
- O contexto pedagógico enviado ao provedor deve excluir e-mail, hashes, tokens e outros dados sensíveis.
- O critério de uma missão deve corresponder às atividades do Step; critérios que dependam de quizzes não devem ser escolhidos se não houver quizzes pertinentes.
- A ausência do corpo da solicitação equivale às opções padrão; opções parciais devem ser aceitas quando válidas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um usuário autenticado solicite a geração de missões para um Step pertencente a uma Trilha sua, por meio de `POST /steps/{step_id}/missions/generate`.
- **FR-002**: O corpo da solicitação MUST ser opcional e, quando fornecido, MUST aceitar somente `count`, `difficulty` e `focus`; campos desconhecidos MUST ser rejeitados.
- **FR-003**: `count` MUST aceitar valores inteiros de 1 a 3, com padrão 1; `difficulty` MUST aceitar `easy`, `medium`, `hard` ou `very_hard`; `focus` MUST ser texto aparado de 1 a 500 caracteres.
- **FR-004**: A solicitação válida para Step ativo sem missões MUST retornar `202 Accepted` imediatamente, com `status: accepted`, `stepId` e `taskId`, sem aguardar a conclusão da geração.
- **FR-005**: Se o Step já tiver missões ativas, a solicitação MUST retornar `200 OK` com `status: skipped` e `reason: missions_already_exist`, sem criar missões adicionais.
- **FR-006**: Steps inexistentes, logicamente excluídos ou não pertencentes ao usuário autenticado MUST produzir resposta indistinguível `404 Not Found`; credenciais ausentes ou inválidas MUST resultar em `401 Unauthorized`.
- **FR-007**: Opções inválidas MUST ser rejeitadas com `422 Unprocessable Content` antes de qualquer trabalho ser agendado.
- **FR-008**: A geração iniciada sob demanda MUST ocorrer fora do ciclo da requisição e MUST revalidar o estado do Step antes de persistir, para prevenir duplicatas em chamadas repetidas ou concorrentes.
- **FR-009**: Toda missão gerada por IA MUST conter somente os campos de negócio `title`, `difficulty`, `xp_reward`, `criteria` e `criteria_value`; a IA MUST NOT fornecer identificadores, timestamps, flags de exclusão, respostas, feedback, arquivos ou progresso.
- **FR-010**: O sistema MUST validar a saída da IA antes de persistir: título aparado não vazio com até 255 caracteres; dificuldade entre `easy`, `medium`, `hard` e `very_hard`; critério entre `number_of_lessons_completed`, `get_all_answer_right_in_a_lesson`, `complete_a_step`, `complete_a_track`, `number_of_steps_completed` e `get_all_answers_right`; e valores inteiros `xp_reward > 0` e `criteria_value > 0`.
- **FR-011**: Campos extras, estrutura inválida ou qualquer campo de negócio inválido na resposta da IA MUST invalidar integralmente o lote; a persistência MUST ser atômica, sem registros parciais.
- **FR-012**: Toda missão persistida MUST pertencer ao Step determinado pelo sistema e MUST iniciar sem progresso associado; nenhum dado de vínculo ou entidade relacionada pode ser confiado à saída da IA.
- **FR-013**: O contexto de geração MUST incluir o título e a descrição da Trilha, título e nível do Step atual, títulos e níveis dos Steps anteriores e missões já existentes no Step, sem e-mail, hashes, tokens ou outros dados sensíveis.
- **FR-014**: O prompt MUST orientar a IA a escolher critérios compatíveis com o conteúdo real do Step e uma dificuldade coerente com seu nível, sem substituir a validação rígida dos campos e enums.
- **FR-015**: Falhas transitórias do provedor MUST usar tentativas limitadas com espera progressiva; falhas de parsing e validação MUST falhar sem retry automático.
- **FR-016**: Falhas do processamento em segundo plano MUST ser registradas com identificadores da tarefa e do Step e uma categoria de erro; a resposta pública MUST seguir Problem Details e MUST NOT expor prompt ou resposta bruta do provedor.
- **FR-017**: A geração inicial da Trilha MUST preservar o contrato atual: somente o primeiro Step recebe conteúdo inicial e pode receber missão gerada; Steps posteriores começam sem Lessons e sem missão.
- **FR-018**: A preparação incremental MUST continuar gerando missões junto ao conteúdo do Step elegível, preservar a prevenção de duplicatas e aplicar as mesmas regras centrais de validação e persistência de missões.
- **FR-019**: Todas as origens de missões geradas por IA MUST convergir para as mesmas regras de domínio, valores positivos, validação e persistência; não deve haver uma rota alternativa que aceite regras divergentes.
- **FR-020**: As missões geradas MUST estar disponíveis nas consultas de missões do Step e nas consultas individuais existentes, com lista de progresso vazia até que o usuário progrida.
- **FR-021**: Os contratos HTTP existentes de criação de Trilha e preparação incremental MUST permanecer inalterados por esta funcionalidade.

### Key Entities

- **Trilha**: percurso de aprendizagem que fornece título e descrição para contextualizar a geração e pertence a um usuário.
- **Step**: etapa ordenada da Trilha, com título e nível; é o recurso-alvo da geração e o proprietário direto das missões.
- **Mission**: atividade associada a exatamente um Step, com título, dificuldade, recompensa de XP, critério e valor do critério; começa sem progresso.
- **Solicitação de geração**: pedido assíncrono para gerar missões em um Step, identificado pela tarefa e associado às opções fornecidas.
- **Opções de geração**: quantidade pretendida, dificuldade sugerida e foco textual opcional, usados para orientar a geração.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em condições normais, pelo menos 95% das solicitações válidas para Steps sem missões recebem resposta em até 1 segundo; em 100% dos testes com provedor deliberadamente lento, o cliente recebe `202 Accepted` e os identificadores necessários antes da conclusão da IA.
- **SC-002**: Em 100% dos testes de Step com missões ativas, a resposta é `200 OK` com `missions_already_exist` e nenhum registro adicional é criado.
- **SC-003**: Em 100% dos casos de Step inexistente, excluído ou pertencente a outro usuário, o cliente observa a mesma resposta `404`, sem informação que permita distinguir esses casos.
- **SC-004**: Em 100% dos testes de lote com pelo menos uma missão inválida ou falha de persistência, zero missões daquele lote permanecem persistidas.
- **SC-005**: Em 100% das respostas aceitas da IA, somente os cinco campos de negócio permitidos são considerados, e todos os valores numéricos persistidos são positivos.
- **SC-006**: Em 100% dos testes com chamadas repetidas ou concorrentes para um mesmo Step, no máximo um conjunto de missões ativas é disponibilizado.
- **SC-007**: Em 100% dos testes com falha de validação ou parsing, não ocorre retry automático; em falhas transitórias do provedor, o número de tentativas nunca excede o limite configurado.
- **SC-008**: Em 100% dos testes do fluxo de geração inicial, somente o primeiro Step recebe conteúdo inicial; em 100% dos testes incrementais, as missões usam as mesmas regras de validação do fluxo sob demanda.
- **SC-009**: Em testes de inspeção do contexto enviado à IA, nenhum e-mail, hash, token ou outro dado sensível do usuário está presente.
- **SC-010**: Clientes conseguem identificar se uma solicitação foi aceita ou ignorada apenas pelo status e campos documentados, e missões válidas tornam-se visíveis pelas consultas existentes do Step.

## Assumptions

- A autenticação, identificação do usuário atual, execução em segundo plano e integração com o provedor de IA já existem e serão reutilizadas.
- A geração sob demanda usa o provedor e o modelo já empregados pela geração de Trilhas.
- `count` usa 1 como padrão quando omitido; valores entre 1 e 3 limitam o tamanho do lote.
- `difficulty` e `focus` são orientações para a IA, não substituem as regras de enum nem a coerência mínima validada pelo domínio.
- Os critérios válidos são `number_of_lessons_completed`, `get_all_answer_right_in_a_lesson`, `complete_a_step`, `complete_a_track`, `number_of_steps_completed` e `get_all_answers_right`.
- A validação centralizada é aplicada também à missão opcional da geração inicial e às missões produzidas durante a preparação incremental.
- Esta funcionalidade depende dos serviços, repositórios e contratos de gerenciamento de Mission definidos pela task de gerenciamento de missões; não inclui a duplicação de operações CRUD.
- `force` para regenerar Steps com missões existentes, geração em lote entre Steps, tradução e avaliação de qualidade das missões estão fora do escopo.
- Regras atuais de elegibilidade e bloqueio de preparação incremental, incluindo o limiar de progresso vigente, permanecem inalteradas.
