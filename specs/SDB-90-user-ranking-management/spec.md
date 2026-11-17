# Feature Specification: Gerenciamento do Ranking de Usuários por XP

**Feature Branch**: `feat/sdb-90-criar-endpoints-para-gerenciamento-do-ranking-dos-usuarios`

**Created**: 2026-10-21

**Status**: Draft

**Input**: User description: "SDB-90 — Criar endpoints para gerenciamento do ranking dos usuários"

## Clarifications

### Session 2026-10-21

- Q: A resposta da consulta à própria posição no ranking (`GET /rankings/me`) deve retornar apenas os cinco campos padrão de uma entrada do ranking ou incluir também o campo adicional `totalUsers`? → A: Retornar exatamente os 5 campos de `RankingEntryResponse` (`position`, `userId`, `name`, `xp`, `missionsCompleted`), sem `totalUsers`.
- Q: Uma missão ativa concluída deve continuar somando XP e missões concluídas no ranking mesmo que a etapa (`Step`) ou trilha (`Track`) pai seja removida logicamente depois? → A: Considerar apenas a exclusão lógica do usuário e da própria missão (preservar XP mesmo se `Step` ou `Track` pai estiver removido logicamente).
- Q: Na consulta de posição individual (`GET /rankings/me`), como o sistema deve conciliar o uso obrigatório de `get_current_user` com o retorno de erro `404` para usuário não encontrado ou removido logicamente? → A: Manter `get_current_user` inalterado na rota e lançar `404` no `RankingService` quando o usuário autenticado não for encontrado como ativo na consulta do ranking.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar o ranking geral de usuários por XP (Priority: P1)

Como usuário autenticado, quero consultar a classificação geral de participantes ordenada por pontos de experiência (XP) em páginas para acompanhar o desempenho da comunidade e comparar meu progresso com o dos demais estudantes.

**Why this priority**: A listagem geral do ranking é a funcionalidade central de gamificação e visibilidade coletiva da plataforma, permitindo que qualquer usuário autenticado compreenda a distribuição de posições e pontuações.

**Independent Test**: Com um conjunto conhecido de usuários ativos e removidos logicamente, com diferentes quantidades de missões concluídas, em andamento, não iniciadas e removidas logicamente, consultar páginas da classificação geral e verificar que apenas usuários ativos são exibidos na ordem correta de XP e desempate, com posições globais sequenciais e metadados de paginação precisos.

**Acceptance Scenarios**:

1. **Given** usuários ativos com diferentes totais de XP derivados de missões ativas concluídas, **When** um usuário autenticado consulta a classificação geral informando página e tamanho de página válidos, **Then** o sistema retorna a lista ordenada do maior para o menor XP com posição global sequencial iniciando em 1, identificador do usuário, nome, total de XP, total de missões concluídas e metadados de paginação completos.
2. **Given** uma classificação geral com múltiplos participantes distribuídos em mais de uma página, **When** o usuário autenticado consulta a segunda página da classificação, **Then** o sistema mantém a numeração global de posições continuando a sequência imediatamente após o último item da página anterior, sem reiniciar a contagem em 1.
3. **Given** usuários ativos que ainda não concluíram nenhuma missão ou possuem apenas missões não iniciadas ou em andamento, **When** a classificação geral é consultada, **Then** esses usuários aparecem normalmente no ranking com XP igual a 0 e quantidade de missões concluídas igual a 0.
4. **Given** uma solicitação de consulta ao ranking sem autenticação válida, **When** a operação é submetida, **Then** o sistema recusa o acesso e não expõe dados da classificação.

---

### User Story 2 - Consultar a própria posição no ranking (Priority: P1)

Como usuário autenticado, quero consultar diretamente minha posição atual, meu XP acumulado e meu total de missões concluídas sem precisar percorrer manualmente várias páginas da classificação geral.

**Why this priority**: Em bases com muitos participantes, localizar a própria colocação paginando a lista geral seria lento e pouco prático; a consulta direta entrega valor imediato para exibição no perfil ou cabeçalho da aplicação.

**Independent Test**: Autenticar-se com um usuário ativo em uma base com múltiplos participantes acima, empatados e abaixo de sua pontuação e verificar que a consulta individual retorna exatamente a mesma posição global, XP e contagem de missões concluídas que esse usuário ocupa na classificação geral.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado e ativo com missões ativas concluídas, **When** ele consulta sua própria colocação no ranking, **Then** o sistema retorna sua posição global exata, seu identificador, seu nome, seu XP total e sua quantidade de missões concluídas, em total consistência com a listagem geral.
2. **Given** um usuário autenticado e ativo que ainda não concluiu nenhuma missão ativa, **When** ele consulta sua própria colocação no ranking, **Then** o sistema retorna XP igual a 0, quantidade de missões concluídas igual a 0 e sua posição global calculada conforme a regra de ordenação e desempate.
3. **Given** um contexto autenticado cujo usuário associado tenha sido removido logicamente ou não seja encontrado como usuário ativo na consulta de ranking, **When** a colocação individual é consultada, **Then** o sistema informa que o recurso não foi encontrado.

