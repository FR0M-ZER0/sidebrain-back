# Feature Specification: Geração incremental de conteúdo de Steps

**Feature Branch**: `SDB-60-incremental-step-content`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "SDB-60 - Criar funcionalidade para geração de lições e quizzes"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preparar o próximo Step antes da conclusão (Priority: P1)

Como usuário que percorre uma trilha, quero que o conteúdo do próximo Step seja preparado quando eu estiver próximo de concluir o Step atual, para continuar estudando sem esperar uma geração síncrona.

**Why this priority**: O look-ahead reduz a espera percebida e evita gerar antecipadamente o conteúdo de toda a Track.

**Independent Test**: Simular o progresso de um Step com 80% ou mais de suas Lessons ativas concluídas e verificar que o próximo Step elegível é identificado e sua geração é enfileirada sem aguardar o provedor externo.

**Acceptance Scenarios**:

1. **Given** um Step ativo com Lessons ativas e pelo menos 80% delas concluídas e um próximo Step sem conteúdo, **When** o progresso é processado, **Then** o sistema enfileira a geração assíncrona do próximo Step e conclui a operação original sem chamar o provedor externo durante a requisição.
2. **Given** um Step com menos de 80% de Lessons ativas concluídas, **When** o progresso é processado, **Then** o sistema não enfileira a geração do próximo Step.
3. **Given** um Step que não possui próximo Step elegível na mesma Track, **When** o threshold é atingido, **Then** o sistema conclui o processamento sem criar conteúdo adicional.

---

### User Story 2 - Gerar conteúdo coerente para um Step (Priority: P1)

Como sistema de aprendizagem, quero gerar o conteúdo do próximo Step usando o contexto da Track e dos Steps anteriores, para entregar Lessons, Quizzes e Missions coerentes com a sequência da trilha.

**Why this priority**: Sem conteúdo válido e relacionado à trilha, o avanço assíncrono não entrega valor ao usuário.

**Independent Test**: Executar a tarefa para um Step elegível e verificar que o conteúdo retornado é validado e persistido com os relacionamentos corretos entre Step, Lessons, Quizzes e Missions.

**Acceptance Scenarios**:

1. **Given** um Step ativo sem conteúdo e uma Track com contexto disponível, **When** a tarefa de geração é processada, **Then** ela consulta a hierarquia necessária, gera e persiste Lessons ordenadas, Quizzes associados às Lessons e Missions associadas ao Step.
2. **Given** uma resposta válida do provedor contendo conteúdo permitido, **When** ela é processada, **Then** a aplicação define IDs, relacionamentos, estado e datas, sem aceitar esses campos como decisão do conteúdo gerado.
3. **Given** uma resposta inválida ou incompatível com os valores permitidos, **When** ela é processada, **Then** nenhum conteúdo parcial fica disponível e a falha é registrada conforme a política de execução assíncrona.

---

### User Story 3 - Evitar duplicidade e recuperar falhas transitórias (Priority: P1)

Como responsável pelo produto, quero que execuções repetidas ou concorrentes não dupliquem conteúdo e que falhas temporárias possam ser repetidas, para manter a integridade da trilha.

**Why this priority**: O disparo pode ocorrer mais de uma vez próximo ao threshold e o provedor externo pode falhar; ambos os casos precisam ser seguros.

**Independent Test**: Submeter duas execuções simultâneas para o mesmo Step e simular timeout e indisponibilidade temporária do provedor, verificando ausência de duplicação, rollback em falha de persistência e limite de tentativas.

**Acceptance Scenarios**:

1. **Given** duas tarefas concorrentes para o mesmo Step, **When** ambas tentam gerar conteúdo, **Then** somente uma persiste o conteúdo e a outra encerra sem duplicar Lessons, Quizzes ou Missions.
2. **Given** um Step que já possui conteúdo ativo, **When** a tarefa é executada novamente, **Then** ela não chama o provedor nem cria novos registros.
3. **Given** uma falha transitória do provedor, **When** a tarefa é processada, **Then** ela pode ser repetida automaticamente até o limite configurado e não deixa conteúdo parcial persistido.
4. **Given** uma falha permanente ou o esgotamento das tentativas, **When** a tarefa termina, **Then** ela registra uma falha observável sem repetir indefinidamente.

