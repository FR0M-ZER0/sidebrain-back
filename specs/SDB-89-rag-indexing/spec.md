# Feature Specification: Referências técnicas para trilhas de programação

**Feature Branch**: `SDB-89-rag-indexing`

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "SDB-89 — Implementar uma pipeline de indexação e uma interface simples de recuperação para apoiar a geração de trilhas, lições, quizzes e missões sobre programação em Python ou JavaScript, preservando os fluxos existentes para outros assuntos."

## Clarifications

### Session 2026-10-19

- Q: Qual confiança mínima habilita o uso de referências quando o objetivo é classificado como programação em Python ou JavaScript? → A: `0,80`; o RAG só é habilitado quando a confiança for igual ou superior a esse valor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar conteúdo de programação com referências confiáveis (Priority: P1)

Como pessoa que aprende programação em Python ou JavaScript, quero receber trilhas e conteúdos tecnicamente corretos, para estudar conceitos e exemplos alinhados a material confiável.

**Why this priority**: A exatidão técnica e a adequação ao objetivo de aprendizagem são o benefício principal da funcionalidade.

**Independent Test**: Enviar objetivos claramente relacionados a Python e JavaScript nos fluxos inicial e incremental e verificar que as referências pertinentes aparecem no contexto de geração e que os conteúdos gerados continuam respeitando sua estrutura e validação existentes.

**Acceptance Scenarios**:

1. **Given** um objetivo e tópico que identificam com confiança programação em Python ou JavaScript, **When** uma trilha é gerada, **Then** referências relevantes ao idioma identificado são disponibilizadas para a geração inicial.
2. **Given** uma etapa posterior pertencente a uma trilha cujo contexto original identifica Python ou JavaScript, **When** seu conteúdo é preparado, **Then** referências pertinentes ao mesmo idioma são disponibilizadas para a geração de lições, quizzes e missões.
3. **Given** referências recuperadas para uma geração, **When** o conteúdo é produzido, **Then** as referências são tratadas como material de apoio, incluem atribuição e não substituem as instruções nem o formato de saída esperado.
4. **Given** o nível `pro` em uma etapa, **When** referências são selecionadas, **Then** o conteúdo adequado a nível avançado pode ser considerado sem alterar o nível ou os contratos públicos da etapa.

---

### User Story 2 - Preservar geração de assuntos sem suporte RAG (Priority: P1)

Como pessoa que aprende assuntos fora de programação em Python ou JavaScript, quero continuar recebendo conteúdo pelo fluxo atual, para que a inclusão de referências técnicas não altere a experiência de outras trilhas.

**Why this priority**: O produto oferece aprendizagem em assuntos diversos e precisa preservar seus fluxos e contratos existentes.

**Independent Test**: Gerar uma trilha sobre um assunto não relacionado e verificar que nenhuma consulta de referências ocorre e que o fluxo existente termina com os mesmos contratos e validações.

**Acceptance Scenarios**:

1. **Given** um objetivo claramente fora de Python e JavaScript, **When** a geração inicial ou incremental é executada, **Then** nenhuma busca ou preparação de referência é solicitada e a geração existente prossegue.
2. **Given** um objetivo que menciona incidentalmente Python ou JavaScript sem ser sobre programação nesses idiomas, **When** o assunto é identificado, **Then** referências não são usadas.
3. **Given** um objetivo ambíguo, idioma não reconhecido ou classificação abaixo de `0,80`, **When** a decisão é tomada, **Then** o sistema não usa referências e mantém a geração atual.
4. **Given** uma falha ao identificar o assunto ou recuperar referências, **When** uma trilha ou etapa é gerada, **Then** o conteúdo ainda pode ser gerado sem referências e a falha fica observável sem expor segredos.

---

### User Story 3 - Manter referências atribuídas e atualizadas (Priority: P1)

Como responsável pelo conteúdo técnico, quero indexar fontes autorizadas, preservar sua atribuição e atualizar somente o material alterado, para manter referências úteis, rastreáveis e operáveis.

**Why this priority**: A qualidade da geração depende de conteúdo atual, identificável e coletado de acordo com as condições de cada fonte.

**Independent Test**: Executar a atualização usando fontes locais de teste, simular documentos novos, inalterados, modificados, removidos, duplicados e com falha, e verificar a atribuição, atualização seletiva e continuidade do processamento.

**Acceptance Scenarios**:

