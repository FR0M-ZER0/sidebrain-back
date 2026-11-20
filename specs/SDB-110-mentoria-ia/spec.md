# Feature Specification: Mentoria de aprendizagem por IA

**Feature Branch**: `feat/sdb-110-adiciona-mentor-ia`

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "Adicionar uma funcionalidade de mentoria por IA que ajude o estudante com seus estudos, guiando-o sobre onde melhorar, o que estudar e como estudar, sem atuar principalmente como professor."

## Clarifications

### Session 2026-11-18

- Q: Ao pedir orientação, sobre quais estudos o mentor deve considerar informações do estudante? → A: O estudante escolhe uma trilha e o mentor considera os dados dessa trilha.
- Q: Como as conversas de mentoria devem se relacionar com as trilhas escolhidas pelo estudante? → A: Cada conversa pertence a uma trilha fixa; o estudante pode abrir várias conversas para a mesma trilha.
- Q: Como o estudante deve poder remover seu histórico de conversas com o mentor? → A: Pode excluir uma conversa específica ou todo o histórico.
- Q: O que deve acontecer com as mensagens quando o estudante exclui uma conversa? → A: O conteúdo das mensagens e orientações armazenadas é apagado, respeitando eventuais obrigações legais.
- Q: Quando a mentoria precisar enviar mensagens e dados da trilha a um serviço externo de IA, como o estudante deve autorizar esse uso? → A: Deve receber informações sobre o uso dos dados e conceder autorização específica antes do primeiro compartilhamento para mentoria.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receber orientação para estudar (Priority: P1)

Como estudante, quero escolher uma trilha, apresentar meu objetivo ou dificuldade e receber orientações sobre o que priorizar e como estudar, para avançar com autonomia.

**Why this priority**: Uma orientação prática e individual é o principal valor da mentoria.

**Independent Test**: Um estudante autenticado informa um objetivo e uma dificuldade e solicita orientação; verifica que recebe prioridade de estudo, justificativa e ação prática, em vez de uma aula completa.

**Acceptance Scenarios**:

1. **Given** um estudante autenticado que informa seu objetivo e sua dificuldade, **When** solicita orientação, **Then** recebe pelo menos uma área para melhorar, uma prioridade de estudo, uma justificativa ligada ao contexto e uma ação prática de como estudar.
2. **Given** uma solicitação para resolver uma atividade pelo estudante, **When** o mentor responde, **Then** prioriza perguntas, dicas ou passos para que ele avance por conta própria, em vez de entregar a solução completa.
3. **Given** uma solicitação sem contexto suficiente para orientar, **When** o mentor responde, **Then** solicita informações relevantes em vez de afirmar dificuldades ou conhecimentos não identificados.

### User Story 2 - Usar o contexto do aprendizado (Priority: P2)

Como estudante, quero que a orientação considere meu aprendizado disponível no sistema, para receber recomendações coerentes com meus objetivos e meu progresso.

**Why this priority**: O contexto ajuda o mentor a priorizar oportunidades reais de melhoria sem obrigar o estudante a repetir informações.

**Independent Test**: Solicitar orientação com dados de progresso conhecidos e, em outra situação, sem dados disponíveis; verificar que a resposta usa o contexto pertinente no primeiro caso e reconhece sua ausência no segundo.

**Acceptance Scenarios**:

1. **Given** dados pertinentes da trilha escolhida, de seu progresso ou de suas avaliações disponíveis, **When** o estudante solicita mentoria, **Then** a orientação considera os dados aplicáveis e identifica a base da recomendação sem inventar resultados.
2. **Given** um estudante sem histórico pertinente, **When** solicita mentoria, **Then** o mentor informa que dispõe de contexto limitado e pede informações ou oferece orientações iniciais condicionadas ao que foi informado.
3. **Given** uma referência a dados pertencentes a outro estudante, **When** é solicitada orientação, **Then** o sistema não utiliza nem revela esses dados.
4. **Given** que a mentoria precise compartilhar dados com um serviço externo de IA pela primeira vez, **When** o estudante solicita orientação, **Then** é informado sobre os dados e seu uso e pode autorizar antes do compartilhamento.
5. **Given** que o estudante não autorizou o compartilhamento, **When** uma orientação depender desse serviço externo, **Then** nenhum dado é enviado ao serviço e o estudante é informado de que a orientação não pode ser gerada.

### User Story 3 - Aprofundar uma orientação (Priority: P2)

