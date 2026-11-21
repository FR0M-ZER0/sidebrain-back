# Feature Specification: Avatar do perfil do usuário

**Feature Branch**: `SDB-111-user-avatar`

**Created**: 2026-11-18

**Status**: Draft

**Input**: User description: "SDB-111 — Permitir que o usuário autenticado escolha, altere e remova um avatar de perfil a partir de um catálogo predefinido de imagens armazenadas pelo backend."

## Clarifications

### Session 2026-11-18

- Q: A consulta do catálogo de avatares deve exigir autenticação ou pode ser acessada sem login? → A: Exigir autenticação válida.
- Q: Qual formato deve ser usado para a referência de imagem retornada pelo catálogo e pelo perfil? → A: URL relativa servida pelo backend.
- Q: No contrato de atualização do perfil, o que deve acontecer quando o campo do avatar não é enviado? → A: Campo ausente mantém; `null` remove.
- Q: Qual tipo de identificador estável deve ser usado para selecionar um avatar no contrato da API? → A: Slug textual imutável.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher um avatar (Priority: P1)

Como usuário autenticado, quero consultar os avatares disponíveis e escolher um deles para personalizar meu perfil.

**Why this priority**: A seleção de um avatar é o principal valor da funcionalidade e permite que o cliente apresente uma identidade visual consistente sem receber imagens do usuário.

**Independent Test**: Consultar o catálogo, selecionar um avatar ativo e consultar o próprio perfil para confirmar que a imagem escolhida é retornada.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado e um catálogo com avatares ativos, **When** ele consulta o catálogo, **Then** recebe cada opção com identificador estável, nome e referência utilizável da imagem.
2. **Given** um usuário autenticado, **When** ele seleciona um identificador ativo, **Then** a seleção é persistida no próprio perfil.
3. **Given** um usuário sem avatar selecionado, **When** ele consulta o próprio perfil, **Then** recebe a referência da imagem padrão.

---

### User Story 2 - Alterar ou remover o avatar (Priority: P1)

Como usuário autenticado, quero trocar ou remover meu avatar para manter meu perfil atualizado.

**Why this priority**: O usuário precisa controlar a seleção ao longo do tempo, e a remoção deve retornar ao estado padrão sem apagar ou alterar os demais dados do perfil.

**Independent Test**: Selecionar um avatar, substituí-lo por outro e depois removê-lo, verificando o perfil após cada operação.

**Acceptance Scenarios**:

1. **Given** um usuário com um avatar selecionado, **When** ele seleciona outro avatar ativo, **Then** o perfil passa a retornar a nova referência.
2. **Given** um usuário com um avatar selecionado, **When** ele remove a seleção, **Then** o perfil passa a retornar a imagem padrão e os demais dados permanecem inalterados.
3. **Given** um usuário cujo avatar foi desativado, **When** ele consulta o próprio perfil, **Then** recebe a imagem padrão e pode selecionar outro avatar ativo.

---

### User Story 3 - Manter o catálogo seguro e administrável (Priority: P2)

Como responsável pela manutenção do produto, quero disponibilizar apenas opções válidas e ativas, preservando usuários existentes quando o catálogo mudar.

**Why this priority**: A validação evita referências inválidas e permite desativar opções sem quebrar perfis ou impedir novas escolhas válidas.

**Independent Test**: Tentar selecionar identificadores inexistentes ou desativados, desativar uma opção existente e verificar as respostas do catálogo e dos perfis.

**Acceptance Scenarios**:

1. **Given** um identificador inexistente ou desativado, **When** um usuário tenta selecioná-lo, **Then** a operação é rejeitada com Problem Details e o avatar atual não é alterado.
2. **Given** uma requisição sem autenticação válida, **When** ela tenta alterar um avatar, **Then** a requisição é rejeitada sem alteração de perfil.
3. **Given** usuários existentes sem avatar, **When** a alteração de dados é aplicada, **Then** eles continuam aptos a consultar e atualizar seus perfis sem escolher um avatar.

### Edge Cases

