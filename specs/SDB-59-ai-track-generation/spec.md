# Feature Specification: Geração de Trilhas com IA

**Feature Branch**: `SDB-59-ai-track-generation`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "SDB-59 - Criar funcionalidade para geração de trilha"

## User Scenarios & Testing

### User Story 1 - Gerar a estrutura de uma trilha personalizada (Priority: P1)

Como usuário que solicitou uma trilha personalizada, quero que o sistema interprete meu objetivo, tópico, nível de conhecimento e respostas de avaliação para criar uma progressão de aprendizagem coerente.

**Why this priority**: A estrutura é a base necessária para representar a trilha e orientar a geração gradual do conteúdo.

**Independent Test**: Fornecer um conjunto válido de contexto de aprendizagem, executar a solicitação assíncrona e verificar que a trilha e todas as etapas previstas são criadas na ordem e nos níveis esperados.

**Acceptance Scenarios**:

1. **Given** um contexto válido de objetivo, tópico e nível de conhecimento, **When** a geração é executada, **Then** o sistema cria uma trilha personalizada com título, descrição e todas as etapas definidas pela estratégia de progressão.
2. **Given** respostas de uma avaliação de conhecimento, **When** a geração é executada, **Then** essas respostas são consideradas na estrutura e no conteúdo gerado.
3. **Given** uma resposta estruturada da IA com etapas inválidas ou incompletas, **When** o sistema valida o resultado, **Then** rejeita a geração e não persiste uma trilha parcial.

### User Story 2 - Disponibilizar o conteúdo inicial da trilha (Priority: P1)

Como usuário que inicia uma trilha, quero receber conteúdo apenas da primeira etapa para começar a estudar sem gerar antecipadamente material que ainda não utilizarei.

**Why this priority**: Entregar o primeiro conteúdo fornece valor imediato e reduz desperdício de geração e armazenamento.

**Independent Test**: Executar uma geração válida e verificar que a primeira etapa contém lições ordenadas, quizzes relacionados e missão quando aplicável, sem conteúdo detalhado nas etapas seguintes.

**Acceptance Scenarios**:

1. **Given** uma trilha com etapas geradas, **When** a primeira etapa é materializada, **Then** ela contém lições com título, texto e posição sequencial.
2. **Given** lições geradas para a primeira etapa, **When** o resultado é persistido, **Then** cada lição possui o quiz correspondente conforme a estratégia da trilha.
3. **Given** uma estratégia que prevê missão para a primeira etapa, **When** o conteúdo é gerado, **Then** a missão contém título, dificuldade, recompensa, critério e valor do critério.
4. **Given** uma primeira etapa para a qual não se aplica missão, **When** o conteúdo é gerado, **Then** a trilha é criada sem missão nessa etapa.

### User Story 3 - Preservar etapas futuras para geração posterior (Priority: P1)

Como produto, quero registrar as etapas futuras apenas como estrutura para que seu conteúdo seja gerado posteriormente com base no progresso real do usuário.

**Why this priority**: Evitar geração antecipada reduz consumo de tokens e mantém o conteúdo futuro contextualizado ao uso efetivo da trilha.

**Independent Test**: Gerar uma trilha com pelo menos duas etapas e confirmar que somente a primeira possui lições, quizzes e missão; as demais permanecem disponíveis para uma geração posterior.

**Acceptance Scenarios**:

1. **Given** etapas posteriores à primeira, **When** a geração inicial termina, **Then** essas etapas existem sem lições, quizzes ou missões associadas.
2. **Given** uma geração inicial em andamento, **When** a IA recebe as instruções de geração, **Then** o pedido delimita explicitamente conteúdo detalhado somente para a primeira etapa.
3. **Given** uma geração inicial, **When** a persistência ocorre, **Then** não são criados registros dependentes de interação do usuário, como respostas, feedbacks, progresso de missão ou arquivos de lição.

### Edge Cases

- O nível de conhecimento ou as respostas de avaliação podem estar ausentes; nesse caso, a geração deve usar somente o contexto disponível e ainda validar a estrutura resultante.
- A IA pode retornar etapas fora de ordem, níveis duplicados indevidos, posições inválidas ou conteúdo posterior à primeira etapa; o resultado deve ser rejeitado antes da persistência.
- A primeira etapa pode não ter missão quando a estratégia de geração indicar que ela não é aplicável.
- Uma resposta vazia, malformada ou incompatível com os dados esperados não deve criar registros parciais.
- Falhas na chamada de IA, na validação ou na persistência devem deixar a trilha sem alterações incompletas.
- Títulos, textos, níveis, dificuldades, critérios e valores fora dos limites do domínio devem ser rejeitados com erro tratável pelo fluxo que acompanha a geração.
- Reexecuções da mesma solicitação não devem gerar registros duplicados sem que o fluxo de acompanhamento determine explicitamente uma nova geração.

## Requirements

### Functional Requirements