Como estudante, quero continuar a conversa e esclarecer uma recomendação, para adaptar os próximos passos às minhas dúvidas e disponibilidade.

**Why this priority**: A mentoria ganha utilidade quando o estudante pode pedir ajustes e detalhamentos sem repetir toda a conversa.

**Independent Test**: Receber uma orientação, informar uma restrição de tempo na mesma conversa e verificar que a resposta seguinte considera essa restrição e o contexto anterior.

**Acceptance Scenarios**:

1. **Given** uma conversa de mentoria iniciada, **When** o estudante pede esclarecimento ou informa uma restrição, **Then** o mentor considera as mensagens anteriores pertinentes e adapta a orientação.
2. **Given** uma conversa existente, **When** seu estudante retorna e solicita sua consulta, **Then** pode visualizar as mensagens e orientações anteriores em ordem de envio.
3. **Given** uma conversa de outro estudante, **When** um usuário tenta consultá-la ou continuá-la, **Then** o acesso é recusado e seu conteúdo não é revelado.
4. **Given** uma trilha própria com conversa existente, **When** o estudante inicia outra conversa para a mesma trilha, **Then** a nova conversa mantém histórico independente e permanece vinculada àquela trilha.
5. **Given** conversas próprias existentes, **When** o estudante exclui uma delas, **Then** o conteúdo armazenado de suas mensagens e orientações é apagado, respeitadas eventuais obrigações legais, e ela deixa de estar disponível para consulta e continuação, sem afetar as outras.
6. **Given** conversas próprias em uma ou mais trilhas, **When** o estudante exclui todo o histórico de mentoria, **Then** nenhuma dessas conversas fica disponível para consulta ou continuação, sem afetar dados de outros estudantes.

### Edge Cases

- Mensagem vazia ou composta apenas por espaços é recusada com orientação para preenchimento.
- Histórico inexistente, insuficiente ou desatualizado não deve ser apresentado como evidência de uma dificuldade atual; o mentor pede contexto ou explicita a limitação.
- Dados de aprendizado conflitantes são tratados como incerteza; o mentor pede esclarecimento em vez de escolher uma conclusão como fato.
- Uma trilha inexistente ou que não pertença ao estudante não pode ser usada na mentoria; o sistema recusa a solicitação sem revelar dados de terceiros.
- Um estudante sem trilha própria precisa criar ou obter acesso a uma trilha própria antes de solicitar mentoria.
- Conversas excluídas não podem ser consultadas, continuadas ou usadas como contexto em novas orientações.
- Se a orientação não puder ser gerada, o estudante é informado e pode tentar novamente; não é exibida uma resposta parcial como concluída.
- Solicitações fora do propósito de estudo recebem um redirecionamento para orientação de aprendizagem.
- Orientações não devem prometer resultados garantidos nem substituir aconselhamento profissional em situações de saúde ou segurança; nesses casos, o estudante deve ser orientado a buscar apoio adequado.
- Nenhuma recomendação altera automaticamente trilhas, progresso, avaliações ou atividades do estudante.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um estudante autenticado escolha uma trilha própria e envie uma solicitação textual de mentoria sobre seus estudos nessa trilha.
- **FR-002**: O mentor MUST orientar o estudante sobre oportunidades de melhoria, prioridades de estudo e ações práticas de como estudar, relacionando as recomendações ao contexto disponível.
- **FR-003**: O mentor MUST favorecer a autonomia com perguntas, dicas e próximos passos; pedidos de solução de atividades MUST ser respondidos com orientação, sem fornecer a solução completa.
- **FR-004**: Quando o contexto for insuficiente para uma recomendação específica, o mentor MUST indicar a limitação e pedir informações relevantes ou apresentar orientação inicial explicitamente condicionada ao contexto informado.
- **FR-005**: O sistema MUST considerar dados pertinentes disponíveis da trilha escolhida pelo estudante, incluindo seu progresso e suas avaliações quando aplicáveis, sem inventar fatos ou resultados; dados de outras trilhas não MUST ser usados como contexto.
- **FR-006**: O mentor MUST indicar ao estudante quais informações sustentam recomendações específicas e distinguir informações conhecidas de hipóteses ou incertezas.
- **FR-007**: O sistema MUST permitir que o estudante continue uma conversa, considerando as mensagens anteriores pertinentes ao responder.
- **FR-008**: O sistema MUST conservar e disponibilizar ao estudante as mensagens e orientações da própria conversa em ordem de envio para consulta posterior.
- **FR-008a**: Cada conversa MUST estar vinculada a uma única trilha fixa; o estudante MUST poder iniciar mais de uma conversa independente para a mesma trilha.
- **FR-008b**: O estudante MUST poder excluir uma conversa própria ou todo o seu histórico de mentoria; o conteúdo armazenado das mensagens e orientações excluídas MUST ser apagado, respeitadas eventuais obrigações legais, e MUST deixar de estar disponível para consulta, continuação e uso como contexto.
- **FR-009**: O sistema MUST restringir a consulta e continuação das conversas e o uso de dados pessoais de aprendizagem ao respectivo estudante autenticado.
- **FR-010**: O sistema MUST rejeitar mensagens vazias e informar o estudante quando não for possível gerar a orientação, sem apresentar conteúdo parcial como resposta concluída; MUST permitir nova tentativa.
- **FR-011**: O mentor MUST redirecionar solicitações sem relação com aprendizagem para seu propósito de orientação de estudos.
- **FR-012**: O mentor MUST evitar garantias de resultado e, diante de necessidade de apoio profissional em saúde ou segurança, recomendar a busca de apoio adequado sem se apresentar como substituto.
- **FR-013**: A mentoria MUST NOT modificar automaticamente trilhas, avaliações, atividades ou progresso em decorrência de uma recomendação.
- **FR-014**: O sistema MUST proteger o conteúdo das conversas e dados de aprendizagem de acesso não autorizado e limitar seu uso ao necessário para fornecer a mentoria.
- **FR-015**: Antes do primeiro compartilhamento de mensagens ou dados de trilha com serviço externo de IA para mentoria, o sistema MUST informar quais dados serão usados e para qual finalidade e obter autorização específica do estudante; sem autorização MUST NOT enviar esses dados e MUST informar quando não puder gerar a orientação.

