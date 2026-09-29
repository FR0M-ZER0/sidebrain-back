# Feature Specification: Gerenciamento de Quizzes

**Feature Branch**: `feat/sdb-51-criar-endpoint-para-gerenciamento-dos-quizzes`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "SDB-51"

## Clarifications

### Session 2026-09-17

- Q: Como a aula do quiz e o usuário de cada resposta devem ser identificados no contrato público? → A: Campos escalares `lesson_id` no quiz e `user_id` em cada resposta.
- Q: Quais estados da aula permitem criar, listar e gerenciar seus quizzes? → A: Qualquer aula não excluída, independentemente de `idle`, `in_progress` ou `done`.
- Q: Em qual ordem os quizzes devem aparecer na listagem paginada de uma aula? → A: `updated_at` decrescente e, em empate, `id` decrescente.
- Q: Qual deve ser o tamanho máximo permitido para a pergunta de um quiz após remover espaços nas extremidades? → A: Máximo de 1.000 caracteres.
- Q: Em qual ordem as respostas de cada quiz devem aparecer nas consultas e nas hierarquias? → A: `created_at` crescente e, em empate, `id` crescente.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar quiz em uma aula (Priority: P1)

Como usuário autenticado com acesso a uma aula não excluída, quero criar um quiz nessa aula para incluir uma pergunta de avaliação no conteúdo estudado.

**Why this priority**: A criação estabelece o recurso central da feature e permite que a aula passe a oferecer avaliações.

**Independent Test**: Com uma aula existente, não excluída e acessível, enviar uma pergunta válida e verificar que um novo quiz é criado na aula indicada, sem exigir que o cliente informe o relacionamento no conteúdo enviado.

**Acceptance Scenarios**:

1. **Given** uma aula existente, não excluída e acessível ao usuário autenticado, em qualquer estado de progresso, **When** o usuário informa uma pergunta válida, **Then** o sistema cria o quiz associado à aula e retorna seus dados de negócio com uma coleção de respostas inicialmente vazia.
2. **Given** uma aula inexistente ou excluída, **When** o usuário tenta criar um quiz para ela, **Then** o sistema recusa a operação, informa que a aula não foi encontrada e não cria dados parciais.
3. **Given** uma aula à qual o usuário autenticado não possui acesso, **When** ele tenta criar um quiz, **Then** o sistema recusa a operação sem alterar a aula.

### User Story 2 - Consultar quizzes e respostas (Priority: P1)

Como usuário com acesso ao conteúdo, quero consultar os quizzes ativos de uma aula com suas respostas para visualizar a avaliação completa dentro da hierarquia de aprendizagem.

**Why this priority**: Os quizzes só entregam valor quando podem ser recuperados junto das perguntas e respostas que compõem a avaliação.

**Independent Test**: Preparar uma aula com quizzes ativos, um quiz excluído e respostas associadas, consultar a coleção e um quiz específico e verificar que apenas quizzes ativos são exibidos, cada um com todas as respostas correspondentes.

**Acceptance Scenarios**:

1. **Given** uma aula não excluída com quizzes ativos e excluídos, **When** sua coleção de quizzes é consultada, **Then** o sistema retorna em páginas somente os quizzes ativos, ordenados por `updated_at` decrescente e `id` decrescente, com seus dados de negócio e respostas associadas.
2. **Given** um quiz ativo e acessível com respostas, **When** ele é consultado por identificador, **Then** o sistema retorna a pergunta, a aula associada e todas as suas respostas ordenadas por `created_at` crescente e `id` crescente.
3. **Given** uma aula não excluída sem quizzes, **When** sua coleção de quizzes é consultada, **Then** o sistema retorna uma página vazia com metadados consistentes.
4. **Given** uma aula com quizzes e respostas, **When** a aula é consultada em uma visão hierárquica, **Then** seus quizzes ativos e as respostas de cada quiz aparecem na hierarquia `Lesson → Quiz[] → Answer[]`.
5. **Given** um quiz inexistente, excluído ou pertencente a uma aula excluída, **When** ele é consultado, **Then** o sistema informa que o recurso não foi encontrado e não expõe seus dados.

### User Story 3 - Atualizar ou remover um quiz (Priority: P2)

Como usuário autenticado com permissão sobre uma aula, quero corrigir a pergunta de um quiz ou removê-lo logicamente para manter a avaliação atualizada sem perder a integridade dos dados relacionados.

**Why this priority**: A manutenção completa o ciclo de gerenciamento e permite corrigir ou retirar conteúdo preservando o histórico interno.

**Independent Test**: Criar um quiz com respostas, alterar sua pergunta e depois removê-lo, verificando que a aula associada não muda, que a remoção não apaga fisicamente o quiz nem suas respostas e que o recurso deixa de aparecer nas consultas normais.

**Acceptance Scenarios**:

