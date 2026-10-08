# Feature Specification: Memória determinística da IA

**Feature Branch**: `SDB-92-ai-memory`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "SDB-92 - Criar gerenciamento da memória da IA para economizar tokens"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reutilizar conteúdo equivalente entre usuários (Priority: P1)

Como usuário que solicita uma trilha ou avaliação de conhecimento, quero receber conteúdo já validado quando outro usuário tiver feito uma solicitação equivalente, para obter uma resposta mais rápida e evitar chamadas desnecessárias à IA.

**Why this priority**: A redução de chamadas é o principal valor da feature e deve preservar a independência dos dados de cada usuário.

**Independent Test**: Criar uma solicitação válida, concluir sua geração e repetir uma solicitação semanticamente equivalente com outro usuário; confirmar que o provedor é chamado apenas uma vez, o conteúdo é reaproveitado e o segundo usuário recebe novos registros próprios.

**Acceptance Scenarios**:

1. **Given** uma trilha validada em cache para um contexto, nível, versão de prompt e modelo específicos, **When** outro usuário solicita o mesmo contexto, **Then** o sistema reutiliza o conteúdo sem chamar o provedor e informa `source=cache`.
2. **Given** uma avaliação validada em cache para um assunto e objetivo equivalentes, **When** outro usuário solicita a avaliação, **Then** o sistema cria uma avaliação própria com as mesmas perguntas e alternativas, sem compartilhar registros ou progresso.
3. **Given** solicitações com o mesmo contexto textual e níveis de conhecimento diferentes, **When** são processadas, **Then** cada nível produz uma entrada distinta e não reutiliza conteúdo do outro nível.

---

### User Story 2 - Reconhecer contextos equivalentes de forma determinística (Priority: P1)

Como responsável pelo produto, quero que variações previsíveis de escrita sejam convertidas em um contexto canônico, para que diferenças de caixa, acentos, espaços, pontuação e aliases curados não gerem conteúdo duplicado.

**Why this priority**: Sem uma chave determinística e versionada, o cache não é confiável e pode servir conteúdo inadequado ou deixar de economizar chamadas.

**Independent Test**: Aplicar a normalização a entradas equivalentes e verificar os valores canônicos e fingerprints produzidos, incluindo o alias `ingles` para `lingua inglesa`.

**Acceptance Scenarios**:

1. **Given** textos com acentos, caixa diferente, espaços repetidos e pontuação periférica, **When** são normalizados, **Then** produzem o mesmo texto canônico.
2. **Given** o tópico `INGLÊS` e o alias curado `ingles -> lingua inglesa`, **When** o fingerprint é calculado, **Then** o tópico canônico é `lingua inglesa`.
3. **Given** uma geração criada com a versão anterior do fingerprint, **When** novas solicitações são processadas, **Then** o sistema não confunde a entrada legada com a versão atual nem reescreve históricos sem migração explícita.

---

### User Story 3 - Preservar integridade durante concorrência e falhas (Priority: P1)

Como responsável pela confiabilidade do produto, quero que solicitações simultâneas e falhas do cache não causem duplicidade, perda de dados ou indisponibilidade da geração, para manter o fluxo atual seguro.

**Why this priority**: A memória é uma otimização; ela não pode introduzir conteúdo parcial, múltiplas chamadas concorrentes ou erro para usuários quando o cache estiver indisponível.

**Independent Test**: Executar solicitações concorrentes para o mesmo fingerprint e simular indisponibilidade, conteúdo inválido e erro de persistência; confirmar uma única geração válida ou fallback para o fluxo normal, sem registros parciais.

**Acceptance Scenarios**:

1. **Given** duas solicitações simultâneas para o mesmo fingerprint sem entrada concluída, **When** ambas tentam gerar conteúdo, **Then** apenas uma chama o provedor e a outra aguarda ou reutiliza o resultado sem duplicar cache ou conteúdo do usuário.
2. **Given** uma falha durante a consulta ou gravação do cache, **When** uma solicitação é processada, **Then** a geração segue pelo fluxo normal de IA e informa `source=ai`, sem transformar a falha de otimização em erro público.
3. **Given** conteúdo inválido ou uma falha de persistência durante a geração, **When** a operação termina, **Then** nenhum conteúdo inválido ou parcial é disponibilizado no cache ou para o usuário.
4. **Given** a memória desabilitada por configuração operacional, **When** uma solicitação é processada, **Then** o comportamento retorna ao fluxo de geração por IA sem exigir nova versão do cliente.