---

### User Story 3 - Garantir elegibilidade, cálculo derivado de XP e desempate determinístico (Priority: P2)

Como usuário autenticado, quero que a classificação reflita exclusivamente usuários ativos e missões ativas concluídas, com regra de desempate estável e sem exposição de dados sensíveis, para que o ranking seja justo, previsível e seguro.

**Why this priority**: Sem regras determinísticas de elegibilidade e desempate, usuários com a mesma pontuação trocariam de posição entre consultas e exclusões lógicas distorceriam a competição.

**Independent Test**: Criar cenários de empate de XP entre múltiplos usuários ativos (incluindo usuários com 0 XP), além de missões removidas logicamente e usuários removidos logicamente, e verificar que a posição permanece idêntica entre consultas repetidas e que registros excluídos não afetam o cálculo nem as posições.

**Acceptance Scenarios**:

1. **Given** dois ou mais usuários ativos com exatamente o mesmo total de XP, **When** a classificação geral ou a posição individual é consultada repetidas vezes, **Then** o sistema atribui posições distintas e estáveis desempatando primeiro pelo cadastro mais antigo e, persistindo o empate, pelo identificador do usuário em ordem crescente.
2. **Given** um usuário ativo que concluiu uma missão que posteriormente foi removida logicamente, **When** o ranking é consultado, **Then** a recompensa de XP e a contagem dessa missão removida são desconsideradas no cálculo do usuário.
3. **Given** um usuário removido logicamente que possuía alto total de XP, **When** o ranking geral ou a posição de outros usuários é consultada, **Then** o usuário removido não aparece na listagem e não ocupa posição à frente dos usuários ativos.

### Edge Cases

- Usuários ativos sem nenhum registro de progresso de missão ou apenas com progressos não iniciados (`idle`) ou em andamento (`in_progress`) devem receber XP igual a 0 e 0 missões concluídas, permanecendo visíveis e posicionados no ranking.
- Pontuações de desempenho internas de um progresso de missão (como nota ou escore da atividade) não devem alterar o cálculo de XP: o valor contabilizado deve ser exclusivamente a recompensa de XP definida na missão ativa concluída.
- Missões removidas logicamente não devem somar XP nem incrementar a quantidade de missões concluídas, mesmo que o progresso associado esteja marcado como concluído (`done`).
- Missões ativas concluídas cujo recurso superior (`Step` ou `Track`) tenha sido removido logicamente continuam válidas no cálculo de XP e de missões concluídas, desde que a própria missão permaneça ativa.
- Usuários removidos logicamente não devem aparecer na classificação geral, não devem ser contabilizados no total de itens da paginação e não devem deslocar a posição dos usuários ativos.
- Empates de XP não compartilham a mesma posição numérica: cada participante recebe uma posição única e sequencial definida pelos critérios de desempate (antiguidade de cadastro e identificador).
- Solicitações de paginação com número de página menor que 1 ou tamanho de página fora do intervalo de 1 a 100 devem ser rejeitadas com erro de validação padronizado.
- Uma página solicitada além do total de páginas existente deve retornar lista de dados vazia preservando os metadados reais de paginação (`page`, `page_size`, `total_items`, `total_pages`).
- Credenciais ausentes ou inválidas na autenticação padrão são recusadas como não autenticadas, enquanto um usuário autenticado que não seja encontrado como ativo na consulta individual do ranking resulta em erro de recurso não encontrado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar apenas operações de leitura para o ranking de usuários, sem permitir criação, edição ou exclusão direta de pontos de experiência (XP) ou posições.
- **FR-002**: O sistema MUST exigir autenticação válida do usuário pelo mecanismo compartilhado do produto para todas as consultas do ranking geral e da posição individual.
- **FR-003**: O sistema MUST calcular o XP de cada usuário ativo de forma derivada como a soma das recompensas de XP das missões ativas (não removidas logicamente) cujo progresso para aquele usuário esteja com estado concluído (`done`), independentemente do estado de exclusão lógica da etapa (`Step`) ou trilha (`Track`) pai.
- **FR-004**: O sistema MUST atribuir XP igual a 0 e quantidade de missões concluídas igual a 0 aos usuários ativos que não possuam nenhuma missão ativa com progresso concluído (`done`), mantendo-os incluídos no ranking.
- **FR-005**: O sistema MUST calcular a quantidade de missões concluídas (`missionsCompleted`) de cada usuário ativo como o total de missões ativas (não removidas logicamente) cujo progresso do usuário esteja com estado concluído (`done`), independentemente do estado de exclusão lógica de `Step` ou `Track`.
- **FR-006**: O sistema MUST ignorar no cálculo de XP e de missões concluídas quaisquer progressos em estado não iniciado (`idle`) ou em andamento (`in_progress`), quaisquer missões removidas logicamente e quaisquer notas ou escores parciais do progresso.
- **FR-007**: O sistema MUST excluir usuários removidos logicamente de todas as listagens, contagens totais de participantes e cálculos de posição do ranking.
- **FR-008**: O sistema MUST ordenar o ranking de forma determinística pelo total de XP em ordem decrescente e, em caso de empate, desempatar pela data de criação do usuário em ordem crescente seguida pelo identificador do usuário em ordem crescente.
- **FR-009**: O sistema MUST atribuir a cada participante elegível uma posição global inteira iniciada em 1 (`position` >= 1), sequencial e sem repetição de número em empates, mantendo a continuidade da numeração entre páginas consecutivas.
- **FR-010**: O sistema MUST permitir listar o ranking geral de forma paginada, retornando a coleção `data` e os metadados `page`, `page_size`, `total_items` e `total_pages`, com página padrão 1 (mínimo 1) e tamanho de página padrão 20 (mínimo 1 e máximo 100).
- **FR-011**: O sistema MUST permitir que o usuário autenticado consulte diretamente sua própria entrada no ranking sem necessidade de paginar a listagem geral, recebendo exatamente a mesma posição e valores que ocupa na classificação global.
- **FR-012**: Cada entrada retornada na listagem geral ou na consulta individual MUST conter exclusivamente os cinco atributos públicos `position`, `userId`, `name`, `xp` e `missionsCompleted`, sem incluir `totalUsers` na resposta individual.
- **FR-013**: O sistema MUST NOT expor endereço de e-mail, credenciais ou hashes de senha, datas internas de auditoria ou atributos internos de armazenamento de usuários, missões ou progressos nas respostas do ranking.
- **FR-014**: O sistema MUST preservar o comportamento padrão de autenticação nas rotas e, caso o usuário autenticado não seja encontrado como usuário ativo (inexistente ou removido logicamente) durante a consulta individual ao ranking, o serviço MUST retornar erro de recurso não encontrado (`404`).
- **FR-015**: Todas as respostas de falha (como ausência ou invalidade de autenticação, parâmetros de paginação inválidos ou usuário não encontrado) MUST seguir o formato padronizado de detalhes de problema adotado pelo produto.

