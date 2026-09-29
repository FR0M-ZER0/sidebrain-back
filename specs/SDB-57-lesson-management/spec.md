# Feature Specification: Gerenciamento de Lições

**Feature Branch**: `feat/sdb-57-criar-endpoint-para-gerenciamento-das-licoes`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "SDB-57 — Criar endpoint para gerenciamento das lições"

## Clarifications

### Session 2026-09-21

- Q: Quando uma lição é removida logicamente, sua posição deve continuar reservada dentro da etapa? → A: Manter a posição reservada após o soft delete.
- Q: O endpoint `PUT /lessons/{lesson_id}` deve exigir todos os quatro campos editáveis (`title`, `text`, `status` e `position`)? → A: Exigir todos os quatro campos no `PUT`.
- Q: Ao alterar a posição de uma lição, o sistema deve ajustar automaticamente as posições das demais lições da etapa? → A: Alterar apenas a lição solicitada e rejeitar posições ocupadas, sem reordenação automática.
- Q: A atualização deve permitir qualquer transição entre `idle`, `in_progress` e `done`, inclusive retornar de `done` para `idle`? → A: Permitir qualquer transição entre os três estados.
- Q: Como a meta de desempenho da listagem com até 50 lições deve ser validada? → A: Benchmark local com PostgreSQL 16 via Docker Compose, `MODE=test`, 5 aquecimentos e 100 requisições sequenciais; página com 50 lições, cada uma com 5 feedbacks, 3 arquivos e 5 quizzes de 10 respostas; P95 de até 2 segundos e quantidade constante de comandos SQL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar lição em uma etapa própria (Priority: P1)

Como usuário autenticado, quero criar uma lição em uma etapa de uma trilha que me pertence para organizar o conteúdo que devo estudar.

**Why this priority**: A criação estabelece a unidade de aprendizagem que será consultada e mantida pelos demais fluxos da feature.

**Independent Test**: Com uma etapa ativa pertencente ao usuário, informar título, texto e posição válidos e verificar que a lição é criada nessa etapa com estado inicial `idle`, sem aceitar que o cliente escolha outra etapa ou campos internos.

**Acceptance Scenarios**:

1. **Given** uma etapa existente, ativa e pertencente a uma trilha do usuário autenticado, **When** ele informa título, texto e posição válidos, **Then** o sistema cria a lição vinculada à etapa selecionada, atribui o estado inicial `idle` e retorna as coleções filhas vazias.
2. **Given** uma etapa inexistente, excluída ou pertencente a outro usuário, **When** o usuário tenta criar uma lição nela, **Then** o sistema informa que o recurso não foi encontrado, não revela sua propriedade e não cria dados parciais.
3. **Given** uma etapa com uma lição ativa em determinada posição, **When** o usuário tenta criar outra lição na mesma posição, **Then** o sistema rejeita a operação com erro de conflito e mantém as lições existentes inalteradas.

---

### User Story 2 - Consultar lições e conteúdo relacionado (Priority: P1)

Como usuário autenticado, quero listar as lições de uma etapa e consultar uma lição específica com seus conteúdos relacionados para acessar uma visão completa da unidade de aprendizagem.

**Why this priority**: A consulta entrega o conteúdo ao usuário e garante que feedbacks, arquivos e avaliações possam ser consumidos no contexto correto.

**Independent Test**: Preparar uma etapa própria com lições ativas e excluídas, além de feedbacks, arquivos, quizzes e respostas, e verificar na listagem paginada e no detalhe que apenas as lições ativas são exibidas com a hierarquia correta.

**Acceptance Scenarios**:

1. **Given** uma etapa ativa do usuário com lições ativas e excluídas, **When** ele consulta a coleção de lições, **Then** o sistema retorna em páginas somente as lições ativas, ordenadas por posição crescente e acompanhadas por metadados de paginação consistentes.
2. **Given** uma lição ativa e acessível com feedbacks, arquivos e quizzes que possuem respostas, **When** ela é consultada por identificador, **Then** o sistema retorna os dados da lição, seus feedbacks, arquivos e quizzes ativos com as respectivas respostas.
3. **Given** uma etapa ativa sem lições ativas, **When** sua coleção é consultada, **Then** o sistema retorna uma página vazia com metadados consistentes.
4. **Given** uma lição inexistente, excluída, contida em um pai excluído ou pertencente a outro usuário, **When** ela é consultada, **Then** o sistema informa que o recurso não foi encontrado sem expor dados protegidos.