1. **Given** as fontes configuradas para Python e JavaScript, **When** a operação de indexação é executada, **Then** ela considera a documentação oficial do Python (tutorial e biblioteca padrão) e o MDN Web Docs para JavaScript, respeitando escopo, licença, políticas de acesso e limites declarados.
2. **Given** uma fonte com páginas, repositórios documentais ou diretórios locais aceitos, **When** seu conteúdo é processado, **Then** cada trecho mantém título, localização de origem, seção, idioma, nível, tipo de conteúdo, tags, licença aplicável, versão e data de coleta disponíveis.
3. **Given** uma página ou arquivo que falha durante a coleta, **When** a fonte continua sendo processada, **Then** a falha é registrada e os demais documentos continuam elegíveis ao processamento.
4. **Given** conteúdo com títulos, texto e exemplos de código, **When** ele é organizado em trechos, **Then** a hierarquia de seções é preservada, o código permanece associado à explicação sempre que possível, blocos de código não são cortados no meio mesmo quando excedem o tamanho-alvo e cada trecho mantém a licença aplicável ao seu conteúdo.
5. **Given** documentos idênticos ou quase duplicados, **When** a deduplicação é aplicada, **Then** o conteúdo repetido é reduzido sem remover as atribuições de origem ou licença que precisam permanecer.
6. **Given** documentos e trechos sem alteração desde a execução anterior, **When** a indexação incremental é executada, **Then** eles não são reprocessados desnecessariamente; conteúdo obsoleto é removido somente dentro da fonte correspondente.
7. **Given** uma mudança de modelo ou dimensão de representação, **When** uma reindexação completa é solicitada, **Then** o operador recebe informação clara de que todos os trechos elegíveis serão reconstruídos.

---

### User Story 4 - Consultar e avaliar a recuperação (Priority: P2)

Como responsável pelo produto, quero consultar os trechos recuperados e medir sua relevância com um conjunto estável de perguntas, para avaliar e diagnosticar a qualidade do material usado na geração.

**Why this priority**: A inspeção e a avaliação tornam a recuperação verificável sem depender de coleta ao vivo ou de um endpoint público adicional.

**Independent Test**: Consultar um índice de fixture local e executar a avaliação fixa, verificando os textos, origens e seções retornados, além das métricas de cobertura esperada.

**Acceptance Scenarios**:

1. **Given** uma consulta com filtros de idioma, nível ou tipo de conteúdo, **When** a recuperação é executada, **Then** os trechos retornados respeitam os filtros e incluem texto e atribuição de origem úteis.
2. **Given** resultados de mais de um método de busca, **When** a lista final é montada, **Then** os resultados são combinados por uma regra de fusão documentada, com parâmetros reproduzíveis e um ponto opcional de reranqueamento desativado por padrão.
3. **Given** o conjunto de avaliação, **When** ele é executado sem acessar fontes externas, **Then** são processadas 20 perguntas sobre Python e JavaScript em níveis variados e é calculado recall@k usando identificadores ou fontes esperados.
4. **Given** uma operação de indexação, **When** ela termina, **Then** um relatório informa documentos encontrados e processados, trechos gerados, falhas, duplicatas removidas, duração e custo estimado de processamento quando disponível.

### Edge Cases

