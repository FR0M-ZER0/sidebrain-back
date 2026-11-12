# Feature Specification: Consistência e Estratégia Síncrona de XP e Ranking (SDB-105)

**Feature Branch**: `feat/sdb-105-adiciona-filas-gerenciar-xp-ranking`

**Created**: 2026-11-11

**Status**: Draft

**Input**: User description: "SDB-105 — Adicionar filas para gerenciar o xp e o ranking (validar estratégia de atualização de XP e ranking mantendo fonte única de verdade consistente, sem processamento assíncrono nem filas nesta etapa)"

## Clarifications

### Session 2026-11-11

- Q: Onde a decisão arquitetural de manter o cálculo síncrono sem filas e a fórmula oficial de XP devem ficar documentadas para cumprir o critério de aceite da SDB-105? → A: Atualizar o `README.md` (junto às seções de fluxo/rotas do sistema) e adicionar docstrings concisas no fluxo de cálculo e conclusão no código.
- Q: Quando o usuário já concluiu uma missão ativa, mas a etapa (`Step`) ou trilha (`Track`) pai dessa missão é removida logicamente depois, essa missão deve continuar somando XP no perfil e no ranking? → A: Sim, preservar o XP e a contagem da missão concluída enquanto a própria missão e o usuário permanecerem ativos (alinhado à `SDB-90`).
- Q: Que escopo de verificação automatizada a entrega da SDB-105 deve exigir para comprovar o fluxo síncrono de XP e ranking? → A: Validar de ponta a ponta pelas operações públicas da aplicação (submissão que conclui missão, consulta imediata ao perfil e ao ranking geral/individual, recálculo idempotente e exclusão lógica da missão), mantendo a verificação existente de consultas constantes sem adicionar novo benchmark de carga.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Refletir XP e posição imediatamente após concluir uma missão (Priority: P1)

Como estudante autenticado da plataforma, ao concluir uma atividade que completa uma missão, quero que meu total de XP, minha contagem de missões concluídas e minha colocação no ranking sejam atualizados imediatamente após a confirmação da resposta, para visualizar meu progresso real sem atrasos ou inconsistências temporárias.

**Why this priority**: A atualização imediata garante confiança na gamificação da plataforma e evita que o estudante veja pontuações desatualizadas logo após concluir um desafio.

**Independent Test**: Em um cenário com missões ativas vinculadas a uma trilha, concluir a atividade necessária para finalizar uma missão e, logo em seguida, consultar o perfil do usuário e o ranking; verificar que ambos refletem imediatamente a recompensa da missão sem depender de processamento posterior em segundo plano.

**Acceptance Scenarios**:

1. **Given** um usuário ativo com uma missão ativa ainda não concluída vinculada às suas atividades, **When** ele submete a atividade que atende ao critério da missão e a operação é confirmada, **Then** qualquer consulta subsequente ao perfil do usuário e ao ranking já exibe o novo total de XP e o incremento de missão concluída imediatamente.
2. **Given** uma submissão de atividade que ainda não atinge o critério completo da missão ou uma tentativa que falha antes da confirmação final, **When** o perfil ou o ranking são consultados em seguida, **Then** nenhum XP parcial ou indevido é contabilizado para essa missão.

---

### User Story 2 - Garantir regra única entre perfil do usuário e ranking (Priority: P1)

Como estudante autenticado ou administrador de produto, quero que o saldo de XP e a quantidade de missões concluídas exibidos no perfil do usuário sigam exatamente a mesma regra de cálculo aplicada no ranking geral e na consulta da própria posição, para que não haja divergência de números entre diferentes telas da aplicação.

**Why this priority**: Números diferentes para o mesmo usuário entre perfil e ranking quebram a credibilidade do sistema e indicam múltiplas fontes de verdade concorrentes.

**Independent Test**: Configurar usuários ativos com múltiplas missões em diferentes estados (não iniciadas, em andamento, concluídas e excluídas logicamente) e comparar o XP e o total de missões concluídas retornados pela consulta de perfil com os valores retornados pela listagem geral de ranking e pela consulta individual de posição.

**Acceptance Scenarios**:

1. **Given** um usuário ativo com um conjunto variado de missões ativas concluídas e em andamento, **When** ele consulta seu perfil, a listagem geral do ranking e sua posição individual no ranking, **Then** os valores de XP total e de missões concluídas são idênticos nas três consultas.
2. **Given** um usuário ativo sem nenhuma missão ativa concluída, **When** ele consulta seu perfil e o ranking, **Then** ambas as consultas retornam XP igual a 0 e quantidade de missões concluídas igual a 0.

---

### User Story 3 - Assegurar idempotência no recálculo e exclusão de missões removidas (Priority: P2)

Como responsável pela integridade dos dados de aprendizagem, quero que o recálculo de progresso de uma missão já concluída nunca conceda XP em duplicidade e que missões removidas logicamente deixem de somar XP e missões concluídas, para manter a pontuação justa e fiel ao estado vigente da plataforma.