- O catálogo autenticado para seleção contém somente avatares ativos; uma opção desativada não aparece em novas consultas.
- A desativação de um avatar já selecionado não remove o registro do usuário nem impede a consulta do perfil; a resposta usa a imagem padrão.
- O identificador `null` representa remoção da seleção; quando o campo não é enviado, a seleção atual é mantida.
- A referência da imagem padrão permanece disponível quando não há avatar selecionado ou quando a opção selecionada se torna inativa.
- Falhas de validação, autenticação ou persistência seguem o formato Problem Details adotado pelo projeto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar um catálogo inicial com dez avatares ativos de animais: gato, cachorro, raposa, urso, coelho, panda, coruja, pinguim, leão e tartaruga.
- **FR-002**: Cada avatar MUST possuir slug textual imutável, nome, estado ativo/inativo e uma URL relativa utilizável, servida pelo backend, para sua imagem armazenada.
- **FR-003**: O sistema MUST disponibilizar também uma imagem padrão armazenada no backend e acessível por uma URL relativa servida pelo backend.
- **FR-004**: O sistema MUST permitir que usuários autenticados consultem o catálogo de avatares ativos sem expor opções desativadas para novas seleções.
- **FR-005**: O usuário autenticado MUST poder selecionar um avatar ativo para o próprio perfil usando seu identificador.
- **FR-006**: O usuário autenticado MUST poder alterar a seleção para outro avatar ativo sem modificar os demais dados do perfil.
- **FR-007**: O usuário autenticado MUST poder remover a seleção enviando o identificador `null`, deixando o identificador persistido sem valor; a ausência do campo MUST manter a seleção atual.
- **FR-008**: O sistema MUST persistir no perfil somente o identificador de um avatar existente e ativo no momento da seleção.
- **FR-009**: A resposta de `GET /v1/users/me` MUST incluir a referência utilizável da imagem selecionada; na ausência de seleção ou quando o avatar estiver inativo, MUST incluir a referência da imagem padrão.
- **FR-010**: O sistema MUST rejeitar identificadores inexistentes ou desativados sem alterar a seleção atualmente persistida.
- **FR-011**: Operações de seleção, alteração e remoção MUST exigir autenticação válida e MUST limitar a alteração ao perfil do usuário autenticado.
- **FR-012**: Erros de validação e autenticação MUST seguir o padrão Problem Details adotado pelo projeto.
- **FR-013**: A alteração de persistência MUST preservar usuários existentes e permitir que perfis atuais permaneçam sem avatar selecionado.
- **FR-014**: O contrato do catálogo, do perfil e das operações de seleção/remoção MUST ser documentado, incluindo o procedimento para adicionar ou desativar avatares.
- **FR-015**: A funcionalidade MUST manter inalterados os fluxos existentes de nome, e-mail, senha e exclusão de conta.
- **FR-016**: O sistema MUST possuir testes unitários e de integração cobrindo catálogo, seleção, alteração, remoção, validação, autenticação, imagem padrão e ausência de regressões no perfil.

### Key Entities

- **Avatar**: Opção predefinida de imagem, com identificador estável, nome, referência da imagem e estado de ativação.
- **Perfil do usuário**: Dados do usuário autenticado, podendo referenciar opcionalmente um avatar selecionado.
- **Imagem padrão**: Referência de imagem usada na resposta do perfil quando não existe uma seleção válida e ativa.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos dez avatares iniciais aparecem no catálogo quando estão ativos, cada um com identificador, nome e referência de imagem utilizável.
- **SC-002**: Pelo menos 95% das operações válidas de seleção, alteração e remoção concluem com o perfil refletindo o novo estado na primeira consulta posterior.
- **SC-003**: 100% dos perfis sem seleção ou com avatar desativado retornam a imagem padrão, sem erro para o usuário.
- **SC-004**: 100% das tentativas de selecionar identificadores inexistentes ou desativados são rejeitadas sem modificar a seleção existente.
- **SC-005**: 100% das operações de alteração sem autenticação válida são rejeitadas e nenhum usuário consegue alterar o perfil de outro.
- **SC-006**: Usuários atuais continuam consultando e atualizando seus perfis após a mudança, sem necessidade de selecionar um avatar.
- **SC-007**: Em testes de aceitação, pelo menos 90% dos participantes conseguem consultar o catálogo, selecionar um avatar e removê-lo sem orientação adicional.

## Assumptions

- A autenticação e os endpoints existentes de perfil serão reutilizados; não será criado um fluxo de autenticação novo.
- O catálogo é mantido pelo backend por configuração ou dados versionados, sem interface de administração para usuários.
- As imagens são distribuídas por referências estáveis disponibilizadas pelo backend e não são enviadas, editadas ou processadas pelo usuário.
- A remoção será representada pelo contrato existente de atualização de perfil, sem duplicação de endpoints.
- A funcionalidade não inclui perfis públicos, criação de avatares ou upload de fotos.

