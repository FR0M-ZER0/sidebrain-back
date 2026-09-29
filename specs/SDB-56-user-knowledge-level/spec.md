# Feature Specification: Nível de Conhecimento do Usuário

**Feature Branch**: `feat/sdb-56-criar-endpoint-para-gerenciamento-do-nivel-de-conhecimento-do-usuario`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "SDB-56 — Criar endpoint para gerenciamento do nível de conhecimento do usuário"

## Clarifications

### Session 2026-09-23

- Q: Mesmo ao pular a avaliação, o usuário deve informar o assunto para que o nível `beginner` fique vinculado ao contexto correto? → A: Exigir `subject` mesmo quando `skip=true`.
- Q: Quando uma avaliação é iniciada, qual identificador deve continuar valendo depois que as perguntas forem geradas? → A: O sistema cria o `assessment_id` ao aceitar a solicitação e o reutiliza durante todo o fluxo.
- Q: Como o sistema deve obter a resposta correta de cada pergunta sem expô-la ao usuário? → A: O fluxo oficial gera exatamente uma alternativa correta por pergunta; o sistema a persiste internamente e a remove das respostas públicas.
- Q: O que deve acontecer se o usuário iniciar outra avaliação com o mesmo contexto (`subject`, `objective` e `skip`) enquanto uma anterior ainda estiver `pending` ou `generated`? → A: Retornar a avaliação ativa existente e o mesmo `assessment_id`.
- Q: Qual tabela de corte deve transformar os cinco acertos nos níveis `beginner`, `intermediate`, `advanced` e `pro`? → A: `0–1 beginner`, `2–3 intermediate`, `4 advanced`, `5 pro`.
- Q: Como evoluir o contrato da task Celery sem quebrar mensagens e consumidores existentes? → A: A task manterá o nome registrado e aceitará temporariamente os contratos v1 e v2. Chamadas v2 usarão argumentos nomeados, `contract_version=2` e `assessment_id`; o contrato v1 será removido somente após a atualização dos produtores e a drenagem das mensagens antigas do broker.
- Q: Qual é a política exata de backoff? → A: Após a tentativa inicial, serão permitidas três novas tentativas, com esperas de 1, 2 e 4 segundos, sem jitter.
- Q: Quais informações podem ser retornadas ao proprietário? → A: `subject` e `objective`, quando presente, podem ser retornados ao proprietário; prompt, resposta bruta, gabarito e códigos internos nunca são públicos.
- Q: Qual código pode ser exposto quando a geração falhar? → A: A API poderá retornar somente `generation_failed` ou `invalid_generation_result`; exceções e códigos do provider permanecem internos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar avaliação de conhecimento (Priority: P1)

Como usuário autenticado, quero iniciar uma avaliação sobre o assunto que desejo aprender para receber perguntas capazes de medir meu conhecimento prévio.

**Why this priority**: Sem uma avaliação identificável e vinculada ao usuário, não há base confiável para receber respostas nem determinar o nível inicial da futura trilha.

**Independent Test**: Iniciar uma avaliação com assunto e objetivo válidos, acompanhar seu processamento e verificar que ela fica disponível com exatamente cinco perguntas de quatro alternativas, sem expor o gabarito ou um nível ainda não calculado.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado e um assunto válido, **When** ele inicia uma avaliação, **Then** o sistema cria uma avaliação em nome desse usuário, retorna seu `assessment_id` canônico e preserva esse identificador durante a preparação das perguntas pelo fluxo oficial já existente.
2. **Given** uma avaliação cuja preparação foi concluída com sucesso, **When** o usuário consulta seu estado, **Then** o sistema apresenta exatamente cinco perguntas com quatro alternativas cada, status `generated` e nenhum nível definitivo ou indicação das alternativas corretas.
3. **Given** uma avaliação em processamento, **When** o usuário consulta seu estado, **Then** o sistema informa que ela ainda não está pronta sem retornar perguntas incompletas.
4. **Given** uma falha definitiva na preparação das perguntas, **When** o usuário consulta a avaliação, **Then** o sistema informa a falha sem disponibilizar perguntas ou resultado parcial.
5. **Given** uma avaliação `pending` ou `generated` para o mesmo usuário, assunto, objetivo e opção de pular, **When** o usuário tenta iniciar novamente a mesma avaliação, **Then** o sistema retorna a avaliação ativa e o mesmo `assessment_id` sem iniciar outra preparação.