### Key Entities

- **Entrada do Ranking (RankingEntry)**: Representação pública e derivada do desempenho de um participante ativo na classificação, composta exclusivamente por posição global (`position`), identificador do usuário (`userId`), nome de exibição (`name`), XP acumulado (`xp`) e total de missões concluídas (`missionsCompleted`).
- **Usuário (User)**: Participante da plataforma; apenas usuários ativos (não removidos logicamente) são elegíveis ao ranking e contribuem para a contagem de posições, usando sua antiguidade de cadastro e identificador como critério de desempate.
- **Missão (Mission)**: Desafio de aprendizagem que define a recompensa fixa de XP atribuída ao estudante quando concluído; apenas missões ativas (não removidas logicamente) contabilizam XP e conclusão no ranking.
- **Progresso de Missão (MissionProgress)**: Registro do vínculo e estado de realização de uma missão por um usuário; somente registros em estado concluído (`done`) geram XP e incrementam a contagem de missões concluídas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos usuários autenticados ativos conseguem consultar tanto uma página da classificação geral quanto sua própria colocação individual em uma única operação cada, obtendo a mesma posição e pontuação em ambas as consultas.
- **SC-002**: Em 100% dos cenários testados com usuários sem missões concluídas, missões em estados `idle` ou `in_progress`, missões removidas logicamente e usuários removidos logicamente, o total de XP, o total de missões concluídas e a posição global refletem estritamente as regras de elegibilidade definidas.
- **SC-003**: Em 100% das consultas repetidas sobre conjuntos de usuários com pontuações empatadas, a ordem e a posição numérica de cada usuário permanecem idênticas entre páginas e entre chamadas sucessivas.
- **SC-004**: 100% das respostas do ranking geral e da posição individual ocultam e-mail, credenciais e campos internos de armazenamento, expondo apenas os cinco atributos públicos contratados.
- **SC-005**: 100% das solicitações sem autenticação válida, com parâmetros de paginação fora dos limites permitidos ou cujos usuários não estejam ativos na consulta individual do ranking são recusadas com a resposta padronizada correspondente.
- **SC-006**: As consultas de listagem paginada do ranking e de posição individual do usuário mantêm quantidade constante de operações de leitura por requisição independentemente do número de usuários retornados na página (sem consultas adicionais por item listado).

## Assumptions

- O ranking é integralmente derivado do histórico atual de missões ativas concluídas por usuários ativos, não existindo saldo manual ou avulso de XP fora das missões nesta versão.
- Recortes temporais (como ranking semanal ou mensal) ou filtros por trilha específica estão fora do escopo desta funcionalidade, que contempla o ranking global acumulado da plataforma.
