# Feature Specification: Gerenciamento de Missões

**Feature Branch**: `SDB-86-mission-crud`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "SDB-86 — Criar endpoints para gerenciar missões"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerenciar missões de um step (Priority: P1)

Como usuário proprietário de um track, quero criar, consultar, listar, atualizar e remover logicamente as missões de seus steps para acompanhar e manter os objetivos de aprendizagem.

**Why this priority**: O gerenciamento do ciclo de vida da missão é o valor central da tarefa e habilita os demais fluxos que dependem de missões.

**Independent Test**: Com um track e um step pertencentes ao usuário, é possível executar as operações de criação, listagem, consulta, atualização e exclusão lógica e verificar os estados resultantes sem depender de funcionalidades de progresso.

**Acceptance Scenarios**:

1. **Given** um step existente, ativo e pertencente ao usuário autenticado, **When** o usuário envia uma missão válida para esse step, **Then** a missão é criada e retornada com seu identificador, o step associado e seus dados sem expor nomes físicos de persistência.
2. **Given** um step com missões ativas, **When** o usuário solicita a listagem, **Then** recebe apenas as missões não excluídas, em ordem paginada, com os dados de progresso desse usuário quando existirem.
3. **Given** uma missão ativa pertencente a um step do usuário, **When** o usuário a consulta ou atualiza com dados válidos, **Then** recebe a missão atualizada e seus progressos do usuário autenticado.
4. **Given** uma missão ativa pertencente a um step do usuário, **When** o usuário solicita sua exclusão, **Then** a operação retorna sucesso sem conteúdo e a missão deixa de aparecer nas consultas futuras.

### User Story 2 - Preservar a hierarquia de aprendizagem (Priority: P2)

Como consumidor da visão de um step ou track, quero receber suas missões e os progressos associados ao usuário atual para visualizar a jornada completa de aprendizagem em uma única resposta coerente.

**Why this priority**: A missão é um recurso filho de Step; perder a composição Step → Mission → MissionProgress quebraria respostas já consumidas pela aplicação.

**Independent Test**: Consultar um step e um track com missões e progresso previamente registrados e verificar que a hierarquia contém as missões ativas e somente os progressos do usuário autenticado.

**Acceptance Scenarios**:

1. **Given** um track com steps que possuem missões ativas, **When** o usuário consulta o track, **Then** cada step inclui suas missões e cada missão inclui os progressos do usuário autenticado.
2. **Given** uma missão com progressos de usuários diferentes, **When** o usuário autenticado consulta o step ou a missão, **Then** somente seus próprios progressos são retornados.
3. **Given** uma missão excluída logicamente, **When** o usuário consulta o step ou track, **Then** essa missão não é incluída na composição hierárquica.

### User Story 3 - Proteger o acesso às missões (Priority: P1)

Como usuário da plataforma, quero que missões de steps pertencentes a outras pessoas ou a recursos excluídos não sejam reveladas nem alteradas.

**Why this priority**: O vínculo entre usuário, track, step e missão é uma regra de autorização e privacidade, não apenas uma regra de filtragem.

**Independent Test**: Tentar criar, listar, consultar, atualizar e excluir missões usando um step ou missão de outro usuário, ou de um recurso logicamente excluído, e verificar que todas as tentativas produzem o mesmo resultado de recurso não encontrado.

**Acceptance Scenarios**:

1. **Given** um step inexistente, excluído ou pertencente a outro usuário, **When** o usuário tenta criar ou listar missões, **Then** recebe `404` sem detalhes que revelem qual condição falhou.
2. **Given** uma missão inexistente, excluída ou vinculada a um track de outro usuário, **When** o usuário tenta consultá-la, atualizá-la ou excluí-la, **Then** recebe `404`.
3. **Given** um payload com campos inválidos, **When** o usuário tenta criar ou atualizar uma missão autorizada, **Then** recebe `422` com erros de validação compreensíveis e nenhum dado parcial é persistido.

### Edge Cases

