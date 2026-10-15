# Feature Specification: Autenticação e gerenciamento do perfil do usuário

**Feature Branch**: sdb-81-criar-endpoints-para-autenticacao-e-gerenciamento-do-perfil-do-usuario
**Created**: 2026-10-14
**Status**: Draft
**Input**: Jira SDB-81 — Criar endpoints para autenticação e gerenciamento do perfil do usuário

## Clarifications

### Session 2026-10-14

- Q: Ao trocar a senha, os tokens de acesso emitidos anteriormente devem perder a validade imediatamente? → A: Sim. Todos os tokens emitidos antes da troca de senha perdem a validade imediatamente.
- Q: A SDB-81 deve limitar temporariamente tentativas repetidas de login e de troca de senha? → A: Sim. Após 5 falhas por e-mail normalizado e origem na entrada, ou por conta e origem na troca de senha, em 15 minutos, responder 429 por 15 minutos, inclusive para e-mails desconhecidos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar conta e entrar imediatamente (Priority: P1)

Como pessoa nova no SideBrain, quero cadastrar nome, e-mail e senha para receber acesso à minha conta e começar a usar minhas trilhas.

**Why this priority**: O cadastro estabelece a identidade que será proprietária dos demais dados do usuário.

**Independent Test**: Cadastrar uma conta com dados válidos e verificar que ela é criada uma única vez, que o retorno permite acessar uma área protegida e que nenhuma senha aparece na resposta.

**Acceptance Scenarios**:

1. **Given** um e-mail ainda não cadastrado, **When** a pessoa envia nome, e-mail e senha válidos para POST /api/v1/auth/register, **Then** recebe 201, um accessToken do tipo Bearer e um usuário com id, name e email.
2. **Given** um e-mail já cadastrado, **When** a pessoa tenta cadastrar o mesmo endereço com outra combinação de letras maiúsculas e minúsculas, **Then** recebe 409 e nenhuma segunda conta é criada.
3. **Given** dados de cadastro inválidos, **When** a pessoa tenta se registrar, **Then** recebe 422 com indicação dos campos inválidos e nenhuma conta é criada.
4. **Given** uma conta cadastrada, **When** seus dados são consultados por qualquer uma das operações desta feature, **Then** a senha e sua representação protegida não aparecem na resposta.

---

### User Story 2 - Entrar com credenciais existentes (Priority: P1)

Como pessoa cadastrada, quero entrar com e-mail e senha para acessar somente os meus dados.

**Why this priority**: Os recursos existentes já exigem uma identidade autenticada; a entrada precisa substituir a credencial provisória usada atualmente.

**Independent Test**: Entrar com uma conta ativa, acessar um recurso protegido com o token recebido e repetir com senha errada, e-mail desconhecido, conta excluída e o antigo Bearer contendo apenas o identificador do usuário.

**Acceptance Scenarios**:

1. **Given** uma conta ativa, **When** a pessoa informa seu e-mail e senha corretos em POST /api/v1/auth/login, **Then** recebe 200, accessToken, tokenType Bearer e seus dados públicos.
2. **Given** uma conta ativa, **When** a pessoa informa o e-mail com diferença apenas de maiúsculas e minúsculas ou espaços nas extremidades, **Then** consegue entrar com a mesma senha.
3. **Given** e-mail inexistente, conta excluída ou senha incorreta e limite de tentativas ainda não atingido, **When** alguém tenta entrar, **Then** recebe o mesmo 401 genérico em todos os casos, sem indicação da causa.
4. **Given** uma credencial ausente, expirada, adulterada ou formada apenas pelo identificador do usuário, **When** alguém acessa um recurso protegido, **Then** recebe 401 com desafio Bearer e não acessa dados protegidos.
5. **Given** cinco falhas de entrada para o mesmo e-mail normalizado e origem em 15 minutos, **When** ocorre outra tentativa nessa combinação durante os 15 minutos seguintes, **Then** recebe 429 em Problem Details, mesmo que o e-mail não exista.

