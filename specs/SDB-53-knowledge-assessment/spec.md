# Feature Specification: Avaliação de Conhecimento para Trilhas

**Feature Branch**: `SDB-53-knowledge-assessment`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "SDB-53 - Criar funcionalidade para obter o nível do usuário na atividade"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar avaliação inicial de conhecimento (Priority: P1)

Como usuário que deseja criar uma trilha de aprendizagem, quero receber perguntas relacionadas ao assunto e ao meu objetivo para que meu conhecimento prévio possa ser avaliado antes da montagem da trilha.

**Why this priority**: A avaliação inicial fornece o contexto necessário para personalizar a futura trilha sem misturar a geração das perguntas com a criação de seus conteúdos.

**Independent Test**: Solicitar uma avaliação para um assunto e objetivo válidos e verificar que o resultado fica disponível com exatamente cinco perguntas estruturadas e relacionadas ao contexto informado.

**Acceptance Scenarios**:

1. **Given** um contexto válido com assunto e, opcionalmente, objetivo de aprendizagem, **When** o usuário escolhe ser avaliado, **Then** o sistema gera e disponibiliza exatamente cinco perguntas para avaliar o conhecimento prévio.
2. **Given** uma solicitação de avaliação, **When** as perguntas são geradas, **Then** elas cobrem dificuldades capazes de distinguir níveis diferentes de conhecimento e permanecem relacionadas ao assunto e objetivo informados.
3. **Given** uma resposta gerada para a avaliação, **When** o resultado é disponibilizado, **Then** cada pergunta possui identificador, enunciado e alternativas estruturadas para consumo posterior.

### User Story 2 - Iniciar sem avaliação (Priority: P1)

Como usuário que declara não ter conhecimento prévio sobre o assunto, quero iniciar no nível básico sem responder perguntas para prosseguir diretamente para o fluxo posterior de criação da trilha.

**Why this priority**: O caminho sem avaliação é uma alternativa explícita do usuário e precisa ser rápido, previsível e independente de serviços externos.

**Independent Test**: Solicitar uma avaliação com a opção de pular habilitada e verificar que o resultado indica o nível inicial, sem perguntas e sem tentativa de geração externa.

**Acceptance Scenarios**:

1. **Given** um usuário que informou não possuir conhecimento prévio, **When** a avaliação é solicitada com a opção de pular habilitada, **Then** o sistema retorna o status de avaliação pulada e o nível inicial `beginner`.
2. **Given** a opção de pular habilitada, **When** a tarefa é processada, **Then** nenhuma pergunta é gerada e nenhuma chamada ao serviço de geração de perguntas é realizada.

### User Story 3 - Consumir um resultado confiável (Priority: P2)

Como fluxo posterior de criação de trilha, quero consumir um resultado de avaliação consistente para usar as perguntas ou o nível inicial sem depender de dados parcialmente processados.

**Why this priority**: A avaliação será consumida por outro fluxo; resultados inválidos ou incompletos poderiam produzir trilhas inadequadas e difíceis de diagnosticar.

**Independent Test**: Simular respostas válidas, inválidas e indisponibilidade temporária do serviço de geração e verificar validação, retry e ausência de resultados parciais conforme cada caso.

**Acceptance Scenarios**:

1. **Given** uma resposta externa com formato válido e cinco perguntas, **When** o resultado é validado, **Then** ele é disponibilizado integralmente para consumo posterior.
2. **Given** uma resposta externa inválida, incompleta ou com quantidade diferente de cinco perguntas, **When** o sistema tenta validá-la, **Then** a avaliação falha sem disponibilizar dados parcialmente lidos.
3. **Given** uma falha temporária no serviço externo, **When** a geração é processada, **Then** a execução pode ser repetida automaticamente conforme a política de tarefas assíncronas, sem criar uma avaliação parcial.

### Edge Cases

