# Feature Specification: Gerenciamento de Trilhas

**Feature Branch**: `SDB-49-track-management`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "Criar endpoint para gerenciamento da trilha, com CRUD da trilha do usuário autenticado e leitura da hierarquia de conteúdo"

## User Scenarios & Testing

### User Story 1 - Criar uma trilha de aprendizagem (Priority: P1)

Como usuário autenticado, quero criar uma trilha informando seu título e, opcionalmente, uma descrição, para organizar meu percurso de aprendizagem.

**Why this priority**: A criação é a capacidade central do gerenciamento de trilhas e habilita todos os demais fluxos de consulta e manutenção.

**Independent Test**: Enviar dados válidos de uma nova trilha para um usuário autenticado e verificar que ela é criada, vinculada ao usuário e retornada com seus dados identificadores e de auditoria.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado e um título válido, **When** ele solicita a criação de uma trilha sem descrição, **Then** o sistema cria a trilha vinculada ao usuário e retorna os dados da nova trilha.
2. **Given** um usuário autenticado e título e descrição válidos, **When** ele solicita a criação de uma trilha, **Then** o sistema persiste ambos os campos e retorna a trilha criada.
3. **Given** um usuário autenticado, **When** ele solicita a criação sem título ou com título vazio, **Then** o sistema rejeita a solicitação com erro de validação e não cria a trilha.

### User Story 2 - Consultar trilhas próprias (Priority: P1)

Como usuário autenticado, quero listar minhas trilhas e consultar uma trilha específica com suas etapas e conteúdos relacionados, para acompanhar e selecionar meu percurso de aprendizagem.

**Why this priority**: A consulta é necessária para que o usuário consiga visualizar as trilhas que criou e operar sobre uma trilha existente.

**Independent Test**: Criar trilhas para dois usuários com etapas e conteúdos relacionados, consultar a listagem e uma trilha por identificador, e verificar que cada usuário visualiza apenas suas próprias trilhas ativas com a hierarquia esperada.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado com trilhas ativas, **When** ele solicita a listagem, **Then** o sistema retorna somente suas trilhas ativas em formato paginado, incluindo total de itens e páginas, e cada trilha inclui suas etapas e os conteúdos relacionados.
2. **Given** um usuário autenticado sem trilhas ativas, **When** ele solicita a listagem, **Then** o sistema retorna uma coleção vazia com metadados de paginação consistentes.
3. **Given** uma trilha ativa pertencente ao usuário autenticado, **When** ele consulta seu identificador, **Then** o sistema retorna os dados da trilha com suas etapas, lições, missões e respectivos recursos filhos.
4. **Given** uma trilha inexistente, excluída ou pertencente a outro usuário, **When** o usuário consulta seu identificador, **Then** o sistema retorna erro de recurso não encontrado sem revelar os dados da trilha.
5. **Given** parâmetros de página inválidos, **When** o usuário solicita a listagem, **Then** o sistema rejeita a solicitação com erro de validação.

### User Story 3 - Atualizar e excluir uma trilha (Priority: P1)

Como usuário autenticado, quero atualizar os dados de uma trilha ou excluí-la, para manter meu percurso de aprendizagem correto e organizado.

**Why this priority**: A manutenção evita dados desatualizados e completa o gerenciamento do ciclo de vida das trilhas.

**Independent Test**: Criar uma trilha, alterar título e descrição, verificar a atualização e solicitar sua exclusão; então confirmar que ela não aparece mais nas consultas de trilhas ativas.

**Acceptance Scenarios**:

1. **Given** uma trilha ativa pertencente ao usuário autenticado, **When** ele atualiza título e/ou descrição com valores válidos, **Then** o sistema salva as alterações e retorna os dados atualizados.
2. **Given** uma trilha ativa pertencente ao usuário autenticado, **When** ele tenta atualizá-la com título vazio ou inválido, **Then** o sistema rejeita a solicitação com erro de validação e preserva os dados anteriores.
3. **Given** uma trilha ativa pertencente ao usuário autenticado, **When** ele solicita sua exclusão, **Then** o sistema a marca como excluída, registra o momento da exclusão e retorna confirmação da operação.
4. **Given** uma trilha excluída, inexistente ou pertencente a outro usuário, **When** o usuário tenta atualizá-la ou excluí-la, **Then** o sistema retorna erro de recurso não encontrado.

### Edge Cases

- Títulos com o tamanho máximo permitido devem ser aceitos; títulos acima desse limite devem ser rejeitados sem persistência parcial.
- Descrições ausentes devem ser aceitas; descrições enviadas devem respeitar a validação de conteúdo e tamanho aplicável.
- Uma trilha excluída não deve aparecer na listagem nem ser retornada em consultas individuais posteriores.
- Identificadores malformados devem resultar em erro de validação, sem consulta ou alteração de dados.
- As operações sobre uma trilha devem respeitar o vínculo com o usuário autenticado, sem permitir acesso cruzado entre usuários.
- Falhas de persistência devem retornar erro padronizado e não expor detalhes internos.
- A leitura de uma trilha com múltiplas relações deve retornar cada filho no nível correto da hierarquia, sem duplicações ou omissões causadas pelo carregamento relacionado.
- O tempo e a quantidade de consultas devem permanecer estáveis conforme aumentam as relações carregadas de uma trilha, evitando uma consulta adicional por item filho.