---

### User Story 3 - Atualizar ou remover uma lição (Priority: P2)

Como usuário autenticado, quero atualizar os dados de uma lição própria ou removê-la logicamente para manter o conteúdo e seu progresso organizados sem apagar o histórico interno.

**Why this priority**: A manutenção completa o ciclo de vida da lição e permite corrigir conteúdo ou retirá-lo de uso preservando seus relacionamentos.

**Independent Test**: Criar uma lição com recursos filhos, substituir seus campos editáveis por valores válidos, removê-la e confirmar que ela deixa de aparecer nas consultas normais sem que seus registros filhos sejam removidos.

**Acceptance Scenarios**:

1. **Given** uma lição ativa pertencente ao usuário, **When** ele informa título, texto, estado e posição válidos, **Then** o sistema substitui os campos editáveis, preserva a etapa vinculada e retorna a lição atualizada com seus filhos.
2. **Given** outra lição ativa na posição solicitada dentro da mesma etapa, **When** o usuário tenta atualizar a posição, **Then** o sistema rejeita a alteração com erro de conflito e preserva os dados anteriores.
3. **Given** uma lição ativa com recursos filhos, **When** o usuário solicita sua remoção, **Then** o sistema conclui a remoção lógica sem conteúdo de resposta e preserva fisicamente a lição e seus filhos.
4. **Given** uma lição excluída, inexistente ou pertencente a outro usuário, **When** o usuário tenta atualizá-la ou removê-la, **Then** o sistema informa que o recurso não foi encontrado e não modifica dados.

### Edge Cases