### Key Entities

- **Estudante**: usuário autenticado que solicita orientação e possui seus dados de aprendizagem.
- **Conversa de mentoria**: sequência de mensagens e orientações pertencente a um estudante e vinculada a uma única trilha fixa; uma trilha pode ter várias conversas independentes.
- **Mensagem de mentoria**: solicitação, esclarecimento ou resposta vinculada a uma conversa, com autoria e ordem de envio.
- **Contexto de aprendizagem**: trilha própria escolhida, objetivo e dificuldades informados pelo estudante e dados pertinentes disponíveis dessa trilha, como progresso e avaliações.
- **Orientação**: resposta do mentor com recomendações ou perguntas de esclarecimento, fundamentadas no contexto disponível.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em uma avaliação de pelo menos 20 solicitações representativas com contexto suficiente, ao menos 90% das respostas apresentam uma área de melhoria, uma prioridade de estudo, sua justificativa e uma ação prática.
- **SC-002**: Em uma avaliação de pelo menos 20 pedidos de resolução de atividades, ao menos 90% das respostas oferecem orientação para o estudante avançar sem entregar a solução completa.
- **SC-003**: Em todos os cenários de teste sem contexto suficiente ou com dados conflitantes, a resposta reconhece a limitação ou incerteza e não apresenta informações não fornecidas como fatos.
- **SC-004**: Em testes com pelo menos dois estudantes, 100% das tentativas de acessar conversas ou usar dados de aprendizagem do outro estudante são recusadas ou não revelam os dados.
- **SC-005**: Em teste de acompanhamento com pelo menos 10 conversas, ao menos 90% das respostas a uma restrição posterior consideram a restrição e uma informação pertinente da conversa anterior.
- **SC-006**: Na avaliação manual de pelo menos 10 cenários sintéticos de mentoria, ao menos 80% das respostas apresentam um próximo passo de estudo claramente identificável.

## Assumptions

- A SDB-110, identificada anteriormente pelo usuário, corresponde a esta funcionalidade; o Jira não estava disponível para confirmar seus detalhes.
- A primeira versão é acionada pelo estudante, usa conversa textual e mantém seu histórico para consulta; notificações proativas e canais de voz estão fora do escopo inicial.
- A mentoria utiliza autenticação e dados de aprendizado existentes da trilha escolhida quando disponíveis; uma trilha própria é necessária, mas avaliações não são obrigatórias.
- A orientação é informativa: criar ou modificar automaticamente planos, trilhas ou atividades, bem como substituir professores ou profissionais de saúde, está fora do escopo.
- Os resultados de qualidade são metas de avaliação, não garantias para cada resposta individual.
- A avaliação inicial usa cenários sintéticos e não exige participantes reais; ela não substitui um teste de usabilidade com estudantes.