## Requirements

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um usuário autenticado crie uma trilha informando um título obrigatório e uma descrição opcional.
- **FR-002**: O sistema MUST vincular cada trilha criada ao usuário autenticado que realizou a operação.
- **FR-003**: O sistema MUST validar campos obrigatórios, identificadores, limites de tamanho e parâmetros de paginação antes de executar operações.
- **FR-004**: O sistema MUST permitir a consulta de uma trilha por identificador somente quando ela pertencer ao usuário autenticado e estiver ativa.
- **FR-005**: O sistema MUST permitir a listagem paginada das trilhas ativas do usuário autenticado, retornando dados, página atual, tamanho da página, total de itens e total de páginas.
- **FR-005a**: O sistema MUST incluir, nas respostas de leitura de trilhas, suas etapas e, para cada etapa, suas lições e missões.
- **FR-005b**: O sistema MUST incluir, para cada lição, seus arquivos, feedbacks, quizzes e respostas dos quizzes.
- **FR-005c**: O sistema MUST incluir, para cada missão, o progresso associado.
- **FR-005d**: O sistema MUST carregar a hierarquia de conteúdo sem executar uma consulta adicional para cada item filho retornado.
- **FR-006**: O sistema MUST permitir a atualização do título e da descrição de uma trilha ativa pertencente ao usuário autenticado.
- **FR-007**: O sistema MUST rejeitar atualizações que deixem o título ausente, vazio ou fora dos limites permitidos, preservando os dados válidos anteriores.
- **FR-008**: O sistema MUST permitir a exclusão de uma trilha ativa pertencente ao usuário autenticado sem apagar fisicamente seu registro.
- **FR-009**: O sistema MUST registrar a data e hora da exclusão lógica quando uma trilha for excluída.
- **FR-010**: O sistema MUST excluir trilhas marcadas como excluídas das listagens e consultas individuais destinadas a trilhas ativas.
- **FR-011**: O sistema MUST retornar respostas de erro padronizadas para validação, recurso não encontrado e falhas de processamento, sem expor dados de outros usuários ou detalhes internos.
- **FR-012**: O sistema MUST manter compatibilidade com a versão vigente dos recursos de trilha e disponibilizar as operações sob o agrupamento de trilhas da API.
- **FR-013**: O sistema MUST obter a propriedade da trilha a partir do contexto de autenticação na criação e não aceitar `userId` como dado de entrada.
- **FR-014**: O sistema MUST excluir dos requests de criação e atualização identificadores internos, usuário proprietário, timestamps e campos de exclusão lógica.

### Key Entities

- **Trilha**: Percurso de aprendizagem criado por um usuário, identificado por um identificador único, com título obrigatório, descrição opcional, datas de criação e atualização e estado de exclusão.
- **Etapa**: Unidade de uma trilha que pode conter lições e missões.
- **Lição**: Conteúdo de uma etapa que pode conter arquivos, feedbacks, quizzes e respostas associadas aos quizzes.
- **Missão**: Atividade de uma etapa que pode conter registros de progresso do usuário.
- **Usuário**: Pessoa autenticada proprietária das trilhas; uma trilha só pode ser consultada ou alterada pelo usuário ao qual está vinculada.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Usuários autenticados conseguem criar, consultar, atualizar e excluir uma trilha em até 4 operações válidas, sem necessidade de intervenção manual.
- **SC-002**: 100% das trilhas exibidas na listagem pertencem ao usuário autenticado e estão ativas.
- **SC-002a**: 100% das respostas de leitura exibem a hierarquia de etapas e recursos filhos no nível correspondente ao relacionamento da trilha.
- **SC-002b**: Nenhuma leitura de trilha executa consultas proporcionais ao número de itens filhos individualmente; o carregamento permanece em operações agrupadas para toda a árvore retornada.
- **SC-003**: 100% das tentativas de acesso, alteração ou exclusão de trilhas inexistentes, excluídas ou de outro usuário recebem uma resposta de recurso não encontrado, sem exposição de dados.
- **SC-004**: 100% das listagens retornam metadados de paginação consistentes com a quantidade de trilhas ativas disponíveis.
- **SC-005**: Pelo menos 95% das operações válidas de gerenciamento de trilhas são concluídas em até 2 segundos sob a carga esperada do produto.
- **SC-006**: Pelo menos 90% dos usuários de teste concluem o fluxo de criação e manutenção de uma trilha na primeira tentativa.

## Assumptions

- O usuário já está autenticado e sua identidade está disponível para as operações protegidas.
- A primeira versão gerencia os dados básicos da trilha; a inclusão, ordenação ou manutenção de etapas e demais filhos pertence a outro escopo.
- Os filhos são somente leitura neste recurso: eles são compostos nas respostas, mas não possuem CRUD por meio dos endpoints de trilha.
- A exclusão de trilhas é lógica para preservar a integridade histórica e permitir o comportamento de ocultação definido nesta especificação.
- O padrão de paginação existente do produto será usado, com valores padrão de página e tamanho definidos pelo contrato vigente da API.
- Os erros seguirão o formato de Problem Details definido nas convenções do projeto.
- A disponibilidade e o desempenho dependem do ambiente operacional esperado para o produto, sem requisito de carga concorrente adicional nesta feature.