- **FR-001**: O sistema MUST executar a geração de uma trilha personalizada de forma assíncrona por meio do mecanismo de tarefas vigente do produto.
- **FR-002**: A geração MUST receber o objetivo do usuário, o tópico da trilha, o nível de conhecimento identificado e, quando existentes, as respostas da avaliação de conhecimento.
- **FR-003**: O sistema MUST solicitar e validar uma estrutura completa de etapas, respeitando a estratégia de progressão e os níveis disponíveis no domínio.
- **FR-004**: O resultado validado MUST conter uma trilha com título e descrição, além da coleção ordenada de etapas com nível e título.
- **FR-005**: O sistema MUST gerar conteúdo detalhado somente para a primeira etapa da trilha na execução inicial.
- **FR-006**: O conteúdo inicial MUST incluir lições com título, texto e posição, mantendo a ordem definida pela posição da lição.
- **FR-007**: O sistema MUST gerar quizzes para as lições da primeira etapa conforme a estratégia de geração, contendo ao menos a pergunta definida pelo domínio.
- **FR-008**: O sistema MUST gerar a missão da primeira etapa quando aplicável, incluindo título, dificuldade, recompensa de experiência, critério e valor do critério.
- **FR-009**: As etapas posteriores MUST ser persistidas sem lições, quizzes ou missões; seu conteúdo será responsabilidade de uma geração posterior fora do escopo desta feature.
- **FR-010**: A geração inicial MUST NOT criar respostas, feedbacks, progresso de missão ou arquivos de lição, pois esses registros dependem da interação do usuário ou de outras funcionalidades.
- **FR-011**: A resposta da IA MUST ser estruturada e validada antes de qualquer persistência, rejeitando campos ausentes, inválidos, fora de domínio ou conteúdo indevido em etapas posteriores.
- **FR-012**: Os modelos internos de geração MUST representar trilha, etapas, conteúdo inicial, lições, quizzes e missão com nomes semânticos, sem expor identificadores físicos de persistência.
- **FR-013**: A persistência MUST ser transacional, revertendo todos os registros criados quando ocorrer falha na validação final ou em qualquer etapa da gravação.
- **FR-014**: A execução MUST disponibilizar ao fluxo de acompanhamento o resultado da task, incluindo sucesso ou falha tratável e, quando concluída, a identificação da trilha gerada.
- **FR-015**: O escopo desta feature MUST permanecer restrito à task assíncrona, geração por IA, validação, schemas internos e persistência; nenhum endpoint novo deve ser implementado.
- **FR-016**: O pedido enviado à IA MUST declarar que a estrutura completa das etapas deve ser gerada, mas que o conteúdo detalhado deve ser produzido somente para a primeira etapa.

### Key Entities

- **Trilha**: Percurso personalizado com título, descrição e uma sequência de etapas.
- **Etapa**: Nível ordenado da trilha, inicialmente representado por nível e título; somente a primeira recebe conteúdo na geração inicial.
- **Lição**: Conteúdo textual ordenado da primeira etapa.
- **Quiz**: Pergunta associada a uma lição da primeira etapa.
- **Missão**: Atividade opcional da primeira etapa, com dificuldade, recompensa e critério de conclusão.
- **Contexto de aprendizagem**: Objetivo, tópico, nível identificado e respostas de avaliação usados para orientar a personalização.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% das gerações válidas persistem uma trilha com todas as etapas previstas e na ordem definida pela estratégia de progressão.
- **SC-002**: 100% das trilhas geradas inicialmente possuem conteúdo detalhado somente na primeira etapa; nenhuma etapa posterior possui lição, quiz ou missão nessa execução.
- **SC-003**: 100% dos resultados persistidos têm suas lições iniciais ordenadas por posição e seus quizzes associados à lição correta.
- **SC-004**: 100% das falhas de validação, geração ou persistência deixam zero registros parciais da trilha criada.
- **SC-005**: 100% das gerações iniciais não criam registros de resposta, feedback, progresso de missão ou arquivo de lição.
- **SC-006**: Pelo menos 95% das solicitações válidas concluem a geração ou comunicam uma falha tratável ao fluxo de acompanhamento sem intervenção manual.
- **SC-007**: Em uma avaliação com usuários de teste, pelo menos 90% identificam a primeira etapa como pronta para iniciar e as etapas seguintes como progressão futura.

## Assumptions

- O fluxo de solicitação e acompanhamento da task assíncrona já existe ou será implementado em escopo próprio; esta feature não cria endpoints.
- O mecanismo de execução assíncrona, o cliente de IA e a sessão de persistência existentes serão reutilizados conforme a arquitetura do produto.
- Os enums e regras de domínio vigentes definem os níveis de etapa, dificuldades, critérios e limites de campos.
- A resposta da IA será obtida em formato estruturado, mas ainda precisará ser validada contra os schemas internos antes da persistência.
- A geração de conteúdo das etapas posteriores será implementada em uma task separada, usando a etapa existente e o progresso do usuário.
- A reexecução e a idempotência serão coordenadas pelo fluxo de acompanhamento da task e pelas regras de persistência existentes.
- Os erros seguirão o formato de erro padronizado do produto e não revelarão detalhes internos do provedor de IA ou da persistência.
