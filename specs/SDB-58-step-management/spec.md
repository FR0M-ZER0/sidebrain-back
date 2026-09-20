# Feature Specification: Gerenciamento de Etapas

**Feature Branch**: `SDB-58-step-management`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "SDB-58 — Implementar o gerenciamento das etapas (Step), permitindo criar, listar, consultar, atualizar e remover etapas vinculadas a um Track, respeitando a propriedade do usuário autenticado e carregando a hierarquia de conteúdo."

## Clarifications

### Session 2026-09-19

- Q: Ao consultar uma etapa, conteúdos filhos marcados como excluídos logicamente devem ser omitidos da árvore retornada? → A: Omitir todos os filhos excluídos logicamente.

## User Scenarios & Testing

### User Story 1 - Criar uma etapa em uma trilha própria (Priority: P1)

Como usuário autenticado, quero criar uma etapa dentro de uma trilha que me pertence, para organizar o conteúdo do meu percurso de aprendizagem.

**Why this priority**: A criação estabelece a unidade de conteúdo que será consultada e mantida pelos demais fluxos.

**Independent Test**: Com uma trilha ativa do usuário, enviar nível e título válidos e verificar que a etapa é criada nessa trilha, sem aceitar uma trilha diferente informada no corpo.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado e uma trilha ativa pertencente a ele, **When** solicita `POST /tracks/{track_id}/steps` com `level` e `title` válidos, **Then** o sistema cria a etapa na trilha indicada pela URL e retorna a etapa criada.
2. **Given** um usuário autenticado, **When** envia um nível fora de `beginner`, `intermediate`, `advanced` ou `pro`, **Then** o sistema rejeita a solicitação com erro de validação e não cria a etapa.
3. **Given** um usuário autenticado, **When** envia uma etapa sem título ou com título inválido, **Then** o sistema rejeita a solicitação com erro de validação e não cria a etapa.
4. **Given** uma trilha inexistente, excluída ou pertencente a outro usuário, **When** solicita a criação de uma etapa, **Then** o sistema rejeita a operação sem revelar dados da trilha.

### User Story 2 - Consultar etapas e seu conteúdo (Priority: P1)

Como usuário autenticado, quero listar ou consultar uma etapa da minha trilha com seu conteúdo relacionado, para visualizar a estrutura completa de aprendizagem.

**Why this priority**: A consulta é o principal meio de uso da etapa e precisa apresentar sua árvore de conteúdo sem acesso cruzado entre usuários.

**Independent Test**: Preparar uma trilha com etapas, lições, quizzes, respostas, feedbacks, arquivos, missões e progressos; consultar a listagem e uma etapa individual e comparar a hierarquia retornada com os relacionamentos existentes.

**Acceptance Scenarios**:

1. **Given** uma trilha ativa com etapas ativas do usuário autenticado, **When** solicita `GET /tracks/{track_id}/steps`, **Then** o sistema retorna as etapas ativas da trilha e, para cada uma, suas lições, quizzes com respostas, feedbacks, arquivos, missões e progressos.
2. **Given** uma etapa ativa pertencente à trilha do usuário autenticado, **When** solicita `GET /tracks/{track_id}/steps/{step_id}`, **Then** o sistema retorna a etapa e toda a hierarquia de filhos prevista para a leitura.
3. **Given** uma trilha sem etapas ativas, **When** o usuário solicita sua listagem, **Then** o sistema retorna uma coleção vazia no formato de listagem vigente, sem incluir etapas excluídas.
4. **Given** uma trilha ou etapa inexistente, excluída, fora da trilha indicada ou pertencente a outro usuário, **When** o usuário consulta o recurso, **Then** o sistema retorna recurso não encontrado sem expor dados protegidos.

### User Story 3 - Atualizar e remover uma etapa (Priority: P1)

Como usuário autenticado, quero atualizar o nível e o título de uma etapa própria ou removê-la logicamente, para manter a trilha correta sem apagar fisicamente o histórico.

**Why this priority**: A manutenção completa o ciclo de vida da etapa e preserva a consistência dos dados da trilha.

**Independent Test**: Criar uma etapa, atualizar seus campos editáveis com valores válidos, verificar a resposta atualizada, removê-la e confirmar que ela não aparece nas consultas normais.