### Edge Cases

- Entradas vazias, apenas com espaços ou com pontuação sem conteúdo devem ser rejeitadas pelas validações existentes antes do fingerprint.
- A normalização deve tratar Unicode, acentos combinados e sequências de espaços de forma consistente.
- Aliases devem ser aplicados somente após a normalização e devem ser únicos; aliases desconhecidos não podem ser inferidos probabilisticamente.
- Alteração de modelo ou versão de prompt deve produzir fingerprint novo e nunca servir conteúdo gerado sob contexto de versão anterior.
- Conteúdo cacheado é imutável; a ausência, corrupção ou incompatibilidade de uma entrada deve resultar em miss e fallback para geração.
- Clonagem não pode copiar respostas, feedbacks, progresso de missões, progresso de badges, logins ou sequência diária.
- O lock de concorrência deve expirar e não pode impedir novas gerações após falha ou encerramento inesperado.
- Registros legados continuam consultáveis conforme o contrato atual; não devem ser recalculados em massa sem migração explícita.
- Logs e métricas não devem conter conteúdo integral gerado, tokens, e-mails ou outras informações sensíveis.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST normalizar deterministicamente objetivo, tópico e assunto aplicáveis usando trim, colapso de espaços, casefold, remoção de diacríticos via normalização Unicode e normalização de pontuação.
- **FR-002**: O sistema MUST consultar aliases curados após a normalização e MUST converter aliases conhecidos para seu tópico canônico antes de calcular o fingerprint.
- **FR-003**: O sistema MUST manter aliases normalizados, únicos e versionáveis, com uma carga inicial curada; a criação e alteração por endpoint público estão fora do escopo desta feature.
- **FR-004**: O sistema MUST calcular fingerprints versionados com o contexto canônico, nível de conhecimento, respostas de avaliação normalizadas quando aplicável, versão do prompt e modelo utilizado.
- **FR-005**: O sistema MUST manter fingerprints legados válidos e MUST NOT recalculá-los ou substituí-los em massa sem uma migração explícita.
- **FR-006**: O sistema MUST armazenar globalmente apenas conteúdo gerado e validado, associado ao fingerprint, ao tipo de conteúdo, à versão do prompt, ao modelo e ao estado de sucesso.
- **FR-007**: O sistema MUST reutilizar um cache de trilha validado entre usuários e criar novos agregados com novos identificadores e ownership do usuário atual.
- **FR-008**: O sistema MUST reutilizar um payload de avaliação validado entre usuários e criar novas perguntas e alternativas vinculadas ao novo assessment.
- **FR-009**: A clonagem MUST copiar somente o template ou payload validado e MUST iniciar vazios todos os dados de progresso, respostas, feedbacks, logins, badges e sequência diária do novo usuário.
- **FR-010**: O sistema MUST impedir chamadas duplicadas ao provedor para o mesmo fingerprint durante gerações concorrentes, usando exclusão mútua de curta duração e uma garantia persistente de unicidade.
- **FR-011**: O sistema MUST tratar conflitos de concorrência sem duplicar cache, trilhas, avaliações, perguntas, alternativas, lessons, quizzes ou missions.
- **FR-012**: O sistema MUST continuar a geração pelo fluxo de IA quando o lookup, lock ou persistência do cache falhar, salvo quando o conteúdo gerado for inválido ou a persistência do resultado do usuário falhar.
- **FR-013**: O sistema MUST rejeitar conteúdo inválido antes de inseri-lo no cache e MUST desfazer integralmente a persistência de uma geração que falhar no meio.
- **FR-014**: O sistema MUST expor `source` com os valores `ai` ou `cache` no progresso de geração, inclusive no evento SSE, e no detalhe de avaliação, de forma aditiva e compatível com clientes existentes.
- **FR-015**: O sistema MUST registrar métricas ou logs estruturados de hits, misses e chamadas evitadas, incluindo fingerprint, tipo e origem, sem conteúdo integral ou dados pessoais.
- **FR-016**: O sistema MUST considerar entradas de cache imutáveis; mudança de modelo ou `prompt_version` deve invalidar logicamente o reuso por meio de novo fingerprint, sem depender de TTL.
- **FR-017**: O sistema MUST permitir desabilitar a memória por configuração operacional, retornando ao fluxo de geração por IA sem mudança de contrato do cliente.
- **FR-018**: O sistema MUST retornar erros públicos no formato Problem Details e MUST manter os endpoints existentes, sem criar endpoint público novo nesta feature.
- **FR-019**: O sistema MUST cobrir normalização, aliases, determinismo entre usuários, separação de progresso, concorrência, fallback, invalidação por versão e compatibilidade dos campos aditivos com testes apropriados.