- O contexto da trilha pode estar ausente ou insuficiente em uma etapa posterior; nesse caso, a classificação deve falhar de forma conservadora e não escolher um idioma por inferência fraca.
- Objetivos podem misturar Python/JavaScript com outros assuntos; referências só devem ser usadas quando o objetivo de aprendizagem de programação estiver identificado com confiança.
- O serviço de identificação do assunto ou de recuperação pode estar indisponível; funcionalidades independentes de referências devem continuar operando sem exigir credenciais opcionais.
- Uma fonte pode estar temporariamente indisponível, conter documentos fora das regras de inclusão ou impedir a coleta por suas políticas; os demais documentos e fontes elegíveis não devem ser descartados.
- Documentos podem não ter título, seção, licença explícita ou versão; o sistema deve registrar os valores disponíveis sem inventar atribuições.
- Um bloco de código maior que o alvo configurado de trecho deve permanecer íntegro, ainda que gere um trecho maior que o usual.
- Uma alteração no método de representação do conteúdo exige reconstrução compatível das referências antes de misturar resultados incompatíveis.
- Reexecuções concorrentes ou repetidas da indexação não devem remover conteúdo pertencente a outras fontes nem causar duplicatas persistidas.
- Os domínios de nível existentes podem incluir valores sem correspondência direta no filtro de referências; `pro` deve ser considerado equivalente a avançado somente para selecionar referências.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST identificar se o objetivo de aprendizagem é especificamente programação em Python, programação em JavaScript ou outro assunto, considerando o objetivo e o tópico disponíveis.
- **FR-002**: O sistema MUST usar referências somente quando o idioma estiver identificado com confiança igual ou superior a `0,80`; menções incidentais, ambiguidade, idioma não reconhecido ou confiança abaixo de `0,80` MUST resultar em não usar referências.
- **FR-003**: O sistema MUST aplicar a mesma decisão de assunto à geração inicial e à preparação incremental, usando o contexto original persistido ou disponível da trilha.
- **FR-004**: O sistema MUST disponibilizar referências recuperadas à geração inicial de trilha e à geração de conteúdo das etapas seguintes, abrangendo lições, quizzes e missões.
- **FR-005**: As referências MUST ser apresentadas como evidências de apoio com fonte e localização, e MUST NOT substituir as instruções, a validação ou o formato estruturado já exigido pela geração.
- **FR-006**: Falhas de identificação ou recuperação MUST permitir que os fluxos de geração existentes prossigam sem referências e MUST ser observáveis sem registrar segredos ou conteúdo desnecessário.
- **FR-007**: A introdução de referências MUST NOT alterar os contratos públicos de request/response, os schemas de conteúdo gerado, a validação existente, a persistência ou a idempotência dos fluxos de geração; MUST NOT adicionar referências aos fluxos de criação manual de trilhas ou de avaliação de conhecimento.
- **FR-008**: O sistema MUST permitir a configuração de fontes de páginas e mapas de site, repositórios documentais e pastas locais, com idioma, licença, versão, regras de inclusão e exclusão e parâmetros próprios da fonte.
- **FR-009**: As fontes iniciais MUST incluir documentação oficial do Python, com tutorial e biblioteca padrão, e documentação JavaScript do MDN Web Docs, com escopo que exclua conteúdo não pertinente.
- **FR-010**: A coleta MUST respeitar as políticas de acesso, instruções de exclusão, licenças e limites configurados para cada fonte, com identificação de crawler, timeouts, concorrência limitada e tratamento isolado de falhas por documento.
- **FR-011**: O sistema MUST extrair conteúdo principal, preservar blocos de código e seu idioma quando identificável, e registrar título e localização de origem.
- **FR-012**: A normalização MUST preservar a integridade de exemplos de código; a deduplicação exata e aproximada MUST ser configurável e documentada e MUST preservar as atribuições de origem e licença necessárias.
- **FR-013**: O sistema MUST organizar o conteúdo por seção e dividi-lo em trechos de aproximadamente 400 a 600 tokens, com sobreposição configurável de aproximadamente 10% a 15%, prefixo que identifique documento e seção e preservação de blocos de código inteiros.
- **FR-014**: Cada documento e trecho MUST ter identificadores estáveis; cada trecho MUST manter também um identificador de conteúdo e do método de representação, além de atribuição de fonte, localização, título, caminho de seção, idioma, nível, tipo de conteúdo, tópicos ou tags, licença aplicável, versão e data de coleta. Quando texto e exemplos de código de uma mesma fonte tiverem licenças distintas, o sistema MUST preservar a atribuição correspondente a cada conteúdo e MUST NOT presumir que compartilham uma única licença.
- **FR-015**: O sistema MUST classificar inicialmente tipo de conteúdo e tags por regras simples, sem exigir classificação automatizada adicional para indexar; essa classificação adicional em lote MUST ser opcional.
- **FR-016**: O sistema MUST permitir localizar conteúdo por similaridade de significado e correspondência de termos, aplicar os filtros de idioma, nível e tipo de conteúdo a ambas as estratégias e combinar seus resultados por uma regra documentada e reproduzível. Um refinamento adicional de ordenação MUST permanecer opcional e desativado por padrão.
- **FR-017**: O resultado de recuperação MUST incluir o texto, a fonte, o endereço ou caminho de origem, título, seção e metadados úteis de cada trecho.
- **FR-018**: O nível `pro` MUST ser mapeado para `advanced` exclusivamente nos filtros de referência, sem alterar os enums ou schemas públicos do produto.
- **FR-019**: O sistema MUST permitir substituir o fornecedor de processamento de conteúdo; credenciais e configurações externas MUST ser opcionais na inicialização e exigidas somente quando a operação correspondente precisar delas.
- **FR-020**: O processamento MUST suportar lotes, tentativas limitadas com espera progressiva para falhas transitórias, registro do método utilizado, reaproveitamento de resultados em conteúdo inalterado e estimativa de custo baseada em preços configuráveis.
- **FR-021**: A indexação incremental MUST detectar documentos e trechos alterados, processar conteúdo alterado, preservar conteúdo inalterado e remover conteúdo obsoleto somente da fonte processada.
- **FR-022**: O sistema MUST permitir reconstrução completa das referências e documentar seus efeitos quando o método de representação mudar.
- **FR-023**: A operação MUST disponibilizar aos responsáveis uma interface interna para indexar uma ou todas as fontes, reconstruir as referências e consultar o material com filtros. Essas capacidades MUST NOT ser expostas como uma nova funcionalidade pública para clientes.
- **FR-024**: O relatório de execução MUST informar documentos encontrados e processados, trechos produzidos, falhas por documento, duplicatas removidas, duração e custo estimado quando calculável.
- **FR-025**: O produto MUST incluir 20 perguntas reproduzíveis de avaliação, cobrindo Python e JavaScript em vários níveis, com origens ou identificadores esperados e cálculo de recall@k sem depender de coleta ao vivo.
- **FR-026**: A documentação MUST explicar configuração e credenciais, operação manual e periódica, fontes e licenças, avaliação, limitações e procedimento e impacto da reindexação completa.

