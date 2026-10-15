# Feature Specification: Gerenciamento de Badges

**Feature Branch**: `SDB-87-badge-management`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "SDB-87 - Criar endpoints para gerenciar badges"

## Clarifications

### Session 2026-10-07

- Q: Quais critérios devem ser aceitos para um badge? → A: `xp_gained`, `tracks_completed`, `lessons_completed`, `right_answers`, `day_streak`, `tracks_created` e `missions_completed`.
- Q: Dois badges ativos podem ter o mesmo nome no catálogo? → A: Nomes únicos entre badges ativos; badges removidos não bloqueiam reutilização.
- Q: A unicidade do nome deve ignorar maiúsculas, minúsculas e espaços nas extremidades? → A: Comparação sem distinção de maiúsculas/minúsculas após remover espaços nas extremidades, preservando no response o nome normalizado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar um badge no catalogo (Priority: P1)

Como usuario autenticado, quero cadastrar um badge no catalogo global para disponibilizar uma conquista com nome, descricao, raridade e criterio de elegibilidade.

**Why this priority**: A criacao estabelece os badges que poderao ser exibidos e acompanhados pelos usuarios.

**Independent Test**: Enviar dados validos para a criacao e verificar que o badge e retornado com seus dados de negocio e uma colecao de progressos vazia.

**Acceptance Scenarios**:

1. **Given** um usuario autenticado e dados validos, **When** ele cria um badge, **Then** o sistema persiste o badge no catalogo e retorna seus dados sem expor campos internos.
2. **Given** um usuario nao autenticado, **When** ele tenta criar um badge, **Then** o sistema recusa a operacao sem persistir dados.
3. **Given** dados ausentes, vazios ou invalidos, **When** o usuario tenta criar um badge, **Then** o sistema informa os campos invalidos e nao cria um registro parcial.

### User Story 2 - Consultar badges e progresso pessoal (Priority: P1)

Como usuario autenticado, quero listar o catalogo ou consultar um badge especifico para conhecer suas regras e meu progresso naquela conquista.

**Why this priority**: A consulta permite que o catalogo e o estado individual de cada conquista sejam consumidos pelos produtos clientes.

**Independent Test**: Preparar badges ativos, um badge removido e progressos de varios usuarios; consultar a lista e um badge especifico e verificar que somente o progresso do usuario autenticado e retornado.

**Acceptance Scenarios**:

1. **Given** badges ativos e removidos, **When** o usuario consulta o catalogo paginado, **Then** o sistema retorna somente os ativos com metadados de pagina e os progressos do usuario autenticado.
2. **Given** um badge ativo com progresso do usuario autenticado, **When** ele consulta o badge por identificador, **Then** o sistema retorna o badge e o status do seu progresso.
3. **Given** um badge ativo sem progresso do usuario autenticado, **When** ele consulta o badge, **Then** o sistema retorna uma colecao de progressos vazia.
4. **Given** um badge inexistente ou removido, **When** o usuario tenta consulta-lo, **Then** o sistema retorna o mesmo resultado de recurso nao encontrado.
5. **Given** um usuario nao autenticado, **When** ele tenta listar ou consultar badges, **Then** o sistema recusa a operacao.

### User Story 3 - Atualizar ou remover um badge (Priority: P2)

Como usuario autenticado, quero atualizar os dados de um badge ou remove-lo logicamente para manter o catalogo correto sem apagar o historico de progresso.

**Why this priority**: A manutencao completa o ciclo de vida do catalogo e preserva dados que podem ser necessarios para historico dos usuarios.

**Independent Test**: Criar um badge com progresso, atualizar seus dados e depois remove-lo; verificar que o badge deixa de aparecer nas consultas e que seu registro e progresso permanecem preservados internamente.

**Acceptance Scenarios**:

1. **Given** um badge ativo e dados validos com pelo menos um campo informado, **When** o usuario o atualiza, **Then** o sistema altera somente os campos enviados e retorna o badge atualizado com o progresso do usuario.
2. **Given** um badge ativo com progresso, **When** o usuario solicita sua remocao, **Then** o sistema conclui a remocao logica sem apagar fisicamente o badge ou seu historico.
3. **Given** um badge removido, **When** o usuario tenta atualiza-lo ou remove-lo novamente, **Then** o sistema retorna recurso nao encontrado e nao altera os dados.
4. **Given** um payload de atualizacao vazio ou invalido, **When** o usuario tenta atualizar um badge, **Then** o sistema rejeita a operacao sem alterar o badge.

### Edge Cases