**Why this priority**: Submissões repetidas, reprocessamentos ou remoção de missões antigas são situações recorrentes que não podem inflar artificialmente o XP nem gerar discrepâncias no ranking.

**Independent Test**: Concluir uma missão, acionar novas avaliações ou recálculos de progresso para a mesma missão e confirmar que o XP e a contagem permanecem inalterados; em seguida, remover logicamente uma missão já concluída e confirmar que sua recompensa deixa de compor o XP e a contagem tanto no perfil quanto no ranking.

**Acceptance Scenarios**:

1. **Given** uma missão ativa que já foi concluída por um usuário ativo, **When** novas atividades são enviadas ou o recálculo de progresso dessa trilha/etapa é executado novamente, **Then** o progresso concluído permanece inalterado e a recompensa de XP não é somada uma segunda vez.
2. **Given** um usuário ativo que concluiu uma missão posteriormente marcada como excluída logicamente, **When** o perfil do usuário ou o ranking são consultados, **Then** nem a recompensa de XP nem a contagem dessa missão excluída aparecem nos totais exibidos.

---

### User Story 4 - Formalizar a decisão síncrona sem filas e critérios de reavaliação (Priority: P2)

Como membro da equipe de produto ou engenharia, quero que a fórmula de cálculo de XP, a decisão de não utilizar filas nesta etapa e os critérios objetivos para uma eventual adoção futura de processamento assíncrono fiquem documentados junto ao fluxo de XP e ranking, para evitar a introdução prematura de complexidade operacional e consistência eventual.

**Why this priority**: A task surgiu com título sugerindo filas, mas a decisão arquitetural registrada exige explicitar por que não introduzir filas agora e quais evidências seriam obrigatórias antes de reconsiderar o tema.

**Independent Test**: Inspecionar a documentação vinculada ao fluxo de XP e ranking e verificar que ela descreve claramente a fórmula de XP, a fonte única de verdade síncrona, a ausência de filas/contadores separados e as condições mensuráveis para reavaliação futura.

**Acceptance Scenarios**:

1. **Given** a documentação do fluxo de XP e ranking após a conclusão desta demanda, **When** um integrante do time consulta como o XP e a colocação são calculados e atualizados, **Then** encontra documentados a fórmula oficial de soma das recompensas de missões ativas concluídas, o comportamento síncrono pós-confirmação e a justificativa da ausência de filas.
2. **Given** uma futura proposta de introdução de filas para XP ou ranking, **When** a equipe avalia os pré-requisitos registrados nesta decisão, **Then** encontra explicitado que qualquer mudança assíncrona exige medição prévia de gargalo real, definição de atraso máximo aceitável e desenho de entrega confiável, idempotência e reconciliação.

### Edge Cases

- Recalcular ou reavaliar o progresso de uma missão que já se encontra concluída não deve gerar nova recompensa de XP, alterar o registro de conclusão nem incrementar novamente o total de missões concluídas.
- Se um usuário responder repetidas vezes ao mesmo questionário ou enviar novas respostas em uma aula após já ter concluído a missão associada, o XP total permanece constante.
- Quando uma missão previamente concluída é removida logicamente, a próxima consulta ao perfil ou ao ranking deve desconsiderá-la imediatamente do cálculo de XP e da contagem de missões concluídas, ajustando a posição no ranking de acordo com o novo total.
- Quando uma missão ativa já concluída tem apenas sua etapa ou trilha pai removida logicamente, ela continua contribuindo normalmente para o XP e a contagem de missões concluídas no perfil e no ranking, pois somente a exclusão lógica da própria missão ou do usuário invalida a pontuação.
- Quando todas as missões concluídas de um usuário são removidas logicamente, seu XP e sua contagem de missões concluídas retornam a 0 sem remover o usuário ativo do ranking.
- Usuários removidos logicamente não devem aparecer nas listagens de ranking nem deslocar a posição dos usuários ativos.
- Falhas ocorridas durante a atualização de progresso antes da confirmação da operação devem preservar o estado anterior, sem registrar conclusão parcial de missão nem alteração indevida de XP.
- A introdução de filas de processamento em segundo plano, trabalhadores assíncronos ou contadores redundantes persistidos para XP sem medição de gargalo descaracteriza o escopo aprovado e deve ser tratada como violação da decisão desta demanda.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST calcular o XP total de cada usuário ativo exclusivamente a partir da soma das recompensas de XP das missões ativas (não excluídas logicamente) cujo progresso do usuário esteja concluído, independentemente do estado de exclusão lógica da etapa ou trilha pai.
- **FR-002**: O sistema MUST calcular a quantidade de missões concluídas de cada usuário ativo exclusivamente a partir da contagem das missões ativas (não excluídas logicamente) cujo progresso do usuário esteja concluído, independentemente do estado de exclusão lógica da etapa ou trilha pai.
- **FR-003**: O sistema MUST utilizar a mesma regra de cálculo de XP e missões concluídas nas consultas de perfil do usuário, na listagem geral do ranking e na consulta individual da posição no ranking.
- **FR-004**: O sistema MUST atualizar o progresso das missões de forma atômica junto à operação de conclusão da atividade, de modo que qualquer consulta posterior à confirmação reflita imediatamente o novo XP, a contagem de missões concluídas e a posição no ranking, sem aguardar processamento assíncrono em fila.
- **FR-005**: O sistema MUST manter o recálculo e a atualização de progresso de missões estritamente idempotentes, impedindo concessão duplicada de XP ou alteração de recompensa para uma missão já concluída em submissões repetidas ou recálculos subsequentes.
- **FR-006**: O sistema MUST desconsiderar missões excluídas logicamente no cálculo de XP e de missões concluídas tanto no perfil quanto no ranking, mesmo quando houver registro prévio de conclusão para aquela missão.
- **FR-007**: O sistema MUST preservar como fonte única de verdade os registros persistidos de progresso das missões e suas definições ativas, sem introduzir contadores separados persistidos de XP ou visões materializadas de ranking nesta etapa.
- **FR-008**: A entrega desta demanda MUST NOT adicionar filas de mensageria, tarefas assíncronas em segundo plano, barramentos gerais de eventos ou novas dependências de fila para cálculo ou concessão de XP e ranking.
- **FR-009**: O sistema MUST preservar inalterados os critérios atuais de conclusão de missão, as recompensas definidas nas missões e as regras determinísticas de ordenação e desempate do ranking.
- **FR-010**: A entrega MUST cobrir com verificação automatizada ponta a ponta pelas operações públicas da aplicação todo o fluxo desde a submissão que conclui uma missão até a consulta imediata de perfil e ranking (listagem geral e posição individual), além do recálculo idempotente sem duplicação de XP e da desconsideração de missões excluídas logicamente, sem adicionar novos benchmarks de carga nesta etapa.
- **FR-011**: A decisão arquitetural de manter o cálculo síncrono sem filas, a fórmula oficial de XP e os critérios objetivos para eventual reavaliação futura MUST ficar documentados no `README.md` do projeto (junto aos fluxos e rotas de perfil/ranking) e em docstrings concisas nos módulos do fluxo de conclusão, cálculo de XP, perfil e ranking.