### Key Entities

- **TopicAlias**: relação global entre um alias normalizado e seu tópico canônico normalizado, usada para curadoria determinística de equivalências.
- **GenerationCache**: entrada global e imutável de conteúdo validado, identificada por fingerprint versionado e classificada como template de trilha ou payload de avaliação.
- **GenerationRequest**: solicitação pertencente a um usuário, preservada para auditoria e consulta de progresso, com referência ao fingerprint e à origem da geração.
- **KnowledgeAssessment**: avaliação pertencente a um usuário; pode ser criada a partir de payload de IA ou clonado de cache sem compartilhar perguntas, alternativas ou progresso.
- **Track Template**: estrutura validada de uma trilha e seus Steps, Lessons, Quizzes e Missions, sem dados de progresso ou identidade reutilizável.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em testes de solicitações equivalentes entre usuários, o provedor é chamado uma única vez e pelo menos uma solicitação subsequente é concluída com `source=cache`.
- **SC-002**: 100% das entradas equivalentes cobertas pelos testes de normalização e aliases produzem o mesmo fingerprint versionado.
- **SC-003**: 100% das clonagens verificadas criam identificadores e ownership novos e não carregam progresso, respostas, feedbacks ou streak do usuário de origem.
- **SC-004**: Em testes de concorrência para um fingerprint, no máximo uma chamada ao provedor é observada e nenhum registro duplicado ou parcial permanece.
- **SC-005**: Alterar o modelo ou a versão do prompt faz com que 100% das solicitações de teste gerem fingerprint novo e não reutilizem entradas antigas.
- **SC-006**: Quando a memória está indisponível ou desligada, 100% das solicitações válidas continuam pelo fluxo de IA e preservam o contrato existente.
- **SC-007**: Clientes que não conhecem o campo `source` continuam consumindo os endpoints existentes sem erro, enquanto clientes atualizados conseguem distinguir `ai` de `cache`.
- **SC-008**: As métricas permitem reconciliar hits, misses e chamadas evitadas em uma janela de operação sem expor conteúdo gerado ou dados pessoais.

## Assumptions

- O fluxo atual de autenticação, ownership, geração assíncrona, validação de conteúdo e publicação de progresso será reutilizado.
- O escopo inicial cobre trilhas e avaliações de conhecimento; geração sob demanda de missões fora desses agregados não recebe fingerprint próprio nesta feature.
- A curadoria inicial de aliases será pequena, determinística e mantida por migração ou seed; similaridade semântica probabilística fica fora do escopo.
- O conteúdo persistido no cache será o payload canônico após validação, nunca IDs, tokens, respostas brutas inválidas ou dados de progresso.
- Não haverá CRUD público de aliases nem endpoint público novo; os contratos existentes receberão apenas campos aditivos.
- A limpeza de entradas órfãs ou antigas será uma rotina futura; a validade operacional depende da versão do prompt e do modelo.
- O cache é uma otimização e sua indisponibilidade não deve impedir a geração normal por IA.
- O desempenho esperado é o de uma consulta de cache local compatível com o tempo usual de uma requisição, sem exigir uma meta específica de latência nesta versão.
