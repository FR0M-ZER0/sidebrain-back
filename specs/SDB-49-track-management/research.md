# Research: Gerenciamento de Trilhas

## Autenticação e ownership

**Decision:** Os endpoints dependerão de `get_current_user`, provider central de autenticação que retorna o usuário autenticado ou `401`. O `trk_user_id` será preenchido exclusivamente pelo contexto; `userId`, `is_deleted`, timestamps e IDs internos não fazem parte dos requests.

**Rationale:** A especificação exige isolamento entre usuários e o código atual não possui um fluxo de login/token implementado. A feature precisa de uma fronteira estável para consumir a autenticação vigente sem duplicar login ou credenciais.

**Alternatives considered:** Aceitar `userId` no payload foi rejeitado por permitir impersonação. Criar login/JWT nesta feature foi rejeitado porque amplia o escopo e não é necessário para o CRUD quando a identidade já é um pressuposto do produto.

## Carregamento da hierarquia

**Decision:** Usar `selectinload` encadeado em uma consulta de leitura, com critérios para `is_deleted = false` em cada relação. O progresso de missão será filtrado por `mpg_user_id` do usuário autenticado; feedbacks e respostas serão retornados conforme o contrato de conteúdo existente, sem dados de auditoria desnecessários.

**Rationale:** A documentação atual do SQLAlchemy recomenda eager loading em `AsyncSession` para evitar lazy loading implícito. `selectinload` agrupa consultas por relação e evita uma consulta por filho, atendendo FR-005d e SC-002b sem o risco de duplicação de linhas de joins profundos.

**Alternatives considered:** `joinedload` foi rejeitado para a árvore com muitas relações 1:N porque pode multiplicar linhas e exigir deduplicação complexa. Lazy loading foi rejeitado por causar N+1 e não ser seguro em código assíncrono.

## Paginação

**Decision:** `page=1`, `page_size=20`, `page >= 1`, `1 <= page_size <= 100`, ordenação estável por `trk_created_at DESC, trk_id DESC`, consulta de total separada e cálculo `ceil(total_items / page_size)`.

**Rationale:** Os valores são compatíveis com a convenção de paginação existente e mantêm o custo previsível. A ordenação explícita torna `limit/offset` determinístico.

**Alternatives considered:** Cursor pagination foi rejeitada porque o contrato vigente exige página, tamanho e total de páginas. Um tamanho ilimitado foi rejeitado por risco de carga e resposta excessiva.

## Exclusão lógica e transações

**Decision:** DELETE atualiza `trk_is_deleted=true` e `trk_deleted_at=now()` em uma transação; listagem e detalhe filtram a trilha. Filhos logicamente excluídos são omitidos da resposta. Falhas de persistência fazem rollback e são convertidas em Problem Details sem detalhes internos.

**Rationale:** Preserva o registro histórico e segue os campos já existentes na migration e no modelo.

**Alternatives considered:** Exclusão física foi rejeitada porque quebra o requisito de preservação. Cascata lógica dos filhos foi rejeitada nesta feature porque os filhos pertencem a outros fluxos; eles apenas são filtrados na leitura da trilha.

## Contratos e erros

**Decision:** Expor `POST /api/v1/tracks`, `GET /api/v1/tracks`, `GET /api/v1/tracks/{track_id}`, `PATCH /api/v1/tracks/{track_id}` e `DELETE /api/v1/tracks/{track_id}`. Respostas de sucesso usam schemas Pydantic; erros usam Problem Details com `400/401/404/422/500` conforme a causa.

**Rationale:** Mantém versionamento explícito, separa HTTP das regras de negócio e evita expor entidades ORM diretamente.

**Alternatives considered:** PUT foi rejeitado para atualização parcial de título/descrição. Retornar `403` para recurso de outro usuário foi rejeitado para não revelar sua existência; ownership falho retorna o mesmo `404` que inexistente.

## Migrações e índices

**Decision:** Não alterar a migration inicial no planejamento-base. Medir a consulta e adicionar migration de índices somente se necessário, priorizando `(trk_user_id, trk_is_deleted, trk_created_at)` e FKs usadas na árvore.

**Rationale:** A estrutura necessária já existe e uma migration especulativa aumenta o risco sem evidência.

**Alternatives considered:** Criar índices automaticamente foi rejeitado até confirmar o plano de execução e o volume esperado.