---

### Edge Cases

- O progresso deve considerar somente Lessons ativas; registros excluídos logicamente não entram no total nem no cálculo de conclusão.
- Um Step sem Lessons ativas não deve produzir divisão inválida nem disparar geração apenas por ausência de conteúdo.
- O valor exatamente igual a 80% deve atingir o threshold; valores abaixo não devem atingir.
- O próximo Step pode já estar em geração ou possuir apenas conteúdo parcial após uma falha anterior; a tarefa deve impedir duplicação e garantir que uma nova tentativa não preserve estado inconsistente.
- Steps excluídos, Tracks excluídas e relações fora da mesma Track não devem ser candidatos.
- A ordem de Lessons deve permanecer consistente por `position`, sem posições duplicadas para o mesmo Step.
- O conteúdo gerado não deve criar Answers, Feedbacks, LessonFiles ou MissionProgress.
- Uma falha ao persistir qualquer parte do conteúdo deve desfazer a operação inteira.
- A ausência de configuração ou indisponibilidade definitiva do provedor deve terminar sem retry infinito e sem expor credenciais.
- A atualização de progresso deve permanecer responsiva enquanto a geração ocorre em segundo plano.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar uma tarefa assíncrona que receba a identificação do Step alvo e gere seu conteúdo sem exigir `userId`.
- **FR-002**: O sistema MUST calcular o progresso do Step a partir da proporção de Lessons ativas concluídas em relação ao total de Lessons ativas.
- **FR-003**: O sistema MUST considerar o threshold atingido quando o progresso for maior ou igual a 80%.
- **FR-004**: Ao atingir o threshold, o sistema MUST identificar o próximo Step ativo da mesma Track que ainda não possui conteúdo elegível para consumo.
- **FR-005**: O sistema MUST enfileirar a geração do próximo Step de forma assíncrona e MUST NOT aguardar a chamada ao provedor externo na operação que processa o progresso.
- **FR-006**: A tarefa MUST consultar a Track, o Step alvo e o contexto dos Steps anteriores necessários antes de solicitar geração.
- **FR-007**: A geração MUST produzir conteúdo para Lessons, Quizzes associados às Lessons e Missions associadas ao Step.
- **FR-008**: O sistema MUST validar estruturalmente o resultado gerado antes de persistir qualquer conteúdo.
- **FR-009**: A aplicação MUST definir IDs, chaves estrangeiras, estados, datas e flags de exclusão; esses campos não podem ser determinados livremente pelo provedor externo.
- **FR-010**: A aplicação MUST preservar os relacionamentos Track → Step, Step → Lesson, Step → Mission e Lesson → Quiz.
- **FR-011**: Lessons MUST ser persistidas com posições consistentes e únicas dentro do Step, respeitando a ordenação do conteúdo.
- **FR-012**: A persistência de Lessons, Quizzes e Missions MUST ser atômica; qualquer falha deve impedir conteúdo parcial persistido.
- **FR-013**: A tarefa MUST ser idempotente e segura contra concorrência para o mesmo Step, de forma que execuções repetidas não criem duplicatas.
- **FR-014**: A tarefa MUST encerrar sem chamar o provedor quando o Step já possuir conteúdo ativo completo ou estiver protegido por uma geração equivalente em andamento.
- **FR-015**: Falhas transitórias do provedor MUST permitir retry automático limitado; falhas permanentes ou conteúdo inválido MUST não provocar retries indefinidos.
- **FR-016**: O sistema MUST respeitar os enums e relacionamentos existentes ao persistir o conteúdo gerado.
- **FR-017**: A geração MUST NOT criar Answer, Feedback, LessonFile ou MissionProgress.
- **FR-018**: A funcionalidade MUST ser acionável pela lógica existente de atualização do progresso e MUST NOT criar novos endpoints HTTP nesta feature.
- **FR-019**: O contexto enviado ao provedor MUST incluir informações suficientes da Track, do Step e dos Steps anteriores para evitar conteúdo incoerente ou repetitivo.
- **FR-020**: Logs e falhas MUST permitir diagnosticar sucesso, retry e erro definitivo sem registrar credenciais ou dados sensíveis desnecessários.