### Key Entities

- **Usuário (User)**: Participante elegível da plataforma cuja atividade e conclusões de missão determinam sua pontuação acumulada e posição no ranking enquanto ativo.
- **Missão (Mission)**: Desafio de aprendizagem associado a uma etapa, portador de uma recompensa fixa de XP; somente missões ativas contribuem para o total de XP e de conclusões.
- **Progresso de Missão (MissionProgress)**: Registro do andamento de um usuário em uma missão; somente registros concluídos servem como base para contabilização de XP e quantidade de missões concluídas.
- **Resumo de XP e Entrada do Ranking (XP Summary / Ranking Entry)**: Visão consolidada e calculada sob demanda contendo pontuação acumulada de XP, total de missões concluídas e colocação global do usuário.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos cenários de conclusão de missão testados de ponta a ponta, a consulta imediatamente posterior ao perfil do usuário e ao ranking reflete a recompensa de XP e a atualização de posição logo após a confirmação da operação, com zero dependência de processamento posterior em fila.
- **SC-002**: Em 100% das comparações realizadas sobre o mesmo conjunto de usuários e missões, o total de XP e o total de missões concluídas retornados no perfil do usuário coincidem exatamente com os valores retornados na listagem geral de ranking e na consulta individual de posição.
- **SC-003**: Em 100% dos cenários de submissão repetida ou recálculo subsequente sobre uma missão já concluída, o acréscimo adicional de XP é igual a 0, mantendo a recompensa contabilizada exatamente uma vez.
- **SC-004**: Em 100% dos cenários envolvendo missões removidas logicamente (mesmo quando previamente concluídas), 0 pontos de XP e 0 conclusões provenientes dessas missões são incluídos no perfil ou no ranking.
- **SC-005**: 100% da suíte automatizada existente e dos novos cenários ponta a ponta pelas operações públicas (conclusão de missão, consulta imediata de perfil/ranking, recálculo idempotente e exclusão lógica de missão) passam integralmente, mantendo quantidade constante de consultas nas leituras de ranking sem adição de filas ou workers assíncronos.
- **SC-006**: 100% dos critérios de documentação estão atendidos com o registro explícito da fórmula de XP, da justificativa de consistência imediata sem filas e dos pré-requisitos mensuráveis para eventual adoção futura de processamento assíncrono.

## Assumptions

- O volume atual de escrita e leitura de missões, perfis e ranking não apresenta evidência medida de gargalo que justifique consistência eventual ou filas dedicadas.
- A autenticação, a estrutura de trilhas, etapas, aulas, questionários, missões e o mecanismo atual de desempate e paginação do ranking já existem e permanecem inalterados.
- Caso medições futuras comprovem contenção ou latência relevante e o produto aceite atraso explícito na exibição do ranking, uma nova tarefa específica deverá ser aberta antes de implementar qualquer mecanismo assíncrono, definindo métricas de justificativa, atraso máximo tolerável, garantias de entrega, idempotência e reconciliação com a fonte de verdade.

