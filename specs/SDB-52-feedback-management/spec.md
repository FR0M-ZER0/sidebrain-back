# Feature Specification: Gerenciamento de Feedback

**Feature Branch**: `SDB-52-feedback-management`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "SDB-52"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar feedback em uma aula (Priority: P1)

Como usuário autenticado, quero registrar um feedback associado a uma aula existente para contribuir com a melhoria do conteúdo.

**Why this priority**: Sem a criação, não há ciclo de gerenciamento nem contribuição de usuários.

**Independent Test**: Com uma aula existente e um usuário autenticado, enviar um texto de feedback e verificar que o feedback é criado, associado à aula e atribuído ao usuário autenticado.

**Acceptance Scenarios**:

1. **Given** uma aula existente e não excluída e um usuário autenticado, **When** o usuário envia um texto válido, **Then** o sistema cria um feedback associado à aula e ao usuário autenticado.
2. **Given** uma aula inexistente ou excluída, **When** o usuário tenta criar um feedback, **Then** o sistema recusa a operação e informa que a aula não foi encontrada.
3. **Given** um usuário não autenticado, **When** tenta criar um feedback, **Then** o sistema recusa a operação por falta de autenticação válida.

### User Story 2 - Consultar feedbacks de uma aula (Priority: P1)

Como usuário, quero consultar os feedbacks ativos de uma aula e visualizar esses feedbacks ao consultar a aula, para acompanhar as contribuições relacionadas ao conteúdo.

**Why this priority**: A consulta torna os feedbacks úteis para usuários e responsáveis pelo conteúdo.

**Independent Test**: Criar feedbacks ativos e excluídos para uma aula, consultar a aula e sua coleção de feedbacks e verificar que somente os ativos são exibidos.

**Acceptance Scenarios**:

1. **Given** uma aula existente com feedbacks ativos, **When** a coleção de feedbacks da aula é consultada, **Then** o sistema retorna os feedbacks ativos com identificador, aula, autor, texto e datas de criação e atualização.
2. **Given** uma aula com feedback excluído logicamente, **When** seus feedbacks ou a própria aula são consultados, **Then** o feedback excluído não aparece.
3. **Given** um feedback ativo existente, **When** ele é consultado por identificador, **Then** o sistema retorna seus dados públicos.
4. **Given** uma aula inexistente ou excluída, **When** seus feedbacks são consultados, **Then** o sistema informa que a aula não foi encontrada.

### User Story 3 - Atualizar ou remover o próprio feedback (Priority: P1)

Como usuário autenticado, quero atualizar ou remover logicamente um feedback que escrevi, para corrigir ou retirar uma contribuição.

**Why this priority**: Ownership é essencial para proteger o conteúdo criado pelos usuários.

**Independent Test**: Criar feedbacks para dois usuários e verificar que cada usuário só consegue alterar ou remover logicamente o próprio feedback.

**Acceptance Scenarios**:

1. **Given** um feedback ativo pertencente ao usuário autenticado, **When** o usuário envia um novo texto válido, **Then** somente o texto permitido é atualizado e o feedback retornado reflete a alteração.
2. **Given** um feedback ativo pertencente a outro usuário, **When** o usuário autenticado tenta atualizá-lo, **Then** o sistema recusa a operação por falta de autorização.
3. **Given** um feedback ativo pertencente ao usuário autenticado, **When** o usuário solicita sua remoção, **Then** o sistema realiza a remoção lógica e confirma a operação sem retornar conteúdo.
4. **Given** um feedback inexistente, já excluído ou inacessível, **When** o usuário tenta consultá-lo, atualizá-lo ou removê-lo, **Then** o sistema não realiza alteração e informa o resultado conforme a política de existência e autorização.

### Edge Cases