---

### User Story 2 - Responder e obter o nível calculado (Priority: P1)

Como usuário com uma avaliação pronta, quero enviar uma resposta para cada pergunta e receber meu nível calculado pelo sistema para iniciar uma trilha adequada ao meu conhecimento.

**Why this priority**: A correção confiável e a classificação são o objetivo central da feature e completam a etapa que ficou fora do escopo da SDB-53.

**Independent Test**: Preparar avaliações próprias com diferentes quantidades de acertos, enviar cinco respostas válidas e verificar que o resultado segue integralmente a tabela de corte, sem aceitar nível, pontuação ou gabarito informados pelo cliente.

**Acceptance Scenarios**:

1. **Given** uma avaliação própria no status `generated`, **When** o usuário envia exatamente uma alternativa válida para cada uma das cinco perguntas, **Then** o sistema corrige as respostas, registra a pontuação e retorna o nível correspondente.
2. **Given** uma submissão com zero ou um acerto, **When** ela é corrigida, **Then** o nível resultante é `beginner`.
3. **Given** uma submissão com dois ou três acertos, **When** ela é corrigida, **Then** o nível resultante é `intermediate`.
4. **Given** uma submissão com quatro acertos, **When** ela é corrigida, **Then** o nível resultante é `advanced`.
5. **Given** uma submissão com cinco acertos, **When** ela é corrigida, **Then** o nível resultante é `pro`.
6. **Given** uma submissão inválida, **When** ela contém quantidade diferente de cinco respostas, perguntas repetidas, identificadores desconhecidos, alternativas de outra pergunta ou campos reservados ao sistema, **Then** o sistema rejeita toda a submissão e não define o nível.

---

### User Story 3 - Prosseguir sem responder à avaliação (Priority: P1)

Como usuário que ainda não possui conhecimento sobre o assunto, quero pular a avaliação para receber o nível inicial e prosseguir sem responder perguntas.

**Why this priority**: O caminho de início direto evita uma etapa desnecessária para iniciantes e faz parte do contrato oficial da avaliação já existente.

**Independent Test**: Iniciar uma avaliação com assunto válido e a opção de pular e verificar que o resultado persistido é `beginner`, não contém perguntas, não exige respostas e não aciona a geração externa de conteúdo.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado que informa um assunto válido e opta por pular a avaliação, **When** a solicitação é processada, **Then** o sistema conclui a avaliação com status `skipped`, nível `beginner` e nenhuma pergunta.
2. **Given** uma avaliação pulada, **When** o usuário tenta submeter respostas, **Then** o sistema rejeita a operação e preserva o nível `beginner` já definido.
3. **Given** a opção de pular habilitada, **When** a avaliação é processada, **Then** nenhum serviço externo de geração de perguntas é acionado.

---

### User Story 4 - Consultar o resultado da avaliação (Priority: P2)

Como usuário autenticado, quero consultar o estado e o nível de uma avaliação própria para reutilizar o resultado no fluxo de criação da minha trilha.

**Why this priority**: A consulta torna o processamento assíncrono acompanhável e permite consumir o nível persistido sem transformar uma classificação específica de assunto em um atributo global do usuário.

**Independent Test**: Consultar avaliações próprias nos estados de processamento, gerada, pulada, concluída e falha, verificando a representação adequada de cada estado e a negação uniforme de acesso a avaliações alheias.

**Acceptance Scenarios**:

1. **Given** uma avaliação própria concluída, **When** o usuário a consulta, **Then** o sistema retorna assunto, estado, pontuação e nível persistidos.
2. **Given** uma avaliação própria gerada e ainda não respondida, **When** o usuário a consulta, **Then** o sistema retorna as perguntas sem gabarito, pontuação ou nível definitivo.
3. **Given** uma avaliação inexistente ou pertencente a outro usuário, **When** o usuário tenta consultá-la, **Then** o sistema informa que o recurso não foi encontrado sem revelar sua existência ou propriedade.

### Edge Cases