---

### User Story 3 - Consultar o próprio perfil (Priority: P1)

Como pessoa autenticada, quero consultar meu perfil para ver o nome e o e-mail associados à minha conta.

**Why this priority**: A consulta confirma a identidade reconhecida pelo produto e oferece o recurso base para o gerenciamento da conta.

**Independent Test**: Consultar GET /api/v1/users/me com token válido e inválido e verificar que o retorno válido contém somente id, name e email do titular.

**Acceptance Scenarios**:

1. **Given** uma conta ativa e token válido, **When** a pessoa consulta GET /api/v1/users/me, **Then** recebe 200 e apenas seus campos públicos id, name e email.
2. **Given** um token ausente ou inválido, **When** alguém consulta o perfil, **Then** recebe 401 e nenhum dado de usuário.
3. **Given** uma conta que deixou de estar disponível após a validação da credencial, **When** a consulta do perfil é concluída, **Then** recebe 404 sem dados da conta.

---

### User Story 4 - Atualizar nome ou e-mail (Priority: P2)

Como pessoa autenticada, quero corrigir meu nome ou e-mail para manter o perfil atualizado sem afetar a senha.

**Why this priority**: A manutenção do perfil depende de uma conta existente e não deve permitir que o cliente escolha outro titular.

**Independent Test**: Alterar apenas nome, apenas e-mail e ambos; confirmar que o retorno reflete a mudança e que tentativa de usar e-mail ocupado ou alterar campos protegidos não modifica a conta.

**Acceptance Scenarios**:

1. **Given** uma conta ativa, **When** a pessoa envia name, email ou ambos para PUT /api/v1/users/me, **Then** recebe 200 e o perfil atualizado, mantendo a identidade e a senha.
2. **Given** outra conta com o e-mail pretendido, **When** a pessoa tenta atualizar o seu e-mail, **Then** recebe 409 e seu perfil anterior é preservado.
3. **Given** um corpo vazio, valor inválido ou campo protegido como password, id ou estado de exclusão, **When** a pessoa tenta atualizar o perfil, **Then** recebe 422 e nenhuma alteração é aplicada.
4. **Given** token ausente, inválido ou conta indisponível, **When** alguém tenta atualizar o perfil, **Then** recebe 401 ou, se a indisponibilidade ocorrer após a autenticação, 404, sem alterar dados.

---

### User Story 5 - Trocar a própria senha (Priority: P2)

Como pessoa autenticada, quero trocar minha senha informando a atual para recuperar o controle da credencial sem criar outra conta.

**Why this priority**: A operação altera uma credencial sensível e exige prova adicional de posse da conta.

**Independent Test**: Trocar a senha com a senha atual correta, confirmar 204 sem corpo, recusa da senha antiga e dos tokens anteriores e sucesso de uma nova entrada com a senha nova.

**Acceptance Scenarios**:

1. **Given** uma conta ativa e a senha atual correta, **When** a pessoa envia currentPassword e uma newPassword diferente e válida para PUT /api/v1/users/me/password, **Then** recebe 204 sem corpo.
2. **Given** uma troca concluída, **When** a pessoa tenta entrar com a senha antiga, usar qualquer token emitido antes da troca e depois entrar com a senha nova, **Then** as duas primeiras tentativas recebem 401 e a última recebe 200 com um novo token.
3. **Given** senha atual incorreta e limite de tentativas ainda não atingido, **When** a pessoa solicita a troca, **Then** recebe 401 e a senha anterior permanece válida.
4. **Given** nova senha fraca, curta ou igual à atual, **When** a pessoa solicita a troca, **Then** recebe 422 e a credencial permanece inalterada.
5. **Given** cinco falhas de troca de senha da mesma conta e origem em 15 minutos, **When** ocorre outra tentativa nessa combinação durante os 15 minutos seguintes, **Then** recebe 429 em Problem Details e a senha permanece inalterada.

---