1. **Given** um quiz ativo e acessível, **When** o usuário informa uma nova pergunta válida, **Then** o sistema atualiza somente a pergunta, preserva a aula associada e retorna o quiz com suas respostas.
2. **Given** um quiz ativo e acessível com respostas, **When** o usuário solicita sua remoção, **Then** o sistema conclui a remoção lógica sem retornar conteúdo e preserva internamente o quiz e suas respostas.
3. **Given** um quiz excluído, **When** alguém tenta consultá-lo, atualizá-lo ou removê-lo novamente, **Then** o sistema o trata como não encontrado e não realiza alteração.
4. **Given** um quiz pertencente a uma aula inacessível ao usuário autenticado, **When** ele tenta atualizá-lo ou removê-lo, **Then** o sistema recusa a operação e preserva o conteúdo original.

### Edge Cases

- Pergunta ausente, vazia, formada somente por espaços ou com mais de 1.000 caracteres após remover espaços nas extremidades deve ser rejeitada sem criar ou alterar um quiz.
- Identificador, aula associada, respostas, datas ou estado de exclusão enviados pelo cliente não devem substituir valores controlados pelo sistema.
- Um quiz ativo cujo recurso pai tenha sido excluído deve ficar inacessível nas consultas e operações normais.
- Um quiz excluído não deve reaparecer em consultas diretas, listagens ou composições hierárquicas.
- A remoção lógica de um quiz com respostas deve preservar essas respostas e não acionar remoção física em cascata.
- Um quiz sem respostas deve ser apresentado com uma coleção vazia, nunca com valor ausente.
- Uma página solicitada além do total disponível deve retornar coleção vazia e metadados de paginação consistentes.
- Consultas com muitos quizzes e respostas devem manter a correspondência correta entre cada quiz e suas respostas, sem duplicações ou omissões.
- Valores de classificação de resposta fora de `good`, `perfect`, `wrong` e `almost_got_it` não devem aparecer nos contratos públicos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um usuário autenticado e autorizado crie um quiz em uma aula existente e não excluída por meio de uma pergunta válida, independentemente de seu estado de progresso (`idle`, `in_progress` ou `done`); após remover espaços nas extremidades, a pergunta MUST conter entre 1 e 1.000 caracteres.
- **FR-002**: O sistema MUST determinar a aula associada pelo contexto em que o quiz é criado e MUST NOT exigir nem permitir que o cliente controle essa associação no conteúdo de criação.
- **FR-003**: O sistema MUST validar a existência, a ausência de exclusão lógica e a acessibilidade da aula antes de criar ou listar quizzes relacionados a ela; os estados `idle`, `in_progress` e `done` MUST ser aceitos.
- **FR-004**: O sistema MUST permitir listar, de forma paginada, os quizzes ativos pertencentes a uma aula não excluída e acessível, ordenados por `updated_at` decrescente e, em caso de empate, por `id` decrescente.
- **FR-005**: Cada listagem MUST informar a coleção retornada, a página atual, o tamanho da página, o total de itens e o total de páginas.
- **FR-006**: O sistema MUST permitir consultar um quiz ativo e acessível por identificador.
- **FR-007**: Toda representação de quiz MUST conter seu identificador, o campo escalar `lesson_id` da aula associada, a pergunta e a coleção de respostas associadas.
- **FR-008**: Cada resposta apresentada como filha de um quiz MUST conter seu identificador, o campo escalar `user_id`, o texto e uma classificação válida entre `good`, `perfect`, `wrong` e `almost_got_it`.
- **FR-009**: O sistema MUST representar quizzes sem respostas com uma coleção vazia.
- **FR-010**: Ao apresentar uma aula em sua visão hierárquica, o sistema MUST incluir seus quizzes ativos e as respostas associadas a cada quiz, respeitando `Lesson → Quiz[] → Answer[]`.
- **FR-011**: Quando conteúdos superiores apresentarem a hierarquia completa de aprendizagem, o sistema MUST preservar a composição `Track → Step → Lesson → Quiz[] → Answer[]` e os mesmos filtros de acesso e exclusão.
- **FR-012**: O sistema MUST permitir atualizar a pergunta de um quiz ativo e acessível; após remover espaços nas extremidades, a nova pergunta MUST conter entre 1 e 1.000 caracteres.
- **FR-013**: A atualização de um quiz MUST NOT permitir alterar sua aula associada, respostas, identificador, datas ou estado de exclusão.
- **FR-014**: O sistema MUST permitir remover logicamente um quiz ativo e acessível, registrando internamente o momento da remoção e preservando o registro.
- **FR-015**: A remoção lógica de um quiz MUST NOT remover fisicamente o quiz nem suas respostas associadas.
- **FR-016**: O sistema MUST excluir quizzes removidos logicamente de todas as consultas normais, incluindo consulta por identificador, listagem da aula e respostas hierárquicas.
- **FR-017**: O sistema MUST tratar como indisponível um quiz cuja aula relacionada não exista ou esteja excluída.
- **FR-018**: Todas as operações de quiz MUST aplicar a mesma política de acesso da aula e do conteúdo superior ao qual ela pertence.
- **FR-019**: O sistema MUST recusar operações sem autenticação válida ou sem autorização aplicável, sem revelar ou modificar conteúdo protegido.
- **FR-020**: O sistema MUST rejeitar dados inválidos com mensagens compreensíveis e MUST NOT persistir alterações parciais.
- **FR-021**: Os contratos apresentados aos clientes MUST usar nomes de negócio e MUST NOT expor nomes físicos de armazenamento nem campos internos de exclusão.
- **FR-022**: O escopo da feature MUST limitar-se ao gerenciamento de quizzes e ao carregamento de respostas existentes; criação, atualização e remoção de respostas ficam fora do escopo.
- **FR-023**: As respostas de cada quiz MUST ser ordenadas por `created_at` crescente e, em caso de empate, por `id` crescente em consultas diretas, listagens e hierarquias.