**Acceptance Scenarios**:

1. **Given** uma etapa ativa da trilha do usuário autenticado, **When** envia `PUT /tracks/{track_id}/steps/{step_id}` com `level` e `title` válidos, **Then** o sistema atualiza os dois campos editáveis e retorna a etapa atualizada.
2. **Given** uma etapa ativa, **When** o usuário tenta alterar identificador, trilha, status, timestamps ou dados de exclusão lógica, **Then** o sistema rejeita ou ignora esses campos e preserva o controle do sistema sobre eles.
3. **Given** uma etapa ativa da trilha do usuário autenticado, **When** solicita `DELETE /tracks/{track_id}/steps/{step_id}`, **Then** o sistema registra a exclusão lógica e seu timestamp e responde sem conteúdo.
4. **Given** uma etapa excluída, **When** o usuário tenta consultá-la, atualizá-la ou removê-la novamente, **Then** o sistema retorna recurso não encontrado e não altera seus dados.
5. **Given** uma etapa de outro usuário, **When** o usuário tenta atualizá-la ou removê-la, **Then** o sistema rejeita a operação sem expor informações do proprietário.

### Edge Cases

- Identificadores malformados devem resultar em erro de validação sem alterar dados.
- O `track_id` deve ser sempre obtido da URL; o corpo não deve permitir escolher ou sobrescrever a trilha.
- O nível deve aceitar somente `beginner`, `intermediate`, `advanced` ou `pro`; o status retornado deve respeitar `idle`, `in_progress` ou `done`.
- O status da etapa é gerenciado pelo sistema e não pode ser alterado por criação ou atualização nesta feature.
- Etapas excluídas logicamente não devem aparecer em listagens ou consultas normais.
- A exclusão lógica da etapa não deve excluir nem marcar automaticamente suas lições, missões ou demais filhos como excluídos.
- A consulta de uma etapa deve manter a hierarquia correta, sem duplicações, omissões ou consultas individuais evitáveis por filho.
- A ausência de autenticação deve ser rejeitada antes de qualquer operação protegida.
- Falhas de persistência devem retornar erro padronizado sem revelar detalhes internos.

## Requirements

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um usuário autenticado crie uma etapa vinculada à trilha indicada na URL.
- **FR-002**: O sistema MUST validar que a trilha existe, está disponível e pertence ao usuário autenticado antes de criar, consultar, atualizar ou remover uma etapa.
- **FR-003**: O sistema MUST aceitar na criação apenas `level` e `title` como dados de negócio, exigindo título e nível válido.
- **FR-004**: O sistema MUST restringir `level` aos valores `beginner`, `intermediate`, `advanced` e `pro`.
- **FR-005**: O sistema MUST permitir a listagem de etapas ativas por trilha, seguindo o formato de listagem e paginação adotado pela API quando aplicável.
- **FR-006**: O sistema MUST permitir a consulta de uma etapa por identificador somente quando ela pertencer à trilha indicada e ao usuário autenticado.
- **FR-007**: O sistema MUST incluir nas respostas de leitura as lições e missões da etapa.
- **FR-008**: O sistema MUST incluir, para cada lição retornada, seus arquivos, feedbacks, quizzes e respostas dos quizzes.
- **FR-009**: O sistema MUST incluir, para cada missão retornada, seus registros de progresso.
- **FR-010**: O sistema MUST carregar os filhos da etapa em operações agrupadas, evitando uma consulta individual para cada filho quando houver possibilidade de carregamento em lote.
- **FR-011**: O sistema MUST permitir a atualização de `level` e `title` de uma etapa ativa, usando atualização completa para o contrato `PUT`.
- **FR-012**: O sistema MUST impedir a alteração de identificadores, vínculo da trilha, status, timestamps e informações de exclusão lógica por meio dos requests de criação e atualização.
- **FR-013**: O sistema MUST permitir a exclusão lógica de uma etapa, preservando seu registro físico e registrando o timestamp da exclusão.
- **FR-014**: O sistema MUST excluir etapas marcadas como excluídas das listagens e consultas normais.
- **FR-015**: O sistema MUST manter inalterados os registros filhos quando uma etapa for excluída logicamente, sem assumir exclusão lógica em cascata.
- **FR-016**: O sistema MUST omitir da árvore de leitura todos os conteúdos filhos marcados como excluídos logicamente.
- **FR-017**: O sistema MUST retornar `201` na criação, `200` nas consultas e atualização, `204` na remoção e erros padronizados para validação, autenticação, autorização e recurso não encontrado conforme o contrato vigente.
- **FR-018**: O sistema MUST ocultar dos schemas públicos os nomes físicos das colunas, campos internos e dados de auditoria ou exclusão lógica não previstos no contrato.
- **FR-019**: O sistema MUST impedir que um usuário acesse, atualize ou remova etapas vinculadas a trilhas de outro usuário sem revelar dados dessas etapas.
- **FR-020**: O sistema MUST limitar esta feature ao CRUD de etapas e à composição de respostas de leitura, sem criar CRUD adicional para lições, missões, quizzes, respostas, feedbacks, arquivos ou progressos.
- **FR-021**: O sistema MUST respeitar os erros e respostas em formato Problem Details adotados pela API.