### User Story 6 - Excluir a própria conta (Priority: P2)

Como pessoa autenticada, quero excluir minha conta para impedir novos acessos, preservando o registro interno necessário à integridade dos dados relacionados.

**Why this priority**: A exclusão encerra o ciclo de vida da conta e deve revogar o acesso imediatamente.

**Independent Test**: Excluir uma conta ativa, confirmar 204 sem corpo, verificar que o registro permanece armazenado como excluído e que login e token anterior deixam de dar acesso.

**Acceptance Scenarios**:

1. **Given** uma conta ativa com dados relacionados, **When** a pessoa chama DELETE /api/v1/users/me, **Then** recebe 204 sem corpo, a conta é marcada como excluída e seus dados relacionados permanecem armazenados.
2. **Given** uma conta excluída, **When** alguém tenta entrar com suas credenciais ou usar um token emitido antes da exclusão, **Then** recebe 401 e não acessa recursos protegidos.
3. **Given** token ausente, inválido ou conta já indisponível, **When** alguém solicita exclusão, **Then** não ocorre nova mutação e a resposta é 401 ou, quando a indisponibilidade é detectada após autenticação, 404.

### Edge Cases

- Nome com apenas espaços, nome após normalização acima de 255 caracteres, e-mail malformado ou acima de 255 caracteres, senha com menos de 8 caracteres e campos obrigatórios ausentes produzem 422 sem persistência parcial.
- O e-mail é comparado após remover espaços nas extremidades e converter para minúsculas. Diferenças de caixa não permitem duplicidade no cadastro nem na alteração; tentativas simultâneas de usar o mesmo e-mail resultam em uma única conta com esse endereço.
- A atualização do próprio e-mail para sua grafia atual normalizada não produz conflito; o mesmo endereço pertencente a outra conta, inclusive excluída, permanece indisponível.
- O acesso protegido com o formato provisório de Bearer contendo somente um UUID é recusado.
- Tokens expirados, inválidos, adulterados e de contas excluídas não concedem acesso; a conta não pode ser escolhida por identificador enviado na URL ou no corpo.
- Após a troca de senha, inclusive o token usado para solicitá-la deixa de conceder acesso; é necessário entrar novamente com a nova senha.
- Campos não previstos nos pedidos, incluindo identificador, hash, timestamps e estado de exclusão, são recusados.
- Falhas no armazenamento durante cadastro, atualização, troca de senha ou exclusão não deixam mudanças parciais.
- Cada operação tem seu próprio limite: na entrada, as falhas são agrupadas por e-mail normalizado e origem do cliente; na troca de senha, por conta autenticada e origem. Uma operação bem-sucedida zera seu respectivo contador. E-mails desconhecidos e contas excluídas seguem o mesmo limite da entrada para não revelar a existência da conta.
- Somente falhas de credencial contam para o limite de tentativas; pedidos inválidos rejeitados com 422 não aumentam o contador.
- O corpo de resposta de 204 é vazio; respostas de erro seguem Problem Details e não expõem senha, hash, token, motivo específico de falha de login ou nomes físicos das colunas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O produto MUST disponibilizar cadastro em POST /api/v1/auth/register com name, email e password obrigatórios, retornando 201 com accessToken, tokenType Bearer e user.
- **FR-002**: O cadastro MUST remover espaços das extremidades do nome e do e-mail, converter o e-mail para minúsculas e exigir nome de 1 a 255 caracteres, e-mail válido de até 255 caracteres e senha de pelo menos 8 caracteres.
- **FR-003**: O produto MUST manter um único titular por e-mail normalizado, sem distinção de maiúsculas e minúsculas, e MUST responder 409 a conflitos de cadastro ou atualização, inclusive em pedidos simultâneos.
- **FR-004**: Senhas MUST ser armazenadas somente em representação protegida adequada à verificação; o valor original MUST NOT ser recuperável do registro nem aparecer em respostas.
- **FR-005**: O produto MUST permitir entrada em POST /api/v1/auth/login com email e password, normalizar o e-mail como no cadastro e retornar 200 com accessToken, tokenType Bearer e user para credenciais de conta ativa.
- **FR-006**: Entrada com e-mail desconhecido, conta excluída ou senha incorreta MUST produzir o mesmo 401 genérico enquanto o limite de tentativas não for atingido, sem revelar qual condição ocorreu. As falhas de credencial MUST ser contadas por e-mail normalizado e origem do cliente; após cinco falhas em 15 minutos, as tentativas seguintes nessa combinação MUST receber 429 pelos 15 minutos seguintes. E-mails desconhecidos e contas excluídas MUST seguir a mesma contagem; entrada bem-sucedida MUST zerar o respectivo contador.
- **FR-007**: O accessToken emitido no cadastro e na entrada MUST ter validade limitada a 60 minutos e identificar exclusivamente a conta autenticada; a credencial provisória formada apenas pelo identificador da conta MUST deixar de ser aceita.
- **FR-008**: Toda operação protegida existente e nova MUST validar a credencial e a condição ativa da conta antes de conceder acesso, respondendo 401 quando a credencial for ausente, inválida, expirada ou associada a conta excluída.
- **FR-009**: O produto MUST disponibilizar GET /api/v1/users/me para retornar 200 com id, name e email da conta autenticada ativa, sem receber identificador de usuário do cliente.
- **FR-010**: O produto MUST disponibilizar PUT /api/v1/users/me para atualizar name, email ou ambos da conta autenticada, exigindo pelo menos um campo e retornando 200 com o perfil resultante.
- **FR-011**: A atualização de perfil MUST aplicar as mesmas regras de normalização e limites do cadastro para name e email e MUST preservar senha, identificador e estado de exclusão.
- **FR-012**: O produto MUST disponibilizar PUT /api/v1/users/me/password com currentPassword e newPassword obrigatórios, exigindo a senha atual correta, nova senha diferente da atual e pelo menos 8 caracteres na nova senha.
- **FR-013**: A troca de senha bem-sucedida MUST retornar 204 sem corpo, fazer a senha anterior deixar de autenticar, invalidar imediatamente todos os tokens emitidos antes da troca e permitir autenticação com a nova senha. Senha atual incorreta MUST produzir 401 sem alteração; após cinco falhas dessa operação para a mesma conta e origem em 15 minutos, tentativas seguintes MUST receber 429 pelos 15 minutos seguintes. A troca bem-sucedida MUST zerar seu contador, separado do limite de entrada.
- **FR-014**: O produto MUST disponibilizar DELETE /api/v1/users/me para marcar a conta autenticada como excluída, registrar o momento da exclusão e retornar 204 sem corpo.
- **FR-015**: A exclusão da conta MUST preservar fisicamente a conta e seus dados relacionados, impedir novas entradas e invalidar o uso de qualquer token anterior em todos os recursos protegidos.
- **FR-016**: Pedidos de perfil MUST operar exclusivamente sobre a identidade autenticada; MUST NOT aceitar identificador de outra conta em URL ou corpo.
- **FR-017**: Pedidos com campos ausentes, inválidos, não previstos ou proibidos MUST retornar 422 sem alteração parcial; o cliente MUST NOT controlar id, hash, datas ou estado de exclusão.
- **FR-018**: A representação pública de usuário MUST conter apenas id, name e email; a resposta de autenticação MUST conter apenas accessToken, tokenType e essa representação de user, sem nomes físicos de armazenamento.
- **FR-019**: Quando a conta ficar indisponível entre a validação da credencial e a operação de perfil, a operação MUST retornar 404 sem revelar dados e sem alteração parcial.
- **FR-020**: Erros 401, 404, 409, 422 e 429 MUST seguir o formato Problem Details do produto, com tipo, título, status e detalhe; respostas 401 por credencial Bearer ausente ou inválida MUST informar o desafio Bearer.
- **FR-021**: Esta feature MUST limitar-se a cadastro, entrada, consulta e alteração do próprio perfil, troca de senha, exclusão lógica e validação da nova credencial nos recursos existentes. MUST NOT incluir renovação de token, recuperação de senha por e-mail, provedores externos, papéis administrativos ou atualização de histórico de login e sequência de dias.
- **FR-022**: A troca do mecanismo de autenticação MUST preservar os contratos funcionais dos demais recursos, exceto pela exigência do novo token Bearer em lugar do identificador provisório. A implantação MUST ter um plano de migração que oriente consumidores existentes a obter novos tokens antes de perderem o acesso com o identificador provisório.