### Key Entities

- **Quiz**: pergunta de avaliação pertencente obrigatoriamente a uma aula; possui identificador, pergunta, `lesson_id` da aula associada, coleção de respostas e estado interno de exclusão lógica.
- **Lesson**: aula que agrupa zero ou mais quizzes e determina o contexto de acesso e o ciclo de vida dos quizzes relacionados.
- **Answer**: resposta existente associada a um quiz e a um usuário; possui identificador, `user_id`, texto, classificação e momento de criação usado na ordenação, sendo somente consultada nesta feature.
- **User**: pessoa autenticada cuja permissão sobre o conteúdo superior determina quais quizzes podem ser consultados ou gerenciados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das criações válidas associam o quiz à aula selecionada pelo contexto, sem depender de identificador de aula fornecido no conteúdo enviado pelo cliente.
- **SC-002**: 100% das tentativas cobertas com aula inexistente, excluída ou inacessível são recusadas sem criar ou modificar quizzes.
- **SC-003**: 100% dos quizzes removidos logicamente deixam de aparecer imediatamente em consultas diretas, listagens e hierarquias, permanecendo preservados internamente com suas respostas.
- **SC-004**: Em 100% das consultas cobertas, cada quiz ativo apresenta exatamente suas respostas associadas, e quizzes sem respostas apresentam uma coleção vazia.
- **SC-005**: Em benchmark end-to-end local com a API em `MODE=test`, PostgreSQL 16 iniciado pelo Docker Compose e sem concorrência, após 5 requisições de aquecimento, o percentil 95 de 100 requisições autenticadas sequenciais a `GET /api/v1/lessons/{lesson_id}/quizzes?page=1&page_size=50`, para uma aula com 50 quizzes ativos e 10 respostas por quiz, MUST ser de no máximo 2 segundos; a quantidade de statements SQL MUST permanecer constante ao comparar cenários com 1 e 50 quizzes.
- **SC-006**: Usuários autorizados conseguem criar, localizar, atualizar e remover um quiz com uma única interação válida para cada operação, sem informar campos internos ou de relacionamento controlados pelo sistema.
- **SC-007**: Em 100% dos testes de contrato, a representação pública de Quiz MUST permitir identificar a aula, a pergunta e as respostas exclusivamente por `lesson_id`, `question` e `answers`; cada Answer MUST ser identificável por `user_id`, `text` e `rate`, sem consultar nomes físicos de armazenamento ou campos internos.
- **SC-008**: Todos os cenários de aceite das três jornadas são verificáveis e passam antes da liberação da funcionalidade.

## Assumptions

- O mecanismo existente de autenticação identifica o usuário atual e será reutilizado sem criar uma nova forma de login ou autorização.
- A permissão sobre um quiz é herdada da aula e dos recursos superiores aos quais ela pertence; a feature não cria novas categorias de permissão.
- A entidade de aula já existe e possui um estado de exclusão lógica que pode ser considerado nas validações.
- A elegibilidade da aula para operações de quiz não depende de seu estado de progresso; apenas existência, exclusão lógica e acesso são considerados.
- A paginação usa os padrões já adotados pelo projeto para valores padrão, limites e comportamento de páginas fora do intervalo.
- As respostas já existem e possuem ciclo de vida próprio; esta feature apenas as apresenta como filhas do quiz.
- A remoção lógica não oferece restauração de quiz nesta primeira versão.
- Os contratos hierárquicos existentes que apresentam aulas serão ampliados para incluir quizzes e respostas sem alterar a regra de acesso dos recursos superiores.
- Perguntas de quiz são normalizadas pela remoção de espaços nas extremidades e devem conter entre 1 e 1.000 caracteres.