### Key Entities

- **Etapa (Step)**: Unidade de aprendizagem pertencente a uma trilha, com identificador, nível, título, status e estado de exclusão lógica.
- **Trilha (Track)**: Percurso de aprendizagem pertencente a um usuário e agregado pai das etapas.
- **Lição (Lesson)**: Conteúdo de uma etapa que pode conter arquivos, feedbacks, quizzes e respostas.
- **Missão (Mission)**: Atividade de uma etapa que pode conter registros de progresso.
- **Usuário**: Proprietário autenticado da trilha e, indiretamente, das etapas que ela contém.
- **Conteúdo relacionado**: Arquivos, feedbacks, quizzes, respostas e progressos apresentados somente como parte da leitura da etapa.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Usuários autenticados conseguem criar, consultar, atualizar e remover logicamente uma etapa própria em até 4 operações válidas, sem intervenção manual.
- **SC-002**: 100% das etapas retornadas em listagens e consultas normais pertencem à trilha solicitada, pertencem ao usuário autenticado e não estão excluídas logicamente.
- **SC-003**: 100% das respostas de leitura de etapas apresentam a hierarquia de lições, missões e respectivos filhos no nível correto, sem expor nomes físicos ou campos internos.
- **SC-004**: Nenhuma consulta de etapa executa uma operação individual por filho quando o carregamento em lote for possível; o número de operações não cresce linearmente com a quantidade de filhos retornados.
- **SC-005**: 100% das tentativas de acesso, alteração ou remoção de etapas inexistentes, excluídas ou pertencentes a outro usuário recebem erro apropriado sem exposição de dados.
- **SC-006**: 100% das etapas removidas logicamente deixam de aparecer nas consultas normais, enquanto seus registros filhos permanecem inalterados por esta feature.
- **SC-007**: Pelo menos 95% das operações válidas de gerenciamento de etapas são concluídas em até 2 segundos sob a carga esperada do produto.
- **SC-008**: Pelo menos 90% dos usuários de teste concluem o fluxo de criação e manutenção de uma etapa na primeira tentativa.

## Assumptions

- O usuário já está autenticado e a aplicação existente fornece sua identidade para autorização.
- O padrão de identificadores, paginação, validação de títulos e Problem Details seguirá os contratos vigentes do projeto.
- O `PUT` representa atualização completa dos campos editáveis da etapa: `level` e `title` são obrigatórios no request; alterações parciais, se necessárias, deverão ser tratadas por contrato específico futuro.
- O status da etapa é controlado pelo sistema e apenas retornado nas respostas desta feature.
- A ordenação das etapas seguirá a ordem natural resultante da consulta existente; não será criado um campo `position` ou outro critério persistente inexistente no modelo.
- As entidades filhas já existentes serão somente leitura neste escopo e não ganharão endpoints CRUD adicionais.
- A exclusão lógica da etapa não altera automaticamente o estado de lições, missões ou demais filhos.
- A primeira versão pode retornar uma árvore de conteúdo extensa; os limites e parâmetros de paginação seguirão o padrão já adotado pela API sem modificar a hierarquia funcional.