- Texto ausente, vazio ou inválido deve ser rejeitado sem criar ou alterar feedback.
- Campos de identificação, autoria, datas e exclusão enviados pelo cliente não devem substituir os valores controlados pelo sistema.
- Uma tentativa de criar feedback para aula excluída deve ser tratada como aula inexistente.
- Um feedback excluído não pode ser atualizado, removido novamente ou reaparecer em consultas normais.
- O acesso de um usuário a feedback de outro usuário deve impedir alterações e exclusões indevidas.
- Consultas de aulas com vários feedbacks devem retornar a composição completa sem gerar uma consulta individual desnecessária para cada feedback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que usuários autenticados criem um feedback associado a uma aula existente e não excluída.
- **FR-002**: O sistema MUST obter a autoria do feedback a partir do usuário autenticado e MUST NOT aceitar a autoria como campo necessário do pedido de criação.
- **FR-003**: O sistema MUST permitir listar os feedbacks ativos associados a uma aula.
- **FR-004**: O sistema MUST permitir consultar um feedback ativo por identificador.
- **FR-005**: O sistema MUST permitir que o autor atualize o texto do próprio feedback, alterando somente os campos permitidos.
- **FR-006**: O sistema MUST impedir que um usuário atualize ou remova o feedback pertencente a outro usuário.
- **FR-007**: O sistema MUST remover feedbacks de forma lógica, preservando o registro para fins de integridade e histórico interno.
- **FR-008**: O sistema MUST excluir feedbacks removidos logicamente das consultas normais, incluindo a listagem da aula e a consulta da própria aula.
- **FR-009**: O sistema MUST incluir os feedbacks ativos de uma aula no conteúdo retornado ao consultar essa aula.
- **FR-010**: O sistema MUST validar a existência e o estado ativo da aula antes de criar ou listar feedbacks associados a ela.
- **FR-011**: O sistema MUST rejeitar pedidos sem autenticação válida nas operações que exigem usuário autenticado.
- **FR-012**: O sistema MUST rejeitar dados inválidos com mensagens compreensíveis e não deve persistir alterações parciais.
- **FR-013**: Os contratos apresentados aos clientes MUST usar nomes de negócio dos campos e MUST NOT expor nomes físicos de colunas de armazenamento.
- **FR-014**: O sistema MUST tratar o feedback como entidade final na composição da resposta, sem exigir entidades filhas próprias.
- **FR-015**: A consulta de uma aula com vários feedbacks MUST evitar consultas individuais desnecessárias por feedback.

### Key Entities

- **Feedback**: contribuição textual de um usuário sobre uma aula, com identificador, texto, autoria, aula associada, datas de criação e atualização e estado de exclusão lógica.
- **Lesson**: aula à qual os feedbacks pertencem; uma aula pode possuir vários feedbacks ativos.
- **User**: usuário autenticado que cria e administra os próprios feedbacks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das operações válidas de criação associam o feedback à aula informada e ao usuário autenticado, sem depender de autoria enviada pelo cliente.
- **SC-002**: 100% dos feedbacks removidos logicamente deixam de aparecer nas consultas normais imediatamente após a remoção.
- **SC-003**: 100% das tentativas cobertas de alteração ou remoção de feedback de outro usuário são recusadas sem modificar o conteúdo original.
- **SC-004**: Usuários conseguem concluir criação, consulta, atualização e remoção de um feedback em até 4 interações válidas por operação, sem fornecer campos internos ou de controle.
- **SC-005**: Em testes com uma aula contendo pelo menos 50 feedbacks, a consulta retorna a coleção completa sem executar uma consulta individual para cada feedback.
- **SC-006**: Todos os cenários de aceite das três jornadas prioritárias são verificáveis por testes automatizados e passam antes da liberação da funcionalidade.

## Assumptions

- O mecanismo existente de autenticação já identifica o usuário atual e pode ser reutilizado.
- A entidade de aula já existe e mantém seu próprio ciclo de vida, incluindo o estado de exclusão lógica.
- A política existente de erros da aplicação será usada para representar validação, inexistência e falta de autorização.
- A primeira versão permite apenas texto no feedback; edição de autoria, aula, datas ou estado de exclusão está fora do escopo.
- O escopo não inclui CRUD adicional de usuários, aulas ou outras entidades.
- A composição de feedbacks deve respeitar os limites de acesso já aplicados à consulta de aulas.