- Identificadores malformados devem produzir erro de validação sem consultar ou alterar conteúdo protegido.
- Título ou texto ausente, nulo, vazio ou formado somente por espaços deve ser rejeitado; o título normalizado não pode exceder 255 caracteres.
- A posição deve ser um número inteiro positivo e único entre todas as lições da mesma etapa, inclusive as removidas logicamente; a mesma posição pode existir em etapas diferentes.
- Uma atualização completa sem qualquer um dos quatro campos editáveis (`title`, `text`, `status` e `position`) deve ser rejeitada sem alteração parcial.
- O estado deve aceitar somente `idle`, `in_progress` ou `done`.
- Identificador, etapa, data de atualização e campos de exclusão enviados pelo cliente devem ser rejeitados como campos não permitidos.
- Uma lição ativa sob etapa ou trilha excluída deve permanecer indisponível nas operações normais.
- Lições e recursos filhos removidos logicamente não devem reaparecer em listagens, detalhes ou hierarquias.
- Lição sem feedbacks, arquivos ou quizzes deve apresentar coleções vazias, nunca valores ausentes.
- Quiz sem respostas deve apresentar uma coleção de respostas vazia.
- Uma página solicitada além do total disponível deve retornar coleção vazia e metadados de paginação consistentes.
- A remoção lógica de uma lição não deve remover nem marcar automaticamente feedbacks, arquivos, quizzes ou respostas como excluídos.
- Falha durante criação, atualização ou remoção não deve deixar mudanças parciais persistidas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um usuário autenticado crie uma lição vinculada a uma etapa existente, ativa e pertencente a uma trilha desse usuário.
- **FR-002**: O sistema MUST determinar a etapa da nova lição pelo contexto da operação e MUST NOT aceitar que o cliente controle esse vínculo no conteúdo enviado.
- **FR-003**: A criação MUST exigir `title`, `text` e `position`, normalizando espaços nas extremidades de `title` e `text` antes da validação.
- **FR-004**: O título normalizado MUST conter de 1 a 255 caracteres, o texto normalizado MUST conter ao menos 1 caractere e a posição MUST ser um inteiro maior ou igual a 1.
- **FR-005**: Toda nova lição MUST receber o estado inicial `idle`, sem aceitar estado fornecido pelo cliente durante a criação.
- **FR-006**: O sistema MUST manter a posição única entre todas as lições de uma mesma etapa, inclusive as removidas logicamente, e MUST rejeitar conflitos sem persistir alteração parcial.
- **FR-007**: O sistema MUST permitir listar de forma paginada as lições ativas de uma etapa ativa e acessível, ordenadas por posição crescente.
- **FR-008**: Toda listagem MUST informar `data`, `page`, `page_size`, `total_items` e `total_pages`, usando página 1 e 20 itens por padrão e aceitando de 1 a 100 itens por página.
- **FR-009**: O sistema MUST permitir consultar uma lição ativa e acessível por identificador.
- **FR-010**: Toda representação de lição MUST conter identificador, título, texto, estado, posição, data de atualização e as coleções `feedbacks`, `files` e `quizzes`.
- **FR-011**: Cada quiz retornado como filho de uma lição MUST conter suas respostas associadas, e todas as coleções sem itens MUST ser representadas por listas vazias.
- **FR-012**: As leituras de lição MUST omitir feedbacks e quizzes removidos logicamente e MUST preservar os filtros de visibilidade já definidos para os recursos filhos.
- **FR-013**: O sistema MUST permitir substituir, em uma atualização completa, `title`, `text`, `status` e `position` de uma lição ativa e acessível.
- **FR-014**: A atualização MUST exigir todos os campos editáveis e MUST aplicar aos campos textuais e à posição as mesmas validações da criação.
- **FR-015**: O estado informado na atualização MUST ser `idle`, `in_progress` ou `done`, e o sistema MUST permitir qualquer transição entre esses estados, inclusive regressões.
- **FR-016**: A atualização MUST NOT permitir alterar a etapa associada, o identificador, a data de atualização ou os dados de exclusão da lição.
- **FR-017**: O sistema MUST permitir remover logicamente uma lição ativa e acessível, preservando seu registro e registrando internamente o momento da remoção.
- **FR-018**: A remoção lógica de uma lição MUST NOT remover fisicamente nem alterar automaticamente seus feedbacks, arquivos, quizzes ou respostas.
- **FR-019**: O sistema MUST excluir lições removidas logicamente de todas as consultas normais, incluindo detalhe, listagem da etapa e hierarquias de conteúdo superiores.
- **FR-020**: Antes de qualquer operação, o sistema MUST validar autenticação, existência e disponibilidade dos pais e a propriedade da trilha na cadeia Usuário → Trilha → Etapa → Lição.
- **FR-021**: Recursos inexistentes, excluídos, contidos em pais excluídos ou pertencentes a outro usuário MUST ser apresentados como não encontrados, sem revelar existência, propriedade ou dados protegidos.
- **FR-022**: O sistema MUST rejeitar payloads com campos não previstos e MUST impedir que o cliente controle identificadores, relacionamentos, datas ou exclusão lógica.
- **FR-023**: Os contratos públicos MUST usar nomes de negócio e MUST NOT expor nomes físicos de armazenamento ou outros campos internos.
- **FR-024**: Criação MUST resultar em `201`, leituras e atualização em `200`, remoção em `204` sem conteúdo e falhas em respostas Problem Details compatíveis com o padrão vigente do produto.
- **FR-025**: As consultas MUST recuperar a hierarquia de filhos como um conjunto, sem degradação proporcional causada por uma operação separada para cada item filho.
- **FR-026**: O escopo da feature MUST limitar-se ao gerenciamento de lições e à leitura dos filhos existentes; criar, atualizar ou remover feedbacks, arquivos, quizzes e respostas fica fora do escopo.

### Key Entities