- Uma missão não pode ser criada sem um step existente, ativo e pertencente ao usuário autenticado.
- O identificador do step vem do contexto da URL na criação e não pode ser alterado durante a atualização.
- Título vazio ou apenas com espaços, dificuldade desconhecida, critério desconhecido, recompensa negativa ou valor de critério não positivo devem ser rejeitados.
- A atualização deve rejeitar um payload vazio; campos omitidos preservam os valores atuais.
- Uma missão já excluída logicamente não pode ser listada, consultada, atualizada ou excluída novamente.
- A exclusão lógica deve preservar a missão e seus registros de progresso para histórico, sem exclusão física em cascata.
- Listagens sem resultados devem retornar uma página válida com coleção vazia e metadados de paginação consistentes.
- Paginação deve usar `page=1` e `page_size=20` por padrão e rejeitar valores fora dos limites definidos pelo contrato.
- Uma missão sem progresso do usuário deve retornar `missionProgresses` vazio.
- O carregamento de progressos em uma listagem não deve gerar uma consulta independente para cada missão.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar operações para criar, listar, consultar por identificador, atualizar e excluir logicamente uma Mission.
- **FR-002**: O sistema MUST tratar Mission como recurso filho de Step na criação e na listagem, usando o identificador do Step no contexto da URL.
- **FR-003**: O sistema MUST validar que o Step existe, não está excluído e pertence ao Track do usuário autenticado antes de permitir qualquer operação contextual sobre suas Missions.
- **FR-004**: O sistema MUST retornar `404` para inexistência, exclusão lógica ou ownership incompatível de Step ou Mission, sem diferenciar esses casos na resposta pública.
- **FR-005**: O sistema MUST aceitar na criação os campos título, dificuldade, recompensa de XP, critério e valor do critério, aplicando as regras de obrigatoriedade e validação definidas no contrato.
- **FR-006**: O sistema MUST permitir atualização parcial dos dados da Mission, exigindo pelo menos um campo e preservando campos omitidos.
- **FR-007**: O sistema MUST impedir que a atualização altere o Step associado à Mission.
- **FR-008**: O sistema MUST executar DELETE como exclusão lógica, mantendo o registro da Mission e preenchendo sua marca temporal de exclusão.
- **FR-009**: O sistema MUST excluir Missions logicamente removidas de todas as consultas e listagens públicas.
- **FR-010**: O sistema MUST aplicar paginação às listagens de Mission, com valores padrão `page=1`, `page_size=20` e limite máximo de 100 itens por página.
- **FR-011**: O sistema MUST retornar respostas sem expor nomes físicos de colunas ou identificadores internos de relacionamento.
- **FR-012**: O sistema MUST representar uma Mission com identificador, Step associado, título, dificuldade, recompensa de XP, critério, valor do critério e coleção `missionProgresses`.
- **FR-013**: O sistema MUST incluir na Mission somente os MissionProgresses pertencentes ao usuário autenticado.
- **FR-014**: O sistema MUST manter a composição Step → Mission[] → MissionProgress[] nas respostas de Step e Track, omitindo Missions excluídas.
- **FR-015**: O sistema MUST carregar os progressos necessários para listagens de forma agrupada, sem comportamento de uma consulta adicional por Mission.
- **FR-016**: O escopo desta feature MUST excluir operações de criação, atualização, mudança de status, pontuação ou exclusão de MissionProgress.
- **FR-017**: O sistema MUST retornar respostas de erro compatíveis com o contrato público existente, incluindo `404` para recurso inacessível e `422` para payload inválido.

### Key Entities

- **Mission**: objetivo associado obrigatoriamente a um Step; possui título, dificuldade, recompensa de XP, critério, valor do critério e marca de exclusão lógica.
- **Step**: etapa de um Track que agrupa Missions e determina o contexto hierárquico da missão.
- **Track**: jornada pertencente a um usuário; define o limite de autorização para acesso às Missions de seus Steps.
- **MissionProgress**: registro de progresso de um usuário em uma Mission, exposto apenas como composição de leitura nesta feature.
- **Usuário autenticado**: identidade que define a autorização de acesso à cadeia Track → Step → Mission e o filtro dos progressos retornados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários autorizados conseguem concluir o fluxo completo de criação, consulta, atualização e exclusão lógica de uma Mission em até 2 minutos em condições normais.
- **SC-002**: 100% das operações de Mission para Steps inexistentes, excluídos ou pertencentes a outro usuário retornam `404` e não revelam dados do recurso protegido.
- **SC-003**: 100% das listagens e consultas de Mission omitem Missions com exclusão lógica e exibem somente progressos do usuário autenticado.
- **SC-004**: Pelo menos 95% das listagens paginadas com até 100 Missions retornam seus dados e progressos em até 1 segundo, sem crescimento linear de consultas por quantidade de Missions.
- **SC-005**: 100% das respostas públicas de Mission usam nomes semânticos do contrato e não expõem nomes físicos de colunas ou chaves de relacionamento internas.
- **SC-006**: A consulta de um Step ou Track mantém a composição completa de Missions ativas e seus progressos do usuário em 100% dos cenários cobertos pelos testes de contrato.
- **SC-007**: Pelo menos 90% dos usuários que executarem o fluxo principal conseguem criar e atualizar uma Mission na primeira tentativa com payload válido.

## Assumptions

- O usuário autenticado já é disponibilizado pelo mecanismo de autenticação existente e seu identificador é a fonte de autorização.
- Os modelos, tabelas e enumerações de Step, Track e MissionProgress existentes serão reutilizados; esta feature não altera a regra de evolução de progresso ou XP.
- O formato de paginação e de erros já adotado pelo projeto permanece o contrato público para as novas operações.
- O cliente utiliza identificadores UUID e os nomes semânticos em camelCase definidos pelos contratos existentes.
- A remoção lógica é suficiente para retenção de histórico; políticas adicionais de retenção de dados estão fora do escopo.
- A feature não inclui alterações de interface visual, notificações ou recálculo automático de progresso.