- Assunto ausente, vazio ou formado somente por espaços deve ser rejeitado em qualquer avaliação, inclusive quando ela for pulada; objetivo ausente continua válido.
- Campos não previstos, inclusive `user_id`, `level`, `score`, resposta correta ou estado, devem ser rejeitados nas entradas do usuário.
- A identidade usada na avaliação deve vir exclusivamente do contexto autenticado, nunca do conteúdo enviado pelo usuário.
- Uma avaliação gerada deve possuir cinco perguntas distintas, cada uma com quatro alternativas de identificadores distintos e exatamente uma alternativa correta definida internamente; qualquer violação torna a preparação inteira inválida.
- O mesmo identificador de pergunta não pode aparecer mais de uma vez na submissão, ainda que a quantidade total de respostas seja cinco.
- Uma alternativa existente, mas pertencente a outra pergunta ou avaliação, deve ser tratada como inválida.
- Avaliações em processamento, com falha, puladas ou já concluídas não podem receber uma submissão de respostas.
- Uma segunda submissão para uma avaliação já concluída deve ser rejeitada sem alterar pontuação, nível ou respostas registradas.
- Solicitações repetidas com o mesmo usuário, assunto, objetivo e opção de pular devem reutilizar a avaliação `pending` ou `generated`; avaliações em estado terminal não impedem uma nova avaliação.
- Uma avaliação própria pode ser consultada durante o processamento, mas nunca deve expor conteúdo parcial.
- Um identificador diferente eventualmente recebido durante a preparação não pode substituir o `assessment_id` canônico criado na aceitação da solicitação.
- Falhas temporárias de conexão, tempo limite ou limitação de uso podem provocar novas tentativas limitadas; falhas de validação, autenticação ou conteúdo inválido são definitivas.
- Logs e mensagens de erro não podem expor prompt, resposta bruta do gerador, gabarito, credenciais ou conteúdo protegido de outro usuário.
- O fluxo não deve criar nem alterar trilhas, etapas, lições ou missões.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que um usuário autenticado inicie uma avaliação informando `subject`, `objective` opcional e `skip`.
- **FR-002**: O sistema MUST obter a identidade da pessoa avaliada exclusivamente do contexto autenticado e MUST NOT aceitar `user_id` no conteúdo enviado pelo usuário.
- **FR-003**: O assunto normalizado MUST ser obrigatório em toda avaliação, inclusive quando `skip=true`, e conter de 1 a 255 caracteres; o objetivo, quando informado, MUST conter de 1 a 1000 caracteres após normalização.
- **FR-004**: O sistema MUST criar o `assessment_id` canônico ao aceitar cada solicitação, retorná-lo imediatamente, preservá-lo durante todo o ciclo de vida e permitir a consulta do estado enquanto a avaliação é processada; nenhum identificador posterior pode substituí-lo.
- **FR-005**: A preparação MUST reutilizar exclusivamente o fluxo oficial de avaliação criado pela SDB-53, fornecendo a identidade autenticada, o assunto, o objetivo opcional e a opção de pular; nenhum fluxo alternativo ou duplicado de geração de perguntas é permitido.
- **FR-006**: Uma avaliação gerada com sucesso MUST conter exatamente cinco perguntas, cada uma com exatamente quatro alternativas e exatamente uma alternativa correta definida pelo fluxo oficial, status `generated` e nível ausente até a correção das respostas.
- **FR-007**: O sistema MUST persistir sob seu controle a alternativa correta recebida para cada pergunta e MUST removê-la de todas as representações destinadas ao usuário; uma pergunta sem alternativa correta ou com mais de uma MUST invalidar toda a avaliação.
- **FR-008**: O sistema MUST persistir a avaliação, suas perguntas, alternativas e dados necessários à correção, vinculando-os ao usuário autenticado e ao assunto avaliado antes de aceitar respostas.
- **FR-009**: O sistema MUST permitir ao proprietário consultar uma avaliação pelo identificador e obter uma representação coerente com os estados `pending`, `generated`, `skipped`, `completed` ou `failed`.
- **FR-010**: Avaliações inexistentes ou pertencentes a outro usuário MUST ser apresentadas como não encontradas, sem revelar existência, propriedade, conteúdo ou resultado.
- **FR-011**: O sistema MUST aceitar respostas somente para uma avaliação própria no estado `generated` e MUST exigir exatamente cinco respostas, uma para cada pergunta da avaliação.
- **FR-012**: Cada resposta MUST identificar uma pergunta da avaliação e uma de suas alternativas; perguntas repetidas, desconhecidas ou de outra avaliação e alternativas desconhecidas ou de outra pergunta MUST invalidar toda a submissão.
- **FR-013**: O sistema MUST rejeitar campos não previstos em todas as entradas e, em especial, MUST NOT aceitar nível, pontuação, gabarito, estado ou identidade do usuário informados pelo cliente.
- **FR-014**: O sistema MUST corrigir as respostas usando exclusivamente o gabarito controlado pelo servidor e calcular uma pontuação inteira entre zero e cinco.
- **FR-015**: O sistema MUST classificar zero ou um acerto como `beginner`, dois ou três acertos como `intermediate`, quatro acertos como `advanced` e cinco acertos como `pro`.
- **FR-016**: Após uma correção válida, o sistema MUST persistir as respostas escolhidas, a pontuação, o nível, o momento da conclusão e o estado `completed` como uma única operação, sem resultado parcial.
- **FR-017**: A primeira submissão válida MUST encerrar a avaliação; novas submissões MUST ser rejeitadas e MUST NOT alterar o resultado persistido.
- **FR-018**: Quando `skip=true`, o sistema MUST concluir a avaliação com status `skipped`, nível `beginner` e lista de perguntas vazia, sem exigir respostas e sem solicitar geração externa; o assunto permanece obrigatório.
- **FR-019**: O nível MUST pertencer ao resultado da avaliação e ao respectivo assunto; esta feature MUST NOT criar nem atualizar um nível global no perfil do usuário.
- **FR-020**: Falhas de conexão, timeout ou rate limit durante a preparação MUST permitir exatamente três novas tentativas após a tentativa inicial, com esperas de 1, 2 e 4 segundos, sem jitter. Falhas de autenticação, validação ou conteúdo inválido MUST encerrar o processamento sem retry.
- **FR-021**: Resposta de geração inválida, incompleta, com quantidade incorreta de perguntas ou alternativas ou sem exatamente uma alternativa correta por pergunta MUST tornar a avaliação `failed` sem disponibilizar ou persistir conteúdo parcial como avaliação válida.
- **FR-022**: Erros de validação MUST identificar entradas inválidas sem alterar a avaliação; recursos inexistentes ou inacessíveis MUST permanecer indistinguíveis; conflitos de estado MUST preservar o resultado anterior.
- **FR-023**: Todas as falhas públicas MUST seguir o formato de erros vigente do produto. Avaliações no estado `failed` MAY expor somente os códigos públicos `generation_failed` ou `invalid_generation_result`. A API MUST NOT expor exceções, códigos do provider, gabarito, prompts, respostas brutas, credenciais, detalhes internos ou dados de outro usuário.
- **FR-024**: O sistema MUST registrar informações suficientes para distinguir sucesso, falha definitiva e nova tentativa, sem registrar prompt, resposta bruta do gerador, credenciais ou gabarito.
- **FR-025**: Os contratos públicos MUST usar nomes de negócio, rejeitar campos extras e MUST NOT expor nomes físicos de armazenamento ou metadados internos.
- **FR-026**: Esta feature MUST limitar-se à preparação, correção, persistência e consulta da avaliação e do nível; criar ou alterar Track, Step, Lesson, Mission ou seus conteúdos fica fora do escopo.
- **FR-027**: Enquanto existir uma avaliação `pending` ou `generated` para o mesmo usuário e o mesmo contexto normalizado de `subject`, `objective` e `skip`, uma nova solicitação MUST retornar essa avaliação e o mesmo `assessment_id` sem iniciar outra preparação; avaliações `skipped`, `completed` ou `failed` não impedem a criação de uma nova avaliação.

