# Feature Specification: Resumo de Estatísticas de Aprendizagem

**Feature Branch**: `feat/sdb-112-endpoint-estatistica-usuario`

**Created**: 2026-11-18

**Status**: Draft

**Input**: Jira SDB-112 — Adicionar endpoints para visualização das estatísticas do usuário

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar o próprio resumo de aprendizagem (Priority: P1)

Como usuário autenticado, quero consultar em um único resumo meus resultados de aprendizagem para acompanhar meu progresso sem reunir informações de diferentes áreas.

**Why this priority**: O resumo consolidado é o valor principal da funcionalidade e permite que a pessoa entenda seu progresso atual em uma única consulta.

**Independent Test**: Preparar um usuário com missões concluídas, posição conhecida no ranking, conquistas concluídas e atividade recente; consultar o resumo e comparar cada valor com as informações existentes do perfil, ranking e conquistas.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado com progresso registrado, **When** consulta seu resumo, **Then** recebe XP total, missões concluídas, posição no ranking, quantidade de conquistas desbloqueadas e sequência atual de dias de atividade.
2. **Given** os mesmos dados de progresso disponíveis no perfil e no ranking, **When** o usuário consulta o resumo, **Then** XP, missões concluídas e posição coincidem com os valores apresentados nesses recursos.
3. **Given** um usuário com conquistas em diferentes estágios, **When** consulta o resumo, **Then** somente conquistas desbloqueadas são contabilizadas.

---

### User Story 2 - Consultar o resumo sem progresso e preservar a privacidade (Priority: P1)

Como usuário autenticado, quero receber um resumo seguro mesmo antes de começar a aprender e consultar somente meus próprios dados.

**Why this priority**: A resposta precisa ser previsível para contas novas e não pode revelar informações privadas de outros usuários.

**Independent Test**: Consultar o resumo de um usuário sem progresso e tentar acessá-lo sem credenciais válidas; confirmar contagens zeradas, posição conforme a regra atual do ranking e recusa de acesso não autenticado.

**Acceptance Scenarios**:

1. **Given** um usuário ativo sem progresso, **When** consulta seu resumo, **Then** XP, missões concluídas, conquistas desbloqueadas e sequência de atividade são zero, enquanto a posição segue a regra existente do ranking.
2. **Given** uma solicitação sem autenticação válida, **When** o resumo é consultado, **Then** o acesso é recusado com o erro padronizado e nenhum dado privado é retornado.
3. **Given** uma consulta autenticada, **When** o cliente tenta escolher outro usuário como titular do resumo, **Then** não consegue consultar estatísticas privadas de outra pessoa.

---

### User Story 3 - Interpretar corretamente a sequência de atividade (Priority: P2)

Como usuário, quero que minha sequência reflita os dias consecutivos recentes e expire depois de uma interrupção, para compreender meu ritmo de atividade sem valores desatualizados.

**Why this priority**: Uma sequência antiga apresentada como atual induziria a pessoa a interpretar incorretamente seu progresso.

**Independent Test**: Consultar usuários cuja última atividade ocorreu hoje, ontem, há mais de um dia completo ou nunca ocorreu; verificar a sequência informada sem que a consulta altere os registros.

**Acceptance Scenarios**:

1. **Given** atividade registrada hoje ou no dia UTC imediatamente anterior, **When** o resumo é consultado, **Then** a sequência armazenada é apresentada como atual.
2. **Given** que a última atividade ocorreu antes do dia UTC imediatamente anterior, **When** o resumo é consultado, **Then** a sequência atual apresentada é zero.
3. **Given** que não há registro de sequência de atividade, **When** o resumo é consultado, **Then** a sequência apresentada é zero.
4. **Given** uma sequência expirada, **When** uma consulta de resumo é realizada, **Then** os registros de atividade e progresso permanecem inalterados.

### Edge Cases