- Um assunto ausente, vazio ou inválido deve impedir a geração de perguntas quando a avaliação estiver habilitada.
- Um objetivo ausente deve ser aceito, mas o assunto continua obrigatório para gerar perguntas.
- Uma resposta com menos ou mais de cinco perguntas deve ser rejeitada.
- Perguntas sem identificador, enunciado ou alternativas válidas devem ser rejeitadas sem exposição do conteúdo parcial.
- A opção de pular deve prevalecer sobre a necessidade de assunto para geração, pois não há perguntas a serem criadas nesse caminho.
- Falhas definitivas, credenciais inválidas ou respostas que não possam ser validadas devem produzir erro observável e não devem ser repetidas indefinidamente.
- Logs devem permitir diagnosticar a execução sem registrar credenciais, respostas sensíveis ou conteúdo desnecessário do usuário.
- A avaliação não deve criar, alterar ou excluir trilhas, etapas, lições ou missões.
- O identificador do usuário deve vir do contexto do fluxo chamador e não deve ser exigido como dado informado pelo usuário.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar uma tarefa assíncrona para preparar a avaliação inicial de conhecimento antes da criação de uma trilha.
- **FR-002**: O sistema MUST aceitar um assunto obrigatório para a geração de perguntas e um objetivo de aprendizagem opcional.
- **FR-003**: O sistema MUST permitir que o fluxo chamador informe se o usuário deseja pular a avaliação.
- **FR-004**: Quando a avaliação estiver habilitada, o sistema MUST solicitar perguntas relacionadas ao assunto e ao objetivo informado, deixando explícito que elas avaliam o conhecimento prévio do usuário.
- **FR-005**: Quando a avaliação estiver habilitada, o sistema MUST disponibilizar exatamente cinco perguntas.
- **FR-006**: Cada pergunta MUST possuir identificador, enunciado e conjunto de alternativas em formato estruturado e validável.
- **FR-007**: As perguntas MUST apresentar dificuldade variada o suficiente para distinguir níveis diferentes de conhecimento sobre o assunto.
- **FR-008**: O sistema MUST validar o resultado gerado antes de disponibilizá-lo ao fluxo posterior.
- **FR-009**: O sistema MUST rejeitar respostas inválidas, incompletas ou com quantidade diferente de cinco perguntas sem disponibilizar conteúdo parcial.
- **FR-010**: Quando o usuário pular a avaliação, o sistema MUST retornar status `skipped` e nível inicial `beginner`, sem gerar perguntas.
- **FR-011**: Quando a avaliação for pulada, o sistema MUST evitar qualquer chamada ao serviço externo de geração de perguntas.
- **FR-012**: Falhas temporárias do serviço externo MUST permitir repetição automática da tarefa conforme a política de execução assíncrona.
- **FR-013**: Falhas definitivas e respostas não recuperáveis MUST ser registradas para diagnóstico, sem retries indefinidos e sem exposição de credenciais ou dados sensíveis.
- **FR-014**: O resultado MUST ser estruturado para ser consumido por um endpoint ou fluxo posterior, sem exigir a criação de endpoint nesta feature.
- **FR-015**: A tarefa MUST obter a identidade do usuário a partir do contexto fornecido pelo fluxo chamador e não MUST exigir `userId` como entrada apresentada ao usuário.
- **FR-016**: A tarefa MUST limitar sua responsabilidade à preparação da avaliação e não MUST criar, atualizar ou excluir Track, Step, Lesson ou Mission.
- **FR-017**: A integração com o serviço externo MUST permanecer separada da regra de negócio de decisão e validação da avaliação.
- **FR-018**: A feature MUST manter a determinação definitiva do nível a partir das respostas e a geração da trilha como etapas posteriores, fora deste escopo.

### Key Entities

- **Contexto de Avaliação**: Assunto, objetivo opcional, preferência do usuário sobre realizar a avaliação e identidade do usuário fornecida pelo fluxo chamador.
- **Pergunta de Conhecimento**: Pergunta identificada, com enunciado e alternativas, criada para medir conhecimento prévio sobre o contexto da trilha.
- **Resultado da Avaliação**: Resultado pronto com identificador e cinco perguntas, ou resultado pulado com status `skipped` e nível inicial `beginner`.
- **Usuário**: Pessoa autenticada que solicita a preparação da avaliação; sua identidade é contextual e não é criada nem alterada por esta feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das solicitações de avaliação habilitada que terminam com sucesso disponibilizam exatamente cinco perguntas válidas.
- **SC-002**: 100% das solicitações com avaliação pulada retornam `beginner`, não incluem perguntas e não acionam o serviço externo de geração.
- **SC-003**: 100% dos resultados inválidos ou incompletos são bloqueados antes de serem disponibilizados ao fluxo posterior.
- **SC-004**: Pelo menos 95% das solicitações válidas de avaliação são concluídas em até 30 segundos, excluindo indisponibilidades externas que acionem retry.
- **SC-005**: 100% das execuções registram informação suficiente para identificar sucesso, falha definitiva ou retry sem expor credenciais e dados sensíveis.
- **SC-006**: Nenhuma execução da avaliação cria ou altera entidades de trilha ou conteúdo relacionadas à trilha.
- **SC-007**: Pelo menos 90% dos consumidores de teste conseguem interpretar o resultado pronto ou pulado sem transformação manual adicional.

## Assumptions

- O fluxo chamador já possui autenticação e fornece a identidade do usuário à tarefa sem exigir que ela seja informada no payload apresentado ao usuário.
- A geração de perguntas usa o provider externo de IA já previsto pelo produto, com credenciais configuradas fora do contexto da solicitação.
- O resultado da avaliação é transitório nesta feature; não será criada tabela ou entidade persistente para armazenar perguntas, respostas ou nível.
- O formato inicial das perguntas é de múltipla escolha, com alternativas textuais, porque permite consumo e avaliação posterior de forma consistente.
- O nível `beginner` representa apenas o ponto inicial quando o usuário pula a avaliação; a classificação definitiva baseada em respostas pertence a outra etapa.
- Um endpoint para disparar ou consultar o resultado pode existir em outra feature, mas não será criado nem alterado nesta.
- Os valores e limites de texto seguirão as validações comuns já adotadas pelo produto para campos de contexto de aprendizagem.
- A política de retry seguirá as regras existentes para tarefas assíncronas e diferenciará falhas temporárias de falhas definitivas.