- **Lição (Lesson)**: Unidade de aprendizagem pertencente obrigatoriamente a uma etapa; possui identificador, título, texto, estado, posição, data de atualização e estado interno de exclusão lógica.
- **Etapa (Step)**: Agrupador pai de lições, pertencente a uma trilha; determina o contexto de criação, listagem e autorização da lição.
- **Trilha (Track)**: Percurso de aprendizagem pertencente a um usuário; sua propriedade determina quem pode consultar e gerenciar as lições das etapas relacionadas.
- **Feedback**: Comentário existente associado a uma lição e apresentado somente para leitura neste escopo.
- **Arquivo da lição (LessonFile)**: Recurso de áudio, GIF ou imagem associado a uma lição e apresentado somente para leitura neste escopo.
- **Quiz**: Avaliação existente associada a uma lição e apresentada com suas respostas correspondentes na hierarquia de leitura.
- **Resposta (Answer)**: Resposta existente associada a um quiz, apresentada somente como conteúdo filho nesta feature.
- **Usuário**: Pessoa autenticada proprietária da trilha e, indiretamente, das etapas e lições que ela contém.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários autenticados conseguem criar, localizar, atualizar e remover logicamente uma lição própria em até quatro operações válidas, sem informar campos internos ou o vínculo da etapa no conteúdo enviado.
- **SC-002**: 100% das tentativas cobertas contra etapas ou lições inexistentes, excluídas, contidas em pais excluídos ou pertencentes a outro usuário são recusadas sem exposição de dados e sem alterações parciais.
- **SC-003**: 100% das listagens retornam somente lições ativas da etapa solicitada, em posição crescente, com metadados de paginação coerentes com o total disponível.
- **SC-004**: Em 100% das leituras cobertas, cada lição apresenta exatamente seus feedbacks, arquivos e quizzes visíveis, cada quiz apresenta suas respostas correspondentes e coleções sem itens são retornadas vazias.
- **SC-005**: 100% dos conflitos de posição na mesma etapa, inclusive com lições removidas logicamente, são rejeitados, enquanto posições iguais em etapas diferentes permanecem válidas.
- **SC-006**: 100% das lições removidas logicamente deixam de aparecer imediatamente nas consultas normais, enquanto seus registros e recursos filhos permanecem inalterados por esta operação.
- **SC-007**: Em benchmark end-to-end local com a API em `MODE=test`, PostgreSQL 16 iniciado pelo Docker Compose e sem concorrência, após 5 requisições de aquecimento, o percentil 95 de 100 requisições autenticadas sequenciais à primeira página da listagem com `page_size=50`, contendo 50 lições ativas e, por lição, 5 feedbacks ativos, 3 arquivos ativos e 5 quizzes ativos com 10 respostas cada, MUST ser de no máximo 2 segundos.
- **SC-008**: No benchmark definido em SC-007, a quantidade de comandos SQL MUST permanecer constante ao comparar cenários equivalentes com 1 e 50 lições, mantendo por lição o mesmo volume de filhos, de modo a demonstrar ausência de N+1.
- **SC-009**: Todos os cenários de aceite das três jornadas são verificáveis e passam antes da liberação da funcionalidade.

## Assumptions

- O mecanismo existente de autenticação fornece a identidade do usuário atual e será reutilizado sem criar uma nova forma de login ou autorização.
- O `PUT` representa atualização completa: `title`, `text`, `status` e `position` são obrigatórios; atualização parcial fica fora deste escopo.
- Título e texto são normalizados pela remoção de espaços nas extremidades; posições válidas começam em 1 e não provocam reordenação automática das demais lições.
- A unicidade de posição considera todas as lições da mesma etapa; uma lição removida logicamente continua reservando sua posição.
- A listagem segue o formato paginado normativo do projeto, mesmo que o exemplo original do Jira mostre somente a coleção de itens.
- A ordenação primária das lições é por posição crescente; as coleções filhas preservam as regras de ordenação de seus contratos vigentes.
- Recursos pertencentes a outro usuário são ocultados como não encontrados, seguindo a política de não revelar ownership já adotada pelo produto.
- Feedbacks, arquivos, quizzes e respostas já possuem ciclo de vida próprio e são somente leitura nesta feature.
- A remoção lógica da lição não oferece restauração nesta primeira versão e não propaga exclusão lógica aos recursos filhos.