- Um usuário sem registro de progresso de missões ou conquistas recebe zero nas contagens correspondentes.
- Conquistas em andamento ou ainda não iniciadas não são contadas como desbloqueadas.
- Conquistas removidas do catálogo não são consideradas desbloqueadas no resumo.
- Uma sequência cuja última atividade ocorreu há mais de um dia UTC completo é apresentada como zero; a leitura não redefine nem grava a sequência.
- Um usuário ativo sem missões concluídas continua recebendo sua posição segundo as regras existentes do ranking, inclusive critérios de desempate.
- Credenciais ausentes, inválidas ou expiradas não permitem acesso ao resumo.
- A indisponibilidade do usuário autenticado durante a consulta segue o tratamento existente de recurso não encontrado, sem revelar dados.
- A consulta não altera progresso, registros de atividade ou estados de conquistas e não inicia recálculos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer uma consulta autenticada do resumo de aprendizagem exclusivamente para o usuário identificado pela sessão atual; o cliente MUST NOT escolher outro usuário para a consulta.
- **FR-002**: O resumo MUST conter os campos `xp`, `missionsCompleted`, `position`, `badgesUnlocked` e `currentDayStreak`; os valores MUST ser inteiros, `position` MUST ser maior ou igual a 1 e os demais MUST ser maiores ou iguais a 0. `position` MUST seguir a regra de colocação existente no ranking.
- **FR-003**: Os valores de `xp`, `missionsCompleted` e `position` MUST ser consistentes com os dados e regras apresentados no perfil e no ranking para o mesmo usuário e estado dos dados.
- **FR-004**: A quantidade `badgesUnlocked` MUST contar somente conquistas ativas do catálogo com progresso do usuário autenticado no estado desbloqueado (`done`); conquistas em andamento, não iniciadas, sem progresso ou removidas do catálogo MUST NOT ser contadas.
- **FR-005**: A sequência MUST considerar como atual uma atividade registrada na data UTC corrente ou na data UTC imediatamente anterior. Se o registro mais recente for anterior a essas datas, `currentDayStreak` MUST ser zero. A ausência de registro também MUST resultar em zero.
- **FR-006**: A consulta MUST ser somente de leitura: ela MUST NOT criar ou atualizar registros, alterar progresso, redefinir sequências armazenadas, atualizar conquistas ou disparar recálculos.
- **FR-007**: Para usuário ativo sem progresso, `xp`, `missionsCompleted`, `badgesUnlocked` e `currentDayStreak` MUST ser zero; `position` MUST refletir a regra existente de ranking para usuários ativos, inclusive participantes com zero XP.
- **FR-008**: A resposta MUST conter somente os valores necessários ao resumo, sem e-mail, credenciais, dados de auditoria ou estatísticas privadas de qualquer outro usuário.
- **FR-009**: Solicitações sem autenticação válida MUST ser recusadas. Erros de autenticação ou de usuário indisponível MUST seguir o padrão Problem Details do produto.
- **FR-010**: A consulta MUST reutilizar os critérios existentes para XP, missões concluídas e posição; MUST NOT criar regras divergentes nem alterar as regras de concessão de XP, ranking, conquistas ou registro de atividade.
- **FR-011**: A inclusão do resumo MUST preservar o funcionamento dos recursos existentes de perfil, ranking e conquistas.

### Key Entities *(include if feature involves data)*

- **Usuário**: Pessoa autenticada a quem pertencem os dados privados do resumo; a consulta é limitada à identidade atual.
- **Progresso de aprendizagem**: Registros existentes de missões concluídas que sustentam XP e quantidade de missões concluídas.
- **Conquista**: Item ativo do catálogo com progresso individual; é considerada desbloqueada quando o progresso desse usuário está concluído.
- **Sequência de atividade**: Valor de dias consecutivos associado à atividade mais recente do usuário, interpretado segundo datas UTC e sem alteração durante a consulta.
- **Posição no ranking**: Colocação calculada pelas regras globais existentes, inclusive para usuários com zero XP.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos cenários cobertos, o usuário consegue consultar em uma única resposta os cinco valores de progresso definidos, sem precisar reuni-los de áreas diferentes.
- **SC-002**: Em 100% das comparações feitas sobre o mesmo estado de dados, XP, missões concluídas e posição coincidem com os valores existentes do perfil e do ranking.
- **SC-003**: Em 100% dos cenários de ausência de progresso, sequência expirada ou conquistas não desbloqueadas, os valores apresentados seguem os critérios documentados.
- **SC-004**: Em 100% das solicitações sem autenticação válida ou que tentem acessar dados de outra pessoa, nenhum dado privado é retornado.
- **SC-005**: Em 100% das consultas verificadas, os registros de progresso, conquistas e atividade permanecem inalterados e os recursos existentes de perfil, ranking e conquistas continuam disponíveis.
- **SC-006**: Pelo menos 95% das consultas são concluídas em até 2 segundos em condições normais de uso.
- **SC-007**: Em 100% dos cenários de falha cobertos, a resposta segue o formato Problem Details adotado pelo produto.

## Assumptions

- O mecanismo atual de autenticação identifica o usuário da consulta e permanece inalterado.
- O catálogo de conquistas considera removidos os itens que já não aparecem nas consultas existentes; somente itens ativos entram na contagem.
- A atividade já registrada é a fonte de verdade. Datas são interpretadas em UTC, conforme a regra de registro vigente.
- Uma sequência com última atividade no dia UTC anterior continua atual durante o dia corrente. Após mais de um dia UTC completo sem atividade, o resumo retorna zero sem modificar o valor armazenado; o próximo registro de atividade segue a regra de reinício já existente.
- A posição segue as regras atuais do ranking, que incluem usuários ativos sem XP; a ausência de progresso não implica posição nula ou zero.
- Interface visual, histórico temporal, comparações, exportações e criação de novas métricas permanecem fora do escopo.