### Key Entities *(include if feature involves data)*

- **Contexto de aprendizagem**: objetivo, tópico e demais informações originais que determinam se referências são aplicáveis e qual idioma usar.
- **Fonte de referência**: origem configurada de material técnico, com escopo de coleta, idioma, licença, nível e estratégia para reconhecer sua versão.
- **Documento de referência**: página ou arquivo coletado com identificador estável, título, localização original, versão e atribuição.
- **Trecho de referência**: parte de um documento com identificador estável e identificadores de conteúdo e representação, associada a uma seção, idioma, nível, tópicos e licença, recuperável durante a geração.
- **Execução de indexação**: operação que coleta ou atualiza fontes e relata documentos, trechos, falhas, duplicatas, duração e custo estimado.
- **Caso de avaliação**: pergunta de teste vinculada às origens ou aos trechos esperados para medir a cobertura da recuperação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos casos de teste com objetivos claramente sobre programação em Python ou JavaScript, referências do idioma correto podem ser disponibilizadas tanto à geração inicial quanto à incremental.
- **SC-002**: Em 100% dos casos de teste com assuntos não relacionados, menções incidentais, contexto ambíguo ou confiança inferior a `0,80`, nenhuma busca ou preparação de referências é acionada.
- **SC-003**: Em 100% das falhas simuladas de classificação ou recuperação, a geração continua sem referências e não altera os contratos nem a validação existentes.
- **SC-004**: 100% dos trechos retornados em testes incluem atribuição de origem e a licença aplicável, distinguindo texto e código quando suas licenças forem diferentes.
- **SC-005**: Uma reindexação incremental de fontes sem alterações reprocessa zero documentos ou trechos inalterados; alterações e remoções afetam somente a fonte correspondente.
- **SC-006**: O conjunto fixo de 20 perguntas é executável sem internet e produz um relatório de recall@k comparável entre execuções.
- **SC-007**: Em uma falha simulada de documento, os demais documentos elegíveis da mesma execução continuam sendo processados e a falha aparece no relatório final.
- **SC-008**: Os fluxos de criação manual de trilha, avaliação de conhecimento e geração de assuntos sem RAG mantêm seus contratos e comportamento cobertos pelos testes existentes.

## Assumptions

- A classificação considera o objetivo e o tópico disponíveis; se o contexto de uma etapa posterior não permitir recuperar o assunto original com confiança, a decisão padrão é não usar referências.
- O limite mínimo de confiança é `0,80`; objetivos abaixo desse valor não usam referências.
- O serviço de identificação do assunto pode falhar ou estar indisponível; uma regra conservadora de fallback não deve obrigar o uso de referências.
- O conjunto inicial de fontes está limitado à documentação oficial do Python (tutorial e biblioteca padrão) e ao MDN Web Docs para JavaScript; fontes adicionais serão adicionadas por configuração após revisão de escopo, acesso e licença.
- Trechos sem metadados disponíveis não devem receber atribuições inferidas; metadados ausentes permanecem explicitamente ausentes.
- Os resultados da avaliação usam um conjunto local fixo e reproduzível e identificadores ou fontes esperados, podendo ser complementados por avaliação contra um índice já carregado.
- As regras de tamanho de trecho, sobreposição, proximidade de duplicatas, fusão e orçamento de custo são configuráveis e documentadas, sem modificar os contratos públicos do produto.
- O armazenamento e o processamento de referências são internos; a recuperação permanece acessível por operação e pelos fluxos de geração, sem criar um novo endpoint público.