### Key Entities

- **Avaliação de Conhecimento**: Execução pertencente a um usuário e contextualizada por assunto e objetivo opcional; possui um `assessment_id` canônico criado na aceitação e preservado em todo o ciclo de vida, além da opção de pular, estado e momentos relevantes do fluxo.
- **Pergunta da Avaliação**: Questão pertencente a uma única avaliação, com enunciado, quatro alternativas e referência interna à alternativa correta, nunca exposta ao usuário.
- **Alternativa da Avaliação**: Opção identificada dentro de uma pergunta; somente uma alternativa por pergunta compõe o gabarito controlado pelo sistema.
- **Submissão da Avaliação**: Conjunto terminal de cinco escolhas do usuário, com uma resposta para cada pergunta da avaliação gerada.
- **Resultado da Avaliação**: Pontuação de zero a cinco e nível `beginner`, `intermediate`, `advanced` ou `pro`, vinculados à avaliação e ao assunto; avaliações puladas possuem nível `beginner` sem pontuação nem submissão.
- **Usuário**: Pessoa autenticada proprietária da avaliação; pode iniciar, responder e consultar apenas avaliações próprias.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das avaliações geradas com sucesso reutilizam o fluxo oficial existente, possuem exatamente cinco perguntas válidas com quatro alternativas e uma resposta correta interna cada e não expõem o gabarito.
- **SC-002**: 100% das submissões válidas produzem a pontuação e o nível previstos na tabela de corte: `0–1 beginner`, `2–3 intermediate`, `4 advanced` e `5 pro`.
- **SC-003**: 100% das submissões com quantidade incorreta, identificadores inválidos, vínculos incompatíveis, perguntas repetidas ou campos controlados pelo sistema são rejeitadas sem definir ou alterar um nível.
- **SC-004**: 100% das avaliações puladas resultam em `beginner`, não contêm perguntas, não exigem respostas e não solicitam geração externa.
- **SC-005**: 100% das tentativas cobertas de consultar ou responder avaliações alheias são recusadas sem revelar existência, propriedade, conteúdo, gabarito ou resultado.
- **SC-006**: 100% das falhas definitivas de preparação deixam a avaliação sem conteúdo parcial utilizável, enquanto falhas temporárias respeitam o limite de três novas tentativas.
- **SC-007**: Em ambiente equivalente ao de produção, considerando pelo menos 100 solicitações válidas e concorrência máxima de 10 requisições, o percentil 95 do tempo entre o recebimento do POST e a resposta com `assessment_id` MUST ser de até 2 segundos.
- **SC-008**: Em ambiente com PostgreSQL, Redis e worker Celery reais, usando provider determinístico que responda em até 20 segundos e sem retry, o percentil 95 de pelo menos 100 avaliações MUST alcançar `generated` ou `skipped` em até 30 segundos.
- **SC-010**: Nenhum cenário de aceite cria ou altera trilhas, etapas, lições ou missões.
- **SC-011**: 100% das solicitações repetidas para um contexto com avaliação `pending` ou `generated` retornam o mesmo `assessment_id` e não iniciam preparação duplicada.