### Key Entities

- **Track**: trilha de aprendizagem que agrupa Steps e fornece título, descrição e contexto geral.
- **Step**: etapa ordenada da Track cujo progresso aciona a preparação do próximo conteúdo.
- **Lesson**: unidade de conteúdo do Step, com texto, posição e estado ativo; é a base do cálculo de progresso.
- **Quiz**: avaliação associada a uma Lesson gerada; Answers submetidas por usuários estão fora do escopo.
- **Mission**: atividade associada ao Step, com dificuldade, recompensa e critérios compatíveis com os valores do produto.
- **Contexto de geração**: conjunto de informações da Track, do Step alvo e dos Steps anteriores usado para orientar a geração.
- **Tarefa de geração**: execução assíncrona responsável por validar, gerar e persistir o conteúdo de um Step.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos casos cobertos em que o progresso atinge exatamente ou supera 80%, um próximo Step elegível é enfileirado sem bloquear a operação de atualização do progresso.
- **SC-002**: Em 100% dos casos abaixo de 80%, nenhum conteúdo do próximo Step é gerado antecipadamente.
- **SC-003**: 100% das execuções bem-sucedidas persistem Lessons, Quizzes e Missions com seus relacionamentos corretos e sem criar entidades fora do escopo.
- **SC-004**: 100% das respostas inválidas ou falhas durante a persistência deixam zero conteúdo parcial disponível para o Step alvo.
- **SC-005**: Em testes com duas tarefas concorrentes para o mesmo Step, o sistema cria no máximo uma coleção de conteúdo para esse Step.
- **SC-006**: 100% das falhas transitórias simuladas podem ser repetidas até um limite finito, e 100% das falhas permanentes encerram sem loop infinito.
- **SC-007**: Pelo menos 95% das tarefas válidas de geração concluídas em ambiente de teste disponibilizam o conteúdo antes de o usuário iniciar o próximo Step, considerando a janela entre 80% e 100% de progresso.
- **SC-008**: 100% dos cenários de aceite das jornadas prioritárias são cobertos por testes automatizados antes da liberação.

## Assumptions

- O sistema existente já mantém a estrutura de Track, Step, Lesson, Quiz e Mission e dispõe de um mecanismo para identificar Lessons concluídas pelo usuário.
- O limiar de 80% é fixo nesta primeira versão e inclui o valor exato de 80%.
- Um Step é considerado sem conteúdo quando não possui a coleção ativa esperada de Lessons e demais conteúdos gerados; o critério exato deve reutilizar as regras existentes do domínio.
- A geração inicial do primeiro Step já existe e será reutilizada ou preservada; esta feature amplia o fluxo para Steps subsequentes.
- O provedor externo de IA e suas credenciais já são configurados pelo produto; a feature não altera a política de credenciais.
- A política de retry usará os limites existentes para tasks assíncronas, com diferenciação entre falhas transitórias e permanentes.
- A transação e o mecanismo de concorrência serão escolhidos conforme as capacidades já disponíveis na persistência, sem alterar o contrato HTTP público.
- A quantidade de Lessons, Quizzes por Lesson e Missions por Step será definida pelo contrato interno de geração e pelos limites já adotados pelo produto, sem inferir novos campos de negócio.
- Answers, Feedbacks, LessonFiles, MissionProgress, Badges, BadgeProgress, DayStreaks e Logins não fazem parte da geração incremental.
- Nenhum endpoint HTTP novo, Request Schema ou Response Schema público será criado para esta feature.