### Key Entities *(include if feature involves data)*

- **Usuário**: Titular de uma conta e proprietário de seus recursos associados. Possui identificador, nome, e-mail único normalizado, representação protegida da senha e condição ativa ou excluída.
- **Credencial de acesso**: Permissão temporária emitida após cadastro ou entrada, vinculada à identidade da conta. Deixa de conceder acesso quando expira, é inválida, a senha é trocada após sua emissão ou a conta é excluída.
- **Perfil público**: Visão do usuário restrita a identificador, nome e e-mail, usada em consultas e respostas de autenticação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos cenários de aceite de cadastro, entrada, consulta, alteração de perfil, troca de senha e exclusão, a operação retorna o resultado e o código esperados.
- **SC-002**: Em 100% dos cenários de e-mail duplicado, inclusive diferenças de caixa e pedidos simultâneos, no máximo uma conta mantém o endereço e o pedido conflitante recebe 409.
- **SC-003**: Em 100% das tentativas com credenciais inválidas, expiradas, provisórias, emitidas antes da última troca de senha ou vinculadas a conta excluída, nenhum recurso protegido é disponibilizado.
- **SC-004**: Em 100% das respostas de sucesso e erro avaliadas, nenhuma senha, representação protegida da senha ou nome físico de coluna é exibido.
- **SC-005**: Após a exclusão, 100% das tentativas de entrada e de uso de tokens anteriores são recusadas, enquanto a conta e seus relacionamentos permanecem armazenados.
- **SC-006**: Em ensaio com 20 clientes simultâneos e dados válidos, pelo menos 95% das operações de cadastro, entrada e consulta de perfil recebem resposta em até 2 segundos.
- **SC-007**: Em uma validação do contrato com cinco consumidores da API, pelo menos quatro conseguem completar cadastro, entrada e consulta do próprio perfil sem esclarecimentos adicionais.
- **SC-008**: Em 100% dos ensaios com cinco falhas de entrada por e-mail normalizado e origem, ou de troca de senha por conta e origem, dentro de 15 minutos, a tentativa seguinte recebe 429 por 15 minutos, inclusive quando o e-mail informado não existe.

## Assumptions

- A conta já possui os dados necessários para nome, e-mail, senha protegida e exclusão lógica; a forma de garantir unicidade case-insensitive para registros preexistentes será definida no planejamento.
- O endereço de e-mail permanece reservado após a exclusão lógica, coerentemente com a unicidade atual do cadastro. Um novo registro com esse endereço recebe 409.
- A política inicial de senha exige ao menos 8 caracteres; regras adicionais de complexidade não fazem parte desta feature.
- A troca de senha encerra o acesso concedido por todos os tokens anteriores, inclusive o usado nessa operação. Uma nova entrada com a senha atualizada é necessária; não há renovação de token nesta entrega.
- As rotas públicas de autenticação e as rotas protegidas de perfil seguem o prefixo /api/v1 adotado pelo produto.
- Os demais recursos protegidos continuam a reconhecer a mesma identidade de usuário e suas regras atuais de propriedade; apenas o formato da credencial muda.
- A implantação exige atualização coordenada dos consumidores para cadastro ou entrada com e-mail e senha; o identificador provisório não é aceito como credencial após a mudança.
- O registro de entradas, sequência de dias e efeitos de gamificação permanecem fora do escopo.