## Métricas pós-entrega não bloqueantes

- **PM-001**: Em estudo com pelo menos 10 participantes representativos, buscar que 90% consigam iniciar, acompanhar e concluir ou pular a avaliação na primeira tentativa.

## Assumptions

- O mecanismo de autenticação vigente fornece uma identidade confiável do usuário e será reutilizado sem criar uma nova forma de login ou autorização.
- A SDB-53 permanece como dependência obrigatória e como fonte exclusiva da preparação de perguntas; esta feature amplia o fluxo para preservar o gabarito, persistir a avaliação e calcular o resultado.
- O nível representa o conhecimento do usuário sobre o assunto daquela avaliação. Um usuário pode possuir avaliações e níveis diferentes para assuntos distintos, portanto o perfil global não receberá um único campo de nível.
- A consulta do nível ocorrerá no contexto da avaliação identificada; uma listagem de histórico ou uma operação separada de “nível global atual” fica fora deste escopo.
- A avaliação aceita somente uma submissão terminal. Reavaliação exige iniciar uma nova avaliação após `skipped`, `completed` ou `failed`, e edição de respostas já enviadas fica fora deste escopo.
- O resultado persistido poderá ser consumido posteriormente pelo fluxo de geração de trilhas, mas esse consumo e qualquer alteração em entidades de trilha ficam fora desta feature.
- A retenção e a remoção de avaliações seguirão a política geral de dados do produto; endpoints de exclusão ou restauração não fazem parte desta entrega.
