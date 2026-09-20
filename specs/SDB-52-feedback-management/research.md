# Research: Gerenciamento de Feedback

## Autenticação e ownership

**Decision:** Todos os endpoints usam `get_current_user`. O service recebe o
`User` autenticado e usa seu `usr_id` para criar e autorizar alterações. O
cliente não envia `user_id`/`author_id` como requisito de criação.

**Rationale:** O provider já valida Bearer e usuário ativo. Reutilizá-lo evita
duplicação e impede impersonação. Feedback de outro usuário é tratado como
inacessível nas operações de mutação, sem expor ownership.

**Alternatives considered:** Aceitar autoria no body foi rejeitado por risco de
impersonação. Criar autenticação nova foi rejeitado por estar fora do escopo.

## Rotas e contratos

**Decision:** Expor `POST` e `GET` em `/api/v1/lessons/{lesson_id}/feedbacks`, e
`GET`, `PATCH` e `DELETE` em `/api/v1/feedbacks/{feedback_id}`. A coleção usa o
envelope paginado padrão. Responses usam schemas Pydantic com aliases públicos.

**Rationale:** A aula é o agregado natural para criação/listagem, enquanto o
identificador do feedback é o recurso natural para detalhe e mutação. O padrão
de paginação do repositório evita listas sem limite.

**Alternatives considered:** Rotas aninhadas para todas as operações foram
rejeitadas porque exigiriam validar simultaneamente dois identificadores em
updates/deletes. Retornar ORM diretamente foi rejeitado por expor colunas físicas.

## Aula ativa e exclusão lógica

**Decision:** Criar e listar primeiro validam `Lesson.lsn_id` com
`lsn_is_deleted = false`. Feedbacks usam `fbk_is_deleted = false` nas consultas;
DELETE preenche `fbk_deleted_at` e atualiza `fbk_updated_at` sem remover a linha.

**Rationale:** A tabela e os campos de ciclo de vida já existem na migration
inicial e o modelo já possui as relações necessárias. O filtro consistente evita
que aulas ou feedbacks excluídos reapareçam.

**Alternatives considered:** Exclusão física foi rejeitada por quebrar histórico
e integridade. Cascatear exclusão a partir da aula foi rejeitado porque o ciclo
de vida da aula pertence a outra feature.

## Validação e transações

**Decision:** `text` será obrigatório, normalizado com `strip()` e validado como
não vazio, com `extra="forbid"`. Criação/edição fazem commit apenas após todas as
validações; falhas fazem rollback e retornam Problem Details.

**Rationale:** Isso cobre campos internos injetados e evita persistência parcial,
seguindo os padrões de `TrackInput` e `TrackUpdate`.

**Alternatives considered:** Aceitar whitespace ou campos extras foi rejeitado
por produzir feedback inútil e permitir tentativa de alterar metadados internos.

## Carregamento da hierarquia e desempenho

**Decision:** Manter `selectinload(Lesson.feedbacks.and_(Feedback.fbk_is_deleted.is_(False)))`
na opção de hierarquia do `TrackRepository`; respostas de aula usam o mesmo
schema público. A listagem direta usa uma query de total e uma query paginada.

**Rationale:** O padrão já existe e agrupa filhos por relação, evitando N+1 em
uma aula com pelo menos 50 feedbacks. `selectinload` é adequado à sessão
assíncrona e a relações 1:N.

**Alternatives considered:** Lazy loading foi rejeitado por N+1 e risco de I/O
implícito em async. `joinedload` foi rejeitado por multiplicação de linhas na
hierarquia completa.

## Banco e migrações

**Decision:** Não criar migration nesta fase: `feedback` já tem PK UUID, FKs,
timestamps e flags de exclusão. Índices adicionais só serão planejados se a
validação de consulta demonstrar necessidade.

**Rationale:** Evita alteração de schema sem evidência e mantém migrations
versionadas/reversíveis conforme a constituição.

**Alternatives considered:** Adicionar índices especulativos foi rejeitado até
medir o plano de execução e o volume real.