- Nome ausente, vazio, formado somente por espacos ou com mais de 255 caracteres deve ser rejeitado.
- O nome deve ser unico entre badges ativos, sem impedir a reutilizacao do nome de um badge removido logicamente.
- A comparacao de nomes deve remover espacos nas extremidades e ignorar diferencas entre maiusculas e minusculas; o nome persistido e retornado deve estar normalizado.
- `rarity` deve aceitar somente `common`, `rare`, `epic` ou `legendary`.
- `criteria` deve aceitar somente `xp_gained`, `tracks_completed`, `lessons_completed`, `right_answers`, `day_streak`, `tracks_created` ou `missions_completed`.
- `criteriaValue` deve ser um inteiro maior que zero.
- Descricao pode ser nula; quando fornecida, deve preservar o significado informado pelo usuario.
- A atualizacao deve exigir pelo menos um campo e deve preservar campos omitidos.
- Identificador, datas, estado de exclusao e relacionamentos nao podem ser controlados pelo cliente.
- Um progresso pertencente a outro usuario nao deve aparecer no response do usuario atual.
- Uma pagina acima do total deve retornar uma colecao vazia com metadados consistentes.
- A remocao de um badge com progresso nao deve acionar exclusao fisica em cascata.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que qualquer usuario autenticado crie um badge no catalogo global, sem exigir identificador de recurso pai na URL ou no corpo, e MUST rejeitar nomes normalizados que ja existam em badges ativos.
- **FR-002**: O sistema MUST remover espacos nas extremidades e normalizar o nome antes de persistir ou comparar, validar nome entre 1 e 255 caracteres, exigir nome unico entre badges ativos sem distinguir maiusculas e minusculas, aceitar raridade entre `common`, `rare`, `epic` e `legendary`, criterio entre `xp_gained`, `tracks_completed`, `lessons_completed`, `right_answers`, `day_streak`, `tracks_created` e `missions_completed`, e exigir valor do criterio inteiro maior que zero.
- **FR-003**: O sistema MUST permitir listar badges ativos de forma paginada, usando pagina 1 e tamanho 20 como padroes e aceitando tamanho maximo de 100.
- **FR-004**: O sistema MUST permitir consultar um badge ativo por identificador.
- **FR-005**: As listagens MUST informar dados, pagina atual, tamanho da pagina, total de itens e total de paginas.
- **FR-006**: Consultas de badge MUST incluir somente os progressos associados ao usuario autenticado; badges sem progresso desse usuario MUST retornar uma colecao vazia.
- **FR-007**: O sistema MUST permitir atualizar parcialmente um badge ativo quando pelo menos um campo editavel for enviado, preservando os campos omitidos e rejeitando nome normalizado que conflite com outro badge ativo.
- **FR-008**: O sistema MUST permitir remover logicamente um badge ativo e registrar o momento da remocao, sem excluir fisicamente o registro ou seus progressos.
- **FR-009**: Badges removidos logicamente MUST ser ignorados em listagens, consultas diretas e respostas compostas; inexistencia e remocao logica MUST resultar no mesmo recurso nao encontrado.
- **FR-010**: Todas as operacoes MUST exigir autenticacao valida; qualquer usuario autenticado pode operar enquanto nao houver papeis de acesso definidos.
- **FR-011**: Os contratos publicos MUST usar nomes semanticos de negocio e MUST NOT expor nomes fisicos de colunas, identificadores internos de relacionamento ou campos de exclusao.
- **FR-012**: O escopo MUST limitar-se ao CRUD de Badge e ao carregamento dos progressos existentes para composicao das respostas; a evolucao do status e o CRUD de BadgeProgress ficam fora desta feature.
- **FR-013**: Dados invalidos, identificadores inexistentes e operacoes sobre badges removidos MUST ser rejeitados sem persistir alteracoes parciais.

### Key Entities

- **Badge**: conquista do catalogo global, com nome, descricao opcional, raridade, criterio e valor do criterio, sujeita a remocao logica.
- **BadgeProgress**: progresso de um usuario em um badge, apresentado apenas no contexto do badge e com identificador e status sem expor os vinculos internos.
- **User**: usuario autenticado cujo progresso deve ser selecionado nas consultas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das operacoes validas de criacao, consulta, atualizacao e remocao realizadas por usuarios autenticados produzem os resultados previstos nos cenarios de aceite.
- **SC-002**: 100% dos badges removidos logicamente deixam de aparecer imediatamente em listagens e consultas diretas, sem perda do registro ou dos progressos armazenados.
- **SC-003**: Em 100% das consultas cobertas, nenhum progresso pertencente a outro usuario e retornado e badges sem progresso pessoal apresentam uma colecao vazia.
- **SC-004**: 100% dos payloads invalidos sao rejeitados sem criar ou alterar badges parcialmente.
- **SC-005**: Usuarios autenticados conseguem concluir cada operacao principal do catalogo em uma unica interacao valida, sem informar campos internos ou relacionamentos controlados pelo sistema.
- **SC-006**: Em 100% dos testes de contrato, os responses permitem identificar badge e progresso apenas por nomes de negocio, sem expor nomes fisicos de armazenamento.

## Assumptions

- O mecanismo existente de autenticacao sera reutilizado e identifica o usuario atual.
- Badge e um recurso raiz de catalogo global e nao herda ownership de outro agregado.
- A entidade Badge e BadgeProgress ja existem e nao exigem alteracao estrutural para esta feature.
- Os valores validos dos criterios sao `xp_gained`, `tracks_completed`, `lessons_completed`, `right_answers`, `day_streak`, `tracks_created` e `missions_completed`; a feature nao cria novos criterios implicitamente.
- Nomes de badges sao unicos entre registros ativos; a remocao logica libera o nome para reutilizacao.
- A unicidade ignora maiusculas, minusculas e espacos nas extremidades; o valor persistido e retornado e o nome normalizado.
- A paginacao segue os padroes normativos ja adotados no projeto.
- A remocao logica nao oferece restauracao nesta primeira versao.
- O status de BadgeProgress e evoluido por regra de dominio separada e apenas e carregado nas respostas desta feature.